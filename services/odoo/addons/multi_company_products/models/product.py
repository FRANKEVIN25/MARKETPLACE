from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'company_id' in fields_list and not res.get('company_id'):
            res['company_id'] = self.env.company.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'company_id' in fields_list and not res.get('company_id'):
            res['company_id'] = self.env.company.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)