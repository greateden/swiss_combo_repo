# Agent Notes

Scope: this folder only.

## Rules

- Do not use `sudo`.
- Do not install into global Python or system paths.
- Source `./env.sh` before build, setup, or pipeline work.
- Keep caches, downloaded models, Python packages, logs, work files, audio, and outputs inside this folder.
- Do not commit generated/heavy folders: `models/`, `python_packages/`, `.hf_home/`, `.cache/`, `work/`, `logs/`, `outputs/`, `tmp/`, or `audio/`.
- Use the local Whisper deployments through `DIALECT_DIR` and `STANDARD_DIR`; do not duplicate Whisper model weights in this repo.

## Aoraki Usage

- Use `module load apptainer/pytorch/24.04` and run Python through `pytorch_exec` when available.
- Use `bash build.sh` to install dependencies and download the translation model.
- Use `bash submit_combo.sh <audio.mp3> [output.txt]` for normal jobs.
- Do not run full Whisper transcription or full translation jobs directly on the login node.
- Let `submit_combo.sh` choose a GPU node, or set `PARTITION`/`NODELIST` explicitly when needed.
- Check `squeue -u "$USER"` and `logs/` while jobs are running.

## Pipeline Notes

- Existing `work/<audio>/dialect.json` and `standard.json` are reused unless `FORCE=1` is set.
- The final builder uses content-based alignment; do not revert to timestamp-only alignment.
- Translation is resumable through `work/<audio>/translations.jsonl`.
