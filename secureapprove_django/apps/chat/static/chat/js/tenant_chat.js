/**
 * SecureApprove - Tenant Chat Widget
 * 
 * Professional real-time chat widget with WebSocket support and polling fallback.
 * Features:
 * - Real-time messaging via WebSocket
 * - Automatic reconnection with exponential backoff
 * - Typing indicators
 * - Presence detection (online/offline users)
 * - File attachments support
 * - Browser notifications
 * - Multi-language support
 * - Responsive design
 */

(function() {
    'use strict';

    // ========================================
    // Configuration
    // ========================================
    
    const CONFIG = {
        POLLING_INTERVAL: 5000,          // 5 seconds
        PRESENCE_INTERVAL: 10000,        // 10 seconds
        TYPING_TIMEOUT: 1500,            // 1.5 seconds
        WEBSOCKET_RECONNECT_BASE: 1000,  // 1 second base
        WEBSOCKET_RECONNECT_MAX: 30000,  // 30 seconds max
        ONLINE_THRESHOLD: 120,           // 2 minutes
        MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
        NOTIFICATION_PERMISSION_KEY: 'chat_notification_permission_requested',
    };

    const ALLOWED_FILE_TYPES = [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain',
        'text/csv',
    ];

    // ========================================
    // State Management
    // ========================================
    
    class ChatState {
        constructor() {
            this.currentConversationId = null;
            this.lastMessageId = null;
            this.typingTimeout = null;
            this.panelVisible = false;
            this.panelInitialized = false;
            this.conversations = [];
            this.users = [];
            this.lastTotalUnread = 0;
            this.currentUserId = null;
            this.csrfToken = null;
        }

        reset() {
            this.currentConversationId = null;
            this.lastMessageId = null;
            this.clearTypingTimeout();
        }

        clearTypingTimeout() {
            if (this.typingTimeout) {
                clearTimeout(this.typingTimeout);
                this.typingTimeout = null;
            }
        }
    }

    // ========================================
    // WebSocket Manager
    // ========================================
    
    class WebSocketManager {
        constructor(callbacks) {
            this.socket = null;
            this.connected = false;
            this.reconnectAttempts = 0;
            this.reconnectTimeout = null;
            this.callbacks = callbacks || {};
        }

        connect() {
            if (!('WebSocket' in window)) {
                console.warn('WebSocket not supported');
                return false;
            }

            const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
            const url = `${scheme}://${window.location.host}/ws/chat/`;

            try {
                this.socket = new WebSocket(url);
                this.setupEventHandlers();
                return true;
            } catch (e) {
                console.error('Failed to create WebSocket:', e);
                this.scheduleReconnect();
                return false;
            }
        }

        setupEventHandlers() {
            if (!this.socket) return;

            this.socket.onopen = () => {
                console.log('%c[CHAT] ✓ WebSocket CONNECTED', 'color: green; font-weight: bold', {
                    url: this.socket ? this.socket.url : null,
                    readyState: this.socket ? this.socket.readyState : null,
                });
                this.connected = true;
                this.reconnectAttempts = 0;
                
                if (this.callbacks.onConnect) {
                    this.callbacks.onConnect();
                }

                // Send ping every 30 seconds to keep connection alive
                this.startPingInterval();
            };

            this.socket.onclose = (event) => {
                console.log('%c[CHAT] ✗ WebSocket DISCONNECTED', 'color: red; font-weight: bold', {
                    code: event.code,
                    reason: event.reason,
                    wasClean: event.wasClean,
                    readyState: this.socket ? this.socket.readyState : null,
                });
                this.connected = false;
                this.stopPingInterval();
                
                if (this.callbacks.onDisconnect) {
                    this.callbacks.onDisconnect();
                }

                // Attempt reconnection unless it was a clean close
                if (event.code !== 1000) {
                    this.scheduleReconnect();
                }
            };

            this.socket.onerror = (error) => {
                console.error('[CHAT] WebSocketManager.onerror', error);
                this.connected = false;
                
                if (this.callbacks.onError) {
                    this.callbacks.onError(error);
                }
            };

            this.socket.onmessage = (event) => {
                console.log('[CHAT] WebSocketManager.onmessage raw:', event.data);
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (e) {
                    console.error('Invalid WebSocket message:', e);
                }
            };
        }

        handleMessage(data) {
            if (!data || !data.type) return;

            const { type } = data;
            console.log('[CHAT] WebSocketManager.handleMessage parsed:', data);

            switch (type) {
                case 'connected':
                    console.log('WebSocket handshake complete');
                    break;

                case 'message_created':
                    if (this.callbacks.onMessage) {
                        this.callbacks.onMessage(data);
                    }
                    break;

                case 'typing':
                    if (this.callbacks.onTyping) {
                        this.callbacks.onTyping(data);
                    }
                    break;

                case 'presence':
                    if (this.callbacks.onPresence) {
                        this.callbacks.onPresence(data);
                    }
                    break;

                case 'pong':
                    // Health check response
                    break;

                default:
                    console.log('Unknown WebSocket message type:', type);
            }
        }

        send(data) {
            if (this.connected && this.socket && this.socket.readyState === WebSocket.OPEN) {
                console.log('%c[CHAT] → Sending WebSocket message', 'color: purple; font-weight: bold', data);
                this.socket.send(JSON.stringify(data));
                return true;
            }
            console.warn('[CHAT] Cannot send WebSocket message - not connected', { connected: this.connected, readyState: this.socket?.readyState });
            return false;
        }

        startPingInterval() {
            this.stopPingInterval();
            this.pingInterval = setInterval(() => {
                this.send({ type: 'ping' });
            }, 30000);
        }

        stopPingInterval() {
            if (this.pingInterval) {
                clearInterval(this.pingInterval);
                this.pingInterval = null;
            }
        }

        scheduleReconnect() {
            if (this.reconnectTimeout) return;

            // Exponential backoff with jitter
            const delay = Math.min(
                CONFIG.WEBSOCKET_RECONNECT_BASE * Math.pow(2, this.reconnectAttempts),
                CONFIG.WEBSOCKET_RECONNECT_MAX
            ) + Math.random() * 1000;

            console.log(`Reconnecting WebSocket in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts + 1})`);

            this.reconnectTimeout = setTimeout(() => {
                this.reconnectTimeout = null;
                this.reconnectAttempts++;
                this.connect();
            }, delay);
        }

        disconnect() {
            this.stopPingInterval();
            if (this.reconnectTimeout) {
                clearTimeout(this.reconnectTimeout);
                this.reconnectTimeout = null;
            }
            if (this.socket) {
                this.socket.close(1000, 'User disconnected');
                this.socket = null;
            }
            this.connected = false;
        }
    }

    // ========================================
    // API Client
    // ========================================
    
    class ChatAPI {
        constructor(csrfToken) {
            this.csrfToken = csrfToken;
        }

        async get(url) {
            const response = await fetch(url, {
                credentials: 'same-origin',
            });

            if (!response.ok) {
                const error = await this.parseError(response);
                throw new Error(error);
            }

            return response.json();
        }

        async post(url, body, isFormData = false) {
            const options = {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                },
            };

            if (isFormData) {
                options.body = body;
            } else {
                options.headers['Content-Type'] = 'application/json';
                options.body = JSON.stringify(body);
            }

            const response = await fetch(url, options);

            if (!response.ok) {
                const error = await this.parseError(response);
                throw new Error(error);
            }

            return response.json();
        }

        async parseError(response) {
            try {
                const data = await response.json();
                return data.error || data.detail || `Request failed (${response.status})`;
            } catch (e) {
                return `Request failed (${response.status})`;
            }
        }

        // Conversations
        async getConversations() {
            return this.get('/api/chat/conversations/');
        }

        async startConversation(participantId) {
            return this.post('/api/chat/conversations/start/', {
                participant_id: participantId,
            });
        }

        // Messages
        async getMessages(conversationId, sinceId = null) {
            let url = `/api/chat/conversations/${conversationId}/messages/`;
            if (sinceId) {
                url += `?since_id=${sinceId}`;
            }
            return this.get(url);
        }

        async sendMessage(conversationId, content, files = []) {
            const formData = new FormData();
            formData.append('content', content);
            
            for (const file of files) {
                formData.append('attachments', file);
            }

            return this.post(
                `/api/chat/conversations/${conversationId}/messages/`,
                formData,
                true
            );
        }

        async markAsRead(conversationId) {
            return this.post(`/api/chat/conversations/${conversationId}/mark_read/`, {});
        }

        async sendTyping(conversationId) {
            return this.post(`/api/chat/conversations/${conversationId}/typing/`, {});
        }

        // Presence
        async getPresence() {
            return this.get('/api/chat/conversations/presence/');
        }
    }

    // ========================================
    // UI Manager
    // ========================================
    
    class ChatUI {
        constructor(elements, i18n) {
            this.elements = elements;
            this.i18n = i18n;
            this.messageLoadingEl = null;
        }

        showError(message) {
            console.error('Chat error:', message);
            if (!this.elements.alerts) return;

            const alert = document.createElement('div');
            alert.className = 'alert alert-danger alert-dismissible fade show py-1 mb-1';
            alert.setAttribute('role', 'alert');
            alert.innerHTML = `
                <small>${this.escapeHtml(this.i18n.error)}: ${this.escapeHtml(message)}</small>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert" aria-label="Close"></button>
            `;

            this.elements.alerts.appendChild(alert);

            setTimeout(() => {
                alert.classList.remove('show');
                alert.addEventListener('transitionend', () => alert.remove(), { once: true });
            }, 5000);
        }

        showMessageLoading() {
            if (!this.elements.messageContainer || this.messageLoadingEl) return;

            const container = document.createElement('div');
            container.className = 'tenant-chat-loading text-center text-muted py-3';
            container.innerHTML = `
                <div class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></div>
                <small>${this.escapeHtml(this.i18n.loadingMessages || 'Loading...')}</small>
            `;

            this.elements.messageContainer.appendChild(container);
            this.messageLoadingEl = container;
        }

        hideMessageLoading() {
            if (this.messageLoadingEl) {
                this.messageLoadingEl.remove();
                this.messageLoadingEl = null;
            }
        }

        setPanelVisible(visible) {
            this.elements.panel.style.display = visible ? 'block' : 'none';
            this.elements.chevron.className = visible ? 'bi bi-chevron-down' : 'bi bi-chevron-up';
        }

        updateBarStatus(text) {
            if (this.elements.barStatus) {
                this.elements.barStatus.textContent = text;
            }
        }

        updatePresenceSummary(text) {
            if (this.elements.presenceSummary) {
                this.elements.presenceSummary.textContent = text;
            }
        }

        updateUnreadBadge(count) {
            if (!this.elements.badge) return;

            if (count > 0) {
                this.elements.badge.style.display = 'inline-block';
                this.elements.badge.textContent = count > 99 ? '99+' : count;
            } else {
                this.elements.badge.style.display = 'none';
                this.elements.badge.textContent = '';
            }
        }

        setCurrentConversationTitle(title) {
            if (this.elements.conversationTitle) {
                this.elements.conversationTitle.textContent = title;
            }
        }

        showTypingIndicator(show = true) {
            if (this.elements.typingIndicator) {
                this.elements.typingIndicator.style.display = show ? 'block' : 'none';
            }
        }

        clearMessages() {
            if (this.elements.messageContainer) {
                this.hideMessageLoading();
                this.elements.messageContainer.innerHTML = '';
            }
        }

        showEmptyState() {
            if (!this.elements.messageContainer) return;
            this.hideMessageLoading();

            const empty = document.createElement('div');
            empty.className = 'tenant-chat-empty-state';
            empty.textContent = this.i18n.noMessages;
            this.elements.messageContainer.appendChild(empty);
        }

        formatTime(dateString) {
            if (!dateString) return '';
            
            try {
                const date = new Date(dateString);
                if (isNaN(date.getTime())) return '';
                
                return date.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } catch (e) {
                return '';
            }
        }

        renderMessage(message, currentUserId) {
            const isMine = currentUserId && message.sender_id === currentUserId;
            
            const wrapper = document.createElement('div');
            wrapper.className = 'tenant-chat-message ' + (isMine ? 'me' : 'other');

            const bubble = document.createElement('div');
            bubble.className = 'tenant-chat-bubble';

            // Sender name
            const header = document.createElement('div');
            header.className = 'fw-semibold';
            header.textContent = message.sender_name || message.sender_email || '';
            bubble.appendChild(header);

            // Message content
            if (message.content) {
                const body = document.createElement('div');
                body.textContent = message.content;
                bubble.appendChild(body);
            }

            // Attachments
            if (message.attachments && message.attachments.length > 0) {
                const attachmentsContainer = document.createElement('div');
                attachmentsContainer.className = 'tenant-chat-attachments mt-1';
                
                message.attachments.forEach(att => {
                    if (!att || !att.file) return;
                    
                    const link = document.createElement('a');
                    link.href = att.file_url || att.file;
                    link.target = '_blank';
                    link.rel = 'noopener noreferrer';
                    link.textContent = att.filename || this.i18n.attachment;
                    attachmentsContainer.appendChild(link);
                });
                
                bubble.appendChild(attachmentsContainer);
            }

            // Metadata (time + status)
            const meta = document.createElement('div');
            meta.className = 'tenant-chat-meta';
            const timeLabel = this.formatTime(message.created_at);
            const statusLabel = message.status || '';
            meta.textContent = [timeLabel, statusLabel].filter(Boolean).join(' · ');
            bubble.appendChild(meta);

            wrapper.appendChild(bubble);
            return wrapper;
        }

        renderMessages(messages, currentUserId) {
            if (!this.elements.messageContainer) return;
            this.hideMessageLoading();

            // Remove empty state if present
            const emptyState = this.elements.messageContainer.querySelector('.tenant-chat-empty-state');
            if (emptyState) {
                emptyState.remove();
            }

            // Render messages
            messages.forEach(msg => {
                const element = this.renderMessage(msg, currentUserId);
                this.elements.messageContainer.appendChild(element);
            });

            // Scroll to bottom
            this.scrollToBottom();
        }

        scrollToBottom() {
            if (this.elements.messageContainer) {
                this.elements.messageContainer.scrollTop = this.elements.messageContainer.scrollHeight;
            }
        }

        renderConversations(conversations) {
            if (!this.elements.conversationList) return;

            this.elements.conversationList.innerHTML = '';

            conversations.forEach(conv => {
                const li = document.createElement('li');
                li.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
                li.dataset.id = conv.id;

                // Build title with preview
                const rawPreview = conv.last_message?.content || '';
                const preview = rawPreview.length > 60 
                    ? `${rawPreview.slice(0, 57)}…` 
                    : rawPreview;

                let title = conv.title || '';
                if (!title && conv.last_message) {
                    const sender = conv.last_message.sender_name || '';
                    title = preview ? `${sender}: ${preview}` : sender || this.i18n.newConversation;
                } else if (!title) {
                    title = this.i18n.newConversation;
                } else if (preview) {
                    title += ` · ${preview}`;
                }

                const unread = conv.unread_count || 0;

                li.innerHTML = `
                    <span class="text-truncate">${this.escapeHtml(title)}</span>
                    ${unread ? `<span class="badge bg-danger ms-2">${unread}</span>` : ''}
                `;

                this.elements.conversationList.appendChild(li);
            });
        }

        renderUsers(users) {
            if (!this.elements.userList) return;

            this.elements.userList.innerHTML = '';

            users.forEach(user => {
                const li = document.createElement('li');
                li.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
                li.dataset.id = user.id;

                const displayName = user.name || user.email;
                const online = !!user.is_online;
                const statusText = online ? this.i18n.online : this.i18n.offline;
                const statusClass = online ? 'text-success' : 'text-muted';

                li.innerHTML = `
                    <span>${this.escapeHtml(displayName)}</span>
                    <small class="${statusClass}">${statusText}</small>
                `;

                this.elements.userList.appendChild(li);
            });
        }

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        validateFiles(files) {
            const errors = [];

            for (const file of files) {
                if (file.size > CONFIG.MAX_FILE_SIZE) {
                    errors.push(`${file.name}: ${this.i18n.fileTooLarge}`);
                }

                if (file.type && !ALLOWED_FILE_TYPES.includes(file.type)) {
                    errors.push(`${file.name}: ${this.i18n.fileTypeNotAllowed}`);
                }
            }

            return errors;
        }
    }

    // ========================================
    // Notification Manager
    // ========================================
    
    class NotificationManager {
        constructor(i18n) {
            this.i18n = i18n;
            this.permissionRequested = localStorage.getItem(CONFIG.NOTIFICATION_PERMISSION_KEY) === 'true';
        }

        async requestPermission() {
            if (!('Notification' in window)) {
                return false;
            }

            if (this.permissionRequested) {
                return Notification.permission === 'granted';
            }

            try {
                const permission = await Notification.requestPermission();
                this.permissionRequested = true;
                localStorage.setItem(CONFIG.NOTIFICATION_PERMISSION_KEY, 'true');
                return permission === 'granted';
            } catch (e) {
                console.error('Error requesting notification permission:', e);
                return false;
            }
        }

        canNotify() {
            return 'Notification' in window && Notification.permission === 'granted';
        }

        show(title, body, icon = null) {
            if (!this.canNotify()) return;

            try {
                const notification = new Notification(title, {
                    body: body,
                    icon: icon || '/static/favicon.ico',
                    badge: icon || '/static/favicon.ico',
                    tag: 'chat-message',
                    renotify: false,
                });

                notification.onclick = () => {
                    window.focus();
                    notification.close();
                };

                // Auto-close after 5 seconds
                setTimeout(() => notification.close(), 5000);
            } catch (e) {
                console.error('Error showing notification:', e);
            }
        }

        notifyNewMessage(senderName, preview, count) {
            if (count === 1) {
                this.show(
                    this.i18n.newMessage,
                    `${senderName}: ${preview}`
                );
            } else {
                this.show(
                    this.i18n.newMessages,
                    `${count} ${this.i18n.unreadMessages}`
                );
            }
        }
    }

    // ========================================
    // Main Chat Widget
    // ========================================
    
    class TenantChatWidget {
        constructor(config) {
            this.state = new ChatState();
            this.state.currentUserId = config.currentUserId;
            this.state.csrfToken = config.csrfToken;

            this.elements = config.elements;
            this.i18n = config.i18n;

            this.api = new ChatAPI(this.state.csrfToken);
            this.ui = new ChatUI(this.elements, this.i18n);
            this.notifications = new NotificationManager(this.i18n);

            this.ws = new WebSocketManager({
                onConnect: () => this.handleWebSocketConnect(),
                onDisconnect: () => this.handleWebSocketDisconnect(),
                onMessage: (data) => this.handleWebSocketMessage(data),
                onTyping: (data) => this.handleWebSocketTyping(data),
                onPresence: (data) => this.handleWebSocketPresence(data),
            });

            this.pollingInterval = null;
            this.presenceInterval = null;

            this.init();
        }

        normalizeConversationData(conversation) {
            if (!conversation || typeof conversation !== 'object') {
                return null;
            }

            const normalized = { ...conversation };
            normalized.id = normalized.id != null ? String(normalized.id) : '';

            if (normalized.last_message) {
                normalized.last_message = this.normalizeMessageData(
                    normalized.last_message,
                    normalized.id
                );
            }

            return normalized;
        }

        normalizeMessageData(message, fallbackConversationId = null) {
            if (!message || typeof message !== 'object') {
                return null;
            }

            const normalized = { ...message };

            if (normalized.conversation !== undefined && normalized.conversation !== null) {
                normalized.conversation = String(normalized.conversation);
            } else if (fallbackConversationId) {
                normalized.conversation = fallbackConversationId;
            }

            if (normalized.conversation_id !== undefined && normalized.conversation_id !== null) {
                normalized.conversation_id = String(normalized.conversation_id);
            }

            if (normalized.attachments && Array.isArray(normalized.attachments)) {
                normalized.attachments = normalized.attachments.map(att => ({ ...att }));
            }

            const senderId = normalized.sender?.id ?? normalized.sender_id ?? null;
            const senderName = normalized.sender?.name ?? normalized.sender_name ?? '';
            const senderEmail = normalized.sender?.email ?? normalized.sender_email ?? '';

            if (normalized.sender_id == null && senderId != null) {
                normalized.sender_id = senderId;
            }
            if (!normalized.sender_name && senderName) {
                normalized.sender_name = senderName;
            }
            if (!normalized.sender_email && senderEmail) {
                normalized.sender_email = senderEmail;
            }

            normalized.sender = {
                id: senderId,
                name: normalized.sender_name || senderName || '',
                email: normalized.sender_email || senderEmail || '',
            };

            return normalized;
        }

        init() {
            console.log('[CHAT] TenantChatWidget.init');
            this.setupEventListeners();
            this.startWebSocket();
            this.startPolling();
            this.loadInitialData();

            // Request notification permission after a short delay
            setTimeout(() => {
                if (!this.notifications.permissionRequested) {
                    this.notifications.requestPermission();
                }
            }, 3000);
        }

        setupEventListeners() {
            // Toggle panel
            this.elements.bar.addEventListener('click', () => {
                this.togglePanel();
            });

            // Conversation selection
            this.elements.conversationList.addEventListener('click', (e) => {
                const item = e.target.closest('li');
                if (item && item.dataset.id) {
                    const convId = item.dataset.id ? String(item.dataset.id) : null;
                    const conv = this.state.conversations.find(c => c.id === convId);
                    this.openConversation(convId, conv?.title);
                    this.switchToTab('chat-active');
                }
            });

            // User selection
            this.elements.userList.addEventListener('click', (e) => {
                const item = e.target.closest('li');
                if (item && item.dataset.id) {
                    this.startConversation(item.dataset.id);
                    this.switchToTab('chat-active');
                }
            });

            // Message form submission
            this.elements.messageForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendMessage();
            });

            // Typing indicator
            this.elements.messageInput.addEventListener('input', () => {
                this.handleTyping();
            });

            // Prevent form submission on Enter (except with Shift+Enter)
            this.elements.messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        togglePanel() {
            this.state.panelVisible = !this.state.panelVisible;
            this.ui.setPanelVisible(this.state.panelVisible);

            if (this.state.panelVisible && !this.state.panelInitialized) {
                this.state.panelInitialized = true;
                this.loadConversations();
                this.loadPresence();
            }
        }

        switchToTab(tabId) {
            const tab = document.querySelector(`#${tabId}-tab`);
            if (tab) {
                tab.click();
            }
        }

        async loadInitialData() {
            try {
                await Promise.all([
                    this.loadConversations(),
                    this.loadPresence(),
                ]);
            } catch (e) {
                console.error('Error loading initial data:', e);
            }
        }

        async loadConversations() {
            try {
                const data = await this.api.getConversations();
                console.log('[CHAT] conversations API response:', data);
                const normalized = Array.isArray(data)
                    ? data.map(conv => this.normalizeConversationData(conv)).filter(Boolean)
                    : [];
                this.state.conversations = normalized;

                // Sort by last message date
                this.state.conversations.sort((a, b) => {
                    const dateA = a.last_message?.created_at 
                        ? new Date(a.last_message.created_at) 
                        : new Date(0);
                    const dateB = b.last_message?.created_at 
                        ? new Date(b.last_message.created_at) 
                        : new Date(0);
                    return dateB - dateA;
                });

                this.ui.renderConversations(this.state.conversations);
                this.updateUnreadCount();
            } catch (e) {
                console.error('Error loading conversations:', e);
                this.ui.updateBarStatus(this.i18n.serviceUnavailable);
            }
        }

        async loadPresence() {
            try {
                const data = await this.api.getPresence();
                this.state.users = Array.isArray(data) ? data : [];

                const onlineCount = this.state.users.filter(u => u.is_online).length;
                
                this.ui.renderUsers(this.state.users);
                
                if (onlineCount > 0) {
                    const statusText = `${onlineCount} ${this.i18n.usersOnline}`;
                    this.ui.updateBarStatus(statusText);
                    this.ui.updatePresenceSummary(statusText);
                } else {
                    this.ui.updateBarStatus(this.i18n.noUsersOnline);
                    this.ui.updatePresenceSummary(this.i18n.noUsersOnline);
                }
            } catch (e) {
                console.error('Error loading presence:', e);
                this.ui.updateBarStatus(this.i18n.serviceUnavailable);
                this.ui.updatePresenceSummary(this.i18n.serviceUnavailable);
            }
        }

        async startConversation(userId) {
            try {
                const conv = await this.api.startConversation(userId);
                const normalizedConv = this.normalizeConversationData(conv);
                if (normalizedConv && normalizedConv.id) {
                    await this.loadConversations();
                    await this.openConversation(normalizedConv.id, normalizedConv.title);
                }
            } catch (e) {
                console.error('Error starting conversation:', e);
                this.ui.showError(this.i18n.errorStartingConversation);
            }
        }

        async openConversation(conversationId, title) {
            this.state.currentConversationId = conversationId != null ? String(conversationId) : null;
            this.state.lastMessageId = null;

            this.ui.clearMessages();
            const fallbackTitle = `${this.i18n.conversation} ${(this.state.currentConversationId || '').substring(0, 8)}`;
            this.ui.setCurrentConversationTitle(title || fallbackTitle);

            await this.loadMessages();
        }

        async loadMessages() {
            if (!this.state.currentConversationId) return;

            try {
                this.ui.showMessageLoading();
                const messages = await this.api.getMessages(
                    this.state.currentConversationId,
                    this.state.lastMessageId
                );

                const normalizedMessages = Array.isArray(messages)
                    ? messages.map(msg => this.normalizeMessageData(msg, this.state.currentConversationId)).filter(Boolean)
                    : [];

                if (normalizedMessages.length === 0) {
                    if (!this.state.lastMessageId) {
                        this.ui.showEmptyState();
                    }
                    return;
                }

                this.ui.renderMessages(normalizedMessages, this.state.currentUserId);

                // Update last message ID
                if (normalizedMessages.length > 0) {
                    const lastMessage = normalizedMessages[normalizedMessages.length - 1];
                    this.state.lastMessageId = lastMessage.id;
                }

                // Mark as read
                await this.api.markAsRead(this.state.currentConversationId);
                await this.loadConversations();
            } catch (e) {
                console.error('Error loading messages:', e);
                this.ui.showError(this.i18n.errorLoadingMessages);
            } finally {
                this.ui.hideMessageLoading();
            }
        }

        async sendMessage() {
            if (!this.state.currentConversationId) return;

            const content = this.elements.messageInput.value.trim();
            const files = Array.from(this.elements.attachmentInput.files);
            const sendButton = this.elements.sendButton;

            if (!content && files.length === 0) return;

            // Validate files
            const fileErrors = this.ui.validateFiles(files);
            if (fileErrors.length > 0) {
                this.ui.showError(fileErrors.join('\n'));
                return;
            }

            try {
                if (sendButton) {
                    sendButton.disabled = true;
                }
                await this.api.sendMessage(this.state.currentConversationId, content, files);

                // Clear inputs
                this.elements.messageInput.value = '';
                this.elements.attachmentInput.value = '';

                // Reload messages
                await this.loadMessages();
            } catch (e) {
                console.error('Error sending message:', e);
                this.ui.showError(this.i18n.errorSendingMessage);
            } finally {
                if (sendButton) {
                    sendButton.disabled = false;
                }
            }
        }

        async handleTyping() {
            if (!this.state.currentConversationId) return;

            try {
                await this.api.sendTyping(this.state.currentConversationId);
            } catch (e) {
                // Silently fail
            }

            // Show typing indicator briefly
            this.ui.showTypingIndicator(true);
            this.state.clearTypingTimeout();
            this.state.typingTimeout = setTimeout(() => {
                this.ui.showTypingIndicator(false);
            }, CONFIG.TYPING_TIMEOUT);
        }

        updateUnreadCount() {
            console.log('[CHAT] conversations state for unread:', this.state.conversations);
            const totalUnread = this.state.conversations.reduce(
                (sum, conv) => sum + (conv.unread_count || 0),
                0
            );
            console.log('[CHAT] total unread computed:', totalUnread, 'panelVisible:', this.state.panelVisible);

            this.ui.updateUnreadBadge(totalUnread);

            // Show notification if unread count increased
            if (totalUnread > this.state.lastTotalUnread) {
                const diff = totalUnread - this.state.lastTotalUnread;
                
                if (this.notifications.canNotify() && !this.state.panelVisible) {
                    // Find most recent conversation with new messages
                    const recentConv = this.state.conversations.find(c => c.unread_count > 0);
                    if (recentConv && recentConv.last_message) {
                        const preview = recentConv.last_message.content || '';
                        this.notifications.notifyNewMessage(
                            recentConv.last_message.sender_name || recentConv.title,
                            preview.substring(0, 100),
                            diff
                        );
                    }
                }
            }

            this.state.lastTotalUnread = totalUnread;
        }

        // WebSocket handlers
        startWebSocket() {
            this.ws.connect();
        }

        handleWebSocketConnect() {
            console.log('[CHAT] TenantChatWidget.handleWebSocketConnect');
        }

        handleWebSocketDisconnect() {
            console.log('[CHAT] TenantChatWidget.handleWebSocketDisconnect');
        }

        handleWebSocketMessage(data) {
            console.log('[CHAT] WS message_created payload:', data);
            const incomingConversationId = data && data.conversation_id != null
                ? String(data.conversation_id)
                : null;
            const currentConversationId = this.state.currentConversationId != null
                ? String(this.state.currentConversationId)
                : null;
            console.log('[CHAT] handleWebSocketMessage state:', {
                incomingConversationId,
                currentConversationId,
                panelVisible: this.state.panelVisible,
            });
            const message = this.normalizeMessageData(data?.message, incomingConversationId);

            if (!incomingConversationId || !message) return;

            // Check if this message is from another user (not from current user)
            const senderId = message.sender?.id ?? message.sender_id ?? null;
            const currentUserId = this.state.currentUserId;
            const isFromOtherUser = senderId != null && (
                currentUserId == null || String(senderId) !== String(currentUserId)
            );

            // If this is for the current conversation, add message
            if (currentConversationId && currentConversationId === incomingConversationId) {
                this.ui.renderMessages([message], this.state.currentUserId);
                
                // Mark as read immediately if panel is open
                if (this.state.panelVisible) {
                    this.api.markAsRead(incomingConversationId).catch(e => 
                        console.error('Error marking as read:', e)
                    );
                } else if (isFromOtherUser) {
                    // Show notification if panel is closed and message is from someone else
                    this.showMessageNotification(message);
                }
            } else if (isFromOtherUser) {
                // Message is for a different conversation - always show notification
                this.showMessageNotification(message);
            }

            // Refresh conversations list to update unread counts
            this.loadConversations();
        }

        showMessageNotification(message) {
            if (!message) return;

            const senderName = message.sender?.name
                || message.sender_name
                || message.sender?.email
                || message.sender_email
                || this.i18n.unknownUser;
            const messagePreview = message.content 
                ? (message.content.length > 50 ? message.content.substring(0, 50) + '...' : message.content)
                : this.i18n.newMessage;

            this.notifications.show(
                `${senderName}`,
                messagePreview
            );
        }

        handleWebSocketTyping(data) {
            const { conversation_id, user_id, user_name } = data;

            // Only show typing for current conversation and from other users
            if (this.state.currentConversationId === conversation_id && 
                user_id !== this.state.currentUserId) {
                this.ui.showTypingIndicator(true);
                
                // Hide after timeout
                setTimeout(() => {
                    this.ui.showTypingIndicator(false);
                }, CONFIG.TYPING_TIMEOUT);
            }
        }

        handleWebSocketPresence(data) {
            // Refresh presence list
            this.loadPresence();
        }

        // Polling fallback
        startPolling() {
            // Main polling for conversations and messages
            this.pollingInterval = setInterval(() => {
                this.loadConversations();

                // Keep active conversation fresh even if WebSocket is connected
                if (this.state.panelVisible && this.state.currentConversationId) {
                    this.loadMessages();
                }

                // If socket got disconnected silently, attempt reconnect
                if (!this.ws.connected) {
                    const socketReadyState = this.ws.socket ? this.ws.socket.readyState : WebSocket.CLOSED;
                    if (!this.ws.socket || socketReadyState === WebSocket.CLOSED) {
                        this.ws.connect();
                    }
                }
            }, CONFIG.POLLING_INTERVAL);

            // Presence polling
            this.presenceInterval = setInterval(() => {
                this.loadPresence();
            }, CONFIG.PRESENCE_INTERVAL);
        }

        stopPolling() {
            if (this.pollingInterval) {
                clearInterval(this.pollingInterval);
                this.pollingInterval = null;
            }
            if (this.presenceInterval) {
                clearInterval(this.presenceInterval);
                this.presenceInterval = null;
            }
        }

        destroy() {
            this.stopPolling();
            this.ws.disconnect();
            this.state.reset();
        }
    }

    // ========================================
    // Bootstrap and Initialize
    // ========================================
    
    function initializeTenantChat() {
        console.log('[CHAT] initializeTenantChat called');
        // Get DOM elements
        const elements = {
            bar: document.getElementById('tenantChatBar'),
            panel: document.getElementById('tenantChatPanel'),
            chevron: document.getElementById('widgetChatChevron'),
            badge: document.getElementById('widgetNewMessagesBadge'),
            barStatus: document.getElementById('widgetBarStatus'),
            conversationList: document.getElementById('widgetConversationList'),
            userList: document.getElementById('widgetUserList'),
            messageContainer: document.getElementById('widgetMessageContainer'),
            messageForm: document.getElementById('widgetMessageForm'),
            messageInput: document.getElementById('widgetMessageInput'),
            attachmentInput: document.getElementById('widgetAttachmentInput'),
            typingIndicator: document.getElementById('widgetTypingIndicator'),
            presenceSummary: document.getElementById('widgetPresenceSummary'),
            conversationTitle: document.getElementById('widgetCurrentConversationTitle'),
            alerts: document.getElementById('widgetChatAlerts'),
            sendButton: document.getElementById('widgetSendButton'),
        };

        // Validate required elements
        if (!elements.bar || !elements.panel || !elements.messageForm) {
            console.error('Chat widget: required DOM elements not found');
            return null;
        }

        // Get CSRF token
        const csrfInput = elements.messageForm.querySelector('[name=csrfmiddlewaretoken]');
        const csrfToken = csrfInput ? csrfInput.value : '';

        // Get current user ID (injected by Django template)
        const currentUserId = window.CHAT_CURRENT_USER_ID || null;

        // Get i18n strings (injected by Django template)
        const i18n = window.CHAT_I18N || {
            newMessage: 'New chat message',
            newMessages: 'New chat messages',
            unreadMessages: 'unread messages',
            usersOnline: 'users online',
            noUsersOnline: 'No users online',
            online: 'Online',
            offline: 'Offline',
            serviceUnavailable: 'Chat service unavailable',
            noMessages: 'No messages yet. Start the conversation.',
            conversation: 'Conversation',
            newConversation: 'New conversation',
            attachment: 'Attachment',
            error: 'Error',
            errorStartingConversation: 'Could not start conversation',
            errorLoadingMessages: 'Could not load messages',
            errorSendingMessage: 'Could not send message',
            fileTooLarge: 'File is too large',
            fileTypeNotAllowed: 'File type not allowed',
            loadingMessages: 'Loading messages...',
            unknownUser: 'Unknown user',
        };

        // Create widget
        const widget = new TenantChatWidget({
            elements,
            i18n,
            currentUserId,
            csrfToken,
        });

        return widget;
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeTenantChat);
    } else {
        initializeTenantChat();
    }

})();
