"""
Comando de carga inicial de categorías de autopartes.

Crea la jerarquía canónica de 3 niveles (Principal → Subcategoría → Hoja)
que debe coincidir con la definida en:
    services/odoo/addons/ecomp/data/categories_seed.xml

USO:
    # En Docker
    docker exec -it ecomparts-backend python manage.py seed_categories

    # Con --dry-run para ver qué crearía sin guardar
    docker exec -it ecomparts-backend python manage.py seed_categories --dry-run

    # Para limpiar y recrear (útil en dev)
    docker exec -it ecomparts-backend python manage.py seed_categories --reset

NOTAS:
    - Es idempotente: get_or_create por nombre dentro de cada nivel.
    - Solo crea; no elimina categorías existentes (a menos que use --reset).
        - Cada categoría recibe un sync_key estable al crearse en Django.
        - odoo_category_id queda en NULL hasta ejecutar push_categories.
            Ese comando crea/vincula las categorías en Odoo y rellena el ID real.
    - seed_products.py referencia categorías por nombre; si cambias nombres
      aquí debes actualizar también los nombres en seed_products.py.
"""

from django.core.management.base import BaseCommand
from apps.products.models import Category


# ---------------------------------------------------------------------------
# Definición de la jerarquía: lista de (raíz, subcategorías, hojas)
# Cada entrada: (nombre_nivel1, [(nombre_nivel2, [nombre_nivel3, ...]), ...])
# ---------------------------------------------------------------------------
CATEGORY_TREE = [
    (
        "Motor y Componentes Internos",
        [
            ("Componentes Internos", [
                "Pistones, Empaques y Juntas",
            ]),
            ("Distribución", [
                "Correas y Cadenas",
                "Tensores y Poleas",
            ]),
            ("Admisión", [
                "Filtros de Aire",
                "Mangueras de Admisión",
                "Sensores MAF y MAP",
            ]),
        ],
    ),
    (
        "Sistema de Frenos",
        [
            ("Fricción", [
                "Pastillas de Freno",
                "Zapatas de Freno",
            ]),
            ("Discos y Tambores", [
                "Discos de Freno",
                "Tambores de Freno",
            ]),
            ("Hidráulico y ABS", [
                "Bombas de Freno",
                "Sensores ABS y Módulos",
            ]),
        ],
    ),
    (
        "Suspensión y Dirección",
        [
            ("Suspensión", [
                "Amortiguadores y Resortes",
                "Bases de Amortiguador",
            ]),
            ("Dirección", [
                "Cremalleras y Bombas",
                "Terminales de Dirección",
            ]),
            ("Tren Delantero", [
                "Rótulas y Bujes",
                "Brazos de Suspensión",
            ]),
        ],
    ),
    (
        "Transmisión",
        [
            ("Embrague", [
                "Kit de Embrague",
                "Disco y Prensa",
            ]),
            ("Tracción", [
                "Ejes y Homocinéticas",
                "Diferencial",
            ]),
        ],
    ),
    (
        "Sistema Eléctrico y Electrónica",
        [
            ("Encendido y Carga", [
                "Bujías y Bobinas",
                "Baterías y Alternador",
            ]),
            ("Sensores y Control", [
                "Sensores de Motor",
                "ECU y Módulos de Control",
            ]),
        ],
    ),
    (
        "Iluminación",
        [
            ("Faros", [
                "Faros Delanteros",
                "Faros Traseros y Neblineros",
            ]),
            ("Bombillas", [
                "LED y Halógenos",
                "Xenón",
            ]),
        ],
    ),
    (
        "Carrocería y Exterior",
        [
            ("Exterior", [
                "Parachoques y Capó",
                "Puertas y Paneles",
            ]),
            ("Espejos y Accesorios", [
                "Espejos Retrovisores",
                "Molduras y Embellecedores",
            ]),
            ("Limpieza de Parabrisas", [
                "Plumillas Limpiaparabrisas",
                "Motores Limpiaparabrisas",
            ]),
        ],
    ),
    (
        "Ruedas y Neumáticos",
        [
            ("Llantas", [
                "Neumáticos",
            ]),
            ("Aros", [
                "Rines de Aluminio y Acero",
            ]),
            ("Accesorios de Rueda", [
                "Pernos y Tuercas",
                "Válvulas de Inflado",
            ]),
        ],
    ),
    (
        "Refrigeración y Climatización",
        [
            ("Enfriamiento Motor", [
                "Radiadores y Termostatos",
                "Bombas de Agua",
            ]),
            ("Aire Acondicionado", [
                "Compresores de AC",
                "Filtro de Habitáculo",
            ]),
        ],
    ),
    (
        "Combustible y Escape",
        [
            ("Combustible", [
                "Bombas de Combustible",
                "Filtros de Combustible",
                "Inyectores",
            ]),
            ("Escape", [
                "Silenciadores y Tubos",
                "Catalizadores",
            ]),
        ],
    ),
    (
        "Mantenimiento y Fluidos",
        [
            ("Aceites", [
                "Aceite de Motor",
                "Aceite de Transmisión",
            ]),
            ("Fluidos", [
                "Refrigerante",
                "Líquido de Frenos",
            ]),
            ("Filtros de Mantenimiento", [
                "Filtro de Aire",
                "Filtro de Aceite",
                "Filtro de Combustible",
            ]),
        ],
    ),
    (
        "Herramientas, Equipos y Accesorios",
        [
            ("Herramientas", [
                "Llaves y Dados",
            ]),
            ("Equipos de Diagnóstico", [
                "Escáner OBD2",
                "Gatas y Elevadores",
            ]),
            ("Accesorios para Vehículo", [
                "Alarmas y Cámaras",
                "Fundas y Protectores",
            ]),
        ],
    ),
]


