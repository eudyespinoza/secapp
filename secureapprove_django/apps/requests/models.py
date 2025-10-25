# ==================================================
# SecureApprove Django - Request Model
# ==================================================

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()

class ApprovalRequest(models.Model):
    """
    Approval Request model compatible with existing SecureApprove data
    """
    
    CATEGORY_CHOICES = [
        ('expense', _('Expense Reimbursement')),
        ('purchase', _('Purchase Request')),
        ('travel', _('Travel Approval')),
        ('contract', _('Contract Approval')),
        ('document', _('Document Withdrawal')),
        ('other', _('Other')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('cancelled', _('Cancelled')),
    ]
    
    # Basic information
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    category = models.CharField(_('Category'), max_length=20, choices=CATEGORY_CHOICES, default='other')
    priority = models.CharField(_('Priority'), max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Amount (optional, depends on category)
    amount = models.DecimalField(
        _('Amount'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Amount for expense, purchase, or travel requests')
    )
    
    # Relationships
    requester = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='submitted_requests',
        verbose_name=_('Requester')
    )
    
    approver = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requests',
        verbose_name=_('Approver')
    )
    
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='requests',
        verbose_name=_('Tenant')
    )
    
    # Approval details
    approver_comment = models.TextField(_('Approver Comment'), blank=True)
    approved_at = models.DateTimeField(_('Approved At'), null=True, blank=True)
    
    # Rejection details
    rejection_reason = models.TextField(_('Rejection Reason'), blank=True)
    rejected_at = models.DateTimeField(_('Rejected At'), null=True, blank=True)
    
    # Metadata (JSON field for dynamic data based on category)
    metadata = models.JSONField(
        _('Metadata'),
        default=dict,
        blank=True,
        help_text=_('Category-specific data: vendor, cost_center, destination, etc.')
    )
    
    # Expiration
    expires_at = models.DateTimeField(_('Expires At'), null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Approval Request')
        verbose_name_plural = _('Approval Requests')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['requester', 'created_at']),
            models.Index(fields=['approver', 'approved_at']),
            models.Index(fields=['status', 'priority']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_approved(self):
        return self.status == 'approved'
    
    @property
    def is_rejected(self):
        return self.status == 'rejected'
    
    @property
    def can_be_approved(self):
        """Check if request can be approved"""
        return self.status == 'pending' and not self.is_expired
    
    @property
    def is_expired(self):
        """Check if request has expired"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    @property
    def category_config(self):
        """Get category configuration for dynamic form handling"""
        configs = {
            'expense': {
                'show_amount': True,
                'required_fields': ['title', 'description', 'amount', 'priority', 'expense_category', 'receipt_ref'],
                'extra_fields': ['expense_category', 'receipt_ref']
            },
            'purchase': {
                'show_amount': True,
                'required_fields': ['title', 'description', 'amount', 'priority', 'vendor', 'cost_center'],
                'extra_fields': ['vendor', 'cost_center']
            },
            'travel': {
                'show_amount': True,
                'required_fields': ['title', 'description', 'amount', 'priority', 'destination', 'start_date', 'end_date'],
                'extra_fields': ['destination', 'start_date', 'end_date']
            },
            'contract': {
                'show_amount': False,
                'required_fields': ['title', 'description', 'priority', 'vendor', 'reason'],
                'extra_fields': ['vendor', 'reason']
            },
            'document': {
                'show_amount': False,
                'required_fields': ['title', 'description', 'priority', 'document_id', 'reason'],
                'extra_fields': ['document_id', 'reason']
            },
            'other': {
                'show_amount': False,
                'required_fields': ['title', 'description', 'priority'],
                'extra_fields': []
            }
        }
        return configs.get(self.category, configs['other'])
    
    def approve(self, approver, comment=''):
        """Approve the request"""
        if not self.can_be_approved:
            raise ValueError("Request cannot be approved")
        
        from django.utils import timezone
        self.status = 'approved'
        self.approver = approver
        self.approver_comment = comment
        self.approved_at = timezone.now()
        self.save()
    
    def reject(self, approver, reason):
        """Reject the request"""
        if not self.can_be_approved:
            raise ValueError("Request cannot be rejected")
        
        from django.utils import timezone
        self.status = 'rejected'
        self.approver = approver
        self.rejection_reason = reason
        self.rejected_at = timezone.now()
        self.save()
    
    def cancel(self):
        """Cancel the request"""
        if self.status != 'pending':
            raise ValueError("Only pending requests can be cancelled")
        
        self.status = 'cancelled'
        self.save()