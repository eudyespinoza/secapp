import logging
from typing import Any, Dict

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time chat features.

    Features:
    - Joins user-specific groups for targeted event delivery
    - Handles incoming ping/pong for connection health checks
    - Broadcasts message_created events when new messages arrive
    - Broadcasts typing events when users are typing
    - Supports presence updates (optional future extension)
    
    Events sent to client:
    - type: "message_created" - New message in a conversation
      {
          "type": "message_created",
          "conversation_id": "uuid",
          "message": {message_data}
      }
    
    - type: "typing" - User is typing in a conversation
      {
          "type": "typing",
          "conversation_id": "uuid",
          "user_id": 123,
          "user_name": "John Doe"
      }
    
    - type: "presence" - User online/offline status change
      {
          "type": "presence",
          "user_id": 123,
          "is_online": true
      }
    """

    async def connect(self) -> None:
        """
        Handle WebSocket connection.
        
        - Authenticates user
        - Joins user-specific group for targeted broadcasts
        - Accepts connection if authenticated
        """
        user = self.scope.get("user")
        
        # Reject unauthenticated connections
        if not user or not user.is_authenticated:
            logger.warning("Rejected unauthenticated chat connection")
            await self.close(code=4401)
            return

        tenant_id = getattr(user, "tenant_id", None)
        if not tenant_id:
            logger.warning("Rejected chat connection for user %s without tenant", user.id)
            await self.close(code=4403)
            return

        # Store user info
        self.user = user
        self.tenant_group_name = f"tenant_{tenant_id}_chat"
        
        # Join tenant group (all chat events are broadcast per tenant)
        await self.channel_layer.group_add(
            self.tenant_group_name,
            self.channel_name
        )
        
        # Update user presence
        await self.update_user_presence()
        
        # Accept connection
        await self.accept()

        logger.info(
            "[CHAT] WebSocket connected for user %s (tenant %s)",
            user.id,
            tenant_id,
        )
        
        # Send connection confirmation
        await self.send_json({
            "type": "connected",
            "user_id": user.id,
            "message": "Connected to chat"
        })

    async def disconnect(self, code: int) -> None:
        """
        Handle WebSocket disconnection.
        
        - Removes user from their group
        - Optionally updates presence to offline (with delay)
        """
        if not hasattr(self, 'user') or not hasattr(self, 'tenant_group_name'):
            return
        
        # Leave tenant group
        await self.channel_layer.group_discard(
            self.tenant_group_name,
            self.channel_name
        )

        logger.info(
            "[CHAT] WebSocket disconnected for user %s (code=%s)",
            getattr(getattr(self, "user", None), "id", None),
            code,
        )

    async def receive_json(self, content: Dict[str, Any], **kwargs: Any) -> None:
        """
        Handle incoming WebSocket messages from client.
        
        Supported message types:
        - ping: Health check (responds with pong)
        - typing: User is typing (future: could broadcast to conversation)
        """
        msg_type = content.get("type")
        
        # Health check ping/pong
        if msg_type == "ping":
            await self.send_json({"type": "pong"})
            return
        
        # Update presence on any activity
        await self.update_user_presence()
        
        # Future: Handle other client-initiated events
        # e.g., typing notifications, read receipts, etc.

    async def chat_message_created(self, event: Dict[str, Any]) -> None:
        """
        Handler for "chat_message_created" events sent to the tenant group.

        Ensures we only forward the payload once per user and skips echoing
        the sender's own messages to avoid duplicates in the UI.
        """
        message = event.get("message", {})
        sender_id = message.get("sender_id")

        if sender_id and hasattr(self, "user") and sender_id == self.user.id:
            # Skip echoing the sender's own message; frontend already renders it
            return

        await self.send_json({
            "type": "message_created",
            "conversation_id": event.get("conversation_id"),
            "message": message,
        })

    async def chat_typing(self, event: Dict[str, Any]) -> None:
        """
        Handler for "chat.typing" events sent to user group.
        
        Forwards typing indicators to the WebSocket client.
        
        Expected event structure:
        {
            "type": "chat.typing",
            "event": "typing",
            "conversation_id": "uuid",
            "user_id": 123,
            "user_name": "John Doe"
        }
        """
        await self.send_json({
            "type": "typing",
            "conversation_id": event.get("conversation_id"),
            "user_id": event.get("user_id"),
            "user_name": event.get("user_name"),
        })

    async def chat_presence(self, event: Dict[str, Any]) -> None:
        """
        Handler for "chat.presence" events sent to user group.
        
        Forwards presence updates to the WebSocket client.
        
        Expected event structure:
        {
            "type": "chat.presence",
            "event": "presence",
            "user_id": 123,
            "is_online": true
        }
        """
        await self.send_json({
            "type": "presence",
            "user_id": event.get("user_id"),
            "is_online": event.get("is_online"),
        })

    @database_sync_to_async
    def update_user_presence(self):
        """Update user's last activity timestamp."""
        if not hasattr(self, 'user'):
            return
        
        try:
            from django.core.cache import cache
            from .models import UserPresence
            
            # Update cache-based presence
            cache.set(
                f"user:last_activity:{self.user.pk}",
                timezone.now(),
                timeout=3600
            )
            
            # Update database presence
            UserPresence.mark_user_online(self.user)
        except Exception as e:
            # Don't fail the connection on presence update errors
            print(f"Error updating presence: {e}")
