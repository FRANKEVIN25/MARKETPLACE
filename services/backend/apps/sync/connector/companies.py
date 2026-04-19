"""
connector/companies.py
======================
Operaciones sobre res.company en Odoo.
"""
import logging

logger = logging.getLogger(__name__)


class OdooCompaniesMixin:
    """Mixin con operaciones sobre res.company."""

    def create_company(self, name: str, email: str = None, currency_id: int = 164):
        """
        Crea una nueva Company en Odoo. Idempotente: si ya existe una company
        con ese nombre, retorna su ID sin crear un duplicado.

        Args:
            name:        Nombre de la compañía
            email:       Email de la compañía (opcional)
            currency_id: ID de la moneda (164 = PEN, 2 = USD)

        Returns:
            int: ID de la Company o None si falla
        """
        try:
            existing = self.execute_kw('res.company', 'search', [[('name', '=', name)]])
            if existing:
                company_id = existing[0] if isinstance(existing, list) else existing
                logger.info(f"✅ Company ya existía en Odoo: {name} (ID: {company_id})")
                return company_id

            vals = {'name': name, 'currency_id': currency_id}
            if email:
                vals['email'] = email

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
