# src/nova_mlops/run_id.py
from __future__ import annotations
from datetime import datetime, timezone
import secrets


def new_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = secrets.token_hex(4)  # 8 hex chars
    return f"{ts}-{suffix}"
