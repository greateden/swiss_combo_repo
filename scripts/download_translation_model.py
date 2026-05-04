#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

from huggingface_hub import hf_hub_download, list_repo_files


MODEL_ALLOW_PATTERNS = [
    "*.json",
    "*.spm",
    "*.txt",
    "pytorch_model.bin",
    "model.safetensors",
    "*.safetensors",
]

REQUIRED_MODEL_FILES = [
    "config.json",
    "pytorch_model.bin",
]

UNUSED_MODEL_FILES = [
    "tf_model.h5",
    "rust_model.ot",
    "flax_model.msgpack",
]


def other_download_processes() -> list[str]:
    try:
        result = subprocess.run(
            ["ps", "-u", str(os.getuid()), "-o", "pid=,cmd="],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    current_pid = os.getpid()
    matches: list[str] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pid_text, _, command = stripped.partition(" ")
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        if pid == current_pid:
            continue
        if "scripts/download_translation_model.py" in command:
            matches.append(stripped)
    return matches


def remove_unused_framework_weights(local_dir: Path) -> None:
    for name in UNUSED_MODEL_FILES:
        path = local_dir / name
        if path.exists():
            path.unlink()
            print(f"Removed unused model file {path}")


def wanted_file(path: str) -> bool:
    if any(fnmatch.fnmatch(path, pattern) for pattern in UNUSED_MODEL_FILES):
        return False
    return any(fnmatch.fnmatch(path, pattern) for pattern in MODEL_ALLOW_PATTERNS)


def download_file(repo_id: str, filename: str, local_dir: Path) -> None:
    print(f"Downloading {filename} ...", flush=True)
    hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=str(local_dir),
    )


def main() -> None:
    active_processes = other_download_processes()
    if active_processes:
        print(
            "Another translation model download is already running and may be holding Hugging Face locks:\n"
            + "\n".join(active_processes)
            + "\nStop that process before rerunning build.sh.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    repo_id = os.environ.get("TRANSLATION_MODEL_ID", "Helsinki-NLP/opus-mt-de-en")
    local_dir = Path(os.environ["TRANSLATION_MODEL_DIR"]).resolve()
    local_dir.mkdir(parents=True, exist_ok=True)

    files = [path for path in list_repo_files(repo_id) if wanted_file(path)]
    for required_file in REQUIRED_MODEL_FILES:
        if required_file not in files:
            raise RuntimeError(f"{repo_id} does not contain required file {required_file}")
    for filename in files:
        download_file(repo_id, filename, local_dir)

    remove_unused_framework_weights(local_dir)
    print(f"Translation model ready at {local_dir}")


if __name__ == "__main__":
    main()
