#!/bin/sh
set -e
WORKERS="${UVICORN_WORKERS:-2}"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${WORKERS}"
