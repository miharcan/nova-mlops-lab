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

      # Install deps: sentiment + openstack client (for Swift)
      /opt/mlops-venv/bin/pip install vaderSentiment python-openstackclient

      # -----------------------------
      # Swift auth via App Credential
      # -----------------------------
      export OS_AUTH_TYPE="v3applicationcredential"
      export OS_AUTH_URL="http://192.168.122.109/identity/v3"
      export OS_REGION_NAME="RegionOne"
      export OS_INTERFACE="public"
      export OS_IDENTITY_API_VERSION="3"
      export OS_APPLICATION_CREDENTIAL_ID="dab821281aac43439313db09d055005f"
      export OS_APPLICATION_CREDENTIAL_SECRET="rgZ-WTKyBNSKjdwhuUij2vxfjQce4Sr8vjm0IUffuUlIWvr21D7bL-8FaZDg1HK13TtJCJ32QFvm0_5LttsLPg"

      echo "[NOVA-MLOPS] swift container list:"
      /opt/mlops-venv/bin/openstack container list || true

      # Optional: download input.txt from Swift if it exists
      INPUT=/tmp/input.txt
      if /opt/mlops-venv/bin/openstack object show mlops-artifacts input.txt >/dev/null 2>&1; then
        /opt/mlops-venv/bin/openstack object save mlops-artifacts input.txt --file "$INPUT"
        echo "[NOVA-MLOPS] downloaded swift://mlops-artifacts/input.txt -> $INPUT"
      else
        echo "[NOVA-MLOPS] no swift input.txt found; using built-in texts"
      fi

      # -----------------------------
      # (Optional) Cinder mount logic
      # -----------------------------
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

      # -----------------------------
      # Run sentiment + write result
      # -----------------------------
      /opt/mlops-venv/bin/python - <<'PY'
import json, os
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

job = "{job_name}"
input_path = "/tmp/input.txt"

if os.path.exists(input_path):
    with open(input_path, "r", encoding="utf-8") as f:
        texts = [ln.strip() for ln in f.readlines() if ln.strip()]
else:
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

with open("/tmp/result.json", "w", encoding="utf-8") as f:
    json.dump({{"job": job, "results": out}}, f)

print("[NOVA-MLOPS] wrote /tmp/result.json", flush=True)
PY

      # Copy to mounted results path if present
      if [ "$MNT" != "/tmp" ]; then
        cp -f /tmp/result.json "$MNT/result.json"
        echo "[NOVA-MLOPS] copied result to $MNT/result.json"
      else
        echo "[NOVA-MLOPS] MNT=/tmp, result stays at /tmp/result.json"
      fi

      sync
      echo "[NOVA-MLOPS] job={job_name} done"

      # -----------------------------
      # Upload result to Swift
      # -----------------------------
      TS=$(date +%s)
      OBJ="results/{job_name}-${{TS}}.json"
      /opt/mlops-venv/bin/openstack object create mlops-artifacts /tmp/result.json --name "$OBJ" || true
      echo "[NOVA-MLOPS] uploaded swift://mlops-artifacts/$OBJ"

      echo "===MLOPS_RESULT==="; cat /tmp/result.json

      echo "===MLOPS_SWIFT_OBJECT==="
      echo "container=mlops-artifacts object=$OBJ"
      echo "===MLOPS_SWIFT_OBJECT_END==="

      poweroff
"""

