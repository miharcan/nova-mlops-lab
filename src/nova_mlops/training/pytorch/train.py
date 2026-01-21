from __future__ import annotations
import argparse
from pathlib import Path
import json
import time

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch_size", type=int, default=128)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--output_dir", type=str, required=True)
    args = p.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Educational placeholder: keeps the project runnable even before torch install
    # When torch is installed, you’ll replace this with real MNIST training.
    metrics_path = out / "metrics.jsonl"
    start = time.time()
    with metrics_path.open("w") as f:
        for epoch in range(args.epochs):
            record = {
                "epoch": epoch,
                "loss": float(1.0 / (epoch + 1)),
                "acc": float(epoch) / max(args.epochs - 1, 1),
            }
            f.write(json.dumps(record) + "\n")

    (out / "model.pt").write_bytes(b"placeholder-model")
    (out / "run.json").write_text(json.dumps({"args": vars(args), "duration_s": time.time() - start}, indent=2))

if __name__ == "__main__":
    main()
