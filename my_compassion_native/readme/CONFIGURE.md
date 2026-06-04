After installation, set the following system parameters in **Settings → Technical → System Parameters**.

## Universal Links / App Links

| Key | Description | Where to find the value |
|---|---|---|
| `my_compassion_native.ios_app_id` | iOS app ID in the format `<TeamID>.<BundleID>`, used for Apple Universal Links verification | Apple Developer Portal → Identifiers → your App ID. Team ID is shown in the top-right of your account page. |
| `my_compassion_native.android_package_name` | Android app package name, used for App Links verification | `capacitor.config.ts` → `appId` field |
| `my_compassion_native.android_sha256_fingerprint` | SHA-256 certificate fingerprint of the Android signing key (colon-separated). | If using Google Play App Signing: **Play Console → your app → Release → App integrity → App signing key certificate → SHA-256 certificate fingerprint**. Otherwise run `keytool -list -v -keystore <keystore>` and copy the SHA-256 line. |

## Firebase Push Notifications

| Key | Description | Where to find the value |
|---|---|---|
| `my_compassion.fcm_service_account` | Full JSON content of the Firebase service account key, used to authenticate push notification requests via FCM | **Google Cloud Console → IAM & Admin → Service Accounts → your service account → Keys → Add Key → JSON**. Paste the entire JSON as the parameter value. |

## Notes

- All parameters must be set independently on each server (staging and production).
- The Android SHA-256 fingerprint differs between debug, release, and Play App Signing keys — use the fingerprint that matches the installed build.
- The FCM service account must have the **Firebase Cloud Messaging API Admin** role in Google Cloud IAM.
