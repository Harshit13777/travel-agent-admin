from django import forms

class PassengerCancellationForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    action = forms.CharField(widget=forms.HiddenInput, initial="cancel_passengers")
    
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'vLargeTextField'}),
        required=True,
        label="Cancellation Reason"
    )
    
    supplier_refund_expected = forms.DecimalField(
        max_digits=12, decimal_places=2, initial=0.00, required=True,
        label="Supplier Refund Expected (INR)"
    )
    
    taxable_refund = forms.DecimalField(
        max_digits=12, decimal_places=2, initial=0.00, required=True,
        label="Taxable Refund (Ticket/Service)"
    )
    
    cgst_rate = forms.DecimalField(max_digits=5, decimal_places=2, initial=0.00, required=True)
    cgst_amount = forms.DecimalField(max_digits=12, decimal_places=2, initial=0.00, required=True)
    sgst_rate = forms.DecimalField(max_digits=5, decimal_places=2, initial=0.00, required=True)
    sgst_amount = forms.DecimalField(max_digits=12, decimal_places=2, initial=0.00, required=True)
    igst_rate = forms.DecimalField(max_digits=5, decimal_places=2, initial=0.00, required=True)
    igst_amount = forms.DecimalField(max_digits=12, decimal_places=2, initial=0.00, required=True)
    
    issue_credit_note = forms.BooleanField(
        required=False,
        initial=True,
        label="Issue Credit Note to Customer?"
    )
