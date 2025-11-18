# SecureApprove - Internal Chat System Documentation

## Overview

SecureApprove includes a professional, real-time internal chat system for tenant organizations. The chat enables secure messaging between users within the same tenant, with support for:

- **Real-time messaging** via WebSocket with automatic fallback to polling
- **1-to-1 and group conversations** (group support ready for future expansion)
- **File attachments** with size and type validation
- **Typing indicators** and presence detection (online/offline)
- **Browser notifications** for new messages
- **Multi-language support** (ES/EN/PT-BR)
- **Multi-tenant isolation** - users can only chat with members of their organization
- **Responsive design** - works on desktop and mobile

---

## Architecture

### Technology Stack

- **Backend**: Django + Django REST Framework + Django Channels
- **Frontend**: Vanilla JavaScript (no frameworks required)
- **WebSocket**: Django Channels with Redis channel layer
- **Database**: PostgreSQL (via Django ORM)
- **Real-time**: WebSocket for instant delivery, HTTP polling as fallback

### Components

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (Browser)                 │
│  ┌────────────────────────────────────────────────┐ │
│  │  TenantChatWidget (tenant_chat.js)             │ │
│  │  - WebSocket connection                        │ │
│  │  - Polling fallback                            │ │
│  │  - UI rendering                                │ │
│  │  - Notifications                               │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
                        ↕ (HTTP/WS)
┌─────────────────────────────────────────────────────┐
│                   Backend (Django)                   │
│  ┌────────────────────────────────────────────────┐ │
│  │  REST API (views.py)                           │ │
│  │  - ChatConversationViewSet                     │ │
│  │  - Authentication & Multi-tenant filtering     │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │  WebSocket Consumer (consumers.py)             │ │
│  │  - ChatConsumer                                │ │
│  │  - Real-time event broadcasting                │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │  Models (models.py)                            │ │
│  │  - ChatConversation, ChatParticipant           │ │
│  │  - ChatMessage, ChatMessageDelivery            │ │
│  │  - ChatAttachment, UserPresence                │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│              Database (PostgreSQL)                   │
└─────────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────────┐
│         Channel Layer (Redis)                        │
│         - WebSocket group management                 │
│         - Message broadcasting                       │
└─────────────────────────────────────────────────────┘
```

---

## Data Models

### ChatConversation

Represents a conversation between users in the same tenant.

**Fields:**
- `id` (UUID): Primary key
- `tenant` (FK): Reference to Tenant
- `title` (str, optional): Display name for group conversations
- `is_group` (bool): True for groups, False for 1-to-1
- `last_message` (FK, optional): Cached reference to last message
- `created_at`, `updated_at` (datetime): Timestamps

**Indexes:**
- `(tenant, updated_at)`: For efficient conversation listing

### ChatParticipant

Through model linking users to conversations with metadata.

**Fields:**
- `id` (UUID): Primary key
- `conversation` (FK): Reference to ChatConversation
- `user` (FK): Reference to User
- `unread_count` (int): Cached unread message count
- `last_read_message` (FK, optional): Last message user has read
- `is_archived` (bool): User has archived this conversation
- `is_muted` (bool): User has muted notifications
- `joined_at` (datetime): When user joined conversation

**Constraints:**
- Unique together: `(conversation, user)`

### ChatMessage

Individual messages within a conversation.

**Fields:**
- `id` (UUID): Primary key
- `conversation` (FK): Reference to ChatConversation
- `sender` (FK): User who sent the message
- `content` (text, max 5000 chars): Message text
- `has_attachments` (bool): Whether message has files attached
- `status` (choice): Aggregated status (sent/delivered/read)
- `created_at`, `updated_at` (datetime): Timestamps

**Indexes:**
- `(conversation, created_at)`: For message retrieval
- `(sender, created_at)`: For user's message history

**Business Logic:**
- On save, updates conversation's `last_message` and `updated_at`

### ChatMessageDelivery

Per-recipient delivery tracking for messages.

**Fields:**
- `id` (UUID): Primary key
- `message` (FK): Reference to ChatMessage
- `recipient` (FK): User receiving the message
- `sent_at` (datetime): When message was created
- `delivered_at` (datetime, nullable): When recipient fetched via API
- `read_at` (datetime, nullable): When recipient marked as read

**Constraints:**
- Unique together: `(message, recipient)`

**Computed Property:**
- `status`: Returns 'read', 'delivered', or 'sent' based on timestamps

### ChatAttachment

File attachments for messages.

**Fields:**
- `id` (UUID): Primary key
- `message` (FK): Reference to ChatMessage
- `file` (FileField): Uploaded file (stored in `media/chat_attachments/YYYY/MM/`)
- `filename` (str): Original filename
- `content_type` (str): MIME type
- `size` (int): File size in bytes
- `uploaded_at` (datetime): Upload timestamp

**Validation:**
- Max file size: 10MB
- Allowed types: Images (JPEG, PNG, GIF, WebP), PDFs, Office docs, text files

### UserPresence

Tracks user online/offline status.

**Fields:**
- `user` (OneToOne): Primary key, reference to User
- `last_activity` (datetime): Last activity timestamp
- `is_online` (bool): Computed online status
- `updated_at` (datetime): Last update

**Class Methods:**
- `mark_user_online(user)`: Update user's presence
- `compute_online_status(threshold_seconds=120)`: Bulk update online status

---

## REST API Endpoints

### Base URL

All chat endpoints are under `/api/chat/`

### Authentication

All endpoints require authentication. Use Django session authentication (cookies).

### Endpoints

#### 1. List Conversations

**GET** `/api/chat/conversations/`

Returns all conversations for the current user.

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "John Doe",
    "is_group": false,
    "created_at": "2025-11-18T10:00:00Z",
    "updated_at": "2025-11-18T12:30:00Z",
    "last_message": {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "sender_id": 123,
      "sender_name": "John Doe",
      "sender_email": "john@example.com",
      "content": "Hello!",
      "created_at": "2025-11-18T12:30:00Z",
      "status": "read",
      "has_attachments": false,
      "attachments": []
    },
    "unread_count": 2,
    "participants": [
      {
        "id": 123,
        "name": "John Doe",
        "email": "john@example.com"
      },
      {
        "id": 456,
        "name": "Jane Smith",
        "email": "jane@example.com"
      }
    ]
  }
]
```

