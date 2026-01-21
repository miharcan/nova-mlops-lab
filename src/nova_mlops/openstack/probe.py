from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class CloudSummary:
    region: str | None
    project_id: str | None
    user_id: str | None


def ping(conn) -> CloudSummary:
    # This is intentionally lightweight and read-only.
    auth = getattr(conn, "current_project_id", None)
    user = getattr(conn, "current_user_id", None)
    region = getattr(conn, "region_name", None)
    return CloudSummary(region=region, project_id=auth, user_id=user)


def list_flavors(conn, limit: int = 20):
    return list(conn.compute.flavors(details=True))[:limit]


def list_images(conn, limit: int = 20):
    return list(conn.compute.images())[:limit]


def list_networks(conn, limit: int = 20):
    return list(conn.network.networks())[:limit]

