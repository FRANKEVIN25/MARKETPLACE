FROM python:3.11-slim-bullseye

# Metadata
LABEL maintainer="ECOMPARTS PERÚ"
LABEL version="1.0"
LABEL description="Django REST API - ECOMPARTS Marketplace"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Directorio de trabajo
WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    postgresql-client \
    libpq-dev \
    curl \
    netcat-openbsd \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar código
COPY . .

# Crear directorios necesarios
RUN mkdir -p staticfiles media logs && \
    touch logs/django.log && \
    chmod +x entrypoint.sh

# Usuario no-root
RUN useradd -m -u 1000 django && \
    chown -R django:django /app

USER django

# Puerto
EXPOSE 8000

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "ecomparts.wsgi:application", "--bind", "0.0.0.0:8000"]
