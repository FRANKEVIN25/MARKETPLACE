from unittest.mock import Mock, patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from .management.commands.setup_odoo import Command


class OdooRuleSetupTests(SimpleTestCase):
    def test_uses_the_rule_id_resolved_in_the_current_database(self):
        connector = Mock()
        connector.execute_kw.side_effect = [
            [{'res_id': 928}],
            [{'id': 928, 'name': 'Company rule', 'domain_force': '[]'}],
            True,
        ]
        with patch.dict(
            'apps.sync.management.commands.setup_odoo.ISOLATION_RULES',
            {'product.product_supplierinfo_comp_rule': "[('company_id', 'in', company_ids)]"},
            clear=True,
        ):
            Command()._apply_isolation_rules(connector)
        connector.execute_kw.assert_any_call(
            'ir.rule', 'write', [[928], {'domain_force': "[('company_id', 'in', company_ids)]"}]
        )

    def test_missing_external_id_does_not_modify_an_unrelated_rule(self):
        connector = Mock()
        connector.execute_kw.return_value = []
        with self.assertRaises(CommandError):
            Command()._apply_isolation_rules(connector)
        self.assertFalse(any(call.args[1] == 'write' for call in connector.execute_kw.call_args_list))

    def test_rule_write_failure_is_reported_to_the_startup_process(self):
        connector = Mock()
        connector.execute_kw.side_effect = [
            [{'res_id': 928}],
            [{'id': 928, 'name': 'Company rule', 'domain_force': '[]'}],
            RuntimeError('Invalid domain'),
        ]
        with self.assertRaises(CommandError):
            Command()._apply_isolation_rules(connector)
