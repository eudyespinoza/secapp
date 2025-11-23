# ==================================================
# SecureApprove Django - Billing Models
# ==================================================

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

User = get_user_model()

class Plan(models.Model):
    """Subscription plans for tenants"""
    
    PLAN_TYPES = [
        ('starter', _('Starter')),
        ('growth', _('Growth')),
        ('scale', _('Scale')),
        ('tier_1', _('Small Team')),
        ('tier_2', _('Medium Team')),
        ('tier_3', _('Large Team')),
    ]
    
    name = models.CharField(max_length=100, choices=PLAN_TYPES, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Pricing
    monthly_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    yearly_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        null=True,
        blank=True,
        help_text=_('Yearly price (optional, defaults to monthly * 10)')
    )
    
    # Limits
    max_approvers = models.PositiveIntegerField(
        help_text=_('Maximum number of approvers allowed')
    )
    max_requests_per_month = models.PositiveIntegerField(
        help_text=_('Maximum requests per month (0 = unlimited)')
    )
    max_users = models.PositiveIntegerField(
        help_text=_('Maximum users in tenant (0 = unlimited)')
    )
    
    # Features
    api_access = models.BooleanField(default=True)
    advanced_analytics = models.BooleanField(default=False)
    custom_workflows = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    
    # Settings
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text=_('Display order'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'monthly_price']
        verbose_name = _('Plan')
        verbose_name_plural = _('Plans')
    
    def __str__(self):
        return f"{self.display_name} (${self.monthly_price}/month)"
    
    @property
    def yearly_price_calculated(self):
        """Calculate yearly price if not set"""
        if self.yearly_price:
            return self.yearly_price
        return self.monthly_price * 10  # 2 months free
    
    @property
    def yearly_savings(self):
        """Calculate savings when paying yearly"""
        monthly_yearly = self.monthly_price * 12
        return monthly_yearly - self.yearly_price_calculated
    
    @property
    def features(self):
        """Get plan features as a list"""
        features_list = []
        if self.api_access:
            features_list.append("API Access")
        if self.advanced_analytics:
            features_list.append("Advanced Analytics")
        if self.custom_workflows:
            features_list.append("Custom Workflows")
        if self.priority_support:
            features_list.append("Priority Support")
        
        # Add user limits
        if self.max_users > 0:
            features_list.append(f"Up to {self.max_users} users")
        else:
            features_list.append("Unlimited users")
            
        # Add request limits
        if self.max_requests_per_month > 0:
            features_list.append(f"{self.max_requests_per_month:,} requests/month")
        else:
            features_list.append("Unlimited requests")
            
        return features_list
    
    def can_create_approver(self, tenant):
        """Check if tenant can create another approver"""
        current_approvers = User.objects.filter(
            tenant=tenant,
            role__in=['admin', 'approver']
        ).count()
        return current_approvers < self.max_approvers
    
    def can_create_user(self, tenant):
        """
        Check if tenant can create another user.

        Instead of using a static max_users per plan, we base this
        on the tenant's configured seats (number of users purchased).
        """
        # If tenant has no explicit seat limit, fall back to plan.max_users
        seats = getattr(tenant, "seats", 0) or 0

        if seats > 0:
            current_users = User.objects.filter(tenant=tenant).count()
            return current_users < seats

        # Legacy fallback: use plan-level max_users (0 = unlimited)
        if self.max_users == 0:
            return True
        current_users = User.objects.filter(tenant=tenant).count()
        return current_users < self.max_users
    
    def can_create_request(self, tenant, month=None, year=None):
        """Check if tenant can create another request this month"""
        if self.max_requests_per_month == 0:  # Unlimited
            return True
        
        from django.utils import timezone
        from apps.requests.models import ApprovalRequest
        
        if not month or not year:
            now = timezone.now()
            month, year = now.month, now.year
        
        current_requests = ApprovalRequest.objects.filter(
            tenant=tenant,
            created_at__year=year,
            created_at__month=month
        ).count()
        
        return current_requests < self.max_requests_per_month

