#!/bin/bash
set -e

# ─────────────────────────────────────────────
# Crear directorios necesarios en runtime
# (después de que los volúmenes ya están montados)
# ─────────────────────────────────────────────
mkdir -p /app/logs
mkdir -p /app/storage/logs
mkdir -p /app/storage/backups
mkdir -p /app/storage/certificates
mkdir -p /app/storage/invoices/xml
mkdir -p /app/storage/invoices/pdf
mkdir -p /app/staticfiles
mkdir -p /app/mediafiles
mkdir -p /app/certificates

# ─────────────────────────────────────────────
# Crear archivos de log si no existen
# ─────────────────────────────────────────────
touch /app/logs/celery.log
touch /app/storage/logs/vendo_sri.log
touch /app/storage/logs/celery_worker.log
touch /app/storage/logs/celery_beat.log
touch /app/storage/logs/gunicorn_access.log
touch /app/storage/logs/gunicorn_error.log
touch /app/storage/logs/sri_integration.log
touch /app/storage/logs/certificates.log

# ─────────────────────────────────────────────
# Ejecutar el comando original pasado al contenedor
# ─────────────────────────────────────────────
exec "$@"