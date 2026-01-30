# Copyright 2023 Emanuel Cino <ecino@compassion.ch>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Website - Child protection agreement",
    "summary": "Adds a form for letting partners agree with the child protection",
    "version": "18.0.1.0.0",
    "development_status": "Beta",
    "category": "Website",
    "website": "https://github.com/CompassionCH/compassion-website",
    "author": "Compassion Switzerland",
    "maintainers": ["ecino"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "website",
        "child_protection",
    ],
    "data": [
        "templates/child_protection_charter.xml",
    ],
}
