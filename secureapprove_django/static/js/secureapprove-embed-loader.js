(function (global) {
  "use strict";

  function randomNonce() {
    var arr = new Uint8Array(16);
    if (global.crypto && global.crypto.getRandomValues) {
      global.crypto.getRandomValues(arr);
      return Array.from(arr).map(function (v) {
        return v.toString(16).padStart(2, "0");
      }).join("");
    }
    return String(Date.now()) + String(Math.random()).slice(2);
  }

  function toError(message, details) {
    var err = new Error(message);
    err.details = details || null;
    return err;
  }

  function normalizeContainer(container) {
    if (!container) {
      throw toError("container is required");
    }

    if (typeof container === "string") {
      var el = document.querySelector(container);
      if (!el) {
        throw toError("container selector not found: " + container);
      }
      return el;
    }

    if (container instanceof HTMLElement) {
      return container;
    }

    throw toError("container must be a selector or HTMLElement");
  }

  function ensureParentOrigin(parentOrigin) {
    if (!parentOrigin) {
      return window.location.origin;
    }
    return String(parentOrigin).replace(/\/+$/, "");
  }

  async function resolveSession(config) {
    if (config.session && config.session.approvalToken && config.session.webauthnOptions) {
      return config.session;
    }

    if (typeof config.fetchSession === "function") {
      var session = await config.fetchSession();
      if (!session || !session.approvalToken || !session.webauthnOptions) {
        throw toError("fetchSession must return approvalToken and webauthnOptions");
      }
      return session;
    }

    throw toError("Provide either session or fetchSession for secure init");
  }

  function createIframe(config, container, nonce, parentOrigin) {
    var iframeUrl = String(config.iframeUrl || "").replace(/\/+$/, "");
    if (!iframeUrl) {
      throw toError("iframeUrl is required");
    }

    var src = iframeUrl + "?parent_origin=" + encodeURIComponent(parentOrigin) + "&nonce=" + encodeURIComponent(nonce);

    var iframe = document.createElement("iframe");
    iframe.src = src;
    iframe.title = config.title || "SecureApprove Embedded Approval";
    iframe.loading = "lazy";
    iframe.referrerPolicy = "strict-origin";
    iframe.allow = "publickey-credentials-get";
    iframe.style.width = "100%";
    iframe.style.height = (config.height || 420) + "px";
    iframe.style.border = "0";
    iframe.style.borderRadius = "12px";

    if (config.sandbox !== false) {
      iframe.sandbox = "allow-scripts allow-forms";
    }

    container.innerHTML = "";
    container.appendChild(iframe);

    return iframe;
  }

  function init(config) {
    if (!config) {
      throw toError("config is required");
    }

    var container = normalizeContainer(config.container);
    var nonce = config.nonce || randomNonce();
    var parentOrigin = ensureParentOrigin(config.parentOrigin);
    var iframe = createIframe(config, container, nonce, parentOrigin);

    var disposed = false;
    var ready = false;

    function cleanup() {
      if (disposed) return;
      disposed = true;
      window.removeEventListener("message", onMessage);
    }

    function postInit(session) {
      if (!iframe.contentWindow) {
        throw toError("iframe contentWindow not available");
      }

      iframe.contentWindow.postMessage({
        source: "secureapprove-loader",
        type: "SECUREAPPROVE_INIT",
        nonce: nonce,
        payload: {
          approvalToken: session.approvalToken,
          webauthnOptions: session.webauthnOptions,
          approved: session.approved !== false,
          context: session.context || {},
        },
      }, parentOrigin);
    }

    async function handleReady() {
      try {
        var session = await resolveSession(config);
        postInit(session);
      } catch (error) {
        if (typeof config.onError === "function") {
          config.onError(error);
        }
      }
    }

    async function onMessage(event) {
      if (disposed) return;
      if (event.origin !== parentOrigin) return;
      if (!event.data || event.data.source !== "secureapprove-iframe") return;
      if (event.data.nonce !== nonce) return;

      var msgType = event.data.type;
      var payload = event.data.payload || {};

      if (msgType === "SECUREAPPROVE_READY") {
        ready = true;
        if (typeof config.onReady === "function") {
          config.onReady(payload);
        }
        await handleReady();
        return;
      }

      if (msgType === "SECUREAPPROVE_READY_ACK") {
        if (typeof config.onReadyAck === "function") {
          config.onReadyAck(payload);
        }
        return;
      }

      if (msgType === "SECUREAPPROVE_RESULT") {
        if (typeof config.onSuccess === "function") {
          config.onSuccess(payload);
        }
        return;
      }

      if (msgType === "SECUREAPPROVE_CANCEL") {
        if (typeof config.onCancel === "function") {
          config.onCancel(payload);
        }
        return;
      }

      if (msgType === "SECUREAPPROVE_ERROR") {
        if (typeof config.onError === "function") {
          config.onError(toError(payload.message || payload.error || "secureapprove_iframe_error", payload));
        }
      }
    }

    window.addEventListener("message", onMessage);

    return {
      iframe: iframe,
      nonce: nonce,
      parentOrigin: parentOrigin,
      isReady: function () { return ready; },
      refreshSession: async function () {
        if (!ready) {
          throw toError("iframe is not ready yet");
        }
        var session = await resolveSession(config);
        postInit(session);
      },
      destroy: function () {
        cleanup();
        if (iframe && iframe.parentNode) {
          iframe.parentNode.removeChild(iframe);
        }
      },
    };
  }

  global.SecureApproveEmbed = {
    init: init,
  };
})(window);
