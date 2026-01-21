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
    # IMPORTANT: must be a plain *string* starting with "#cloud-config"
    return f"""#cloud-config
package_update: true
packages:
  - python3-pip

runcmd:
  - pip3 install -q vaderSentiment
  - |
      python3 - << 'EOF'
      from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

      job = "{job_name}"
      texts = [
          "I love this product.",
          "This is the worst experience I've had.",
          "The service was okay, nothing special.",
      ]

      a = SentimentIntensityAnalyzer()
      for t in texts:
          s = a.polarity_scores(t)
          print(f"[NOVA-MLOPS] job={job} text=\\"{t}\\" compound={s['compound']:+.3f}")
      EOF
"""
