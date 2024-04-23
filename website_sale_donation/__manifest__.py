# Copyright 2024 Compassion Switzerland
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Website - Sale donation",
    "summary": "Allows to have a product considered as a donation",
    "version": "14.0.1.0.0",
    "development_status": "Beta",
    "category": "Website",
    "website": "https://github.com/CompassionCH/compassion-website",
    "author": "Compassion Switzerland",
    "maintainers": ["ecino"],
    "license": "AGPL-3",
    "installable": True,
    "external_dependencies": {
        "python": [],
        "bin": [],
    },
    "depends": [
        "website_sale",
        "sale_automatic_workflow",  # OCA/sale-workflow
        "mass_mailing",
    ],
    "data": [
        "templates/website_cart.xml",
    ],
}
