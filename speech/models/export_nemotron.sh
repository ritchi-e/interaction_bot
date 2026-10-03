#!/usr/bin/env bash
# Export a NeMo cache-aware streaming ASR checkpoint to sherpa-onnx layout.
# Usage: export_nemotron.sh <hf_or_local_model> <output_dir>
set -euo pipefail

MODEL="${1:?model id}"
OUT="${2:?output dir}"
CHUNK_MS="${CHUNK_MS:-560}"

mkdir -p "$OUT"

if ! python -c "import nemo.collections.asr" 2>/dev/null; then
  echo "NeMo not installed; cannot export $MODEL" >&2
  exit 1
fi

# Prefer an upstream sherpa export script if present in the image.
if [[ -n "${SHERPA_EXPORT_SCRIPT:-}" && -f "$SHERPA_EXPORT_SCRIPT" ]]; then
  python "$SHERPA_EXPORT_SCRIPT" \
    --model "$MODEL" \
    --output-dir "$OUT" \
    --chunk-ms "$CHUNK_MS"
  exit 0
fi

python - <<'PY' "$MODEL" "$OUT" "$CHUNK_MS"
import sys
from pathlib import Path

model_id, out_dir, chunk_ms = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3])
out_dir.mkdir(parents=True, exist_ok=True)

try:
    import nemo.collections.asr as nemo_asr
except ImportError as exc:
    raise SystemExit(f"NeMo missing: {exc}") from exc

print(f"loading {model_id}")
try:
    model = nemo_asr.models.ASRModel.from_pretrained(model_id)
except Exception:
    model = nemo_asr.models.ASRModel.restore_from(model_id)

model.eval()
# Best-effort ONNX export when the model exposes export().
export_fn = getattr(model, "export", None)
if export_fn is None:
    raise SystemExit("model has no export(); use sherpa fallback package")

onnx_path = out_dir / "model.onnx"
print(f"exporting onnx -> {onnx_path}")
export_fn(str(onnx_path))
print("export finished; you may still need to split encoder/decoder/joiner for sherpa")
PY
