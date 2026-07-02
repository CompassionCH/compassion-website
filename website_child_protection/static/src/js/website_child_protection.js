/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";
import FormEditorRegistry from "@website/js/form_editor_registry";

FormEditorRegistry.add("child_protection", {
  formFields: [
    {
      type: "boolean",
      modelRequired: true,
      name: "read_check",
      string: _t("Read and Understood"),
    },
    {
      type: "boolean",
      modelRequired: true,
      name: "validation_check",
      string: _t("Aware of Violation Consequences"),
    },
    {
      type: "boolean",
      modelRequired: true,
      name: "legal_check",
      string: _t("Legal Action Awareness"),
    },
    {
      type: "boolean",
      modelRequired: true,
      name: "understand_check",
      string: _t("Understand Update"),
    },
    {
      type: "hidden",
      modelRequired: true,
      name: "partner_uuid",
      string: "UUID",
    },
  ],
});
