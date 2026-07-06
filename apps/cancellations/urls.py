from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required
from .views import CancellationWizardView

urlpatterns = [
    path('wizard/<int:invoice_id>/', staff_member_required(CancellationWizardView.as_view()), name='cancellation_wizard'),
]
