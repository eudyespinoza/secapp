"""
Admin configuration for Chat app.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    ChatConversation,
    ChatParticipant,
    ChatMessage,
    ChatMessageDelivery,
    ChatAttachment,
    UserPresence,
)


class ChatParticipantInline(admin.TabularInline):
    """Inline admin for conversation participants."""
    model = ChatParticipant
    extra = 0
    fields = ['user', 'unread_count', 'is_archived', 'is_muted', 'joined_at']
    readonly_fields = ['joined_at']
    raw_id_fields = ['user']


class ChatMessageInline(admin.TabularInline):
    """Inline admin for conversation messages."""
    model = ChatMessage
    extra = 0
    fields = ['sender', 'content_preview', 'has_attachments', 'status', 'created_at']
    readonly_fields = ['sender', 'content_preview', 'has_attachments', 'status', 'created_at']
    can_delete = False
    
    def content_preview(self, obj):
        """Show truncated message content."""
        if obj.content:
            return obj.content[:100] + ('...' if len(obj.content) > 100 else '')
        return '[No content]'
    content_preview.short_description = 'Message Preview'
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    """Admin for chat conversations."""
    
    list_display = [
        'id_short',
        'tenant',
        'title_display',
        'is_group',
        'participant_count',
        'message_count',
        'last_message_date',
        'created_at',
    ]
    
    list_filter = [
        'is_group',
        'tenant',
        'created_at',
        'updated_at',
    ]
    
    search_fields = [
        'id',
        'title',
        'tenant__name',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'last_message_preview',
        'participant_list',
    ]
    
    fields = [
        'id',
        'tenant',
        'title',
        'is_group',
        'last_message',
        'created_at',
        'updated_at',
        'last_message_preview',
        'participant_list',
    ]
    
    inlines = [ChatParticipantInline, ChatMessageInline]
    
    def id_short(self, obj):
        """Show shortened UUID."""
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def title_display(self, obj):
        """Show conversation title or generate one."""
        if obj.title:
            return obj.title
        
        participants = obj.participant_set.select_related('user')[:3]
        names = [p.user.get_full_name() or p.user.email for p in participants]
        
        if len(names) > 2:
            return f"{', '.join(names[:2])} +{len(names) - 2} more"
        return ', '.join(names) or '[No participants]'
    title_display.short_description = 'Title/Participants'
    
    def participant_count(self, obj):
        """Count participants."""
        return obj.participant_set.count()
    participant_count.short_description = 'Participants'
    
    def message_count(self, obj):
        """Count messages."""
        count = obj.messages.count()
        if count > 0:
            url = reverse('admin:chat_chatmessage_changelist') + f'?conversation__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    message_count.short_description = 'Messages'
    
    def last_message_date(self, obj):
        """Show last message timestamp."""
        if obj.last_message:
            return obj.last_message.created_at
        return None
    last_message_date.short_description = 'Last Message'
    
    def last_message_preview(self, obj):
        """Show preview of last message."""
        if obj.last_message:
            msg = obj.last_message
            sender = msg.sender.get_full_name() or msg.sender.email
            content = msg.content[:100] if msg.content else '[No content]'
            return format_html(
                '<strong>{}:</strong> {}',
                sender,
                content
            )
        return 'No messages yet'
    last_message_preview.short_description = 'Last Message Preview'
    
    def participant_list(self, obj):
        """Show list of all participants."""
        participants = obj.participant_set.select_related('user').all()
        items = []
        for p in participants:
            user_url = reverse('admin:authentication_user_change', args=[p.user.id])
            items.append(
                f'<li><a href="{user_url}">{p.user.get_full_name() or p.user.email}</a> '
                f'(unread: {p.unread_count})'
                f'{" [MUTED]" if p.is_muted else ""}'
                f'{" [ARCHIVED]" if p.is_archived else ""}</li>'
            )
        return mark_safe(f'<ul>{"".join(items)}</ul>')
    participant_list.short_description = 'All Participants'


@admin.register(ChatParticipant)
class ChatParticipantAdmin(admin.ModelAdmin):
    """Admin for conversation participants."""
    
    list_display = [
        'conversation_short',
        'user',
        'unread_count',
        'is_archived',
        'is_muted',
        'joined_at',
    ]
    
    list_filter = [
        'is_archived',
        'is_muted',
        'joined_at',
    ]
    
    search_fields = [
        'user__email',
        'user__first_name',
        'user__last_name',
        'conversation__id',
    ]
    
    readonly_fields = ['joined_at']
    
    raw_id_fields = ['user']
    autocomplete_fields = ['conversation', 'last_read_message']
    
    def conversation_short(self, obj):
        """Show conversation link."""
        url = reverse('admin:chat_chatconversation_change', args=[obj.conversation.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            str(obj.conversation.id)[:8]
        )
    conversation_short.short_description = 'Conversation'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin for chat messages."""
    
    list_display = [
        'id_short',
        'conversation_short',
        'sender',
        'content_preview',
        'has_attachments',
        'attachment_count',
        'status',
        'created_at',
    ]
    
    list_filter = [
        'has_attachments',
        'status',
        'created_at',
    ]
    
    search_fields = [
        'id',
        'content',
        'sender__email',
        'sender__first_name',
        'sender__last_name',
        'conversation__id',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'full_content',
        'delivery_status',
    ]
    
    fields = [
        'id',
        'conversation',
        'sender',
        'full_content',
        'has_attachments',
        'status',
        'created_at',
        'updated_at',
        'delivery_status',
    ]
    
    raw_id_fields = ['sender']
    autocomplete_fields = ['conversation']
    
    def id_short(self, obj):
        """Show shortened UUID."""
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def conversation_short(self, obj):
        """Show conversation link."""
        url = reverse('admin:chat_chatconversation_change', args=[obj.conversation.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            str(obj.conversation.id)[:8]
        )
    conversation_short.short_description = 'Conversation'
    
    def content_preview(self, obj):
        """Show truncated content."""
        if obj.content:
            return obj.content[:50] + ('...' if len(obj.content) > 50 else '')
        return '[No content]'
    content_preview.short_description = 'Preview'
    
    def full_content(self, obj):
        """Show full message content."""
        return obj.content or '[No content]'
    full_content.short_description = 'Full Message'
    
    def attachment_count(self, obj):
        """Count attachments."""
        if not obj.has_attachments:
            return 0
        count = obj.attachments.count()
        if count > 0:
            url = reverse('admin:chat_chatattachment_changelist') + f'?message__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    attachment_count.short_description = 'Attachments'
    
    def delivery_status(self, obj):
        """Show delivery status for all recipients."""
        deliveries = obj.deliveries.select_related('recipient').all()
        items = []
        for d in deliveries:
            status_color = {
                'read': 'green',
                'delivered': 'orange',
                'sent': 'gray',
            }.get(d.status, 'gray')
            items.append(
                f'<li><strong>{d.recipient.get_full_name() or d.recipient.email}:</strong> '
                f'<span style="color: {status_color};">{d.status.upper()}</span></li>'
            )
        if items:
            return mark_safe(f'<ul>{"".join(items)}</ul>')
        return 'No deliveries'
    delivery_status.short_description = 'Delivery Status'


@admin.register(ChatMessageDelivery)
class ChatMessageDeliveryAdmin(admin.ModelAdmin):
    """Admin for message delivery tracking."""
    
    list_display = [
        'message_short',
        'recipient',
        'status_display',
        'sent_at',
        'delivered_at',
        'read_at',
    ]
    
    list_filter = [
        'sent_at',
        'delivered_at',
        'read_at',
    ]
    
    search_fields = [
        'message__id',
        'message__content',
        'recipient__email',
        'recipient__first_name',
        'recipient__last_name',
    ]
    
    readonly_fields = [
        'sent_at',
        'delivered_at',
        'read_at',
        'status_display',
    ]
    
    raw_id_fields = ['recipient']
    autocomplete_fields = ['message']
    
    def message_short(self, obj):
        """Show message link."""
        url = reverse('admin:chat_chatmessage_change', args=[obj.message.id])
        content = obj.message.content[:30] if obj.message.content else '[No content]'
        return format_html(
            '<a href="{}">{}</a>',
            url,
            content
        )
    message_short.short_description = 'Message'
    
    def status_display(self, obj):
        """Show status with color."""
        status = obj.status
        color = {
            'read': 'green',
            'delivered': 'orange',
            'sent': 'gray',
        }.get(status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status.upper()
        )
    status_display.short_description = 'Status'


@admin.register(ChatAttachment)
class ChatAttachmentAdmin(admin.ModelAdmin):
    """Admin for message attachments."""
    
    list_display = [
        'id_short',
        'message_short',
        'filename',
        'content_type',
        'size_display',
        'file_link',
        'uploaded_at',
    ]
    
    list_filter = [
        'content_type',
        'uploaded_at',
    ]
    
    search_fields = [
        'id',
        'filename',
        'message__id',
        'message__content',
    ]
    
    readonly_fields = [
        'id',
        'size',
        'uploaded_at',
        'file_preview',
    ]
    
    fields = [
        'id',
        'message',
        'file',
        'filename',
        'content_type',
        'size',
        'uploaded_at',
        'file_preview',
    ]
    
    autocomplete_fields = ['message']
    
    def id_short(self, obj):
        """Show shortened UUID."""
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def message_short(self, obj):
        """Show message link."""
        url = reverse('admin:chat_chatmessage_change', args=[obj.message.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            str(obj.message.id)[:8]
        )
    message_short.short_description = 'Message'
    
    def size_display(self, obj):
        """Show file size in human-readable format."""
        size = obj.size
        if size < 1024:
            return f'{size} B'
        elif size < 1024 * 1024:
            return f'{size / 1024:.1f} KB'
        else:
            return f'{size / (1024 * 1024):.1f} MB'
    size_display.short_description = 'Size'
    
    def file_link(self, obj):
        """Show link to download file."""
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">Download</a>',
                obj.file.url
            )
        return 'No file'
    file_link.short_description = 'File'
    
    def file_preview(self, obj):
        """Show image preview if applicable."""
        if obj.file and obj.content_type.startswith('image/'):
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px;" />',
                obj.file.url
            )
        return 'No preview available'
    file_preview.short_description = 'Preview'


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    """Admin for user presence tracking."""
    
    list_display = [
        'user',
        'is_online_display',
        'last_activity',
        'updated_at',
    ]
    
    list_filter = [
        'is_online',
        'last_activity',
        'updated_at',
    ]
    
    search_fields = [
        'user__email',
        'user__first_name',
        'user__last_name',
    ]
    
    readonly_fields = [
        'last_activity',
        'updated_at',
    ]
    
    fields = [
        'user',
        'last_activity',
        'is_online',
        'updated_at',
    ]
    
    raw_id_fields = ['user']
    
    actions = ['mark_online', 'mark_offline', 'compute_status']
    
    def is_online_display(self, obj):
        """Show online status with color."""
        if obj.is_online:
            return format_html(
                '<span style="color: green; font-weight: bold;">● ONLINE</span>'
            )
        return format_html(
            '<span style="color: gray;">○ OFFLINE</span>'
        )
    is_online_display.short_description = 'Status'
    
    def mark_online(self, request, queryset):
        """Mark selected users as online."""
        for presence in queryset:
            presence.update_activity()
        self.message_user(request, f'{queryset.count()} users marked as online.')
    mark_online.short_description = 'Mark as online'
    
    def mark_offline(self, request, queryset):
        """Mark selected users as offline."""
        queryset.update(is_online=False)
        self.message_user(request, f'{queryset.count()} users marked as offline.')
    mark_offline.short_description = 'Mark as offline'
    
    def compute_status(self, request, queryset):
        """Recompute online status for all users."""
        UserPresence.compute_online_status()
        self.message_user(request, 'Online status recomputed for all users.')
    compute_status.short_description = 'Recompute online status (all)'
