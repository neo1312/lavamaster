import base64
import io

from django.http import HttpResponse
from django.template.loader import render_to_string
from qrcode import make as make_qr


def qr_data_uri(order):
    qr = make_qr(f'LAVAMASTER:{order.ticket_number}')
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()


def ticket_context(order):
    return {
        'order': order,
        'qr_data_uri': qr_data_uri(order),
    }


def ticket_html(request, order):
    return HttpResponse(
        render_to_string('orders/ticket.html', ticket_context(order), request=request)
    )


def ticket_pdf(order):
    from weasyprint import HTML

    html = render_to_string('orders/ticket.html', ticket_context(order))
    pdf = HTML(string=html, base_url='.').write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="ticket_{order.ticket_number}.pdf"'
    )
    return response
