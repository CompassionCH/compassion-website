/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import {rpc} from "@web/core/network/rpc";

// The donor pays in a browser this page cannot see into, and its own timers are
// suspended while that browser is on top - so it can only read the outcome from
// the server, once the donor is back (T3378).
// Each poll of an unfinished payment costs one gateway call.
const GIVE_UP_MS = 300000;
const POLL_MS = 3000;
const MAX_AGE_S = 600;
const HANDLED_KEY = "my2_payment_handled";

let pollTimer = null;
let startedAt = null;

// Only the app can close the browser it opened.
function closeNativePaymentSheet() {
  const handlers = window.webkit && window.webkit.messageHandlers;
  if (handlers && handlers.nativePayment) {
    handlers.nativePayment.postMessage("close");
  }
}

function isNativeApp() {
  return window.Capacitor && window.Capacitor.getPlatform() !== "web";
}

function banner(message, tone) {
  let el = document.getElementById("my2_payment_banner");
  if (!el) {
    el = document.createElement("div");
    el.id = "my2_payment_banner";
    el.setAttribute("role", "status");
    document.body.appendChild(el);
  }
  el.className = "my2-payment-banner my2-payment-banner-" + tone;
  el.textContent = message;
}

function clearBanner() {
  const el = document.getElementById("my2_payment_banner");
  if (el) {
    el.remove();
  }
}

function stop() {
  if (pollTimer) {
    window.clearTimeout(pollTimer);
    pollTimer = null;
  }
  startedAt = null;
}

function handle(status) {
  if (!status || !status.state || status.seconds_ago > MAX_AGE_S) {
    clearBanner();
    stop();
    return false;
  }
  if (window.sessionStorage.getItem(HANDLED_KEY) === status.reference) {
    stop();
    return false;
  }

  if (status.processing) {
    // Settling, not failed: never offer to pay again from here.
    banner(_t("Thank you! We're confirming your gift…"), "pending");
    if (Date.now() - startedAt > GIVE_UP_MS) {
      banner(
        _t(
          "Your gift has arrived. We're confirming it shortly – you can safely close this page."
        ),
        "pending"
      );
      stop();
      return false;
    }
    return true;
  }

  stop();
  window.sessionStorage.setItem(HANDLED_KEY, status.reference);
  if (status.state === "done") {
    // Success only: a failure must stay on screen to be read.
    closeNativePaymentSheet();
    clearBanner();
    if (window.location.pathname.indexOf("/my2/gifts/thankyou") === -1) {
      window.location = "/my2/gifts/thankyou";
    }
  } else {
    banner(
      _t(
        "The payment didn't go through. Nothing was charged – feel free to try again."
      ),
      "failed"
    );
  }
  return false;
}

function poll() {
  function again() {
    if (startedAt && Date.now() - startedAt < GIVE_UP_MS) {
      pollTimer = window.setTimeout(poll, POLL_MS);
    } else {
      stop();
    }
  }
  rpc("/my2/payment/status")
    .then((status) => {
      if (handle(status)) {
        again();
      }
    })
    .catch(again);
}

function start() {
  // The app and visibilitychange both resume; startedAt catches the second
  // call, which lands before the first poll has scheduled a timer.
  if (pollTimer || startedAt) {
    return;
  }
  startedAt = Date.now();
  poll();
}

function init() {
  if (!isNativeApp()) {
    return;
  }
  // Called by the app once the payment browser is gone.
  window.my2ResumePaymentPolling = start;
  start();
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      start();
    }
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
