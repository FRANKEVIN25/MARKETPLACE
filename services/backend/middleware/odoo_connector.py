"""
Conector básico con Odoo via XML-RPC
"""
import xmlrpc.client
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class OdooConnector:
    """Cliente básico para Odoo"""
    
    def __init__(self):
        self.url = settings.ODOO_CONFIG['URL'].rstrip('/')
        self.db = settings.ODOO_CONFIG['DB']
        self.username = settings.ODOO_CONFIG['USERNAME']
        self.password = settings.ODOO_CONFIG['PASSWORD']
        self._uid = None
    
    @property
    def uid(self):
        """Obtener UID autenticado (con caché)"""
        if self._uid:
            return self._uid
        
        cached_uid = cache.get('odoo_uid')
        if cached_uid:
            self._uid = cached_uid
            return self._uid
        
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            uid = common.authenticate(self.db, self.username, self.password, {})
            
            if uid:
                self._uid = uid
                cache.set('odoo_uid', uid, 3600)
                logger.info(f"✅ Autenticado en Odoo con UID: {uid}")
                return uid
            else:
                logger.error("❌ Falló la autenticación con Odoo")
                return None
        except Exception as e:
            logger.exception(f"❌ Error conectando a Odoo: {e}")
            return None
    
    def execute(self, model, method, params=None, kwargs=None):
        """Ejecutar método en modelo de Odoo"""
        if not self.uid:
            raise Exception("No se pudo autenticar con Odoo")
        
        params = params or []
        kwargs = kwargs or {}
        
        try:
            models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            result = models.execute_kw(
                self.db, self.uid, self.password,
                model, method, params, kwargs
            )
            return result
        except Exception as e:
            logger.exception(f"❌ Error ejecutando {method} en {model}: {e}")
            raise
    
    def create_product(self, product_data):
        """Crear producto en Odoo (ejemplo simple)"""
        vals = {
            'name': product_data['name'],
            'default_code': product_data.get('reference', ''),
            'list_price': float(product_data.get('price', 0)),
            'type': product_data.get('product_type', 'consu'),
        }
        
        template_id = self.execute('product.template', 'create', params=[vals])
        logger.info(f"✅ Producto creado en Odoo: template_id={template_id}")
        return template_id


# Instancia singleton
odoo_connector = OdooConnector()