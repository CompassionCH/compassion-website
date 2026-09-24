/** @odoo-module **/

import {rpc} from "@web/core/network/rpc";
import {session} from "@web/session";
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
    // Logged out, register_device (auth="user") raises the
    // "session expired" modal that reloads the page (T3481).
    if (!session.is_public) {
      initPushNotifications();
    }
  }
});
