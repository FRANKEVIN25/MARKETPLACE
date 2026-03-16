FROM python:3.11-slim-bullseye

ARG ODOO_VERSION=18.0
ARG ODOO_HOME=/opt/odoo
ARG ODOO_USER=odoo

# Metadata
LABEL maintainer="ECOMPARTS PERÚ"
LABEL version="1.0"
LABEL description="Odoo 18 Community - ECOMPARTS Marketplace Multi-Tenant"

# Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    g++ \
    gosu \
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
    gettext-base \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario Odoo
RUN useradd -m -d ${ODOO_HOME} -U -r ${ODOO_USER}

# Clonar Odoo 18
WORKDIR ${ODOO_HOME}

RUN git clone --depth 1 --branch ${ODOO_VERSION} \
    https://github.com/odoo/odoo.git ${ODOO_HOME}/odoo-server

# 🔧 PARCHE: cbor2 a versión funcional
RUN sed -i 's/cbor2==5.4.2/cbor2==5.4.6/g' ${ODOO_HOME}/odoo-server/requirements.txt

# ✅ PASO 1: Instalar setuptools, pip, wheel y gevent + zope.interface (SIN --no-build-isolation)
RUN pip install --no-cache-dir --upgrade pip wheel setuptools==70.0.0 && \
    pip install --no-cache-dir gevent "zope.interface==7.0.3" "zope.event==5.0"

# ✅ PASO 2: Instalar requirements de Odoo (CON --no-build-isolation)
RUN pip install --no-cache-dir --no-build-isolation -r ${ODOO_HOME}/odoo-server/requirements.txt

# ✅ PASO 3: Paquetes extra (openpyxl, etc.)
RUN pip install --no-cache-dir openpyxl ofxparse qifparse

# Crear directorios necesarios
RUN mkdir -p /mnt/extra-addons \
    && mkdir -p /etc/odoo \
    && mkdir -p /var/lib/odoo

# Copiar addons personalizados y plantilla de configuración
COPY addons/ /mnt/extra-addons/
COPY config/odoo.conf.tpl /etc/odoo/odoo.conf.tpl

# Permisos
RUN chown -R ${ODOO_USER}:${ODOO_USER} \
    ${ODOO_HOME} \
    /mnt/extra-addons \
    /etc/odoo \
    /var/lib/odoo

# Copiar entrypoint para procesamiento de templates y variables
COPY entrypoint.sh /opt/odoo/entrypoint.sh
RUN chmod +x /opt/odoo/entrypoint.sh && chown ${ODOO_USER}:${ODOO_USER} /opt/odoo/entrypoint.sh

# Crear directorios para filestore
RUN mkdir -p /opt/odoo/.local/share/Odoo && chown -R ${ODOO_USER}:${ODOO_USER} /opt/odoo/.local/share/Odoo

# Agregar odoo-bin al PATH
ENV PATH="${ODOO_HOME}/odoo-server:${PATH}"

# Exponer puertos
EXPOSE 8069 8072

# Usar entrypoint para generar/templar /etc/odoo/odoo.conf si es necesario
ENTRYPOINT ["/opt/odoo/entrypoint.sh"]
CMD ["-c", "/etc/odoo/odoo.conf"]