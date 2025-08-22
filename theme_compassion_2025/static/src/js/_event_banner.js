odoo.define('theme_compassion_2025.event_banner', function (require) {
    'use strict';

    var ajax = require('web.ajax');

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

        ajax.jsonRpc('/my2/active-event-banners', 'call', {}).then(function (res) {
            if (!res || !res.html) return;
            const $banner = $(res.html);
             // Wrapper erstellen, Banner hineinpacken
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