---

#### 2. Start/Get Conversation

**POST** `/api/chat/conversations/start/`

Start a 1-to-1 conversation with another user, or retrieve existing one.

**Request Body:**
```json
{
  "participant_id": 456
}
```

**Response:** Same structure as conversation object above

**Status Codes:**
- `200 OK`: Existing conversation returned
- `201 Created`: New conversation created
- `400 Bad Request`: Invalid participant_id
- `404 Not Found`: Participant not found in tenant

---

#### 3. List Messages

**GET** `/api/chat/conversations/{conversation_id}/messages/`

Get messages from a conversation.

**Query Parameters:**
- `since_id` (optional): Return only messages after this message ID

**Response:**
```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "conversation": "550e8400-e29b-41d4-a716-446655440000",
    "sender_id": 123,
    "sender_name": "John Doe",
    "sender_email": "john@example.com",
    "content": "Hello, how are you?",
    "has_attachments": false,
    "attachments": [],
    "created_at": "2025-11-18T12:30:00Z",
    "updated_at": "2025-11-18T12:30:00Z",
    "status": "read"
  }
]
```

**Notes:**
- Messages are ordered by `created_at` ascending
- Fetching messages automatically marks them as `delivered` for the current user

---

#### 4. Send Message

**POST** `/api/chat/conversations/{conversation_id}/messages/`

Send a new message with optional attachments.

**Content-Type:** `multipart/form-data`

**Form Fields:**
- `content` (string, optional): Message text (max 5000 chars)
- `attachments` (files, optional): One or more files

**Example (with fetch API):**
```javascript
const formData = new FormData();
formData.append('content', 'Hello!');
formData.append('attachments', fileInput.files[0]);

fetch('/api/chat/conversations/UUID/messages/', {
  method: 'POST',
  body: formData,
  credentials: 'same-origin',
  headers: {
    'X-CSRFToken': csrfToken
  }
});
```

**Response:** Message object (same structure as in list messages)

**Status Codes:**
- `201 Created`: Message sent successfully
- `400 Bad Request`: Validation error (empty message, file too large, etc.)
- `403 Forbidden`: Not a participant in conversation

