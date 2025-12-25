#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/frame.jpg [area_id]"
  exit 1
fi

FILE="$1"
AREA_ID="${2:-1}"

curl -sS -X POST "http://localhost:8000/api/v1/analyze-frame" \
  -F "file=@${FILE}" \
  -F "area_id=${AREA_ID}" | python3 -m json.tool
