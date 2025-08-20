odoo.define('theme_compassion_2025.event_banner', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');

    /**
     * Widget, das für die Anzeige von Event-Bannern zuständig ist.
     * Es wird automatisch auf dem Element mit der ID 'EventBannerComponent' instanziiert.
     */
    publicWidget.registry.EventBanner = publicWidget.Widget.extend({
        selector: '#EventBannerComponent',
        events: {
            'click .js_close_banner': '_onCloseBanner',
        },

        /**
         * @override
         */
        start: function () {
            // Die _super-Methode gibt einen Promise zurück, den wir weitergeben.
            var def = this._super.apply(this, arguments);
            this._fetchAndRenderBanner();
            return def;
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Ruft die Banner-Daten vom Server ab und rendert den Banner, falls nötig.
         * @private
         */
        _fetchAndRenderBanner: function () {
            var self = this;
            ajax.jsonRpc('/my2/active-event-banners', 'call', {}).then(function (banner) {
                if (self._shouldShowBanner(banner)) {
                    self._renderBanner(banner);
                }
            });
        },

        /**
         * Prüft, ob ein Banner-Objekt gültig ist und vom Benutzer noch nicht geschlossen wurde.
         * @private
         * @param {Object} banner - Das Banner-Datenobjekt vom Server.
         * @returns {boolean} - True, wenn der Banner angezeigt werden soll.
         */
        _shouldShowBanner: function (banner) {
            if (!banner || !banner.id) {
                return false; // Kein gültiger Banner für diese Seite
            }
            var dismissedBanners = JSON.parse(localStorage.getItem('dismissedBanners') || '[]');
            return !dismissedBanners.includes(banner.id);
        },

        /**
         * Erstellt das HTML für den Banner und fügt es in das Widget-Element ein.
         * @private
         * @param {Object} banner - Das Banner-Datenobjekt.
         */
        _renderBanner: function (banner) {
            // Das Design und die Klassen müssen eventuell an Ihr Theme "theme_compassion_2025" angepasst werden.
            var bannerHtml = `
                <div class="event-banner bg-${banner.color} text-white p-3 text-center" data-banner-id="${banner.id}">
                    <div class="container d-flex justify-content-center align-items-center">
                        ${banner.pictogram ? `<i class="fa fa-${banner.pictogram} mr-3"></i>` : ''}
                        <span class="flex-grow-1">${banner.text}</span>
                        ${banner.button_action ? `<a href="${banner.button_action}" class="btn btn-sm btn-light ml-3">Mehr erfahren</a>` : ''}
                        <button type="button" class="close js_close_banner ml-3" aria-label="Close">
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                </div>
            `;
            this.$el.html(bannerHtml);
        },

        /**
         * Event-Handler für den Klick auf den Schliessen-Button.
         * @private
         * @param {Event} ev
         */
        _onCloseBanner: function (ev) {
            ev.preventDefault();
            var $banner = $(ev.currentTarget).closest('.event-banner');
            var bannerId = $banner.data('banner-id');

            // Speichere die ID im localStorage, um den Banner nicht erneut anzuzeigen.
            var dismissedBanners = JSON.parse(localStorage.getItem('dismissedBanners') || '[]');
            if (!dismissedBanners.includes(bannerId)) {
                dismissedBanners.push(bannerId);
                localStorage.setItem('dismissedBanners', JSON.stringify(dismissedBanners));
            }

            // Blende den Banner mit einer Animation aus und zerstöre danach das Widget.
            $banner.slideUp(() => {
                this.destroy();
            });
        },
    });

    return publicWidget.registry.EventBanner;
});