class Command(BaseCommand):
    help = (
        "Carga la jerarquía canónica de 3 niveles de categorías de autopartes. "
        "Idempotente: no duplica si ya existen. "
        "Equivalente al categories_seed.xml de ecomp en Odoo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra qué categorías se crearían sin guardar nada.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "PELIGRO: Elimina TODAS las categorías existentes antes de insertar. "
                "Solo para entornos de desarrollo."
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        reset = options["reset"]

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 Modo DRY-RUN — no se guardará nada.\n"))

        if reset and not dry_run:
            self.stdout.write(self.style.WARNING("⚠  Eliminando todas las categorías existentes..."))
            deleted, _ = Category.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"   {deleted} categorías eliminadas.\n"))

        created_total = 0
        existed_total = 0

        for (root_name, subcategories) in CATEGORY_TREE:
            # ── Nivel 1 ────────────────────────────────────────────────────
            root_obj = self._get_or_create(root_name, parent=None, dry_run=dry_run)
            is_new = root_obj is None  # dry-run devuelve None
            if is_new or (root_obj and not dry_run):
                created_total += 1

            self.stdout.write(
                f"\n📁 {'[DRY-RUN] ' if dry_run else ''}"
                f"{'✓ Creada' if is_new else '✓ Existente'}: {root_name}"
            )

            for (sub_name, leaf_names) in subcategories:
                # ── Nivel 2 ────────────────────────────────────────────────
                sub_obj = self._get_or_create(sub_name, parent=root_obj, dry_run=dry_run)
                self.stdout.write(f"  └── {sub_name}")

                for leaf_name in leaf_names:
                    # ── Nivel 3 ────────────────────────────────────────────
                    self._get_or_create(leaf_name, parent=sub_obj, dry_run=dry_run)
                    self.stdout.write(f"       └── {leaf_name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Jerarquía de categorías {'simulada' if dry_run else 'cargada'} correctamente."
            )
        )
        self.stdout.write(
            "   Siguiente paso: empujar categorías a Odoo para poblar odoo_category_id:\n"
            "   docker exec -it ecomparts-backend python manage.py push_categories\n"
        )

    # -----------------------------------------------------------------------
    def _get_or_create(self, name: str, parent, dry_run: bool):
        """
        Crea la categoría si no existe. En dry-run solo imprime.

        Returns:
            Category | None  (None si dry_run=True)
        """
        if dry_run:
            exists = Category.objects.filter(name=name, parent=parent).exists()
            status = "existente" if exists else "→ se crearía"
            self.stdout.write(f"   [{status}] {name}")
            return None

        lookup = {"name": name}
        if parent is not None:
            lookup["parent"] = parent

        obj, created = Category.objects.get_or_create(
            **lookup,
            defaults={"is_active": True},
        )
        return obj
