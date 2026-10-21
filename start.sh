#!/bin/sh
# Container entrypoint: prepare the database (extensions, tables, knowledge base), then serve.
# Hosting platforms (Render, Railway, Fly) set PORT; locally it defaults to 8000.
set -e
cd /app/backend
echo "Tambaya NG: preparing database..."
python -m scripts.init_db
echo "Tambaya NG: starting web server on port ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"
