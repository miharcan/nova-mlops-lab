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

runcmd:
  - pip3 install -q transformers torch sentencepiece
  - |
    python3 - << 'EOF'
from transformers import pipeline

texts = [
    "I love this product.",
    "This is the worst experience I've had.",
    "The service was okay, nothing special."
]

clf = pipeline("sentiment-analysis")

for text, result in zip(texts, clf(texts)):
    print(
        "[NOVA-MLOPS] job={job} text=\\"{text}\\" label={label} score={score:.3f}".format(
            job="{job_name}",
            text=text,
            label=result["label"],
            score=result["score"],
        )
    )
EOF
"""
