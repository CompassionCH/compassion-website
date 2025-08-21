odoo.define('theme_compassion_2025.event_banner', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var core = require('web.core');
    var qweb = core.qweb;

    $(function () {
        console.warn('Event banner script loaded');
        function onCloseBanner(ev) {
            ev.preventDefault();
            const $banner = $(ev.currentTarget).closest('.event-banner');
            const bannerId = $banner.data('banner-id');
            const dismissedBanners = JSON.parse(localStorage.getItem('dismissedBanners') || '[]');
            if (!dismissedBanners.includes(bannerId)) {
                dismissedBanners.push(bannerId);
                localStorage.setItem('dismissedBanners', JSON.stringify(dismissedBanners));
            }
            $banner.slideUp(function () { $banner.remove(); });
        }

        // 1) QWeb-Templates laden
        ajax.loadXML('/theme_compassion_2025/static/src/xml/EventBanner.xml', qweb).then(function () {
            // 2) Danach rendern
            return ajax.jsonRpc('/my2/active-event-banners', 'call', {});
        }).then(function (banner) {
            if (!banner || !banner.id) return;

            const bannerHtml = qweb.render('theme_compassion_2025.EventBannerComponent', banner);
            const $banner = $(bannerHtml);
            $('main .container').first().prepend($banner);
            $banner.on('click', '.js_close_banner', onCloseBanner);
            $banner.slideDown();
        }).catch(function (e) {
            console.warn('Event banner failed', e);
        });
    });
});