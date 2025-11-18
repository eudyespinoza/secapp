# SecureApprove - Chat System Deployment Guide

## Quick Start

This guide helps you deploy the enhanced chat system for SecureApprove.

---

## Prerequisites

- PostgreSQL database running
- Redis server (for WebSocket support)
- Python virtual environment activated
- Django project configured

---

## Step 1: Install Dependencies

The required packages should already be in `requirements.txt`:

```bash
channels>=4.0.0
channels-redis>=4.1.0
daphne>=4.0.0
```

If not installed:

```bash
cd secureapprove_django
pip install channels channels-redis daphne
```

---

## Step 2: Configure Redis

### Option A: Docker (Recommended)

Add to `docker-compose.yml`:

```yaml
redis:
  image: redis:7-alpine
  restart: unless-stopped
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes
```

Start Redis:

```bash
docker-compose up -d redis
```

### Option B: Local Redis

Install Redis on your system and start it:

```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Windows
# Download from https://redis.io/download
# Or use WSL
```

### Verify Redis

```bash
redis-cli ping
# Should return: PONG
```

---

## Step 3: Update Environment Variables

Add to your `.env` file:

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/1

# Or if using Docker:
REDIS_URL=redis://redis:6379/1
```

---

## Step 4: Verify Django Configuration

Check that `config/settings.py` has:

```python
# Should already be configured
INSTALLED_APPS = [
    ...
    'channels',
    ...
    'apps.chat',
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

---

## Step 5: Run Database Migrations

```bash
cd secureapprove_django
python manage.py migrate chat
```

Expected output:
```
Running migrations:
  Applying chat.0001_initial... OK
```

---

## Step 6: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

This copies `tenant_chat.js` to the static directory.

---

## Step 7: Test the Configuration

### Test Redis Connection

```bash
python manage.py shell
```

```python
from channels.layers import get_channel_layer
channel_layer = get_channel_layer()
print(channel_layer)  # Should not be None

# Test sending a message
import asyncio
async def test():
    await channel_layer.send('test_channel', {'type': 'test.message', 'text': 'Hello'})
    
asyncio.run(test())
# Should complete without errors
```

### Test Chat Models

```bash
python manage.py shell
```

```python
from apps.chat.models import ChatConversation, UserPresence
from apps.authentication.models import User

# Check models are available
print(ChatConversation.objects.count())
print(UserPresence.objects.count())
```

---

## Step 8: Run the Application

### Development

```bash
# Using Django development server (includes Channels support)
python manage.py runserver 0.0.0.0:8000
```

### Production with Daphne

```bash
# Install Daphne if not already
pip install daphne

# Run ASGI server
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

---

## Step 9: Configure Nginx (Production Only)

Add WebSocket proxy configuration to your Nginx config:

```nginx
# HTTP/HTTPS traffic
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# WebSocket traffic
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400;
}
```

Reload Nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Step 10: Create Systemd Service (Production Only)

Create `/etc/systemd/system/secureapprove-chat.service`:

```ini
[Unit]
Description=SecureApprove ASGI Server (Daphne)
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/SecureApprove/secureapprove_django
Environment="PATH=/path/to/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings"
EnvironmentFile=/path/to/SecureApprove/.env
ExecStart=/path/to/venv/bin/daphne -b 127.0.0.1 -p 8000 config.asgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable secureapprove-chat
sudo systemctl start secureapprove-chat
sudo systemctl status secureapprove-chat
```

---

## Step 11: Test the Chat

1. **Open Browser:** Navigate to your SecureApprove instance
2. **Login:** Use two different user accounts in the same tenant
3. **Open Chat Widget:** Click the chat bar at bottom-right
4. **Start Conversation:** 
   - Go to "Users & Groups" tab
   - Click on a user to start conversation
5. **Send Messages:** Type and send messages between the two users
6. **Verify Real-Time:** Messages should appear instantly (WebSocket)
7. **Test Attachments:** Try uploading an image or PDF
8. **Check Notifications:** Grant permission and verify browser notifications work

---

## Troubleshooting

### Chat Widget Not Appearing

**Check:**
1. User is authenticated (logged in)
2. JavaScript file is loaded: Check Network tab for `tenant_chat.js`
3. No JavaScript errors: Check Browser Console

**Fix:**
```bash
python manage.py collectstatic --noinput
```

---

### WebSocket Connection Fails

**Check:**
1. Redis is running: `redis-cli ping`
2. Channels configuration: Review `settings.py`
3. Nginx WebSocket proxy: Check `/ws/` location block

**Debug:**
Open Browser Console → Network → WS tab
- Should see connection to `ws://your-domain/ws/chat/`
- Connection should show "101 Switching Protocols"

**If fails:**
- Check Redis: `docker-compose logs redis` or `systemctl status redis`
- Check Daphne logs: `journalctl -u secureapprove-chat -f`

---

