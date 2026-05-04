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

check_deployments

if [[ $# -lt 1 ]]; then
  echo "Usage: sbatch run_combo.slurm audio/file.mp3 [output.txt]" >&2
  exit 2
fi

audio="$(realpath "$1")"
output="${2:-outputs/$(basename "${audio%.*}").parallel.txt}"
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
}

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
)

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
source ./env.sh
pytorch_python scripts/build_parallel_subtitles.py \
  --dialect-json "$work_dir/dialect.json" \
  --standard-json "$work_dir/standard.json" \
  --output "$output" \
  --srt-output "$srt_output" \
  --debug-alignment "$SWISS_COMBO_DIR/outputs/${debug_stem}.alignment.tsv" \
  --translation-cache "$work_dir/translations.jsonl"
