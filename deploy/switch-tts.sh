#!/usr/bin/env bash
# Point the live stack at Maya 2 Native TTS (default), or optionally Svara.
# Usage:  ./deploy/switch-tts.sh [maya|svara]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY="$ROOT/deploy"
MAYA_DIR="$ROOT/maya2-native"
ENV_FILE="$ROOT/.env"
TARGET="${1:-maya}"

if [[ "$TARGET" != "maya" && "$TARGET" != "svara" ]]; then
  echo "Usage: $0 [maya|svara]" >&2
  exit 2
fi

caller_up() {
  local overlay="$1"
  docker compose -p caller --env-file "$ENV_FILE" \
    -f "$DEPLOY/docker-compose.yml" \
    -f "$DEPLOY/docker-compose.data.yml" \
    -f "$overlay" \
    up -d backend celery celery-beat context-guard
}

set_env_tts_url() {
  local url="$1"
  if grep -q '^SPEECH_TTS_URL=' "$ENV_FILE"; then
    sed -i "s|^SPEECH_TTS_URL=.*|SPEECH_TTS_URL=$url|" "$ENV_FILE"
  else
    echo "SPEECH_TTS_URL=$url" >>"$ENV_FILE"
  fi
}

patch_dograh_tts_url() {
  local url="$1"
  # Legacy V2 blob (kept for bootstrap / older readers).
  docker exec dograh-postgres-1 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "
UPDATE organization_configurations
SET value = jsonb_set(value::jsonb, '{byok,pipeline,tts,base_url}', to_jsonb('$url'::text), true),
    updated_at = NOW()
WHERE key = 'MODEL_CONFIGURATION_V2';
"
  # Live Dograh v3 catalog: TTS provider_connection base_url. Without this,
  # calls keep dialing the previous engine (e.g. stopped Svara) and the phone
  # stays silent even though SPEECH_TTS_URL / V2 already point at the new one.
  docker exec dograh-postgres-1 psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c "
UPDATE provider_connections pc
SET connection_settings = jsonb_set(
      COALESCE(pc.connection_settings::jsonb, '{}'::jsonb),
      '{base_url}',
      to_jsonb('$url'::text),
      true
    ),
    updated_at = NOW()
FROM model_configurations mc
WHERE mc.organization_id = pc.organization_id
  AND mc.is_active = true
  AND (mc.configuration->'tts'->>'provider_connection_uuid') = pc.uuid
  AND pc.provider = 'openai';
"
}

if [[ "$TARGET" == "maya" ]]; then
  echo "==> Stopping Svara to free the GPU"
  docker stop svara-tts-api 2>/dev/null || true

  if [[ ! -x "$MAYA_DIR/runtime/venv/bin/python" ]]; then
    echo "==> Installing Maya 2 Native into $MAYA_DIR/runtime (on /data)"
    "$MAYA_DIR/install-venv.sh"
  fi

  echo "==> Building/starting Maya 2 Native + proxy"
  docker compose -p maya --env-file "$ENV_FILE" -f "$MAYA_DIR/docker-compose.yml" up -d --build

  echo "==> Waiting for Maya /health (first boot downloads weights)"
  for i in $(seq 1 90); do
    if docker exec maya-tts-api curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then
      echo "Maya ready after ${i}0s-ish"
      break
    fi
    if [[ $i -eq 90 ]]; then
      echo "Maya did not become healthy in time; check: docker logs maya-tts-api" >&2
      exit 1
    fi
    sleep 10
  done

  set_env_tts_url "http://maya-tts-proxy:8080/v1"
  patch_dograh_tts_url "http://maya-tts-proxy:8080/v1"
  caller_up "$DEPLOY/maya.host.yml"
  echo "==> TTS is now Maya 2 Native (presets via maya-tts-proxy). Svara is stopped."
else
  echo "==> Stopping Maya stack"
  docker compose -p maya -f "$MAYA_DIR/docker-compose.yml" stop || true

  echo "==> Starting Svara"
  docker start svara-tts-api

  echo "==> Waiting for Svara /health"
  for i in $(seq 1 60); do
    if docker exec svara-tts-api curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then
      echo "Svara ready"
      break
    fi
    sleep 10
  done

  set_env_tts_url "http://svara-tts-api:8080/v1"
  patch_dograh_tts_url "http://svara-tts-api:8080/v1"
  caller_up "$DEPLOY/svara.host.yml"
  echo "==> TTS is back on Svara. Maya containers are stopped."
fi
