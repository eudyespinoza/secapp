# ==================================================
# SecureApprove Django - Dynamic Request Forms
# ==================================================

from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML
from crispy_forms.bootstrap import Field
from .models import ApprovalRequest

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class DynamicRequestForm(forms.ModelForm):
    """
    Dynamic form that shows/hides fields based on request category
    Replicates the exact behavior of the Next.js form
    """
    
    # Extra fields for dynamic categories
    purchase_vendor = forms.CharField(
        label=_('Vendor'),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Vendor name')})
    )
    
    contract_vendor = forms.CharField(
        label=_('Vendor'),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Vendor name')})
    )
    
    cost_center = forms.CharField(
        label=_('Cost Center'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Cost center code')})
    )
    
    expense_category = forms.CharField(
        label=_('Expense Category'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Meals, Transportation, etc.')})
    )
    
    receipt_ref = forms.CharField(
        label=_('Receipt Reference'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Receipt number or reference')})
    )
    
    destination = forms.CharField(
        label=_('Destination'),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Travel destination')})
    )
    
    start_date = forms.DateField(
        label=_('Start Date'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    end_date = forms.DateField(
        label=_('End Date'),
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    document_id = forms.CharField(
        label=_('Document ID'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': _('Document ID or reference')})
    )
    
    contract_reason = forms.CharField(
        label=_('Reason'),
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': _('Explain the reason for this request')})
    )
    
    document_reason = forms.CharField(
        label=_('Reason'),
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': _('Explain the reason for this request')})
    )
    
    attachments = forms.FileField(
        label=_('Attachments'),
        required=False,
        widget=MultipleFileInput(attrs={'multiple': True, 'class': 'form-control'}),
        help_text=_('You can select multiple files. Max size 25MB per file.')
    )
    
    class Meta:
        model = ApprovalRequest
        fields = ['title', 'description', 'category', 'priority', 'amount']
        
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': _('Request title'),
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': _('Detailed description of your request'),
                'class': 'form-control'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_category'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Get current category to determine field requirements
        category = self.data.get('category') or self.initial.get('category') or 'expense'
        
        # Configure fields based on category
        config = self._get_category_config(category)
        
        # Set required fields based on category
        for field_name in self.fields:
            if field_name in config['required_fields']:
                self.fields[field_name].required = True
            elif field_name in config.get('extra_fields', []):
                self.fields[field_name].required = field_name in config['required_fields']
        
        # Show/hide amount field based on category
        if not config['show_amount']:
            self.fields['amount'].required = False
            self.fields['amount'].widget = forms.HiddenInput()
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        self.helper.attrs = {'novalidate': True, 'enctype': 'multipart/form-data'}
        
        self.helper.layout = Layout(
            Fieldset(
                _('Request Information'),
                'category',
                Row(
                    Column('title', css_class='col-md-8'),
                    Column('priority', css_class='col-md-4'),
                ),
                'description',
                Row(
                    Column('amount', css_class='col-md-12', css_id='amount-field'),
                ),
                'attachments',
            ),
            
            # Dynamic fields container
            HTML('<div id="dynamic-fields">'),
            self._get_dynamic_fields_layout(),
            HTML('</div>'),
            
            Submit('submit', _('Submit Request'), css_class='btn btn-primary btn-lg mt-3')
        )
    
    def _get_category_config(self, category):
        """Get configuration for a specific category"""
        configs = {
            'expense': {
                'show_amount': True,
                'required_fields': ['title', 'description', 'amount', 'priority', 'expense_category', 'receipt_ref'],
                'extra_fields': ['expense_category', 'receipt_ref']
            },
            'purchase': {
                'show_amount': True,
                'required_fields': ['title', 'description', 'amount', 'priority', 'purchase_vendor', 'cost_center'],
                'extra_fields': ['purchase_vendor', 'cost_center']
            },
            'travel': {
                'show_amount': True,
                'required_fields': ['title', 'description', 'amount', 'priority', 'destination', 'start_date', 'end_date'],
                'extra_fields': ['destination', 'start_date', 'end_date']
            },
            'contract': {
                'show_amount': False,
                'required_fields': ['title', 'description', 'priority', 'contract_vendor', 'contract_reason'],
                'extra_fields': ['contract_vendor', 'contract_reason']
            },
            'document': {
                'show_amount': False,
                'required_fields': ['title', 'description', 'priority', 'document_id', 'document_reason'],
                'extra_fields': ['document_id', 'document_reason']
            },
            'other': {
                'show_amount': False,
                'required_fields': ['title', 'description', 'priority'],
                'extra_fields': []
            }
        }
        return configs.get(category, configs['other'])
    
    def _get_dynamic_fields_layout(self):
        """Get layout for dynamic fields based on category"""
        return Fieldset(
            _('Additional Information'),
            # Expense fields
            HTML('<div class="dynamic-group" data-category="expense" style="display: none;">'),
            Row(
                Column('expense_category', css_class='col-md-6'),
                Column('receipt_ref', css_class='col-md-6'),
            ),
            HTML('</div>'),
            
            # Purchase fields
            HTML('<div class="dynamic-group" data-category="purchase" style="display: none;">'),
            Row(
                Column('purchase_vendor', css_class='col-md-6'),
                Column('cost_center', css_class='col-md-6'),
            ),
            HTML('</div>'),
            
            # Travel fields
            HTML('<div class="dynamic-group" data-category="travel" style="display: none;">'),
            'destination',
            Row(
                Column('start_date', css_class='col-md-6'),
                Column('end_date', css_class='col-md-6'),
            ),
            HTML('</div>'),
            
            # Contract fields
            HTML('<div class="dynamic-group" data-category="contract" style="display: none;">'),
            'contract_vendor',
            'contract_reason',
            HTML('</div>'),
            
            # Document fields
            HTML('<div class="dynamic-group" data-category="document" style="display: none;">'),
            'document_id',
            'document_reason',
            HTML('</div>'),
        )
    
    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        
        if not category:
            return cleaned_data
        
        config = self._get_category_config(category)
        
        # Validate required extra fields
        for field_name in config.get('extra_fields', []):
            if field_name in config['required_fields']:
                value = cleaned_data.get(field_name)
                if not value:
                    self.add_error(field_name, _('This field is required for this category.'))
        
        # Validate amount field
        if config['show_amount']:
            amount = cleaned_data.get('amount')
            if not amount or amount <= 0:
                self.add_error('amount', _('Amount is required and must be greater than 0 for this category.'))
        
        # Validate date fields for travel
        if category == 'travel':
            start_date = cleaned_data.get('start_date')
            end_date = cleaned_data.get('end_date')
            if start_date and end_date and start_date > end_date:
                self.add_error('end_date', _('End date must be after start date.'))
        
        # Validate attachments size
        if self.files:
            attachments = self.files.getlist('attachments')
            for file in attachments:
                if file.size > 25 * 1024 * 1024:
                    self.add_error('attachments', _('File {} is too large. Max size is 25MB.').format(file.name))

        return cleaned_data
    
    def save(self, commit=True):
        request = super().save(commit=False)
        
        if self.user:
            request.requester = self.user
            if hasattr(self.user, 'tenant') and self.user.tenant:
                request.tenant = self.user.tenant
        
        # Store extra fields in metadata
        category = request.category
        config = self._get_category_config(category)
        metadata = {}
        
        # Map fields to metadata keys
        field_mapping = {
            'purchase_vendor': 'vendor',
            'contract_vendor': 'vendor',
            'contract_reason': 'reason',
            'document_reason': 'reason',
        }
        
        for field_name in config.get('extra_fields', []):
            value = self.cleaned_data.get(field_name)
            if value:
                metadata_key = field_mapping.get(field_name, field_name)
                metadata[metadata_key] = str(value) if not isinstance(value, str) else value
        
        request.metadata = metadata
        
        if commit:
            request.save()
        
        return request