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

# ✅ PASO 1: Instalar setuptools, pip, wheel y gevent + zope.interface
RUN pip install --no-cache-dir --upgrade pip wheel setuptools==70.0.0 && \
    pip install --no-cache-dir gevent "zope.interface==7.0.3" "zope.event==5.0"

# ✅ PASO 2: Instalar requirements de Odoo
RUN pip install --no-cache-dir --no-build-isolation -r ${ODOO_HOME}/odoo-server/requirements.txt

# ✅ PASO 3: Paquetes extra
RUN pip install --no-cache-dir openpyxl ofxparse qifparse

# Crear directorios necesarios
RUN mkdir -p /mnt/extra-addons \
    /var/lib/odoo \
    /etc/odoo \
    ${ODOO_HOME}/.local/share/Odoo

# Permisos
RUN chown -R ${ODOO_USER}:${ODOO_USER} \
    ${ODOO_HOME} \
    /mnt/extra-addons \
    /var/lib/odoo \
    /etc/odoo

# Cambiar a usuario odoo
USER ${ODOO_USER}

# Agregar odoo-bin al PATH
ENV PATH="${ODOO_HOME}/odoo-server:${PATH}"

# Exponer puertos
EXPOSE 8069 8072

# Comando por defecto
ENTRYPOINT ["odoo-bin"]
CMD ["-c", "/etc/odoo/odoo.conf"]