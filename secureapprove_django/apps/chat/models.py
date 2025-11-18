# ==================================================
# SecureApprove Django - Chat Models
# ==================================================

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = settings.AUTH_USER_MODEL


class ChatConversation(models.Model):
    """
    Conversation between users of the same tenant.
    Supports both 1-to-1 and group conversations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='chat_conversations',
    )
    title = models.CharField(
        _('Title'),
        max_length=255,
        blank=True,
        help_text=_('Optional title for group conversations'),
    )
    is_group = models.BooleanField(
        _('Is Group'),
        default=False,
        help_text=_('True for group conversations, False for 1-to-1'),
    )
    participants = models.ManyToManyField(
        User,
        through='ChatParticipant',
        related_name='chat_conversations',
    )
    last_message = models.ForeignKey(
        'ChatMessage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text=_('Cache of last message for quick access'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = _('Chat Conversation')
        verbose_name_plural = _('Chat Conversations')
        indexes = [
            models.Index(fields=['tenant', '-updated_at']),
        ]

    def __str__(self) -> str:
        if self.title:
            return f"{self.title} ({self.tenant_id})"
        return f"Conversation {self.id} (tenant={self.tenant_id})"


class ChatParticipant(models.Model):
    """
    Through model for conversation participants with additional metadata.
    Tracks per-participant read status and settings.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='participant_set',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_participant_set',
    )
    unread_count = models.PositiveIntegerField(
        _('Unread Count'),
        default=0,
        help_text=_('Cached count of unread messages'),
    )
    last_read_message = models.ForeignKey(
        'ChatMessage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        help_text=_('Last message this user has read'),
    )
    is_archived = models.BooleanField(
        _('Is Archived'),
        default=False,
        help_text=_('User has archived this conversation'),
    )
    is_muted = models.BooleanField(
        _('Is Muted'),
        default=False,
        help_text=_('User has muted notifications for this conversation'),
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('conversation', 'user')]
        verbose_name = _('Chat Participant')
        verbose_name_plural = _('Chat Participants')
        indexes = [
            models.Index(fields=['user', '-joined_at']),
            models.Index(fields=['conversation', 'user']),
        ]

    def __str__(self) -> str:
        return f"{self.user} in {self.conversation_id}"


class ChatMessage(models.Model):
    """
    Message inside a conversation.
    Supports text content and file attachments.
    """

    STATUS_CHOICES = [
        ('sent', _('Sent')),
        ('delivered', _('Delivered')),
        ('read', _('Read')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_messages',
    )
    content = models.TextField(
        _('Content'),
        blank=True,
        max_length=5000,
        help_text=_('Message text content'),
    )
    has_attachments = models.BooleanField(
        _('Has Attachments'),
        default=False,
    )
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='sent',
        help_text=_('Aggregated delivery status'),
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = _('Chat Message')
        verbose_name_plural = _('Chat Messages')
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', '-created_at']),
        ]

    def __str__(self) -> str:
        preview = self.content[:50] if self.content else '[No content]'
        return f"Message from {self.sender_id}: {preview}"

    def save(self, *args, **kwargs):
        """Update conversation's last_message and updated_at on save."""
        super().save(*args, **kwargs)
        if self.conversation:
            self.conversation.last_message = self
            self.conversation.updated_at = self.created_at
            self.conversation.save(update_fields=['last_message', 'updated_at'])



class ChatAttachment(models.Model):
    """
    File attached to a message.
    Enforces file size and type validation.
    """

    # Maximum file size: 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # Allowed MIME types
    ALLOWED_CONTENT_TYPES = [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain',
        'text/csv',
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    file = models.FileField(
        upload_to='chat_attachments/%Y/%m/',
        verbose_name=_('File'),
        max_length=500,
    )
    filename = models.CharField(
        _('Filename'),
        max_length=255,
        blank=True,
    )
    content_type = models.CharField(
        _('Content Type'),
        max_length=100,
        blank=True,
    )
    size = models.PositiveIntegerField(
        _('Size (bytes)'),
        default=0,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Chat Attachment')
        verbose_name_plural = _('Chat Attachments')
        indexes = [
            models.Index(fields=['message', 'uploaded_at']),
        ]

    def __str__(self) -> str:
        return f"{self.filename} ({self.size} bytes)"

    def save(self, *args, **kwargs):
        if self.file and not self.filename:
            self.filename = self.file.name
        if self.file and not self.size:
            try:
                self.size = self.file.size
            except Exception:
                self.size = 0
        if self.file and not self.content_type:
            self.content_type = getattr(self.file, 'content_type', '')
        super().save(*args, **kwargs)


class ChatMessageDelivery(models.Model):
    """
    Delivery/read state per recipient.
    
    Tracks message lifecycle for each participant:
    - sent_at: message was created
    - delivered_at: recipient has fetched the message via API
    - read_at: recipient has opened the conversation and marked as read
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='deliveries',
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_deliveries',
    )
    sent_at = models.DateTimeField(default=timezone.now)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('message', 'recipient')]
        verbose_name = _('Chat Message Delivery')
        verbose_name_plural = _('Chat Message Deliveries')
        indexes = [
            models.Index(fields=['recipient', 'read_at']),
            models.Index(fields=['message', 'recipient']),
        ]

    def __str__(self) -> str:
        return f"Delivery to {self.recipient} - {self.status}"

    @property
    def status(self) -> str:
        """
        Simple status string: sent / delivered / read
        """
        if self.read_at:
            return 'read'
        if self.delivered_at:
            return 'delivered'
        return 'sent'


class UserPresence(models.Model):
    """
    Stores user presence/activity information.
    Alternative to cache-based approach for persistence.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='chat_presence',
    )
    last_activity = models.DateTimeField(
        _('Last Activity'),
        default=timezone.now,
        db_index=True,
    )
    is_online = models.BooleanField(
        _('Is Online'),
        default=False,
        help_text=_('Computed field: online if last_activity is recent'),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('User Presence')
        verbose_name_plural = _('User Presences')

    def __str__(self) -> str:
        return f"{self.user} - {'Online' if self.is_online else 'Offline'}"

    def update_activity(self):
        """Update last activity timestamp and online status."""
        self.last_activity = timezone.now()
        self.is_online = True
        self.save(update_fields=['last_activity', 'is_online', 'updated_at'])

    @classmethod
    def mark_user_online(cls, user):
        """Mark a user as online (create or update presence)."""
        presence, _ = cls.objects.get_or_create(user=user)
        presence.update_activity()
        return presence

    @classmethod
    def compute_online_status(cls, threshold_seconds=120):
        """
        Compute online status for all users based on last activity.
        Users with activity within threshold_seconds are marked online.
        """
        threshold = timezone.now() - timezone.timedelta(seconds=threshold_seconds)
        cls.objects.filter(last_activity__gte=threshold).update(is_online=True)
        cls.objects.filter(last_activity__lt=threshold).update(is_online=False)


