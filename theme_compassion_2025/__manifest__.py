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
    "version": "14.0.1.0.0",
    "author": "Compassion Switzerland",
    "depends": ["website"],
    "data": [
        "views/assets.xml",
        "views/images_content.xml",
        "views/template_header.xml",
        "views/footer.xml",
        "templates/components/Portrait.xml",
        # Components
        "templates/components/Title.xml",
        "templates/components/Vignette.xml",
        "templates/components/Select.xml",
        "templates/components/FormField.xml",
        "templates/components/RangeInputLoading.xml",
        # Buttons
        "templates/components/buttons/ThemedButton.xml",
    ],
    "images": ["static/description/compassion_screenshot.png"],
    "license": "LGPL-3",
}
