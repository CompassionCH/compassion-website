document.addEventListener("DOMContentLoaded", function (event) {

    odoo.define('my_compassion.show_password', function (require) {
        'use strict';

        var publicWidget = require('web.public.widget');

        publicWidget.registry.show_password = publicWidget.Widget.extend({
            selector: '#eye_password',
            events: {
                'click': '_onClick',
            },

            _onClick: function (ev) {
                console.log("Show password clicked");
                // ev.preventDefault();
                // var $icon = $(ev.currentTarget);
                // var $input = $icon.siblings('input');
                // var type = $input.attr('type');
                // if (type === 'password') {
                //     $input.attr('type', 'text');
                //     $icon.removeClass('fa-eye').addClass('fa-eye-slash');
                // } else {
                //     $input.attr('type', 'password');
                //     $icon.removeClass('fa-eye-slash').addClass('fa-eye');
                // }
            },
        });
    });
});
