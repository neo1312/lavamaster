from django.db import models


class Customer(models.Model):
    name = models.CharField('Nombre', max_length=150)
    phone = models.CharField('Teléfono', max_length=20, blank=True)
    email = models.EmailField('Correo', blank=True)
    rfc = models.CharField('RFC', max_length=20, blank=True)
    notes = models.TextField('Notas', blank=True)
    blacklisted = models.BooleanField('Bloqueado', default=False)
    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ('name',)

    def __str__(self):
        return self.name

    @property
    def has_balance(self):
        return any(o.balance_due > 0 for o in self.orders.filter(status__in=('received', 'ready_to_wash', 'on_wash', 'ready_to_delivery')))

    @property
    def active_orders(self):
        return self.orders.exclude(status__in=('delivered', 'completed'))
