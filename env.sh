#!/usr/bin/env bash
set -euo pipefail

export SWISS_COMBO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

resolve_dir() {
  local path="$1"
  if [[ -d "$path" ]]; then
    cd "$path" && pwd
  else
    printf '%s\n' "$path"
  fi
}

export DIALECT_DIR="${DIALECT_DIR:-$(resolve_dir "$SWISS_COMBO_DIR/swiss-german-swiss")}"
export STANDARD_DIR="${STANDARD_DIR:-$(resolve_dir "$SWISS_COMBO_DIR/swiss_german")}"

export TRANSLATION_MODEL_ID="${TRANSLATION_MODEL_ID:-Helsinki-NLP/opus-mt-de-en}"
export TRANSLATION_MODEL_DIR="${TRANSLATION_MODEL_DIR:-$SWISS_COMBO_DIR/models/Helsinki-NLP__opus-mt-de-en}"
export PYTHON_PACKAGES_DIR="${PYTHON_PACKAGES_DIR:-$SWISS_COMBO_DIR/python_packages}"

export HF_HOME="$SWISS_COMBO_DIR/.hf_home"
export HF_HUB_CACHE="$SWISS_COMBO_DIR/.hf_home/hub"
export TRANSFORMERS_CACHE="$SWISS_COMBO_DIR/.hf_home/transformers"
export HF_DATASETS_CACHE="$SWISS_COMBO_DIR/.hf_home/datasets"
export XDG_CACHE_HOME="$SWISS_COMBO_DIR/.cache"
export PIP_CACHE_DIR="$SWISS_COMBO_DIR/.cache/pip"
export MPLCONFIGDIR="$SWISS_COMBO_DIR/.cache/matplotlib"
export TMPDIR="$SWISS_COMBO_DIR/tmp"
export PYTHONUSERBASE="$SWISS_COMBO_DIR/.python_userbase"
export PYTHONNOUSERSITE=1
export HF_HUB_DISABLE_XET=1
export TOKENIZERS_PARALLELISM=false
export PYTHONPATH="$PYTHON_PACKAGES_DIR${PYTHONPATH:+:$PYTHONPATH}"

deployment_help() {
  local name="$1"
  local value="$2"
  local purpose="$3"
  cat >&2 <<EOF
[ERROR] $name does not exist: $value
[ERROR] Set $name to the $purpose Whisper deployment.
[ERROR] Expected deployment folders contain scripts/transcribe.py and env.sh.
[ERROR] If you are using the default deployments, run: bash build.sh
[ERROR] To locate candidates:
[ERROR]   find /projects/sciences/computing/$USER -type f -path '*/scripts/transcribe.py' -printf '%h\n'
[ERROR] Then rerun with absolute paths, for example:
[ERROR]   DIALECT_DIR=/path/to/swiss-dialect-whisper STANDARD_DIR=/path/to/standard-german-whisper bash submit_combo.sh audio/file.mp3 outputs/file.parallel.txt
EOF
}

check_deployments() {
  local failed=0
  if [[ ! -d "$DIALECT_DIR" || ! -f "$DIALECT_DIR/scripts/transcribe.py" || ! -f "$DIALECT_DIR/env.sh" ]]; then
    deployment_help "DIALECT_DIR" "$DIALECT_DIR" "Swiss German"
    failed=1
  fi
  if [[ ! -d "$STANDARD_DIR" || ! -f "$STANDARD_DIR/scripts/transcribe.py" || ! -f "$STANDARD_DIR/env.sh" ]]; then
    deployment_help "STANDARD_DIR" "$STANDARD_DIR" "Standard German"
    failed=1
  fi
  return "$failed"
}

mkdir -p \
  "$SWISS_COMBO_DIR"/{audio,logs,models,outputs,python_packages,scripts,tmp,work} \
  "$HF_HOME" "$HF_HUB_CACHE" "$TRANSFORMERS_CACHE" "$HF_DATASETS_CACHE" \
  "$XDG_CACHE_HOME" "$PIP_CACHE_DIR" "$MPLCONFIGDIR" "$TRANSLATION_MODEL_DIR"
