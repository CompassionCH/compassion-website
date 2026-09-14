##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Post-migration to 18.0.1.0.3 of my_compassion_native.

Opt the MyCompassion website into the mobile-web app shell
(``my2_bottom_nav_on_web``). The field defaults to False so the bottom-tab-bar
shell stays native-app-only until a country opts in (see its help text); CH
(T3410 QA) expects it on for the MyCompassion website's mobile browser
experience, where it is currently off, so mobile visitors get the regular
website header/footer instead of the intended app-style bottom nav.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    website = env.ref("my_compassion.my2_website", raise_if_not_found=False)
    if website and not website.my2_bottom_nav_on_web:
        website.my2_bottom_nav_on_web = True
