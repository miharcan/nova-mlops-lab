from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

STATE_DIR = Path(".nova-mlops/state")


def write_job_state(job_name: str, state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / f"{job_name}.json").write_text(json.dumps(state, indent=2))


def read_job_state(job_name: str) -> Optional[dict[str, Any]]:
    p = STATE_DIR / f"{job_name}.json"
    return json.loads(p.read_text()) if p.exists() else None

