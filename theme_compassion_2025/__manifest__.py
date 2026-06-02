##############################################################################
#
#       ______ Releasing children from poverty      _
#      / ____/___  ____ ___  ____  ____ ___________(_)___  ____
#     / /   / __ \/ __ `__ \/ __ \/ __ `/ ___/ ___/ / __ \/ __ \
#    / /___/ /_/ / / / / / / /_/ / /_/ (__  |__  ) / /_/ / / / /
#    \____/\____/_/ /_/ /_/ .___/\__,_/____/____/_/\____/_/ /_/
#                        /_/
#                            in Jesus' name
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    @author: Daniel Palumbo
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": "Compassion Theme 2025",
    "category": "Theme/Compassion",
    "summary": "Compassion Theme 2025",
    "website": "https://github.com/CompassionCH/compassion-website",
    "sequence": 260,
    "version": "18.0.1.0.0",
    "author": "Compassion Switzerland",
    "depends": ["website"],
    "external_dependencies": {"python": ["python-slugify"]},
    "data": [
        "security/ir.model.access.csv",
        # Data
        "data/colors.xml",
        "data/icons.xml",
        "data/pictograms.xml",
        "data/dynamic_stylesheets.xml",
        "data/assets.xml",
        # Views
        "views/theme_compassion_views.xml",
        "views/images_content.xml",
        "views/template_header.xml",
        "views/footer.xml",
        # Component templates (server-side QWeb)
        "templates/components/Portrait.xml",
        "templates/components/Title.xml",
        "templates/components/Vignette.xml",
        "templates/components/Select.xml",
        "templates/components/FormField.xml",
        "templates/components/Banner.xml",
        "templates/components/RangeInputLoading.xml",
        "templates/components/EventBanner.xml",
        "templates/components/Map.xml",
        "templates/components/buttons/ThemedButton.xml",
        "templates/components/buttons/ToggleButton.xml",
        "templates/components/LanguageSelector.xml",
        # Styles (QWeb CSS templates for the dynamic stylesheet pipeline)
        "templates/styles/colors_stylesheet.xml",
        "templates/styles/icons_stylesheet.xml",
        "templates/styles/pictograms_stylesheet.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            "theme_compassion_2025/static/src/scss/primary_variables.scss",
        ],
        "web.assets_frontend": [
            "theme_compassion_2025/static/src/scss/bootstrap_overridden.scss",
            "theme_compassion_2025/static/src/scss/abstracts/_variables.scss",
            "theme_compassion_2025/static/src/scss/abstracts/_functions.scss",
            "theme_compassion_2025/static/src/scss/base/_borders.scss",
            "theme_compassion_2025/static/src/scss/base/_font-face.scss",
            "theme_compassion_2025/static/src/scss/base/_typography.scss",
            "theme_compassion_2025/static/src/scss/base/_base.scss",
            "theme_compassion_2025/static/src/scss/layout/_layout.scss",
            "theme_compassion_2025/static/src/scss/layout/_grid.scss",
            "theme_compassion_2025/static/src/scss/layout/_header.scss",
            "theme_compassion_2025/static/src/scss/components/_portrait.scss",
            "theme_compassion_2025/static/src/scss/components/_buttons.scss",
            "theme_compassion_2025/static/src/scss/components/_event_banner.scss",
            "theme_compassion_2025/static/src/scss/components/_thread.scss",
            "theme_compassion_2025/static/src/scss/components/_title.scss",
            "theme_compassion_2025/static/src/scss/components/_select.scss",
            "theme_compassion_2025/static/src/scss/components/_vignette.scss",
            "theme_compassion_2025/static/src/scss/components/_password.scss",
            "theme_compassion_2025/static/src/scss/components/_progress_bar.scss",
            "theme_compassion_2025/static/src/scss/components/_range_input.scss",
            "theme_compassion_2025/static/src/scss/components/_form_field.scss",
            "theme_compassion_2025/static/src/scss/components/_toggle_button.scss",
            "theme_compassion_2025/static/src/scss/components/_map.scss",
            "theme_compassion_2025/static/src/scss/components/_language_selector.scss",
            "theme_compassion_2025/static/src/css/custom_style.css",
            # OWL component JS
            "theme_compassion_2025/static/src/js/components/Password.js",
            "theme_compassion_2025/static/src/js/components/RangeInput.js",
            "theme_compassion_2025/static/src/js/components/ProgressBar.js",
            "theme_compassion_2025/static/src/xml/Password.xml",
            "theme_compassion_2025/static/src/xml/RangeInput.xml",
            "theme_compassion_2025/static/src/xml/ProgressBar.xml",
            # publicWidget JS
            "theme_compassion_2025/static/src/js/widgets/event_banner.js",
            "theme_compassion_2025/static/src/js/widgets/map.js",
            "theme_compassion_2025/static/src/js/widgets/form_field_validator.js",
        ],
    },
    "post_init_hook": "_post_init_hook",
    "images": ["static/description/compassion_screenshot.png"],
    "license": "LGPL-3",
    "installable": True,
}
