from django.contrib.admin import SimpleListFilter

class InvoiceStatusFilter(SimpleListFilter):
    title = 'Invoice Status'
    parameter_name = 'invoice_status'

    def lookups(self, request, model_admin):
        return (
            ('invoiced', 'Invoiced'),
            ('not_invoiced', 'Not Invoiced'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'invoiced':
            return queryset.filter(locked_at__isnull=False)
        if self.value() == 'not_invoiced':
            return queryset.filter(locked_at__isnull=True)
        return queryset
