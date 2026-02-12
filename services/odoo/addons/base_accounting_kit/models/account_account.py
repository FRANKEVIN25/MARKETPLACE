# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models
from odoo.tools.misc import get_lang


class CashFlow(models.Model):
    """
    Este modelo HEREDA (extiende) el modelo nativo de Odoo: account.account.

    Agrega funcionalidad adicional al Plan Contable estándar de Odoo, 
    específicamente para el manejo de flujos de caja (Cash Flow).
    """
    _inherit = 'account.account'

    def get_cash_flow_ids(self):
        """
        Devuelve un dominio dinámico que filtra los tipos de flujo de caja
        disponibles para esta cuenta.

        Busca un registro predefinido dentro del módulo base_accounting_kit
        llamado 'account_financial_report_cash_flow0' y usa ese registro
        como referencia para limitar las opciones disponibles.
        """
        cash_flow_id = self.env.ref(
            'base_accounting_kit.account_financial_report_cash_flow0'
        )

        if cash_flow_id:
            return [('parent_id.id', '=', cash_flow_id.id)]

    # Campo nuevo agregado al modelo account.account
    # Permite asignar a cada cuenta contable un tipo de flujo de caja
    cash_flow_type = fields.Many2one(
        'account.financial.report',
        string="Tipo de Flujo de Caja",
        domain=get_cash_flow_ids
    )

    @api.onchange('cash_flow_type')
    def onchange_cash_flow_type(self):
        """
        Método que se ejecuta automáticamente cuando cambia el valor
        del campo 'cash_flow_type' en la interfaz de usuario.

        Su función es mantener sincronizada la relación entre:
        - El tipo de flujo de caja seleccionado
        - La lista de cuentas asociadas a dicho flujo

        Básicamente:
        - Agrega la cuenta actual al nuevo flujo seleccionado
        - Quita la cuenta del flujo anterior si existía
        """

        # Se agrega la cuenta actual al nuevo flujo seleccionado
        for rec in self.cash_flow_type:
            rec.write({
                'account_ids': [(4, self._origin.id)]
            })

        # Si la cuenta ya tenía un flujo asignado anteriormente,
        # se elimina la relación con ese flujo antiguo
        if self._origin.cash_flow_type.ids:
            for rec in self._origin.cash_flow_type:
                rec.write({
                    'account_ids': [(3, self._origin.id)]
                })


class AccountCommonJournalReport(models.TransientModel):
    """
    Modelo transitorio (wizard) utilizado para la generación
    de reportes contables de tipo 'Libro Diario'.

    Es un modelo temporal que solo existe mientras el usuario
    está generando un reporte.
    """
    _name = 'account.common.journal.report'
    _description = 'Reporte Común de Diario'
    _inherit = "account.report"

    # Relación Many2many que define qué reportes forman parte
    # de una sección principal
    section_main_report_ids = fields.Many2many(
        string="Pertenece a la Sección",
        comodel_name='account.report',
        relation="account_common_journal_report_section_rel",
        column1="sub_report_id",
        column2="main_report_id"
    )

    # Relación inversa de las secciones del reporte
    section_report_ids = fields.Many2many(
        string="Secciones",
        comodel_name='account.report',
        relation="account_common_journal_report_section_rel",
        column1="main_report_id",
        column2="sub_report_id"
    )

    # Permite indicar si el reporte debe mostrar la columna de moneda
    amount_currency = fields.Boolean(
        'Incluir Moneda',
        help="Imprimir el reporte con la columna de moneda si esta es "
             "diferente a la moneda de la compañía."
    )

    # Compañía sobre la cual se genera el reporte
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )

    # Rango de fechas para filtrar el reporte
    date_from = fields.Date(string='Fecha Inicio')
    date_to = fields.Date(string='Fecha Fin')

    # Permite elegir si se consideran solo asientos publicados
    # o también los borradores
    target_move = fields.Selection(
        [
            ('posted', 'Solo Asientos Publicados'),
            ('all', 'Todos los Asientos'),
        ],
        string='Movimientos a Incluir',
        required=True,
        default='posted'
    )

    def pre_print_report(self, data):
        """
        Método previo a la impresión del reporte.

        Se encarga de inyectar en los datos del reporte
        el valor del campo 'amount_currency', para que
        el motor de reportes sepa si debe mostrar o no
        la columna de moneda.
        """
        data['form'].update({
            'amount_currency': self.amount_currency
        })
        return data

    def check_report(self):
        """
        Método principal que se ejecuta al presionar el botón
        para generar el reporte.

        Prepara toda la información necesaria:
        - Fechas
        - Diarios seleccionados
        - Tipo de movimientos
        - Contexto de idioma
        """

        self.ensure_one()

        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')

        # Se leen los valores ingresados en el wizard
        data['form'] = self.read([
            'date_from',
            'date_to',
            'journal_ids',
            'target_move',
            'company_id'
        ])[0]

        # Se construye el contexto que usará el reporte
        used_context = self._build_contexts(data)

        data['form']['used_context'] = dict(
            used_context,
            lang=get_lang(self.env).code
        )

        # Llamada final para imprimir el reporte
        return self.with_context(
            discard_logo_check=True
        )._print_report(data)

    def _build_contexts(self, data):
        """
        Construye un diccionario de contexto basado en los
        valores seleccionados por el usuario en el wizard.

        Este contexto es el que se enviará al motor de reportes
        para filtrar la información correctamente.
        """
        result = {}

        result['journal_ids'] = (
            'journal_ids' in data['form']
            and data['form']['journal_ids']
            or False
        )

        result['state'] = (
            'target_move' in data['form']
            and data['form']['target_move']
            or ''
        )

        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False

        # Si se especifica fecha inicial, se fuerza rango estricto
        result['strict_range'] = True if result['date_from'] else False

        result['company_id'] = data['form']['company_id'][0] or False

        return result
