"""
connector/users.py
==================
Operaciones sobre res.users en Odoo.
"""
import logging

logger = logging.getLogger(__name__)


class OdooUsersMixin:
    """Mixin con operaciones sobre res.users."""

    def create_user_for_company(
        self,
        name: str,
        login: str,
        password: str,
        company_id: int,
        groups: list = None,
    ) -> int | None:
        """
        Crea un usuario en Odoo asignado a una Company específica. Idempotente:
        si ya existe un usuario con ese login, retorna su ID.

        Args:
            name:       Nombre completo del usuario
            login:      Email/username para login
            password:   Password en texto plano
            company_id: ID de la Company principal
            groups:     Lista de IDs de grupos de permisos (None = grupos por defecto)

        Returns:
            int: ID del usuario creado/encontrado, o None si falla
        """
        try:
            if groups is None:
                groups = self._get_default_vendor_groups()

            existing = self.execute_kw('res.users', 'search', [[('login', '=', login)]])
            if existing:
                user_id = existing[0] if isinstance(existing, list) else existing
                logger.info(f"✅ Usuario ya existía en Odoo: {login} (ID: {user_id})")
                return user_id

            vals = {
                'name': name,
                'login': login,
                'password': password,
                'company_id': company_id,
                'company_ids': [(6, 0, [company_id])],  # solo esta company
            }
            if groups and isinstance(groups, list) and len(groups) > 0:
                vals['groups_id'] = [(6, 0, groups)]

            user_id = self.execute_kw('res.users', 'create', [[vals]])
            if isinstance(user_id, list):
                user_id = user_id[0]
            logger.info(
                f"✅ Usuario creado en Odoo: {login} (ID: {user_id}) "
                f"para Company {company_id}"
            )
            return user_id

        except Exception as e:
            logger.error(f"❌ Error creando usuario '{login}': {e}")
            return None

    def _get_default_vendor_groups(self) -> list:
        """
        Retorna los IDs de grupos por defecto para usuarios vendor:
        Inventario/Usuario y Ventas/Vendedor.
        """
        group_xmlids = [
            'stock.group_stock_user',
            'sales_team.group_sale_salesman',
        ]
        return [
            gid for xmlid in group_xmlids
            if (gid := self._get_group_id_by_xmlid(xmlid)) is not None
        ]

    def _get_group_id_by_xmlid(self, xmlid: str) -> int | None:
        """
        Resuelve el ID numérico de un grupo Odoo a partir de su XML ID.

        Args:
            xmlid: XML ID del grupo (ej: 'stock.group_stock_user')

        Returns:
            int: ID del grupo, o None si no existe
        """
        try:
            module, name = xmlid.split('.')
            result = self.execute_kw(
                'ir.model.data', 'search_read',
                [[['module', '=', module], ['name', '=', name]]],
                {'fields': ['res_id'], 'limit': 1},
            )
            if result:
                return result[0]['res_id']
            logger.warning(f"Grupo no encontrado en Odoo: {xmlid}")
            return None
        except Exception as e:
            logger.error(f"Error obteniendo grupo '{xmlid}': {e}")
            return None

    def update_user_companies(self, user_id: int, company_ids: list) -> bool:
        """
        Actualiza el conjunto de companies accesibles para un usuario.

        Args:
            user_id:     ID del usuario en Odoo
            company_ids: Lista de IDs de companies a asignar

        Returns:
            True si la operación fue exitosa
        """
        try:
            self.execute_kw(
                'res.users', 'write',
                [[user_id], {'company_ids': [(6, 0, company_ids)]}],
            )
            logger.info(f"✅ Companies actualizadas para usuario {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error actualizando companies de usuario {user_id}: {e}")
            return False

    def get_user(self, user_id: int) -> dict | None:
        """
        Obtiene datos básicos de un usuario.

        Args:
            user_id: ID del usuario en Odoo

        Returns:
            dict con id, name, login, company_id, company_ids — o None
        """
        try:
            users = self.execute_kw(
                'res.users', 'search_read',
                [[['id', '=', user_id]]],
                {'fields': ['id', 'name', 'login', 'company_id', 'company_ids'], 'limit': 1},
            )
            return users[0] if users else None
        except Exception as e:
            logger.error(f"Error obteniendo usuario {user_id}: {e}")
            return None
