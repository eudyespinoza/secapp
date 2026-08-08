(function (global) {
  "use strict";

  function toError(message, details) {
    var err = new Error(message);
    err.details = details || null;
    return err;
  }

  function randomNonce() {
    if (!global.crypto || !global.crypto.getRandomValues) {
      throw toError("Secure random generation requires a secure browser context");
    }
    var bytes = new Uint8Array(16);
    global.crypto.getRandomValues(bytes);
    return Array.from(bytes).map(function (value) {
      return value.toString(16).padStart(2, "0");
    }).join("");
  }

  function normalizeContainer(container) {
    if (!container) throw toError("container is required");
    if (typeof container === "string") {
      var element = document.querySelector(container);
      if (!element) throw toError("container selector not found: " + container);
      return element;
    }
    if (container instanceof HTMLElement) return container;
    throw toError("container must be a selector or HTMLElement");
  }

  function normalizeOrigin(value, label) {
    var parsed;
    try {
      parsed = new URL(String(value || ""), global.location.href);
    } catch (error) {
      throw toError(label + " must be a valid URL");
    }
    if (parsed.protocol !== "https:" && parsed.hostname !== "localhost" && parsed.hostname !== "127.0.0.1") {
      throw toError(label + " must use HTTPS outside local development");
    }
    return parsed.origin;
  }

  async function resolveSession(config, parentOrigin) {
    var session = config.session;
    if (!session && typeof config.fetchSession === "function") {
      session = await config.fetchSession();
    }
    if (!session || !session.approvalToken || !session.webauthnOptions || !session.transaction) {
      throw toError("Session must include approvalToken, webauthnOptions, and transaction");
    }
    if (!session.transaction.id || session.transaction.parentOrigin !== parentOrigin) {
      throw toError("Session transaction is not bound to this parent origin");
    }
    if (session.transaction.decision !== "approve" && session.transaction.decision !== "reject") {
      throw toError("Session transaction has an invalid decision");
    }
    return session;
  }

  function createIframe(config, container, nonce, parentOrigin, iframeUrl) {
    iframeUrl.searchParams.set("parent_origin", parentOrigin);
    iframeUrl.searchParams.set("nonce", nonce);

    var iframe = document.createElement("iframe");
    iframe.src = iframeUrl.toString();
    iframe.title = config.title || "SecureApprove WebAuthn approval";
    iframe.loading = "eager";
    iframe.referrerPolicy = "no-referrer";
    iframe.allow = "publickey-credentials-get *";
    iframe.style.width = "100%";
    iframe.style.height = (config.height || 460) + "px";
    iframe.style.border = "0";
    iframe.style.borderRadius = "12px";

    if (config.sandbox !== false) {
      iframe.sandbox = "allow-scripts allow-same-origin";
    }

    container.innerHTML = "";
    container.appendChild(iframe);
    return iframe;
  }

  function init(config) {
    if (!config) throw toError("config is required");

    var container = normalizeContainer(config.container);
    var actualParentOrigin = normalizeOrigin(global.location.origin, "window origin");
    var parentOrigin = normalizeOrigin(config.parentOrigin || actualParentOrigin, "parentOrigin");
    if (parentOrigin !== actualParentOrigin) {
      throw toError("parentOrigin must match the page's actual origin");
    }

    var rawIframeUrl = config.iframeUrl;
    if (!rawIframeUrl) throw toError("iframeUrl is required");
    var iframeUrl = new URL(String(rawIframeUrl), global.location.href);
    var iframeOrigin = normalizeOrigin(iframeUrl.origin, "iframeUrl");
    var nonce = config.nonce || randomNonce();
    var iframe = createIframe(config, container, nonce, parentOrigin, iframeUrl);

    var disposed = false;
    var ready = false;
    var initializing = false;
    var activeTransactionId = null;

    function cleanup() {
      if (disposed) return;
      disposed = true;
      global.removeEventListener("message", onMessage);
    }

    function postInit(session) {
      if (!iframe.contentWindow) throw toError("iframe contentWindow not available");
      activeTransactionId = session.transaction.id;
      iframe.contentWindow.postMessage({
        source: "secureapprove-loader",
        type: "SECUREAPPROVE_INIT",
        nonce: nonce,
        payload: {
          approvalToken: session.approvalToken,
          webauthnOptions: session.webauthnOptions,
          transaction: session.transaction,
        },
      }, iframeOrigin);
    }

    async function handleReady() {
      if (initializing) return;
      initializing = true;
      try {
        postInit(await resolveSession(config, parentOrigin));
      } catch (error) {
        if (typeof config.onError === "function") config.onError(error);
      } finally {
        initializing = false;
      }
    }

    async function onMessage(event) {
      if (disposed || event.origin !== iframeOrigin || event.source !== iframe.contentWindow) return;
      if (!event.data || event.data.source !== "secureapprove-iframe") return;
      if (event.data.nonce !== nonce) return;

      var messageType = event.data.type;
      var payload = event.data.payload || {};
      if (messageType === "SECUREAPPROVE_READY") {
        ready = true;
        if (typeof config.onReady === "function") config.onReady(payload);
        await handleReady();
      } else if (messageType === "SECUREAPPROVE_READY_ACK") {
        if (typeof config.onReadyAck === "function") config.onReadyAck(payload);
      } else if (messageType === "SECUREAPPROVE_RESULT") {
        if (!activeTransactionId || payload.transactionId !== activeTransactionId) {
          if (typeof config.onError === "function") {
            config.onError(toError("SecureApprove result transaction mismatch", payload));
          }
        } else if (typeof config.onSuccess === "function") {
          config.onSuccess(payload);
        }
      } else if (messageType === "SECUREAPPROVE_CANCEL") {
        if (typeof config.onCancel === "function") config.onCancel(payload);
      } else if (messageType === "SECUREAPPROVE_ERROR" && typeof config.onError === "function") {
        config.onError(toError(payload.message || payload.error || "secureapprove_iframe_error", payload));
      }
    }

    global.addEventListener("message", onMessage);
    return {
      iframe: iframe,
      iframeOrigin: iframeOrigin,
      nonce: nonce,
      parentOrigin: parentOrigin,
      isReady: function () { return ready; },
      refreshSession: async function () {
        if (!ready) throw toError("iframe is not ready yet");
        postInit(await resolveSession(config, parentOrigin));
      },
      destroy: function () {
        cleanup();
        if (iframe && iframe.parentNode) iframe.parentNode.removeChild(iframe);
      },
    };
  }

  global.SecureApproveEmbed = { init: init };
})(window);
