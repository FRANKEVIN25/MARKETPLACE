"""
Conector profesional con Odoo via JSON-RPC
Migrado de XML-RPC → JSON-RPC el 9 Mar 2026
Incluye métodos para crear companies, usuarios y gestionar permisos
"""
import requests
import json
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class OdooConnector:
    """
    Cliente para interactuar con Odoo via JSON-RPC
    Soporta autenticación con credenciales específicas o usa las del settings
    """

    def __init__(self, url=None, db_name=None, username=None, password=None):
        """
        Inicializa el conector con credenciales específicas o usa las del settings

        Args:
            url: URL de Odoo (ej: http://odoo:8069)
            db_name: Nombre de la base de datos
            username: Usuario de Odoo
            password: Password de Odoo (texto plano)
        """
        self.url = (url or settings.ODOO_CONFIG.get('URL', 'http://odoo:8069')).rstrip('/')
        self.db_name = db_name or settings.ODOO_CONFIG.get('DB', 'ecomparts_odoo_shared')
        self.username = username or settings.ODOO_CONFIG.get('USERNAME', 'admin')
        self.password = password or settings.ODOO_CONFIG.get('PASSWORD', 'admin')
        self._uid = None
        self._session = requests.Session()
        self._session.headers.update({'Content-Type': 'application/json'})

    # ====== CORE JSON-RPC ======

    def _call(self, endpoint, params):
        """
        Realiza una llamada JSON-RPC a Odoo

        Args:
            endpoint (str): Endpoint relativo (ej: /web/session/authenticate)
            params (dict): Parámetros del método

        Returns:
            El campo 'result' de la respuesta JSON

        Raises:
            Exception: Si hay error en la respuesta o de red
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": params,
        }

        try:
            response = self._session.post(
                f"{self.url}{endpoint}",
                data=json.dumps(payload),
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                error = result["error"]
                raise Exception(
                    f"Odoo JSON-RPC error {error.get('code')}: "
                    f"{error.get('message')} — {error.get('data', {}).get('message', '')}"
                )

            return result.get("result")

        except requests.exceptions.RequestException as e:
            logger.exception(f"Error de red conectando a Odoo {self.url}: {e}")
            raise

    @property
    def uid(self):
        """
        Obtiene el UID autenticado.

        No se cachea en Redis porque el UID está ligado a las cookies de sesión
        almacenadas en self._session.  Si se reutilizara el UID de otra instancia
        (o de una instancia anterior) sin las cookies correspondientes, Odoo
        devuelve "Session Expired" en todas las llamadas.

        La autenticación es rápida (~50 ms) y se llama una sola vez por instancia
        de OdooConnector (self._uid actúa de caché intra-instancia).

        Returns:
            int: User ID de Odoo o None si falla
        """
        if self._uid:
            return self._uid

        return self._authenticate()

    def _authenticate(self):
        """Autentica contra Odoo y almacena el UID en self._uid."""
        try:
            result = self._call("/web/session/authenticate", {
                "db": self.db_name,
                "login": self.username,
                "password": self.password,
            })

            uid = result.get("uid") if result else None

            if uid:
                self._uid = uid
                logger.info(
                    f"✅ Conectado a Odoo {self.url} como {self.username} (UID: {uid})"
                )
                return uid
            else:
                logger.error(f"❌ Falló autenticación en Odoo para {self.username}")
                return None

        except Exception as e:
            logger.exception(f"Error autenticando en Odoo: {e}")
            return None

    def execute_kw(self, model, method, args=None, kwargs=None):
        """
        Ejecuta un método en un modelo de Odoo via JSON-RPC

        Args:
            model (str): Nombre del modelo (ej: 'res.company')
            method (str): Método a ejecutar (ej: 'create', 'search_read', 'write')
            args (list): Argumentos posicionales
            kwargs (dict): Argumentos nombrados (fields, limit, domain, etc.)

        Returns:
            Resultado del método ejecutado

        Raises:
            Exception: Si no se puede autenticar o ejecutar
        """
        if not self.uid:
            raise Exception("No se pudo autenticar con Odoo")

        args = args or []
        kwargs = kwargs or {}

        # Extraer context del llamador (si lo pasa) y fusionar con el nuestro.
        # No forzamos 'lang' — Odoo usará el idioma del usuario autenticado.
        caller_context = kwargs.pop('context', {})
        merged_context = {'tz': 'America/Lima', **caller_context}

        def _do_call():
            return self._call("/web/dataset/call_kw", {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": {
                    **kwargs,
                    "context": merged_context,
                },
            })

        try:
            return _do_call()
        except Exception as e:
            err_msg = str(e).lower()
            # Sesión expirada: borrar UID, reautenticar y reintentar una vez.
            if 'session expired' in err_msg or 'session_invalid' in err_msg:
                logger.warning(
                    f"⚠️  Sesión Odoo expirada en {method}/{model}. "
                    "Reautenticando y reintentando..."
                )
                self._uid = None
                if self._authenticate():
                    return _do_call()   # segundo intento con sesión fresca

            logger.exception(f"Error ejecutando {method} en {model}: {e}")
            raise

    # ====== MÉTODOS PARA COMPANIES ======

    def create_company(self, name, email=None, currency_id=164):
        """
        Crea una nueva Company en Odoo

        Args:
            name (str): Nombre de la compañía
            email (str): Email de la compañía
            currency_id (int): ID de la moneda (164 = PEN, 2 = USD)

        Returns:
            int: ID de la Company creada o None si falla
        """
        try:
            vals = {
                'name': name,
                'currency_id': currency_id,
            }
            if email:
                vals['email'] = email

            # Verificar si ya existe una company con ese nombre
            existing = self.execute_kw('res.company', 'search', [[('name', '=', name)]])
            if existing:
                company_id = existing[0] if isinstance(existing, list) else existing
                logger.info(f"✅ Company ya existía en Odoo: {name} (ID: {company_id})")
                return company_id

            company_id = self.execute_kw('res.company', 'create', [[vals]])
            # execute_kw puede retornar [id] o id — normalizar a int
            if isinstance(company_id, list):
                company_id = company_id[0]
            logger.info(f"✅ Company creada en Odoo: {name} (ID: {company_id})")
            return company_id

        except Exception as e:
            logger.error(f"❌ Error creando company {name}: {e}")
            return None

    def get_company(self, company_id):
        """
        Obtiene información de una Company

        Args:
            company_id (int): ID de la Company

        Returns:
            dict: Datos de la Company o None
        """
        try:
            companies = self.execute_kw(
                'res.company', 'search_read',
                [[['id', '=', company_id]]],
                {'fields': ['id', 'name', 'email', 'currency_id'], 'limit': 1}
            )
            return companies[0] if companies else None
        except Exception as e:
            logger.error(f"Error obteniendo company {company_id}: {e}")
            return None

    # ====== MÉTODOS PARA USUARIOS ======

    def create_user_for_company(self, name, login, password, company_id, groups=None):
        """
        Crea un usuario en Odoo asignado a una Company específica

        Args:
            name (str): Nombre completo del usuario
            login (str): Email/username para login
            password (str): Password en texto plano
            company_id (int): ID de la Company principal
            groups (list): Lista de IDs de grupos de permisos (opcional)

        Returns:
            int: ID del usuario creado o None si falla
        """
        try:
            if groups is None:
                groups = self._get_default_vendor_groups()

            vals = {
                'name': name,
                'login': login,
                'password': password,
                'company_id': company_id,
                'company_ids': [(6, 0, [company_id])],  # SOLO esta company
            }

            if groups and isinstance(groups, list) and len(groups) > 0:
                vals['groups_id'] = [(6, 0, groups)]

            # Verificar si ya existe un usuario con ese login
            existing = self.execute_kw('res.users', 'search', [[('login', '=', login)]])
            if existing:
                user_id = existing[0] if isinstance(existing, list) else existing
                logger.info(f"✅ Usuario ya existía en Odoo: {login} (ID: {user_id})")
                return user_id

            user_id = self.execute_kw('res.users', 'create', [[vals]])
            # execute_kw puede retornar [id] o id — normalizar a int
            if isinstance(user_id, list):
                user_id = user_id[0]
            logger.info(
                f"✅ Usuario creado en Odoo: {login} (ID: {user_id}) "
                f"para Company {company_id}"
            )
            return user_id

        except Exception as e:
            logger.error(f"❌ Error creando usuario {login}: {e}")
            return None

    def _get_default_vendor_groups(self):
        """
        Obtiene los IDs de grupos por defecto para vendors

        Returns:
            list: Lista de IDs de grupos
        """
        group_xmlids = [
            'stock.group_stock_user',
            'sales_team.group_sale_salesman',
        ]
        return [
            gid for xmlid in group_xmlids
            if (gid := self._get_group_id_by_xmlid(xmlid)) is not None
        ]

    def _get_group_id_by_xmlid(self, xmlid):
        """
        Obtiene el ID de un grupo por su XML ID

        Args:
            xmlid (str): XML ID del grupo (ej: 'stock.group_stock_user')

        Returns:
            int: ID del grupo o None
        """
        try:
            module, name = xmlid.split('.')
            result = self.execute_kw(
                'ir.model.data', 'search_read',
                [[['module', '=', module], ['name', '=', name]]],
                {'fields': ['res_id'], 'limit': 1}
            )
            if result:
                return result[0]['res_id']
            else:
                logger.warning(f"Grupo no encontrado: {xmlid}")
                return None
        except Exception as e:
            logger.error(f"Error obteniendo grupo {xmlid}: {e}")
            return None

    def update_user_companies(self, user_id, company_ids):
        """
        Actualiza las companies a las que un usuario tiene acceso

        Args:
            user_id (int): ID del usuario
            company_ids (list): Lista de IDs de companies

        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            self.execute_kw(
                'res.users', 'write',
                [[user_id], {'company_ids': [(6, 0, company_ids)]}]
            )
            logger.info(f"✅ Companies actualizadas para usuario {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error actualizando companies de usuario {user_id}: {e}")
            return False

    def get_user(self, user_id):
        """
        Obtiene información de un usuario

        Args:
            user_id (int): ID del usuario

        Returns:
            dict: Datos del usuario o None
        """
        try:
            users = self.execute_kw(
                'res.users', 'search_read',
                [[['id', '=', user_id]]],
                {'fields': ['id', 'name', 'login', 'company_id', 'company_ids'], 'limit': 1}
            )
            return users[0] if users else None
        except Exception as e:
            logger.error(f"Error obteniendo usuario {user_id}: {e}")
            return None

    # ====== MÉTODOS PARA PRODUCTOS ======

    def get_products(self, company_id=None, limit=None):
        """
        Obtiene productos de Odoo

        Args:
            company_id (int): Filtrar por Company (opcional)
            limit (int): Límite de resultados (opcional)

        Returns:
            list: Lista de productos
        """
        try:
            domain = []
            if company_id:
                domain.append(('company_id', '=', company_id))

            kwargs = {
                'fields': [
                    'id', 'name', 'default_code', 'description_sale',
                    'list_price', 'standard_price', 'qty_available',
                    'barcode', 'weight', 'active', 'image_1920'
                ]
            }
            if limit:
                kwargs['limit'] = limit

            return self.execute_kw('product.product', 'search_read', [domain], kwargs)

        except Exception as e:
            logger.error(f"Error obteniendo productos: {e}")
            return []

    def get_product_stock(self, product_id):
        """
        Obtiene el stock de un producto específico

        Args:
            product_id (int): ID del producto

        Returns:
            dict: Información de stock o None
        """
        try:
            products = self.execute_kw(
                'product.product', 'search_read',
                [[['id', '=', product_id]]],
                {'fields': ['qty_available', 'virtual_available'], 'limit': 1}
            )
            return products[0] if products else None
        except Exception as e:
            logger.error(f"Error obteniendo stock de producto {product_id}: {e}")
            return None

    def create_product(self, product_data):
        """
        Crea un producto en Odoo

        Args:
            product_data (dict): Datos del producto

        Returns:
            int: ID del template creado o None
        """
        try:
            vals = {
                'name': product_data['name'],
                'default_code': product_data.get('reference', ''),
                'list_price': float(product_data.get('price', 0)),
                'type': product_data.get('product_type', 'consu'),
            }

            for field in ['description', 'cost', 'barcode', 'weight']:
                if field in product_data:
                    key_map = {'description': 'description_sale', 'cost': 'standard_price'}
                    key = key_map.get(field, field)
                    vals[key] = float(product_data[field]) if field in ('cost', 'weight') else product_data[field]

            template_id = self.execute_kw('product.template', 'create', [[vals]])
            logger.info(f"✅ Producto creado en Odoo: {product_data['name']} (ID: {template_id})")
            return template_id

        except Exception as e:
            logger.error(f"Error creando producto: {e}")
            return None

    # ====== HEALTH CHECK ======

    def ping(self):
        """
        Verifica que la conexión a Odoo funciona

        Returns:
            bool: True si Odoo responde correctamente
        """
        try:
            result = self._call("/web/dataset/call_kw", {
                "model": "res.lang",
                "method": "search_read",
                "args": [[]],
                "kwargs": {"fields": ["id"], "limit": 1},
            })
            return result is not None
        except Exception:
            return False


def get_odoo_connector_for_provider(provider):
    """
    Factory function: Retorna un OdooConnector configurado para un Provider específico

    Args:
        provider: Instancia del modelo Provider

    Returns:
        OdooConnector: Conector configurado con credenciales de admin
    """
    from apps.marketplace.models import Provider

    if not isinstance(provider, Provider):
        raise TypeError("provider debe ser una instancia de Provider")

    connection_info = provider.get_odoo_connection_info()

    if provider.has_odoo_credentials():
        logger.warning(
            f"Provider {provider.name} tiene credenciales propias pero "
            "aún no implementamos desencriptación. Usando admin."
        )

    return OdooConnector(
        url=connection_info['url'],
        db_name=connection_info['db'],
        username=settings.ODOO_CONFIG.get('USERNAME', 'admin'),
        password=settings.ODOO_CONFIG.get('PASSWORD', 'admin'),
    )


# Instancia singleton para uso general (con credenciales por defecto)
odoo_connector = OdooConnector()