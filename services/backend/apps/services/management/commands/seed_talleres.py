"""
Management command: seed_talleres
Carga datos de prueba realistas para la app `services`:
    - ServiceCategory (catálogo plano)
  - Service
  - Workshop (distintas combinaciones service_level / commerce_level)
  - WorkshopLocation (dirección y coordenadas)
  - WorkshopService (con precios, tiempos y garantías)
  - WorkshopSchedule (horario semanal)
  - WorkshopServiceHistory (métricas históricas)
  - WorkshopVehicleExpertise (expertise por marca/modelo)

Uso:
  python manage.py seed_talleres
  python manage.py seed_talleres --flush   ← borra datos anteriores del app
"""

import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from apps.services.models import (
    ServiceCategory,
    Service,
    Workshop,
    WorkshopLocation,
    WorkshopService,
    WorkshopSchedule,
    WorkshopServiceHistory,
    WorkshopVehicleExpertise,
)
from apps.vehicles.models import Marca, ModeloVehiculo


# ─────────────────────────────────────────────────────────────────────────────
# Datos maestros
# ─────────────────────────────────────────────────────────────────────────────

CATEGORIES = [
    {'name': 'Motor y Rendimiento',       'icon': 'fa-engine',       'order':  1},
    {'name': 'Frenos y Seguridad',        'icon': 'fa-stop-circle',  'order':  2},
    {'name': 'Suspensión y Dirección',    'icon': 'fa-car-side',     'order':  3},
    {'name': 'Diagnóstico',               'icon': 'fa-laptop-code',  'order':  4},
    {'name': 'Transmisión y Embrague',    'icon': 'fa-gears',        'order':  5},
    {'name': 'Sistema de Enfriamiento',   'icon': 'fa-temperature-half', 'order': 6},
    {'name': 'Electricidad e Iluminación','icon': 'fa-bolt',         'order':  7},
    {'name': 'Aire Acondicionado',        'icon': 'fa-snowflake',    'order':  8},
    {'name': 'Sistema de Escape',         'icon': 'fa-wind',         'order':  9},
    {'name': 'Neumáticos y Aros',         'icon': 'fa-circle',       'order': 10},
    {'name': 'Mantenimiento',             'icon': 'fa-wrench',       'order': 11},
    {'name': 'Planchado y Pintura',       'icon': 'fa-paint-brush',  'order': 12},
]

