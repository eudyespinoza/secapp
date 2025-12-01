/**
 * SecureApprove - Service Worker for Push Notifications
 * Handles push notifications even when the app is in background or inactive
 */

// App theme colors (matching CSS variables in base.html)
const THEME_COLORS = {
  primary: '#4f46e5',      // --primary-color (indigo)
  primaryDark: '#3730a3',  // --primary-dark
  secondary: '#10b981',    // --secondary-color (green)
  success: '#059669',      // --success-color
  warning: '#d97706',      // --warning-color
  danger: '#dc2626',       // --danger-color
  info: '#0ea5e9'          // --info-color
};

// Track shown notifications to prevent duplicates
const shownNotifications = new Map();
const NOTIFICATION_DEDUPE_TIME = 5000; // 5 seconds window for deduplication

// Install event - activate immediately
self.addEventListener('install', function(event) {
  console.log('[SW] Installing Service Worker...');
  // Force the waiting service worker to become active
  event.waitUntil(self.skipWaiting());
});

// Activate event - claim all clients immediately
self.addEventListener('activate', function(event) {
  console.log('[SW] Activating Service Worker...');
  // Take control of all pages immediately
  event.waitUntil(self.clients.claim());
});

// Push event - handles incoming push notifications
self.addEventListener('push', function(event) {
  console.log('[SW] Push received:', event);
  
  let data = {
    title: 'SecureApprove',
    body: 'You have a new notification',
    icon: '/static/img/logo-push-192.png',
    badge: '/static/img/badge-mono.png',
    url: '/dashboard/'
  };

  // Parse push data if available
  if (event.data) {
    try {
      data = Object.assign(data, event.data.json());
    } catch (e) {
      console.error('[SW] Error parsing push data:', e);
      // Try as text
      try {
        const text = event.data.text();
        data.body = text;
      } catch (e2) {
        console.error('[SW] Error parsing push data as text:', e2);
      }
    }
  }

  // Create a unique key for deduplication based on tag and body
  const notificationKey = `${data.tag || 'default'}-${data.body || ''}`;
  const now = Date.now();
  
  // Check for duplicate notification within the deduplication window
  if (shownNotifications.has(notificationKey)) {
    const lastShown = shownNotifications.get(notificationKey);
    if (now - lastShown < NOTIFICATION_DEDUPE_TIME) {
      console.log('[SW] Skipping duplicate notification:', notificationKey);
      return;
    }
  }
  
  // Record this notification
  shownNotifications.set(notificationKey, now);
  
  // Clean up old entries (older than 1 minute)
  for (const [key, timestamp] of shownNotifications.entries()) {
    if (now - timestamp > 60000) {
      shownNotifications.delete(key);
    }
  }

  // Determine notification color based on type/status
  let themeColor = data.color || THEME_COLORS.primary;
  if (data.notificationType === 'approved' || data.status === 'approved') {
    themeColor = THEME_COLORS.success;
  } else if (data.notificationType === 'rejected' || data.status === 'rejected') {
    themeColor = THEME_COLORS.danger;
  } else if (data.notificationType === 'warning') {
    themeColor = THEME_COLORS.warning;
  }

  // Build notification options with all properties for background support
  const options = {
    body: data.body || 'You have a new notification',
    icon: data.icon || '/static/img/logo-push-192.png',
    badge: data.badge || '/static/img/badge-mono.png',
    image: data.image || null,
    // Tag allows replacing notifications with the same tag (prevents duplicates)
    tag: data.tag || 'secureapprove-notification',
    // Renotify: vibrate/sound even if replacing same tag notification
    renotify: data.renotify !== undefined ? data.renotify : true,
    // RequireInteraction: keep notification visible until user interacts
    requireInteraction: data.requireInteraction !== undefined ? data.requireInteraction : true,
    // Silent: no sound/vibration (we want sound, so false)
    silent: false,
    // Vibration pattern
    vibrate: data.vibrate || [200, 100, 200, 100, 200],
    // Data to pass to click handler
    data: {
      dateOfArrival: Date.now(),
      url: data.url || '/dashboard/',
      requestId: data.requestId || null,
      notificationType: data.notificationType || 'general',
      themeColor: themeColor
    },
    // Actions (buttons in the notification)
    actions: data.actions || [
      {
        action: 'view',
        title: 'View',
        icon: '/static/img/icono-verde.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/static/img/icono-cerrar.png'
      }
    ],
    // Timestamp
    timestamp: Date.now()
  };

  // Show the notification - waitUntil keeps SW alive until notification is shown
  const promiseChain = self.registration.showNotification(data.title || 'SecureApprove', options);
  
  event.waitUntil(promiseChain);
});

// Notification click event - handles user clicking on notification or action buttons
self.addEventListener('notificationclick', function(event) {
  console.log('[SW] Notification click:', event.action, event.notification);
  
  // Close the notification
  event.notification.close();
  
  const notificationData = event.notification.data || {};
  let urlToOpen = notificationData.url || '/dashboard/';

  // Handle action button clicks
  if (event.action === 'view' || event.action === 'ver') {
    // Open the specific URL
    urlToOpen = notificationData.url || '/dashboard/';
  } else if (event.action === 'close' || event.action === 'cerrar') {
    // Just close the notification (already done above)
    return;
  }

  // Open or focus the appropriate window
  const promiseChain = clients.matchAll({
    type: 'window',
    includeUncontrolled: true
  }).then(function(windowClients) {
    // Check if there is already a window/tab with the target URL
    for (let i = 0; i < windowClients.length; i++) {
      const client = windowClients[i];
      // If a matching client is found, focus it
      if (client.url.includes(urlToOpen) && 'focus' in client) {
        return client.focus();
      }
    }
    
    // If no matching client, check for any open window of our app
    for (let i = 0; i < windowClients.length; i++) {
      const client = windowClients[i];
      if ('focus' in client && 'navigate' in client) {
        return client.focus().then(function(focusedClient) {
          return focusedClient.navigate(urlToOpen);
        });
      }
    }
    
    // If no window is open, open a new one
    if (clients.openWindow) {
      return clients.openWindow(urlToOpen);
    }
  });

  event.waitUntil(promiseChain);
});

// Notification close event - handles user dismissing the notification
self.addEventListener('notificationclose', function(event) {
  console.log('[SW] Notification closed:', event.notification);
  // Could be used for analytics or cleanup
});

// Message event - allows communication between main app and service worker
self.addEventListener('message', function(event) {
  console.log('[SW] Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Periodic sync for keeping subscription alive (if supported)
self.addEventListener('periodicsync', function(event) {
  if (event.tag === 'keep-alive') {
    console.log('[SW] Periodic sync: keep-alive');
    event.waitUntil(Promise.resolve());
  }
});

// Background sync for failed push subscriptions
self.addEventListener('sync', function(event) {
  console.log('[SW] Background sync:', event.tag);
  if (event.tag === 'push-sync') {
    event.waitUntil(Promise.resolve());
  }
});
