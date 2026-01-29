from __future__ import annotations

from openstack import connection

from nova_mlops.run_id import new_run_id
from nova_mlops.openstack.cloud_init import training_cloud_init
from nova_mlops.openstack.cloud_init import nlp_inference_cloud_init


def get_conn():
    """
    Uses the same auth as the `openstack` CLI:
    env vars or clouds.yaml
    """
    return connection.from_config()


def boot_job(
    job_name: str,
    image: str,
    flavor: str,
    network: str,
    swift_container: str = "mlops-artifacts",
) -> dict[str, str]:
    conn = get_conn()

    img = conn.compute.find_image(image)
    flv = conn.compute.find_flavor(flavor)
    net = conn.network.find_network(network)

    if not img or not flv or not net:
        raise RuntimeError("image, flavor, or network not found")

    run_id = new_run_id()

    # Swift prefix layout
    swift_results_object = f"results/{job_name}/{run_id}/results.json"
    swift_manifest_object = f"manifests/{job_name}/{run_id}.json"
    swift_log_object = f"logs/{job_name}/{run_id}.log"

    # Avoid name collisions by including run_id
    server_name = f"mlops-{job_name}-{run_id}"

    user_data = nlp_inference_cloud_init(
        job_name=job_name,
        run_id=run_id,
        swift_container="mlops-artifacts",
        swift_results_object=f"results/{job_name}/{run_id}/results.json",
        swift_manifest_object=f"manifests/{job_name}/{run_id}.json",
        swift_log_object=f"logs/{job_name}/{run_id}.log",
        image=image,
        flavor=flavor,
        network=network,
    )

    server = conn.compute.create_server(
        name=server_name,
        image_id=img.id,
        flavor_id=flv.id,
        networks=[{"uuid": net.id}],
        user_data=user_data,
    )

    server = conn.compute.wait_for_server(server)

    return {
        "job": job_name,
        "run_id": run_id,
        "server_id": server.id,
        "server_name": server_name,
        "image": image,
        "flavor": flavor,
        "network": network,
        "swift_container": swift_container,
        "swift_results_object": swift_results_object,
        "swift_manifest_object": swift_manifest_object,
        "swift_log_object": swift_log_object,
    }


def get_console_logs(server_id: str) -> str:
    conn = get_conn()
    return conn.compute.get_server_console_output(server_id)