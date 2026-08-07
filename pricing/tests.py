from decimal import Decimal

from django.test import TestCase

from pricing.models import ServiceCategory, ServiceType


class ServiceCategoryTests(TestCase):
    def test_category_creation(self):
        cat = ServiceCategory.objects.create(name='Planchado', emoji='👔')
        st = ServiceType.objects.create(
            name='Camisa', category=cat, unit='piece', rate_per_kg='25.00'
        )
        self.assertEqual(st.category, cat)
        self.assertEqual(st.unit, ServiceType.Unit.PIECE)

    def test_delete_category_keeps_services(self):
        cat = ServiceCategory.objects.create(name='Planchado', emoji='👔')
        st = ServiceType.objects.create(name='Camisa', category=cat, rate_per_kg='25.00')
        cat.delete()
        st.refresh_from_db()
        self.assertIsNone(st.category)


class TieredPricingTests(TestCase):
    def setUp(self):
        self.cat = ServiceCategory.objects.create(name='Lavado general', emoji='🧺')
        self.t1 = ServiceType.objects.create(
            name='Lavado general', category=self.cat, unit='kg',
            min_weight_kg='0.50', max_weight_kg='5.00', rate_per_kg='25.00',
        )
        self.t2 = ServiceType.objects.create(
            name='Lavado general', category=self.cat, unit='kg',
            min_weight_kg='5.00', max_weight_kg='10.00', rate_per_kg='22.00',
        )
        self.t3 = ServiceType.objects.create(
            name='Lavado general', category=self.cat, unit='kg',
            min_weight_kg='10.00', max_weight_kg=None, rate_per_kg='18.00',
        )

    def test_resolve_band_by_weight(self):
        self.assertEqual(self.t1.resolve_for('3.00').pk, self.t1.pk)
        self.assertEqual(self.t1.resolve_for('5.00').pk, self.t1.pk)
        self.assertEqual(self.t1.resolve_for('7.50').pk, self.t2.pk)
        self.assertEqual(self.t1.resolve_for('15.00').pk, self.t3.pk)

    def test_effective_rate(self):
        self.assertEqual(self.t1.effective_rate('3.00'), Decimal('25.00'))
        self.assertEqual(self.t1.effective_rate('7.50'), Decimal('22.00'))
        self.assertEqual(self.t1.effective_rate('15.00'), Decimal('18.00'))

    def test_plain_service_has_no_tier(self):
        plain = ServiceType.objects.create(name='Toallas', rate_per_kg='28.00')
        self.assertFalse(plain.is_tier)
        self.assertEqual(plain.resolve_for('4.00').pk, plain.pk)
