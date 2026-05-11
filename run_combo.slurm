#!/bin/bash
#SBATCH --job-name=swiss-combo
#SBATCH --partition=aoraki_gpu
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=120G
#SBATCH --time=04:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:-$(dirname "$0")}"
source ./env.sh

if command -v module >/dev/null 2>&1; then
  module load apptainer/pytorch/24.04
fi

if ! command -v pytorch_exec >/dev/null 2>&1; then
  echo "[ERROR] pytorch_exec was not found. Load apptainer/pytorch/24.04 on Aoraki." >&2
  exit 1
fi

standard_german=0
word_by_word=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --standard-german)
      standard_german=1
      shift
      ;;
    --word-by-word)
      word_by_word=1
      shift
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if [[ "$standard_german" == "1" ]]; then
  check_standard_deployment
else
  check_deployments
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: sbatch run_combo.slurm [--standard-german] [--word-by-word] audio/file.mp3 [output.txt|output.json]" >&2
  exit 2
fi

audio="$(realpath "$1")"
if [[ $# -ge 2 ]]; then
  output="$2"
else
  suffix="parallel"
  extension="txt"
  if [[ "$standard_german" == "1" ]]; then
    suffix="standard"
  fi
  if [[ "$word_by_word" == "1" ]]; then
    suffix="$suffix.wordlinks"
    extension="json"
  fi
  output="outputs/$(basename "${audio%.*}").$suffix.$extension"
fi
stem="$(basename "${audio%.*}")"
output_base="$(basename "${output%.*}")"
debug_stem="${output_base%.parallel}"
srt_output="${output%.*}.srt"
work_dir="$SWISS_COMBO_DIR/work/$stem"
mkdir -p "$work_dir"

export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"

nvidia-smi || true

pytorch_python() {
  pytorch_exec env \
    PATH="$SWISS_COMBO_DIR/python_packages/bin:$SWISS_COMBO_DIR/python_packages/imageio_ffmpeg/binaries:${PATH:-}" \
    python3 "$@"
}

clear_model_env() {
  unset MODEL_ID
  unset MODEL_DIR
  unset PYTHON_PACKAGES_DIR
  unset PYTHONPATH
  unset PYTHONUSERBASE
  unset HF_HOME
  unset HF_HUB_CACHE
  unset TRANSFORMERS_CACHE
  unset HF_DATASETS_CACHE
  unset XDG_CACHE_HOME
  unset PIP_CACHE_DIR
  unset MPLCONFIGDIR
  unset SWISS_GERMAN_DIR
  unset SWISS_GERMAN_SWISS_DIR
  unset SWISS_COMBO_DIR
  unset TRANSLATION_MODEL_ID
  unset TRANSLATION_MODEL_DIR
  unset SWISS_TO_STANDARD_MODEL_ID
  unset SWISS_TO_STANDARD_MODEL_DIR
  unset ALIGNMENT_MODEL_ID
  unset ALIGNMENT_MODEL_DIR
}

if [[ "$standard_german" != "1" ]]; then
  (
    cd "$DIALECT_DIR"
    clear_model_env
    source ./env.sh
    if [[ "${FORCE:-0}" != "1" && -s "$work_dir/dialect.json" && -s "$work_dir/dialect.txt" ]]; then
      echo "[INFO] Reusing existing dialect transcript: $work_dir/dialect.json"
    else
      pytorch_python scripts/transcribe.py "$audio" \
        --output "$work_dir/dialect.txt" \
        --json "$work_dir/dialect.json" \
        --timestamps chunk \
        --batch-size "${BATCH_SIZE:-8}"
    fi
    if [[ "$word_by_word" == "1" ]]; then
      if [[ "${FORCE:-0}" != "1" && -s "$work_dir/dialect.words.json" && -s "$work_dir/dialect.words.txt" ]]; then
        echo "[INFO] Reusing existing dialect word transcript: $work_dir/dialect.words.json"
      else
        pytorch_python scripts/transcribe.py "$audio" \
          --output "$work_dir/dialect.words.txt" \
          --json "$work_dir/dialect.words.json" \
          --timestamps word \
          --batch-size "${BATCH_SIZE:-8}"
      fi
    fi
  )
fi

(
  cd "$STANDARD_DIR"
  clear_model_env
  source ./env.sh
  if [[ "${FORCE:-0}" != "1" && -s "$work_dir/standard.json" && -s "$work_dir/standard.txt" ]]; then
    echo "[INFO] Reusing existing standard transcript: $work_dir/standard.json"
  else
    pytorch_python scripts/transcribe.py "$audio" \
      --output "$work_dir/standard.txt" \
      --json "$work_dir/standard.json" \
      --timestamps chunk \
      --batch-size "${BATCH_SIZE:-8}"
  fi
  if [[ "$word_by_word" == "1" ]]; then
    if [[ "${FORCE:-0}" != "1" && -s "$work_dir/standard.words.json" && -s "$work_dir/standard.words.txt" ]]; then
      echo "[INFO] Reusing existing standard word transcript: $work_dir/standard.words.json"
    else
      pytorch_python scripts/transcribe.py "$audio" \
        --output "$work_dir/standard.words.txt" \
        --json "$work_dir/standard.words.json" \
        --timestamps word \
        --batch-size "${BATCH_SIZE:-8}"
    fi
  fi
)

cd "$SWISS_COMBO_DIR"
unset PYTHON_PACKAGES_DIR
unset PYTHONPATH
unset PYTHONUSERBASE
unset HF_HOME
unset HF_HUB_CACHE
unset TRANSFORMERS_CACHE
unset HF_DATASETS_CACHE
unset XDG_CACHE_HOME
unset PIP_CACHE_DIR
unset MPLCONFIGDIR
unset TRANSLATION_MODEL_ID
unset TRANSLATION_MODEL_DIR
unset SWISS_TO_STANDARD_MODEL_ID
unset SWISS_TO_STANDARD_MODEL_DIR
unset ALIGNMENT_MODEL_ID
unset ALIGNMENT_MODEL_DIR
source ./env.sh
pbuild_args=(
  scripts/build_parallel_subtitles.py
  --standard-json "$work_dir/standard.json" \
  --output "$output" \
  --srt-output "$srt_output" \
  --debug-alignment "$SWISS_COMBO_DIR/outputs/${debug_stem}.alignment.tsv" \
  --translation-cache "$work_dir/translations.jsonl"
)
if [[ "$standard_german" == "1" ]]; then
  pbuild_args+=(--standard-german)
else
  pbuild_args+=(--dialect-json "$work_dir/dialect.json")
fi
if [[ "$word_by_word" == "1" ]]; then
  pbuild_args+=(--word-by-word)
  pbuild_args+=(--standard-words-json "$work_dir/standard.words.json")
  if [[ "$standard_german" != "1" ]]; then
    pbuild_args+=(--dialect-words-json "$work_dir/dialect.words.json")
  fi
fi
pytorch_python "${pbuild_args[@]}"
