from django.core.management.base import BaseCommand

from pricing.models import ServiceType

DEFAULT_SERVICES = [
    {'name': 'Ropa normal', 'rate': '25.00', 'days': 1},
    {'name': 'Ropa de trabajo', 'rate': '30.00', 'days': 1},
    {'name': 'Toallas', 'rate': '28.00', 'days': 1},
    {'name': 'Cobijas y edredones', 'rate': '45.00', 'days': 2},
    {'name': 'Ropa delicada', 'rate': '55.00', 'days': 2},
    {'name': 'Planchado', 'rate': '35.00', 'days': 1},
]


class Command(BaseCommand):
    help = 'Crea los tipos de servicio con tarifas por defecto (ajustables).'

    def handle(self, *args, **options):
        created = 0
        for i, data in enumerate(DEFAULT_SERVICES):
            _, was_created = ServiceType.objects.get_or_create(
                name=data['name'],
                defaults={
                    'rate_per_kg': data['rate'],
                    'estimated_days': data['days'],
                    'sort_order': i,
                },
            )
            created += int(was_created)
        self.stdout.write(
            self.style.SUCCESS(f'{created} tipos de servicio creados.')
        )
