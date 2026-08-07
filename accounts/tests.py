from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from customers.models import Customer
from orders.models import Order, OrderLine, Payment
from pricing.models import ServiceType


class RoleAccessTests(TestCase):
    def setUp(self):
        self.cashier = User.objects.create_user(
            username='cajero', password='pass', role=User.Role.CASHIER
        )
        self.admin = User.objects.create_user(
            username='admin2', password='pass', role=User.Role.ADMIN
        )
        self.service = ServiceType.objects.create(
            name='Ropa normal', rate_per_kg='25.00'
        )
        self.customer = Customer.objects.create(name='Ana', phone='555')
        self.order = Order.objects.create(
            customer=self.customer, received_by=self.cashier
        )
        OrderLine.objects.create(
            order=self.order, service_type=self.service, weight_kg='2.00'
        )
        self.order.refresh_totals()

    def test_cashier_can_access_pos(self):
        self.client.force_login(self.cashier)
        self.assertEqual(self.client.get('/pos/').status_code, 200)
        self.assertEqual(self.client.get(f'/pos/orders/{self.order.pk}/').status_code, 200)

    def test_cashier_redirected_to_pos_from_home(self):
        self.client.force_login(self.cashier)
        response = self.client.get('/')
        self.assertRedirects(response, '/pos/')

    def test_admin_redirected_to_dashboard_from_home(self):
        self.client.force_login(self.admin)
        response = self.client.get('/')
        self.assertRedirects(response, '/dashboard/')

    def test_cashier_blocked_from_erp(self):
        self.client.force_login(self.cashier)
        response = self.client.get('/erp/receptionists/')
        self.assertRedirects(response, '/pos/')
        self.assertEqual(self.client.get('/dashboard/').status_code, 302)

    def test_admin_can_access_erp(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/dashboard/').status_code, 200)
        self.assertEqual(self.client.get('/erp/receptionists/').status_code, 200)
        self.assertEqual(self.client.get('/erp/service-types/').status_code, 200)
        self.assertEqual(self.client.get('/erp/customers/').status_code, 200)

    def test_cashier_can_transition_status_via_api(self):
        api = APIClient()
        api.force_authenticate(self.cashier)
        response = api.post(
            f'/api/orders/{self.order.pk}/status/',
            {'status': Order.Status.READY_TO_WASH},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.READY_TO_WASH)

    def test_cashier_can_add_payment_via_api(self):
        api = APIClient()
        api.force_authenticate(self.cashier)
        response = api.post(
            f'/api/orders/{self.order.pk}/payments/',
            {'amount': '50.00', 'method': 'cash'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Payment.objects.count(), 1)

    def test_cashier_cannot_manage_service_types(self):
        api = APIClient()
        api.force_authenticate(self.cashier)
        response = api.post(
            '/api/service-types/',
            {'name': 'X', 'rate_per_kg': '10.00'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_manage_service_types(self):
        api = APIClient()
        api.force_authenticate(self.admin)
        response = api.post(
            '/api/service-types/',
            {'name': 'Alfombras', 'rate_per_kg': '80.00'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)

    def test_orders_list_filters_by_status_and_date(self):
        self.client.force_login(self.cashier)
        self.assertEqual(self.client.get('/pos/orders/?status=on_wash').status_code, 200)
        self.assertEqual(self.client.get('/pos/orders/?date=all').status_code, 200)
        self.assertEqual(self.client.get('/pos/orders/?status=received&date=all').status_code, 200)
