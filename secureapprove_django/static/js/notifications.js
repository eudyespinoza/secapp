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
            titleError: 'Error',
            iosPwaRequired: 'To receive notifications on iOS, please add this app to your Home Screen: tap the Share button and select "Add to Home Screen".',
            iosPwaTitle: 'iOS Instructions'
        },
        es: {
            httpsRequired: 'Error: Las notificaciones Push requieren HTTPS. Estás accediendo a través de una conexión insegura.',
            permissionDenied: 'Las notificaciones están bloqueadas. Por favor, habilítalas en la configuración de tu navegador (haz clic en el candado de la barra de direcciones).',
            success: '¡Notificaciones activadas con éxito!',
            error: 'Error al activar las notificaciones: ',
            titleSuccess: 'Éxito',
            titleError: 'Error',
            iosPwaRequired: 'Para recibir notificaciones en iOS, agrega esta app a tu pantalla de inicio: toca el botón Compartir y selecciona "Añadir a pantalla de inicio".',
            iosPwaTitle: 'Instrucciones iOS'
        },
        'pt-br': {
            httpsRequired: 'Erro: Notificações Push requerem HTTPS. Você está acessando via conexão insegura.',
            permissionDenied: 'As notificações estão bloqueadas. Por favor, ative-as nas configurações do seu navegador (clique no cadeado na barra de endereços).',
            success: 'Notificações ativadas com sucesso!',
            error: 'Falha ao ativar notificações: ',
            titleSuccess: 'Sucesso',
            titleError: 'Erro',
            iosPwaRequired: 'Para receber notificações no iOS, adicione este app à sua tela inicial: toque no botão Compartilhar e selecione "Adicionar à Tela de Início".',
            iosPwaTitle: 'Instruções iOS'
        }
    };

    // Detect iOS Safari (not in standalone/PWA mode)
    function isIOSSafari() {
        const ua = navigator.userAgent;
        const isIOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
        const isSafari = /Safari/.test(ua) && !/Chrome|CriOS|FxiOS|OPiOS|mercury/.test(ua);
        return isIOS && isSafari;
    }

    function isStandalone() {
        return window.matchMedia('(display-mode: standalone)').matches || 
               window.navigator.standalone === true;
    }

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

        showIOSPwaInstructions() {
            // Show a modal with iOS PWA installation instructions
            const existingModal = document.getElementById('iosPwaModal');
            if (existingModal) {
                const modal = new bootstrap.Modal(existingModal);
                modal.show();
                return;
            }

            // Create modal dynamically
            const modalHtml = `
                <div class="modal fade" id="iosPwaModal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">
                                    <i class="bi bi-phone me-2"></i>${this.t('iosPwaTitle')}
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body text-center">
                                <div class="mb-3">
                                    <i class="bi bi-box-arrow-up display-4 text-primary"></i>
                                </div>
                                <p class="mb-3">${this.t('iosPwaRequired')}</p>
                                <div class="d-flex justify-content-center gap-3 text-muted">
                                    <div>
                                        <i class="bi bi-1-circle-fill fs-4 text-primary d-block mb-1"></i>
                                        <small>Tap <i class="bi bi-box-arrow-up"></i></small>
                                    </div>
                                    <div>
                                        <i class="bi bi-2-circle-fill fs-4 text-primary d-block mb-1"></i>
                                        <small>Add to Home Screen</small>
                                    </div>
                                    <div>
                                        <i class="bi bi-3-circle-fill fs-4 text-primary d-block mb-1"></i>
                                        <small>Open from Home</small>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-primary" data-bs-dismiss="modal">OK</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            const modal = new bootstrap.Modal(document.getElementById('iosPwaModal'));
            modal.show();
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

            // Check for iOS Safari not in standalone mode
            if (isIOSSafari() && !isStandalone()) {
                console.warn('[Push] iOS Safari requires PWA mode for push notifications');
                this.subscribeButton.addEventListener('click', () => {
                    this.showIOSPwaInstructions();
                });
                // Still continue to check support in case iOS 16.4+ supports it
            }
            
            if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
                console.warn('[Push] Push messaging is not supported');
                // On iOS, show instructions instead of hiding button
                if (isIOSSafari()) {
                    this.subscribeButton.addEventListener('click', () => {
                        this.showIOSPwaInstructions();
                    });
                } else {
                    this.subscribeButton.style.display = 'none';
                }
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
            
            // Check current status and auto-subscribe if permission is granted
            this.checkSubscriptionStatus();
            
            if (Notification.permission === 'granted') {
                // Silently ensure subscription is valid (no toast)
                this.ensureSubscription().catch(e => console.log('[Push] Auto-subscribe failed:', e));
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
                    // Need to subscribe
                    const convertedVapidKey = this.urlBase64ToUint8Array(this.vapidKey);
                    subscription = await registration.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: convertedVapidKey
                    });
                    // Send to server silently
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
                            // New service worker is installed but waiting
                            // Tell it to activate immediately
                            newWorker.postMessage({ type: 'SKIP_WAITING' });
                        }
                    });
                });
                
                // Listen for controller change to reload if needed
                navigator.serviceWorker.addEventListener('controllerchange', () => {
                    console.log('[Push] Service Worker controller changed');
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
                        this.showToast(this.t('permissionDenied'), 'error');
                    }
                    return;
                }

                // 1. Register Service Worker with updateViaCache: 'none' to ensure fresh SW
                const registration = await navigator.serviceWorker.register(CONFIG.SERVICE_WORKER_PATH, {
                    updateViaCache: 'none'
                });
                
                // Wait for the service worker to be ready
                await navigator.serviceWorker.ready;
                console.log('[Push] Service Worker registered');

                // Check for updates and force activation
                registration.update();
                
                // If there's a waiting service worker, tell it to activate immediately
                if (registration.waiting) {
                    registration.waiting.postMessage({ type: 'SKIP_WAITING' });
                }

                // 2. Check if already subscribed
                let subscription = await registration.pushManager.getSubscription();
                let isNewSubscription = false;
                
                if (subscription) {
                    // Already subscribed - just update server silently
                    console.log('[Push] Already subscribed');
                } else {
                    // 3. Subscribe - this is a new subscription
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
                
                // Only show success message if user clicked the button AND it's a new subscription
                // OR if user explicitly clicked (showFeedback=true) regardless
                if (showFeedback && isNewSubscription) {
                    this.showToast(this.t('success'), 'success');
                }

            } catch (e) {
                console.error('[Push] Subscription failed:', e);
                
                if (showFeedback) {
                    let errorMsg = e.message;
                    if (errorMsg.includes('permission denied') || errorMsg.includes('Permission denied')) {
                        errorMsg = this.t('permissionDenied');
                    } else {
                        errorMsg = this.t('error') + errorMsg;
                    }
                    
                    this.showToast(errorMsg, 'error');
                }
            }
        }

        async sendSubscriptionToServer(subscription) {
            const response = await fetch(CONFIG.SUBSCRIBE_ENDPOINT, {
                method: 'POST',
                credentials: 'same-origin',  // Required for iOS Safari cookie handling
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
