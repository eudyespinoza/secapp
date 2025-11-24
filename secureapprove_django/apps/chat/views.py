import logging

from django.db import transaction
from django.db.models import Q, Prefetch
from django.utils import timezone
from django.views.generic import TemplateView
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils.translation import gettext as _

from apps.authentication.models import User
from apps.tenants.utils import ensure_user_tenant
from apps.requests.tasks import send_webpush_notification
from .models import (
    ChatConversation,
    ChatParticipant,
    ChatMessage,
    ChatMessageDelivery,
    ChatAttachment,
    UserPresence,
)
from .serializers import (
    ChatConversationSerializer,
    ChatMessageSerializer,
    UserPresenceSerializer,
    ChatAttachmentSerializer,
)

try:
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
except Exception:  # pragma: no cover
    async_to_sync = None
    get_channel_layer = None

logger = logging.getLogger(__name__)


class ChatPageView(TemplateView):
    """
    Simple template-based chat UI for tenant users.
    """

    template_name = 'chat/chat.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('authentication:webauthn_login')
        
        # Update presence
        UserPresence.mark_user_online(request.user)
        cache.set(f"user:last_activity:{request.user.pk}", timezone.now(), timeout=3600)
        
        return super().dispatch(request, *args, **kwargs)


def broadcast_to_conversation(conversation, event_type, payload):
    """
    Helper to broadcast WebSocket events to all participants in a conversation.

    Sends a single event to the tenant-wide chat channel so every user that
    belongs to the tenant receives the update in real time (frontend filters
    automatically based on the conversation data it already has).
    """
    if not async_to_sync or not get_channel_layer or not conversation:
        return

    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        async_to_sync(channel_layer.group_send)(
            f"tenant_{conversation.tenant_id}_chat",
            {
                "type": event_type,
                **payload,
            },
        )
    except Exception as e:
        # Log but don't fail the request
        logger.warning("WebSocket broadcast error for conversation %s: %s", conversation.id, e)


