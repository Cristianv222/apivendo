# Usar imagen base oficial de Python
FROM python:3.1-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive



# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    # Dependencias básicas
    gcc \
    g++ \
    libc6-dev \
    # PostgreSQL
    libpq-dev \
    # SSL/TLS
    libssl-dev \
    libffi-dev \
    # Utilidades
    curl \
    wget \
    gnupg \
    # Limpieza de imagen
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Directorio de trabajo
WORKDIR /app

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --upgrade pip && 

# Copiar código de la aplicación
COPY . /app/

# Crear directorios necesarios con permisos correctos
RUN mkdir -p \
    /app/storage/logs \
    /app/storage/backups \
    /app/storage/certificates \
    /app/storage/invoices/xml \
    /app/storage/invoices/pdf \
    /app/staticfiles \
    /app/certificates

# Configurar permisos
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod -R 755 /app/storage/certificates && \
    chmod -R 755 /app/storage/logs
# Crear archivos de log iniciales
RUN touch /app/storage/logs/vendo_sri.log \
    /app/storage/logs/celery_worker.log \
    /app/storage/logs/celery_beat.log \
    /app/storage/logs/gunicorn_access.log \
    /app/storage/logs/gunicorn_error.log \
    /app/storage/logs/sri_integration.log \
    /app/storage/logs/certificates.log

# Configurar permisos de logs
RUN chown -R appuser:appuser /app/storage/logs && \
    chmod 644 /app/storage/logs/*.log

# Colectar archivos estáticos (se ejecuta también en docker-compose)
RUN python manage.py collectstatic --noinput --settings=vendo_sri.settings
