# Agent Notes

Scope: this folder only.

## Rules

- Do not use `sudo`.
- Do not install into global Python or system paths.
- Source `./env.sh` before build, setup, or pipeline work.
- Keep caches, downloaded models, Python packages, logs, work files, audio, and outputs inside this folder.
- Do not commit generated/heavy folders: `models/`, `python_packages/`, `swiss-german-swiss/`, `swiss_german/`, `.hf_home/`, `.cache/`, `work/`, `logs/`, `outputs/`, `tmp/`, or `audio/`.
- Use the local Whisper deployments through `DIALECT_DIR` and `STANDARD_DIR`; do not duplicate Whisper model weights in this repo.

## Aoraki Usage

- Use `module load apptainer/pytorch/24.04` and run Python through `pytorch_exec` when available.
- Use `bash build.sh` to install dependencies, create the default Whisper deployments, download the Whisper models, download the German-to-English translation model, download the Swiss-to-Standard fallback model, and download the multilingual word-alignment model.
- Default Whisper roles: `DIALECT_DIR` is Swiss German speech to Swiss German-style text, and `STANDARD_DIR` is Swiss German speech to Standard German text. Both generated deployments force Whisper language `de` to reduce English/other-language drift. Do not replace `STANDARD_DIR` with a generic German ASR model unless the user explicitly asks for that tradeoff.
- If a Swiss German row has dialect text but no Standard German text, the builder may fill only that missing Standard German line with `SWISS_TO_STANDARD_MODEL_DIR`. Never overwrite an existing Standard German sentence with fallback normalization.
- Use `bash submit_combo.sh <audio.mp3> [output.txt]` for normal subtitle jobs.
- Use `bash submit_combo.sh --word-by-word <audio.mp3> [output.json]` for source-anchored learning JSON. This mode writes wordlinks JSON only, not `.txt` or `.srt` subtitles.
- Use `bash submit_combo.sh --standard-german <audio.mp3>` when the input audio is already Standard German. Combine it with `--word-by-word` for Standard German to English wordlinks.
- Use `python3 subtitle_viewer.py <wordlinks.json>` to inspect wordlinks output locally. Optional audio playback in the viewer depends on `pygame`; without it, the viewer remains a JSON/timer display with manual offset controls. The viewer wordbook must use `source_id` alignment links, not repeated-string matching.
- Do not run full Whisper transcription or full translation jobs directly on the login node.
- Do not run Whisper, translation, or neural word-alignment inference on the login/root node. Always submit through SLURM, even for short audio clips.
- Let `submit_combo.sh` choose a GPU node, or set `PARTITION`/`NODELIST` explicitly when needed.
- Check `squeue -u "$USER"` and `logs/` while jobs are running.
- If a run fails with missing `DIALECT_DIR` or `STANDARD_DIR`, run `bash build.sh` first. If custom deployments are needed, locate them with `find /projects/sciences/computing/$USER -type f -path '*/scripts/transcribe.py' -printf '%h\n'`, then rerun with absolute `DIALECT_DIR=/path/to/dialect` and `STANDARD_DIR=/path/to/standard` values. The deployment directories must contain both `env.sh` and `scripts/transcribe.py`.

## Pipeline Notes

- Existing `work/<audio>/dialect.json` and `standard.json` are reused unless `FORCE=1` is set.
- Word-by-word jobs also reuse `work/<audio>/dialect.words.json` and `standard.words.json` unless `FORCE=1` is set.
- The final builder uses content-based alignment; do not revert to timestamp-only alignment.
- Translation is resumable through `work/<audio>/translations.jsonl`.
- Swiss-to-Standard fallback normalization is resumable through `work/<audio>/swiss_to_standard.jsonl`.
- Wordlink `source_id` values must always come from the original language line: Swiss German for normal mode, Standard German for `--standard-german`. Target-language extra words should remain unlinked with `source_id: null`.
- The wordlink builder may use bilingual hint rules plus the multilingual alignment model. Keep regression coverage in `scripts/test_wordlinks.py` when changing this behavior.
- When Whisper word timestamps are zero-length or inconsistent with the sentence text, the builder should estimate sane per-word timing inside the sentence span instead of clustering all words at the end.
- For the viewer wordbook, infer German gender only from local article context in the aligned Standard German sentence. Show `?` when the sentence does not prove a gender; do not add dictionary-based gender guesses.
