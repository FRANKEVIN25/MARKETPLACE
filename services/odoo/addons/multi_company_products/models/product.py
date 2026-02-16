from odoo import models, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically assign company_id"""
        for vals in vals_list:
            # Si no tiene company_id asignada, usar la del usuario actual
            if 'company_id' not in vals or not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically assign company_id"""
        for vals in vals_list:
            # Si no tiene company_id asignada, usar la del usuario actual
            if 'company_id' not in vals or not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)
