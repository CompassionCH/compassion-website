# Android Push Notification Setup

## 1. Firebase Console
- Create a Firebase project (or reuse the one from iOS) and add your Android app.
- Use the package name from `my_compassion_native.android_package_name` (e.g. `ch.mycompassion.app`).
- Download the `google-services.json` file and place it in `android/app/` in the Capacitor project.

## 2. Google Cloud Platform
- In the GCP console for your Firebase project, enable the **Firebase Cloud Messaging API**.
- Go to **IAM & Admin → Service Accounts**, create a service account with the **Firebase Cloud Messaging API Admin** role.
- Generate a **JSON** key and download it.

## 3. Odoo Backend
- Store the GCP JSON key in the system parameter `my_compassion.fcm_service_account`.
  See `readme/CONFIGURE.md` for details.

## 4. App Links
- Set the system parameters `my_compassion_native.android_package_name` and
  `my_compassion_native.android_sha256_fingerprint` so that `/.well-known/assetlinks.json`
  is served correctly. Android verifies these automatically on app install.
  If the fingerprint changes (e.g. after a keystore rotation), devices may need to
  reinstall the app to re-trigger verification.
