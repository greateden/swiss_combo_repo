#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import snapshot_download


def main() -> None:
    repo_id = os.environ.get("TRANSLATION_MODEL_ID", "Helsinki-NLP/opus-mt-de-en")
    local_dir = Path(os.environ["TRANSLATION_MODEL_DIR"]).resolve()
    local_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=repo_id, local_dir=str(local_dir))
    print(f"Translation model ready at {local_dir}")


if __name__ == "__main__":
    main()
