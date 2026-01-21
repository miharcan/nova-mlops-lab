from __future__ import annotations

from openstack import connection


def get_conn(cloud: str | None = None):
    """
    Uses clouds.yaml (preferred) or OS_* env vars.
    """
    if cloud:
        return connection.from_config(cloud=cloud)
    return connection.from_config()

