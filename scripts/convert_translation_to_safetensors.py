#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

from transformers import AutoModelForSeq2SeqLM


def main() -> None:
    model_dir = Path(os.environ["TRANSLATION_MODEL_DIR"]).resolve()
    safe_path = model_dir / "model.safetensors"
    model = AutoModelForSeq2SeqLM.from_pretrained(str(model_dir), local_files_only=True)
    model.save_pretrained(str(model_dir), safe_serialization=True)
    print(f"Wrote {safe_path}")


if __name__ == "__main__":
    main()
