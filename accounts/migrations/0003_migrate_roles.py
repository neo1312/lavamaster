from django.db import migrations


def migrate_roles(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role__in=('frontdesk', 'operator')).update(role='cashier')
    User.objects.filter(role='manager').update(role='admin')


def reverse_roles(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role='cashier').update(role='frontdesk')
    User.objects.filter(role='admin').update(role='manager')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_user_role'),
    ]

    operations = [
        migrations.RunPython(migrate_roles, reverse_roles),
    ]
