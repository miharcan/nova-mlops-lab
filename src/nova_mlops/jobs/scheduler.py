from __future__ import annotations
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from .models import JobSpec
from .state_store import write_job_state

def _args_to_cli(args: dict) -> list[str]:
    out: list[str] = []
    for k, v in args.items():
        out += [f"--{k}", str(v)]
    return out

def run_local(job: JobSpec) -> int:
    out_dir = Path(job.artifacts.output_dir) / job.name
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = job.run.entrypoint.split() + _args_to_cli(job.run.args) + ["--output_dir", str(out_dir)]

    write_job_state(job.name, {
        "name": job.name,
        "cloud": job.resources.cloud,
        "status": "RUNNING",
        "cmd": cmd,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "artifact_dir": str(out_dir),
    })

    proc = subprocess.run(cmd, capture_output=False)
    status = "SUCCEEDED" if proc.returncode == 0 else "FAILED"

    write_job_state(job.name, {
        "name": job.name,
        "cloud": job.resources.cloud,
        "status": status,
        "returncode": proc.returncode,
        "cmd": cmd,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "artifact_dir": str(out_dir),
    })
    return proc.returncode
