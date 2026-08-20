odoo.define("my_compassion_native.payment_resume", function (require) {
    "use strict";

    const core = require("web.core");
    const _t = core._t;

    // The gateway is paid for outside this webview: iOS hands the PostFinance
    // URL to an SFSafariViewController and reloads us when the sheet closes,
    // Android can come back with the webview parked on the gateway. Either way
    // the donor lands on a page whose cart the payment lock has emptied, with no
    // confirmation anywhere - which is what made testers pay a second time
    // (T3378). Ask the server, which queries PostFinance directly, instead of
    // waiting for the sweep cron.

    // On iOS the payment sheet sits on top of this page while the donor pays, so
    // polling has to outlast the payment itself. Back off instead of hammering:
    // every poll that finds the payment unfinished costs one gateway call.
    const GIVE_UP_MS = 300000;
    const BACKOFF = [
        [20000, 2000],
        [90000, 5000],
        [GIVE_UP_MS, 20000],
    ];
    // Ignore anything older than a payment made during this visit.
    const MAX_AGE_S = 600;
    const HANDLED_KEY = "my2_payment_handled";

    let pollTimer = null;
    let startedAt = null;

    function nextDelay() {
        const elapsed = Date.now() - startedAt;
        const step = BACKOFF.find((entry) => elapsed < entry[0]);
        return step ? step[1] : null;
    }

    // SFSafariViewController can only be closed by the app that opened it, and it
    // cannot see where it navigated - so unless we say so, the donor has to close
    // the payment sheet by hand after paying.
    function closeNativePaymentSheet() {
        const handlers = window.webkit && window.webkit.messageHandlers;
        if (handlers && handlers.nativePayment) {
            handlers.nativePayment.postMessage("close");
        }
    }

    function isNativeApp() {
        return window.Capacitor && window.Capacitor.getPlatform() !== "web";
    }

    function alreadyHandled(reference) {
        return window.sessionStorage.getItem(HANDLED_KEY) === reference;
    }

    function markHandled(reference) {
        window.sessionStorage.setItem(HANDLED_KEY, reference);
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

    function fetchStatus() {
        return fetch("/my2/payment/status", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: {} }),
        })
            .then((response) => response.json())
            .then((payload) => (payload && payload.result) || null);
    }

    function handle(status) {
        if (!status || !status.state || status.seconds_ago > MAX_AGE_S) {
            clearBanner();
            stop();
            return false;
        }
        if (alreadyHandled(status.reference)) {
            stop();
            return false;
        }

        if (status.processing) {
            // CONFIRMED means the gateway has the money and is settling; it is a
            // success in progress, so never offer to pay again from here.
            banner(_t("Thank you! We're confirming your gift…"), "pending");
            if (Date.now() - startedAt > GIVE_UP_MS) {
                banner(
                    _t("Your gift has arrived. We're confirming it shortly – you can safely close this page."),
                    "pending"
                );
                stop();
                return false;
            }
            return true;
        }

        stop();
        markHandled(status.reference);
        closeNativePaymentSheet();
        if (status.state === "done") {
            clearBanner();
            if (window.location.pathname.indexOf("/my2/gifts/thankyou") === -1) {
                window.location = "/my2/gifts/thankyou";
            }
        } else {
            banner(_t("The payment didn't go through. Nothing was charged – feel free to try again."), "failed");
        }
        return false;
    }

    function poll() {
        function again() {
            const delay = startedAt && nextDelay();
            if (delay) {
                pollTimer = window.setTimeout(poll, delay);
            } else {
                stop();
            }
        }
        fetchStatus()
            .then((status) => {
                if (handle(status)) {
                    again();
                }
            })
            // Offline or server hiccup: keep the banner, try again.
            .catch(again);
    }

    function start() {
        if (pollTimer) {
            return;
        }
        startedAt = Date.now();
        poll();
    }

    $(function () {
        if (!isNativeApp()) {
            return;
        }
        start();
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "visible") {
                start();
            }
        });
    });
});
