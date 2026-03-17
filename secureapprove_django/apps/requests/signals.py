from django.db.models.signals import post_save
from django.db import transaction
from django.db.models import Q
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from .models import ApprovalRequest
from .tasks import send_webpush_notification
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


def _get_user_display_name(user):
    full_name = user.get_full_name().strip()
    if full_name:
        return full_name
    return getattr(user, 'email', '') or getattr(user, 'username', '') or str(user.pk)


def _send_group_notification(channel_layer, user_id, payload):
    if not channel_layer:
        logger.warning("Notification channel layer unavailable for user %s", user_id)
        return False

    try:
        async_to_sync(channel_layer.group_send)(f"user_{user_id}", payload)
        return True
    except Exception:
        logger.exception("Failed to send websocket notification to user %s", user_id)
        return False


def _queue_webpush_notification(user_id, payload, ttl=1000):
    try:
        send_webpush_notification.delay(user_id=user_id, payload=payload, ttl=ttl)
        return True
    except Exception:
        logger.exception("Failed to queue webpush notification for user %s", user_id)
        return False

@receiver(post_save, sender=ApprovalRequest)
def notify_approval_request_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    requester_name = _get_user_display_name(instance.requester)
    
    if created:
        # Notify approvers in the tenant
        if instance.tenant:
            approvers = list(
                User.objects.filter(
                    tenant=instance.tenant,
                    is_active=True,
                ).filter(
                    Q(role__in=['approver', 'tenant_admin', 'superadmin', 'admin']) |
                    Q(is_staff=True) |
                    Q(is_superuser=True)
                )
            )
            
            logger.info(f"New request {instance.id}: Found {len(approvers)} approvers to notify.")

            def dispatch_created_notifications():
                for approver in approvers:
                    # Don't notify the requester if they are also an approver
                    if approver == instance.requester:
                        continue

                    message = _("New request from {name}: {title}").format(name=requester_name, title=instance.title)
                    _send_group_notification(
                        channel_layer,
                        approver.id,
                        {
                            "type": "notification_approval_request",
                            "request_id": instance.id,
                            "title": instance.title,
                            "requester_name": requester_name,
                            "status": instance.status,
                            "status_display": instance.get_status_display(),
                            "priority": instance.priority,
                            "category_display": instance.get_category_display(),
                            "created_at": instance.created_at.isoformat(),
                            "message": message,
                        }
                    )

                    payload = {
                        "title": _("New Request"),
                        "body": message,
                        "icon": "/static/img/logo-push-96.png",
                        "badge": "/static/img/badge-mono.png",
                        "color": "#4f46e5",
                        "image": None,
                        "url": f"/dashboard/{instance.id}/",
                        "tag": f"req-{instance.id}-new",
                        "renotify": True,
                        "requireInteraction": True,
                        "notificationType": "new_request",
                        "status": "pending",
                        "requestId": str(instance.id),
                        "vibrate": [200, 100, 200],
                        "actions": [
                            {
                                "action": "ver",
                                "title": _("View"),
                                "icon": "/static/img/icono-verde.png"
                            },
                            {
                                "action": "cerrar",
                                "title": _("Close"),
                                "icon": "/static/img/icono-cerrar.png"
                            }
                        ]
                    }
                    logger.info(f"Sending WebPush for request {instance.id} to user {approver.id}")
                    _queue_webpush_notification(user_id=approver.id, payload=payload, ttl=1000)

                _send_group_notification(
                    channel_layer,
                    instance.requester.id,
                    {
                        "type": "notification_approval_request",
                        "request_id": instance.id,
                        "title": instance.title,
                        "requester_name": requester_name,
                        "status": instance.status,
                        "status_display": instance.get_status_display(),
                        "priority": instance.priority,
                        "category_display": instance.get_category_display(),
                        "created_at": instance.created_at.isoformat(),
                        "message": _("Request created: {title}").format(title=instance.title)
                    }
                )

            transaction.on_commit(dispatch_created_notifications)
                
    else:
        # Notify requester of status change
        if instance.status in ['approved', 'rejected']:
            approver_name = instance.approver.get_full_name() if instance.approver else None
            status_display = instance.get_status_display()

            def dispatch_status_notifications():
                _send_group_notification(
                    channel_layer,
                    instance.requester.id,
                    {
                        "type": "notification_approval_status",
                        "request_id": instance.id,
                        "title": instance.title,
                        "status": instance.status,
                        "status_display": status_display,
                        "approver_name": approver_name,
                        "created_at": instance.created_at.isoformat(),
                        "category_display": instance.get_category_display(),
                        "message": _("Your request '{title}' has been {status}.").format(title=instance.title, status=status_display.lower())
                    }
                )

                notification_color = "#059669" if instance.status == 'approved' else "#dc2626"
                payload = {
                    "title": _("Request {status}").format(status=status_display),
                    "body": _("Your request '{title}' has been {status}.").format(title=instance.title, status=status_display.lower()),
                    "icon": "/static/img/logo-push-96.png",
                    "badge": "/static/img/badge-mono.png",
                    "color": notification_color,
                    "image": None,
                    "url": f"/dashboard/{instance.id}/",
                    "tag": f"req-{instance.id}-{instance.status}",
                    "renotify": True,
                    "requireInteraction": True,
                    "notificationType": instance.status,
                    "status": instance.status,
                    "requestId": str(instance.id),
                    "vibrate": [200, 100, 200],
                    "actions": [
                        {
                            "action": "ver",
                            "title": _("View"),
                            "icon": "/static/img/icono-verde.png"
                        },
                        {
                            "action": "cerrar",
                            "title": _("Close"),
                            "icon": "/static/img/icono-cerrar.png"
                        }
                    ]
                }
                _queue_webpush_notification(user_id=instance.requester.id, payload=payload, ttl=1000)

            transaction.on_commit(dispatch_status_notifications)
