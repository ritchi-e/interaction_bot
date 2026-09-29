#!/bin/sh
# Shallow-clone a pinned Dograh release into ./dograh (gitignored).
set -eu
ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
TAG="${DOGRAH_TAG:-dograh-v1.47.0}"
DEST="$ROOT/dograh"
if [ -d "$DEST/.git" ]; then
  echo "dograh already present at $DEST"
  exit 0
fi
git clone --depth 1 --branch "$TAG" https://github.com/dograh-hq/dograh.git "$DEST"
echo "Cloned $TAG"
