odoo.define("website_form_project.form", function (require) {
  "use strict";

  var core = require("web.core");
  var FormEditorRegistry = require("website_form.form_editor_registry");

  var _t = core._t;

  FormEditorRegistry.add("child_protection", {
    formFields: [
      {
        type: "boolean",
        modelRequired: true,
        name: "agreed",
        string: _t("Check to agree to this charter"),
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