class Subscription(models.Model):
    """Tenant subscription to a plan"""
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('cancelled', _('Cancelled')),
        ('past_due', _('Past Due')),
        ('suspended', _('Suspended')),
        ('trialing', _('Trialing')),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('monthly', _('Monthly')),
        ('yearly', _('Yearly')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    
    # Billing
    billing_cycle = models.CharField(
        max_length=20,
        choices=BILLING_CYCLE_CHOICES,
        default='monthly'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='trialing'
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    # Mercado Pago Integration
    mp_subscription_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text=_('Mercado Pago subscription ID')
    )
    mp_customer_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text=_('Mercado Pago customer ID')
    )
    
    class Meta:
        verbose_name = _('Subscription')
        verbose_name_plural = _('Subscriptions')
    
    def __str__(self):
        return f"{self.tenant.name} - {self.plan.display_name}"
    
    @property
    def is_active(self):
        """Check if subscription is active"""
        return self.status in ['active', 'trialing']
    
    @property
    def is_trial(self):
        """Check if subscription is in trial"""
        return self.status == 'trialing'
    
    @property
    def current_price(self):
        """Get current subscription price"""
        if self.billing_cycle == 'yearly':
            return self.plan.yearly_price_calculated
        return self.plan.monthly_price
    
    def can_create_approver(self):
        """Check if subscription allows creating another approver"""
        return self.plan.can_create_approver(self.tenant)
    
    def can_create_user(self):
        """Check if subscription allows creating another user"""
        return self.plan.can_create_user(self.tenant)
    
    def can_create_request(self, month=None, year=None):
        """Check if subscription allows creating another request"""
        return self.plan.can_create_request(self.tenant, month, year)

class Payment(models.Model):
    """Payment records for subscriptions"""
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('cancelled', _('Cancelled')),
        ('refunded', _('Refunded')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Mercado Pago Integration
    mp_payment_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text=_('Mercado Pago payment ID')
    )
    mp_preference_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text=_('Mercado Pago preference ID')
    )
    
    # Additional data
    payment_method = models.CharField(max_length=50, blank=True)
    external_reference = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
    
    def __str__(self):
        return f"Payment {self.id} - ${self.amount} ({self.status})"
    
    @property
    def is_successful(self):
        """Check if payment was successful"""
        return self.status == 'approved'

class UsageMetrics(models.Model):
    """Track usage metrics for billing and analytics"""
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='usage_metrics'
    )
    
    # Period
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    
    # Metrics
    requests_created = models.PositiveIntegerField(default=0)
    requests_approved = models.PositiveIntegerField(default=0)
    requests_rejected = models.PositiveIntegerField(default=0)
    api_calls = models.PositiveIntegerField(default=0)
    
    # User activity
    active_users = models.PositiveIntegerField(default=0)
    total_users = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['subscription', 'year', 'month']
        ordering = ['-year', '-month']
        verbose_name = _('Usage Metrics')
        verbose_name_plural = _('Usage Metrics')
    
    def __str__(self):
        return f"{self.subscription.tenant.name} - {self.year}/{self.month:02d}"
    
    @property
    def total_requests(self):
        """Total requests for the period"""
        return self.requests_created
    
    @property
    def approval_rate(self):
        """Calculate approval rate"""
        total = self.requests_approved + self.requests_rejected
        if total == 0:
            return 0
        return (self.requests_approved / total) * 100

class Invoice(models.Model):
    """Invoices for subscription payments"""
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('sent', _('Sent')),
        ('paid', _('Paid')),
        ('overdue', _('Overdue')),
        ('cancelled', _('Cancelled')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice'
    )
    
    # Invoice details
    invoice_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Dates
    issue_date = models.DateField()
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    
    # Period covered
    period_start = models.DateField()
    period_end = models.DateField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-issue_date']
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - ${self.total_amount}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            # Generate invoice number
            from django.utils import timezone
            now = timezone.now()
            self.invoice_number = f"INV-{now.year}{now.month:02d}-{now.day:02d}-{self.subscription.tenant.id[:8].upper()}"
        
        super().save(*args, **kwargs)