**Validations:**
- At least one of `content` or `attachments` required
- Content max length: 5000 characters
- File max size: 10MB per file
- File types: See ChatAttachment model documentation

---

#### 5. Mark as Read

**POST** `/api/chat/conversations/{conversation_id}/mark_read/`

Mark all messages in a conversation as read for the current user.

**Request Body:** Empty `{}`

**Response:**
```json
{
  "status": "ok",
  "marked_read": 5
}
```

**Effects:**
- Updates all `ChatMessageDelivery` records to set `read_at`
- Resets `unread_count` to 0 for the participant

---

#### 6. Typing Indicator

**POST** `/api/chat/conversations/{conversation_id}/typing/`

Notify other participants that the user is typing.

**Request Body:** Empty `{}`

**Response:**
```json
{
  "status": "ok"
}
```

**Effects:**
- Broadcasts a `typing` event via WebSocket to other participants
- Updates user presence timestamp

---

#### 7. Presence Information

**GET** `/api/chat/conversations/presence/`

Get online/offline status for all users in the tenant.

**Response:**
```json
[
  {
    "id": 123,
    "name": "John Doe",
    "email": "john@example.com",
    "is_online": true,
    "last_seen": "2025-11-18T12:35:00Z"
  },
  {
    "id": 456,
    "name": "Jane Smith",
    "email": "jane@example.com",
    "is_online": false,
    "last_seen": "2025-11-18T10:00:00Z"
  }
]
```

**Notes:**
- Users are considered online if `last_activity` is within 2 minutes
- Presence is updated on every API call and WebSocket activity

---

#### 8. Archive/Unarchive Conversation

**PATCH** `/api/chat/conversations/{conversation_id}/archive/`
**PATCH** `/api/chat/conversations/{conversation_id}/unarchive/`

Archive or unarchive a conversation for the current user.

**Response:**
```json
{
  "status": "archived"
}
```

---

#### 9. Mute/Unmute Conversation

**PATCH** `/api/chat/conversations/{conversation_id}/mute/`
**PATCH** `/api/chat/conversations/{conversation_id}/unmute/`

Mute or unmute notifications for a conversation.

**Response:**
```json
{
  "status": "muted"
}
```

---

## WebSocket API

### Connection

**URL:** `ws(s)://<host>/ws/chat/`

**Authentication:** Uses Django session cookies (same as HTTP requests)

### Connection Flow

1. Client connects to WebSocket
2. Server authenticates via Django session
3. If authenticated:
   - Server joins client to `user_{user_id}` group
   - Server sends `{"type": "connected", "user_id": 123, "message": "Connected to chat"}`
4. If not authenticated:
   - Server closes connection with code 4401

### Incoming Messages (Client → Server)

#### Ping/Pong

**Client sends:**
```json
{
  "type": "ping"
}
```

**Server responds:**
```json
{
  "type": "pong"
}
```

Used for connection health checks. Client should ping every 30 seconds.

### Outgoing Events (Server → Client)

#### Message Created

Sent when a new message is posted in a conversation where the user is a participant.

```json
{
  "type": "message_created",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "sender_id": 123,
    "sender_name": "John Doe",
    "content": "Hello!",
    "created_at": "2025-11-18T12:30:00Z",
    "status": "sent",
    "has_attachments": false,
    "attachments": []
  }
}
```

**Client should:**
- If conversation is currently open: render the message
- Update conversation list with new message preview
- Increment unread counter (unless conversation is open)
- Show browser notification (if permission granted and conversation not open)

---

#### Typing

Sent when another user is typing in a conversation.

```json
{
  "type": "typing",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 123,
  "user_name": "John Doe"
}
```

**Client should:**
- If conversation is currently open: show "John Doe is typing..." indicator
- Hide indicator after 1-2 seconds

---

#### Presence

Sent when a user's online status changes (future feature).

```json
{
  "type": "presence",
  "user_id": 123,
  "is_online": true
}
```

---

### Reconnection Strategy

The WebSocket manager implements exponential backoff:

- **Base delay:** 1 second
- **Max delay:** 30 seconds
- **Formula:** `min(base * 2^attempts + random_jitter, max)`

Client automatically attempts to reconnect when connection is lost.

---

## Frontend Integration

### Loading the Chat Widget

The chat widget is automatically loaded for authenticated users in `base.html`:

