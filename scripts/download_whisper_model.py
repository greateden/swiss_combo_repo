#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import os

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from huggingface_hub import hf_hub_download, list_repo_files


ALLOW_PATTERNS = [
    "*.json",
    "*.txt",
    "*.model",
    "*.safetensors",
    "*.safetensors.index.json",
    "pytorch_model.bin",
    "preprocessor_config.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "normalizer.json",
]

IGNORE_PATTERNS = [
    "*.h5",
    "*.msgpack",
    "*.onnx",
    "*.tflite",
    "*.gguf",
    "*.ot",
    "tf_model*",
    "flax_model*",
]


def wanted_file(path: str) -> bool:
    if any(fnmatch.fnmatch(path, pattern) for pattern in IGNORE_PATTERNS):
        return False
    return any(fnmatch.fnmatch(path, pattern) for pattern in ALLOW_PATTERNS)


def main() -> None:
    repo_id = os.environ["MODEL_ID"]
    files = [path for path in list_repo_files(repo_id) if wanted_file(path)]
    if not files:
        raise RuntimeError(f"No downloadable Transformers files found for {repo_id}")
    print(f"Downloading Whisper model files for {repo_id}")
    for filename in files:
        print(f"Downloading {filename} ...", flush=True)
        hf_hub_download(repo_id=repo_id, filename=filename)
    print(f"Whisper model ready: {repo_id}")


if __name__ == "__main__":
    main()
