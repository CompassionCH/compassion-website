odoo.define("my_compassion_native.capacitor_push", function (require) {
    "use strict";

    const ajax = require("web.ajax");
    const core = require("web.core");
    const session = require("web.session");

    function saveTokenToOdoo(deviceToken) {
        ajax.jsonRpc("/my2/api/register_device", "call", {
            token: deviceToken,
            device_type: window.Capacitor.getPlatform(),
        }).catch(function (error) {
            console.error("Capacitor Push: RPC call failed", error);
        });
    }

    async function initPushNotifications() {
        const { PushNotifications } = window.Capacitor.Plugins;
        if (!PushNotifications) return;

        let permStatus = await PushNotifications.checkPermissions();
        if (permStatus.receive === "prompt") {
            permStatus = await PushNotifications.requestPermissions();
        }
        if (permStatus.receive !== "granted") return;

        PushNotifications.addListener("registration", async () => {
            try {
                const { FCM } = window.Capacitor.Plugins;
                const fcmToken = await FCM.getToken();
                saveTokenToOdoo(fcmToken.token);
            } catch (error) {
                console.error("Capacitor Push: Failed to get FCM token", error);
            }
        });

        PushNotifications.addListener("registrationError", (error) => {
            console.error("Capacitor Push: Registration error", error);
        });

        PushNotifications.addListener("pushNotificationReceived", async (notification) => {
            try {
                const { Dialog } = window.Capacitor.Plugins;
                if (Dialog) {
                    await Dialog.alert({ title: notification.title, message: notification.body });
                }
            } catch (e) {
                if (core && core.bus) {
                    core.bus.trigger("notification", {
                        title: notification.title,
                        message: notification.body,
                        sticky: true,
                    });
                }
            }
        });

        PushNotifications.addListener("pushNotificationActionPerformed", (action) => {
            const data = action.notification.data;
            if (data && data.url) {
                window.location.href = data.url;
            }
        });

        await PushNotifications.register();
    }

    $(function () {
        if (!window.Capacitor || window.Capacitor.getPlatform() === "web") return;

        const path = window.location.pathname.toLowerCase();
        if (!path.includes("login") && !path.includes("signup")) {
            $("body").addClass("capacitor-native-app");
            // Logged out, register_device (auth="user") raises the
            // "session expired" modal that reloads the page (T3481).
            if (session.user_id) {
                initPushNotifications();
            }
        }
    });
});
