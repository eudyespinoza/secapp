import uuid

# ==================================================
# SecureApprove Django - Tenant Model
# ==================================================

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.billing.pricing import get_price_per_user


class Tenant(models.Model):
    """
    Multi-tenant model compatible with existing SecureApprove data
    """
    
    PLAN_CHOICES = [
        ('tier_1', _('2-6 users - $90/user/month')),
        ('tier_2', _('7-12 users - $75/user/month')),
        ('tier_3', _('12+ users - $65/user/month')),
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
    plan_id = models.CharField(_('Plan'), max_length=20, choices=PLAN_CHOICES, default='tier_1')
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
        """
        Get monthly price based on number of seats (users).

        Pricing rules (USD per user):
          - 2–6 users  -> 60 USD/user
          - 7–12 users -> 55 USD/user
          - >12 users  -> 50 USD/user
        """
        price_per_user = get_price_per_user(self.seats)
        return price_per_user * self.seats
    
    def can_add_approver(self):
        """Check if tenant can add another approver"""
        if self.plan_id == 'scale':
            return True
        return self.approvers_count < self.approver_limit

    @property
    def used_seats(self):
        """Number of active users occupying seats in this tenant"""
        return self.active_users_count

    @property
    def available_seats(self):
        """Remaining seats based on current configuration"""
        if self.seats <= 0:
            return None  # Unlimited / not configured
        remaining = self.seats - self.used_seats
        return max(remaining, 0)


class TenantUserInvite(models.Model):
    """
    Invitation for a user to join a tenant.

    Used by tenant admins to add users up to the
    number of purchased seats.
    """

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('accepted', _('Accepted')),
        ('cancelled', _('Cancelled')),
        ('expired', _('Expired')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='invites',
        verbose_name=_('Tenant'),
    )
    email = models.EmailField(_('Email'))
    role = models.CharField(_('Role'), max_length=20, default='requester')
    token = models.CharField(_('Token'), max_length=128, unique=True)
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    expires_at = models.DateTimeField(_('Expires At'), null=True, blank=True)
    accepted_at = models.DateTimeField(_('Accepted At'), null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_invites',
        verbose_name=_('Created By'),
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Tenant User Invite')
        verbose_name_plural = _('Tenant User Invites')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'email']),
            models.Index(fields=['tenant', 'status']),
        ]

    def __str__(self):
        return f"Invite {self.email} -> {self.tenant.key} ({self.status})"

    @property
    def is_expired(self):
        if self.expires_at is None:
            return False
        return self.expires_at < timezone.now()