### Messages Not Sending

**Check:**
1. CSRF token is present in the form
2. User has permission (is participant in conversation)
3. File size is under 10MB
4. File type is allowed

**Debug:**
- Browser Console → Network tab
- Look for POST request to `/api/chat/conversations/{id}/messages/`
- Check response status and error message

---

### Presence Always Offline

**Check:**
1. `UserPresence` table exists: `python manage.py migrate chat`
2. Presence endpoint is being called: `/api/chat/conversations/presence/`
3. Threshold is 120 seconds (users must have activity within 2 min)

**Fix:**
```python
# In Django shell
from apps.chat.models import UserPresence
UserPresence.compute_online_status()
```

---

### File Uploads Failing

**Check:**
1. `MEDIA_ROOT` and `MEDIA_URL` are configured in `settings.py`
2. Media directory exists and is writable
3. File size < 10MB
4. File type in allowed list (see `ChatAttachment.ALLOWED_CONTENT_TYPES`)

**Debug:**
```bash
# Check media directory permissions
ls -la media/chat_attachments/
chmod -R 755 media/
```

---

## Monitoring

### Check Active WebSocket Connections

```bash
# Redis CLI
redis-cli
> KEYS *
> CLIENT LIST
```

### Check Django Logs

```bash
# Development
# Logs appear in console

# Production (systemd)
journalctl -u secureapprove-chat -f --lines=100
```

### Monitor Redis

```bash
redis-cli INFO | grep connected_clients
redis-cli MONITOR  # Live stream of commands
```

---

## Performance Tuning

### For High Traffic (1000+ users)

1. **Redis Persistence:**
   ```yaml
   # docker-compose.yml
   redis:
     command: redis-server --appendonly yes --save 60 1000
   ```

2. **Increase Redis Memory:**
   ```yaml
   redis:
     command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
   ```

3. **Scale Daphne Workers:**
   ```bash
   # Run multiple Daphne instances behind load balancer
   daphne -b 127.0.0.1 -p 8001 config.asgi:application &
   daphne -b 127.0.0.1 -p 8002 config.asgi:application &
   ```

4. **Enable Redis Cluster** (for very large deployments)

5. **Add Database Connection Pooling:**
   ```python
   # settings.py
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'CONN_MAX_AGE': 600,  # 10 minutes
           'OPTIONS': {
               'connect_timeout': 10,
               'options': '-c statement_timeout=30000',  # 30 seconds
           },
       }
   }
   ```

---

## Security Checklist

- [x] Multi-tenant isolation enforced (tenant filtering on all queries)
- [x] WebSocket authentication via Django session
- [x] File upload validation (size and type)
- [x] CSRF protection on POST endpoints
- [ ] Rate limiting on message sending (optional, recommended)
- [ ] Regular Redis security updates
- [ ] Nginx WebSocket timeout configured (prevent resource exhaustion)

---

## Backup Recommendations

### Database

```bash
# Backup chat data
pg_dump -U postgres -d secureapprove -t chat_* > chat_backup.sql

# Restore
psql -U postgres -d secureapprove < chat_backup.sql
```

### Redis (if using persistence)

```bash
# Redis automatically saves to dump.rdb
cp /var/lib/redis/dump.rdb /backup/redis-$(date +%Y%m%d).rdb
```

### Media Files

```bash
# Backup chat attachments
tar -czf chat_attachments_$(date +%Y%m%d).tar.gz media/chat_attachments/
```

---

## Rollback Plan

If chat system has issues:

### Disable Chat Widget

Comment out in `templates/base.html`:

```html
{% comment %}
{% if user.is_authenticated %}
<script src="{% static 'chat/js/tenant_chat.js' %}"></script>
{% endif %}
{% endcomment %}
```

### Revert Migrations

```bash
python manage.py migrate chat zero
```

⚠️ **Warning:** This will delete all chat data!

---

## Next Steps

After successful deployment:

1. ✅ Test with real users
2. ✅ Monitor performance and errors
3. ✅ Gather user feedback
4. ✅ Plan additional features (see CHAT-DOCUMENTATION.md)

---

## Support

- **Documentation:** See `CHAT-DOCUMENTATION.md` for complete API reference
- **Logs:** Check Django and Daphne logs for errors
- **Redis:** Monitor Redis with `redis-cli INFO`

---

## Success Criteria

Chat system is working correctly when:

- ✅ Users can start conversations
- ✅ Messages send and receive in real-time
- ✅ WebSocket connection establishes successfully
- ✅ File attachments upload and download
- ✅ Online/offline status updates
- ✅ Browser notifications appear (with permission)
- ✅ No JavaScript console errors
- ✅ Multi-tenant isolation verified (users can't see other tenants' chats)

---

**Deployment completed!** 🎉

If you encounter issues, refer to the Troubleshooting section or consult `CHAT-DOCUMENTATION.md`.
