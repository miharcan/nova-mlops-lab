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

write_files:
  - path: /tmp/nova_mlops_sentiment.py
    permissions: "0755"
    content: |
      from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

      job = 'sentiment-demo'
      texts = [
          "I love this product.",
          "This is the worst experience I've had.",
          "The service was okay, nothing special.",
      ]

      a = SentimentIntensityAnalyzer()
      for t in texts:
          s = a.polarity_scores(t)
          print("[NOVA-MLOPS] job=%s text=%r compound=%+.3f" % (job, t, s["compound"]))
runcmd:
  - [ bash, -lc, "set -euxo pipefail; python3 -m pip install --no-cache-dir -q vaderSentiment; python3 /tmp/nova_mlops_sentiment.py | tee /dev/ttyS0 /var/log/nova-mlops.log" ]
"""

