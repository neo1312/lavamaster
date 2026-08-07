from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError

from customers.models import Customer
from pricing.models import ServiceType

STATUS_RECEIVED = 'received'
STATUS_READY_TO_WASH = 'ready_to_wash'
STATUS_ON_WASH = 'on_wash'
STATUS_READY_TO_DELIVERY = 'ready_to_delivery'
STATUS_DELIVERED = 'delivered'
STATUS_COMPLETED = 'completed'

ACTIVE_STATUSES = (
    STATUS_RECEIVED,
    STATUS_READY_TO_WASH,
    STATUS_ON_WASH,
    STATUS_READY_TO_DELIVERY,
)

PAYMENT_CASH = 'cash'
PAYMENT_CARD = 'card'

PAYMENT_ADVANCE = 'advance'
PAYMENT_PARTIAL = 'partial'
PAYMENT_FINAL = 'final'

ALLOWED_TRANSITIONS = {
    STATUS_RECEIVED: (STATUS_READY_TO_WASH,),
    STATUS_READY_TO_WASH: (STATUS_ON_WASH,),
    STATUS_ON_WASH: (STATUS_READY_TO_DELIVERY,),
    STATUS_READY_TO_DELIVERY: (STATUS_DELIVERED,),
    STATUS_DELIVERED: (STATUS_COMPLETED,),
    STATUS_COMPLETED: (),
}


