import json
from typing import Any, Dict

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    Lightweight WebSocket consumer for the internal chat.

    - Uses per-user groups (\"user_<id>\") so views can push events to
      connected clients via Channels.
    - Currently supports one-way events from server to client:
        * type=\"message_created\" with payload \"message\" and
          \"conversation_id\".
    - Client-to-server messages are optional and ignored for now
      (reserved for future extensions like presence/typing over WS).
    """

    async def connect(self) -> None:
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.user_group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        user = self.scope.get("user")
        if not user or not getattr(self, "user_group_name", None):
            return
        await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def receive_json(self, content: Dict[str, Any], **kwargs: Any) -> None:
        """
        Placeholder for future commands.
        For now we just support an optional \"ping\" -> \"pong\".
        """
        msg_type = content.get("type")
        if msg_type == "ping":
            await self.send_json({"type": "pong"})

    async def chat_message(self, event: Dict[str, Any]) -> None:
        """
        Handler for \"chat.message\" events sent to the user group from views.

        The event is expected to have:
          - event: logical event type (e.g. \"message_created\")
          - conversation_id
          - message: serialized ChatMessage
        """
        await self.send_json(
            {
                "type": event.get("event", "message_created"),
                "conversation_id": event.get("conversation_id"),
                "message": event.get("message"),
            }
        )

