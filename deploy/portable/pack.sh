#!/bin/bash
# Snapshot the running app (not the TTS weights) into /data/caller/portable.
# Copy that folder to the new GPU machine and run ./start.sh, then ./start-tts.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${PORTABLE_OUT:-/data/caller/portable}"
mkdir -p "$OUT"

echo "Saving the running app containers, without the voice model."
docker commit caller-backend-1 caller-portable:backend >/dev/null
docker commit caller-celery-1 caller-portable:celery >/dev/null
docker commit caller-celery-beat-1 caller-portable:beat >/dev/null
docker commit caller-context-guard-1 caller-portable:guard >/dev/null
docker commit caller-frontend-1 caller-portable:frontend >/dev/null
docker cp "$ROOT/speech/voxtral_proxy/server.py" caller-speech-tts-1:/app/server.py
docker commit caller-speech-tts-1 caller-portable:speech >/dev/null

echo "Writing the image archive."
docker save -o "$OUT/images-app.tar" \
  caller-portable:backend \
  caller-portable:celery \
  caller-portable:beat \
  caller-portable:guard \
  caller-portable:speech \
  caller-portable:frontend \
  postgres:16-alpine \
  redis:7-alpine \
  caddy:2 \
  dograhai/dograh-api:latest \
  dograhai/dograh-ui:latest \
  pgvector/pgvector:pg17 \
  redis:7 \
  bitnamilegacy/minio:latest

echo "Dumping the two databases."
docker exec caller-postgres-1 pg_dump -U caller --no-owner --no-acl caller | gzip -c > "$OUT/caller.sql.gz"
docker exec dograh-postgres-1 pg_dump -U postgres --no-owner --no-acl postgres | gzip -c > "$OUT/dograh.sql.gz"

cp "$ROOT/.env" "$OUT/caller.env"
cp "$ROOT/dograh/.env" "$OUT/dograh.env"
cp "$ROOT/deploy/Caddyfile" "$OUT/Caddyfile"
cp "$ROOT/deploy/voxtral_tts.l4.yaml" "$OUT/voxtral_tts.l4.yaml"
cp "$ROOT/deploy/portable/compose.app.yml" "$OUT/compose.app.yml"
cp "$ROOT/deploy/portable/compose.tts.yml" "$OUT/compose.tts.yml"
cp "$ROOT/deploy/portable/compose.dograh-data.yml" "$OUT/compose.dograh-data.yml"
cp "$ROOT/deploy/portable/start.sh" "$OUT/start.sh"
cp "$ROOT/deploy/portable/start-tts.sh" "$OUT/start-tts.sh"
cp "$ROOT/deploy/dograh.override.yml" "$OUT/dograh.override.yml"
cp "$ROOT/deploy/dograh.minio.yml" "$OUT/dograh.minio.yml"
mkdir -p "$OUT/overrides" "$OUT/dograh"
cp "$ROOT/deploy/dograh-overrides/check_validity.py" "$OUT/overrides/check_validity.py"
cp "$ROOT/deploy/dograh-overrides/service_factory.py" "$OUT/overrides/service_factory.py"
# Dograh's own compose is required to start its api the same way.
cp "$ROOT/dograh/docker-compose.yaml" "$OUT/dograh/docker-compose.yaml"
chmod 700 "$OUT/caller.env" "$OUT/dograh.env"
chmod 755 "$OUT/start.sh" "$OUT/start-tts.sh"

echo "Bundle is ready at $OUT"
du -sh "$OUT" "$OUT/images-app.tar" "$OUT/caller.sql.gz" "$OUT/dograh.sql.gz"
