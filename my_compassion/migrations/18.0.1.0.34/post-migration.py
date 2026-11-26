##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import json
from pathlib import Path

from odoo import SUPERUSER_ID, api

from odoo.addons.my_compassion.tools.translations import reapply_translations


def migrate(cr, version):
    """Write this version's corrected translations over the old ones.

    corrected_terms.json lists, per language, the terms whose translation
    this version changed against 18.0.1.0.33's catalogs (same msgid, both
    translated, different text). An upgrade alone keeps the translation a
    database already stores, so these are re-applied; every other stored
    translation is left as it is.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    terms = json.loads(
        (Path(__file__).parent / "corrected_terms.json").read_text(encoding="utf-8")
    )
    reapply_translations(env, "my_compassion", terms)
