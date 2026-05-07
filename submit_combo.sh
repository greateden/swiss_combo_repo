#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source ./env.sh

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

if [[ $# -lt 1 ]]; then
  echo "Usage: bash submit_combo.sh [--standard-german] [--word-by-word] path/to/audio.mp3 [path/to/output.txt|output.json]" >&2
  exit 2
fi

audio="$1"
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
time_limit="${TIME:-04:00:00}"
memory="${MEM:-120G}"
cpus="${CPUS:-4}"
gpu_wait_seconds="${GPU_WAIT_SECONDS:-60}"

if [[ "$standard_german" == "1" ]]; then
  check_standard_deployment
else
  check_deployments
fi

mode_args=()
if [[ "$standard_german" == "1" ]]; then
  mode_args+=(--standard-german)
fi
if [[ "$word_by_word" == "1" ]]; then
  mode_args+=(--word-by-word)
fi

sbatch_args=()
if [[ -n "${PARTITION:-}" ]]; then
  sbatch_args+=(--partition="$PARTITION")
  if [[ -n "${NODELIST:-}" ]]; then
    sbatch_args+=(--nodelist="$NODELIST")
  fi
else
  attempt=1
  while true; do
    if selection="$(python3 scripts/select_gpu_node.py --mem "$memory" --cpus "$cpus" --format sbatch 2>/dev/null)"; then
      read -r -a selected_args <<< "$selection"
      sbatch_args+=("${selected_args[@]}")
      echo "[INFO] Selected ${selection}"
      break
    fi

    echo "[INFO] No unrestricted GPU node currently satisfies CPU_MEM=${memory} CPUS=${cpus}; waiting ${gpu_wait_seconds}s before retry ${attempt}." >&2
    sleep "$gpu_wait_seconds"
    attempt=$((attempt + 1))
  done
fi

sbatch \
  "${sbatch_args[@]}" \
  --time="$time_limit" \
  --mem="$memory" \
  --cpus-per-task="$cpus" \
  run_combo.slurm "${mode_args[@]}" "$audio" "$output"
