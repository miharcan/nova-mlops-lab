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
    """NLP demo payload.

    Always works in "console-log mode" (no SSH / no floating IP required).
    
    If a Cinder *data* volume is attached as /dev/vdb, this payload will:
      - format it (if it has no filesystem)
      - mount it at /mnt/results
      - write result.json and a copy of the job log
    This lets you demo Cinder + Horizon by inspecting the volume after the job.
    """

    return f"""#cloud-config
package_update: true
packages:
  - python3-pip

write_files:
  - path: /usr/local/bin/nova-mlops-mount-results.sh
    permissions: "0755"
    content: |
      #!/usr/bin/env bash
      set -euo pipefail
      DEV=/dev/vdb
      MNT=/mnt/results
      if [ ! -b "$DEV" ]; then
        echo "[NOVA-MLOPS] no_results_volume=true" | tee /dev/ttyS0
        exit 0
      fi
      mkdir -p "$MNT"
      if ! blkid "$DEV" >/dev/null 2>&1; then
        echo "[NOVA-MLOPS] formatting_results_volume=true" | tee /dev/ttyS0
        mkfs.ext4 -F "$DEV" >/dev/null
      fi
      mount "$DEV" "$MNT"
      chmod 0777 "$MNT" || true
      echo "[NOVA-MLOPS] mounted_results_volume=true mountpoint=$MNT" | tee /dev/ttyS0

  - path: /tmp/nova_mlops_sentiment.py
    permissions: "0755"
    content: |
      from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
      import json, os

      job = 'sentiment-demo'
      texts = [
          "I love this product.",
          "This is the worst experience I've had.",
          "The service was okay, nothing special.",
      ]

      a = SentimentIntensityAnalyzer()
      out = []
      for t in texts:
          s = a.polarity_scores(t)
          out.append({"text": t, **s})
          print("[NOVA-MLOPS] job=%s text=%r compound=%+.3f" % (job, t, s["compound"]))

      result_dir = os.environ.get("NOVA_MLOPS_RESULTS_DIR", "")
      if result_dir:
          os.makedirs(result_dir, exist_ok=True)
          with open(os.path.join(result_dir, "result.json"), "w") as f:
              json.dump({"job": job, "results": out}, f)
runcmd:
  - [ bash, -lc, "set -euxo pipefail; /usr/local/bin/nova-mlops-mount-results.sh || true" ]
  - [ bash, -lc, "set -euxo pipefail; python3 -m pip install --no-cache-dir -q vaderSentiment; NOVA_MLOPS_RESULTS_DIR=/mnt/results python3 /tmp/nova_mlops_sentiment.py | tee /dev/ttyS0 /var/log/nova-mlops.log" ]
  - [ bash, -lc, "set -euxo pipefail; if mountpoint -q /mnt/results; then cp -f /var/log/nova-mlops.log /mnt/results/nova-mlops.log; sync; umount /mnt/results; fi" ]
  - [ bash, -lc, "poweroff" ]
"""

