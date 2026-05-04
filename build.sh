#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
source ./env.sh

if command -v module >/dev/null 2>&1; then
  module load apptainer/pytorch/24.04
fi

bash scripts/setup_whisper_deployments.sh

python_runner=(python3)
if command -v pytorch_exec >/dev/null 2>&1; then
  python_runner=(pytorch_exec python3)
else
  echo "[WARN] pytorch_exec not found; using python3 from the current environment." >&2
  echo "[WARN] On Aoraki, run from a shell where apptainer/pytorch/24.04 is available." >&2
fi

"${python_runner[@]}" -m pip install \
  --upgrade \
  --target "$PYTHON_PACKAGES_DIR" \
  --cache-dir "$PIP_CACHE_DIR" \
  -r requirements.txt

ffmpeg_exe="$("${python_runner[@]}" - <<'PY'
import imageio_ffmpeg

print(imageio_ffmpeg.get_ffmpeg_exe())
PY
)"
mkdir -p "$PYTHON_PACKAGES_DIR/bin"
ln -sf "$ffmpeg_exe" "$PYTHON_PACKAGES_DIR/bin/ffmpeg"
"$PYTHON_PACKAGES_DIR/bin/ffmpeg" -version | sed -n '1p'

(
  cd "$DIALECT_DIR"
  source ./env.sh
  "${python_runner[@]}" "$SWISS_COMBO_DIR/scripts/download_whisper_model.py"
)

(
  cd "$STANDARD_DIR"
  source ./env.sh
  "${python_runner[@]}" "$SWISS_COMBO_DIR/scripts/download_whisper_model.py"
)

"${python_runner[@]}" scripts/download_translation_model.py
"${python_runner[@]}" scripts/convert_translation_to_safetensors.py

echo "Build complete."
echo "Swiss German Whisper deployment: $DIALECT_DIR"
echo "Standard German Whisper deployment: $STANDARD_DIR"
echo "Translation model: $TRANSLATION_MODEL_DIR"
echo "Python packages: $PYTHON_PACKAGES_DIR"
