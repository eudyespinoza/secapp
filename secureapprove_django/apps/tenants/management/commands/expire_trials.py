from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.billing.models import Subscription
from apps.tenants.models import Tenant
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Expire trials that have passed their end date'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_subscriptions = Subscription.objects.filter(
            status='trialing',
            trial_end__lt=now
        )
        
        count = 0
        for sub in expired_subscriptions:
            try:
                # Suspend subscription
                sub.status = 'suspended'
                sub.save(update_fields=['status'])
                
                # Deactivate tenant
                tenant = sub.tenant
                tenant.is_active = False
                tenant.status = 'suspended'
                tenant.save(update_fields=['is_active', 'status'])
                
                logger.info(f"Expired trial for tenant {tenant.name} ({tenant.key})")
                self.stdout.write(self.style.SUCCESS(f"Expired trial for tenant {tenant.name}"))
                count += 1
            except Exception as e:
                logger.error(f"Error expiring trial for subscription {sub.id}: {e}")
                self.stdout.write(self.style.ERROR(f"Error expiring trial for subscription {sub.id}: {e}"))
                
        self.stdout.write(self.style.SUCCESS(f"Successfully expired {count} trials"))
