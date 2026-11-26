# Generate editable theme styles before the first page needs them

The theme renders editable colors, icons and pictograms into shared `ir.attachment`
records with stable SCSS URLs. Declare each URL with `<asset>` in theme XML. Odoo stores
it as a `theme.ir.asset` template. Applying the theme creates or updates an `ir.asset`
copy for that website. The three styles join `web.assets_frontend`. The palette joins
`web._assets_primary_variables` and regenerates only when every required color slot is
present. Its static baseline lives in the manifest.
[Stylesheet attachments](../../theme_compassion_2025/data/dynamic_stylesheets.xml) ·
[Bundle declarations](../../theme_compassion_2025/data/assets.xml) ·
[Palette generator](../../theme_compassion_2025/models/colors.py)

Generate synchronously on install and on upgrades that need to rebuild stored styles. A
queued job could leave the first page unstyled. The current install hook calls the
generators directly. Creating, editing or deleting a source record regenerates its
styles, and writing the attachment clears the `assets` cache for the next bundle build.
[Install hook](../../theme_compassion_2025/hooks.py) ·
[Stylesheet generator](../../theme_compassion_2025/models/stylesheet_generator_mixin.py)

For a URL rename, change both XML files for fresh installs. Both use `noupdate`, so a
versioned migration must also update the stored attachment's `url`, the existing
template's `path` and any linked website copies still using the old path. The earlier
migration renamed only attachment URLs because the bundle declarations were new in that
version.
[Earlier URL migration](../../theme_compassion_2025/migrations/18.0.1.0.0/post-migration.py)
