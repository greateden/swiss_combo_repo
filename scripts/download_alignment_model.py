#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import os
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from huggingface_hub import hf_hub_download, list_repo_files


MODEL_ALLOW_PATTERNS = [
    "*.json",
    "*.txt",
    "*.safetensors",
    "pytorch_model.bin",
    "vocab.txt",
]

REQUIRED_MODEL_FILES = [
    "config.json",
    "vocab.txt",
]

UNUSED_MODEL_FILES = [
    "tf_model.h5",
    "rust_model.ot",
    "flax_model.msgpack",
]


def wanted_file(path: str) -> bool:
    if any(fnmatch.fnmatch(path, pattern) for pattern in UNUSED_MODEL_FILES):
        return False
    return any(fnmatch.fnmatch(path, pattern) for pattern in MODEL_ALLOW_PATTERNS)


def main() -> None:
    repo_id = os.environ.get("ALIGNMENT_MODEL_ID", "bert-base-multilingual-cased")
    local_dir = Path(os.environ["ALIGNMENT_MODEL_DIR"]).resolve()
    local_dir.mkdir(parents=True, exist_ok=True)

    files = [path for path in list_repo_files(repo_id) if wanted_file(path)]
    for required_file in REQUIRED_MODEL_FILES:
        if required_file not in files:
            raise RuntimeError(f"{repo_id} does not contain required file {required_file}")

    for filename in files:
        print(f"Downloading {filename} ...", flush=True)
        hf_hub_download(repo_id=repo_id, filename=filename, local_dir=str(local_dir))

    for name in UNUSED_MODEL_FILES:
        path = local_dir / name
        if path.exists():
            path.unlink()
            print(f"Removed unused model file {path}")

    print(f"Alignment model ready at {local_dir}")


if __name__ == "__main__":
    main()
