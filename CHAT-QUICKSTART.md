# Quick Start: Applying Chat System Upgrade

## 🚀 Automated Deployment (Recommended)

**The easiest way** - Use the automated deployment script:

### Windows (PowerShell):
```powershell
.\deploy.ps1
```

### Linux/Mac:
```bash
chmod +x deploy.sh
./deploy.sh
```

**This will automatically:**
- ✅ Check and migrate chat schema (handles old → new migration)
- ✅ Run all database migrations
- ✅ Collect static files
- ✅ Restart services
- ✅ Run health checks

**Options:**
```bash
# Check migration status only (no changes)
./deploy.sh --check-only

# Force chat schema reset (deletes all chat data!)
./deploy.sh --force-chat-reset

# Skip database migrations
./deploy.sh --skip-migrations

# Use custom compose file
./deploy.sh --compose-file docker-compose.local.yml
```

**Done!** 🎉 The script handles everything automatically.

---

## ⚡ Manual Deployment (If needed)

If you prefer manual control or the automated script fails:

### 1. Apply Chat Schema Migration

```bash
cd d:\OtherProyects\SecApp\secureapprove_django
python manage.py migrate_chat_schema
```

**This command:**
- ✅ Detects old chat tables and migrates them
- ✅ Safely handles schema changes
- ✅ Creates new tables if needed

### 2. Apply Other Migrations

```bash
python manage.py migrate --noinput
```

### 3. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 4. Restart Your Server

If using Docker:
```bash
cd d:\OtherProyects\SecApp
docker-compose restart web
```

If running locally:
- Stop your development server (Ctrl+C)
- Start again: `python manage.py runserver`

### 5. Test the Chat

1. Open browser: http://localhost:8000
2. Login as a user
3. Look for chat widget in bottom-right corner
4. Click to expand
5. Start a conversation!

**Done!** 🎉

---

## 🔍 Verification Checklist

After applying changes, verify:

- [ ] No migration errors
- [ ] Static files collected successfully
- [ ] Chat widget appears at bottom-right
- [ ] Can start conversation with another user
- [ ] Messages send and receive
- [ ] No JavaScript console errors

---

## ⚠️ If You See Errors

### Error: "No module named 'channels'"

**Solution:**
```bash
pip install channels channels-redis daphne
```

### Error: Redis connection failed

**Solution:**

1. Start Redis:
```bash
docker-compose up -d redis
```

2. Or install locally and start:
```bash
# Windows (with WSL or download from redis.io)
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis
```

3. Verify:
```bash
redis-cli ping
# Should return: PONG
```

### Error: "tenant_chat.js not found" (404)

**Solution:**
```bash
python manage.py collectstatic --noinput --clear
```

### Error: WebSocket connection failed

**Check:**
1. Is Redis running? `redis-cli ping`
2. Is `CHANNEL_LAYERS` configured in settings.py? ✅ (Should already be there)
3. Is `ASGI_APPLICATION` set? ✅ (Should already be there)

**For now:** Chat will work with HTTP polling fallback. WebSocket is optional but recommended.

---

## 📋 What Changed?

### Files Modified:
1. ✅ `apps/chat/models.py` - Enhanced data models
2. ✅ `apps/chat/views.py` - Complete API rewrite
3. ✅ `apps/chat/serializers.py` - New serializers
4. ✅ `apps/chat/consumers.py` - Enhanced WebSocket consumer
5. ✅ `apps/chat/admin.py` - New Django admin interface
6. ✅ `templates/base.html` - Removed inline JS, added external script
7. ✅ `staticfiles/chat/js/tenant_chat.js` - NEW professional frontend

### Files Added:
1. ✅ `CHAT-DOCUMENTATION.md` - Complete technical documentation
2. ✅ `CHAT-DEPLOYMENT.md` - Deployment guide
3. ✅ `CHAT-UPGRADE-SUMMARY.md` - Feature overview
4. ✅ `CHAT-QUICKSTART.md` - This file