# (category_name, service_name, service_type, complexity)
SERVICES_DATA = [
    # Motor y Rendimiento
    ('Motor y Rendimiento', 'Cambio de aceite y filtros',        'maintenance', 'low'),
    ('Motor y Rendimiento', 'Afinamiento',                        'maintenance', 'medium'),
    ('Motor y Rendimiento', 'Reparación de culata',               'repair',      'high'),
    ('Motor y Rendimiento', 'Overhaul de motor',                  'repair',      'high'),
    ('Motor y Rendimiento', 'Cambio de bujías',                   'maintenance', 'low'),
    # Frenos y Seguridad
    ('Frenos y Seguridad', 'Cambio de pastillas',                 'maintenance', 'low'),
    ('Frenos y Seguridad', 'Cambio de discos',                    'maintenance', 'medium'),
    ('Frenos y Seguridad', 'Rectificado de tambores',             'repair',      'medium'),
    ('Frenos y Seguridad', 'Revisión de sistema de frenos',       'diagnostic',  'low'),
    ('Frenos y Seguridad', 'Cambio de líquido de frenos',         'maintenance', 'low'),
    # Suspensión y Dirección
    ('Suspensión y Dirección', 'Alineación y balanceo',           'maintenance', 'low'),
    ('Suspensión y Dirección', 'Cambio de amortiguadores',        'maintenance', 'medium'),
    ('Suspensión y Dirección', 'Cambio de rótulas y terminales',  'repair',      'medium'),
    ('Suspensión y Dirección', 'Revisión de dirección',           'diagnostic',  'low'),
    # Diagnóstico
    ('Diagnóstico', 'Escaneo computarizado',                      'diagnostic',  'low'),
    ('Diagnóstico', 'Diagnóstico general',                        'diagnostic',  'low'),
    ('Diagnóstico', 'Diagnóstico de motor',                       'diagnostic',  'medium'),
    # Transmisión y Embrague
    ('Transmisión y Embrague', 'Cambio de aceite de caja',        'maintenance', 'low'),
    ('Transmisión y Embrague', 'Reparación de transmisión automática', 'repair', 'high'),
    ('Transmisión y Embrague', 'Cambio de embrague',              'repair',      'high'),
    ('Transmisión y Embrague', 'Cambio de aceite de diferencial', 'maintenance', 'low'),
    # Sistema de Enfriamiento
    ('Sistema de Enfriamiento', 'Cambio de refrigerante',         'maintenance', 'low'),
    ('Sistema de Enfriamiento', 'Reparación de radiador',         'repair',      'medium'),
    ('Sistema de Enfriamiento', 'Cambio de termostato',           'repair',      'low'),
    # Electricidad e Iluminación
    ('Electricidad e Iluminación', 'Diagnóstico eléctrico',       'diagnostic',  'low'),
    ('Electricidad e Iluminación', 'Cambio de alternador o batería', 'repair',   'medium'),
    ('Electricidad e Iluminación', 'Instalación de accesorios',   'maintenance', 'low'),
    ('Electricidad e Iluminación', 'Reparación de iluminación',   'repair',      'medium'),
    # Aire Acondicionado
    ('Aire Acondicionado', 'Carga de gas refrigerante',           'maintenance', 'low'),
    ('Aire Acondicionado', 'Mantenimiento de A/C',                'maintenance', 'medium'),
    ('Aire Acondicionado', 'Reparación de compresor de A/C',      'repair',      'high'),
    # Sistema de Escape
    ('Sistema de Escape', 'Revisión de sistema de escape',        'diagnostic',  'low'),
    ('Sistema de Escape', 'Reparación de silenciador',            'repair',      'medium'),
    ('Sistema de Escape', 'Cambio de catalizador',                'repair',      'high'),
    # Neumáticos y Aros
    ('Neumáticos y Aros', 'Balanceo de neumáticos',               'maintenance', 'low'),
    ('Neumáticos y Aros', 'Rotación de neumáticos',               'maintenance', 'low'),
    ('Neumáticos y Aros', 'Cambio de neumáticos',                 'maintenance', 'low'),
    ('Neumáticos y Aros', 'Reparación de aro',                    'repair',      'medium'),
    # Mantenimiento
    ('Mantenimiento', 'Mantenimiento general',                    'maintenance', 'low'),
    ('Mantenimiento', 'Cambio de filtro de aire',                 'maintenance', 'low'),
    ('Mantenimiento', 'Cambio de filtro de combustible',          'maintenance', 'low'),
    ('Mantenimiento', 'Revisión pre-viaje',                       'diagnostic',  'low'),
    # Planchado y Pintura
    ('Planchado y Pintura', 'Planchado de carrocería',            'repair',      'medium'),
    ('Planchado y Pintura', 'Pintura general',                    'repair',      'high'),
    ('Planchado y Pintura', 'Retoque de pintura',                 'repair',      'low'),
    ('Planchado y Pintura', 'Corrección de pintura',              'repair',      'medium'),
]

