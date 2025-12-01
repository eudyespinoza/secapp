/**
 * SecureApprove - Web Push Notifications
 * Handles Service Worker registration and Push Subscription
 */

(function() {
    'use strict';

    const CONFIG = {
        SERVICE_WORKER_PATH: '/service-worker.js',
        SUBSCRIBE_ENDPOINT: '/webpush/save_information/',
        VAPID_META_NAME: 'vapid-key',
    };

    class NotificationManager {
        constructor() {
            this.subscribeButton = document.getElementById('webpush-subscribe-button');
            this.vapidKey = this.getVapidKey();
            
            this.init();
        }

        getVapidKey() {
            const meta = document.querySelector(`meta[name="${CONFIG.VAPID_META_NAME}"]`) || 
                         document.getElementById(CONFIG.VAPID_META_NAME);
            return meta ? meta.content : null;
        }

        init() {
            if (!this.subscribeButton) return;

            // Check for Secure Context
            if (!window.isSecureContext && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
                console.warn('[Push] Secure Context (HTTPS) required for Service Workers');
                this.subscribeButton.addEventListener('click', () => {
                    alert('Error: Push Notifications require HTTPS. You are accessing via an insecure connection.');
                });
                return;
            }
            
            if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
                console.warn('[Push] Push messaging is not supported');
                this.subscribeButton.style.display = 'none';
                return;
            }

            if (!this.vapidKey) {
                console.warn('[Push] VAPID key not found');
                // Alert for debugging purposes since the user reported "nothing happens"
                console.error('VAPID key missing. Check {% webpush_header %} in base.html');
                return;
            }

            this.subscribeButton.addEventListener('click', () => this.subscribe(true));
            
            // Register Service Worker immediately to keep it alive for background notifications
            this.registerServiceWorker();
            
            // Check current status
            this.checkSubscriptionStatus();
            
            // Silently ensure subscription if permission is already granted
            if (Notification.permission === 'granted') {
                this.ensureSubscription().catch(e => console.log('[Push] Silent subscription check failed:', e));
            }
        }

        async ensureSubscription() {
            // Silent subscription check/renewal - no user feedback
            try {
                const registration = await navigator.serviceWorker.getRegistration(CONFIG.SERVICE_WORKER_PATH);
                if (!registration) {
                    await this.registerServiceWorker();
                    return;
                }
                
                let subscription = await registration.pushManager.getSubscription();
                if (!subscription) {
                    const convertedVapidKey = this.urlBase64ToUint8Array(this.vapidKey);
                    subscription = await registration.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: convertedVapidKey
                    });
                    await this.sendSubscriptionToServer(subscription);
                    console.log('[Push] Silent subscription successful');
                }
                this.updateButtonState(true);
            } catch (e) {
                console.log('[Push] Silent subscription check failed:', e);
            }
        }

        async registerServiceWorker() {
            try {
                const registration = await navigator.serviceWorker.register(CONFIG.SERVICE_WORKER_PATH, {
                    updateViaCache: 'none'
                });
                console.log('[Push] Service Worker registered on page load');
                
                // Check for updates periodically
                registration.update();
                
                // Handle service worker updates
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    console.log('[Push] New Service Worker found, installing...');
                    
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            newWorker.postMessage({ type: 'SKIP_WAITING' });
                        }
                    });
                });
                
                return registration;
            } catch (e) {
                console.error('[Push] Service Worker registration failed:', e);
            }
        }

        async checkSubscriptionStatus() {
            try {
                const registration = await navigator.serviceWorker.getRegistration(CONFIG.SERVICE_WORKER_PATH);
                if (registration) {
                    const subscription = await registration.pushManager.getSubscription();
                    if (subscription) {
                        this.updateButtonState(true);
                    }
                }
            } catch (e) {
                console.error('[Push] Error checking subscription:', e);
            }
        }

        updateButtonState(isSubscribed) {
            if (isSubscribed) {
                this.subscribeButton.innerHTML = '<i class="bi bi-bell-slash me-2"></i>Disable Notifications';
                this.subscribeButton.classList.add('text-danger');
            } else {
                this.subscribeButton.innerHTML = '<i class="bi bi-bell me-2"></i>Enable Notifications';
                this.subscribeButton.classList.remove('text-danger');
            }
        }

        urlBase64ToUint8Array(base64String) {
            const padding = '='.repeat((4 - base64String.length % 4) % 4);
            const base64 = (base64String + padding)
                .replace(/\-/g, '+')
                .replace(/_/g, '/');
            const rawData = window.atob(base64);
            const outputArray = new Uint8Array(rawData.length);
            for (let i = 0; i < rawData.length; ++i) {
                outputArray[i] = rawData.charCodeAt(i);
            }
            return outputArray;
        }

        async subscribe(showFeedback = false) {
            try {
                // Check permission first
                if (Notification.permission === 'denied') {
                    if (showFeedback) {
                        alert('Notifications are blocked. Please enable them in your browser settings.');
                    }
                    return;
                }

                // 1. Register Service Worker with updateViaCache: 'none'
                const registration = await navigator.serviceWorker.register(CONFIG.SERVICE_WORKER_PATH, {
                    updateViaCache: 'none'
                });
                await navigator.serviceWorker.ready;
                console.log('[Push] Service Worker registered');

                // Force update and activation
                registration.update();
                
                if (registration.waiting) {
                    registration.waiting.postMessage({ type: 'SKIP_WAITING' });
                }

                // 2. Check if already subscribed
                let subscription = await registration.pushManager.getSubscription();
                let isNewSubscription = false;
                
                if (subscription) {
                    console.log('[Push] Already subscribed');
                } else {
                    // 3. Subscribe - new subscription
                    const convertedVapidKey = this.urlBase64ToUint8Array(this.vapidKey);
                    subscription = await registration.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: convertedVapidKey
                    });
                    console.log('[Push] Subscribed successfully');
                    isNewSubscription = true;
                }

                // 4. Send to Server
                await this.sendSubscriptionToServer(subscription);
                
                this.updateButtonState(true);
                
                // Only show success if user clicked AND it's a new subscription
                if (showFeedback && isNewSubscription) {
                    alert('Notifications enabled successfully!');
                }

            } catch (e) {
                console.error('[Push] Subscription failed:', e);
                if (showFeedback) {
                    alert('Failed to enable notifications: ' + e.message);
                }
            }
        }

        async sendSubscriptionToServer(subscription) {
            const response = await fetch(CONFIG.SUBSCRIBE_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                },
                body: JSON.stringify({
                    status_type: 'subscribe',
                    subscription: subscription.toJSON(),
                    browser: navigator.userAgent
                }),
            });

            if (!response.ok) {
                throw new Error('Failed to save subscription on server');
            }
        }

        getCsrfToken() {
            const name = 'csrftoken';
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
    }

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => new NotificationManager());
    } else {
        new NotificationManager();
    }

})();
