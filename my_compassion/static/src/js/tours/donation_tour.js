odoo.define('compassion_website.donation_tour', function (require) {
      "use strict";

    var tour = require('web_tour.tour');

    tour.register('donation_tour_full_cycle', {
        test: true,
        url: '/my2/gift-package/add'
    }, [
        {
            content: "Suche das Test-Produkt und klicke auf Learn More",
            trigger: ".donation-product-container:contains('Test Donation Goat') a:contains('Learn More')",
            run: "click"
        },
        {
            content: "Pruefen ob wir auf der Detailseite sind (H2 Header)",
            trigger: ".donation-details-header h2:contains('Test Donation Goat')",
            run: "text"
        },
        {
            content: "Klicke auf 'Monthly'",
            trigger: ".my2_donation_form .donation-frequency label:contains('Monthly')",
            run: "click"
        },
        {
            content: "Waehle ein Patenkind aus",
            trigger: ".my2_donation_form select[name='recipient']",
            run: "text Anedu"
        },
        {
            content: "Waehle Betrag 'Medium'",
            trigger: ".my2_donation_form label[for='donation-suggested-medium']",
            run: "click"
        },
        {
            content: "Klicke auf Add & check out",
            trigger: ".my2_donation_form button:contains('Add & check out')",
            run: "click"
        },
        {
            content: "Pruefen, ob wir im Warenkorb (Gift Package) sind",
            trigger: "h1:contains('Gift Package'), .my2_gift_package_page",
            run: "text"
        },
        {
            content: "Pruefen, ob das Produkt in der Liste liegt",
            trigger: "body:has(div:contains('Test Donation Goat')), body:has(td:contains('Test Donation Goat'))",
            run: function () {
                console.log("Produkt erfolgreich im Warenkorb gefunden!");
            }
        },
        {
            content: "Klicke auf den Loeschen-Button",
            trigger: "i.icon-trash01, .action-button i[class*='trash']",
            run: "click"
        },
        {
            content: "Warten bis das Item weg ist",
            trigger: "body:not(:has(:contains('Test Donation Goat')))",
            run: function () {
                console.log("Produkt erfolgreich geloescht!");
            }
        }
    ]);
});