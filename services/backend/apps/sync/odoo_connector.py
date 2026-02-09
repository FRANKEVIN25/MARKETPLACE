"""
Conector profesional con Odoo via XML-RPC
Incluye métodos para crear companies, usuarios y gestionar permisos
"""
import xmlrpc.client
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class OdooConnector:
    """
    Cliente para interactuar con Odoo via XML-RPC
    Soporta autenticación con credenciales específicas o usa las del settings
    """
    
    def __init__(self, url=None, db_name=None, username=None, password=None):
        """
        Inicializa el conector con credenciales específicas o usa las del settings
        
        Args:
            url: URL de Odoo (ej: http://localhost:8069)
            db_name: Nombre de la base de datos
            username: Usuario de Odoo
            password: Password de Odoo (texto plano, no hash)
        """
        self.url = (url or settings.ODOO_CONFIG.get('URL', 'http://localhost:8069')).rstrip('/')
        self.db_name = db_name or settings.ODOO_CONFIG.get('DB', 'ecomparts_odoo_shared')
        self.username = username or settings.ODOO_CONFIG.get('USERNAME', 'admin')
        self.password = password or settings.ODOO_CONFIG.get('PASSWORD', 'admin')
        self._uid = None
        self._models = None
    
    @property
    def uid(self):
        """
        Obtener UID autenticado (con caché por sesión)
        
        Returns:
            int: User ID de Odoo
        """
        if self._uid:
            return self._uid
        
        # Cache key único por credenciales
        cache_key = f'odoo_uid_{self.username}_{self.db_name}'
        cached_uid = cache.get(cache_key)
        
        if cached_uid:
            self._uid = cached_uid
            return self._uid
        
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            uid = common.authenticate(self.db_name, self.username, self.password, {})
            
            if uid:
                self._uid = uid
                cache.set(cache_key, uid, 3600)  # Cache por 1 hora
                logger.info(f"Conectado a Odoo {self.url} como {self.username} (UID: {uid})")
                return uid
            else:
                logger.error(f"Falló autenticación en Odoo para {self.username}")
                return None
                
        except Exception as e:
            logger.exception(f"Error conectando a Odoo: {e}")
            return None
    
    @property
    def models(self):
        """
        Proxy para ejecutar métodos en modelos de Odoo
        
        Returns:
            ServerProxy: Proxy de XML-RPC
        """
        if not self._models:
            self._models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
        return self._models
    
    def execute_kw(self, model, method, args=None, kwargs=None):
        """
        Ejecuta un método en un modelo de Odoo
        
        Args:
            model (str): Nombre del modelo (ej: 'res.company')
            method (str): Método a ejecutar (ej: 'create', 'search', 'write')
            args (list): Argumentos posicionales
            kwargs (dict): Argumentos nombrados
            
        Returns:
            Result del método ejecutado
            
        Raises:
            Exception: Si no se puede autenticar o ejecutar
        """
        if not self.uid:
            raise Exception("No se pudo autenticar con Odoo")
        
        args = args or []
        kwargs = kwargs or {}
        
        try:
            result = self.models.execute_kw(
                self.db_name, self.uid, self.password,
                model, method, args, kwargs
            )
            return result
        except Exception as e:
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
            
            company_id = self.execute_kw('res.company', 'create', [vals])
            
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
            # Grupos por defecto: Inventario (Usuario) + Ventas (Usuario)
            if groups is None:
                groups = self._get_default_vendor_groups()
            
            vals = {
                'name': name,
                'login': login,
                'password': password,
                'company_id': company_id,
                'company_ids': [(6, 0, [company_id])],  # SOLO esta company
            }
            
            # Agregar grupos solo si existen y son válidos
            if groups and isinstance(groups, list) and len(groups) > 0:
                vals['groups_id'] = [(6, 0, groups)]
            
            user_id = self.execute_kw('res.users', 'create', [vals])
            
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
        Obtiene los IDs de los grupos por defecto para vendors
        
        Returns:
            list: Lista de IDs de grupos
        """
        group_xmlids = [
            'stock.group_stock_user',      # Inventario: Usuario
            'sales_team.group_sale_salesman',  # Ventas: Usuario
        ]
        
        group_ids = []
        for xmlid in group_xmlids:
            group_id = self._get_group_id_by_xmlid(xmlid)
            if group_id:
                group_ids.append(group_id)
        
        return group_ids
    
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
                    'barcode', 'weight', 'active'
                ]
            }
            
            if limit:
                kwargs['limit'] = limit
            
            products = self.execute_kw(
                'product.product', 'search_read',
                [domain],
                kwargs
            )
            
            return products
            
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
            
            if 'description' in product_data:
                vals['description_sale'] = product_data['description']
            
            if 'cost' in product_data:
                vals['standard_price'] = float(product_data['cost'])
            
            if 'barcode' in product_data:
                vals['barcode'] = product_data['barcode']
            
            if 'weight' in product_data:
                vals['weight'] = float(product_data['weight'])
            
            template_id = self.execute_kw('product.template', 'create', [[vals]])
            
            logger.info(f"✅ Producto creado en Odoo: {product_data['name']} (ID: {template_id})")
            return template_id
            
        except Exception as e:
            logger.error(f"Error creando producto: {e}")
            return None


def get_odoo_connector_for_provider(provider):
    """
    Factory function: Retorna un OdooConnector configurado para un Provider específico
    
    Args:
        provider (Provider): Instancia del modelo Provider
        
    Returns:
        OdooConnector: Conector configurado
    """
    from apps.marketplace.models import Provider
    
    if not isinstance(provider, Provider):
        raise TypeError("provider debe ser una instancia de Provider")
    
    connection_info = provider.get_odoo_connection_info()
    
    # Si el provider tiene credenciales propias, úsalas
    if provider.has_odoo_credentials():
        # NOTA: Aquí necesitaríamos desencriptar el password
        # Por ahora usamos las credenciales del admin para sincronización
        logger.warning(
            f"Provider {provider.name} tiene credenciales pero "
            "aún no implementamos desencriptación. Usando admin."
        )
    
    # Usar credenciales de admin para operaciones de sincronización
    return OdooConnector(
        url=connection_info['url'],
        db_name=connection_info['db'],
        username=settings.ODOO_CONFIG.get('USERNAME', 'admin'),
        password=settings.ODOO_CONFIG.get('PASSWORD', 'admin')
    )


# Instancia singleton para uso general (con credenciales por defecto)
odoo_connector = OdooConnector()