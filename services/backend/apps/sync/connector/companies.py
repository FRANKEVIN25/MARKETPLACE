"""
connector/companies.py
======================
Operaciones sobre res.company en Odoo.
"""
import logging

logger = logging.getLogger(__name__)


class OdooCompaniesMixin:
    """Mixin con operaciones sobre res.company."""

    def get_currency_id_by_code(self, code: str) -> int | None:
        """
        Resuelve el ID numérico de una moneda a partir de su código ISO.
        p.ej. 'PEN' → ID real en esta instancia Odoo.
        """
        try:
            result = self.execute_kw(
                'res.currency', 'search_read',
                [[['name', '=', code]]],
                {'fields': ['id', 'name'], 'limit': 1},
            )
            if result:
                return result[0]['id']
            logger.warning("Moneda '%s' no encontrada en Odoo", code)
            return None
        except Exception as e:
            logger.error("Error buscando moneda '%s': %s", code, e)
            return None

    def create_company(
        self,
        name: str,
        email: str = None,
        currency_code: str = 'PEN',
        vat: str = None,
        phone: str = None,
    ):
        """
        Crea una nueva Company en Odoo. Idempotente: si ya existe una company
        con ese nombre, retorna su ID sin crear un duplicado.

        Args:
            name:          Nombre de la compañía
            email:         Email de la compañía (opcional)
            currency_code: Código ISO de la moneda (default 'PEN')
            vat:           RUC / número de identificación tributaria (opcional)
            phone:         Teléfono de la compañía (opcional)

        Returns:
            int: ID de la Company o None si falla
        """
        try:
            existing = self.execute_kw('res.company', 'search', [[('name', '=', name)]])
            if existing:
                company_id = existing[0] if isinstance(existing, list) else existing
                logger.info(f"✅ Company ya existía en Odoo: {name} (ID: {company_id})")
                return company_id

            vals = {'name': name}
            currency_id = self.get_currency_id_by_code(currency_code)
            if currency_id:
                vals['currency_id'] = currency_id
            else:
                logger.warning("No se pudo resolver moneda '%s', usando default de Odoo", currency_code)
            if email:
                vals['email'] = email
            if vat:
                vals['vat'] = vat
            if phone:
                vals['phone'] = phone

            company_id = self.execute_kw('res.company', 'create', [[vals]])
            if isinstance(company_id, list):
                company_id = company_id[0]
            logger.info(f"✅ Company creada en Odoo: {name} (ID: {company_id})")
            return company_id

        except Exception as e:
            logger.error(f"❌ Error creando company '{name}': {e}")
            return None

    def get_company(self, company_id: int) -> dict | None:
        """
        Obtiene datos básicos de una Company.

        Args:
            company_id: ID de la Company en Odoo

        Returns:
            dict con id, name, email, currency_id — o None si no existe o falla
        """
        try:
            companies = self.execute_kw(
                'res.company', 'search_read',
                [[['id', '=', company_id]]],
                {'fields': ['id', 'name', 'email', 'currency_id'], 'limit': 1},
            )
            return companies[0] if companies else None
        except Exception as e:
            logger.error(f"Error obteniendo company {company_id}: {e}")
            return None

    def update_company(
        self,
        company_id: int,
        email: str = None,
        currency_code: str = 'PEN',
        vat: str = None,
        phone: str = None,
    ) -> bool:
        """
        Actualiza campos de una Company existente en Odoo.

        Args:
            company_id:    ID de la Company a actualizar
            email:         Email (opcional)
            currency_code: Código ISO de moneda (default 'PEN')
            vat:           RUC / NIF (opcional)
            phone:         Teléfono (opcional)

        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            vals = {}
            currency_id = self.get_currency_id_by_code(currency_code)
            if currency_id:
                vals['currency_id'] = currency_id
            if email:
                vals['email'] = email
            if vat:
                vals['vat'] = vat
            if phone:
                vals['phone'] = phone

            if not vals:
                return True

            self.execute_kw('res.company', 'write', [[company_id], vals])
            logger.info("✅ Company %s actualizada en Odoo: %s", company_id, list(vals.keys()))
            return True
        except Exception as e:
            logger.error("❌ Error actualizando company %s: %s", company_id, e)
            return False
