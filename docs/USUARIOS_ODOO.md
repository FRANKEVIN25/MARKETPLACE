# Usuarios tecnicos de Odoo

Este documento define los usuarios tecnicos base del stack ECOMPARTS y como recrearlos de forma segura tras un reset de la base Odoo o en un despliegue nuevo.

## Objetivo

Separar dos responsabilidades:

- `admin2@ecomparts.local`: administrador humano/operativo con acceso total a Odoo.
- `service@ecomparts.local`: cuenta tecnica usada por Django para autenticarse por JSON-RPC contra Odoo.

La separacion evita que Django dependa de una cuenta administrativa interactiva y reduce el riesgo de mezclar credenciales entre operaciones humanas y sincronizacion automatica.

## Variables de entorno

Las credenciales vigentes quedan separadas asi:

```env
ODOO_ADMIN_PASSWORD=Odoo!MasterPass2025    
ODOO_ADMIN_LOGIN=admin2@ecomparts.local
ODOO_ADMIN_PASS=Admin!2025
ODOO_SERVICE_LOGIN=service@ecomparts.local
ODOO_SERVICE_PASS=Service!2025

# Conexion Django -> Odoo
ODOO_URL=http://odoo:8069
ODOO_USERNAME=service@ecomparts.local
ODOO_PASSWORD=Service!2025
```

Reglas importantes:

- `ODOO_USERNAME` y `ODOO_PASSWORD` deben apuntar siempre al usuario de servicio.
- `ODOO_SERVICE_LOGIN` y `ODOO_SERVICE_PASS` deben mantener el mismo valor efectivo que usa Django.
- `ODOO_ADMIN_PASSWORD` no es un usuario. Es la master password de Odoo para operaciones de administracion de base de datos.

## Roles de cada usuario

### 1. Administrador Odoo

Credenciales:

- `ODOO_ADMIN_LOGIN`
- `ODOO_ADMIN_PASS`

Uso esperado:

- Ingreso al UI de Odoo.
- Tareas funcionales y tecnicas de administracion.
- Verificacion manual de modulos, grupos, companias y parametrizacion.
- Soporte operativo tras resets o incidentes.

Grupos que hoy asigna el script:

- `base.group_user`
- `base.group_system`

Interpretacion:

- Tiene privilegios administrativos completos dentro de Odoo.
- Es la cuenta correcta para gestion humana, no para que Django se autentique.

### 2. Usuario de servicio Odoo-Django

Credenciales:

- `ODOO_SERVICE_LOGIN`
- `ODOO_SERVICE_PASS`
- `ODOO_USERNAME`
- `ODOO_PASSWORD`

Uso esperado:

- Autenticacion JSON-RPC desde Django.
- Comandos como `upgrade_odoo_module`, `push_categories`, `sync_products` y provisiones relacionadas.
- Integraciones backend y workers Celery con Odoo.

Grupos que hoy asigna el script:

- `base.group_user`
- `base.group_system`
- `sales_team.group_sale_manager`
- `stock.group_stock_manager`

Interpretacion:

- Hoy tiene permisos amplios porque el backend no solo lee catalogo; tambien crea registros, actualiza modulos y ejecuta sincronizaciones estructurales.
- Si en produccion se quiere reducir privilegios, primero hay que auditar exactamente que modelos y metodos usa Django para no romper la integracion.

## Estado real del script `create_service_user.py`

Archivo fuente:

- `services/odoo/scripts/create_service_user.py`

### Se usa o es referencial

Estado actual:

- Si se ha usado en este proyecto, pero de forma manual.
- No se ejecuta automaticamente al levantar Docker Compose.
- No lo llama el entrypoint de Odoo.
- No esta copiado dentro de la imagen Odoo como parte del arranque.

Esto significa que hoy es un script operativo de mantenimiento/bootstrap, no un paso automatico del deploy.

### Que hace hoy el script

- Busca al usuario por `login`.
- Si no existe, lo crea.
- Si existe, intenta actualizar su password.
- Marca el usuario como activo.
- Asigna los grupos definidos para admin y servicio.
- Hace `commit` explicito al final.

### Que no hace hoy el script

- No se autoejecuta en el arranque del contenedor.
- No crea ni inicializa la base de datos Odoo.
- No instala ni actualiza modulos.
- No elimina usuarios sobrantes o heredados.
- No limpia grupos previos que el usuario ya tuviera.
- No fuerza explicitamente `company_id` y `company_ids` del usuario.
- No rota secretos ni los toma desde un gestor externo.

Conclusión practica:

- Para bootstrap de usuarios, el script esta suficientemente completo.
- Para un proceso de provisionamiento productivo totalmente automatizado, todavia es una pieza manual y no reemplaza una rutina completa de post-inicializacion.

## Como ejecutarlo correctamente

Prerequisitos:

- Estar en la raiz del repo.
- Tener Odoo arriba y saludable.
- Tener el `.env` correcto ya cargado en los contenedores.

Comando recomendado:

```bash
docker exec -i ecomparts-odoo-shared \
  /opt/odoo/odoo-server/odoo-bin shell \
  --no-http \
  -d ecomparts_odoo_shared \
  -c /etc/odoo/odoo.conf \
  < services/odoo/scripts/create_service_user.py
```

Notas:

- Se usa `--no-http` para evitar conflicto con el puerto `8069` cuando Odoo ya esta corriendo.
- El script no vive dentro del contenedor; se envia por `stdin` desde el archivo del repo.
- Si cambias `ODOO_DB`, ajusta tambien el valor de `-d`.

## Cuando conviene ejecutarlo

- Despues de recrear una base Odoo limpia.
- Despues de restaurar un backup donde no existan estos usuarios.
- Despues de cambiar passwords en `.env`.
- Despues de detectar errores de autenticacion entre Django y Odoo.

## Verificacion posterior recomendada

1. Validar que Odoo acepte el login del usuario de servicio.
2. Ejecutar una operacion real desde Django, por ejemplo:

```bash
docker exec -it ecomparts-backend python manage.py upgrade_odoo_module --module=ecomparts_integration
docker exec -it ecomparts-backend python manage.py push_categories
```

Si ambos comandos pasan, la autenticacion y los permisos base del usuario de servicio estan alineados con el backend.

## Recomendaciones para produccion

- No reutilizar passwords de ejemplo; reemplazarlos por secretos fuertes y unicos.
- Mantener `admin2` y `service` separados tambien en gestion operativa y auditoria.
- No configurar Django para entrar con la cuenta administrativa.
- Ejecutar el script como parte del runbook de recuperacion, o automatizarlo en una etapa explicita de post-init si mas adelante se quiere cero intervencion manual.
- Si se endurecen permisos del usuario de servicio, validar primero flujos de sincronizacion, actualizacion de modulos y provisiones multi-company.

## Resumen operativo

- `admin2@ecomparts.local` es la cuenta administrativa humana.
- `service@ecomparts.local` es la cuenta tecnica de integracion.
- Django debe usar siempre `service@ecomparts.local / Service!2025`.
- El script actual sirve para recrear ambos usuarios, pero hoy se ejecuta manualmente.