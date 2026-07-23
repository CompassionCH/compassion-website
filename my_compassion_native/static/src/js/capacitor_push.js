/** @odoo-module **/

import {rpc} from "@web/core/network/rpc";
import {toast} from "@my_compassion/js/toast_service";
import {whenReady} from "@odoo/owl";

function saveTokenToOdoo(deviceToken) {
  rpc("/my2/api/register_device", {
    token: deviceToken,
    device_type: window.Capacitor.getPlatform(),
  }).catch(function (error) {
    console.error("Capacitor Push: RPC call failed", error);
  });
}

async function initPushNotifications() {
  const {PushNotifications} = window.Capacitor.Plugins;
  if (!PushNotifications) {
    return;
  }

  let permStatus = await PushNotifications.checkPermissions();
  if (permStatus.receive === "prompt") {
    permStatus = await PushNotifications.requestPermissions();
  }
  if (permStatus.receive !== "granted") {
    return;
  }

  PushNotifications.addListener("registration", async () => {
    try {
      const {FCM} = window.Capacitor.Plugins;
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
      const {Dialog} = window.Capacitor.Plugins;
      if (Dialog) {
        await Dialog.alert({title: notification.title, message: notification.body});
      }
    } catch {
      toast.info(notification.body, notification.title);
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

whenReady(() => {
  if (!window.Capacitor || window.Capacitor.getPlatform() === "web") {
    return;
  }

  const path = window.location.pathname.toLowerCase();
  if (!path.includes("login") && !path.includes("signup")) {
    document.body.classList.add("capacitor-native-app");
    initPushNotifications();
  }
});

// On the login page in the native app, strip any "session expired" modal the
// WebView surfaces so it cannot trap the user behind a dead dialog.
whenReady(() => {
  if (!window.Capacitor || window.Capacitor.getPlatform() === "web") {
    return;
  }
  if (!window.location.pathname.includes("login")) {
    return;
  }

  const observer = new MutationObserver(function () {
    document.querySelectorAll(".modal").forEach(function (modal) {
      if (modal.textContent.toLowerCase().includes("session expired")) {
        modal.remove();
        document.body.classList.remove("modal-open");
        document.querySelectorAll(".modal-backdrop").forEach((b) => b.remove());
      }
    });
  });

  observer.observe(document.body, {childList: true, subtree: true});
});
