from __future__ import annotations

import os
from openstack import connection


def get_conn(cloud: str | None = None):
    """
    Create an OpenStack SDK connection.

    DevStack commonly publishes only PUBLIC endpoints. So we default to public,
    but allow override via OS_INTERFACE.
    """
    interface = os.environ.get("OS_INTERFACE", "public")
    region = os.environ.get("OS_REGION_NAME", None)

    kwargs = {"cloud": cloud, "interface": interface}
    if region:
        kwargs["region_name"] = region

    return connection.from_config(**kwargs)

