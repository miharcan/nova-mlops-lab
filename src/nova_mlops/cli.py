from __future__ import annotations
from pathlib import Path
import typer
import yaml
from rich import print
from rich.table import Table

from nova_mlops.jobs.models import JobSpec
from nova_mlops.jobs.scheduler import run_local
from nova_mlops.jobs.state_store import read_job_state, write_job_state

app = typer.Typer(add_completion=False)

def load_job(path: Path) -> JobSpec:
    data = yaml.safe_load(path.read_text())
    return JobSpec.from_dict(data)


@app.command()
def submit(job_file: Path):
    job = load_job(job_file)
    if job.resources.cloud != "local":
        raise typer.BadParameter("Only local is supported in MVP. Set resources.cloud=local.")
    rc = run_local(job)
    raise typer.Exit(code=rc)

@app.command()
def status(name: str):
    st = read_job_state(name)
    if not st:
        print(f"[red]No state found for[/red] {name}")
        raise typer.Exit(code=1)
    print(st)


openstack_app = typer.Typer()
app.add_typer(openstack_app, name="openstack")

@openstack_app.command("ping")
def openstack_ping(cloud: str = typer.Option(None, help="Cloud name from clouds.yaml")):
    from nova_mlops.openstack.connection import get_conn
    from nova_mlops.openstack.probe import ping

    conn = get_conn(cloud=cloud)
    summary = ping(conn)
    print({"region": summary.region, "project_id": summary.project_id, "user_id": summary.user_id})


@openstack_app.command("flavors")
def openstack_flavors(cloud: str = typer.Option(None), limit: int = typer.Option(20)):
    from nova_mlops.openstack.connection import get_conn
    from nova_mlops.openstack.probe import list_flavors

    conn = get_conn(cloud=cloud)
    rows = list_flavors(conn, limit=limit)

    t = Table(title="Flavors")
    t.add_column("Name")
    t.add_column("VCPUs")
    t.add_column("RAM(MB)")
    t.add_column("Disk(GB)")
    for f in rows:
        t.add_row(str(f.name), str(getattr(f, "vcpus", "")), str(getattr(f, "ram", "")), str(getattr(f, "disk", "")))
    print(t)


@openstack_app.command("images")
def openstack_images(cloud: str = typer.Option(None), limit: int = typer.Option(20)):
    from nova_mlops.openstack.connection import get_conn
    from nova_mlops.openstack.probe import list_images

    conn = get_conn(cloud=cloud)
    rows = list_images(conn, limit=limit)

    t = Table(title="Images")
    t.add_column("Name")
    t.add_column("ID")
    for img in rows:
        t.add_row(str(img.name), str(img.id))
    print(t)


@openstack_app.command("networks")
def openstack_networks(cloud: str = typer.Option(None), limit: int = typer.Option(20)):
    from nova_mlops.openstack.connection import get_conn
    from nova_mlops.openstack.probe import list_networks

    conn = get_conn(cloud=cloud)
    rows = list_networks(conn, limit=limit)

    t = Table(title="Networks")
    t.add_column("Name")
    t.add_column("ID")
    for n in rows:
        t.add_row(str(n.name), str(n.id))
    print(t)


@openstack_app.command("run")
def openstack_run(
    name: str,
    image: str = typer.Option("ubuntu-22.04", help="Image name (Glance)"),
    flavor: str = typer.Option("m1.small", help="Flavor name"),
    network: str = typer.Option("private", help="Tenant network name"),
    cloud: str = typer.Option(None, help="Cloud name from clouds.yaml"),
):
    """
    Launch a VBox-safe 'training job' as a Nova instance using cloud-init.
    """
    from nova_mlops.openstack.connection import get_conn
    from nova_mlops.openstack.jobs import launch_job

    conn = get_conn(cloud=cloud)
    res = launch_job(conn, name=name, image=image, flavor=flavor, network=network)

    st = read_job_state(name) or {}
    st.update(
        {
            "name": name,
            "backend": "openstack",
            "cloud": cloud,
            "server_id": res.server_id,
            "server_name": res.server_name,
            "image": image,
            "flavor": flavor,
            "network": network,
            "status": "RUNNING",
        }
    )
    write_job_state(name, st)
    print({"job": name, "server_id": res.server_id, "server_name": res.server_name})


