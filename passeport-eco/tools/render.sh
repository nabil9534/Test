#!/usr/bin/env bash
# Rendu complet d'un épisode : page → MP4 muet → bande-son → MP4 final.
# Usage : tools/render.sh <slug> [voix.wav|mp3|m4a]
set -euo pipefail
cd "$(dirname "$0")/.."
slug=$1; voice=${2:-}
python3 builder.py "specs/$slug.json"
node tools/record.js "$slug"
python3 tools/soundtrack.py "$slug" $voice
mkdir -p videos
ffmpeg -loglevel error -y -i "build/$slug.silent.mp4" -i "build/$slug.wav" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "videos/$slug.mp4"
echo "→ videos/$slug.mp4"
