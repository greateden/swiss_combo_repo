# Swiss Combo Subtitles

Build parallel subtitle text from two local Whisper deployments:

- Swiss German-style transcript from `../swiss-german-swiss`
- Standard German transcript from `../swiss_german`
- English translation from `Helsinki-NLP/opus-mt-de-en`

Output blocks are:

```text
Swiss German sentence
Standard German sentence
English translation
```

## Build

On Aoraki:

```bash
cd swiss_combo_repo
bash build.sh
```

This installs Python packages into `python_packages/` and downloads the translation model into `models/`. Both paths are ignored by git.

The two Whisper deployments are expected as sibling folders. Override them if needed:

```bash
DIALECT_DIR=/path/to/swiss-german-swiss \
STANDARD_DIR=/path/to/swiss_german \
bash build.sh
```

## Run

```bash
bash submit_combo.sh path/to/audio.mp3 outputs/audio.parallel.txt
```

`submit_combo.sh` selects an available Aoraki GPU node when it can. You can override scheduling:

```bash
TIME=08:00:00 MEM=120G CPUS=4 PARTITION=aoraki_gpu_L40 bash submit_combo.sh path/to/audio.mp3
```

Intermediate transcripts, translation cache, logs, and outputs stay inside this folder. Existing `work/<audio>/dialect.json` and `standard.json` are reused unless `FORCE=1` is set.

## Important Files

- `build.sh`: install dependencies and download/convert the translation model.
- `submit_combo.sh`: normal SLURM submission entrypoint.
- `run_combo.slurm`: SLURM job body.
- `scripts/build_parallel_subtitles.py`: align Swiss/Standard text and translate with a resumable JSONL cache.
