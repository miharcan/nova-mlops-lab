from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from nova_mlops.openstack.cloud_init import training_cloud_init


@dataclass
class JobLaunchResult:
    server_id: str
    server_name: str


def launch_job(
    conn,
    name: str,
    image: str,
    flavor: str,
    network: str,
    user_data: Optional[str] = None,
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

    server_name = f"mlops-{name}"
    server = conn.compute.create_server(
        name=server_name,
        image_id=img.id,
        flavor_id=flv.id,
        networks=[{"uuid": net.id}],
        user_data=(user_data or training_cloud_init(name)),
    )
    server = conn.compute.wait_for_server(server)
    return JobLaunchResult(server_id=server.id, server_name=server.name)


def get_console_logs(conn, server_id: str, length: int | None = None) -> str:
    # openstacksdk supports console logs via compute proxy
    return conn.compute.get_server_console_output(server_id, length=length)
