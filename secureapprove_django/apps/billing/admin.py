# ==================================================
# SecureApprove Django - Billing Admin
# ==================================================

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Plan, Subscription, Payment, UsageMetrics, Invoice

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = [
        'display_name', 'name', 'monthly_price', 'yearly_price_calculated',
        'max_approvers', 'max_users', 'max_requests_per_month', 'is_active'
    ]
    list_filter = ['is_active', 'api_access', 'advanced_analytics']
    search_fields = ['name', 'display_name']
    ordering = ['order', 'monthly_price']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'display_name', 'description', 'order', 'is_active')
        }),
        (_('Pricing'), {
            'fields': ('monthly_price', 'yearly_price')
        }),
        (_('Limits'), {
            'fields': ('max_approvers', 'max_users', 'max_requests_per_month')
        }),
        (_('Features'), {
            'fields': ('api_access', 'advanced_analytics', 'custom_workflows', 'priority_support')
        }),
    )
    
    def yearly_price_calculated(self, obj):
        return f"${obj.yearly_price_calculated}"
    yearly_price_calculated.short_description = _('Yearly Price')

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'tenant', 'plan', 'status', 'billing_cycle', 
        'current_period_start', 'current_period_end', 'is_trial'
    ]
    list_filter = ['status', 'billing_cycle', 'plan']
    search_fields = ['tenant__name', 'mp_subscription_id']
    readonly_fields = ['created_at', 'mp_subscription_id', 'mp_customer_id']
    
    fieldsets = (
        (_('Subscription Details'), {
            'fields': ('tenant', 'plan', 'status', 'billing_cycle')
        }),
        (_('Billing Period'), {
            'fields': ('current_period_start', 'current_period_end', 'trial_end')
        }),
        (_('Mercado Pago'), {
            'fields': ('mp_subscription_id', 'mp_customer_id')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'cancelled_at')
        }),
    )
    
    def is_trial(self, obj):
        return obj.is_trial
    is_trial.boolean = True
    is_trial.short_description = _('Trial')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'subscription_tenant', 'amount', 'currency', 
        'status', 'payment_method', 'created_at', 'paid_at'
    ]
    list_filter = ['status', 'currency', 'payment_method', 'created_at']
    search_fields = ['subscription__tenant__name', 'mp_payment_id', 'external_reference']
    readonly_fields = ['created_at', 'mp_payment_id', 'mp_preference_id']
    
    fieldsets = (
        (_('Payment Details'), {
            'fields': ('subscription', 'amount', 'currency', 'status', 'payment_method')
        }),
        (_('Dates'), {
            'fields': ('created_at', 'paid_at')
        }),
        (_('Mercado Pago'), {
            'fields': ('mp_payment_id', 'mp_preference_id', 'external_reference')
        }),
        (_('Additional Data'), {
            'fields': ('metadata',)
        }),
    )
    
    def subscription_tenant(self, obj):
        return obj.subscription.tenant.name
    subscription_tenant.short_description = _('Tenant')

@admin.register(UsageMetrics)
class UsageMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'subscription_tenant', 'year', 'month', 'total_requests',
        'requests_approved', 'requests_rejected', 'approval_rate_display',
        'active_users', 'api_calls'
    ]
    list_filter = ['year', 'month']
    search_fields = ['subscription__tenant__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Period'), {
            'fields': ('subscription', 'year', 'month')
        }),
        (_('Request Metrics'), {
            'fields': ('requests_created', 'requests_approved', 'requests_rejected')
        }),
        (_('User Activity'), {
            'fields': ('active_users', 'total_users', 'api_calls')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def subscription_tenant(self, obj):
        return obj.subscription.tenant.name
    subscription_tenant.short_description = _('Tenant')
    
    def approval_rate_display(self, obj):
        rate = obj.approval_rate
        color = 'green' if rate >= 80 else 'orange' if rate >= 60 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    approval_rate_display.short_description = _('Approval Rate')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'subscription_tenant', 'total_amount',
        'status', 'issue_date', 'due_date', 'paid_date'
    ]
    list_filter = ['status', 'issue_date', 'due_date']
    search_fields = ['invoice_number', 'subscription__tenant__name']
    readonly_fields = ['created_at', 'updated_at', 'invoice_number']
    
    fieldsets = (
        (_('Invoice Details'), {
            'fields': ('subscription', 'invoice_number', 'status')
        }),
        (_('Amounts'), {
            'fields': ('subtotal', 'tax_amount', 'total_amount')
        }),
        (_('Dates'), {
            'fields': ('issue_date', 'due_date', 'paid_date')
        }),
        (_('Period'), {
            'fields': ('period_start', 'period_end')
        }),
        (_('Payment'), {
            'fields': ('payment',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def subscription_tenant(self, obj):
        return obj.subscription.tenant.name
    subscription_tenant.short_description = _('Tenant')