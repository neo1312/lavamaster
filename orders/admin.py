from django.contrib import admin

from .models import Order, OrderLine, Payment


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 1


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('received_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'customer', 'status', 'total_weight_kg', 'subtotal', 'balance_due', 'received_at')
    list_filter = ('status', 'received_at')
    search_fields = ('number', 'customer__name', 'customer__phone')
    inlines = (OrderLineInline, PaymentInline)
    readonly_fields = ('number', 'subtotal', 'received_at')

    def balance_due(self, obj):
        return obj.balance_due

    balance_due.short_description = 'Saldo'
