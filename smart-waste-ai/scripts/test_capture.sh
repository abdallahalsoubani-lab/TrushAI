#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/frame.jpg [area_id] [track_id] [session_id]"
  exit 1
fi

FILE="$1"
AREA_ID="${2:-1}"
TRACK_ID="${3:-1}"
SESSION_ID="${4:-session_test}"

curl -sS -X POST "http://localhost:8000/api/v1/walkscan/capture" \
  -F "file=@${FILE}" \
  -F "area_id=${AREA_ID}" \
  -F "session_id=${SESSION_ID}" \
  -F "track_id=${TRACK_ID}" \
  -F "status=EMPTY" \
  -F "confidence=0.8" | python3 -m json.tool
