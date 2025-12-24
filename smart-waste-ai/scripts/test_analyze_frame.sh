#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /path/to/frame.jpg"
  exit 1
fi

FILE="$1"

curl -sS -X POST "http://localhost:8000/api/v1/analyze-frame" \
  -F "file=@${FILE}" | python3 -m json.tool