# (username, email, password, workshop_dict)
# Cada workshop_dict puede incluir una clave 'location' (dict) y
# 'specialties_names' (list) — ambas se extraen antes del create().
WORKSHOPS_DATA = [
    (
        'taller_don_carlos',
        'doncarlos@taller.pe',
        'pass_don_carlos',
        {
            'name': 'Taller Don Carlos',
            'ruc': '10456789012',
            'service_level': 'BASIC',
            'commerce_level': 'BUYER',
            'bays': 2,
            'employees': 3,
            'description': 'Taller familiar con 15 años de experiencia en mecánica general.',
            'years_experience': 15,
            'phone': '934567890',
            'whatsapp': '934567890',
            'is_verified': True,
            'is_active': True,
            'certifications': [],
            'specialties_names': ['Motor y Rendimiento', 'Frenos y Seguridad'],
            'location': {
                'address': 'Av. Gran Chimú 420',
                'district': 'San Juan de Lurigancho',
                'province': 'Lima',
                'department': 'Lima',
                'latitude': '-12.009800',
                'longitude': '-77.006400',
                'is_main': True,
            },
        },
    ),
    (
        'mecanica_avila',
        'avila@mecanicaavila.pe',
        'pass_avila',
        {
            'name': 'Mecánica Ávila SAC',
            'ruc': '20345678901',
            'service_level': 'MANAGED',
            'commerce_level': 'B2B_BUYER',
            'bays': 5,
            'employees': 8,
            'description': (
                'Taller profesional con ERP Odoo. Especialistas en frenos y suspensión. '
                'Trabajamos con flotas corporativas.'
            ),
            'years_experience': 10,
            'phone': '912345678',
            'whatsapp': '912345678',
            'website': 'https://mecanicaavila.pe',
            'is_verified': True,
            'is_active': True,
            'certifications': ['RUC activo', 'Emisión de facturas electrónicas'],
            'specialties_names': ['Frenos y Seguridad', 'Suspensión y Dirección'],
            'location': {
                'address': 'Av. Universitaria 1530',
                'district': 'Los Olivos',
                'province': 'Lima',
                'department': 'Lima',
                'latitude': '-11.981400',
                'longitude': '-77.070300',
                'is_main': True,
            },
        },
    ),
    (
        'centro_miraflores',
        'info@centroautomotrizmiraf.pe',
        'pass_centro',
        {
            'name': 'Centro Automotriz Miraflores',
            'ruc': '20567890123',
            'service_level': 'ADVANCED',
            'commerce_level': 'SELLER',
            'bays': 8,
            'employees': 15,
            'max_fleet_size': 20,
            'description': (
                'Centro premium con tecnología de punta, ERP Odoo, analítica y venta de repuestos. '
                'Certificados ISO 9001.'
            ),
            'years_experience': 20,
            'phone': '998765432',
            'whatsapp': '998765432',
            'website': 'https://centroautomotrizmiraf.pe',
            'is_verified': True,
            'is_active': True,
            'certifications': ['ISO 9001', 'Certificación ASE', 'RUC activo'],
            'specialties_names': ['Motor y Rendimiento', 'Diagnóstico', 'Transmisión y Embrague'],
            'location': {
                'address': 'Calle Berlín 356',
                'district': 'Miraflores',
                'province': 'Lima',
                'department': 'Lima',
                'latitude': '-12.121100',
                'longitude': '-77.027300',
                'is_main': True,
            },
        },
    ),
    (
        'taller_rapido',
        'rapido@express.pe',
        'pass_rapido',
        {
            'name': 'Taller Express El Rápido',
            'ruc': '20610000001',
            'service_level': 'BASIC',
            'commerce_level': 'BUYER',
            'bays': 1,
            'employees': 2,
            'description': 'Taller de barrio, rápido y económico. Cambio de aceite en 30 minutos.',
            'years_experience': 5,
            'phone': '923456789',
            'whatsapp': '923456789',
            'is_verified': False,
            'is_active': True,
            'certifications': ['RUC activo'],
            'specialties_names': ['Motor y Rendimiento', 'Mantenimiento'],
            'location': {
                'address': 'Jr. Huánuco 280',
                'district': 'Ate',
                'province': 'Lima',
                'department': 'Lima',
                'latitude': '-12.057200',
                'longitude': '-76.935800',
                'is_main': True,
            },
        },
    ),
    (
        'autotech_service',
        'admin@autotech.pe',
        'pass_autotech',
        {
            'name': 'AutoTech Service',
            'ruc': '20234567890',
            'service_level': 'MANAGED',
            'commerce_level': 'B2B_BUYER',
            'bays': 4,
            'employees': 6,
            'description': (
                'Servicio técnico autorizado. Diagnóstico computarizado y electricidad automotriz. '
                'Atención de lunes a sábado.'
            ),
            'years_experience': 8,
            'phone': '987654321',
            'whatsapp': '987654321',
            'website': 'https://autotech.pe',
            'is_verified': True,
            'is_active': True,
            'certifications': ['RUC activo', 'Certificación Bosch Car Service'],
            'specialties_names': ['Electricidad e Iluminación', 'Diagnóstico'],
            'location': {
                'address': 'Av. Javier Prado Este 4200',
                'district': 'San Borja',
                'province': 'Lima',
                'department': 'Lima',
                'latitude': '-12.089200',
                'longitude': '-76.998600',
                'is_main': True,
            },
        },
    ),
    (
        'motores_y_mas',
        'contacto@motoressur.pe',
        'pass_motores',
        {
            'name': 'Motores y Más EIRL',
            'ruc': '10123456789',
            'service_level': 'BASIC',
            'commerce_level': 'NONE',
            'bays': 2,
            'employees': 3,
            'description': 'Especialistas en motores de combustión. Solo servicio, sin venta de repuestos.',
            'years_experience': 12,
            'phone': '911223344',
            'is_verified': False,
            'is_active': True,
            'certifications': ['RUC activo'],
            'specialties_names': ['Motor y Rendimiento', 'Transmisión y Embrague'],
            'location': {
                'address': 'Av. Pachacútec 1100',
                'district': 'Villa El Salvador',
                'province': 'Lima',
                'department': 'Lima',
                'latitude': '-12.208600',
                'longitude': '-76.938500',
                'is_main': True,
            },
        },
    ),
    (
        'techcar_premium',
        'info@techcar.pe',
        'pass_techcar',
        {
            'name': 'TechCar Premium',
            'ruc': '20678901234',
            'service_level': 'ADVANCED',
            'commerce_level': 'SELLER',
            'bays': 10,
            'employees': 20,
            'max_fleet_size': 50,
            'description': (
                'Concesionario multimarca con servicio técnico premium, venta de repuestos originales '
                'y analítica de flota. ERP Odoo + BI.'
            ),
            'years_experience': 25,
            'phone': '016154000',
            'whatsapp': '998112233',
            'website': 'https://techcarpremium.pe',
            'is_verified': True,
            'is_active': True,
            'certifications': ['ISO 9001', 'ISO 14001', 'ASE', 'RUC activo'],
            'specialties_names': [
                'Motor y Rendimiento', 'Transmisión y Embrague',
                'Diagnóstico', 'Electricidad e Iluminación',
            ],
            'location': {
                'address': 'Av. Rivera Navarrete 540',
                'district': 'San Isidro',
                'province': 'Lima',
                'department': 'Lima',
                'latitude': '-12.092800',
                'longitude': '-77.028700',
                'is_main': True,
            },
        },
    ),
    (
        'taller_los_andes',
        'losandes@taller.pe',
        'pass_andes',
        {
            'name': 'Taller Mecánico Los Andes',
            'ruc': '20610000002',
            'service_level': 'BASIC',
            'commerce_level': 'BUYER',
            'bays': 3,
            'employees': 4,
            'description': 'Taller de barrio con especialidad en frenos y A/C. Precios accesibles.',
            'years_experience': 7,
            'phone': '955667788',
            'whatsapp': '955667788',
            'is_verified': True,
            'is_active': True,
            'certifications': ['RUC activo'],
            'specialties_names': ['Frenos y Seguridad', 'Aire Acondicionado'],
            'location': {
                'address': 'Jr. Madre de Dios 340',
                'district': 'Independencia',
                'province': 'Lima',
                'department': 'Lima',
                'latitude': '-11.994200',
                'longitude': '-77.053000',
                'is_main': True,
            },
        },
    ),
    (
        'taller_escapes_peru',
        'escapes@escapesperu.pe',
        'pass_escapes',
        {
            'name': 'Escapes Perú',
            'ruc': '20610000003',
            'service_level': 'BASIC',
            'commerce_level': 'BUYER',
            'bays': 2,
            'employees': 3,
            'description': 'Especialistas en sistemas de escape y planchado automotriz.',
            'years_experience': 9,
            'phone': '944556677',
            'whatsapp': '944556677',
            'is_verified': False,
            'is_active': True,
            'certifications': ['RUC activo'],
            'specialties_names': ['Sistema de Escape', 'Planchado y Pintura'],
            'location': {
                'address': 'Av. Argentina 2350',
                'district': 'Carmen de la Legua',
                'province': 'Callao',
                'department': 'Callao',
                'latitude': '-12.053100',
                'longitude': '-77.099400',
                'is_main': True,
            },
        },
    ),
    (
        'neumaticos_veloz',
        'ventas@neumaticosveloz.pe',
        'pass_veloz',
        {
            'name': 'Neumáticos Veloz',
            'ruc': '20610000004',
            'service_level': 'BASIC',
            'commerce_level': 'BUYER',
            'bays': 4,
            'employees': 5,
            'description': 'Centro especializado en neumáticos, aros y sistema de enfriamiento.',
            'years_experience': 11,
            'phone': '966778899',
            'whatsapp': '966778899',
            'is_verified': True,
            'is_active': True,
            'certifications': ['RUC activo'],
            'specialties_names': ['Neumáticos y Aros', 'Sistema de Enfriamiento'],
            'location': {
                'address': 'Av. Túpac Amaru 3400',
                'district': 'Comas',
                'province': 'Lima',
                'department': 'Lima',
                'latitude': '-11.942600',
                'longitude': '-77.047800',
                'is_main': True,
            },
        },
    ),
]

