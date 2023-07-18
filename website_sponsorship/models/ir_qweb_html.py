from odoo import api, models


class HTMLConverter(models.AbstractModel):
    _inherit = 'ir.qweb.field.html'

    @api.model
    def value_to_html(self, value, options):
        """
        This fixes an issue that prevented using HTML fields in dynamic content
        snippet.
        """
        if "template_options" not in options:
            options["template_options"] = {}
        return super().value_to_html(value, options)
