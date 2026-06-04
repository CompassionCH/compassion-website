# iOS Push Notification Setup

## 1. Apple Developer Platform
- In *Identifiers*, enable **Push Notifications** for your app ID(s).
- Go to *Keys* → **+**, select **Apple Push Notifications service (APNs)**.
- Download the `.p8` file (only available once). Note the **Key ID** and **Team ID**.

## 2. Firebase Console
- Create a Firebase project and add your iOS app(s).
- Go to **Project Settings → Cloud Messaging → Apple app configuration**.
- Upload the `.p8` file, Key ID, and Team ID for each app.

## 3. Google Cloud Platform
- In the GCP console for your Firebase project, enable the **Firebase Cloud Messaging API**.
- Go to **IAM & Admin → Service Accounts**, create a service account with the **Firebase Cloud Messaging API Admin** role.
- Generate a **JSON** key and download it.

## 4. Odoo Backend
- Store the GCP JSON key in the system parameter `my_compassion.fcm_service_account`.
  See `readme/CONFIGURE.md` for details.