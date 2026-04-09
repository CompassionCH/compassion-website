{
    "name": "Muskathlon Theme",
    "category": "Theme/Compassion",
    "summary": "Compassion Muskathlon Theme",
    "sequence": 260,
    "version": "18.0.1.0.0",
    "author": "Compassion Switzerland",
    "website": "https://github.com/CompassionCH/compassion-website",
    "depends": ["website_sale"],
    "data": [
        "views/images_content.xml",
        "data/presets.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            "theme_muskathlon/static/src/scss/primary_variables.scss",
        ],
        "web.assets_frontend": [
            "theme_muskathlon/static/src/scss/font.scss",
        ],
        "web._assets_frontend_helpers": [
            ("prepend", "theme_muskathlon/static/src/scss/bootstrap_overidden.scss"),
        ],
    },
    "images": ["static/description/muskathlon_screenshot.jpeg"],
    "license": "LGPL-3",
    "installable": True,
}
