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
