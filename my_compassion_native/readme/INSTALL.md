Install the Python dependency:

```bash
pip install firebase-admin
```

The Capacitor native app must be built separately from the `my_compassion_app` repository.
Sync the Odoo web bundle to the native project before building:

```bash
npm run sync:prod        # iOS
npm run sync:prod-android  # Android
```

After installation, configure the required system parameters described in CONFIGURE.md.
