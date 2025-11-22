from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from .models import ApprovalRequest

User = get_user_model()

@receiver(post_save, sender=ApprovalRequest)
def notify_approval_request_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    
    if created:
        # Notify approvers in the tenant
        if instance.tenant:
            approvers = User.objects.filter(
                tenant=instance.tenant,
                role__in=['approver', 'tenant_admin', 'superadmin', 'admin'],
                is_active=True
            )
            
            for approver in approvers:
                # Don't notify the requester if they are also an approver
                if approver == instance.requester:
                    continue
                    
                async_to_sync(channel_layer.group_send)(
                    f"user_{approver.id}",
                    {
                        "type": "notification_approval_request",
                        "request_id": instance.id,
                        "title": instance.title,
                        "requester_name": instance.requester.get_full_name(),
                        "message": f"New request from {instance.requester.get_full_name()}: {instance.title}"
                    }
                )
                
    else:
        # Notify requester of status change
        if instance.status in ['approved', 'rejected']:
            async_to_sync(channel_layer.group_send)(
                f"user_{instance.requester.id}",
                {
                    "type": "notification_approval_status",
                    "request_id": instance.id,
                    "title": instance.title,
                    "status": instance.status,
                    "message": f"Your request '{instance.title}' has been {instance.get_status_display().lower()}."
                }
            )
