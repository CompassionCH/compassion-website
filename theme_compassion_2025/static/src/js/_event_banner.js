odoo.define('theme_compassion_2025.event_banner', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const rpc = require('web.rpc');

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

            items.slice().reverse().forEach(item => {
                if (!item || !item.html) {
                    return;
                }
                const $banner = $(item.html);
                const id = item.id;

                const key = 'dismissedBanners';
                const list = JSON.parse(localStorage.getItem(key) || '[]');
                if (list.includes(id)) {
                    return;
                }

                const $wrap = $('<div class="event-banner-wrap"></div>').append($banner);
                $container.prepend($wrap);
                const targetBannerHeight = $banner.outerHeight(true);

                requestAnimationFrame(() => {
                  // 1) Startzustand sicherstellen
                  $wrap.css('max-height', 0);

                  // 2) Reflow erzwingen, damit die folgende Änderung animiert
                  // eslint-disable-next-line no-unused-expressions
                  $wrap[0].offsetHeight;

                  // 3) Zielhöhe setzen + Klasse (für die Opacity/Transform des Inhalts)
                  $wrap.addClass('is-open');
                  $wrap.css('max-height', targetBannerHeight + 'px');

                  // 4) Nach Ende der max-height-Transition freigeben (nur Wrapper + richtige Eigenschaft)
                  const onEnd = (e) => {
                    const prop = e.originalEvent ? e.originalEvent.propertyName : e.propertyName;
                    if (e.target !== $wrap[0] || prop !== 'max-height') return;
                    $wrap.off('transitionend', onEnd);
                    $wrap.css('max-height', 'none'); // => keine Obergrenze mehr, Resize egal
                  };
                  $wrap.on('transitionend', onEnd);

                  // 5) Fallback, falls kein transitionend kommt (z. B. 350ms + Puffer)
                  setTimeout(() => {
                    if ($wrap.css('max-height') !== 'none') {
                      $wrap.off('transitionend', onEnd);
                      $wrap.css('max-height', 'none');
                    }
                  }, 500);
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
          const $wrap   = $banner.closest('.event-banner-wrap');
          const id      = $banner.data('id'); // (oder data('banner-id') wenn du umstellst)

          // Wenn freigegeben: aktuelle Höhe fixieren, damit die Transition sichtbar ist
          if ($wrap.css('max-height') === 'none') {
            $wrap.css('max-height', $banner.outerHeight(true) + 'px');
            // Reflow, damit der folgende Wechsel auf 0 sicher animiert
            // eslint-disable-next-line no-unused-expressions
            $wrap[0].offsetHeight;
          }

          requestAnimationFrame(() => {
            $wrap.removeClass('is-open').css('max-height', 0)
                 .one('transitionend', () => $wrap.remove());
          });

          this._dismiss(id);
        },
    });

    return publicWidget.registry.EventBanner;
});
