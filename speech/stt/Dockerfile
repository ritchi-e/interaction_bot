FROM nvidia/cuda:12.9.2-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
# Needs the "-cudnn-" base image (not plain "-runtime-"): both onnxruntime-gpu
# (used for the smart-turn classifier) and sherpa-onnx's own bundled
# onnxruntime (used for the main ASR model) link against libcudnn.so.9 and
# silently fall back to CPU execution if it's missing -- there is no hard
# crash, just a warning buried in the logs, so this is easy to miss.
# Also needs CUDA 12.6+ specifically: the GPU sherpa-onnx wheel below bundles
# onnxruntime 1.28.2, whose CUDA execution provider references
# cudaLibraryGetKernel, a runtime symbol not present in libcudart.so.12 from
# CUDA 12.4.1 (what this image used to pin) -- it fails with "undefined
# symbol" at load time, not at pip-install time, so pin a current CUDA.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv ca-certificates \
    libasound2 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

WORKDIR /app
COPY requirements.txt .
# IMPORTANT: plain `pip install sherpa-onnx` from PyPI pulls a CPU-only wheel
# (it logs "Please compile with -DSHERPA_ONNX_ENABLE_GPU=ON" and silently
# falls back to CPU). The CUDA-enabled wheels are only published via k2-fsa's
# own wheel index, keyed by CUDA/cuDNN version -- must match the cuDNN
# installed above (cuda12.cudnn9) and the interpreter (cp310 / Python 3.10).
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
         "sherpa-onnx==1.13.8+cuda12.cudnn9.onnxruntime1.28.2" \
         -f https://k2-fsa.github.io/sherpa/onnx/cuda.html

COPY asr.py turns.py server.py ./

ENV MODELS_DIR=/models
ENV SHERPA_PROVIDER=cuda
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--ws", "websockets"]
