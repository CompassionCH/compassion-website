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
from odoo.http import request

_logger = logging.getLogger(__name__)


class StylesheetGeneratorMixin(models.AbstractModel):
    """
    Abstract class to provide common functionality for generating theme related
    stylesheets.
    """

    _name = "stylesheet.generator.mixin"
    _description = "Stylesheet Generator Mixin"

    @api.model
    def _generate_stylesheet(self):
        """
        Generates a CSS stylesheet from a template and updates the corresponding CSS
        attachment.
        """
        if not hasattr(self, "css_template_xml_id"):
            _logger.warning(
                f"Model {self._name} is missing 'css_template_xml_id' attribute. Skipping generation."
            )
            return

        # TODO clean this ugly way of doing
        module, template_id = self.css_template_xml_id.split(".")

        css_template_xml = self.env["ir.model.data"].search(
            [
                ("name", "=", template_id),
                ("module", "=", module),
            ]
        )
        if not css_template_xml:
            _logger.warning(
                f"Stylesheet template '{self.css_template_xml_id}' not found. Skipping generation."
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
        else:
            _logger.warning(
                f"Attachment '{self.css_attachment_xml_id}' not found. Skipping css generation"
            )

        try:
            # Ensure request object is initialise
            request.env
            # Force-reload web.assets_frontend
            self.env["ir.qweb"]._get_asset_nodes("web.assets_frontend", {}, js=False)
            _logger.info(f"Successfully re-loaded assets for {self._name}.")
        except RuntimeError:
            # This is expected when the asset regeneration is call out of request context
            # For exemple during an update, when the odd http server is not fully loaded.
            _logger.warning(
                f"Failed to re-load assets for {self._name}. Please do it manually using the interface."
            )