```html
{% if user.is_authenticated %}
<!-- Chat Widget Configuration -->
<script>
  window.CHAT_CURRENT_USER_ID = {{ user.id }};
  window.CHAT_I18N = {
    newMessage: '{% trans "New chat message" %}',
    // ... other translations
  };
</script>

<!-- Tenant Chat Widget -->
<script src="{% static 'chat/js/tenant_chat.js' %}"></script>
{% endif %}
```

### Widget Structure

The widget consists of:

1. **Chat Bar** (`#tenantChatBar`): Fixed bottom-right bar showing status and unread count
2. **Chat Panel** (`#tenantChatPanel`): Expandable panel with 3 tabs:
   - **Internal chat**: Active conversation with messages
   - **Chats**: List of all conversations
   - **Users & Groups**: List of users with online status

### DOM Elements

Required elements (already in `base.html`):

```html
<div id="tenantChatBar" class="tenant-chat-bar">...</div>
<div id="tenantChatPanel" class="tenant-chat-panel">
  <div id="widgetMessageContainer">...</div>
  <form id="widgetMessageForm">
    <textarea id="widgetMessageInput"></textarea>
    <input type="file" id="widgetAttachmentInput" multiple>
  </form>
  <ul id="widgetConversationList"></ul>
  <ul id="widgetUserList"></ul>
  <span id="widgetNewMessagesBadge"></span>
  ...
</div>
```

### Browser Notifications

The widget requests notification permission automatically after 3 seconds.

**Notification Behavior:**
- Only shown if user has granted permission
- Only for conversations that are NOT currently open
- Shows sender name and message preview
- Auto-closes after 5 seconds
- Clicking notification brings window to focus

---

## Deployment Configuration

### 1. Redis Setup

Django Channels requires Redis for the channel layer.

**Docker Compose (recommended):**

```yaml
redis:
  image: redis:7-alpine
  restart: unless-stopped
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

**Environment Variable:**

```bash
REDIS_URL=redis://redis:6379/1
```

### 2. Django Settings

In `config/settings.py`:

```python
# Channels
INSTALLED_APPS = [
    ...
    'channels',
    ...
]

ASGI_APPLICATION = 'config.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}
```

### 3. ASGI Configuration

Ensure `config/asgi.py` is set up correctly:

```python
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

import apps.chat.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(apps.chat.routing.websocket_urlpatterns)
    ),
})
```

### 4. Running with ASGI

**Development:**
```bash
python manage.py runserver
# OR with Daphne:
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

**Production (with Daphne behind Nginx):**

```nginx
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Systemd service:**

```ini
[Unit]
Description=SecureApprove ASGI (Daphne)
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/secureapprove
Environment="DJANGO_SETTINGS_MODULE=config.settings"
ExecStart=/path/to/venv/bin/daphne -b 127.0.0.1 -p 8000 config.asgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

### 5. Database Migrations

Run migrations to create chat tables:

```bash
python manage.py makemigrations chat
python manage.py migrate chat
```

### 6. Static Files

Collect static files to serve `tenant_chat.js`:

```bash
python manage.py collectstatic --noinput
```

---

## Troubleshooting

### WebSocket Connection Fails

**Symptoms:** Chat works but messages don't appear in real-time

**Causes:**
1. Redis not running
2. Channels not configured
3. Nginx not proxying WebSocket correctly

**Debug:**
```bash
# Check Redis
redis-cli ping  # Should return PONG

# Check Django Channels
python manage.py shell
>>> from channels.layers import get_channel_layer
>>> channel_layer = get_channel_layer()
>>> channel_layer  # Should not be None
```

### Messages Not Appearing

**Check:**
1. Browser console for JavaScript errors
2. Django logs for API errors
3. Network tab to see if requests are succeeding
4. User is authenticated and in correct tenant

### File Upload Fails

**Check:**
1. File size is under 10MB
2. File type is in allowed list
3. `MEDIA_ROOT` and `MEDIA_URL` are configured
4. Media directory is writable

### Presence Always Shows Offline

**Check:**
1. `UserPresence.compute_online_status()` is being called
2. Presence API is being polled
3. Threshold (120 seconds) is appropriate for your use case

---

## Performance Optimization

### Database

1. **Indexes:** Already added to models for optimal querying
2. **Prefetch:** Viewsets use `select_related` and `prefetch_related`
3. **Caching:** Consider caching conversation lists for very active tenants

