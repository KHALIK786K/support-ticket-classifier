"""
CLI to train the model offline.

    python scripts/train_model.py --data data/raw/tickets.csv --model logreg

After successful training the artifact is saved to models/pipeline.pkl
(configurable via MODEL_PATH in .env).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running this script directly (without `python -m`)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.logging import configure_logging  # noqa: E402
from app.ml.train import train_model  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the ticket classifier")
    parser.add_argument("--data", type=Path, default=Path("data/raw/tickets.csv"))
    parser.add_argument("--model", choices=["logreg", "random_forest"], default="logreg")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    configure_logging("INFO")
    res = train_model(args.data, model_type=args.model, output_path=args.out)
    print(
        f"✓ Trained. test_f1={res['test_f1_macro']:.4f} "
        f"val_f1={res['val_f1_macro']:.4f} → {res['output_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
