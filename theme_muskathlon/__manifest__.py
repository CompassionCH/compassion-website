{
    "name": "Muskathlon Theme",
    "category": "Theme/Compassion",
    "summary": "Compassion Muskathlon Theme",
    "sequence": 260,
    "version": "18.0.1.0.1",
    "author": "Compassion Switzerland",
    "website": "https://github.com/CompassionCH/compassion-website",
    "depends": ["website_sale"],
    "data": [
        "views/images_content.xml",
        "views/template_header.xml",
        "views/layout.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            "theme_muskathlon/static/src/scss/primary_variables.scss",
        ],
        "web.assets_frontend": [
            "theme_muskathlon/static/src/scss/font.scss",
            "theme_muskathlon/static/src/scss/website.scss",
        ],
    },
    "images": ["static/description/muskathlon_screenshot.jpeg"],
    "license": "LGPL-3",
    "installable": True,
}
