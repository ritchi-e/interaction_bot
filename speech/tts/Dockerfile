FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 ca-certificates espeak-ng git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir "git+https://github.com/huggingface/parler-tts.git" \
    && pip install --no-cache-dir "TTS==0.22.0"

COPY cache.py text.py engine.py piper_engine.py parler_engine.py indic_tts_engine.py server.py ./
COPY voices ./voices

ENV MODELS_DIR=/models
ENV TTS_DEVICE=cuda
ENV TTS_NFE=16
ENV TTS_SKIP_F5=1
# Default Hindi path is Indic-TTS FastPitch; keep Parler off to free T4 VRAM.
ENV PARLER_DISABLED=1
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/models/hf-cache

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=300s --retries=12 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
