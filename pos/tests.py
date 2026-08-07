from decimal import Decimal

from django.test import TestCase

from accounts.models import User
from pricing.models import ServiceCategory, ServiceType


class PosCreateOrderTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            'admin', 'admin@test.local', 'pass', role=User.Role.ADMIN
        )
        self.client.force_login(self.admin)

        self.cat = ServiceCategory.objects.create(name='Lavado general', emoji='🧺')
        self.t1 = ServiceType.objects.create(
            name='Lavado general', category=self.cat, unit='kg',
            min_weight_kg='0.50', max_weight_kg='5.00', rate_per_kg='25.00',
        )
        self.t2 = ServiceType.objects.create(
            name='Lavado general', category=self.cat, unit='kg',
            min_weight_kg='5.00', max_weight_kg='10.00', rate_per_kg='22.00',
        )
        self.camisa = ServiceType.objects.create(
            name='Camisa', unit='piece', rate_per_kg='25.00'
        )

    def test_create_order_with_piece_and_tier_lines(self):
        response = self.client.post('/pos/', {
            'customer_name': 'Carlos Ruiz',
            'service_type': [str(self.camisa.pk), str(self.t1.pk)],
            'weight': ['3', '7.5'],
            'payment_amount': '0.00',
            'payment_method': 'cash',
        })
        self.assertEqual(response.status_code, 302)

        from orders.models import Order, OrderLine
        order = Order.objects.latest('id')
        lines = {l.service_type_id: l for l in order.lines.all()}
        self.assertEqual(lines[self.camisa.pk].unit, 'piece')
        self.assertEqual(lines[self.camisa.pk].quantity, 3)
        self.assertEqual(lines[self.t2.pk].unit, 'kg')
        self.assertEqual(lines[self.t2.pk].weight_kg, Decimal('7.50'))
        self.assertEqual(lines[self.t2.pk].rate_per_kg, Decimal('22.00'))
        self.assertEqual(order.total_weight_kg, Decimal('7.50'))
        self.assertEqual(order.subtotal, Decimal('240.00'))

    def test_invalid_quantity_ignored(self):
        from orders.models import Order
        self.client.post('/pos/', {
            'customer_name': 'Carlos Ruiz',
            'service_type': [str(self.camisa.pk)],
            'weight': ['2.5'],
            'payment_amount': '0.00',
            'payment_method': 'cash',
        })
        self.assertFalse(Order.objects.exists())

    def test_pos_home_groups_tier_services(self):
        response = self.client.get('/pos/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<option value="1">Lavado general</option>')
        self.assertContains(response, 'Camisa · $25.00/pieza')
        self.assertNotContains(response, 'Lavado general 0.50–5.00 kg')
        self.assertNotContains(response, 'desde $')

    def test_tier_map_covers_rep_and_bands(self):
        from pos.views import _build_service_options
        data = _build_service_options()
        for pk, bands in data['tier_map'].items():
            self.assertIn(int(pk), {b['pk'] for b in bands})
            self.assertGreaterEqual(len(bands), 2)

    def test_orders_list_page(self):
        from orders.models import Order, OrderLine
        self.client.post('/pos/', {
            'customer_name': 'Lista Test',
            'service_type': [str(self.camisa.pk)],
            'weight': ['2'],
            'payment_amount': '0.00', 'payment_method': 'cash',
        })
        response = self.client.get('/pos/orders/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Órdenes')
        self.assertContains(response, 'Lista Test')
        self.assertContains(response, 'Todos')
        OrderLine.objects.filter(order__customer__name='Lista Test').delete()
        Order.objects.filter(customer__name='Lista Test').delete()

    def test_orders_list_visible_for_cashier(self):
        cashier = User.objects.create_user(
            'caja2', password='pass', role=User.Role.CASHIER
        )
        self.client.force_login(cashier)
        self.assertEqual(self.client.get('/pos/orders/').status_code, 200)

    def test_pos_home_has_no_orders_table(self):
        response = self.client.get('/pos/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Órdenes</h2>')
        self.assertNotContains(response, 'date=today')
