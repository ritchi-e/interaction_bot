#!/bin/bash
# Load a TTS model and attach it to the app at http://tts:8091.
# Default is the same Voxtral model the calls use today.
#
#   ./start-tts.sh
#   TTS_MODEL=mistralai/Voxtral-4B-TTS-2603 ./start-tts.sh
#
# The model downloads into ${CALLER_DATA_ROOT:-/data/caller}/speech-models
# the first time. This script does not put the weights inside the app bundle.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p "${CALLER_DATA_ROOT:-/data/caller}/speech-models"
docker network create caller 2>/dev/null || true
docker compose --env-file caller.env -f compose.tts.yml up -d
echo "Voice container is starting. First load can take several minutes."
echo "The app is already pointed at http://tts:8091."
