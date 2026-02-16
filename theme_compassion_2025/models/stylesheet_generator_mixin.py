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
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StylesheetGeneratorMixin(models.AbstractModel):
    """
    Abstract class to provide common functionalities for generating theme related
    stylesheets.

    Inheriting models must define the following class attributes:
    - render_key (str): The key used in the QWeb context to pass the records.
    - css_template_xml_id (str): The XML ID of the 'ir.ui.view' used as a template.
    - css_attachment_xml_id (str): The XML ID of the 'ir.attachment' to update
    """

    _name = "stylesheet.generator.mixin"
    _description = "Stylesheet Generator Mixin"

    render_key = None
    css_template_xml_id = None
    css_attachment_xml_id = None
    website_name = "MyCompassion"

    def _check_required_attributes(self):
        """Ensure that the inheriting class has defined the required attributes."""
        if not all(
            [self.render_key, self.css_template_xml_id, self.css_attachment_xml_id]
        ):
            raise UserError(
                f"The model '{self._name}' inheriting 'stylesheet.generator.mixin' "
                "must define 'render_key', 'css_template_xml_id', and "
                "'css_attachment_xml_id'."
            )

    @api.model
    def _generate_stylesheet(self):
        """
        Generates a CSS stylesheet from a QWeb template and updates the
        corresponding ir.attachment record.
        """
        self._check_required_attributes()

        view_template = self.env.ref(self.css_template_xml_id, raise_if_not_found=False)
        if not view_template:
            _logger.warning(
                f"Stylesheet template '{self.css_template_xml_id}' not found for model "
                f"'{self._name}'. Skipping CSS generation."
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
        attachment = self.env.ref(self.css_attachment_xml_id, raise_if_not_found=False)
        if not attachment:
            _logger.warning(
                f"Attachment '{self.css_attachment_xml_id}' not found for model "
                f"'{self._name}'. Skipping CSS update."
            )
            return
        attachment.write({"datas": css_content_b64, "website_id": False})
        _logger.info(f"Successfully updated {attachment.name} file.")

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
