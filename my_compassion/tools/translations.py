##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging

from odoo.tools.misc import file_path
from odoo.tools.translate import DeepDefaultDict, TranslationImporter

_logger = logging.getLogger(__name__)


def reapply_translations(env, module, terms):
    """Write the module catalog's translation of the given terms over the
    translation a database already stores, leaving every other term alone.

    Upgrading a module loads its catalogs without overwriting a translation
    the database already has, so a corrected translation never reaches a
    database that holds the old one. This re-applies just the corrected
    terms; a term not listed keeps whatever is stored, including a
    translation staff edited. Records flagged noupdate are left alone, as
    Odoo's own overwrite does.

    :param module: technical name of the module whose catalogs are read
    :param terms: ``{lang: [[reference, msgid], ...]}``, a reference being a
        catalog occurrence such as
        ``model_terms:ir.ui.view,arch_db:my_compassion.some_view`` or
        ``model:ir.actions.server,name:my_compassion.some_action``. Code
        terms need no entry: they are read from the catalog at runtime.
    :return: the number of terms handed to the importer
    """
    installed = {code for code, _name in env["res.lang"].get_installed()}
    importer = TranslationImporter(env.cr, verbose=False)
    wanted = set()
    for lang, entries in terms.items():
        if lang not in installed:
            continue
        importer.load_file(file_path(f"{module}/i18n/{lang}.po"), lang)
        for reference, msgid in entries:
            kind, target = reference.split(":", 1)
            model_field, xmlid = target.split(":", 1)
            model, field = model_field.split(",", 1)
            wanted.add((kind, model, field, xmlid, msgid, lang))

    model_terms = DeepDefaultDict()
    for model, fields in importer.model_terms_translations.items():
        for field, records in fields.items():
            for xmlid, sources in records.items():
                for src, translations in sources.items():
                    for lang, value in translations.items():
                        key = ("model_terms", model, field, xmlid, src, lang)
                        if key in wanted:
                            model_terms[model][field][xmlid][src][lang] = value
    # a whole-field translation has one value per record and language, so
    # its msgid (the source value itself) is not needed to find it
    wanted_fields = {key[1:4] + key[5:] for key in wanted if key[0] == "model"}
    model_values = DeepDefaultDict()
    for model, fields in importer.model_translations.items():
        for field, records in fields.items():
            for xmlid, translations in records.items():
                for lang, value in translations.items():
                    if (model, field, xmlid, lang) in wanted_fields:
                        model_values[model][field][xmlid][lang] = value

    count = sum(
        len(translations)
        for fields in model_terms.values()
        for records in fields.values()
        for sources in records.values()
        for translations in sources.values()
    ) + sum(
        len(translations)
        for fields in model_values.values()
        for records in fields.values()
        for translations in records.values()
    )
    importer.model_terms_translations = model_terms
    importer.model_translations = model_values
    importer.save(overwrite=True)
    _logger.info("Re-applied %s corrected translations of %s.", count, module)
    return count