# Precios referenciales (min, max) en soles por servicio
SERVICE_PRICES = {
    'Cambio de aceite y filtros':               (60,    120),
    'Afinamiento':                              (120,   280),
    'Reparación de culata':                     (800,  2200),
    'Overhaul de motor':                        (2500, 6000),
    'Cambio de bujías':                         (40,    120),
    'Cambio de pastillas':                      (80,    200),
    'Cambio de discos':                         (200,   500),
    'Rectificado de tambores':                  (100,   250),
    'Revisión de sistema de frenos':            (50,    100),
    'Cambio de líquido de frenos':              (40,     80),
    'Alineación y balanceo':                    (40,     90),
    'Cambio de amortiguadores':                 (200,   600),
    'Cambio de rótulas y terminales':           (150,   400),
    'Revisión de dirección':                    (50,    100),
    'Escaneo computarizado':                    (50,    120),
    'Diagnóstico general':                      (40,    100),
    'Diagnóstico de motor':                     (80,    180),
    'Cambio de aceite de caja':                 (90,    200),
    'Reparación de transmisión automática':     (1200, 3500),
    'Cambio de embrague':                       (500,  1400),
    'Cambio de aceite de diferencial':          (80,    160),
    'Cambio de refrigerante':                   (60,    120),
    'Reparación de radiador':                   (200,   600),
    'Cambio de termostato':                     (80,    200),
    'Diagnóstico eléctrico':                    (60,    150),
    'Cambio de alternador o batería':           (150,   450),
    'Instalación de accesorios':                (80,    300),
    'Reparación de iluminación':                (60,    200),
    'Carga de gas refrigerante':                (80,    180),
    'Mantenimiento de A/C':                     (120,   350),
    'Reparación de compresor de A/C':           (600,  1800),
    'Revisión de sistema de escape':            (50,    100),
    'Reparación de silenciador':                (120,   350),
    'Cambio de catalizador':                    (400,  1200),
    'Balanceo de neumáticos':                   (30,     60),
    'Rotación de neumáticos':                   (30,     60),
    'Cambio de neumáticos':                     (40,     80),
    'Reparación de aro':                        (80,    250),
    'Mantenimiento general':                    (80,    200),
    'Cambio de filtro de aire':                 (30,     80),
    'Cambio de filtro de combustible':          (40,    100),
    'Revisión pre-viaje':                       (50,    120),
    'Planchado de carrocería':                  (200,   800),
    'Pintura general':                          (1500, 5000),
    'Retoque de pintura':                       (150,   500),
    'Corrección de pintura':                    (300,  1000),
}

