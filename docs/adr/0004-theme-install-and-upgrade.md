# Preserve per-website theme assets by repairing the shared theme category

Each website must load its selected theme's palette on both a fresh install and an
upgrade. On upgraded databases, a duplicate category can prevent Odoo from recognizing
installed themes. Their palettes then enter the bundles of sites using other themes.

The theme migration reparents the affected shared category under
`base.module_category_theme`. This gives one theme responsibility for metadata used by
several themes, but repairs asset selection for every affected site in one place. Check
per-site palette isolation on both installation paths when changing this behavior.
[Theme category migration](../../theme_compassion_2025/migrations/18.0.1.0.2/post-migration.py)
