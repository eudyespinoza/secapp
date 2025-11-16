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
    For ahora modelamos DM (2 participantes), pero se puede extender a más.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='chat_conversations',
    )
    participants = models.ManyToManyField(
        User,
        related_name='chat_conversations',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Chat Conversation')
        verbose_name_plural = _('Chat Conversations')

    def __str__(self) -> str:
        return f"Conversation {self.id} (tenant={self.tenant_id})"


class ChatMessage(models.Model):
    """
    Message inside a conversation.
    """

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
    content = models.TextField(blank=True)
    has_attachments = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = _('Chat Message')
        verbose_name_plural = _('Chat Messages')

    def __str__(self) -> str:
        return f"Message {self.id} from {self.sender_id}"


class ChatAttachment(models.Model):
    """
    File attached to a message.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    file = models.FileField(
        upload_to='chat_attachments/',
        verbose_name=_('File'),
    )
    filename = models.CharField(_('Filename'), max_length=255, blank=True)
    content_type = models.CharField(_('Content Type'), max_length=100, blank=True)
    size = models.PositiveIntegerField(_('Size (bytes)'), default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Chat Attachment')
        verbose_name_plural = _('Chat Attachments')

    def save(self, *args, **kwargs):
        if self.file and not self.filename:
            self.filename = self.file.name
        if self.file and not self.size:
            try:
                self.size = self.file.size
            except Exception:
                self.size = 0
        super().save(*args, **kwargs)


class ChatMessageDelivery(models.Model):
    """
    Delivery/read state per recipient.

      sent_at:    message created for this recipient
      delivered_at: recipient ha recuperado el mensaje vía API
      read_at:    recipient ha abierto la conversación y marcado como leído
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
        unique_together = ('message', 'recipient')
        verbose_name = _('Chat Message Delivery')
        verbose_name_plural = _('Chat Message Deliveries')

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

