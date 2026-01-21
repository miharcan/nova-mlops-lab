from openstack import connection
from nova_mlops.jobs.cloud_init import training_cloud_init


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
) -> str:
    conn = get_conn()

    img = conn.compute.find_image(image)
    flv = conn.compute.find_flavor(flavor)
    net = conn.network.find_network(network)

    if not img or not flv or not net:
        raise RuntimeError("image, flavor, or network not found")

    server = conn.compute.create_server(
        name=f"mlops-{job_name}",
        image_id=img.id,
        flavor_id=flv.id,
        networks=[{"uuid": net.id}],
        user_data=training_cloud_init(job_name),
    )

    server = conn.compute.wait_for_server(server)
    return server.id


def get_console_logs(server_id: str) -> str:
    conn = get_conn()
    return conn.compute.get_server_console_output(server_id)
