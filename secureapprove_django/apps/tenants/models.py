# ==================================================
# SecureApprove Django - Tenant Model
# ==================================================

from django.db import models
from django.utils.translation import gettext_lazy as _

class Tenant(models.Model):
    """
    Multi-tenant model compatible with existing SecureApprove data
    """
    
    PLAN_CHOICES = [
        ('starter', _('Starter - Up to 2 approvers')),
        ('growth', _('Growth - Up to 6 approvers')),
        ('scale', _('Scale - Unlimited approvers')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('suspended', _('Suspended')),
        ('cancelled', _('Cancelled')),
        ('trial', _('Trial')),
    ]
    
    # Basic information
    key = models.SlugField(_('Key'), max_length=50, unique=True)
    name = models.CharField(_('Name'), max_length=200)
    
    # Plan and limits
    plan_id = models.CharField(_('Plan'), max_length=20, choices=PLAN_CHOICES, default='starter')
    seats = models.PositiveIntegerField(_('Seats'), default=5)
    approver_limit = models.PositiveIntegerField(_('Approver Limit'), default=2)
    
    # Status
    is_active = models.BooleanField(_('Active'), default=True)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='trial')
    
    # Billing information (JSON field to store billing data)
    billing = models.JSONField(
        _('Billing Information'),
        default=dict,
        blank=True,
        help_text=_('Stores billing provider data, subscription IDs, etc.')
    )
    
    # Metadata
    metadata = models.JSONField(
        _('Metadata'),
        default=dict,
        blank=True,
        help_text=_('Additional tenant configuration and data')
    )
    
    # Timestamps
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Tenant')
        verbose_name_plural = _('Tenants')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.key})"
    
    @property
    def plan_display(self):
        """Get plan display name"""
        return dict(self.PLAN_CHOICES).get(self.plan_id, self.plan_id)
    
    @property
    def active_users_count(self):
        """Count of active users in this tenant"""
        return self.users.filter(is_active=True).count()
    
    @property
    def approvers_count(self):
        """Count of users who can approve requests"""
        return self.users.filter(
            is_active=True,
            role__in=['approver', 'tenant_admin', 'superadmin']
        ).count()
    
    @property
    def is_over_approver_limit(self):
        """Check if tenant has exceeded approver limit"""
        return self.approvers_count > self.approver_limit
    
    @property
    def monthly_price(self):
        """Get monthly price based on plan"""
        prices = {
            'starter': 25,
            'growth': 45,
            'scale': 65,
        }
        return prices.get(self.plan_id, 45)
    
    def can_add_approver(self):
        """Check if tenant can add another approver"""
        if self.plan_id == 'scale':
            return True
        return self.approvers_count < self.approver_limit