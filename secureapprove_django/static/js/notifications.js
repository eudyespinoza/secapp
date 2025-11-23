/**
 * SecureApprove - Web Push Notifications
 * Handles Service Worker registration and Push Subscription
 */

(function() {
    'use strict';

    const CONFIG = {
        SERVICE_WORKER_PATH: '/service-worker.js',
        SUBSCRIBE_ENDPOINT: '/webpush/save_information',
        VAPID_META_NAME: 'vapid-key',
    };

    const I18N = {
        en: {
            httpsRequired: 'Error: Push Notifications require HTTPS. You are accessing via an insecure connection.',
            permissionDenied: 'Notifications are blocked. Please enable them in your browser settings (click the lock icon in the address bar).',
            success: 'Notifications enabled successfully!',
            error: 'Failed to enable notifications: ',
            titleSuccess: 'Success',
            titleError: 'Error'
        },
        es: {
            httpsRequired: 'Error: Las notificaciones Push requieren HTTPS. Estás accediendo a través de una conexión insegura.',
            permissionDenied: 'Las notificaciones están bloqueadas. Por favor, habilítalas en la configuración de tu navegador (haz clic en el candado de la barra de direcciones).',
            success: '¡Notificaciones activadas con éxito!',
            error: 'Error al activar las notificaciones: ',
            titleSuccess: 'Éxito',
            titleError: 'Error'
        },
        'pt-br': {
            httpsRequired: 'Erro: Notificações Push requerem HTTPS. Você está acessando via conexão insegura.',
            permissionDenied: 'As notificações estão bloqueadas. Por favor, ative-as nas configurações do seu navegador (clique no cadeado na barra de endereços).',
            success: 'Notificações ativadas com sucesso!',
            error: 'Falha ao ativar notificações: ',
            titleSuccess: 'Sucesso',
            titleError: 'Erro'
        }
    };

    class NotificationManager {
        constructor() {
            this.subscribeButton = document.getElementById('webpush-subscribe-button');
            this.vapidKey = this.getVapidKey();
            
            // Detect language
            this.lang = document.documentElement.lang.toLowerCase() || 'en';
            // Handle cases like 'es-es' -> 'es', but keep 'pt-br'
            if (this.lang !== 'pt-br' && this.lang.includes('-')) {
                this.lang = this.lang.split('-')[0];
            }
            if (!I18N[this.lang]) this.lang = 'en';

            this.init();
        }

        t(key) {
            return I18N[this.lang][key] || I18N['en'][key];
        }

        showToast(message, type = 'info') {
            const toastEl = document.getElementById('systemToast');
            const toastTitle = document.getElementById('systemToastTitle');
            const toastBody = document.getElementById('systemToastBody');
            const toastIcon = document.getElementById('systemToastIcon');
            
            if (!toastEl || !toastTitle || !toastBody) {
                // Fallback if toast elements are missing
                alert(message);
                return;
            }

            toastBody.textContent = message;
            
            if (type === 'success') {
                toastTitle.textContent = this.t('titleSuccess');
                toastIcon.className = 'bi bi-check-circle-fill me-2 text-success';
            } else if (type === 'error') {
                toastTitle.textContent = this.t('titleError');
                toastIcon.className = 'bi bi-exclamation-triangle-fill me-2 text-danger';
            } else {
                toastTitle.textContent = 'Notification';
                toastIcon.className = 'bi bi-bell-fill me-2 text-primary';
            }

            // Use Bootstrap's Toast API
            // Assuming bootstrap is available globally as per base.html
            if (typeof bootstrap !== 'undefined') {
                const toast = new bootstrap.Toast(toastEl);
                toast.show();
            } else {
                alert(message);
            }
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
                    this.showToast(this.t('httpsRequired'), 'error');
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

            this.subscribeButton.addEventListener('click', () => this.subscribe());
            
            // Check current status
            this.checkSubscriptionStatus();
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

        async subscribe() {
            try {
                // Check permission first
                if (Notification.permission === 'denied') {
                    this.showToast(this.t('permissionDenied'), 'error');
                    return;
                }

                // 1. Register Service Worker
                const registration = await navigator.serviceWorker.register(CONFIG.SERVICE_WORKER_PATH);
                await navigator.serviceWorker.ready;
                console.log('[Push] Service Worker registered');

                // 2. Check if already subscribed
                let subscription = await registration.pushManager.getSubscription();
                
                if (subscription) {
                    // Unsubscribe logic could go here if we want to toggle
                    // For now, we'll just re-send to server to be safe
                    console.log('[Push] Already subscribed');
                } else {
                    // 3. Subscribe
                    const convertedVapidKey = this.urlBase64ToUint8Array(this.vapidKey);
                    subscription = await registration.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: convertedVapidKey
                    });
                    console.log('[Push] Subscribed successfully');
                }

                // 4. Send to Server
                await this.sendSubscriptionToServer(subscription);
                
                this.updateButtonState(true);
                this.showToast(this.t('success'), 'success');

            } catch (e) {
                console.error('[Push] Subscription failed:', e);
                
                let errorMsg = e.message;
                if (errorMsg.includes('permission denied') || errorMsg.includes('Permission denied')) {
                    errorMsg = this.t('permissionDenied');
                } else {
                    errorMsg = this.t('error') + errorMsg;
                }
                
                this.showToast(errorMsg, 'error');
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
                    browser: this.getBrowserName(),
                    user_agent: navigator.userAgent
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

        getBrowserName() {
            const agent = navigator.userAgent.toLowerCase();
            if (agent.indexOf('edge') > -1) return 'Edge';
            if (agent.indexOf('edg') > -1) return 'Edge';
            if (agent.indexOf('opr') > -1) return 'Opera';
            if (agent.indexOf('chrome') > -1) return 'Chrome';
            if (agent.indexOf('firefox') > -1) return 'Firefox';
            if (agent.indexOf('safari') > -1) return 'Safari';
            return 'Other';
        }
    }

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => new NotificationManager());
    } else {
        new NotificationManager();
    }

})();