# Tiempos estimados en minutos por servicio
SERVICE_TIMES = {
    'Cambio de aceite y filtros':               30,
    'Afinamiento':                              120,
    'Reparación de culata':                     480,
    'Overhaul de motor':                        1440,
    'Cambio de bujías':                         45,
    'Cambio de pastillas':                      60,
    'Cambio de discos':                         90,
    'Rectificado de tambores':                  120,
    'Revisión de sistema de frenos':            45,
    'Cambio de líquido de frenos':              30,
    'Alineación y balanceo':                    45,
    'Cambio de amortiguadores':                 120,
    'Cambio de rótulas y terminales':           90,
    'Revisión de dirección':                    30,
    'Escaneo computarizado':                    30,
    'Diagnóstico general':                      30,
    'Diagnóstico de motor':                     60,
    'Cambio de aceite de caja':                 60,
    'Reparación de transmisión automática':     480,
    'Cambio de embrague':                       240,
    'Cambio de aceite de diferencial':          45,
    'Cambio de refrigerante':                   45,
    'Reparación de radiador':                   180,
    'Cambio de termostato':                     60,
    'Diagnóstico eléctrico':                    60,
    'Cambio de alternador o batería':           90,
    'Instalación de accesorios':                60,
    'Reparación de iluminación':                60,
    'Carga de gas refrigerante':                45,
    'Mantenimiento de A/C':                     90,
    'Reparación de compresor de A/C':           300,
    'Revisión de sistema de escape':            30,
    'Reparación de silenciador':                90,
    'Cambio de catalizador':                    120,
    'Balanceo de neumáticos':                   20,
    'Rotación de neumáticos':                   30,
    'Cambio de neumáticos':                     30,
    'Reparación de aro':                        60,
    'Mantenimiento general':                    60,
    'Cambio de filtro de aire':                 15,
    'Cambio de filtro de combustible':          30,
    'Revisión pre-viaje':                       45,
    'Planchado de carrocería':                  240,
    'Pintura general':                          480,
    'Retoque de pintura':                       120,
    'Corrección de pintura':                    180,
}

SPECIALTY_SERVICE_MAP = {
    'Motor y Rendimiento': [
        'Cambio de aceite y filtros',
        'Afinamiento',
        'Reparación de culata',
        'Overhaul de motor',
        'Cambio de bujías',
    ],
    'Frenos y Seguridad': [
        'Cambio de pastillas',
        'Cambio de discos',
        'Rectificado de tambores',
        'Revisión de sistema de frenos',
        'Cambio de líquido de frenos',
    ],
    'Suspensión y Dirección': [
        'Alineación y balanceo',
        'Cambio de amortiguadores',
        'Cambio de rótulas y terminales',
        'Revisión de dirección',
    ],
    'Diagnóstico': [
        'Escaneo computarizado',
        'Diagnóstico general',
        'Diagnóstico de motor',
    ],
    'Transmisión y Embrague': [
        'Cambio de aceite de caja',
        'Reparación de transmisión automática',
        'Cambio de embrague',
        'Cambio de aceite de diferencial',
    ],
    'Sistema de Enfriamiento': [
        'Cambio de refrigerante',
        'Reparación de radiador',
        'Cambio de termostato',
    ],
    'Electricidad e Iluminación': [
        'Diagnóstico eléctrico',
        'Cambio de alternador o batería',
        'Instalación de accesorios',
        'Reparación de iluminación',
    ],
    'Aire Acondicionado': [
        'Carga de gas refrigerante',
        'Mantenimiento de A/C',
        'Reparación de compresor de A/C',
    ],
    'Sistema de Escape': [
        'Revisión de sistema de escape',
        'Reparación de silenciador',
        'Cambio de catalizador',
    ],
    'Neumáticos y Aros': [
        'Balanceo de neumáticos',
        'Rotación de neumáticos',
        'Cambio de neumáticos',
        'Reparación de aro',
    ],
    'Mantenimiento': [
        'Mantenimiento general',
        'Cambio de filtro de aire',
        'Cambio de filtro de combustible',
        'Revisión pre-viaje',
    ],
    'Planchado y Pintura': [
        'Planchado de carrocería',
        'Pintura general',
        'Retoque de pintura',
        'Corrección de pintura',
    ],
}

