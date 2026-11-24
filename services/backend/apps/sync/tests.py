from unittest.mock import Mock, patch
from types import SimpleNamespace

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from .management.commands.setup_odoo import Command
from .services.orders import _get_or_create_partner, _get_utm_source_id, _single_created_id


class OdooCreatedIdTests(SimpleTestCase):
    def test_first_order_for_a_new_customer_uses_an_integer_partner_id(self):
        customer = SimpleNamespace(user=SimpleNamespace(email='new@lab.local',
            first_name='Ana', last_name='LAB', username='ana'), document_number='', phone='')
        for created in (42, [42]):
            with self.subTest(created=created):
                connector = Mock()
                connector.execute_kw.side_effect = [[], created]
                self.assertEqual(_get_or_create_partner(connector, customer), 42)

    def test_new_utm_source_uses_an_integer_relation_id(self):
        connector = Mock()
        connector.execute_kw.side_effect = [[], [17]]
        self.assertEqual(_get_utm_source_id(connector), 17)

    def test_invalid_or_multiple_created_ids_are_rejected(self):
        for value in (None, False, [], [1, 2], '42', 0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                _single_created_id(value)


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
