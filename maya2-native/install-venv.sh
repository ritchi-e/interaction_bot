#!/usr/bin/env bash
# Install maya3 into /data/.../runtime/venv using a one-shot CUDA container.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
RUNTIME="$ROOT/runtime"
CACHE="$ROOT/hf-cache"
mkdir -p "$RUNTIME" "$CACHE"

echo "Installing maya3 venv into $RUNTIME (uses /data, not root docker layers)"
docker run --rm \
  -v "$RUNTIME:/opt/maya2" \
  -v "$CACHE:/root/.cache/huggingface" \
  -e HF_HOME=/root/.cache/huggingface \
  --env-file "$ROOT/../.env" \
  nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04 \
  bash -lc '
    set -euo pipefail
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y --no-install-recommends python3.11 python3.11-venv python3-pip git curl ca-certificates libsndfile1
    ln -sf /usr/bin/python3.11 /usr/bin/python
    if [[ ! -x /opt/maya2/venv/bin/python ]]; then
      python -m venv /opt/maya2/venv
    fi
    /opt/maya2/venv/bin/pip install --upgrade pip setuptools wheel
    /opt/maya2/venv/bin/pip install \
      "maya3[server] @ git+https://github.com/MayaResearch/maya2-native" \
      --extra-index-url https://download.pytorch.org/whl/cu128
    /opt/maya2/venv/bin/python -c "import maya3, torch; print(\"maya3 ok\", maya3.__file__, \"cuda\", torch.cuda.is_available())"
  '
# Host Triton JIT segfaults on driver 595 / CUDA 13.2 — force eager fallbacks.
docker run --rm \
  -v "$RUNTIME:/opt/maya2" \
  -v "$ROOT/patch_engine.py:/tmp/patch_engine.py:ro" \
  -v "$ROOT/patch_triton_fallback.py:/tmp/patch_triton_fallback.py:ro" \
  --entrypoint bash maya-tts-api:latest -lc \
  'python3 /tmp/patch_engine.py; python3 /tmp/patch_triton_fallback.py' || \
docker run --rm \
  -v "$RUNTIME:/opt/maya2" \
  -v "$ROOT/patch_engine.py:/tmp/patch_engine.py:ro" \
  -v "$ROOT/patch_triton_fallback.py:/tmp/patch_triton_fallback.py:ro" \
  --entrypoint bash nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04 -lc \
  'apt-get update >/dev/null && apt-get install -y -qq python3 >/dev/null && python3 /tmp/patch_engine.py && python3 /tmp/patch_triton_fallback.py'
echo "Install complete."
