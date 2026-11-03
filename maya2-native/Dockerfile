# Thin CUDA runtime. The maya3 venv lives on /data (mounted at /opt/maya2)
# so root disk is not filled with another 20–40GB image layer.
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/root/.cache/huggingface \
    PATH=/opt/maya2/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3.11 python3.11-venv python3.11-dev python3-pip git curl ca-certificates \
      build-essential g++ \
      libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python

WORKDIR /opt/maya2
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=420s --retries=20 \
  CMD curl -fsS http://127.0.0.1:8080/health || exit 1

CMD ["python", "-m", "maya3.server", \
     "--ckpt", "maya-research/maya2-native", \
     "--host", "0.0.0.0", "--port", "8080", \
     "--max-seats", "4"]
