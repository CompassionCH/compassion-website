odoo.define('theme_compassion_2025.event_banner', function (require) {
    'use strict';

    var rpc = require('web.rpc');

    console.log("event banner loaded");

    $(function () {
        function onCloseBanner(ev) {
            ev.preventDefault();
            const $banner = $(ev.currentTarget).closest('.event-banner');
            const id = $banner.data('banner-id');
            const dismissed = JSON.parse(localStorage.getItem('dismissedBanners') || '[]');
            if (!dismissed.includes(id)) {
                dismissed.push(id);
                localStorage.setItem('dismissedBanners', JSON.stringify(dismissed));
            }
            $banner.slideUp(function () { $banner.remove(); });
        }

        rpc.query({
            route: '/my2/active-event-banners',
            params: { current_page_route: window.location.pathname }
        }).then(function (eventBanners) {
            if (!eventBanners || !eventBanners.length) {
                return;
            }

            const $container = $('main .container').first();

            eventBanners.slice().reverse().forEach((eventBanner) => {
                if (!eventBanner || !eventBanner.html) {
                    return;
                }
                const $eventBanner = $(eventBanner.html);
                const id = eventBanner.id;


                const $wrap = $('<div class="event-banner-wrap"></div>').append($eventBanner);
                $container.prepend($wrap);

                const targetHeight = $eventBanner.outerHeight(true);
                requestAnimationFrame(() => {
                    $wrap.css('max-height', targetHeight + 'px').addClass('is-open');
                });

                /*$wrap.on('click', '.js_close_banner', function (ev) {
                    ev.preventDefault();
                    closeBanner($wrap, eventBanner.id);
                });*/
            });
        }).catch(console.warn);
    });
});