class ApprovalTypeConfig(models.Model):
    """
    Configuration for approval types per tenant.
    Allows tenants to:
    - Enable/disable approval types
    - Create custom approval types
    - Set required approvers count
    - Assign specific approvers per type
    """
    
    # Default category choices (same as ApprovalRequest)
    DEFAULT_CATEGORIES = [
        ('expense', _('Expense Reimbursement')),
        ('purchase', _('Purchase Request')),
        ('travel', _('Travel Approval')),
        ('contract', _('Contract Approval')),
        ('document', _('Document Withdrawal')),
        ('other', _('Other')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='approval_type_configs',
        verbose_name=_('Tenant'),
    )
    
    # Category key (e.g., 'expense', 'purchase', or custom like 'vacation')
    category_key = models.CharField(
        _('Category Key'),
        max_length=50,
        help_text=_('Unique identifier for this approval type within the tenant')
    )
    
    # Display name for the category
    name = models.CharField(
        _('Name'),
        max_length=100,
        help_text=_('Display name for this approval type')
    )
    
    # Description
    description = models.TextField(
        _('Description'),
        blank=True,
        help_text=_('Optional description of this approval type')
    )
    
    # Icon (Bootstrap Icons class name)
    icon = models.CharField(
        _('Icon'),
        max_length=50,
        default='bi-file-earmark-check',
        help_text=_('Bootstrap Icons class (e.g., bi-cash, bi-cart)')
    )
    
    # Color for UI
    color = models.CharField(
        _('Color'),
        max_length=20,
        default='primary',
        help_text=_('Bootstrap color class (primary, success, warning, danger, info)')
    )
    
    # Enable/Disable
    is_enabled = models.BooleanField(
        _('Enabled'),
        default=True,
        help_text=_('Whether this approval type is available for new requests')
    )
    
    # Is this a custom type created by tenant (vs default system type)
    is_custom = models.BooleanField(
        _('Custom Type'),
        default=False,
        help_text=_('True if this is a custom type created by the tenant')
    )
    
    # Approval requirements
    required_approvers = models.PositiveIntegerField(
        _('Required Approvers'),
        default=1,
        help_text=_('Number of approvers required to approve requests of this type')
    )
    
    # Specific approvers for this type (if empty, any approver can approve)
    designated_approvers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='designated_approval_types',
        verbose_name=_('Designated Approvers'),
        help_text=_('Specific users who can approve this type. Leave empty for any approver.')
    )
    
    # Show amount field
    show_amount = models.BooleanField(
        _('Show Amount Field'),
        default=False,
        help_text=_('Whether to show the amount field for this approval type')
    )
    
    # Extra fields configuration (JSON)
    extra_fields = models.JSONField(
        _('Extra Fields'),
        default=list,
        blank=True,
        help_text=_('Additional fields configuration for this approval type')
    )
    
    # Sort order
    sort_order = models.PositiveIntegerField(
        _('Sort Order'),
        default=0,
        help_text=_('Order in which this type appears in lists')
    )
    
    # Timestamps
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Approval Type Configuration')
        verbose_name_plural = _('Approval Type Configurations')
        ordering = ['sort_order', 'name']
        unique_together = [['tenant', 'category_key']]
        indexes = [
            models.Index(fields=['tenant', 'is_enabled']),
            models.Index(fields=['tenant', 'category_key']),
        ]
    
    def __str__(self):
        status = "✓" if self.is_enabled else "✗"
        return f"{status} {self.name} ({self.tenant.key})"
    
    @classmethod
    def get_default_config(cls, category_key):
        """Get default configuration for a category"""
        defaults = {
            'expense': {
                'name': _('Expense Reimbursement'),
                'icon': 'bi-cash-stack',
                'color': 'success',
                'show_amount': True,
                'extra_fields': ['expense_category', 'receipt_ref'],
            },
            'purchase': {
                'name': _('Purchase Request'),
                'icon': 'bi-cart',
                'color': 'primary',
                'show_amount': True,
                'extra_fields': ['vendor', 'cost_center'],
            },
            'travel': {
                'name': _('Travel Approval'),
                'icon': 'bi-airplane',
                'color': 'info',
                'show_amount': True,
                'extra_fields': ['destination', 'start_date', 'end_date'],
            },
            'contract': {
                'name': _('Contract Approval'),
                'icon': 'bi-file-earmark-text',
                'color': 'warning',
                'show_amount': False,
                'extra_fields': ['vendor', 'reason'],
            },
            'document': {
                'name': _('Document Withdrawal'),
                'icon': 'bi-file-earmark-arrow-down',
                'color': 'secondary',
                'show_amount': False,
                'extra_fields': ['document_id', 'reason'],
            },
            'other': {
                'name': _('Other'),
                'icon': 'bi-three-dots',
                'color': 'dark',
                'show_amount': False,
                'extra_fields': [],
            },
        }
        return defaults.get(category_key, defaults['other'])
    
    @classmethod
    def initialize_for_tenant(cls, tenant):
        """
        Initialize default approval type configurations for a new tenant.
        Creates configs for all default categories.
        """
        created_configs = []
        for idx, (key, label) in enumerate(cls.DEFAULT_CATEGORIES):
            config_data = cls.get_default_config(key)
            config, created = cls.objects.get_or_create(
                tenant=tenant,
                category_key=key,
                defaults={
                    'name': str(config_data['name']),
                    'icon': config_data['icon'],
                    'color': config_data['color'],
                    'show_amount': config_data['show_amount'],
                    'extra_fields': config_data['extra_fields'],
                    'is_enabled': True,
                    'is_custom': False,
                    'required_approvers': 1,
                    'sort_order': idx * 10,
                }
            )
            if created:
                created_configs.append(config)
        return created_configs
    
    def get_designated_approver_ids(self):
        """Get list of designated approver user IDs"""
        return list(self.designated_approvers.values_list('id', flat=True))
    
    def can_user_approve(self, user):
        """Check if a user can approve requests of this type"""
        # If no designated approvers, any approver can approve
        if not self.designated_approvers.exists():
            return user.role in ['approver', 'tenant_admin', 'superadmin']
        
        # Check if user is in designated approvers
        return self.designated_approvers.filter(id=user.id).exists()

