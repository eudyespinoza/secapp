from django.db import transaction
from django.utils import timezone
from django.views.generic import TemplateView
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.authentication.models import User
from apps.tenants.utils import ensure_user_tenant
from .models import ChatConversation, ChatMessage, ChatMessageDelivery, ChatAttachment
from .serializers import (
    ChatConversationSerializer,
    ChatMessageSerializer,
    UserPresenceSerializer,
)


class ChatPageView(TemplateView):
    """
    Simple template-based chat UI for tenant users.
    """

    template_name = 'chat/chat.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect

            return redirect('authentication:webauthn_login')
        # Update presence in cache
        cache.set(f"user:last_activity:{request.user.pk}", timezone.now(), timeout=3600)
        return super().dispatch(request, *args, **kwargs)


@method_decorator(csrf_exempt, name="dispatch")
class ChatConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Conversation list and creation for current tenant/user.
    """

    serializer_class = ChatConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        tenant = ensure_user_tenant(user)
        if not tenant:
            return ChatConversation.objects.none()
        return ChatConversation.objects.filter(
            tenant=tenant,
            participants=user,
        ).distinct()

    def perform_authentication(self, request):
        super().perform_authentication(request)
        # Update presence in cache
        if request.user.is_authenticated:
            cache.set(f"user:last_activity:{request.user.pk}", timezone.now(), timeout=3600)

    @action(detail=False, methods=['post'])
    def start(self, request):
        """
        Start or get a conversation with another participant in the same tenant.
        Body: { "participant_id": "<uuid>" }
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

        try:
            other = User.objects.get(id=participant_id, tenant=tenant)
        except User.DoesNotExist:
            return Response(
                {'error': 'Participant not found in your tenant'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Reuse existing DM if exists
        conv = ChatConversation.objects.filter(
            tenant=tenant,
            participants=user,
        ).filter(participants=other).first()
        if not conv:
            conv = ChatConversation.objects.create(tenant=tenant)
            conv.participants.add(user, other)

        serializer = self.get_serializer(conv)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def messages(self, request, pk=None):
        """
        GET: list messages for a conversation (optionally since message id or timestamp)
        POST: send message (content + optional attachment)
        """
        conv = self.get_object()
        user = request.user

        if request.method == 'GET':
            since_id = request.query_params.get('since_id')
            qs = conv.messages.all()
            if since_id:
                qs = qs.filter(id__gt=since_id)

            # Mark as delivered for current user
            ChatMessageDelivery.objects.filter(
                message__in=qs, recipient=user, delivered_at__isnull=True
            ).update(delivered_at=timezone.now())

            serializer = ChatMessageSerializer(qs, many=True, context={'request': request})
            return Response(serializer.data)

        # POST: create message
        content = request.data.get('content', '').strip()
        files = request.FILES.getlist('attachments')

        if not content and not files:
            return Response(
                {'error': 'Message content or attachment is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            msg = ChatMessage.objects.create(
                conversation=conv,
                sender=user,
                content=content,
                has_attachments=bool(files),
            )

            for f in files:
                ChatAttachment.objects.create(
                    message=msg,
                    file=f,
                    filename=f.name,
                    size=f.size,
                    content_type=getattr(f, 'content_type', ''),
                )

            # Create delivery rows for each participant except sender
            recipients = conv.participants.exclude(id=user.id)
            now = timezone.now()
            deliveries = [
                ChatMessageDelivery(
                    message=msg,
                    recipient=r,
                    sent_at=now,
                )
                for r in recipients
            ]
            ChatMessageDelivery.objects.bulk_create(deliveries)

        serializer = ChatMessageSerializer(msg, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark all messages in conversation as read for current user.
        """
        conv = self.get_object()
        user = request.user
        now = timezone.now()

        ChatMessageDelivery.objects.filter(
            message__conversation=conv,
            recipient=user,
            read_at__isnull=True,
        ).update(read_at=now, delivered_at=now)

        return Response({'status': 'ok'})

    @action(detail=True, methods=['post'])
    def typing(self, request, pk=None):
        """
        Simple typing indicator: we update last activity in cache.
        Frontend puede considerarlo como "escribiendo" si hay actividad
        reciente en el endpoint de typing.
        """
        cache.set(f"user:last_activity:{request.user.pk}", timezone.now(), timeout=3600)
        return Response({'status': 'ok'})

    @action(detail=False, methods=['get'])
    def presence(self, request):
        """
        Presence info for all users in the same tenant.
        """
        user = request.user
        tenant = ensure_user_tenant(user)
        if not tenant:
            return Response([], status=status.HTTP_200_OK)

        qs = User.objects.filter(tenant=tenant, is_active=True)
        serializer = UserPresenceSerializer(qs, many=True)
        return Response(serializer.data)
