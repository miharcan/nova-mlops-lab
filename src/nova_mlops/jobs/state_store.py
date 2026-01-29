from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

STATE_DIR = Path(".nova-mlops/state")


def write_job_state(job_name: str, state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = STATE_DIR / f"{job_name}.json"
    path.write_text(json.dumps(state, indent=2, sort_keys=True))


def read_job_state(job_name: str) -> Optional[dict[str, Any]]:
    path = STATE_DIR / f"{job_name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())
