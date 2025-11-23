import logging
from celery import shared_task
from webpush import send_user_notification
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task
def send_webpush_notification(user_id, payload, ttl=1000):
    """
    Async task to send web push notification
    """
    try:
        user = User.objects.get(id=user_id)
        send_user_notification(user=user, payload=payload, ttl=ttl)
        logger.info(f"WebPush sent to user {user_id}")
        return f"Notification sent to user {user_id}"
    except User.DoesNotExist:
        logger.error(f"WebPush failed: User {user_id} not found")
        return f"User {user_id} not found"
    except Exception as e:
        logger.error(f"WebPush failed for user {user_id}: {str(e)}")
        return f"Error sending notification to user {user_id}: {str(e)}"
