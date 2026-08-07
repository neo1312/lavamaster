from django.core.management.base import BaseCommand

from pricing.models import ServiceCategory, ServiceType

CATALOG = [
    {
        'category': ('Lavado general', '🧺', 10),
        'services': [
            {'name': 'Lavado general', 'unit': 'kg', 'min': '0.50', 'max': '5.00', 'rate': '25.00', 'days': 1},
            {'name': 'Lavado general', 'unit': 'kg', 'min': '5.00', 'max': '10.00', 'rate': '22.00', 'days': 1},
            {'name': 'Lavado general', 'unit': 'kg', 'min': '10.00', 'max': None, 'rate': '18.00', 'days': 1},
        ],
    },
    {
        'category': ('Planchado', '👔', 20),
        'services': [
            {'name': 'Camisa', 'unit': 'piece', 'rate': '25.00', 'days': 1},
            {'name': 'Pantalón', 'unit': 'piece', 'rate': '30.00', 'days': 1},
            {'name': 'Blusa', 'unit': 'piece', 'rate': '25.00', 'days': 1},
            {'name': 'Falda', 'unit': 'piece', 'rate': '25.00', 'days': 1},
            {'name': 'Vestido', 'unit': 'piece', 'rate': '45.00', 'days': 1},
            {'name': 'Suéter', 'unit': 'piece', 'rate': '35.00', 'days': 1},
            {'name': 'Chamarra', 'unit': 'piece', 'rate': '60.00', 'days': 1},
            {'name': 'Short', 'unit': 'piece', 'rate': '20.00', 'days': 1},
            {'name': 'Juego de sábanas', 'unit': 'piece', 'rate': '80.00', 'days': 1},
            {'name': 'Cortinas', 'unit': 'piece', 'rate': '120.00', 'days': 1},
        ],
    },
    {
        'category': ('Blancos', '🤍', 30),
        'services': [
            {'name': 'Ropa blanca', 'unit': 'kg', 'rate': '30.00', 'days': 1},
            {'name': 'Toallas blancas', 'unit': 'kg', 'rate': '28.00', 'days': 1},
            {'name': 'Sábanas blancas', 'unit': 'kg', 'rate': '35.00', 'days': 1},
            {'name': 'Mantelería', 'unit': 'kg', 'rate': '40.00', 'days': 1},
        ],
    },
    {
        'category': ('Cobijas y edredones', '🛏️', 40),
        'services': [
            {'name': 'Cobija sencilla', 'unit': 'piece', 'rate': '60.00', 'days': 2},
            {'name': 'Cobija matrimonial', 'unit': 'piece', 'rate': '80.00', 'days': 2},
            {'name': 'Edredón', 'unit': 'piece', 'rate': '120.00', 'days': 2},
            {'name': 'Colcha', 'unit': 'piece', 'rate': '90.00', 'days': 2},
            {'name': 'Almohada', 'unit': 'piece', 'rate': '30.00', 'days': 1},
        ],
    },
    {
        'category': ('Otros artículos', '🧦', 50),
        'services': [
            {'name': 'Toalla pequeña', 'unit': 'piece', 'rate': '15.00', 'days': 1},
            {'name': 'Toalla mediana', 'unit': 'piece', 'rate': '20.00', 'days': 1},
            {'name': 'Toalla grande', 'unit': 'piece', 'rate': '30.00', 'days': 1},
            {'name': 'Bata de baño', 'unit': 'piece', 'rate': '50.00', 'days': 1},
            {'name': 'Uniforme', 'unit': 'piece', 'rate': '40.00', 'days': 1},
            {'name': 'Mandil', 'unit': 'piece', 'rate': '25.00', 'days': 1},
            {'name': 'Playera', 'unit': 'piece', 'rate': '20.00', 'days': 1},
            {'name': 'Sudadera', 'unit': 'piece', 'rate': '45.00', 'days': 1},
            {'name': 'Jeans', 'unit': 'piece', 'rate': '40.00', 'days': 1},
            {'name': 'Ropa interior (x3)', 'unit': 'piece', 'rate': '25.00', 'days': 1},
        ],
    },
]

LEGACY_NAMES = [
    'Ropa normal', 'Ropa de trabajo', 'Toallas', 'Cobijas y edredones',
    'Ropa delicada', 'Planchado',
]


class Command(BaseCommand):
    help = 'Crea categorías y tarifas base (ajustables desde la UI).'

    def handle(self, *args, **options):
        categories_created = 0
        services_created = 0
        for entry in CATALOG:
            cat_name, emoji, order = entry['category']
            category, created = ServiceCategory.objects.get_or_create(
                name=cat_name, defaults={'emoji': emoji, 'sort_order': order},
            )
            categories_created += int(created)
            for i, data in enumerate(entry['services']):
                _, was_created = ServiceType.objects.get_or_create(
                    name=data['name'],
                    category=category,
                    min_weight_kg=data.get('min'),
                    max_weight_kg=data.get('max'),
                    defaults={
                        'unit': data['unit'],
                        'rate_per_kg': data['rate'],
                        'estimated_days': data.get('days', 1),
                        'sort_order': i,
                        'active': True,
                    },
                )
                services_created += int(was_created)
        deactivated = (
            ServiceType.objects.filter(name__in=LEGACY_NAMES)
            .exclude(active=False).update(active=False)
        )
        self.stdout.write(self.style.SUCCESS(
            f'{categories_created} categorías, {services_created} tarifas creadas, '
            f'{deactivated} tarifas legadas desactivadas.'
        ))
