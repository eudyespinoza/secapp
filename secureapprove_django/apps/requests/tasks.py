import logging
from celery import shared_task
from webpush import send_user_notification
from django.contrib.auth import get_user_model
from django.conf import settings

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={'max_retries': 3})
def send_webpush_notification(self, user_id, payload, ttl=None):
    """
    Async task to send web push notification
    """
    ttl_value = ttl if ttl is not None else getattr(settings, 'WEBPUSH_DEFAULT_TTL', 86400)

    try:
        user = User.objects.get(id=user_id)
        send_user_notification(user=user, payload=payload, ttl=ttl_value)
        logger.info(f"WebPush sent to user {user_id} (ttl={ttl_value})")
        return f"Notification sent to user {user_id}"
    except User.DoesNotExist:
        logger.error(f"WebPush failed: User {user_id} not found")
        return f"User {user_id} not found"
    except Exception as e:
        logger.error(f"WebPush failed for user {user_id}: {str(e)}")
        return f"Error sending notification to user {user_id}: {str(e)}"
