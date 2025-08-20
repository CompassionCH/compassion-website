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
    "version": "14.0.2.0.0",
    "author": "Compassion Switzerland",
    "depends": ["website"],
    "external_dependencies": {
        "python": ["python-slugify"],
    },
    "data": [
        "views/theme_compassion_views.xml",
        "views/assets.xml",
        "views/images_content.xml",
        "views/template_header.xml",
        "views/footer.xml",
        # Data
        "data/colors.xml",
        "data/icons.xml",
        "data/pictograms.xml",
        "data/dynamic_stylesheets.xml",
        # Components
        "templates/components/Portrait.xml",
        "templates/components/Title.xml",
        "templates/components/Vignette.xml",
        "templates/components/Select.xml",
        "templates/components/FormField.xml",
        "templates/components/RangeInputLoading.xml",
        "templates/components/EventBanner.xml",
        # Buttons
        "templates/components/buttons/ThemedButton.xml",
        "templates/components/buttons/ToggleButton.xml",
        # Styles
        "templates/styles/colors_stylesheet.xml",
        "templates/styles/icons_stylesheet.xml",
        "templates/styles/pictograms_stylesheet.xml",
        # Security
        "security/ir.model.access.csv",
    ],
    "post_init_hook": "_post_init_hook",
    "images": ["static/description/compassion_screenshot.png"],
    "license": "LGPL-3",
}
