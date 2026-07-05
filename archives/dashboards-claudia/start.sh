#!/bin/bash
# Claudia Dashboard startup script
VENV="${HERMES:-$HOME/.hermes}/hermes-agent/venv"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=7842
cd "$DIR"
echo "Checking dependencies..."
$VENV/bin/python -c "import googleapiclient" 2>/dev/null || $VENV/bin/python -m pip install --quiet google-api-python-client google-auth-oauthlib google-auth-httplib2
echo "Starting Claudia Dashboard on http://localhost:$PORT ..."
$VENV/bin/uvicorn server:app --host 0.0.0.0 --port $PORT
