
odoo.define('website_sponsorship.child_search_page', function (require) {
'use strict';

var Dialog = require('web.Dialog');
var publicWidget = require('web.public.widget');

publicWidget.registry.ChildHold = publicWidget.Widget.extend({
    selector: '#child_search',

    start: function () {
        this.hold_child();
        return this._super.apply(this, arguments);
    },

     hold_child: async function(recordId) {
        const urlParams = new URLSearchParams(window.location.search);
        const paramsDictionary = {};
        for (const [key, value] of urlParams.entries()) {
            paramsDictionary[key] = value;
          }
        const params = $.param(paramsDictionary);
        var self = this;
        $.ajax({
                    url: '/hold_a_child?' + params,
                    type: 'POST',
                    dataType: 'json',
                    contentType: 'application/json',
                    data: JSON.stringify(paramsDictionary),
                    // processData: false,
                    success: function(data) {
                        location.reload();
                    },
                    error: function(xhr, status, error) {
                        // Handle error if the request fails
                        console.error(error);
                        self.display_error();
                    }
                });
        },

    display_error: function() {
        $("#not_found").removeClass("d-none");
        $("#spinner").hide();
        $("#not_found").fadeTo(500, 1);
    }
});

publicWidget.registry.ChildSearch = publicWidget.Widget.extend({
    selector: 'div[name="childpool_page"]',

    start: function () {
        this.set_values();
        $("button[name='search_mobile']").on("click", function() {
           $("div[name='search_inputs']").toggleClass("d-none");
        });
        $("a[name='search']").on("click", function() {
            const gender = $("select[name='gender']").val();
            const age_group = $("select[name='age_group']").val();
            var age_min = "";
            var age_max = "";
            if (age_group && age_group.indexOf("-") !== -1) {
                age_min = age_group.split("-")[0];
                age_max = age_group.split("-")[1];
            }
            const country = $("select[name='country']").val();
            const birthdate = $("input[name='birthday']").val();
            window.location.href = `?gender=${gender}&age_min=${age_min}&age_max=${age_max}&country=${country}&birthday=${birthdate}`;
        });
        return this._super.apply(this, arguments);
    },

    set_values: function() {
        const urlParams = new URLSearchParams(window.location.search);
        var age_min = false;
        var age_max = false;
        for (const [key, value] of urlParams.entries()) {
            $(`*[name='${key}']`).val(value);
            if (key === "age_min")
                age_min = parseInt(value);
            if (key === "age_max")
                age_max = parseInt(value);
        };
        if (Number.isInteger(age_min) && Number.isInteger(age_max)) {
            $("select[name='age_group']").val(`${age_min}-${age_max}`);
        }
        const random_button = $("a[name='random']");
        random_button.attr("href", random_button.attr("href") + "?" + urlParams.toString());
    }

})
});

