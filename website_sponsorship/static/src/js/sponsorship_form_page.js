
odoo.define('website_sponsorship.form_page', function (require) {
'use strict';

var Dialog = require('web.Dialog');
var publicWidget = require('web.public.widget');

publicWidget.registry.HelloWorldPopup = publicWidget.Widget.extend({
    selector: '#sponsorship-form',

    start: function () {
        //$("#sponsorship_amount").text("50");
        // let origin = $("select[name='origin_id']").val();
        this.setup_default_values();

        $("#sponsorship_plus_info").click(function () {
            $("#sponsorship_plus_help").toggleClass("d-none");
        });
        $("#do_later").click(function () {
            $("#thankyou_notice").removeClass("d-none");
            $("#next-step-chooser").addClass("d-none");
            $("#sponsorship-form-section").addClass("d-none");
        });
        $("#step2-button").click(function () {
            $("#sponsorship-form-section").removeClass("d-none");
        });
        return this._super.apply(this, arguments);
    },

    setup_default_values: function() {
        let form_values = $("#form_values").data();
        let origin = form_values['origin_id'];
        if (origin) {
            $("select[name='origin_id']").val(origin);
            $("input[name='Origin of my sponsorship']").val(form_values['origin_name']);
        } else {
            this.show_origin_field();
        }
        let select_fields = ["partner_title", "partner_lang", "payment_mode_id"];
        select_fields.forEach((s_field) => {
            if (form_values[s_field])
                $(`select[name='${s_field}']`).val(form_values[s_field]);
        });
        let check_fields = ["partner_spoken_lang_ids"];
        check_fields.forEach((c_field) => {
           if (form_values[c_field]) {
               form_values[c_field].forEach((check_id) => {
                  $(`input[name='${c_field}'][value='${check_id}']`).attr("checked", "checked");
               });
           }
        });
        let birthdate = form_values['partner_birthdate_date'];
        if (birthdate) {
            $("input[name='partner_birthdate_date']").val(new Date(birthdate).toLocaleDateString());
        }
    },

    show_origin_field: function () {
        $("#origin_id,#origin_details").removeClass("s_website_form_field_hidden");
    }
})
});

