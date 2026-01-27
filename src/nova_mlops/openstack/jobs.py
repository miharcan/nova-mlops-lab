from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from nova_mlops.openstack.cloud_init import training_cloud_init

import base64

@dataclass
class JobLaunchResult:
    server_id: str
    server_name: str
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

    server_name = f"mlops-{name}"

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


    ud = (user_data or training_cloud_init(name))
    ud_b64 = base64.b64encode(ud.encode("utf-8")).decode("ascii")

    create_kwargs = dict(
        name=server_name,
        image_id=img.id,
        flavor_id=flv.id,
        networks=[{"uuid": net.id}],
        user_data=ud_b64,
    )

    if bdmv2 is not None:
        create_kwargs["block_device_mapping_v2"] = bdmv2

    server = conn.compute.create_server(**create_kwargs)


    server = conn.compute.wait_for_server(server)
    return JobLaunchResult(server_id=server.id, server_name=server.name, volume_id=volume_id)


def get_console_logs(conn, server_id: str, length: int | None = None) -> str:
    # openstacksdk supports console logs via compute proxy
    return conn.compute.get_server_console_output(server_id, length=length)
