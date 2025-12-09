odoo.define('compassion_website.donation_tour', function (require) {
      "use strict";

    var tour = require('web_tour.tour');

    tour.register('donation_tour_full_cycle', {
        test: true,
        url: '/my2/gifts',
    }, [
        {
            content: "Select the Goat Donation Fund from the list",
            trigger: ".card.vignette h3:contains('Goat Donation Fund')",
            run: "click"
        },
        {
            content: "Check if we are on the details page (H2 header)",
            trigger: ".donation-details-header h2:contains('Goat Donation Fund')",
            run: "text"
        },
        {
            content: "Click on 'Monthly'",
            trigger: ".my2_donation_form .donation-frequency label:contains('Monthly')",
            run: "click"
        },
        {
            content: "Select suggestion 'Medium' amount",
            trigger: ".my2_donation_form label[for='donation-suggested-medium']",
            run: "click"
        },
        {
            content: "Click on Add & check out",
            trigger: ".my2_donation_form button:contains('Add & check out')",
            run: "click"
        },
        {
            content: "Check if we are in the cart (Gift Package)",
            trigger: "h1:contains('Gift Package'), .my2_gift_package_page",
            run: "text"
        },
        {
            content: "Check if the product is in the list",
            trigger: "body:has(div:contains('Goat Donation Fund')), body:has(td:contains('Goat Donation Fund'))",
            run: function () {
                console.log("Product successfully found in cart!");
            }
        },
        {
            content: "Check total amount before delete (CHF 100)",
            trigger: ".bg-light-green:contains('Total amount'):contains(' 100')",
            run: "text"
        },
        {
            content: "Click on the delete button",
            trigger: "i.icon-trash01, .action-button i[class*='trash']",
            run: "click"
        },
        {
            content: "Wait until the item is gone",
            trigger: "body:not(:has(:contains('Test Donation Goat')))",
            run: function () {
                console.log("Product successfully deleted!");
            }
        },
        {
            content: "Check if the cart is empty",
            trigger: "body:has(div:contains('Your Gift Package is empty.'))",
            run: function () {
                console.log("Cart is empty as expected!");
            }
        },
    ]);
});