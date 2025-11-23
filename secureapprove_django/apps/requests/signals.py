from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from .models import ApprovalRequest
from .tasks import send_webpush_notification

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
                        "status": instance.status,
                        "status_display": instance.get_status_display(),
                        "priority": instance.priority,
                        "category_display": instance.get_category_display(),
                        "created_at": instance.created_at.isoformat(),
                        "message": _("New request from {name}: {title}").format(name=instance.requester.get_full_name(), title=instance.title)
                    }
                )

                # Web Push Notification (Async)
                payload = {
                    "title": _("New Request"),
                    "body": _("New request from {name}: {title}").format(name=instance.requester.get_full_name(), title=instance.title),
                    "icon": "/static/img/logo.png",
                    "color": "#4f46e5",
                    "url": f"/dashboard/requests/{instance.id}/"
                }
                send_webpush_notification.delay(user_id=approver.id, payload=payload, ttl=1000)
                
    else:
        # Notify requester of status change
        if instance.status in ['approved', 'rejected']:
            approver_name = instance.approver.get_full_name() if instance.approver else None
            status_display = instance.get_status_display()
            
            async_to_sync(channel_layer.group_send)(
                f"user_{instance.requester.id}",
                {
                    "type": "notification_approval_status",
                    "request_id": instance.id,
                    "title": instance.title,
                    "status": instance.status,
                    "status_display": status_display,
                    "approver_name": approver_name,
                    "message": _("Your request '{title}' has been {status}.").format(title=instance.title, status=status_display.lower())
                }
            )

            # Web Push Notification (Async)
            payload = {
                "title": _("Request {status}").format(status=status_display),
                "body": _("Your request '{title}' has been {status}.").format(title=instance.title, status=status_display.lower()),
                "icon": "/static/img/logo.png",
                "color": "#4f46e5",
                "url": f"/dashboard/requests/{instance.id}/"
            }
            send_webpush_notification.delay(user_id=instance.requester.id, payload=payload, ttl=1000)
