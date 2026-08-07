from decimal import Decimal

from django.db import models


class ServiceCategory(models.Model):
    name = models.CharField('Nombre', max_length=100, unique=True)
    emoji = models.CharField('Emoji', max_length=8, blank=True)
    sort_order = models.PositiveSmallIntegerField('Orden', default=0)
    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Categoría de servicio'
        verbose_name_plural = 'Categorías de servicio'
        ordering = ('sort_order', 'name')

    def __str__(self):
        return f'{self.emoji} {self.name}'.strip()


class ServiceType(models.Model):
    class Unit(models.TextChoices):
        KG = 'kg', 'Por kg'
        PIECE = 'piece', 'Por pieza'

    name = models.CharField('Nombre', max_length=100)
    description = models.TextField('Descripción', blank=True)
    category = models.ForeignKey(
        ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='services', verbose_name='Categoría',
    )
    unit = models.CharField(
        'Unidad', max_length=10, choices=Unit.choices, default=Unit.KG,
    )
    min_weight_kg = models.DecimalField(
        'Peso mínimo (kg)', max_digits=8, decimal_places=2, null=True, blank=True,
    )
    max_weight_kg = models.DecimalField(
        'Peso máximo (kg)', max_digits=8, decimal_places=2, null=True, blank=True,
    )
    rate_per_kg = models.DecimalField(
        'Tarifa por kg/pieza', max_digits=10, decimal_places=2,
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
        unit_label = 'kg' if self.unit == self.Unit.KG else 'pieza'
        return f'{self.name} (${self.rate_per_kg}/{unit_label})'

    @property
    def unit_display_short(self):
        return 'kg' if self.unit == self.Unit.KG else 'pieza'

    @property
    def is_tier(self):
        return self.unit == self.Unit.KG and (
            self.min_weight_kg is not None or self.max_weight_kg is not None
        )

    def resolve_for(self, weight):
        """Devuelve la fila (rango) aplicable a un peso dado.

        Las tarifas por rango comparten name + category; cada fila es un
        tramo con min/max. Las filas sin rango son servicios simples.
        Si el peso no cae en ningún tramo (p. ej. debajo del mínimo), se
        resuelve al rango más cercano para cobrar la porción proporcional.
        """
        weight = Decimal(weight)
        if not self.is_tier:
            return self
        bands = list(
            ServiceType.objects.filter(
                active=True, name=self.name, category_id=self.category_id,
            ).order_by('min_weight_kg', 'pk')
        )
        for candidate in bands:
            mn = candidate.min_weight_kg
            mx = candidate.max_weight_kg
            if mn is not None and weight < Decimal(mn):
                continue
            if mx is not None and weight > Decimal(mx):
                continue
            if mn is not None or mx is not None:
                return candidate
        if not bands:
            return self
        if bands[0].min_weight_kg is not None and weight < Decimal(bands[0].min_weight_kg):
            return bands[0]
        if bands[-1].max_weight_kg is not None and weight > Decimal(bands[-1].max_weight_kg):
            return bands[-1]
        return self

    def effective_rate(self, weight):
        return Decimal(self.resolve_for(weight).rate_per_kg)
