#!/bin/bash
# Bring the caller stack back after a reboot.
#
# Starts the containers that are already on this machine. It does not rebuild
# images and does not recreate containers, so files copied into a running
# container stay in place.
#
# Installed as a boot service by:
#   sudo cp deploy/caller-stack.service /etc/systemd/system/
#   sudo systemctl daemon-reload
#   sudo systemctl enable --now caller-stack.service

set -u

log() {
  echo "$(date -Is) $*"
}

wait_for() {
  local label="$1"
  local tries="$2"
  local pause="$3"
  shift 3
  local i
  for i in $(seq 1 "$tries"); do
    if "$@" >/dev/null 2>&1; then
      log "$label is ready"
      return 0
    fi
    sleep "$pause"
  done
  log "$label was not ready after $((tries * pause))s; continuing"
  return 1
}

missing=0

start_one() {
  local name="$1"
  if ! docker inspect "$name" >/dev/null 2>&1; then
    log "missing container $name"
    missing=1
    return
  fi
  docker update --restart unless-stopped "$name" >/dev/null
  if docker start "$name" >/dev/null; then
    log "started $name"
  else
    log "failed to start $name"
    missing=1
  fi
}

# Keep the previous TTS engine off the GPU so Maya can load.
stop_one() {
  local name="$1"
  if ! docker inspect "$name" >/dev/null 2>&1; then
    return
  fi
  docker update --restart no "$name" >/dev/null 2>&1 || true
  if docker stop "$name" >/dev/null 2>&1; then
    log "stopped $name (not used at boot)"
  fi
}

wait_for "docker" 60 2 docker info
wait_for "nvidia" 36 5 nvidia-smi || true

stop_one svara-tts-api

# Databases and object storage, then Maya TTS, then the app, then Dograh.
for name in \
  caller-postgres-1 \
  caller-redis-1 \
  dograh-postgres-1 \
  dograh-redis-1 \
  minio \
  maya-tts-api \
  maya-tts-proxy \
  caller-backend-1 \
  caller-celery-1 \
  caller-celery-beat-1 \
  caller-context-guard-1 \
  caller-frontend-1 \
  caller-caddy-1 \
  dograh-api \
  dograh-ui-1
do
  start_one "$name"
done

log "Maya keeps loading after its container starts; /health on maya-tts-api can take several minutes on cold boot"
exit "$missing"
