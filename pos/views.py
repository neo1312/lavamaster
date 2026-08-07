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
from pricing.models import ServiceType

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


@login_required
@require_http_methods(['GET', 'POST'])
def pos_home(request):
    service_types = ServiceType.objects.filter(active=True)

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
        weights = request.POST.getlist('weight')

        lines = []
        for service_id, weight in zip(service_ids, weights):
            if not service_id:
                continue
            service_type = ServiceType.objects.filter(pk=service_id).first()
            parsed = _parse_weight(weight)
            if service_type and parsed is not None:
                lines.append((service_type, parsed))

        if not lines:
            messages.error(request, 'Agrega al menos una línea con peso válido.')
            return redirect('pos_home')

        order = Order.objects.create(customer=customer, received_by=request.user)
        for service_type, weight in lines:
            OrderLine.objects.create(
                order=order, service_type=service_type, weight_kg=weight
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

    return render(request, 'pos/home.html', {
        'service_types': service_types,
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
