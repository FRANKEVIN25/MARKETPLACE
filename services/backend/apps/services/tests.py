from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.customer.models import Customer
from apps.vehicles.models import Marca
from .models import Service, ServiceCategory, Workshop


User = get_user_model()


class WorkshopProfileMeViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='taller1',
            email='taller1@example.com',
            password='secret123',
        )
        self.customer = Customer.objects.create(
            user=self.user,
            customer_type='company',
            company_name='Taller Norte',
            business_activity='workshop',
            document_type='RUC',
            document_number='20123456789',
            phone='999111222',
        )
        self.client.force_authenticate(self.user)
        self.url = '/api/v1/services/workshop-profile/me/'

    def test_get_creates_workshop_for_authenticated_company_workshop(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Workshop.objects.filter(owner=self.user).count(), 1)

        workshop = Workshop.objects.get(owner=self.user)
        self.assertEqual(response.data['id'], workshop.id)
        self.assertEqual(response.data['name'], 'Taller Norte')
        self.assertEqual(response.data['locations'], [])
        self.assertEqual(response.data['schedules'], [])

    def test_patch_updates_locations_and_schedules(self):
        self.client.get(self.url)

        payload = {
            'name': 'Taller Norte Premium',
            'phone': '999333444',
            'description': 'Atención rápida y transparente.',
            'large_description': 'Especialistas multimarca con sedes en Lima.',
            'locations': [
                {
                    'name': 'Sede Principal',
                    'address': 'Av. Los Talleres 123',
                    'district': 'San Luis',
                    'province': 'Lima',
                    'department': 'Lima',
                    'is_main': True,
                },
                {
                    'name': 'Sucursal Sur',
                    'address': 'Av. Primavera 456',
                    'district': 'Surco',
                    'province': 'Lima',
                    'department': 'Lima',
                    'is_main': False,
                },
            ],
            'schedules': [
                {
                    'day_of_week': 0,
                    'start_time': '08:00',
                    'end_time': '18:00',
                    'is_active': True,
                },
                {
                    'day_of_week': 6,
                    'start_time': '09:00',
                    'end_time': '13:00',
                    'is_active': True,
                },
            ],
        }

        response = self.client.patch(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        workshop = Workshop.objects.get(owner=self.user)
        self.assertEqual(workshop.name, 'Taller Norte Premium')
        self.assertEqual(workshop.phone, '999333444')
        self.assertEqual(workshop.locations.count(), 2)
        self.assertEqual(workshop.schedules.count(), 2)
        self.assertTrue(workshop.locations.filter(is_main=True, district='San Luis').exists())
        self.assertTrue(workshop.schedules.filter(day_of_week=0, start_time='08:00').exists())

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.company_name, 'Taller Norte Premium')
        self.assertEqual(self.customer.phone, '999333444')


class WorkshopCatalogMeViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='taller2',
            email='taller2@example.com',
            password='secret123',
        )
        self.customer = Customer.objects.create(
            user=self.user,
            customer_type='company',
            company_name='Taller Catálogo',
            business_activity='workshop',
            document_type='RUC',
            document_number='20999999991',
            phone='999888777',
        )
        self.category = ServiceCategory.objects.create(
            name='Frenos y Seguridad',
            description='Servicios de seguridad y frenado',
            order=1,
        )
        self.service = Service.objects.create(
            category=self.category,
            name='Cambio de pastillas',
            description='Cambio preventivo de pastillas delanteras',
            service_type='repair',
            complexity='medium',
        )
        self.marca = Marca.objects.create(nombre='Toyota')
        self.client.force_authenticate(self.user)
        self.url = '/api/v1/services/catalog/me/'

    def test_get_returns_categories_and_empty_configuration(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['categories']), 1)
        self.assertEqual(response.data['categories'][0]['services'][0]['name'], 'Cambio de pastillas')
        self.assertEqual(response.data['workshop_services'], [])
        self.assertEqual(response.data['vehicle_expertise'], [])

    def test_patch_persists_catalog_and_vehicle_expertise(self):
        Workshop.objects.create(
            owner=self.user,
            customer_profile=self.customer,
            name='Taller Catálogo',
            ruc='20999999991',
            phone='999888777',
        )

        payload = {
            'workshop_services': [
                {
                    'service': self.service.id,
                    'is_specialized': True,
                    'min_price': '120.00',
                    'max_price': '180.00',
                    'currency': 'PEN',
                    'estimated_time_min': 90,
                    'available': True,
                    'has_warranty': True,
                    'warranty_days': 30,
                }
            ],
            'vehicle_expertise': [
                {
                    'marca': self.marca.id,
                    'expertise_level': 'expert',
                    'notes': 'Alto volumen de trabajos Toyota.',
                }
            ],
        }

        response = self.client.patch(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        workshop = Workshop.objects.get(owner=self.user)
        self.assertEqual(workshop.workshop_services.count(), 1)
        self.assertEqual(workshop.vehicle_expertise.count(), 1)
        self.assertEqual(response.data['workshop_services'][0]['service_name'], 'Cambio de pastillas')
        self.assertEqual(response.data['vehicle_expertise'][0]['marca_nombre'], 'Toyota')
