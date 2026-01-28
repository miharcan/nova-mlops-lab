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
    return f"""#cloud-config
package_update: true
packages:
  - python3-pip
  - util-linux

runcmd:
  - |
      set -eu

      mkdir -p /var/log/mlops
      LOG=/var/log/mlops/job.log
      exec >>"$LOG" 2>&1
      tail -n +1 -f "$LOG" >/dev/console &

      echo "[NOVA-MLOPS] job={job_name} starting"

      apt-get update -y
      apt-get install -y python3-venv python3-full

      python3 -m venv /opt/mlops-venv
      /opt/mlops-venv/bin/pip install --upgrade pip
      /opt/mlops-venv/bin/pip install vaderSentiment

      DEV="/dev/vdb"
      MNT="/mnt/results"

      if [ -b "$DEV" ]; then
        mkdir -p "$MNT"
        if ! blkid "$DEV" >/dev/null 2>&1; then
          mkfs.ext4 -F "$DEV"
        fi
        mount "$DEV" "$MNT"
        echo "[NOVA-MLOPS] mounted $DEV at $MNT"
      else
        echo "[NOVA-MLOPS] no cinder volume detected at $DEV; using /tmp"
        MNT="/tmp"
      fi

      /opt/mlops-venv/bin/python - <<'PY'
      import json
      from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

      job = "{job_name}"
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
      echo "[NOVA-MLOPS] job={job_name} done; result at $MNT/result.json"
      poweroff
"""

