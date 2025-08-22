odoo.define('theme_compassion_2025.event_banner', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const rpc = require('web.rpc');
    console.log('Event Banner loaded');

    publicWidget.registry.EventBanner = publicWidget.Widget.extend({
        selector: 'main',
        events: {
            'click .event-banner .action-close': '_onClose',
        },


        async start() {
            await this._super(...arguments);
            return this._loadAndRender();
        },


        async _loadAndRender() {
            const items = await rpc.query({
                route: '/my2/active-event-banners',
                params: {
                    current_page_route: window.location.pathname
                },
            });

            if (!items || !items.length) {
                return;
            }

            const dismissed = JSON.parse(localStorage.getItem('dismissedBanners') || '[]');
            const $container = $('main .container').first();

            items.slice().reverse().forEach(it => {
                if (!it || !it.html) {
                    return;
                }
                const $banner = $(it.html);
                const id = it.id;

                const key = 'dismissedBanners';
                const list = JSON.parse(localStorage.getItem(key) || '[]');
                if (list.includes(id)) {
                    return;
                }

                const $wrap = $('<div class="event-banner-wrap"></div>').append($banner);
                $container.prepend($wrap);
                const targetH = $banner.outerHeight(true);

                requestAnimationFrame(() => {
                    $wrap.css('max-height', targetH + 'px').addClass('is-open');
                });
            });
        },

        _dismiss(id) {
            const key = 'dismissedBanners';
            const list = JSON.parse(localStorage.getItem(key) || '[]');
            if (!list.includes(id)) {
              list.push(id);
              localStorage.setItem(key, JSON.stringify(list));
            }
        },

        _onClose(ev) {
            ev.preventDefault();
            const $banner = $(ev.currentTarget).closest('.event-banner');
            const $wrap = $banner.closest('.event-banner-wrap');
            const id = $banner.data("id");

            $wrap.removeClass('is-open').css('max-height', 0).one('transitionend', () => $wrap.remove());

            this._dismiss(id);
        },
    });

    return publicWidget.registry.EventBanner;
});
