odoo.define('my_compassion.error_page_redirect', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    publicWidget.registry.RedirectDashboard = publicWidget.Widget.extend({
        selector: "[data-custom='dashboard']",
        events: {
            click: '_onClickDashboard',
        },

        _onClickDashboard() {
            window.location.href = '/my2/dashboard';
        },
    });

    publicWidget.registry.RedirectContactUs = publicWidget.Widget.extend({
        selector: "[data-custom='contact_us']",
        events: {
            click: '_onClickContactUs',
        },

        _onClickContactUs() {
            window.location.href = '/contactus';
        },
    });

});