#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source ./env.sh

if [[ $# -lt 1 ]]; then
  echo "Usage: bash submit_combo.sh path/to/audio.mp3 [path/to/output.txt]" >&2
  exit 2
fi

audio="$1"
output="${2:-outputs/$(basename "${audio%.*}").parallel.txt}"
time_limit="${TIME:-04:00:00}"
memory="${MEM:-120G}"
cpus="${CPUS:-4}"

check_deployments

sbatch_args=()
if [[ -n "${PARTITION:-}" ]]; then
  sbatch_args+=(--partition="$PARTITION")
  if [[ -n "${NODELIST:-}" ]]; then
    sbatch_args+=(--nodelist="$NODELIST")
  fi
else
  if selection="$(python3 scripts/select_gpu_node.py --mem "$memory" --cpus "$cpus" --format sbatch 2>/dev/null)"; then
    read -r -a selected_args <<< "$selection"
    sbatch_args+=("${selected_args[@]}")
    echo "[INFO] Selected ${selection}"
  else
    sbatch_args+=(--partition=aoraki_gpu)
    echo "[WARN] No immediate unrestricted GPU node found; submitting to aoraki_gpu without --nodelist." >&2
  fi
fi

sbatch \
  "${sbatch_args[@]}" \
  --time="$time_limit" \
  --mem="$memory" \
  --cpus-per-task="$cpus" \
  run_combo.slurm "$audio" "$output"
