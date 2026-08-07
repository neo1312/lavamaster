from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import User
from customers.models import Customer
from pricing.models import ServiceCategory, ServiceType


def _parse_decimal(raw, min_value=None):
    raw = str(raw or '').strip().replace(',', '.')
    if not raw:
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    if min_value is not None and value < min_value:
        return None
    return value

MODULES = [
    {
        'title': 'POS',
        'emoji': '🛒',
        'sub': 'Cobrar y recibir órdenes',
        'url': 'pos_home',
        'cls': 'm-pos',
    },
    {
        'title': 'Recepcionistas',
        'emoji': '👥',
        'sub': 'Usuarios del mostrador',
        'url': 'erp_receptionists',
        'cls': 'm-users',
    },
    {
        'title': 'Tarifas',
        'emoji': '💲',
        'sub': 'Tipos de servicio y precio/kg',
        'url': 'erp_service_types',
        'cls': 'm-pricing',
    },
    {
        'title': 'Clientes',
        'emoji': '📇',
        'sub': 'Directorio de clientes',
        'url': 'erp_customers',
        'cls': 'm-customers',
    },
    {
        'title': 'Reportes',
        'emoji': '📊',
        'sub': 'Próximamente',
        'url': None,
        'cls': 'm-reports',
    },
]


@login_required
def home(request):
    if request.user.is_superuser or request.user.role == User.Role.ADMIN:
        return redirect('dashboard')
    return redirect('pos_home')


@login_required
def dashboard(request):
    if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
        return redirect('pos_home')
    return render(request, 'erp/dashboard.html', {
        'modules': MODULES,
        'receptionists_count': User.objects.filter(role=User.Role.CASHIER).count(),
        'customers_count': Customer.objects.count(),
        'service_types_count': ServiceType.objects.count(),
        'active_page': 'dashboard',
    })


@login_required
@require_http_methods(['GET', 'POST'])
def receptionists(request):
    if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
        return redirect('pos_home')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            username = request.POST.get('username', '').strip()
            full_name = request.POST.get('full_name', '').strip()
            password = request.POST.get('password', '')
            if not username or not password:
                messages.error(request, 'Usuario y contraseña son obligatorios.')
            elif User.objects.filter(username=username).exists():
                messages.error(request, 'Ese usuario ya existe.')
            else:
                User.objects.create_user(
                    username=username, password=password,
                    first_name=full_name, role=User.Role.CASHIER,
                )
                messages.success(request, f'Recepcionista {username} creado 🎉')
        elif action == 'toggle':
            user = get_object_or_404(User, pk=request.POST.get('user_id'))
            user.is_active = not user.is_active
            user.save()
            messages.success(
                request,
                f'{user.username} {"activado" if user.is_active else "desactivado"}.',
            )
        elif action == 'reset_password':
            user = get_object_or_404(User, pk=request.POST.get('user_id'))
            new_password = request.POST.get('password', '')
            if not new_password:
                messages.error(request, 'Ingresa una nueva contraseña.')
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, f'Contraseña de {user.username} actualizada.')
        elif action == 'edit':
            user = get_object_or_404(User, pk=request.POST.get('user_id'))
            user.first_name = request.POST.get('full_name', '').strip()
            user.save()
            messages.success(request, 'Cambios guardados.')
        return redirect('erp_receptionists')

    return render(request, 'erp/receptionists.html', {
        'receptionists': User.objects.filter(role=User.Role.CASHIER).order_by('username'),
        'active_page': 'erp',
    })


