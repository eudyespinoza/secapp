# ==================================================
# SecureApprove Django - Billing Serializers
# ==================================================

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Plan, Subscription, Payment, Invoice, UsageMetrics

class PlanSerializer(serializers.ModelSerializer):
    """Serializer for Plan model"""
    
    yearly_price_calculated = serializers.ReadOnlyField()
    yearly_savings = serializers.ReadOnlyField()
    
    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'display_name', 'description',
            'monthly_price', 'yearly_price', 'yearly_price_calculated', 'yearly_savings',
            'max_approvers', 'max_requests_per_month', 'max_users',
            'api_access', 'advanced_analytics', 'custom_workflows', 'priority_support',
            'order'
        ]

class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Subscription model"""
    
    plan_details = PlanSerializer(source='plan', read_only=True)
    tenant_name = serializers.CharField(source='tenant.name', read_only=True)
    is_active = serializers.ReadOnlyField()
    is_trial = serializers.ReadOnlyField()
    current_price = serializers.ReadOnlyField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'tenant_name', 'plan', 'plan_details',
            'billing_cycle', 'status', 'is_active', 'is_trial',
            'current_price', 'created_at', 'trial_end',
            'current_period_start', 'current_period_end', 'cancelled_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'trial_end', 'current_period_start',
            'current_period_end', 'cancelled_at'
        ]

class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model"""
    
    subscription_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id', 'subscription', 'subscription_info', 'amount', 'currency',
            'status', 'payment_method', 'created_at', 'paid_at',
            'external_reference'
        ]
        read_only_fields = [
            'id', 'created_at', 'paid_at', 'mp_payment_id', 'mp_preference_id'
        ]
    
    def get_subscription_info(self, obj):
        return {
            'tenant_name': obj.subscription.tenant.name,
            'plan_name': obj.subscription.plan.display_name
        }

class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice model"""
    
    subscription_info = serializers.SerializerMethodField()
    payment_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'subscription', 'subscription_info', 'payment', 'payment_info',
            'invoice_number', 'status', 'subtotal', 'tax_amount', 'total_amount',
            'issue_date', 'due_date', 'paid_date', 'period_start', 'period_end',
            'created_at'
        ]
        read_only_fields = [
            'id', 'invoice_number', 'created_at'
        ]
    
    def get_subscription_info(self, obj):
        return {
            'tenant_name': obj.subscription.tenant.name,
            'plan_name': obj.subscription.plan.display_name
        }
    
    def get_payment_info(self, obj):
        if obj.payment:
            return {
                'id': obj.payment.id,
                'status': obj.payment.status,
                'amount': obj.payment.amount,
                'paid_at': obj.payment.paid_at
            }
        return None

class UsageMetricsSerializer(serializers.ModelSerializer):
    """Serializer for Usage Metrics"""
    
    approval_rate = serializers.ReadOnlyField()
    total_requests = serializers.ReadOnlyField()
    
    class Meta:
        model = UsageMetrics
        fields = [
            'subscription', 'year', 'month',
            'requests_created', 'requests_approved', 'requests_rejected',
            'total_requests', 'approval_rate',
            'api_calls', 'active_users', 'total_users',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class BillingStatsSerializer(serializers.Serializer):
    """Serializer for billing statistics"""
    
    current_plan = PlanSerializer(read_only=True)
    subscription = SubscriptionSerializer(read_only=True)
    usage_this_month = UsageMetricsSerializer(read_only=True)
    recent_payments = PaymentSerializer(many=True, read_only=True)
    recent_invoices = InvoiceSerializer(many=True, read_only=True)
    limits_status = serializers.DictField(read_only=True)

class PlanChangeSerializer(serializers.Serializer):
    """Serializer for plan change requests"""
    
    plan_name = serializers.ChoiceField(
        choices=['starter', 'growth', 'scale'],
        help_text="New plan to change to"
    )
    
    def validate_plan_name(self, value):
        try:
            Plan.objects.get(name=value, is_active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError(_('Invalid plan selected.'))
        return value

class SubscriptionCreateSerializer(serializers.Serializer):
    """Serializer for creating subscriptions"""
    
    plan_name = serializers.ChoiceField(
        choices=['starter', 'growth', 'scale'],
        help_text="Plan to subscribe to"
    )
    billing_cycle = serializers.ChoiceField(
        choices=['monthly', 'yearly'],
        default='monthly',
        help_text="Billing frequency"
    )
    
    def validate_plan_name(self, value):
        try:
            Plan.objects.get(name=value, is_active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError(_('Invalid plan selected.'))
        return value