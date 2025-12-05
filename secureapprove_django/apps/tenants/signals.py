# ==================================================
# SecureApprove Django - Tenant Signals
# ==================================================

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Tenant, ApprovalTypeConfig

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Tenant)
def initialize_approval_types_for_new_tenant(sender, instance, created, **kwargs):
    """
    Initialize default approval type configurations when a new tenant is created.
    """
    if created:
        try:
            configs = ApprovalTypeConfig.initialize_for_tenant(instance)
            if configs:
                logger.info(
                    f"Initialized {len(configs)} approval type configurations for tenant: {instance.key}"
                )
        except Exception as e:
            logger.error(
                f"Failed to initialize approval types for tenant {instance.key}: {e}"
            )
