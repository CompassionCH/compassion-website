# iOS Push Notification Setup: Odoo + Firebase + Capacitor

## 1. Apple Developer Platform
* **Enable Capability:** In *Identifiers*, check **Push Notifications** for both Prod (`ch.mycompassion.app`) and Dev (`.dev`) app IDs.
* **Create APNs Key:** Go to *Keys* > **+**. Select **Apple Push Notifications service (APNs)**.
* **Configure:** Set environment to **Production** and restriction to **Team Scoped (All Topics)**.
* **Download:** Save the `.p8` file (you can only download it once). Copy the **Key ID** and your **Team ID**.

## 2. Firebase Console
* **Setup:** Create a Firebase project and add your iOS apps (Prod & Dev).
* **Upload Passport:** Go to **Project Settings** > **Cloud Messaging** > **Apple app configuration**.
* **Configure Keys:** Upload the `.p8` file, Key ID, and Team ID to **BOTH** the Development and Production slots for **ALL** your iOS apps.

## 3. Google Cloud Platform (GCP)
* **Enable API:** Open the GCP console for your Firebase project and enable the **Firebase Cloud Messaging API**.
* **Service Account:** Go to **IAM & Admin > Service Accounts**. Create one with the **Firebase Cloud Messaging API Admin** role.
* **Generate Key:** Create a new **JSON** key for this Service Account and download it.

## 4. Odoo Backend
* **Store Credentials:** Save the GCP JSON key securely (e.g., `ir.config_parameter`).
* **Data Model:** Create `mycompassion.device.token` to link device tokens to `res.users`.
* **Register Endpoint (`/my2/api/register_device`):** Save the incoming FCM token to the DB *and* the browser session (`request.session["mycompassion_device_token"] = token`).
* **Send Push Method:** Build the HTTP request to Google using the JSON credentials. Include a `data` dict for routing (e.g., `{"url": "/my2/dashboard"}`).
* **Logout Override:** Inherit `odoo.addons.web.controllers.main.Session`. Pop the token from `request.session`, delete it from the DB, then call `super().logout()`.
* **Cron Jobs:** Query the DB directly and log successful pushes in Odoo's Chatter (`mail.message`) to prevent duplicate spam.

## 5. Capacitor Frontend
**File Reference:** `my_compassion_native/static/src/js/capacitor_push.js`
* **Plugins:** Install `@capacitor/push-notifications` and `@capacitor-community/fcm`.
* **Registration Flow:** Request permissions -> Read APNs token on success -> Translate via `FCM.getToken()` -> AJAX post the FCM token to Odoo.
* **Foreground Listener:** Use `pushNotificationReceived` to trigger an Odoo UI toast or native Capacitor Dialog when the app is actively open.
* **Background Routing:** Use `pushNotificationActionPerformed` to intercept taps on the lock screen. Extract `data.url` and assign it to `window.location.href` to route the user.
