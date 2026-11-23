"""Check an existing Django -> Celery -> Odoo order without creating one."""

import time

from django.core.management.base import BaseCommand, CommandError

from apps.orders.models import SubOrder
from apps.sync.odoo_connector import OdooConnector


class Command(BaseCommand):
    help = "Verifica que una SubOrder creada por el flujo web llego a la compania correcta de Odoo"

    def add_arguments(self, parser):
        parser.add_argument("sub_order_number")
        parser.add_argument("--wait-seconds", type=int, default=90)

    def handle(self, *args, **options):
        deadline = time.monotonic() + options["wait_seconds"]
        number = options["sub_order_number"]
        while True:
            try:
                sub = (SubOrder.objects.select_related("provider")
                       .prefetch_related("items__product")
                       .get(sub_order_number=number))
            except SubOrder.DoesNotExist as error:
                raise CommandError(f"No existe SubOrder {number}") from error
            if sub.odoo_sync_error:
                raise CommandError(f"Fallo la sincronizacion de {number}: {sub.odoo_sync_error_detail}")
            if sub.odoo_sale_id:
                break
            if time.monotonic() >= deadline:
                raise CommandError(f"Celery no registro odoo_sale_id para {number} dentro del plazo")
            time.sleep(2)
        if not sub.provider.odoo_company_id:
            raise CommandError("El proveedor no tiene odoo_company_id")
        connector = OdooConnector()
        if not connector.uid:
            raise CommandError("No se pudo autenticar la cuenta de servicio en Odoo")
        context = {"allowed_company_ids": [sub.provider.odoo_company_id]}
        sale = connector.execute_kw("sale.order", "read", [[sub.odoo_sale_id]], {
            "fields": ["company_id", "x_marketplace_suborder_id", "order_line"],
            "context": context,
        })
        if len(sale) != 1:
            raise CommandError("La sale.order vinculada no existe en Odoo")
        sale = sale[0]
        if sale["company_id"][0] != sub.provider.odoo_company_id:
            raise CommandError("La sale.order pertenece a otra compania")
        if sale["x_marketplace_suborder_id"] != number:
            raise CommandError("El identificador de SubOrder no coincide en Odoo")
        lines = connector.execute_kw("sale.order.line", "read", [sale["order_line"]], {
            "fields": ["product_id", "product_uom_qty"], "context": context,
        }) if sale["order_line"] else []
        items = list(sub.items.all())
        if not items or any(not item.product.odoo_product_id for item in items):
            raise CommandError("Hay items sin producto vinculado a Odoo")
        expected = sorted((item.product.odoo_product_id, item.quantity) for item in items)
        actual = sorted((line["product_id"][0], int(line["product_uom_qty"])) for line in lines)
        if expected != actual:
            raise CommandError(f"Lineas diferentes entre Django y Odoo: {expected} != {actual}")
        self.stdout.write(self.style.SUCCESS(
            f"OK SubOrder {number}: Django id={sub.id}, Odoo sale.order id={sub.odoo_sale_id}, "
            f"compania={sub.provider.odoo_company_id}, lineas={len(actual)}"
        ))
