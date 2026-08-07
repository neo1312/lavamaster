import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from customers.models import Customer
from orders.models import (
    Order,
    OrderLine,
    Payment,
    ACTIVE_STATUSES,
    ALLOWED_TRANSITIONS,
)
from pricing.models import ServiceCategory, ServiceType

STATUS_CHIPS = [
    ('', 'Todos', '📋'),
    ('received', 'Recibido', '📥'),
    ('ready_to_wash', 'Listo para lavar', '🧺'),
    ('on_wash', 'En lavado', '🫧'),
    ('ready_to_delivery', 'Listo para entrega', '📦'),
    ('delivered', 'Entregado', '✅'),
    ('completed', 'Completado', '✔️'),
]


def _parse_weight(raw):
    try:
        value = Decimal(str(raw).replace(',', '.'))
    except InvalidOperation:
        return None
    return value if value > 0 else None


def _build_service_options():
    """Estructura del select agrupado por categoría + datos para el JS."""
    active = list(
        ServiceType.objects.filter(active=True)
        .select_related('category')
        .order_by('category__sort_order', 'sort_order', 'name')
    )
    categories = list(ServiceCategory.objects.all().order_by('sort_order', 'name'))
    uncategorized = [st for st in active if st.category_id is None]

    rates, units, tier_map = {}, {}, {}
    reps = {}
    min_rates = {}
    group_rows = {}
    for st in active:
        if st.is_tier and st.category_id:
            group_rows.setdefault((st.category_id, st.name), []).append(st)

    for key, members in group_rows.items():
        members.sort(
            key=lambda m: (m.min_weight_kg is None, m.min_weight_kg or Decimal('0'), m.pk)
        )
        rep = members[0]
        reps[key] = rep
        min_rates[key] = min((Decimal(m.rate_per_kg) for m in members))
        rates[rep.pk] = str(rep.rate_per_kg)
        units[rep.pk] = 'kg'
        tier_map[rep.pk] = [
            {
                'pk': m.pk,
                'rate': str(m.rate_per_kg),
                'min': str(m.min_weight_kg) if m.min_weight_kg is not None else None,
                'max': str(m.max_weight_kg) if m.max_weight_kg is not None else None,
            }
            for m in members
        ]

    for st in active:
        if not st.is_tier:
            rates[st.pk] = str(st.rate_per_kg)
            units[st.pk] = st.unit

    option_groups = []
    emitted = set()
    for cat in categories:
        opts = []
        for st in active:
            if st.category_id != cat.pk:
                continue
            if st.is_tier:
                key = (cat.pk, st.name)
                if key in emitted:
                    continue
                emitted.add(key)
                rep = reps[key]
                opts.append({
                    'pk': rep.pk,
                    'label': f'{rep.name} · desde ${min_rates[key]}/kg',
                })
            else:
                unit_txt = 'kg' if st.unit == ServiceType.Unit.KG else 'pieza'
                opts.append({
                    'pk': st.pk,
                    'label': f'{st.name} · ${st.rate_per_kg}/{unit_txt}',
                })
        option_groups.append({'emoji': cat.emoji, 'name': cat.name, 'options': opts})

    if uncategorized:
        opts = [
            {
                'pk': st.pk,
                'label': (
                    f'{st.name} · ${st.rate_per_kg}/'
                    f"{'kg' if st.unit == ServiceType.Unit.KG else 'pieza'}"
                ),
            }
            for st in uncategorized if not st.is_tier
        ]
        if opts:
            option_groups.append({'emoji': '', 'name': 'Sin categoría', 'options': opts})

    return {
        'service_groups': option_groups,
        'rates': rates,
        'units': units,
        'tier_map': tier_map,
    }