### WebSocket

1. **Connection Pooling:** Redis connection pooling is automatic
2. **Scaling:** For large deployments, use Redis Cluster
3. **Load Balancing:** Sticky sessions required for WebSocket

### Polling Fallback

If WebSocket is unavailable:
- Conversations polled every 5 seconds
- Messages polled every 5 seconds (only if conversation open)
- Presence polled every 10 seconds

Consider increasing intervals for very large tenants.

---

## Security Considerations

### Multi-Tenant Isolation

✅ **Enforced at:**
- Database queries (all filtered by tenant)
- API endpoints (ensure_user_tenant)
- WebSocket groups (per-user, not per-tenant-wide)

### File Upload Security

✅ **Protections:**
- File size limit (10MB)
- Content-type whitelist
- Files stored outside web root
- Filenames sanitized by Django

### WebSocket Security

✅ **Protections:**
- Authentication via Django session
- Per-user groups (no cross-tenant leakage)
- CSRF protection for HTTP endpoints

### Rate Limiting

⚠️ **Recommended:** Add rate limiting to:
- Message sending endpoint
- Conversation creation endpoint
- Typing indicator endpoint

Example with Django REST Framework:

```python
from rest_framework.throttling import UserRateThrottle

class MessageRateThrottle(UserRateThrottle):
    rate = '60/min'  # 60 messages per minute

class ChatConversationViewSet(viewsets.ModelViewSet):
    throttle_classes = [MessageRateThrottle]
```

---

## Future Enhancements

### Planned Features

1. **Group Conversations:** Full support for multi-user groups
   - Group creation UI
   - Add/remove participants
   - Group settings (name, avatar)

2. **Rich Attachments:**
   - Image previews inline
   - Video/audio playback
   - Link previews

3. **Search:**
   - Full-text search across messages
   - Filter by conversation, sender, date

4. **Message Reactions:**
   - Emoji reactions to messages
   - Aggregate counts

5. **Voice/Video Calls:**
   - Integration with WebRTC for calls

6. **Message Editing/Deletion:**
   - Edit sent messages
   - Delete with tombstone

7. **Read Receipts:**
   - Show who has read each message in groups

### Contributing

To contribute to chat improvements:

1. Review this documentation
2. Check existing models and API
3. Maintain multi-tenant security
4. Write tests for new features
5. Update this documentation

---

## Testing

### Manual Testing

1. **Basic Flow:**
   - Log in as two users in same tenant
   - Start conversation
   - Send messages back and forth
   - Verify real-time delivery
   - Check unread counts
   - Test file uploads

2. **WebSocket:**
   - Open browser dev tools
   - Check Network → WS tab
   - Verify connection establishes
   - Send message from other user
   - Verify event received

3. **Fallback:**
   - Block WebSocket port
   - Verify polling fallback works
   - Messages still appear (with delay)

### Automated Tests

```python
# Example test
from django.test import TestCase
from apps.chat.models import ChatConversation, ChatMessage

class ChatTestCase(TestCase):
    def test_send_message(self):
        # Create conversation
        conv = ChatConversation.objects.create(tenant=self.tenant)
        conv.participants.add(self.user1, self.user2)
        
        # Send message via API
        response = self.client.post(
            f'/api/chat/conversations/{conv.id}/messages/',
            {'content': 'Hello'},
        )
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ChatMessage.objects.count(), 1)
```

---

## Support

For issues or questions:

1. Check this documentation
2. Review API endpoint responses for error messages
3. Check browser console and Django logs
4. Verify Redis and Channels configuration
5. Contact development team

---

## Changelog

### Version 2.0 (November 2025)

- ✨ Complete rewrite of chat system
- ✨ Improved data models with proper relationships
- ✨ Professional WebSocket implementation
- ✨ Refactored frontend to external JS file
- ✨ Browser notifications support
- ✨ File attachment validation
- ✨ Typing indicators
- ✨ Presence detection
- ✨ Multi-language support
- ✨ Comprehensive documentation

### Version 1.0 (Initial)

- Basic chat functionality
- Polling-only (no WebSocket)
- Embedded JavaScript in template

---

**Last Updated:** November 18, 2025
**Maintained By:** SecureApprove Development Team