@method_decorator(csrf_exempt, name="dispatch")
class ChatConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing chat conversations.
    
    Provides:
    - List conversations for current user
    - Create/get 1-to-1 conversations
    - Retrieve, update, delete conversations
    - Nested routes for messages
    - Mark as read, typing indicators, presence
    """

    serializer_class = ChatConversationSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = None

    def get_queryset(self):
        """Get conversations for current user in their tenant."""
        user = self.request.user
        tenant = ensure_user_tenant(user)
        if not tenant:
            return ChatConversation.objects.none()

        # Optimize queries with select_related and prefetch_related
        queryset = ChatConversation.objects.filter(
            tenant=tenant,
            participant_set__user=user,
        ).select_related(
            'tenant',
            'last_message',
            'last_message__sender',
        ).prefetch_related(
            Prefetch(
                'participant_set',
                queryset=ChatParticipant.objects.select_related('user')
            ),
            'last_message__attachments',
        ).distinct().order_by('-updated_at')

        return queryset

    def list(self, request, *args, **kwargs):
        """Return conversations as a flat array (no pagination) for the widget."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

        logger.info(
            "[CHAT] /api/chat/conversations/ returned %s items for user %s",
            len(data),
            getattr(request.user, "id", None),
        )
        logger.debug("[CHAT] conversations payload: %s", data)
        return Response(data)

    def perform_authentication(self, request):
        """Update user presence on every API call."""
        super().perform_authentication(request)
        if request.user.is_authenticated:
            UserPresence.mark_user_online(request.user)
            cache.set(f"user:last_activity:{request.user.pk}", timezone.now(), timeout=3600)

    @action(detail=False, methods=['post'])
    def start(self, request):
        """
        Start or get a 1-to-1 conversation with another user.
        
        Body: { "participant_id": "<user_id>" }
        
        Returns existing conversation if one exists, otherwise creates new one.
        """
        user = request.user
        tenant = ensure_user_tenant(user)
        if not tenant:
            return Response(
                {'error': 'No tenant associated with current user'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        participant_id = request.data.get('participant_id')
        if not participant_id:
            return Response(
                {'error': 'participant_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate participant exists and is in same tenant
        try:
            other = User.objects.get(id=participant_id, tenant=tenant, is_active=True)
        except User.DoesNotExist:
            return Response(
                {'error': 'Participant not found in your tenant'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if other.id == user.id:
            return Response(
                {'error': 'Cannot start conversation with yourself'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if 1-to-1 conversation already exists
        # Find conversations where both users are participants and it's not a group
        with transaction.atomic():
            existing = ChatConversation.objects.filter(
                tenant=tenant,
                is_group=False,
                participant_set__user=user,
            ).filter(
                participant_set__user=other,
            ).first()

            if existing:
                serializer = self.get_serializer(existing)
                return Response(serializer.data)

            # Create new conversation
            conv = ChatConversation.objects.create(
                tenant=tenant,
                is_group=False,
            )
            
            # Add participants
            ChatParticipant.objects.create(conversation=conv, user=user)
            ChatParticipant.objects.create(conversation=conv, user=other)

        serializer = self.get_serializer(conv)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


    @action(detail=True, methods=['get', 'post'])
    def messages(self, request, pk=None):
        """
        GET: List messages for a conversation (with optional pagination by since_id)
        POST: Send a new message (text + optional attachments)
        """
        conv = self.get_object()
        user = request.user

        # Verify user is participant
        if not conv.participant_set.filter(user=user).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if request.method == 'GET':
            # Get messages, optionally filtering by since_id
            since_id = request.query_params.get('since_id')
            qs = conv.messages.select_related('sender').prefetch_related('attachments')
            
            if since_id:
                try:
                    last_msg = conv.messages.get(id=since_id)
                    qs = qs.filter(created_at__gt=last_msg.created_at)
                except ChatMessage.DoesNotExist:
                    pass  # Return all messages if reference doesn't exist

            # Mark as delivered for current user
            ChatMessageDelivery.objects.filter(
                message__in=qs,
                recipient=user,
                delivered_at__isnull=True
            ).update(delivered_at=timezone.now())

            serializer = ChatMessageSerializer(
                qs,
                many=True,
                context={'request': request}
            )
            return Response(serializer.data)

        # POST: Create new message
        content = request.data.get('content', '').strip()
        files = request.FILES.getlist('attachments')

        # Validation
        if not content and not files:
            return Response(
                {'error': 'Message content or attachment is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if content and len(content) > 5000:
            return Response(
                {'error': 'Message content must be under 5000 characters'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate attachments
        for f in files:
            if f.size > ChatAttachment.MAX_FILE_SIZE:
                return Response(
                    {'error': f'File {f.name} exceeds maximum size of {ChatAttachment.MAX_FILE_SIZE / (1024*1024)}MB'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            # Create message with attachments
            with transaction.atomic():
                msg = ChatMessage.objects.create(
                    conversation=conv,
                    sender=user,
                    content=content,
                    has_attachments=bool(files),
                )

                # Create attachments
                for f in files:
                    ChatAttachment.objects.create(
                        message=msg,
                        file=f,
                        filename=f.name,
                        size=f.size,
                        content_type=getattr(f, 'content_type', ''),
                    )

                # Create delivery records for all participants except sender
                recipients = conv.participant_set.exclude(user=user).select_related('user')
                now = timezone.now()
                deliveries = [
                    ChatMessageDelivery(
                        message=msg,
                        recipient=recipient.user,
                        sent_at=now,
                    )
                    for recipient in recipients
                ]
                ChatMessageDelivery.objects.bulk_create(deliveries)

                # Update unread counts for recipients
                for recipient in recipients:
                    recipient.unread_count += 1
                    recipient.save(update_fields=['unread_count'])

                    # Send Web Push Notification
                    if not recipient.is_muted:
                        payload = {
                            "title": _("New message from {name}").format(name=user.get_full_name() or user.email),
                            "body": content[:100] if content else _("Sent an attachment"),
                            "icon": "/static/img/logo.png",
                            "tag": f"chat-{conv.id}",
                            "url": f"/dashboard/?chat_id={conv.id}"
                        }
                        try:
                            send_webpush_notification.delay(user_id=recipient.user.id, payload=payload, ttl=1000)
                        except Exception as e:
                            logger.error(f"Failed to queue webpush notification: {e}")

            # Serialize response
            serializer = ChatMessageSerializer(msg, context={'request': request})

            logger.info(
                "[CHAT] Sending WS message_created conversation=%s tenant=%s message=%s",
                conv.id,
                conv.tenant_id,
                msg.id,
            )

            # Broadcast via WebSocket
            broadcast_to_conversation(
                conv,
                "chat_message_created",
                {
                    "conversation_id": str(conv.id),
                    "message": serializer.data,
                },
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating message: {e}", exc_info=True)
            return Response(
                {'error': f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark all messages in conversation as read for current user.
        Updates delivery records and resets unread counter.
        """
        conv = self.get_object()
        user = request.user
        now = timezone.now()

        with transaction.atomic():
            # Mark all unread deliveries as read
            updated_count = ChatMessageDelivery.objects.filter(
                message__conversation=conv,
                recipient=user,
                read_at__isnull=True,
            ).update(read_at=now, delivered_at=now)

            # Reset unread count and update last read message for this participant
            last_message = conv.messages.order_by('-created_at').first()
            update_kwargs = {'unread_count': 0}
            if last_message:
                update_kwargs['last_read_message'] = last_message

            ChatParticipant.objects.filter(
                conversation=conv,
                user=user,
            ).update(**update_kwargs)

        return Response({
            'status': 'ok',
            'marked_read': updated_count,
        })

    @action(detail=True, methods=['post'])
    def typing(self, request, pk=None):
        """
        Notify other participants that user is typing.
        Broadcasts a typing event via WebSocket.
        """
        conv = self.get_object()
        user = request.user

        # Verify user is participant
        if not conv.participant_set.filter(user=user).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Update presence
        UserPresence.mark_user_online(user)
        cache.set(f"user:last_activity:{user.pk}", timezone.now(), timeout=3600)

        # Broadcast typing event
        broadcast_to_conversation(
            conv,
            "chat_typing",
            {
                "conversation_id": str(conv.id),
                "user_id": user.id,
                "user_name": user.get_full_name() or user.email,
            },
        )

        return Response({'status': 'ok'})

    @action(detail=False, methods=['get'])
    def presence(self, request):
        """
        Get presence info for all users in the same tenant.
        Returns list with online/offline status.
        """
        user = request.user
        tenant = ensure_user_tenant(user)
        if not tenant:
            return Response([], status=status.HTTP_200_OK)

        # Update user presence computation
        UserPresence.compute_online_status(threshold_seconds=120)

        # Get all active users in tenant
        qs = User.objects.filter(
            tenant=tenant,
            is_active=True,
        ).select_related('chat_presence').order_by('email')

        serializer = UserPresenceSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def archive(self, request, pk=None):
        """Archive conversation for current user."""
        conv = self.get_object()
        user = request.user

        ChatParticipant.objects.filter(
            conversation=conv,
            user=user,
        ).update(is_archived=True)

        return Response({'status': 'archived'})

    @action(detail=True, methods=['patch'])
    def unarchive(self, request, pk=None):
        """Unarchive conversation for current user."""
        conv = self.get_object()
        user = request.user

        ChatParticipant.objects.filter(
            conversation=conv,
            user=user,
        ).update(is_archived=False)

        return Response({'status': 'unarchived'})

    @action(detail=True, methods=['patch'])
    def mute(self, request, pk=None):
        """Mute notifications for conversation."""
        conv = self.get_object()
        user = request.user

        ChatParticipant.objects.filter(
            conversation=conv,
            user=user,
        ).update(is_muted=True)

        return Response({'status': 'muted'})

    @action(detail=True, methods=['patch'])
    def unmute(self, request, pk=None):
        """Unmute notifications for conversation."""
        conv = self.get_object()
        user = request.user

        ChatParticipant.objects.filter(
            conversation=conv,
            user=user,
        ).update(is_muted=False)

        return Response({'status': 'unmuted'})

