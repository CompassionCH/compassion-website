odoo.define("website_sponsorship.form_snippet", function (require) {
  "use strict";

  var core = require("web.core");
  var FormEditorRegistry = require("website_form.form_editor_registry");

  var _t = core._t;

  FormEditorRegistry.add("child_sponsorship", {
    formFields: [
      {
        type: "char",
        modelRequired: true,
        name: "partner_firstname",
        string: _t("Firstname"),
      },
      {
        type: "char",
        modelRequired: true,
        name: "partner_lastname",
        string: _t("Lastname"),
      },
      {
        type: "char",
        modelRequired: true,
        name: "partner_email",
        string: _t("Email"),
      },
    ],
  });
});