@login_required
@require_http_methods(['GET', 'POST'])
def pos_home(request):
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        customer_name = request.POST.get('customer_name', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()

        if customer_id:
            customer = get_object_or_404(Customer, pk=customer_id)
        elif customer_name:
            customer = Customer.objects.create(name=customer_name, phone=customer_phone)
        else:
            messages.error(request, 'Selecciona un cliente o captura un nombre.')
            return redirect('pos_home')

        service_ids = request.POST.getlist('service_type')
        raw_values = request.POST.getlist('weight')

        lines = []
        for service_id, raw in zip(service_ids, raw_values):
            if not service_id:
                continue
            service = ServiceType.objects.filter(pk=service_id, active=True).first()
            if not service:
                continue
            parsed = _parse_weight(raw)
            if parsed is None:
                continue
            resolved = service.resolve_for(parsed)
            if resolved.unit == ServiceType.Unit.PIECE:
                qty = int(parsed)
                if qty != parsed or qty < 1:
                    continue
                lines.append((resolved, 'piece', qty))
            else:
                lines.append((resolved, 'kg', parsed))

        if not lines:
            messages.error(request, 'Agrega al menos una línea con peso o cantidad válidos.')
            return redirect('pos_home')

        order = Order.objects.create(customer=customer, received_by=request.user)
        for service_type, unit, amount in lines:
            if unit == 'piece':
                OrderLine.objects.create(
                    order=order, service_type=service_type, unit='piece',
                    quantity=amount, weight_kg=0,
                )
            else:
                OrderLine.objects.create(
                    order=order, service_type=service_type, unit='kg',
                    weight_kg=amount,
                )
        order.refresh_totals()

        payment_amount = _parse_weight(request.POST.get('payment_amount') or '0')
        payment_method = request.POST.get(
            'payment_method', Payment.Method.CASH
        )
        if payment_amount and payment_amount > 0:
            if payment_amount <= order.balance_due:
                Payment.objects.create(
                    order=order, amount=payment_amount, method=payment_method,
                    received_by=request.user,
                )
            else:
                messages.warning(request, 'El pago excede el saldo; se omite.')

        messages.success(
            request, f'Orden #{order.ticket_number} creada 🎉'
        )
        return redirect('pos_order_detail', pk=order.pk)

    valid_statuses = dict(Order.Status.choices)
    status_filter = request.GET.get('status', '')
    if status_filter not in valid_statuses:
        status_filter = ''

    date_filter = request.GET.get('date', 'today')

    orders = Order.objects.select_related('customer').order_by('-number')
    if status_filter:
        orders = orders.filter(status=status_filter)
    if date_filter == 'today':
        orders = orders.filter(received_at__date=timezone.localdate())

    options = _build_service_options()
    return render(request, 'pos/home.html', {
        'service_groups': options['service_groups'],
        'rates_json': json.dumps(options['rates']),
        'units_json': json.dumps(options['units']),
        'tiers_json': json.dumps(options['tier_map']),
        'customers': Customer.objects.order_by('name'),
        'orders': orders,
        'status_chips': STATUS_CHIPS,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'active_page': 'pos',
    })


@login_required
@require_http_methods(['GET', 'POST'])
def pos_order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('customer', 'received_by')
        .prefetch_related('lines__service_type', 'payments'),
        pk=pk,
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'payment':
            amount = _parse_weight(request.POST.get('amount') or '0')
            method = request.POST.get('method', Payment.Method.CASH)
            if amount and amount > 0:
                if amount <= order.balance_due:
                    Payment.objects.create(
                        order=order, amount=amount, method=method,
                        received_by=request.user,
                    )
                    messages.success(request, 'Pago registrado 💰')
                else:
                    messages.error(request, 'El pago excede el saldo pendiente.')
            else:
                messages.error(request, 'Monto inválido.')
        elif action == 'status':
            new_status = request.POST.get('status')
            try:
                order.transition_status(new_status)
                messages.success(
                    request,
                    f'Estado: {order.get_status_display()} ✅',
                )
            except ValidationError as exc:
                messages.error(request, exc.messages[0])
        return redirect('pos_order_detail', pk=pk)

    next_statuses = [
        (s, dict(Order.Status.choices)[s])
        for s in ALLOWED_TRANSITIONS.get(order.status, ())
    ]

    status_flow = [
        ('received', 'Recibido', '📥'),
        ('ready_to_wash', 'Listo para lavar', '🧺'),
        ('on_wash', 'En lavado', '🫧'),
        ('ready_to_delivery', 'Listo para entrega', '📦'),
        ('delivered', 'Entregado', '✅'),
        ('completed', 'Completado', '✔️'),
    ]
    current_idx = next(
        i for i, (v, _, _) in enumerate(status_flow) if v == order.status
    )
    timeline = []
    for i, (value, label, emoji) in enumerate(status_flow):
        state = 'current' if value == order.status else ('done' if i < current_idx else 'pending')
        timeline.append((state, value, label, emoji))

    return render(request, 'pos/order_detail.html', {
        'order': order,
        'next_statuses': next_statuses,
        'timeline': timeline,
        'active_page': 'pos',
    })


@login_required
def pos_order_ticket(request, pk):
    from orders.ticket import ticket_context
    order = get_object_or_404(Order, pk=pk)
    return render(request, 'orders/ticket.html', ticket_context(order))
