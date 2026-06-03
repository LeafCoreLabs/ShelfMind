#!/bin/sh
set -e

echo "Waiting for database..."
until python -c "
import os, sys
from sqlalchemy import create_engine, text
url = os.environ.get('DATABASE_URL_SYNC', '')
engine = create_engine(url)
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
print('Database ready')
" 2>/dev/null; do
  sleep 2
done

echo "Running migrations..."
alembic upgrade head

echo "Seeding demo data if needed..."
python -m app.seed

if [ "$EMBED_CELERY" = "true" ] || [ "$EMBED_CELERY" = "1" ]; then
  echo "Starting embedded Celery worker + beat (free-tier mode)..."
  celery -A app.celery_app worker -B -l info --concurrency=1 &
fi

exec "$@"
