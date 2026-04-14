# Migration: add odoo_category_id to Category for Odoo↔Django category linking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='odoo_category_id',
            field=models.IntegerField(
                blank=True,
                null=True,
                unique=True,
                help_text=(
                    'ID de la categoría en Odoo (product.category). '
                    'Permite vincular categorías aunque los IDs auto-incrementales difieran.'
                ),
            ),
        ),
    ]
