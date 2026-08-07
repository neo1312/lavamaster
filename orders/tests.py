from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from customers.models import Customer
from orders.models import Order, OrderLine, Payment
from pricing.models import ServiceType


class OrderFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='recep', password='pass', role=User.Role.CASHIER
        )
        self.customer = Customer.objects.create(name='Juan Pérez', phone='5551234567')
        self.ropa = ServiceType.objects.create(
            name='Ropa normal', rate_per_kg='25.00'
        )
        self.toallas = ServiceType.objects.create(
            name='Toallas', rate_per_kg='28.00'
        )

    def _create_order(self, **kwargs):
        order = Order.objects.create(customer=self.customer, **kwargs)
        OrderLine.objects.create(
            order=order, service_type=self.ropa, weight_kg='4.00'
        )
        OrderLine.objects.create(
            order=order, service_type=self.toallas, weight_kg='2.00'
        )
        order.refresh_totals()
        return order

    def test_sequential_ticket_numbers(self):
        o1 = self._create_order()
        o2 = self._create_order()
        self.assertEqual(o1.ticket_number, '000001')
        self.assertEqual(o2.ticket_number, '000002')
        self.assertEqual(o2.number, o1.number + 1)

    def test_totals_and_balance(self):
        order = self._create_order()
        self.assertEqual(order.total_weight_kg, Decimal('6.00'))
        self.assertEqual(order.subtotal, Decimal('156.00'))
        self.assertEqual(order.balance_due, Decimal('156.00'))

    def test_line_rate_snapshot_from_service_type(self):
        order = Order.objects.create(customer=self.customer)
        line = OrderLine.objects.create(
            order=order, service_type=self.ropa, weight_kg='1.00'
        )
        self.assertEqual(Decimal(line.rate_per_kg), Decimal('25.00'))
        self.assertEqual(line.subtotal, Decimal('25.00'))

    def test_payment_types(self):
        order = self._create_order()
        p1 = Payment.objects.create(
            order=order, amount='56.00', method=Payment.Method.CASH,
            received_by=self.user,
        )
        self.assertEqual(p1.payment_type, Payment.Type.ADVANCE)
        self.assertEqual(order.balance_due, Decimal('100.00'))
        p2 = Payment.objects.create(
            order=order, amount='100.00', method=Payment.Method.CARD,
            received_by=self.user,
        )
        self.assertEqual(p2.payment_type, Payment.Type.FINAL)
        self.assertEqual(order.balance_due, Decimal('0.00'))

    def test_payment_cannot_exceed_balance(self):
        order = self._create_order()
        with self.assertRaises(ValidationError):
            payment = Payment(order=order, amount='200.00', method=Payment.Method.CASH)
            payment.full_clean()

    def test_status_transitions(self):
        order = self._create_order()
        order.transition_status(Order.Status.READY_TO_WASH)
        self.assertEqual(order.status, Order.Status.READY_TO_WASH)
        with self.assertRaises(ValidationError):
            order.transition_status(Order.Status.READY_TO_DELIVERY)

    def test_cannot_deliver_with_balance(self):
        order = self._create_order()
        order.transition_status(Order.Status.READY_TO_WASH)
        order.transition_status(Order.Status.ON_WASH)
        order.transition_status(Order.Status.READY_TO_DELIVERY)
        with self.assertRaises(ValidationError):
            order.transition_status(Order.Status.DELIVERED)

    def test_deliver_and_complete_after_payment(self):
        order = self._create_order()
        Payment.objects.create(
            order=order, amount=order.subtotal, method=Payment.Method.CASH,
            received_by=self.user,
        )
        for status in (
            Order.Status.READY_TO_WASH,
            Order.Status.ON_WASH,
            Order.Status.READY_TO_DELIVERY,
            Order.Status.DELIVERED,
            Order.Status.COMPLETED,
        ):
            order.transition_status(status)
        self.assertEqual(order.status, Order.Status.COMPLETED)
        self.assertIsNotNone(order.completed_at)
