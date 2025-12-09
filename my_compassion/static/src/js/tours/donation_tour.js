odoo.define('compassion_website.donation_tour', function (require) {
      "use strict";

    var tour = require('web_tour.tour');

    var MOCK_TEST_DATA = {
        product_name: 'Test Product',
    };

    tour.register('single_one_time_gift_with_suggested_amount', {
        test: true,
        url: '/my2/gifts',
    }, [
        {
            content: "Select the Test Product from the list",
            trigger: `.card.vignette h3:contains("${MOCK_TEST_DATA.product_name}")`,
            run: "click"
        },
        {
            content: "Check if we are on the details page (H2 header)",
            trigger: `.donation-details-header h2:contains("${MOCK_TEST_DATA.product_name}")`,
            run: "text"
        },
        {
            content: "Click on 'One Time'",
            trigger: ".my2_donation_form .donation-frequency label:contains('One Time')",
            run: "click"
        },
        {
            content: "Select suggestion 'Medium' amount",
            trigger: ".my2_donation_form label[for='donation-suggested-low']",
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
            trigger: `body:has(div:contains("${MOCK_TEST_DATA.product_name}")), body:has(td:contains("${MOCK_TEST_DATA.product_name}"))`,
            run: function () {
                console.log("Product successfully found in cart!");
            }
        },
        {
            content: "Check total amount before delete (CHF 50)",
            trigger: ".bg-light-green:contains('Total amount'):contains(' 50')",
            run: "text"
        },
    ]);

     tour.register('single_monthly_gift_with_suggested_amount', {
        test: true,
        url: '/my2/gifts',
    }, [
        {
            content: "Select the Test Product from the list",
            trigger: `.card.vignette h3:contains("${MOCK_TEST_DATA.product_name}")`,
            run: "click"
        },
        {
            content: "Check if we are on the details page (H2 header)",
            trigger: `.donation-details-header h2:contains("${MOCK_TEST_DATA.product_name}")`,
            run: "text"
        },
        {
            content: "Click on 'Monthly'",
            trigger: ".my2_donation_form .donation-frequency label:contains('Monthly')",
            run: "click"
        },
        {
            content: "Select suggestion 'Medium' amount",
            trigger: ".my2_donation_form label[for='donation-suggested-low']",
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
            trigger: `body:has(div:contains("${MOCK_TEST_DATA.product_name}")), body:has(td:contains("${MOCK_TEST_DATA.product_name}"))`,
            run: function () {
                console.log("Product successfully found in cart!");
            }
        },
        {
            content: "Check total amount before delete (CHF 50)",
            trigger: ".bg-light-green:contains('Total amount'):contains(' 50')",
            run: "text"
        },
    ]);
});