from django.db import models


class ServiceType(models.Model):
    name = models.CharField('Nombre', max_length=100)
    description = models.TextField('Descripción', blank=True)
    rate_per_kg = models.DecimalField(
        'Tarifa por kg', max_digits=10, decimal_places=2
    )
    estimated_days = models.PositiveSmallIntegerField('Días estimados', default=1)
    active = models.BooleanField('Activo', default=True)
    sort_order = models.PositiveSmallIntegerField('Orden', default=0)
    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Tipo de servicio'
        verbose_name_plural = 'Tipos de servicio'
        ordering = ('sort_order', 'name')

    def __str__(self):
        return f'{self.name} (${self.rate_per_kg}/kg)'
