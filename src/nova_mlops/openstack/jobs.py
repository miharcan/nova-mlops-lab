from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from datetime import datetime, timezone

from nova_mlops.run_id import new_run_id
from nova_mlops.jobs.state_store import write_job_state
from nova_mlops.openstack.cloud_init import nlp_inference_cloud_init


@dataclass
class JobLaunchResult:
    server_id: str
    server_name: str
    run_id: str
    swift_container: str
    swift_results_object: str
    swift_manifest_object: str
    swift_log_object: str
    volume_id: str | None = None



def launch_job(
    conn,
    name: str,
    image: str,
    flavor: str,
    network: str,
    user_data: Optional[str] = None,
    cinder_volume_size_gb: int | None = None,
    cinder_volume_name: str | None = None,
) -> JobLaunchResult:
    img = conn.compute.find_image(image)
    flv = conn.compute.find_flavor(flavor)
    net = conn.network.find_network(network)

    if not img:
        raise RuntimeError(f"Image not found: {image}")
    if not flv:
        raise RuntimeError(f"Flavor not found: {flavor}")
    if not net:
        raise RuntimeError(f"Network not found: {network}")

    run_id = new_run_id()
    
    #server_name = f"mlops-{name}"
    # include run_id in server name to avoid collisions
    server_name = f"mlops-{name}-{run_id}"

    swift_container = "mlops-artifacts"
    swift_results_object = f"results/{name}/{run_id}/results.json"
    swift_manifest_object = f"manifests/{name}/{run_id}.json"
    swift_log_object = f"logs/{name}/{run_id}.log"

    volume_id: str | None = None
    bdmv2 = None
   
    # Normalize 0/negative to "no volume"
    if cinder_volume_size_gb is not None and cinder_volume_size_gb <= 0:
        cinder_volume_size_gb = None

    if cinder_volume_size_gb is not None:
        vol_name = cinder_volume_name or f"mlops-{name}-results"
        vol = conn.block_storage.create_volume(name=vol_name, size=cinder_volume_size_gb)
        vol = conn.block_storage.wait_for_status(
            vol, status="available", failures=["error"], interval=2, wait=600
        )
        volume_id = vol.id
        bdmv2 = [{
            "uuid": volume_id,
            "source_type": "volume",
            "destination_type": "volume",
            "boot_index": -1,
            "delete_on_termination": False,
        }]


    #ud = (user_data or training_cloud_init(name))
    #ud_b64 = base64.b64encode(ud.encode("utf-8")).decode("ascii")

    if user_data is not None:
        ud = user_data
    else:
        # For NLP job runner, use the richer template.
        # If you're launching "training" jobs, call training_cloud_init(name, run_id) instead.
        ud = nlp_inference_cloud_init(
            job_name=name,
            run_id=run_id,
            swift_container=swift_container,
            swift_results_object=swift_results_object,
            swift_manifest_object=swift_manifest_object,
            swift_log_object=swift_log_object,
            image=image,
            flavor=flavor,
            network=network,
        )

    create_kwargs = dict(
        name=server_name,
        image_id=img.id,
        flavor_id=flv.id,
        networks=[{"uuid": net.id}],
        user_data=ud  # ud_b64,
    )

    if bdmv2 is not None:
        create_kwargs["block_device_mapping_v2"] = bdmv2

    server = conn.compute.create_server(**create_kwargs)


    server = conn.compute.wait_for_server(server)
    state = {
        "job": name,
        "run_id": run_id,
        "server_id": server.id,
        "server_name": server.name,
        "image": image,
        "flavor": flavor,
        "network": network,
        "swift": {
            "container": swift_container,
            "results_object": swift_results_object,
            "manifest_object": swift_manifest_object,
            "log_object": swift_log_object,
        },
        "volume_id": volume_id,
        "created_at": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
    }
    write_job_state(name, state)

    return JobLaunchResult(
        server_id=server.id,
        server_name=server.name,
        run_id=run_id,
        swift_container=swift_container,
        swift_results_object=swift_results_object,
        swift_manifest_object=swift_manifest_object,
        swift_log_object=swift_log_object,
        volume_id=volume_id,
    )



def get_console_logs(conn, server_id: str, length: int | None = None) -> str:
    # openstacksdk supports console logs via compute proxy
    return conn.compute.get_server_console_output(server_id, length=length)
