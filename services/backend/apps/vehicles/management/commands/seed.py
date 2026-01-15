from django.core.management.base import BaseCommand
import random
from apps.vehicles.models import Marca, ModeloVehiculo, Transmision, Traccion, Motor, VariantVehiculo


class Command(BaseCommand):
    help = 'Genera datos de prueba para los modelos de vehículos'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando carga de datos...")

        # 1. Crear Marcas
        marcas_nombres = ['Toyota', 'Honda', 'Ford', 'Hyundai', 'Tesla']
        marcas_objs = []
        for nombre in marcas_nombres:
            m, _ = Marca.objects.get_or_create(nombre=nombre)
            marcas_objs.append(m)

        # 2. Crear Modelos por Marca
        modelos_data = {
            'Toyota': ['Corolla', 'RAV4', 'Hilux'],
            'Honda': ['Civic', 'CR-V'],
            'Ford': ['F-150', 'Mustang', 'Explorer'],
            'Hyundai': ['Tucson', 'Elantra'],
            'Tesla': ['Model 3', 'Model Y']
        }
        modelos_objs = []
        for marca in marcas_objs:
            for mod_nombre in modelos_data.get(marca.nombre, []):
                mod, _ = ModeloVehiculo.objects.get_or_create(nombre=mod_nombre, marca=marca)
                modelos_objs.append(mod)

        # 3. Crear Transmisiones
        transmisiones = [
            ('MT', 5), ('MT', 6), ('AT', 6), ('AT', 8), ('CVT', None), ('DCT', 7)
        ]
        trans_objs = []
        for t, v in transmisiones:
            obj, _ = Transmision.objects.get_or_create(tipo=t, velocidades=v)
            trans_objs.append(obj)

        # 4. Crear Tracciones
        tracciones = ['4x2', '4x4', 'AWD']
        trac_objs = []
        for t in tracciones:
            obj, _ = Traccion.objects.get_or_create(tipo=t)
            trac_objs.append(obj)

        # 5. Crear Motores (CORREGIDO)
        motores_data = [
            ('GSL', 1600, 'G4FG', 'D-CVVT'),
            ('GSL', 2000, 'M20A-FKS', 'VVT-iE'),
            ('Hib', 1800, '2ZR-FXE', 'Hybrid Synergy Drive'),
            ('Ele', 0, 'Dual Motor', 'Tesla-Electric'),  # ✅ Cambiado None a 0
            ('Dis', 2800, '1GD-FTV', 'Turbo Diesel Intercooler'),
        ]
        motor_objs = []
        for comb, cc, cod, tec in motores_data:
            m, _ = Motor.objects.get_or_create(
                combustible=comb, cilindrada_cc=cc, codigo_motor=cod, tecnologia=tec
            )
            motor_objs.append(m)

        # 6. Crear 20 Variantes
        self.stdout.write("Generando variantes...")
        variantes_creadas = 0
        intentos = 0
        max_intentos = 50
        
        while variantes_creadas < 20 and intentos < max_intentos:
            try:
                VariantVehiculo.objects.create(
                    modelo=random.choice(modelos_objs),
                    motor=random.choice(motor_objs),
                    transmision=random.choice(trans_objs),
                    traccion=random.choice(trac_objs),
                    anio_desde=random.randint(2015, 2022),
                    anio_hasta=random.choice([2024, None])
                )
                variantes_creadas += 1
            except Exception:
                # En caso de que se repita una combinación única (unique_together)
                pass
            intentos += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'¡Listo! Se han creado {VariantVehiculo.objects.count()} variantes en total.'
            )
        )