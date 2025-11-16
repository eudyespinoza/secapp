from django.utils import timezone
from django.core.cache import cache
from rest_framework import serializers

from apps.authentication.models import User
from .models import ChatConversation, ChatMessage, ChatMessageDelivery, ChatAttachment


class ChatAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatAttachment
        fields = ['id', 'filename', 'content_type', 'size', 'file', 'uploaded_at']


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_id = serializers.UUIDField(source='sender.id', read_only=True)
    attachments = ChatAttachmentSerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id',
            'conversation',
            'sender_id',
            'sender_name',
            'content',
            'has_attachments',
            'attachments',
            'created_at',
            'updated_at',
            'status',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'status', 'has_attachments']

    def get_status(self, obj):
        """
        Status for the current user.

        For recipients:
          - sent / delivered / read based on their delivery row.

        For the sender:
          - aggregated status across all recipients:
              read      -> at least one recipient read
              delivered -> at least one delivered
              sent      -> message created but not yet delivered
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        user = request.user

        # Recipient perspective
        try:
            delivery = obj.deliveries.get(recipient=user)
            return delivery.status
        except ChatMessageDelivery.DoesNotExist:
            pass

        # Sender perspective (DM: one or more recipients)
        if getattr(obj, "sender_id", None) == getattr(user, "id", None):
            deliveries = list(obj.deliveries.all())
            if not deliveries:
                return "sent"
            if any(d.read_at for d in deliveries):
                return "read"
            if any(d.delivered_at for d in deliveries):
                return "delivered"
            return "sent"

        return None


class ChatConversationSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatConversation
        fields = ['id', 'created_at', 'last_message', 'unread_count']

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if not last_msg:
            return None
        return ChatMessageSerializer(last_msg, context=self.context).data

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        return ChatMessageDelivery.objects.filter(
            message__conversation=obj,
            recipient=request.user,
            read_at__isnull=True,
        ).count()


class UserPresenceSerializer(serializers.ModelSerializer):
    is_online = serializers.SerializerMethodField()
    last_seen = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'is_online', 'last_seen']

    def _get_last_activity(self, obj):
        key = f"user:last_activity:{obj.pk}"
        return cache.get(key)

    def get_is_online(self, obj):
        last = self._get_last_activity(obj)
        if not last:
            return False
        # Consider online if active in last 60 seconds
        return last >= timezone.now() - timezone.timedelta(seconds=60)

    def get_last_seen(self, obj):
        return self._get_last_activity(obj)
