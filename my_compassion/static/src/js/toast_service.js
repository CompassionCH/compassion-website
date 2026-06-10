/** @odoo-module **/

/**
 * Toast notification service.
 *
 * Renders the `my_compassion.toast_notification_component` client template
 * (shipped in the `web.assets_frontend` bundle, styled by
 * `toast_notification.css`) and appends it to the page body. Each toast
 * dismisses itself automatically after six seconds.
 *
 * Usage:
 *     import { toast } from "@my_compassion/js/toast_service";
 *     toast.success("Saved!");          // default title "Success"
 *     toast.error("It failed", "Oops"); // custom title
 *
 * Methods: `info`, `success`, `warning`, `error`, each taking the message
 * body and an optional title. The `error` method maps to the "danger"
 * visual type.
 */

import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

// The average reading time for a toast is around 5 seconds + 1 second
// per 120 characters, so remove the toast after 6 seconds.
const DISMISS_DELAY_MS = 6000;

/**
 * Render a toast notification and append it to the page body.
 *
 * @param {String} type - the visual style: "info", "success", "warning" or "danger"
 * @param {String} title - the toast header
 * @param {String} message - the toast body
 */
function show(type, title, message) {
    const el = renderToElement("my_compassion.toast_notification_component", {
        type,
        title,
        message,
    });
    document.body.appendChild(el);
    setTimeout(() => el.remove(), DISMISS_DELAY_MS);
}

/**
 * Toast notification service exposing one convenience method per style.
 * Each method takes the message body and an optional title.
 */
export const toast = {
    info: (msg, title = _t("Info")) => show("info", title, msg),
    success: (msg, title = _t("Success")) => show("success", title, msg),
    warning: (msg, title = _t("Warning")) => show("warning", title, msg),
    error: (msg, title = _t("Error")) => show("danger", title, msg),
};
