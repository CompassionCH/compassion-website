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

    tour.register('single_one_time_gift_with_custom_amount', {
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
            content: "Select 'Custom amount' radio button",
            trigger: "label[for='donation-suggested-custom']",
            run: "click"
        },
        {
            content: "Enter the custom amount (75.00)",
            trigger: "input[name='custom_amount']",
            run: "text 75.00"
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

    tour.register('single_monthly_gift_with_custom_amount', {
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
            content: "Select 'Custom amount' radio button",
            trigger: "label[for='donation-suggested-custom']",
            run: "click"
        },
        {
            content: "Enter the custom amount (75.00)",
            trigger: "input[name='custom_amount']",
            run: "text 75.00"
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
    ]);

    tour.register('remove_item_from_cart', {
        test: true,
        url: '/my2/gift-package',
    }, [
        {
            content: "Check if product is visible in cart",
            trigger: `.donation-item-container:contains("${MOCK_TEST_DATA.product_name}")`,
            run: function() { console.log("Item found, ready to delete."); }
        },
        {
            content: "Click on the delete button for this specific product",
            trigger: `.donation-item-container:contains("${MOCK_TEST_DATA.product_name}") .action-button:has(.icon-trash01)`,
            run: "click"
        },
        {
            content: "Wait until the item disappears",
            trigger: `body:not(:has(.donation-item-container:contains("${MOCK_TEST_DATA.product_name}")))`,
            run: function() { console.log("Item successfully deleted."); }
        },
        {
            content: "Check if cart is empty",
            trigger: "body:contains('Your Gift Package is empty.')",
            run: "text"
        }
    ]);

    tour.register('update_item_in_cart', {
        test: true,
        url: '/my2/gift-package',
    }, [
        {
            content: "Click on the edit button (pencil icon) for the specific product",
            trigger: `.donation-item-container:contains("${MOCK_TEST_DATA.product_name}") .icon-edit05`,
            run: "click"
        },
        {
            content: "Select 'Custom amount' to enable the input field",
            trigger: "label[for='donation-suggested-custom']",
            run: "click"
        },
        {
            content: "Write custom amount of 75 into field",

            trigger: "input[name='custom_amount']",
            run: "text 75.00"
        },
        {
            content: "Click on Ok button",
            trigger: "button:contains('Ok')",
            run: "click"
        },
        {
            content: "Verify update: Check if the price changed to 75",
            trigger: `.donation-item-container:contains("${MOCK_TEST_DATA.product_name}"):contains("75")`,
            run: function() { console.log("Item successfully updated to 75."); }
        }
    ]);

    tour.register('single_one_time_gift_through_modal', {
        test: true,
        url: '/my2/gift-package',
    }, [
        {
            content: "Click on 'Add a gift' button to go to catalog",
            trigger: 'a[href="/my2/gift-package/add"]',
            run: "click"
        },
        {
            content: "Select 'Gift for a child' category",
            trigger: 'label[for="donation-type-fund"]',
            run: "click"
        },
        {
            content: "Click 'Add' button on the specific test product card",
            trigger: `.donation-product-container:contains("${MOCK_TEST_DATA.product_name}") button:contains("Add")`,
            run: "click"
        },
        {
            content: "Click 'Add & check out' in the opening modal",
            trigger: ".my2_donation_form button:contains('Add & check out')",
            run: "click"
        },
        {
            content: "Verify: Check if we are back in cart and product is there",
            trigger: `.donation-item-container:contains("${MOCK_TEST_DATA.product_name}")`,
            run: function() { console.log("New item successfully added to cart."); }
        }
    ]);
});