class Order(models.Model):
    class Status(models.TextChoices):
        RECEIVED = STATUS_RECEIVED, 'Recibido'
        READY_TO_WASH = STATUS_READY_TO_WASH, 'Listo para lavar'
        ON_WASH = STATUS_ON_WASH, 'En lavado'
        READY_TO_DELIVERY = STATUS_READY_TO_DELIVERY, 'Listo para entrega'
        DELIVERED = STATUS_DELIVERED, 'Entregado'
        COMPLETED = STATUS_COMPLETED, 'Completado'

    number = models.PositiveIntegerField('Número de orden', unique=True, editable=False)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name='orders',
        verbose_name='Cliente',
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.RECEIVED,
        verbose_name='Estado',
    )
    total_weight_kg = models.DecimalField(
        'Peso total (kg)', max_digits=8, decimal_places=2, default=Decimal('0.00')
    )
    subtotal = models.DecimalField(
        'Subtotal', max_digits=12, decimal_places=2, default=Decimal('0.00'),
        editable=False,
    )
    promised_at = models.DateField('Fecha prometida', null=True, blank=True)
    notes = models.TextField('Notas', blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        blank=True, related_name='received_orders', verbose_name='Recibido por',
    )
    received_at = models.DateTimeField('Recibido', auto_now_add=True)
    delivered_at = models.DateTimeField('Entregado', null=True, blank=True)
    completed_at = models.DateTimeField('Completado', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Orden'
        verbose_name_plural = 'Órdenes'
        ordering = ('-number',)

    def __str__(self):
        return f'Orden #{self.number}'

    @property
    def ticket_number(self):
        return f'{self.number:06d}'

    def save(self, *args, **kwargs):
        if not self.number:
            with transaction.atomic():
                last = (
                    Order.objects.select_for_update()
                    .order_by('-number').first()
                )
                self.number = (last.number if last else 0) + 1
        super().save(*args, **kwargs)

    def clean(self):
        if self.status in (STATUS_DELIVERED, STATUS_COMPLETED) and self.balance_due > 0:
            raise ValidationError(
                'No se puede cerrar la orden con saldo pendiente.'
            )

    @property
    def paid(self):
        return sum(
            (Decimal(p.amount) for p in self.payments.all()), Decimal('0.00')
        )

    @property
    def balance_due(self):
        return self.subtotal - self.paid

    def refresh_totals(self):
        total_weight = sum(
            (Decimal(l.weight_kg) for l in self.lines.all()), Decimal('0.00')
        )
        subtotal = sum(
            (Decimal(l.subtotal) for l in self.lines.all()), Decimal('0.00')
        )
        self.total_weight_kg = total_weight
        self.subtotal = subtotal
        self.save(update_fields=['total_weight_kg', 'subtotal', 'updated_at'])

    def transition_status(self, new_status, user=None):
        if new_status == self.status:
            return
        if new_status not in ALLOWED_TRANSITIONS.get(self.status, ()):
            choices = dict(Order.Status.choices)
            raise ValidationError(
                f'Transición no permitida de {self.get_status_display()} '
                f'a {choices.get(new_status)}'
            )
        self.status = new_status
        if new_status in (STATUS_DELIVERED, STATUS_COMPLETED):
            if self.balance_due > 0:
                raise ValidationError(
                    'No se puede entregar una orden con saldo pendiente.'
                )
        if new_status == STATUS_DELIVERED:
            self.delivered_at = self.delivered_at or self.get_now()
        if new_status == STATUS_COMPLETED:
            self.completed_at = self.get_now()
        self.save()

    @staticmethod
    def get_now():
        from django.utils import timezone
        return timezone.now()


class OrderLine(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='lines',
        verbose_name='Orden',
    )
    service_type = models.ForeignKey(
        ServiceType, on_delete=models.PROTECT, verbose_name='Tipo de servicio'
    )
    unit = models.CharField(
        'Unidad', max_length=10, choices=ServiceType.Unit.choices,
        null=True, blank=True,
    )
    weight_kg = models.DecimalField(
        'Peso (kg)', max_digits=8, decimal_places=2, default=Decimal('0.00'),
        blank=True,
    )
    quantity = models.PositiveSmallIntegerField('Cantidad', default=1)
    rate_per_kg = models.DecimalField(
        'Tarifa por kg', max_digits=10, decimal_places=2
    )
    notes = models.CharField('Notas', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Línea de orden'
        verbose_name_plural = 'Líneas de orden'

    def __str__(self):
        if self.unit == ServiceType.Unit.PIECE:
            return f'{self.service_type.name} x{self.quantity}'
        return f'{self.service_type.name} - {self.weight_kg} kg'

    @property
    def subtotal(self):
        if self.unit == ServiceType.Unit.PIECE:
            return (
                Decimal(self.quantity) * Decimal(self.rate_per_kg)
            ).quantize(Decimal('0.01'))
        return (
            Decimal(self.weight_kg) * Decimal(self.rate_per_kg)
        ).quantize(Decimal('0.01'))

    def save(self, *args, **kwargs):
        if self._state.adding:
            if not self.rate_per_kg:
                self.rate_per_kg = self.service_type.rate_per_kg
            if not self.unit:
                self.unit = self.service_type.unit
        super().save(*args, **kwargs)


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = PAYMENT_CASH, 'Efectivo'
        CARD = PAYMENT_CARD, 'Tarjeta'

    class Type(models.TextChoices):
        ADVANCE = PAYMENT_ADVANCE, 'Anticipo'
        PARTIAL = PAYMENT_PARTIAL, 'Abono'
        FINAL = PAYMENT_FINAL, 'Liquidación'

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='payments',
        verbose_name='Orden',
    )
    amount = models.DecimalField(
        'Monto', max_digits=12, decimal_places=2
    )
    method = models.CharField(
        max_length=10, choices=Method.choices, verbose_name='Método'
    )
    payment_type = models.CharField(
        max_length=10, choices=Type.choices, verbose_name='Tipo'
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        blank=True, related_name='collected_payments', verbose_name='Recibido por',
    )
    reference = models.CharField('Referencia', max_length=100, blank=True)
    received_at = models.DateTimeField('Recibido', auto_now_add=True)

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ('received_at',)

    def __str__(self):
        return f'{self.get_payment_type_display()} {self.amount} ({self.get_method_display()})'

    def clean(self):
        amount = Decimal(self.amount)
        if amount <= 0:
            raise ValidationError('El monto debe ser mayor a cero.')
        if amount > Decimal(self.order.balance_due):
            raise ValidationError('El pago excede el saldo pendiente.')

    def save(self, *args, **kwargs):
        if not self.payment_type:
            amount = Decimal(self.amount)
            balance_before = Decimal(self.order.balance_due)
            if amount >= balance_before:
                self.payment_type = Payment.Type.FINAL
            elif self.order.payments.exists():
                self.payment_type = Payment.Type.PARTIAL
            else:
                self.payment_type = Payment.Type.ADVANCE
        super().save(*args, **kwargs)
        self.order.refresh_totals()
