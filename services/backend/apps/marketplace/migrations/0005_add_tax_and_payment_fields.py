# Generated manually on 2026-02-18
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0004_provider_odoo_password_hash_provider_odoo_user_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='provider',
            name='tax_regime',
            field=models.CharField(
                choices=[
                    ('RUS', 'Régimen Único Simplificado'),
                    ('RER', 'Régimen Especial de Renta'),
                    ('RMT', 'Régimen MYPE Tributario'),
                    ('GENERAL', 'Régimen General')
                ],
                default='GENERAL',
                max_length=20,
                verbose_name='Régimen Tributario'
            ),
        ),
        migrations.AddField(
            model_name='provider',
            name='igv_applicable',
            field=models.BooleanField(
                default=True,
                help_text='False solo para RUS',
                verbose_name='Aplica IGV (18%)'
            ),
        ),
        migrations.AddField(
            model_name='provider',
            name='emite_comprobante',
            field=models.CharField(
                choices=[
                    ('boleta', 'Solo Boleta'),
                    ('factura', 'Solo Factura'),
                    ('ambos', 'Boleta y Factura')
                ],
                default='ambos',
                max_length=20,
                verbose_name='Tipo de Comprobante'
            ),
        ),
        migrations.AddField(
            model_name='provider',
            name='banco_nombre',
            field=models.CharField(blank=True, max_length=100, verbose_name='Nombre del Banco'),
        ),
        migrations.AddField(
            model_name='provider',
            name='banco_cuenta',
            field=models.CharField(blank=True, max_length=50, verbose_name='Número de Cuenta'),
        ),
        migrations.AddField(
            model_name='provider',
            name='banco_cci',
            field=models.CharField(blank=True, max_length=50, verbose_name='CCI Interbancario'),
        ),
        migrations.AddField(
            model_name='provider',
            name='yape_numero',
            field=models.CharField(blank=True, max_length=15, verbose_name='Número Yape'),
        ),
        migrations.AddField(
            model_name='provider',
            name='plin_numero',
            field=models.CharField(blank=True, max_length=15, verbose_name='Número Plin'),
        ),
    ]