# Horarios típicos: (day_of_week, start, end)
SCHEDULE_WEEKDAYS = [
    (0, '08:00', '18:00'),
    (1, '08:00', '18:00'),
    (2, '08:00', '18:00'),
    (3, '08:00', '18:00'),
    (4, '08:00', '18:00'),
    (5, '08:00', '13:00'),
]
SCHEDULE_EXTENDED = [
    (0, '07:30', '19:00'),
    (1, '07:30', '19:00'),
    (2, '07:30', '19:00'),
    (3, '07:30', '19:00'),
    (4, '07:30', '19:00'),
    (5, '07:30', '17:00'),
    (6, '09:00', '13:00'),
]


# ─────────────────────────────────────────────────────────────────────────────
# Command
# ─────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Carga datos de prueba para la app services (talleres, categorías, servicios, horarios)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Elimina todos los datos existentes de la app services antes de cargar.',
        )

    def handle(self, *args, **options):
        rng = random.Random(42)  # seed fijo → resultados reproducibles

        if options['flush']:
            self.stdout.write(self.style.WARNING('⚠ Eliminando datos existentes de services...'))
            WorkshopVehicleExpertise.objects.all().delete()
            WorkshopServiceHistory.objects.all().delete()
            WorkshopSchedule.objects.all().delete()
            WorkshopService.objects.all().delete()
            WorkshopLocation.objects.all().delete()
            Workshop.objects.all().delete()
            Service.objects.all().delete()
            ServiceCategory.objects.all().delete()
            self.stdout.write(self.style.WARNING('✓ Datos eliminados.\n'))

        # ── 1. Categorías ──────────────────────────────────────────────────────
        self.stdout.write('▶ Creando categorías de servicio...')
        cat_map = {}   # name → ServiceCategory

        for cat_data in CATEGORIES:
            cat, created = ServiceCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'icon': cat_data['icon'],
                    'order': cat_data['order'],
                },
            )
            cat_map[cat_data['name']] = cat
            status = '✓ creada' if created else '  ya existe'
            self.stdout.write(f'  {status}: {cat.name}')

        self.stdout.write(self.style.SUCCESS(f'  → {len(cat_map)} categorías\n'))

        # ── 2. Servicios ───────────────────────────────────────────────────────
        self.stdout.write('▶ Creando servicios del catálogo...')
        service_map = {}  # service_name → Service

        for (cat_name, service_name, stype, complexity) in SERVICES_DATA:
            category = cat_map.get(cat_name)
            svc, created = Service.objects.get_or_create(
                name=service_name,
                category=category,
                defaults={
                    'service_type': stype,
                    'complexity': complexity,
                },
            )
            service_map[service_name] = svc

        self.stdout.write(self.style.SUCCESS(f'  → {len(service_map)} servicios\n'))

        # ── 3. Usuarios propietarios ───────────────────────────────────────────
        self.stdout.write('▶ Creando usuarios propietarios...')
        user_map = {}

        # Superuser admin
        admin_user, created = User.objects.get_or_create(username='admin')
        if created:
            admin_user.set_password('admin123')
            admin_user.is_superuser = True
            admin_user.is_staff = True
            admin_user.email = 'admin@ecomparts.pe'
            admin_user.save()
            self.stdout.write(self.style.WARNING('  ✓ Superuser admin creado (pass: admin123)'))

        for (uname, email, pwd, _) in WORKSHOPS_DATA:
            user, created = User.objects.get_or_create(
                username=uname,
                defaults={'email': email},
            )
            if created:
                user.set_password(pwd)
                user.save()
                self.stdout.write(f'  ✓ Usuario creado: {uname}')
            user_map[uname] = user

        self.stdout.write(self.style.SUCCESS(f'  → {len(user_map)} usuarios\n'))

        # ── 4. Talleres ────────────────────────────────────────────────────────
        self.stdout.write('▶ Creando talleres...')
        workshop_map = {}    # workshop_name → Workshop
        specialty_map = {}   # workshop_name → [category_name, ...]

        for (uname, _, _, wdata) in WORKSHOPS_DATA:
            specialty_names = wdata.pop('specialties_names', [])
            location_data   = wdata.pop('location', {})
            owner = user_map[uname]

            ruc = wdata.get('ruc')
            if Workshop.objects.filter(owner=owner).exists():
                workshop = Workshop.objects.filter(owner=owner).first()
                self.stdout.write(f'  ya existe: {wdata["name"]}')
            elif ruc and Workshop.objects.filter(ruc=ruc).exists():
                workshop = Workshop.objects.get(ruc=ruc)
                self.stdout.write(f'  ya existe: {wdata["name"]}')
            else:
                workshop = Workshop.objects.create(owner=owner, **wdata)
                self.stdout.write(f'  ✓ creado: {workshop}')

            # WorkshopLocation principal
            if location_data and not workshop.locations.filter(is_main=True).exists():
                WorkshopLocation.objects.create(workshop=workshop, **location_data)

            workshop_map[workshop.name] = workshop
            specialty_map[workshop.name] = specialty_names

        self.stdout.write(self.style.SUCCESS(f'  → {len(workshop_map)} talleres\n'))

        # ── 5. WorkshopServices ────────────────────────────────────────────────
        self.stdout.write('▶ Asignando servicios a talleres...')
        ws_count = 0

        for workshop in Workshop.objects.all():
            specialties = specialty_map.get(workshop.name, [])

            # Servicios según especialidades declaradas
            offered_service_names = set()
            for specialty in specialties:
                offered_service_names.update(SPECIALTY_SERVICE_MAP.get(specialty, []))

            # Todos los talleres ofrecen diagnóstico general y escaneo
            offered_service_names.add('Diagnóstico general')
            offered_service_names.add('Escaneo computarizado')

            for svc_name in offered_service_names:
                svc = service_map.get(svc_name)
                if not svc:
                    continue

                min_p, max_p = SERVICE_PRICES.get(svc_name, (50, 200))
                min_price = round(min_p * rng.uniform(0.9, 1.0), 2)
                max_price = round(max_p * rng.uniform(1.0, 1.1), 2)
                est_time = SERVICE_TIMES.get(svc_name, 60)

                has_warranty = (
                    workshop.service_level == 'ADVANCED'
                    or (workshop.service_level == 'MANAGED' and rng.random() > 0.3)
                )
                warranty_days = rng.choice([30, 60, 90, 180]) if has_warranty else 0

                first_specialty = specialties[0] if specialties else ''
                is_specialized = svc_name in SPECIALTY_SERVICE_MAP.get(first_specialty, [])

                ws, created = WorkshopService.objects.get_or_create(
                    workshop=workshop,
                    service=svc,
                    defaults={
                        'min_price': min_price,
                        'max_price': max_price,
                        'estimated_time_min': est_time,
                        'has_warranty': has_warranty,
                        'warranty_days': warranty_days,
                        'is_specialized': is_specialized,
                        'available': True,
                    },
                )
                if created:
                    ws_count += 1

        self.stdout.write(self.style.SUCCESS(f'  → {ws_count} WorkshopService creados\n'))

        # ── 6. Horarios ────────────────────────────────────────────────────────
        self.stdout.write('▶ Generando horarios semanales...')
        sched_count = 0

        for workshop in Workshop.objects.all():
            # Talleres ADVANCED / premium tienen horario extendido
            schedule = (
                SCHEDULE_EXTENDED
                if workshop.service_level == 'ADVANCED'
                else SCHEDULE_WEEKDAYS
            )
            for (day, start, end) in schedule:
                _, created = WorkshopSchedule.objects.get_or_create(
                    workshop=workshop,
                    day_of_week=day,
                    start_time=start,
                    defaults={'end_time': end, 'is_active': True},
                )
                if created:
                    sched_count += 1

        self.stdout.write(self.style.SUCCESS(f'  → {sched_count} horarios creados\n'))

        # ── 7. Historial ───────────────────────────────────────────────────────
        self.stdout.write('▶ Generando historial de servicios...')
        hist_count = 0

        for workshop in Workshop.objects.all():
            for ws in workshop.workshop_services.select_related('service').all():
                base_demand = workshop.years_experience * rng.randint(5, 15)
                total_demand = max(1, base_demand + rng.randint(-10, 10))

                total_ratings = rng.randint(max(1, total_demand // 5), max(2, total_demand // 2))

                base_rating = 4.0 if workshop.is_verified else 3.5
                avg_rating = round(
                    min(5.0, max(1.0, base_rating + rng.uniform(-0.5, 0.8))), 2
                )
                last_jobs = date.today() - timedelta(days=rng.randint(1, 90))

                _, created = WorkshopServiceHistory.objects.get_or_create(
                    workshop=workshop,
                    service=ws.service,
                    defaults={
                        'total_demand': total_demand,
                        'total_ratings': total_ratings,
                        'avg_rating': avg_rating,
                        'last_jobs_date': last_jobs,
                    },
                )
                if created:
                    hist_count += 1

        self.stdout.write(self.style.SUCCESS(f'  → {hist_count} registros de historial\n'))

        # ── 8. Vehicle Expertise ───────────────────────────────────────────────
        self.stdout.write('▶ Asignando expertise vehicular...')
        exp_count = 0

        # workshop_name → [(marca_nombre, nivel), ...]
        BRAND_EXPERTISE = {
            'Taller Don Carlos':               [('Toyota', 'pro'),    ('Nissan', 'basic')],
            'Mecánica Ávila SAC':              [('Toyota', 'expert'), ('Honda', 'pro'),    ('Hyundai', 'basic')],
            'Centro Automotriz Miraflores':    [('BMW', 'expert'),    ('Mercedes-Benz', 'expert'), ('Audi', 'pro')],
            'Taller Express El Rápido':        [('Toyota', 'basic'),  ('Kia', 'basic')],
            'AutoTech Service':                [('Toyota', 'pro'),    ('Kia', 'pro'),      ('Hyundai', 'pro')],
            'Motores y Más EIRL':              [('Toyota', 'expert'), ('Mitsubishi', 'pro')],
            'TechCar Premium':                 [('Toyota', 'expert'), ('BMW', 'pro'),      ('Ford', 'pro'), ('Chevrolet', 'basic')],
            'Taller Mecánico Los Andes':       [('Kia', 'pro'),       ('Hyundai', 'pro')],
            'Escapes Perú':                    [('Toyota', 'basic'),  ('Nissan', 'basic')],
            'Neumáticos Veloz':                [('Toyota', 'basic'),  ('Kia', 'basic'),    ('Hyundai', 'basic')],
        }

        for workshop_name, brand_levels in BRAND_EXPERTISE.items():
            workshop = workshop_map.get(workshop_name)
            if not workshop:
                continue

            for (marca_nombre, nivel) in brand_levels:
                try:
                    marca = Marca.objects.get(nombre=marca_nombre)
                except Marca.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'    ⚠ Marca "{marca_nombre}" no encontrada — omitida')
                    )
                    continue

                _, created = WorkshopVehicleExpertise.objects.get_or_create(
                    workshop=workshop,
                    marca=marca,
                    modelo=None,
                    defaults={
                        'expertise_level': nivel,
                        'total_jobs': rng.randint(20, 200),
                        'last_job_date': date.today() - timedelta(days=rng.randint(1, 60)),
                    },
                )
                if created:
                    exp_count += 1

        # Expertise por modelo (nivel 2)
        MODEL_EXPERTISE = {
            'Mecánica Ávila SAC':        [('Corolla',      'Toyota', 'expert')],
            'AutoTech Service':          [('Hilux',        'Toyota', 'pro')],
            'Motores y Más EIRL':        [('Land Cruiser', 'Toyota', 'expert')],
            'TechCar Premium':           [('Serie 3',      'BMW',    'expert')],
        }

        for workshop_name, model_levels in MODEL_EXPERTISE.items():
            workshop = workshop_map.get(workshop_name)
            if not workshop:
                continue

            for (modelo_nombre, marca_nombre, nivel) in model_levels:
                try:
                    marca = Marca.objects.get(nombre=marca_nombre)
                    modelo = ModeloVehiculo.objects.get(nombre=modelo_nombre, marca=marca)
                except (Marca.DoesNotExist, ModeloVehiculo.DoesNotExist):
                    self.stdout.write(
                        self.style.WARNING(
                            f'    ⚠ Modelo "{marca_nombre} {modelo_nombre}" no encontrado — omitido'
                        )
                    )
                    continue

                _, created = WorkshopVehicleExpertise.objects.get_or_create(
                    workshop=workshop,
                    marca=None,
                    modelo=modelo,
                    defaults={
                        'expertise_level': nivel,
                        'total_jobs': rng.randint(40, 300),
                        'last_job_date': date.today() - timedelta(days=rng.randint(1, 30)),
                    },
                )
                if created:
                    exp_count += 1

        self.stdout.write(self.style.SUCCESS(f'  → {exp_count} registros de expertise vehicular\n'))

        # ── Resumen ────────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            '\n✅ Seed completado:\n'
            f'   Categorías      : {ServiceCategory.objects.count()}\n'
            f'   Servicios       : {Service.objects.count()}\n'
            f'   Talleres        : {Workshop.objects.count()}\n'
            f'   Ubicaciones     : {WorkshopLocation.objects.count()}\n'
            f'   WS asignados    : {WorkshopService.objects.count()}\n'
            f'   Horarios        : {WorkshopSchedule.objects.count()}\n'
            f'   Historial       : {WorkshopServiceHistory.objects.count()}\n'
            f'   Expertise veh.  : {WorkshopVehicleExpertise.objects.count()}\n'
        ))
