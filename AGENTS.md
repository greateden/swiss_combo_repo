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
- Use `bash build.sh` to install dependencies, create the default Whisper deployments, download the Whisper models, and download the translation model.
- Default Whisper roles: `DIALECT_DIR` is Swiss German speech to Swiss German-style text, and `STANDARD_DIR` is Swiss German speech to Standard German text. Do not replace `STANDARD_DIR` with a generic German ASR model unless the user explicitly asks for that tradeoff.
- Use `bash submit_combo.sh <audio.mp3> [output.txt]` for normal jobs.
- Do not run full Whisper transcription or full translation jobs directly on the login node.
- Let `submit_combo.sh` choose a GPU node, or set `PARTITION`/`NODELIST` explicitly when needed.
- Check `squeue -u "$USER"` and `logs/` while jobs are running.
- If a run fails with missing `DIALECT_DIR` or `STANDARD_DIR`, run `bash build.sh` first. If custom deployments are needed, locate them with `find /projects/sciences/computing/$USER -type f -path '*/scripts/transcribe.py' -printf '%h\n'`, then rerun with absolute `DIALECT_DIR=/path/to/dialect` and `STANDARD_DIR=/path/to/standard` values. The deployment directories must contain both `env.sh` and `scripts/transcribe.py`.

## Pipeline Notes

- Existing `work/<audio>/dialect.json` and `standard.json` are reused unless `FORCE=1` is set.
- The final builder uses content-based alignment; do not revert to timestamp-only alignment.
- Translation is resumable through `work/<audio>/translations.jsonl`.
