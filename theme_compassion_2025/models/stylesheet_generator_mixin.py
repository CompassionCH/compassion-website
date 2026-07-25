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

from lxml import etree

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
        self._render_to_attachment(
            self.css_template_xml_id,
            self.css_attachment_xml_id,
            {self.render_key: self.search([])},
        )

    @api.model
    def _render_to_attachment(self, template_xml_id, attachment_xml_id, render_context):
        """Render a QWeb template and store the CSS result in the given attachment."""
        view_template = self.env.ref(template_xml_id, raise_if_not_found=False)
        if not view_template:
            _logger.warning(
                f"Stylesheet template '{template_xml_id}' not found for model "
                f"'{self._name}'. Skipping CSS generation."
            )
            return

        # theme_* modules stage <template>s into theme.ir.ui.view until the theme is
        # activated on a website, and ir.qweb._render(xml_id) only resolves a real
        # ir.ui.view. While only the staged view exists, render its arch directly.
        if view_template._name == "ir.ui.view":
            template = template_xml_id
        else:
            template = etree.fromstring(view_template.arch)
        css_content = self.env["ir.qweb"]._render(template, render_context)

        attachment = self.env.ref(attachment_xml_id, raise_if_not_found=False)
        if not attachment:
            _logger.warning(
                f"Attachment '{attachment_xml_id}' not found for model "
                f"'{self._name}'. Skipping CSS update."
            )
            return
        attachment.write(
            {
                "datas": base64.b64encode(css_content.encode("utf-8")),
                "website_id": False,
            }
        )
        _logger.info(f"Successfully updated {attachment.name} file.")

        # Invalidate the assets cache so the regenerated stylesheet goes live.
        # A bare clear_cache() only clears the default cache. The frontend
        # bundle version is memoized in the assets cache, so without this the
        # served bundle stays stale until the next server restart.
        self.env.registry.clear_cache("assets")

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
