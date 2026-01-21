def training_cloud_init(job_name: str) -> str:
    return f"""#cloud-config
runcmd:
  - echo "[NOVA-MLOPS] job={job_name} step=setup"
  - sleep 2
  - echo "[NOVA-MLOPS] step=train epoch=1 loss=0.91"
  - sleep 2
  - echo "[NOVA-MLOPS] step=train epoch=2 loss=0.73"
  - sleep 2
  - echo "[NOVA-MLOPS] step=done"
"""
