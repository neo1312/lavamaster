from django.test import TestCase

from accounts.models import User
from pricing.models import ServiceCategory, ServiceType


class ErpServiceTypesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            'admin', 'admin@test.local', 'pass', role=User.Role.ADMIN
        )
        self.client.force_login(self.admin)

    def test_create_category_and_service(self):
        self.client.post('/erp/service-types/', {
            'action': 'category_create', 'name': 'Planchado', 'emoji': '👔',
        })
        cat = ServiceCategory.objects.get(name='Planchado')
        self.assertEqual(cat.emoji, '👔')

        self.client.post('/erp/service-types/', {
            'action': 'create',
            'name': 'Camisa', 'category': str(cat.pk), 'unit': 'piece',
            'rate_per_kg': '25.00', 'estimated_days': '1',
        })
        st = ServiceType.objects.get(name='Camisa')
        self.assertEqual(st.category, cat)
        self.assertEqual(st.unit, 'piece')

    def test_create_tiered_service(self):
        self.client.post('/erp/service-types/', {
            'action': 'create',
            'name': 'Lavado general', 'category': '', 'unit': 'kg',
            'min_weight_kg': '0.50', 'max_weight_kg': '5.00',
            'rate_per_kg': '25.00', 'estimated_days': '1',
        })
        st = ServiceType.objects.get(name='Lavado general')
        self.assertEqual(st.min_weight_kg, 0.50)
        self.assertEqual(st.max_weight_kg, 5.00)

    def test_inline_category_and_unit_update(self):
        cat = ServiceCategory.objects.create(name='Blancos', emoji='🤍')
        st = ServiceType.objects.create(name='Ropa blanca', rate_per_kg='30.00')
        self.client.post('/erp/service-types/', {
            'action': 'update', 'id': str(st.pk),
            'name': 'Ropa blanca', 'category': str(cat.pk), 'unit': 'piece',
            'rate_per_kg': '35.00', 'estimated_days': '2', 'active': 'on',
        })
        st.refresh_from_db()
        self.assertEqual(st.category, cat)
        self.assertEqual(st.unit, 'piece')
        self.assertEqual(float(st.rate_per_kg), 35.00)

    def test_service_types_page_renders_grouped(self):
        cat = ServiceCategory.objects.create(name='Planchado', emoji='👔')
        ServiceType.objects.create(name='Camisa', category=cat, unit='piece', rate_per_kg='25.00')
        ServiceType.objects.create(name='Toallas', rate_per_kg='28.00')
        response = self.client.get('/erp/service-types/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Planchado')
        self.assertContains(response, 'Camisa')
        self.assertContains(response, 'Sin categoría')
