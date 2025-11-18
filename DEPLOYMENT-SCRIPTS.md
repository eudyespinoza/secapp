# 🚀 SecureApprove Deployment Scripts

This directory contains automated deployment scripts for SecureApprove, including the chat system upgrade.

## 📁 Available Scripts

### 1. **deploy.sh** (Linux/Mac)
Automated deployment script for Unix-based systems.

### 2. **deploy.ps1** (Windows)
Automated deployment script for Windows PowerShell.

### 3. **migrate_chat_schema** (Django Command)
Django management command for safe chat schema migration.

Location: `secureapprove_django/apps/chat/management/commands/migrate_chat_schema.py`

---

## 🎯 Quick Start

### Development/Local Deployment

**Windows:**
```powershell
.\deploy.ps1 --compose-file docker-compose.local.yml
```

**Linux/Mac:**
```bash
./deploy.sh --compose-file docker-compose.local.yml
```

### Production Deployment

**Windows:**
```powershell
.\deploy.ps1
```

**Linux/Mac:**
```bash
./deploy.sh
```

---

## 📖 Deployment Script Options

### Standard Deployment
Runs complete deployment with all checks:
```bash
./deploy.sh
```

**What it does:**
1. ✅ Pre-deployment checks
2. ✅ Pull latest images
3. ✅ Build services
4. ✅ Run database migrations
5. ✅ Migrate chat schema (if needed)
6. ✅ Collect static files
7. ✅ Compile translations
8. ✅ Restart services
9. ✅ Health checks

### Check-Only Mode
Check if migration is needed without making changes:
```bash
./deploy.sh --check-only
```

**Use case:** CI/CD pipelines, pre-deployment validation

### Force Chat Reset
**⚠️ WARNING: This deletes all chat data!**
```bash
./deploy.sh --force-chat-reset
```

**Use case:** 
- Development environment cleanup
- Complete schema reset
- Troubleshooting migration issues

**Not recommended for production with existing data!**

### Skip Migrations
Skip database migration step:
```bash
./deploy.sh --skip-migrations
```

**Use case:**
- Static file-only updates
- Configuration changes
- When migrations already applied manually

### Custom Compose File
Use a different docker-compose file:
```bash
./deploy.sh --compose-file docker-compose.prod.yml
```

**Use case:**
- Multiple environments (dev, staging, prod)
- Custom configurations

---

## 🔧 Chat Schema Migration Command

The `migrate_chat_schema` Django management command handles safe migration from old to new chat schema.

### Usage

**Check if migration is needed:**
```bash
python manage.py migrate_chat_schema --check-only
```

**Run migration:**
```bash
python manage.py migrate_chat_schema
```

**Force recreation (deletes all chat data):**
```bash
python manage.py migrate_chat_schema --force
```

### What It Does

1. **Detects existing schema:**
   - Checks for old chat tables (chatmessagemention, chatmessagereaction, etc.)
   - Checks for new chat tables (userpresence, chatparticipant, etc.)
   - Determines if migration is needed

2. **Safely migrates:**
   - Drops old tables in correct order (respects foreign keys)
   - Unmarks old migrations
   - Creates new schema with all tables and indexes

3. **Handles edge cases:**
   - Mixed schemas (old + new tables)
   - Fresh installations (no tables)
   - Already migrated (up-to-date schema)

### Exit Codes

- `0` - Success or no migration needed
- `1` - Error or migration needed (in --check-only mode)

---

## 🔄 Automatic Migration in Docker

The chat schema migration is **automatically checked** during container startup via `docker-entrypoint.sh`:

```bash
# In docker-entrypoint.sh
python manage.py migrate_chat_schema --check-only
if [ $? -ne 0 ]; then
  python manage.py migrate_chat_schema
fi
```

**This means:**
- ✅ First deployment: Automatic schema creation
- ✅ Upgrade deployment: Automatic migration from old to new
- ✅ Regular restarts: No-op if schema is current

**No manual intervention needed!**

---

## 🏗️ Architecture

### Old Chat Schema (Before Upgrade)
```
chat_chatconversation
chat_chatconversation_participants (many-to-many)
chat_chatmessage
chat_chatmessagemention
chat_chatmessagereaction
chat_chattypingindicator
```

### New Chat Schema (After Upgrade)
```
chat_chatconversation       (enhanced)
chat_chatparticipant        (new: replaces M2M)
chat_chatmessage           (enhanced)
chat_chatmessagedelivery   (new: per-recipient tracking)
chat_chatattachment        (new: file uploads)
chat_userpresence          (new: online/offline status)
```

### Migration Process

```
┌─────────────────────────────────────────────────────────┐
│ 1. Detect Schema State                                  │
│    - Check for old tables                               │
│    - Check for new tables                               │
│    - Determine action needed                            │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │ Schema State?                        │
        └──────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
    ┌─────────┐      ┌─────────┐     ┌──────────┐
    │ No      │      │ Old     │     │ New      │
    │ Tables  │      │ Schema  │     │ Schema   │
    └─────────┘      └─────────┘     └──────────┘
          │                │                │
          ▼                ▼                ▼
    ┌─────────┐      ┌─────────┐     ┌──────────┐
    │ Create  │      │ Migrate │     │ No-Op    │
    │ Fresh   │      │ Schema  │     │          │
    └─────────┘      └─────────┘     └──────────┘
```

---

## 🎭 Deployment Scenarios

### Scenario 1: Fresh Installation
**State:** No database, no tables  
**Action:** Create all tables from scratch  
**Data Loss:** None (no existing data)

