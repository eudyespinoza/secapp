const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function loadWidget() {
  class FakeHTMLElement {}
  const container = new FakeHTMLElement();
  container.children = [];
  container.appendChild = function appendChild(child) {
    this.children.push(child);
    child.parentNode = this;
  };
  container.removeChild = function removeChild(child) {
    this.children = this.children.filter((item) => item !== child);
  };

  const sentMessages = [];
  const listeners = new Map();
  const iframeWindow = {
    postMessage(message, targetOrigin) {
      sentMessages.push({ message, targetOrigin });
    },
  };

  const document = {
    querySelector(selector) {
      return selector === "#widget" ? container : null;
    },
    createElement(tag) {
      assert.equal(tag, "iframe");
      return {
        contentWindow: iframeWindow,
        style: {},
        parentNode: null,
      };
    },
  };

  const window = {
    crypto: {
      getRandomValues(array) {
        array.fill(7);
        return array;
      },
    },
    location: {
      origin: "https://client.example",
      href: "https://client.example/checkout",
    },
    addEventListener(type, callback) {
      listeners.set(type, callback);
    },
    removeEventListener(type) {
      listeners.delete(type);
    },
  };

  const context = vm.createContext({
    Array,
    Error,
    HTMLElement: FakeHTMLElement,
    Promise,
    String,
    URL,
    Uint8Array,
    document,
    window,
  });
  const loaderPath = path.resolve(
    __dirname,
    "../../static/js/secureapprove-embed-loader.js",
  );
  vm.runInContext(fs.readFileSync(loaderPath, "utf8"), context, {
    filename: loaderPath,
  });

  return {
    container,
    iframeWindow,
    listeners,
    sentMessages,
    widget: window.SecureApproveEmbed,
  };
}

test("cross-origin READY sends INIT only to the SecureApprove iframe origin", async () => {
  const harness = loadWidget();
  let readyCalls = 0;
  const controller = harness.widget.init({
    container: "#widget",
    iframeUrl: "https://secureapprove.com/en/embed/secureapprove/",
    fetchSession: async () => ({
      approvalToken: "token",
      webauthnOptions: { challenge: "challenge" },
      transaction: {
        id: "6acdf944-25f6-44f2-8f82-fbbd2a6305c2",
        parentOrigin: "https://client.example",
        decision: "approve",
      },
    }),
    onReady() {
      readyCalls += 1;
    },
  });

  const iframe = harness.container.children[0];
  assert.match(iframe.sandbox, /allow-same-origin/);
  assert.match(iframe.allow, /publickey-credentials-get/);

  await harness.listeners.get("message")({
    origin: "https://secureapprove.com",
    source: harness.iframeWindow,
    data: {
      source: "secureapprove-iframe",
      type: "SECUREAPPROVE_READY",
      nonce: controller.nonce,
      payload: {},
    },
  });
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(readyCalls, 1);
  assert.equal(harness.sentMessages.length, 1);
  assert.equal(harness.sentMessages[0].targetOrigin, "https://secureapprove.com");
  assert.equal(harness.sentMessages[0].message.type, "SECUREAPPROVE_INIT");
});

test("messages from another window are ignored even with the expected origin", async () => {
  const harness = loadWidget();
  let successCalls = 0;
  const controller = harness.widget.init({
    container: "#widget",
    iframeUrl: "https://secureapprove.com/en/embed/secureapprove/",
    session: {
      approvalToken: "token",
      webauthnOptions: { challenge: "challenge" },
      transaction: {
        id: "6acdf944-25f6-44f2-8f82-fbbd2a6305c2",
        parentOrigin: "https://client.example",
        decision: "approve",
      },
    },
    onSuccess() {
      successCalls += 1;
    },
  });

  await harness.listeners.get("message")({
    origin: "https://secureapprove.com",
    source: {},
    data: {
      source: "secureapprove-iframe",
      type: "SECUREAPPROVE_RESULT",
      nonce: controller.nonce,
      payload: { transactionId: "6acdf944-25f6-44f2-8f82-fbbd2a6305c2" },
    },
  });

  assert.equal(successCalls, 0);
});

test("a result for another transaction is rejected after the secure handshake", async () => {
  const harness = loadWidget();
  let successCalls = 0;
  let errorCalls = 0;
  const controller = harness.widget.init({
    container: "#widget",
    iframeUrl: "https://secureapprove.com/en/embed/secureapprove/",
    session: {
      approvalToken: "token",
      webauthnOptions: { challenge: "challenge" },
      transaction: {
        id: "6acdf944-25f6-44f2-8f82-fbbd2a6305c2",
        parentOrigin: "https://client.example",
        decision: "approve",
      },
    },
    onSuccess() {
      successCalls += 1;
    },
    onError() {
      errorCalls += 1;
    },
  });

  await harness.listeners.get("message")({
    origin: "https://secureapprove.com",
    source: harness.iframeWindow,
    data: {
      source: "secureapprove-iframe",
      type: "SECUREAPPROVE_READY",
      nonce: controller.nonce,
      payload: {},
    },
  });
  await new Promise((resolve) => setImmediate(resolve));

  await harness.listeners.get("message")({
    origin: "https://secureapprove.com",
    source: harness.iframeWindow,
    data: {
      source: "secureapprove-iframe",
      type: "SECUREAPPROVE_RESULT",
      nonce: controller.nonce,
      payload: { transactionId: "00000000-0000-4000-8000-000000000099" },
    },
  });

  assert.equal(successCalls, 0);
  assert.equal(errorCalls, 1);
});
