# Imagen base oficial
FROM python:3.10-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libc6-dev \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    curl \
    wget \
    gnupg \
    libmagic-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Crear usuario no root
RUN useradd -ms /bin/bash appuser

# Establecer directorio de trabajo
WORKDIR /app

# Copiar primero requirements.txt para aprovechar el cache
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código de la aplicación
COPY . /app/

# Crear directorios necesarios (como respaldo, pero el entrypoint los garantiza en runtime)
RUN mkdir -p \
    /app/storage/logs \
    /app/storage/backups \
    /app/storage/certificates \
    /app/storage/invoices/xml \
    /app/storage/invoices/pdf \
    /app/staticfiles \
    /app/mediafiles \
    /app/certificates \
    /app/logs

# Crear archivos de logs vacíos
RUN touch /app/storage/logs/vendo_sri.log \
          /app/storage/logs/celery_worker.log \
          /app/storage/logs/celery_beat.log \
          /app/storage/logs/gunicorn_access.log \
          /app/storage/logs/gunicorn_error.log \
          /app/storage/logs/sri_integration.log \
          /app/storage/logs/certificates.log \
          /app/logs/celery.log

# Copiar entrypoint y dar permisos
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Dar permisos a los archivos y carpetas
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod -R 644 /app/storage/logs/*.log && \
    chmod 644 /app/logs/celery.log

# Cambiar a usuario no root
#USER appuser

# Entrypoint garantiza directorios en runtime (después de volúmenes)
ENTRYPOINT ["/app/entrypoint.sh"]
