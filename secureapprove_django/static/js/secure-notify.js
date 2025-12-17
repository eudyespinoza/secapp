/**
 * SecureApprove - Global UI Notification System
 * 
 * Provides consistent, themed notification popups across the entire application.
 * Supports light/dark themes and multiple notification types.
 * Replaces browser alert() with styled modals.
 * 
 * Usage:
 *   SecureNotify.error('Something went wrong');
 *   SecureNotify.success('Operation completed!');
 *   SecureNotify.warning('Please check your input');
 *   SecureNotify.info('Did you know?');
 *   SecureNotify.show('Custom message', 'error', callback);
 */

(function() {
    'use strict';

    // Notification type configurations
    const NOTIFICATION_TYPES = {
        error: {
            icon: 'bi-exclamation-triangle-fill',
            titleKey: 'Error',
            cssClass: 'error'
        },
        warning: {
            icon: 'bi-exclamation-circle-fill',
            titleKey: 'Warning',
            cssClass: 'warning'
        },
        info: {
            icon: 'bi-info-circle-fill',
            titleKey: 'Information',
            cssClass: 'info'
        },
        success: {
            icon: 'bi-check-circle-fill',
            titleKey: 'Success',
            cssClass: 'success'
        }
    };

    // Translations (will be overridden by Django i18n if available)
    const DEFAULT_TRANSLATIONS = {
        'Error': 'Error',
        'Warning': 'Warning',
        'Information': 'Information',
        'Success': 'Success',
        'OK': 'OK'
    };

    let translations = { ...DEFAULT_TRANSLATIONS };
    let overlay = null;
    let isInitialized = false;

    /**
     * Initialize the notification system
     */
    function init() {
        if (isInitialized) return;

        // Load translations if available
        if (window.SECURE_NOTIFY_I18N) {
            translations = { ...DEFAULT_TRANSLATIONS, ...window.SECURE_NOTIFY_I18N };
        }

        // Create notification overlay if it doesn't exist
        if (!document.getElementById('secureNotifyOverlay')) {
            createOverlay();
        }

        overlay = document.getElementById('secureNotifyOverlay');
        isInitialized = true;
    }

    /**
     * Create the notification overlay and inject into DOM
     */
    function createOverlay() {
        // Create styles if not already present
        if (!document.getElementById('secureNotifyStyles')) {
            const style = document.createElement('style');
            style.id = 'secureNotifyStyles';
            style.textContent = `
                .secure-notify-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 99999;
                    opacity: 0;
                    visibility: hidden;
                    transition: opacity 0.3s ease, visibility 0.3s ease;
                }
                .secure-notify-overlay.show {
                    opacity: 1;
                    visibility: visible;
                }
                .secure-notify-popup {
                    background: var(--card-bg, #ffffff);
                    border-radius: 16px;
                    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
                    border: 1px solid var(--border-color, #e5e7eb);
                    max-width: 420px;
                    width: 90%;
                    padding: 1.5rem;
                    transform: scale(0.9) translateY(-20px);
                    transition: transform 0.3s ease;
                }
                .secure-notify-overlay.show .secure-notify-popup {
                    transform: scale(1) translateY(0);
                }
                .secure-notify-icon {
                    width: 56px;
                    height: 56px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 1rem;
                }
                .secure-notify-icon i {
                    font-size: 24px;
                }
                .secure-notify-icon.error {
                    background: linear-gradient(135deg, #fee2e2, #fecaca);
                    color: #dc2626;
                }
                .secure-notify-icon.warning {
                    background: linear-gradient(135deg, #fef3c7, #fde68a);
                    color: #d97706;
                }
                .secure-notify-icon.info {
                    background: linear-gradient(135deg, #dbeafe, #bfdbfe);
                    color: #2563eb;
                }
                .secure-notify-icon.success {
                    background: linear-gradient(135deg, #d1fae5, #a7f3d0);
                    color: #059669;
                }
                [data-theme="dark"] .secure-notify-icon.error {
                    background: linear-gradient(135deg, #7f1d1d, #991b1b);
                    color: #fca5a5;
                }
                [data-theme="dark"] .secure-notify-icon.warning {
                    background: linear-gradient(135deg, #78350f, #92400e);
                    color: #fcd34d;
                }
                [data-theme="dark"] .secure-notify-icon.info {
                    background: linear-gradient(135deg, #1e3a8a, #1e40af);
                    color: #93c5fd;
                }
                [data-theme="dark"] .secure-notify-icon.success {
                    background: linear-gradient(135deg, #064e3b, #065f46);
                    color: #6ee7b7;
                }
                .secure-notify-title {
                    font-weight: 600;
                    font-size: 1.1rem;
                    text-align: center;
                    margin-bottom: 0.5rem;
                    color: var(--text-color, #1f2937);
                }
                .secure-notify-message {
                    text-align: center;
                    color: var(--text-muted, #6b7280);
                    font-size: 0.9rem;
                    line-height: 1.5;
                    margin-bottom: 1.25rem;
                    word-wrap: break-word;
                }
                .secure-notify-btn {
                    display: block;
                    width: 100%;
                    padding: 0.75rem 1rem;
                    border-radius: 8px;
                    font-weight: 500;
                    text-align: center;
                    cursor: pointer;
                    background: var(--primary-color, #4f46e5);
                    color: white;
                    border: none;
                    transition: all 0.2s ease;
                }
                .secure-notify-btn:hover {
                    background: var(--primary-hover, #4338ca);
                    transform: translateY(-1px);
                }
                .secure-notify-btn:focus {
                    outline: none;
                    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.3);
                }
            `;
            document.head.appendChild(style);
        }

        // Create overlay HTML
        const overlayDiv = document.createElement('div');
        overlayDiv.id = 'secureNotifyOverlay';
        overlayDiv.className = 'secure-notify-overlay';
        overlayDiv.innerHTML = `
            <div class="secure-notify-popup">
                <div id="secureNotifyIcon" class="secure-notify-icon error">
                    <i id="secureNotifyIconI" class="bi bi-exclamation-triangle-fill"></i>
                </div>
                <div id="secureNotifyTitle" class="secure-notify-title">Error</div>
                <div id="secureNotifyMessage" class="secure-notify-message"></div>
                <button type="button" id="secureNotifyBtn" class="secure-notify-btn">OK</button>
            </div>
        `;
        document.body.appendChild(overlayDiv);
    }

    /**
     * Show a notification
     * @param {string} message - The message to display
     * @param {string} type - Notification type: 'error', 'warning', 'info', 'success'
     * @param {function} onClose - Optional callback when notification is closed
     */
    function show(message, type = 'error', onClose = null) {
        init();

        const config = NOTIFICATION_TYPES[type] || NOTIFICATION_TYPES.error;
        
        const iconContainer = document.getElementById('secureNotifyIcon');
        const iconI = document.getElementById('secureNotifyIconI');
        const title = document.getElementById('secureNotifyTitle');
        const messageDiv = document.getElementById('secureNotifyMessage');
        const btn = document.getElementById('secureNotifyBtn');

        iconContainer.className = 'secure-notify-icon ' + config.cssClass;
        iconI.className = 'bi ' + config.icon;
        title.textContent = translations[config.titleKey] || config.titleKey;
        messageDiv.textContent = message;
        btn.textContent = translations['OK'] || 'OK';

        overlay.classList.add('show');

        // Remove any existing handlers
        const newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);

        // Handle close
        const closeHandler = function() {
            overlay.classList.remove('show');
            if (onClose) {
                setTimeout(onClose, 300); // Wait for animation
            }
        };

        newBtn.addEventListener('click', closeHandler);

        // Close on overlay click
        const overlayClickHandler = function(e) {
            if (e.target === overlay) {
                closeHandler();
            }
        };
        overlay.onclick = overlayClickHandler;

        // Close on Escape key
        const escHandler = function(e) {
            if (e.key === 'Escape' && overlay.classList.contains('show')) {
                closeHandler();
            }
        };
        document.addEventListener('keydown', escHandler, { once: true });

        // Focus the button for accessibility
        setTimeout(() => newBtn.focus(), 100);
    }

    /**
     * Show an error notification
     */
    function error(message, onClose) {
        show(message, 'error', onClose);
    }

    /**
     * Show a success notification
     */
    function success(message, onClose) {
        show(message, 'success', onClose);
    }

    /**
     * Show a warning notification
     */
    function warning(message, onClose) {
        show(message, 'warning', onClose);
    }

    /**
     * Show an info notification
     */
    function info(message, onClose) {
        show(message, 'info', onClose);
    }

    /**
     * Set translations
     */
    function setTranslations(trans) {
        translations = { ...DEFAULT_TRANSLATIONS, ...trans };
    }

    // Expose API
    window.SecureNotify = {
        show: show,
        error: error,
        success: success,
        warning: warning,
        info: info,
        setTranslations: setTranslations,
        init: init
    };

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