@login_required
@require_http_methods(['GET', 'POST'])
def service_types(request):
    if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
        return redirect('pos_home')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            name = request.POST.get('name', '').strip()
            unit = request.POST.get('unit', 'kg')
            rate = _parse_decimal(request.POST.get('rate_per_kg'), min_value=Decimal('0.01'))
            days_raw = request.POST.get('estimated_days', '1').strip()
            try:
                days_int = int(days_raw)
            except ValueError:
                days_int = None
            if not name or rate is None or days_int is None or unit not in ('kg', 'piece'):
                messages.error(request, 'Revisa los datos: nombre, tarifa y días son obligatorios.')
            else:
                category = None
                category_id = request.POST.get('category', '') or None
                if category_id:
                    category = ServiceCategory.objects.filter(pk=category_id).first()
                new_category = request.POST.get('new_category_name', '').strip()
                if new_category:
                    category, _ = ServiceCategory.objects.get_or_create(
                        name__iexact=new_category,
                        defaults={'name': new_category, 'emoji': request.POST.get('new_category_emoji', '').strip()},
                    )
                ServiceType.objects.create(
                    name=name, category=category, unit=unit,
                    min_weight_kg=(
                        _parse_decimal(request.POST.get('min_weight_kg'))
                        if unit == 'kg' else None
                    ),
                    max_weight_kg=(
                        _parse_decimal(request.POST.get('max_weight_kg'))
                        if unit == 'kg' else None
                    ),
                    rate_per_kg=rate, estimated_days=days_int,
                )
                messages.success(request, f'Tarifa {name} creada 💲')
        elif action == 'update':
            st = get_object_or_404(ServiceType, pk=request.POST.get('id'))
            st.name = request.POST.get('name', st.name).strip()
            unit = request.POST.get('unit', st.unit)
            if unit in ('kg', 'piece'):
                st.unit = unit
            category_id = request.POST.get('category', '') or None
            st.category = (
                ServiceCategory.objects.filter(pk=category_id).first()
                if category_id else None
            )
            rate = _parse_decimal(request.POST.get('rate_per_kg'), min_value=Decimal('0.01'))
            if rate is not None:
                st.rate_per_kg = rate
            days_raw = request.POST.get('estimated_days', '').strip()
            if days_raw.isdigit() and int(days_raw) > 0:
                st.estimated_days = int(days_raw)
            if st.unit == 'kg':
                st.min_weight_kg = _parse_decimal(request.POST.get('min_weight_kg'))
                st.max_weight_kg = _parse_decimal(request.POST.get('max_weight_kg'))
            else:
                st.min_weight_kg = None
                st.max_weight_kg = None
            st.active = 'active' in request.POST
            st.save()
            messages.success(request, 'Tarifa actualizada.')
        elif action == 'delete':
            st = get_object_or_404(ServiceType, pk=request.POST.get('id'))
            try:
                st.delete()
                messages.success(request, 'Tarifa eliminada.')
            except ProtectedError:
                messages.error(
                    request,
                    f"No se puede eliminar «{st.name}»: se usa en órdenes. Desactívala en su lugar.",
                )
        elif action == 'category_create':
            name = request.POST.get('name', '').strip()
            if not name:
                messages.error(request, 'El nombre de la categoría es obligatorio.')
            elif ServiceCategory.objects.filter(name__iexact=name).exists():
                messages.error(request, 'Ya existe una categoría con ese nombre.')
            else:
                ServiceCategory.objects.create(
                    name=name, emoji=request.POST.get('emoji', '').strip(),
                )
                messages.success(request, f'Categoría {name} creada 🏷️')
        elif action == 'category_update':
            cat = get_object_or_404(ServiceCategory, pk=request.POST.get('id'))
            name = request.POST.get('name', '').strip()
            if name:
                cat.name = name
            cat.emoji = request.POST.get('emoji', '').strip()
            cat.save()
            messages.success(request, 'Categoría actualizada.')
        elif action == 'category_delete':
            cat = get_object_or_404(ServiceCategory, pk=request.POST.get('id'))
            cat.delete()
            messages.success(
                request, 'Categoría eliminada (sus tarifas quedan sin categoría).'
            )
        return redirect('erp_service_types')

    categories = []
    for cat in ServiceCategory.objects.order_by('sort_order', 'name'):
        categories.append((
            cat,
            ServiceType.objects.filter(category=cat).order_by('sort_order', 'name'),
        ))
    uncategorized = ServiceType.objects.filter(
        category__isnull=True
    ).order_by('sort_order', 'name')

    return render(request, 'erp/service_types.html', {
        'categories': categories,
        'uncategorized': uncategorized,
        'category_list': ServiceCategory.objects.order_by('sort_order', 'name'),
        'active_page': 'erp',
    })


@login_required
@require_http_methods(['GET', 'POST'])
def customers(request):
    if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
        return redirect('pos_home')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            name = request.POST.get('name', '').strip()
            if not name:
                messages.error(request, 'El nombre es obligatorio.')
            else:
                Customer.objects.create(
                    name=name,
                    phone=request.POST.get('phone', '').strip(),
                    email=request.POST.get('email', '').strip(),
                    rfc=request.POST.get('rfc', '').strip(),
                )
                messages.success(request, f'Cliente {name} creado 📇')
        elif action == 'update':
            customer = get_object_or_404(Customer, pk=request.POST.get('id'))
            customer.name = request.POST.get('name', customer.name).strip()
            customer.phone = request.POST.get('phone', customer.phone).strip()
            customer.email = request.POST.get('email', customer.email).strip()
            customer.rfc = request.POST.get('rfc', customer.rfc).strip()
            customer.blacklisted = 'blacklisted' in request.POST
            customer.save()
            messages.success(request, 'Cliente actualizado.')
        elif action == 'delete':
            customer = get_object_or_404(Customer, pk=request.POST.get('id'))
            customer.delete()
            messages.success(request, 'Cliente eliminado.')
        return redirect('erp_customers')

    query = request.GET.get('q', '').strip()
    customers_qs = Customer.objects.order_by('name')
    if query:
        customers_qs = customers_qs.filter(
            name__icontains=query
        ) | customers_qs.filter(phone__icontains=query)

    return render(request, 'erp/customers.html', {
        'customers': customers_qs,
        'query': query,
        'active_page': 'erp',
    })