@openstack_app.command("logs")
def openstack_logs(
    name: str,
    cloud: str = typer.Option(None, help="Cloud name from clouds.yaml (optional)"),
):
    """
    Fetch console logs from Nova for a previously launched job.
    """
    from nova_mlops.openstack.connection import get_conn
    from nova_mlops.openstack.jobs import get_console_logs

    st = read_job_state(name)
    if not st or "server_id" not in st:
        print(f"[red]No OpenStack server_id found for job[/red] {name}")
        raise typer.Exit(code=1)

    conn = get_conn(cloud=cloud or st.get("cloud"))
    out = get_console_logs(conn, st["server_id"])
    print(out)


@openstack_app.command("cleanup")
def openstack_cleanup(
    name: str,
    cloud: str = typer.Option(None, help="Cloud name from clouds.yaml (optional)"),
    delete_volume: bool = typer.Option(
        False,
        help="Also delete the job's Cinder results volume if one was created.",
    ),
):
    """
    Delete the Nova instance for a job (idempotent).
    """
    from nova_mlops.openstack.connection import get_conn
    from nova_mlops.openstack.jobs import delete_server

    st = read_job_state(name)
    if not st or "server_id" not in st:
        print(f"[yellow]Nothing to cleanup for[/yellow] {name}")
        raise typer.Exit(code=0)

    conn = get_conn(cloud=cloud or st.get("cloud"))
    delete_server(conn, st["server_id"])

    if delete_volume and st.get("volume_id"):
        # Best-effort; volume may already be deleted or still in-use.
        try:
            conn.block_storage.delete_volume(st["volume_id"], ignore_missing=True)
            print(f"[green]Deleted volume[/green] {st['volume_id']}")
        except Exception as e:
            print(f"[yellow]Could not delete volume[/yellow] {st['volume_id']}: {e}")

    st["status"] = "DELETED"
    write_job_state(name, st)
    print(f"[green]Deleted server[/green] {st['server_id']}")



@openstack_app.command("run-nlp")
def openstack_run_nlp(
    name: str,
    image: str = typer.Option("ubuntu-jammy", help="Image name (Glance)"),
    flavor: str = typer.Option("m1.small", help="Flavor name"),
    network: str = typer.Option("private", help="Tenant network name"),
    cloud: str = typer.Option(None, help="Cloud name from clouds.yaml"),
    cinder_volume_size_gb: int = typer.Option(
        1,
        help="Create and attach a Cinder data volume of this size (GB) at /dev/vdb for job artifacts. Set 0 to disable.",
    ),
):
    """
    Launch a quick NLP inference demo as a Nova instance (cloud-init).
    """
    from nova_mlops.openstack.connection import get_conn
    from nova_mlops.openstack.jobs import launch_job
    from nova_mlops.openstack.cloud_init import nlp_inference_cloud_init

    conn = get_conn(cloud=cloud)
    #res = launch_job(
    #    conn,
    #    name=name,
    #    image=image,
    #    flavor=flavor,
    #    network=network,
    #    user_data=nlp_inference_cloud_init(name),
    #    cinder_volume_size_gb=(cinder_volume_size_gb if cinder_volume_size_gb > 0 else None),
    #    cinder_volume_name=f"mlops-{name}-results",
    #)
    res = launch_job(
        conn,
        name=name,
        image=image,
        flavor=flavor,
        network=network,
        cinder_volume_size_gb=(cinder_volume_size_gb if cinder_volume_size_gb > 0 else None),
        cinder_volume_name=f"mlops-{name}-results",
    )

    st = read_job_state(name) or {}
    st.update(
        {
            "name": name,
            "backend": "openstack",
            "cloud": cloud,
            "server_id": res.server_id,
            "server_name": res.server_name,
            "volume_id": getattr(res, "volume_id", None),
            "image": image,
            "flavor": flavor,
            "network": network,
            "status": "RUNNING",
        }
    )
    write_job_state(name, st)

    #print({"job": name, "server_id": res.server_id, "server_name": res.server_name})
    print(
        {
            "job": name,
            "server_id": res.server_id,
            "server_name": res.server_name,
            "run_id": st.get("run_id"),
            "swift_results": st.get("swift", {}).get("results_object"),
            "swift_manifest": st.get("swift", {}).get("manifest_object"),
            "swift_log": st.get("swift", {}).get("log_object"),
        }
    )

