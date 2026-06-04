/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import FormEditorRegistry from "@website/js/form_editor_registry";

FormEditorRegistry.add("crm_request", {
  formFields: [
    {
      type: "char",
      modelRequired: true,
      name: "name",
      string: _t("Subject"),
    },
    {
      type: "email",
      modelRequired: true,
      name: "email_from",
      string: _t("Email"),
    },
    {
      type: "tel",
      modelRequired: false,
      name: "partner_phone",
      string: _t("Phone number"),
    },
    {
      type: "text",
      modelRequired: true,
      name: "description",
      string: _t("Message"),
    },
  ],
});
