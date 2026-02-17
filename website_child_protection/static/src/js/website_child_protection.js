odoo.define("website_child_protection.form", function (require) {
    "use strict";

    const core = require("web.core");
    const FormEditorRegistry = require("website_form.form_editor_registry");

    const _t = core._t;

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
});
