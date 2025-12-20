from django.utils import timezone
from django.core.cache import cache
from rest_framework import serializers

from apps.authentication.models import User
from .models import (
    ChatConversation,
    ChatParticipant,
    ChatMessage,
    ChatMessageDelivery,
    ChatAttachment,
    UserPresence,
)


class ChatAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for chat file attachments."""

    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ChatAttachment
        fields = ['id', 'filename', 'content_type', 'size', 'file', 'file_url', 'download_url', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at', 'size', 'content_type']

    def get_file_url(self, obj):
        """Return absolute URL for file."""
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None

    def get_download_url(self, obj):
        """Return absolute URL for forced download."""
        request = self.context.get('request')
        if obj.file and request:
            # Replace /media/ with /media/download/ to force download
            file_url = obj.file.url
            download_path = file_url.replace('/media/', '/media/download/')
            return request.build_absolute_uri(download_path)
        elif obj.file:
            return obj.file.url.replace('/media/', '/media/download/')
        return None

    def validate_file(self, value):
        """Validate file size and content type."""
        if value.size > ChatAttachment.MAX_FILE_SIZE:
            raise serializers.ValidationError(
                f'File size must be under {ChatAttachment.MAX_FILE_SIZE / (1024*1024)}MB'
            )

        return value



class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages with delivery status."""

    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    attachments = ChatAttachmentSerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id',
            'conversation',
            'sender_id',
            'sender_name',
            'sender_email',
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
            return 'sent'

        user = request.user

        # Recipient perspective
        try:
            delivery = obj.deliveries.get(recipient=user)
            return delivery.status
        except ChatMessageDelivery.DoesNotExist:
            pass

        # Sender perspective
        if getattr(obj, "sender_id", None) == getattr(user, "id", None):
            deliveries = list(obj.deliveries.all())
            if not deliveries:
                return "sent"
            if any(d.read_at for d in deliveries):
                return "read"
            if any(d.delivered_at for d in deliveries):
                return "delivered"
            return "sent"

        return "sent"

    def validate_content(self, value):
        """Validate message content length."""
        if value and len(value) > 5000:
            raise serializers.ValidationError('Message content must be under 5000 characters')
        return value



class ChatParticipantSerializer(serializers.ModelSerializer):
    """Serializer for conversation participants."""

    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = ChatParticipant
        fields = [
            'id',
            'user_id',
            'user_name',
            'user_email',
            'unread_count',
            'is_archived',
            'is_muted',
            'joined_at',
        ]
        read_only_fields = ['id', 'joined_at', 'unread_count']


class ChatConversationSerializer(serializers.ModelSerializer):
    """Serializer for conversations with last message and participant info."""

    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    is_group = serializers.BooleanField(read_only=True)

    class Meta:
        model = ChatConversation
        fields = [
            'id',
            'title',
            'is_group',
            'created_at',
            'updated_at',
            'last_message',
            'unread_count',
            'participants',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        """Get the last message in the conversation."""
        if obj.last_message:
            return ChatMessageSerializer(obj.last_message, context=self.context).data
        
        # Fallback if last_message cache is not set
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return ChatMessageSerializer(last_msg, context=self.context).data
        return None

    def get_unread_count(self, obj):
        """Get unread message count for current user."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0

        try:
            participant = obj.participant_set.get(user=request.user)
            return participant.unread_count
        except ChatParticipant.DoesNotExist:
            return 0

    def get_participants(self, obj):
        """Get list of participants with basic info."""
        # Use select_related to avoid N+1 queries
        participants = obj.participant_set.select_related('user').all()
        return [
            {
                'id': p.user.id,
                'name': p.user.get_full_name(),
                'email': p.user.email,
            }
            for p in participants
        ]

    def get_title(self, obj):
        """
        Human-friendly conversation title.

        For direct messages, uses the other participant's name/email.
        For group conversations, uses the title or joins participant names.
        """
        # If title is set, use it
        if obj.title:
            return obj.title

        request = self.context.get('request')
        user = getattr(request, 'user', None)

        # Get participants excluding current user
        participants = obj.participant_set.select_related('user').all()
        others = [p.user for p in participants]
        if user and getattr(user, 'is_authenticated', False):
            others = [u for u in others if u.id != user.id]

        # For 1-to-1: use other person's name
        if len(others) == 1:
            other = others[0]
            return other.get_full_name() or other.email

        # For groups: join names
        if others:
            names = [u.get_full_name() or u.email for u in others[:3]]
            if len(others) > 3:
                names.append(f'+{len(others) - 3} more')
            return ", ".join(names)

        # Fallback
        return f"Conversation"



class UserPresenceSerializer(serializers.ModelSerializer):
    """Serializer for user presence information."""

    is_online = serializers.SerializerMethodField()
    last_seen = serializers.DateTimeField(source='last_activity', read_only=True)
    name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'is_online', 'last_seen']
        read_only_fields = ['id', 'name', 'email']

    def get_is_online(self, obj):
        """
        Determine if user is online based on last activity.
        Uses both UserPresence model and cache.
        """
        # Try UserPresence model first
        try:
            presence = obj.chat_presence
            # Consider online if activity within last 2 minutes
            threshold = timezone.now() - timezone.timedelta(seconds=120)
            return presence.last_activity >= threshold
        except (UserPresence.DoesNotExist, AttributeError):
            pass

        # Fallback to cache-based presence
        key = f"user:last_activity:{obj.pk}"
        last_activity = cache.get(key)
        if not last_activity:
            return False
        
        threshold = timezone.now() - timezone.timedelta(seconds=120)
        return last_activity >= threshold

