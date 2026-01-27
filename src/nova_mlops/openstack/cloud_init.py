def training_cloud_init(job_name: str) -> str:
    """
    VBox-safe demo payload: emits logs to the Nova console via cloud-init.
    No SSH / no floating IP required.
    """
    return f"""#cloud-config
runcmd:
  - echo "[NOVA-MLOPS] job={job_name} step=setup"
  - sleep 2
  - echo "[NOVA-MLOPS] job={job_name} step=train epoch=1 loss=0.91"
  - sleep 2
  - echo "[NOVA-MLOPS] job={job_name} step=train epoch=2 loss=0.73"
  - sleep 2
  - echo "[NOVA-MLOPS] job={job_name} step=done"
"""


def nlp_inference_cloud_init(job_name: str) -> str:
    """
    Return cloud-init user-data that installs vaderSentiment, runs a tiny sentiment job,
    writes results to /mnt/results if a Cinder volume is attached as /dev/vdb,
    and prints progress to the console.
    """
    #cloud-config
    return f"""#cloud-config
package_update: true
packages:
  - python3-pip
  - util-linux

runcmd:
  - |
      set -euxo pipefail
      echo "[NOVA-MLOPS] job={job_name} starting" | tee /dev/console

      # If a Cinder volume is attached, it usually appears as /dev/vdb in DevStack
      DEV="/dev/vdb"
      MNT="/mnt/results"

      if [ -b "$DEV" ]; then
        mkdir -p "$MNT"
        # Format only if it looks unformatted
        if ! blkid "$DEV" >/dev/null 2>&1; then
          mkfs.ext4 -F "$DEV"
        fi
        mount "$DEV" "$MNT"
        echo "[NOVA-MLOPS] mounted $DEV at $MNT" | tee /dev/console
      else
        echo "[NOVA-MLOPS] no cinder volume detected at $DEV; using /tmp" | tee /dev/console
        MNT="/tmp"
      fi

      python3 - <<'PY'
import json
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

job = {job_name!r}
texts = [
  "OpenStack executed this workload successfully.",
  "The networking setup was painful but now it's solid.",
  "I would not recommend debugging NAT at midnight."
]

a = SentimentIntensityAnalyzer()
out = []
for t in texts:
    s = a.polarity_scores(t)
    out.append({{"text": t, **s}})
    print(f"[NOVA-MLOPS] job={{job}} compound={{s['compound']:+.3f}} text={{t!r}}", flush=True)

with open("/tmp/result.json", "w") as f:
    json.dump({{"job": job, "results": out}}, f)

print("[NOVA-MLOPS] wrote /tmp/result.json", flush=True)
PY

      cp -f /tmp/result.json "$MNT/result.json"
      sync
      echo "[NOVA-MLOPS] job={job_name} done; result at $MNT/result.json" | tee /dev/console
      poweroff
"""

