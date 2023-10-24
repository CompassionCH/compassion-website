odoo.define("website_event_compassion.form_snippet", function (require) {
  "use strict";

  let core = require("web.core");
  let FormEditorRegistry = require("website_form.form_editor_registry");

  let _t = core._t;

  FormEditorRegistry.add("event_registration", {
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
        type: "email",
        modelRequired: true,
        name: "partner_email",
        string: _t("Email"),
      },
      {
        type: "date",
        modelRequired: true,
        name: "partner_birthdate_date",
        string: _t("Birthdate"),
      },
      {
        type: "tel",
        modelRequired: false,
        name: "partner_phone",
        string: _t("Phone"),
      },
      {
        type: "tel",
        modelRequired: false,
        name: "partner_mobile",
        string: _t("Mobile"),
      },
      {
        type: "char",
        modelRequired: true,
        name: "partner_street",
        string: _t("Street"),
      },
      {
        type: "integer",
        modelRequired: true,
        name: "partner_zip",
        string: _t("Postal code"),
      },
      {
        type: "char",
        modelRequired: true,
        name: "partner_city",
        string: _t("City"),
      },
      {
        type: "char",
        modelRequired: true,
        name: "birth_name",
        string: _t("Passport name"),
      },
      {
        type: "char",
        modelRequired: true,
        name: "passport_number",
        string: _t("Passport number"),
      },
      {
        type: "date",
        modelRequired: true,
        name: "passport_expiration_date",
        string: _t("Passport expiration date"),
      },
      {
        type: "char",
        modelRequired: true,
        name: "emergency_name",
        string: _t("Emergency contact name"),
      },
      {
        type: "tel",
        modelRequired: true,
        name: "emergency_phone",
        string: _t("Emergency contact phone"),
      },
      {
        type: "binary",
        modelRequired: false,
        name: "profile_picture",
        string: _t("Profile picture"),
      },
      {
        type: "text",
        modelRequired: true,
        name: "profile",
        string: _t("Profile name"),
      },
      {
        type: "text",
        modelRequired: true,
        name: "ambassador_quote",
        string: _t("My motto"),
      },
      {
        type: "hidden",
        modelRequired: true,
        name: "event_id",
        string: _t("Event"),
      },
      {
        type: "hidden",
        modelRequired: false,
        name: "amount_objective",
        string: _t("Fundraising objective"),
      },
      {
        type: "text",
        modelRequired: false,
        name: "comments",
        string: _t("Comments"),
      },
    ],
  });
});
