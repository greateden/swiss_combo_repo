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

The build also creates the default sibling Whisper deployments if they are missing:

- `../swiss-german-swiss`: Swiss German ASR, default model `Flurin17/whisper-large-v3-turbo-swiss-german`
- `../swiss_german`: Standard German ASR, default model `primeline/whisper-large-v3-turbo-german`

Those deployment folders and their Hugging Face caches stay outside this repo. Override them if needed:

```bash
DIALECT_DIR=/path/to/swiss-german-swiss \
STANDARD_DIR=/path/to/swiss_german \
bash build.sh
```

`DIALECT_DIR` and `STANDARD_DIR` must each point to a Whisper deployment containing `env.sh` and `scripts/transcribe.py`. If the defaults do not exist on Aoraki, run `bash build.sh` first. To locate existing deployments:

```bash
find /projects/sciences/computing/$USER -type f -path '*/scripts/transcribe.py' -printf '%h\n'
```

Then submit with absolute paths:

```bash
DIALECT_DIR=/path/to/swiss-dialect-whisper \
STANDARD_DIR=/path/to/standard-german-whisper \
bash submit_combo.sh audio/file.mp3 outputs/file.parallel.txt
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

## Bug Fixes

- The translation model downloader avoids the threaded Hugging Face snapshot path that can stall on Aoraki. It downloads only the required Transformers files, skips unused TensorFlow/Rust/Flax weights, disables Xet by default for this setup, and exits clearly if another downloader is already holding Hugging Face locks.
- Job submission now checks `DIALECT_DIR` and `STANDARD_DIR` before calling `sbatch`, so missing Whisper deployment paths fail immediately with debugging commands instead of producing a failed SLURM job.
- `build.sh` now creates and warms the default Whisper deployments, including the Swiss German Hugging Face ASR model and the Standard German ASR model.

## Important Files

- `build.sh`: install dependencies and download/convert the translation model.
- `submit_combo.sh`: normal SLURM submission entrypoint.
- `run_combo.slurm`: SLURM job body.
- `scripts/build_parallel_subtitles.py`: align Swiss/Standard text and translate with a resumable JSONL cache.
