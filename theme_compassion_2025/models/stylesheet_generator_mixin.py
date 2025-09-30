##############################################################################
#
#    Copyright (C) 2025 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import base64
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class StylesheetGeneratorMixin(models.AbstractModel):
    """
    Abstract class to provide common functionalities for generating theme related
    stylesheets.
    """

    _name = "stylesheet.generator.mixin"
    _description = "Stylesheet Generator Mixin"

    render_key = None
    css_template_xml_id = None
    css_attachment_xml_id = None

    @api.model
    def _generate_stylesheet(self):
        """
        Generates a CSS stylesheet from a template and updates the corresponding CSS
        attachment.
        """
        if not getattr(self, "css_template_xml_id", None):
            _logger.warning(
                f"Model {self._name} is missing 'css_template_xml_id' attribute. "
                f"Skipping generation."
            )
            return

        module, template_id = self.css_template_xml_id.split(".")

        css_template_xml = self.env["ir.model.data"].search(
            [
                ("name", "=", template_id),
                ("module", "=", module),
            ]
        )
        views = self.env["ir.ui.view"].browse(css_template_xml.res_id or [])
        if not css_template_xml or not views.exists():
            _logger.warning(
                f"Stylesheet template '{self.css_template_xml_id}' not found. "
                f"Skipping generation."
            )
            return

        records = self.search([])

        # Render the QWeb template
        css_content = self.env["ir.qweb"]._render(
            self.css_template_xml_id,
            {self.render_key: records},
        )

        css_content_b64 = base64.b64encode(css_content)

        # Find and update css file present in ir.attachment
        attachment = self.env.ref(self.css_attachment_xml_id)
        if attachment:
            attachment.write({"datas": css_content_b64})
            _logger.info(f"Successfully updated {attachment.name} file.")
        else:
            _logger.warning(
                f"Attachment '{self.css_attachment_xml_id}' not found. Skipping css "
                f"generation"
            )

        # force bundle invalidation
        self.env["ir.qweb"].clear_caches()
        _logger.info(f"Successfully re-loaded assets for {self._name}.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._generate_stylesheet()
        # Force-reload web.assets_frontend
        return records

    def write(self, vals):
        res = super().write(vals)
        self._generate_stylesheet()
        return res

    def unlink(self):
        res = super().unlink()
        self._generate_stylesheet()
        return res
