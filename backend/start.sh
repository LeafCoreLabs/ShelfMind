#!/bin/sh
set -e
exec /app/entrypoint.sh gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b "0.0.0.0:${PORT:-8000}" -w 1 --timeout 120