**Steps:**
```bash
./deploy.sh
```

**Output:**
```
✓ No chat tables found. Fresh installation detected.
Applying chat migrations...
✓ Chat tables created successfully!
```

---

### Scenario 2: Upgrade from Old Chat
**State:** Old chat tables exist  
**Action:** Migrate to new schema  
**Data Loss:** ⚠️ Chat history will be lost

**Steps:**
```bash
./deploy.sh
```

**Output:**
```
⚠ Old chat schema detected. Migration required.
Step 1: Dropping old chat tables...
Step 2: Unmarking migrations...
Step 3: Creating new schema...
✓ Chat migration completed successfully!
```

**Note:** To preserve chat history, use a custom data migration (not included by default).

---

### Scenario 3: Already Migrated
**State:** New schema already in place  
**Action:** No-op  
**Data Loss:** None

**Steps:**
```bash
./deploy.sh
```

**Output:**
```
✓ New chat schema already in place. No migration needed.
```

---

### Scenario 4: Mixed Schema (Troubleshooting)
**State:** Both old and new tables exist (incomplete migration)  
**Action:** Cleanup and recreate  
**Data Loss:** ⚠️ All chat data

**Steps:**
```bash
./deploy.sh --force-chat-reset
```

**Output:**
```
⚠ Mixed schema detected (old + new tables). Cleanup required.
⚠ FORCE mode enabled. All chat data will be deleted.
Type "yes" to confirm: yes
```

---

## 🧪 Testing Deployment

### Test in Development First

1. **Check current state:**
   ```bash
   ./deploy.sh --check-only
   ```

2. **Run deployment:**
   ```bash
   ./deploy.sh --compose-file docker-compose.local.yml
   ```

3. **Verify:**
   - Check logs: `docker compose logs -f web`
   - Test chat: http://localhost:8000
   - Check database: `docker compose exec db psql -U postgres -d secureapprove -c "\dt chat_*"`

---

## 🚨 Troubleshooting

### Issue: "Migration needed but tables already exist"
**Cause:** Inconsistent state between Django migrations and actual database

**Solution:**
```bash
# Option 1: Force reset (development only)
./deploy.sh --force-chat-reset

# Option 2: Manual cleanup
docker compose exec web python manage.py migrate_chat_schema --force
```

---

### Issue: "relation already exists" during migration
**Cause:** Partial migration failed, some tables exist

**Solution:**
```bash
# Drop all chat tables manually
docker compose exec db psql -U postgres -d secureapprove -c "
  DROP TABLE IF EXISTS 
    chat_chatmessagemention,
    chat_chatmessagereaction,
    chat_chattypingindicator,
    chat_chatmessagedelivery,
    chat_chatattachment,
    chat_chatmessage,
    chat_chatparticipant,
    chat_chatconversation_participants,
    chat_chatconversation,
    chat_userpresence
  CASCADE;
"

# Then re-run migration
python manage.py migrate_chat_schema
```

---

### Issue: Deployment script fails with permission error
**Cause:** Script is not executable

**Solution (Linux/Mac):**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Solution (Windows):**
```powershell
# Change execution policy (run as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then run
.\deploy.ps1
```

---

## 📊 Monitoring Deployment

### Check Service Health
```bash
docker compose ps
```

### View Logs
```bash
# All services
docker compose logs -f

# Web service only
docker compose logs -f web

# Last 100 lines
docker compose logs --tail=100 web
```

### Check Database Tables
```bash
docker compose exec db psql -U postgres -d secureapprove -c "\dt chat_*"
```

### Verify Migration Status
```bash
docker compose exec web python manage.py showmigrations chat
```

---

## 🔐 Production Considerations

### Environment Variables
Ensure these are set in production:

```env
DJANGO_ENV=production
DEBUG=False
SECRET_KEY=<strong-random-key>
DB_HOST=<production-db-host>
DB_PASSWORD=<strong-db-password>
REDIS_URL=redis://redis:6379/0
```

### Pre-Deployment Checklist

- [ ] Backup database before deployment
- [ ] Test deployment in staging environment
- [ ] Verify Redis is running (for WebSocket support)
- [ ] Check disk space for static files
- [ ] Review recent logs for errors
- [ ] Notify team of deployment window

### Post-Deployment Checklist

- [ ] Verify all services are running (`docker compose ps`)
- [ ] Test HTTP endpoint (http://your-domain.com)
- [ ] Test chat functionality (send/receive messages)
- [ ] Check logs for errors (`docker compose logs`)
- [ ] Verify WebSocket connection (check browser console)
- [ ] Test file uploads in chat
- [ ] Monitor performance and errors

---

## 📚 Additional Resources

- **CHAT-QUICKSTART.md** - Quick deployment guide
- **CHAT-DEPLOYMENT.md** - Detailed production deployment guide
- **CHAT-DOCUMENTATION.md** - Complete API and architecture reference
- **CHAT-UPGRADE-SUMMARY.md** - Feature overview and migration summary

---

## 🆘 Support

If deployment fails:

1. Check logs: `docker compose logs --tail=100 web`
2. Review error messages carefully
3. Check database connectivity
4. Verify environment variables
5. Try `--check-only` mode first
6. Use `--force-chat-reset` in development (not production!)

For persistent issues, review the complete documentation in **CHAT-DEPLOYMENT.md**.

---

**Version:** 2.0  
**Last Updated:** November 18, 2025  
**Status:** ✅ Production Ready
