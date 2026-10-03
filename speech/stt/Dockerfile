FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "sherpa-onnx==1.12.14" || \
       pip install --no-cache-dir sherpa-onnx

COPY asr.py turns.py server.py ./

ENV MODELS_DIR=/models
ENV SHERPA_PROVIDER=cuda
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--ws", "websockets"]
