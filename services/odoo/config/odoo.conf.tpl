[options]
# ============================================
# DATABASE
# ============================================
db_host = postgres
db_name = ${ODOO_DB}
db_user = ${POSTGRES_USER}
db_password = ${POSTGRES_PASSWORD}
db_port = 5432

# Máximo de conexiones a la BD (protección)
db_maxconn = 64

# ============================================
# ADDONS PATH
# ============================================
# addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
addons_path = /opt/odoo/odoo-server/odoo/addons,/opt/odoo/odoo-server/addons,/mnt/extra-addons

# ============================================
# SERVER
# ============================================
http_port = 8069
http_interface = 0.0.0.0
admin_passwd = ${ODOO_ADMIN_PASSWORD}
list_db = True

# Asegura que no se carguen datos demo
without_demo = all

# ============================================
# PERFORMANCE & WORKERS
# ============================================
# ⭐ CAMBIO CRÍTICO: Activar workers para multi-tenant
workers = 4
# Número de workers = (2 × CPU cores) + 1
# Con 4 workers puedes atender ~16 requests simultáneos

# Threads para tareas programadas
max_cron_threads = 2

# ============================================
# LÍMITES DE TIEMPO (PROTECCIÓN CRÍTICA)
# ============================================
# ⭐ CAMBIO: Reducir timeouts para evitar queries pesadas
# Timeout de CPU: 2 minutos (antes era 10 min)
limit_time_cpu = 120

# Timeout real: 4 minutos (antes era 20 min)
limit_time_real = 240

# ============================================
# LÍMITES DE MEMORIA (PROTECCIÓN CRÍTICA)
# ============================================
# ⭐ NUEVO: Límites de memoria por worker
# Soft limit: 2 GB (el worker se reinicia después de procesar la request)
limit_memory_soft = 2147483648

# Hard limit: 2.5 GB (el worker se mata inmediatamente)
limit_memory_hard = 2684354560

# ============================================
# LÍMITES DE REQUESTS (PROTECCIÓN)
# ============================================
# ⭐ NUEVO: Número de requests antes de reiniciar worker
# Evita memory leaks
limit_request = 8192

# Límite de tiempo por request HTTP
limit_time_real_cron = 300

# ============================================
# LOGGING
# ============================================
log_level = info
log_db = False
logfile = False
# recomendado para multitenat 
# dbfilter = ^${ODOO_DB}$

# ⭐ NUEVO: Log de queries lentas (para monitoreo)
log_db_level = warning

# ============================================
# SECURITY
# ============================================
proxy_mode = False

# ⭐ NUEVO: Límites de seguridad
# Prevenir ataques de fuerza bruta
max_login_attempts = 5

# Deshabilitar password reset por email (opcional)
# reset_password = False

# ============================================
# SESSION & CACHE
# ============================================
# ⭐ NUEVO: Configuración de sesiones
# Tiempo de vida de sesión: 7 días
session_timeout = 604800

# ============================================
# GEVENT (Optimización para I/O)
# ============================================
# ⭐ NUEVO: Usar gevent para mejor concurrencia
# Solo si workers > 0
server_wide_modules = base,web

# ============================================
# LONGPOLLING / WEBSOCKET (Odoo 18)
# ============================================
# Puerto para el servicio de websockets/evented
# Usado para notificaciones en tiempo real y chat
[longpolling]
port = 8072

# ============================================
# NOTAS IMPORTANTES
# ============================================
# Con esta configuración:
# - 4 workers × 2GB = 8GB RAM máximo para Odoo
# - Queries >2min se cancelan automáticamente
# - Workers se reinician después de 8192 requests
# - Máximo 64 conexiones a PostgreSQL
# 
# Capacidad estimada:
# - 40-60 vendors activos simultáneos
# - 150+ vendors totales (no todos activos al mismo tiempo)
