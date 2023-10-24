odoo.define(
  "website_event_compassion.event_registration_form_page",
  function (require) {
    "use strict";

    let publicWidget = require("web.public.widget");

    publicWidget.registry.EventRegistrationForm = publicWidget.Widget.extend({
      selector: "#event_registration_form",

      start: function () {
        this.setup_default_values();
        $("input[name='partner_phone']").on("change", function () {
          $("input[name='phone']").val($(this).val());
        });
        $("input[name='partner_mobile']").on("change", function () {
          $("input[name='mobile']").val($(this).val());
        });
        return this._super(...arguments);
      },

      setup_default_values: function () {
        let form_values = $("#form_values").data();
        let event_id = form_values["event_id"];
        if (event_id) $("select[name='event_id']").val(event_id);
        let select_fields = ["partner_title"];
        select_fields.forEach((s_field) => {
          if (form_values[s_field])
            $(`select[name='${s_field}']`).val(form_values[s_field]);
        });
        let birthdate = form_values["partner_birthdate_date"];
        if (birthdate) {
          $("input[name='partner_birthdate_date']").val(
            new Date(birthdate).toLocaleDateString()
          );
        }
      },
    });
  }
);
