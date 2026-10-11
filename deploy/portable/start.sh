#!/bin/bash
# On the rented GPU machine, from this folder:
#   ./start.sh
#   ./start-tts.sh
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f images-app.tar ]]; then
  echo "images-app.tar is missing. Run pack.sh on the current machine first." >&2
  exit 1
fi

echo "Loading the app images."
docker load -i images-app.tar
docker network create caller 2>/dev/null || true

# Bind mounts in the override are written for the repo. Point them at this folder.
python3 - << 'PY'
from pathlib import Path
path = Path("dograh.override.yml")
text = path.read_text()
text = text.replace("../deploy/dograh-overrides/", "./overrides/")
path.write_text(text)
PY

echo "Starting the app. The voice model is not started yet."
docker compose --env-file caller.env -f compose.app.yml up -d

echo "Starting Dograh on the same network."
docker compose --env-file dograh.env \
  -f dograh/docker-compose.yaml \
  -f dograh.override.yml \
  -f dograh.minio.yml \
  -f compose.dograh-data.yml \
  up -d

# First boot only: the dump is applied by Postgres when the volume is empty.
# If this folder is reused and the database is already full, the dump is skipped.
echo "App is up. Load a voice model next: ./start-tts.sh"
echo "Calls stay silent until that container is healthy."
