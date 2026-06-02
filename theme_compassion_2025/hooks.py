##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################


def _post_init_hook(env):
    """Called after the module is installed to generate the colors, icons and
    pictograms stylesheet attachments from their records.
    """
    for model_name in (
        "theme.compassion.colors",
        "theme.compassion.icons",
        "theme.compassion.pictograms",
    ):
        env[model_name].sudo()._generate_stylesheet()