### Database:
1. ✅ New migration: `apps/chat/migrations/0001_initial.py`
2. ✅ 6 new/updated tables (see CHAT-UPGRADE-SUMMARY.md)

---

## 🚨 Important Notes

### Multi-Tenant Security
All chat queries are automatically filtered by tenant. Users can only:
- See conversations from their tenant
- Send messages to users in their tenant
- View presence of users in their tenant

✅ **No action needed** - this is handled automatically by the code.

### File Uploads
- Max size: 10MB per file
- Allowed types: Images, PDFs, Office docs, text files
- Files stored in `media/chat_attachments/YYYY/MM/`

**Make sure `media/` directory is writable:**
```bash
chmod -R 755 media/
```

### WebSocket (Optional but Recommended)
- If Redis is running: Real-time WebSocket messaging ✅
- If Redis is not available: HTTP polling fallback ✅
- Either way, **chat will work**

---

## 📖 Next Steps

After basic setup:

1. **Read Documentation:**
   - `CHAT-DOCUMENTATION.md` - Full API and architecture reference
   - `CHAT-DEPLOYMENT.md` - Production deployment guide

2. **Test Thoroughly:**
   - Test with multiple users
   - Try file attachments
   - Check browser notifications
   - Verify mobile responsiveness

3. **Production Deployment:**
   - Follow `CHAT-DEPLOYMENT.md` for Nginx, Daphne, Systemd setup
   - Enable SSL/TLS for secure WebSocket (wss://)
   - Set up monitoring and logging

4. **Explore Admin Interface:**
   - Visit `/admin/chat/` to see all chat data
   - Manage conversations, messages, attachments
   - Track user presence

---

## 🆘 Need Help?

1. **Check Logs:**
   ```bash
   # Development
   # Logs appear in console

   # Docker
   docker-compose logs -f web

   # Production (systemd)
   journalctl -u secureapprove-chat -f --lines=100
   ```

2. **Check Browser Console:**
   - Open DevTools (F12)
   - Look for errors in Console tab
   - Check Network tab for failed requests
   - Check WS tab for WebSocket connection

3. **Review Documentation:**
   - See "Troubleshooting" sections in CHAT-DEPLOYMENT.md
   - Check CHAT-DOCUMENTATION.md for API details

4. **Common Issues:**
   - Redis not running → Start with `docker-compose up -d redis`
   - Migrations not applied → Run `python manage.py migrate chat`
   - Static files not found → Run `python manage.py collectstatic`
   - WebSocket fails → Check Redis and Nginx configuration

---

## ✅ Success Criteria

Chat is working when you can:

1. ✅ See chat widget at bottom-right (authenticated users only)
2. ✅ Expand chat panel by clicking the bar
3. ✅ See list of users in "Users & Groups" tab
4. ✅ Click a user to start conversation
5. ✅ Send and receive messages in real-time
6. ✅ Upload and download file attachments
7. ✅ See "X users online" status in chat bar
8. ✅ Get browser notifications for new messages (after granting permission)

---

## 🎯 Summary

### Minimum Steps:
```bash
# 1. Apply migrations
python manage.py migrate chat

# 2. Collect static files
python manage.py collectstatic --noinput

# 3. Restart server
# (Docker: docker-compose restart web)
# (Local: restart runserver)

# Done! 🎉
```

### With Redis (Recommended):
```bash
# 1. Start Redis
docker-compose up -d redis

# 2. Verify Redis
redis-cli ping  # Should return PONG

# 3. Apply migrations
python manage.py migrate chat

# 4. Collect static files
python manage.py collectstatic --noinput

# 5. Restart server
daphne config.asgi:application

# Done with WebSocket support! 🚀
```

---

**Ready to deploy!** For production setup, see `CHAT-DEPLOYMENT.md`.

**Questions?** Check the comprehensive documentation in `CHAT-DOCUMENTATION.md`.

---

**Version:** 2.0  
**Last Updated:** November 18, 2025  
**Status:** ✅ Ready for Deployment
