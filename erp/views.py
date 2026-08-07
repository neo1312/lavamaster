from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import User
from customers.models import Customer
from pricing.models import ServiceType

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
            rate = request.POST.get('rate_per_kg', '').strip().replace(',', '.')
            days = request.POST.get('estimated_days', '1').strip()
            try:
                rate_dec = float(rate)
                days_int = int(days)
            except ValueError:
                messages.error(request, 'Tarifa o días inválidos.')
                return redirect('erp_service_types')
            if not name or rate_dec <= 0:
                messages.error(request, 'Nombre y tarifa válida son obligatorios.')
            else:
                ServiceType.objects.create(
                    name=name, rate_per_kg=rate_dec, estimated_days=days_int,
                )
                messages.success(request, f'Servicio {name} creado 💲')
        elif action == 'update':
            st = get_object_or_404(ServiceType, pk=request.POST.get('id'))
            st.name = request.POST.get('name', st.name).strip()
            st.rate_per_kg = request.POST.get('rate_per_kg', st.rate_per_kg)
            st.estimated_days = request.POST.get('estimated_days', st.estimated_days)
            st.active = 'active' in request.POST
            st.save()
            messages.success(request, 'Tarifa actualizada.')
        elif action == 'delete':
            st = get_object_or_404(ServiceType, pk=request.POST.get('id'))
            st.delete()
            messages.success(request, 'Servicio eliminado.')
        return redirect('erp_service_types')

    return render(request, 'erp/service_types.html', {
        'service_types': ServiceType.objects.order_by('sort_order', 'name'),
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
