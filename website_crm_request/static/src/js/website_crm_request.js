odoo.define("website_form_crm_request.form", function (require) {
  "use strict";

  var core = require("web.core");
  var FormEditorRegistry = require("website_form.form_editor_registry");

  var _t = core._t;

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
});
