# ==================================================
# SecureApprove Django - Billing Signals
# ==================================================

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from apps.tenants.models import Tenant
from .models import Plan, Subscription
from .services import get_billing_service

@receiver(post_save, sender=Tenant)
def create_default_subscription(sender, instance, created, **kwargs):
    """Create default subscription when a new tenant is created"""
    
    if created and not hasattr(instance, 'subscription'):
        # Get the starter plan (or first available plan)
        try:
            starter_plan = Plan.objects.get(name='starter', is_active=True)
        except Plan.DoesNotExist:
            starter_plan = Plan.objects.filter(is_active=True).first()
        
        if starter_plan:
            # Create trial subscription
            now = timezone.now()
            trial_end = now + timezone.timedelta(days=14)
            
            Subscription.objects.create(
                tenant=instance,
                plan=starter_plan,
                billing_cycle='monthly',
                status='trialing',
                current_period_start=now,
                current_period_end=trial_end,
                trial_end=trial_end
            )