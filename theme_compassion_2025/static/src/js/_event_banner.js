odoo.define('theme_compassion_2025.event_banner', function (require) {
    'use strict';

    var rpc = require('web.rpc');

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
       params: {
            current_page_route: window.location.pathname
        }
       }).then(function (res) {
            if (!res || !res.html) return;
            const $banner = $(res.html);

              const $wrap = $('<div class="event-banner-wrap"></div>').append($banner);
              const $container = $('main .container').first();
              $container.prepend($wrap);

              const targetHeight= $banner.outerHeight(true);

              requestAnimationFrame(() => {
                $wrap.css('max-height', targetHeight + 'px');
                $wrap.addClass('is-open');
              });

            $banner.on('click', '.js_close_banner', onCloseBanner);
            $banner.slideDown();
        }).catch(function (e) {
            console.warn('Event banner failed', e);
        });
    });
});
