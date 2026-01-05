FROM python:3.11-slim-bullseye

ARG ODOO_VERSION=19.0
ARG ODOO_HOME=/opt/odoo
ARG ODOO_USER=odoo

# Metadata
LABEL maintainer="ECOMPARTS PERÚ"
LABEL version="1.0"
LABEL description="Odoo 19 Community - ECOMPARTS Marketplace"

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    libldap2-dev \
    libsasl2-dev \
    libpq-dev \
    libjpeg-dev \
    libffi-dev \
    build-essential \
    curl \
    wget \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario Odoo (sin privilegios)
RUN useradd -m -d ${ODOO_HOME} -U -r ${ODOO_USER}

# Clonar Odoo 19
WORKDIR ${ODOO_HOME}
RUN git clone --depth 1 --branch ${ODOO_VERSION} \
    https://github.com/odoo/odoo.git ${ODOO_HOME}/odoo-server

# Instalar dependencias Python de Odoo
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r ${ODOO_HOME}/odoo-server/requirements.txt

# Copiar addons personalizados
COPY --chown=odoo:odoo addons/ /mnt/extra-addons/

# Copiar configuración
COPY --chown=odoo:odoo config/odoo.conf /etc/odoo/odoo.conf

# Permisos
RUN chown -R ${ODOO_USER}:${ODOO_USER} ${ODOO_HOME} /mnt/extra-addons /etc/odoo

# Crear directorio para filestore
RUN mkdir -p /var/lib/odoo && chown -R ${ODOO_USER}:${ODOO_USER} /var/lib/odoo

USER ${ODOO_USER}

ENV PATH="${ODOO_HOME}/odoo-server:${PATH}"

# Puerto
EXPOSE 8069

# Entrypoint
ENTRYPOINT ["odoo-bin"]
CMD ["-c", "/etc/odoo/odoo.conf"]
