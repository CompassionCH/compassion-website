/** @odoo-module **/

/**
 * Test tours for the donation flow, driven by tests/test_donation_flow.py.
 * Steps without a `run` only wait for their trigger (assertion steps).
 */

import {registry} from "@web/core/registry";

const MOCK_TEST_DATA = {
  product_name: "Test Product",
  product_name_2: "Second Fund",
};

registry.category("web_tour.tours").add("single_one_time_fund_with_suggested_amount", {
  url: "/my2/gifts",
  steps: () => [
    {
      content: "Select the Test Product from the list",
      trigger: `.card.vignette h3:contains("${MOCK_TEST_DATA.product_name}")`,
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Check if we are on the details page (H2 header)",
      trigger: `.donation-details-header h2:contains("${MOCK_TEST_DATA.product_name}")`,
    },
    {
      content: "Select suggestion 'Low' amount",
      trigger: ".my2_donation_form label[for='donation-suggested-low']",
      run: "click",
    },
    {
      content: "Click on Add & check out",
      trigger: ".my2_donation_form button:contains('Add & check out')",
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Check if we are in the cart (Fund Package)",
      trigger: ".my2_gift_package",
    },
    {
      content: "Check if the product is in the list",
      trigger: `body:has(div:contains("${MOCK_TEST_DATA.product_name}")), body:has(td:contains("${MOCK_TEST_DATA.product_name}"))`,
    },
    {
      content: "Check total amount before delete (CHF 50)",
      trigger: ".bg-light-green:contains('Total amount'):contains(' 50')",
    },
  ],
});

registry.category("web_tour.tours").add("single_one_time_fund_with_custom_amount", {
  url: "/my2/gifts",
  steps: () => [
    {
      content: "Select the Test Product from the list",
      trigger: `.card.vignette h3:contains("${MOCK_TEST_DATA.product_name}")`,
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Check if we are on the details page (H2 header)",
      trigger: `.donation-details-header h2:contains("${MOCK_TEST_DATA.product_name}")`,
    },
    {
      content: "Enter the custom amount (75.00)",
      trigger: "input[name='custom_amount']",
      run: "edit 75.00",
    },
    {
      content: "Click on Add & check out",
      trigger: ".my2_donation_form button:contains('Add & check out')",
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Check if we are in the cart (Fund Package)",
      trigger: ".my2_gift_package",
    },
    {
      content: "Check if the product is in the list",
      trigger: `body:has(div:contains("${MOCK_TEST_DATA.product_name}")), body:has(td:contains("${MOCK_TEST_DATA.product_name}"))`,
    },
  ],
});

registry.category("web_tour.tours").add("second_one_time_fund_with_custom_amount", {
  url: "/my2/gifts",
  steps: () => [
    {
      content: "Select the second fund from the list",
      trigger: `.card.vignette h3:contains("${MOCK_TEST_DATA.product_name_2}")`,
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Check if we are on the details page (H2 header)",
      trigger: `.donation-details-header h2:contains("${MOCK_TEST_DATA.product_name_2}")`,
    },
    {
      content: "Enter the custom amount (75.00)",
      trigger: "input[name='custom_amount']",
      run: "edit 75.00",
    },
    {
      content: "Click on Add & check out",
      trigger: ".my2_donation_form button:contains('Add & check out')",
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Check if we are in the cart (Fund Package)",
      trigger: ".my2_gift_package",
    },
    {
      content: "Check if the second fund is in the list",
      trigger: `body:has(div:contains("${MOCK_TEST_DATA.product_name_2}")), body:has(td:contains("${MOCK_TEST_DATA.product_name_2}"))`,
    },
  ],
});

registry.category("web_tour.tours").add("single_monthly_fund_with_suggested_amount", {
  url: "/my2/gifts",
  steps: () => [
    {
      content: "Select the Test Product from the list",
      trigger: `.card.vignette h3:contains("${MOCK_TEST_DATA.product_name}")`,
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Check if we are on the details page (H2 header)",
      trigger: `.donation-details-header h2:contains("${MOCK_TEST_DATA.product_name}")`,
    },
    {
      content: "Click on 'Monthly'",
      trigger: ".my2_donation_form .donation-frequency label:contains('Monthly')",
      run: "click",
    },
    {
      content: "Select suggestion 'Medium' amount",
      trigger: ".my2_donation_form label[for='donation-suggested-low']",
      run: "click",
    },
    {
      content: "Click on Add & check out",
      trigger: ".my2_donation_form button:contains('Add & check out')",
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Check if we are in the cart (Fund Package)",
      trigger: ".my2_gift_package",
    },
    {
      content: "Check if the product is in the list",
      trigger: `body:has(div:contains("${MOCK_TEST_DATA.product_name}")), body:has(td:contains("${MOCK_TEST_DATA.product_name}"))`,
    },
    {
      content: "Check total amount before delete (CHF 50)",
      trigger: ".bg-light-green:contains('Total amount'):contains(' 50')",
    },
  ],
});

registry.category("web_tour.tours").add("single_monthly_fund_with_custom_amount", {
  url: "/my2/gifts",
  steps: () => [
    {
      content: "Select the Test Product from the list",
      trigger: `.card.vignette h3:contains("${MOCK_TEST_DATA.product_name}")`,
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Check if we are on the details page (H2 header)",
      trigger: `.donation-details-header h2:contains("${MOCK_TEST_DATA.product_name}")`,
    },
    {
      content: "Click on 'Monthly'",
      trigger: ".my2_donation_form .donation-frequency label:contains('Monthly')",
      run: "click",
    },
    {
      content: "Enter the custom amount (75.00)",
      trigger: "input[name='custom_amount']",
      run: "edit 75.00",
    },
    {
      content: "Click on Add & check out",
      trigger: ".my2_donation_form button:contains('Add & check out')",
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Check if we are in the cart (Fund Package)",
      trigger: ".my2_gift_package",
    },
    {
      content: "Check if the product is in the list",
      trigger: `body:has(div:contains("${MOCK_TEST_DATA.product_name}")), body:has(td:contains("${MOCK_TEST_DATA.product_name}"))`,
    },
  ],
});

registry.category("web_tour.tours").add("remove_item_from_cart", {
  url: "/my2/gift-package",
  steps: () => [
    {
      content: "Check if product is visible in cart",
      trigger: `.donation-item-container:contains("${MOCK_TEST_DATA.product_name}")`,
    },
    {
      content: "Click on the delete button for this specific product",
      trigger: `.donation-item-container:contains("${MOCK_TEST_DATA.product_name}") .action-button:has(.icon-trash01)`,
      run: "click",
    },
    {
      content: "Wait until the item disappears",
      trigger: `body:not(:has(.donation-item-container:contains("${MOCK_TEST_DATA.product_name}")))`,
    },
    {
      content: "Check if cart is empty",
      trigger: "body:contains('Your Gift Basket is empty.')",
    },
  ],
});

registry.category("web_tour.tours").add("update_item_in_cart", {
  url: "/my2/gift-package",
  steps: () => [
    {
      content: "Click on the edit button (pencil icon) for the specific product",
      trigger: `.donation-item-container:contains("${MOCK_TEST_DATA.product_name}") .icon-edit05`,
      run: "click",
    },
    {
      content: "Select 'Custom amount' to enable the input field",
      trigger: "#edit-donation-form input[name='custom_amount']",
      run: "click",
    },
    {
      content: "Write custom amount of 75 into field",
      trigger: "input[name='custom_amount']",
      run: "edit 75.00",
    },
    {
      content: "Click on Ok button",
      trigger: "button:contains('Ok')",
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Verify update: Check if the price changed to 75",
      trigger: `.donation-item-container:contains("${MOCK_TEST_DATA.product_name}"):contains("75")`,
    },
  ],
});

registry.category("web_tour.tours").add("single_one_time_fund_through_modal", {
  url: "/my2/gift-package",
  steps: () => [
    {
      content: "Click on 'Add a fund' button to go to catalog",
      trigger: 'a[href="/my2/gift-package/add"]',
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Select 'fund for a child' category",
      trigger: 'label[for="donation-type-fund"]',
      run: "click",
    },
    {
      content: "Click 'Add' button on the specific test product card",
      trigger: `.donation-product-container:contains("${MOCK_TEST_DATA.product_name}") button:contains("Add")`,
      run: "click",
    },
    {
      content: "Click 'Add & check out' in the opening modal",
      trigger: ".my2_donation_form button:contains('Add & check out')",
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Verify: Check if we are back in cart and product is there",
      trigger: `.donation-item-container:contains("${MOCK_TEST_DATA.product_name}")`,
    },
  ],
});

registry.category("web_tour.tours").add("try_to_submit_empty_custom_amount", {
  url: "/my2/gifts",
  steps: () => [
    {
      content: "Select the Test Product from the list",
      trigger: `.card.vignette h3:contains("${MOCK_TEST_DATA.product_name}")`,
      run: "click",
      expectUnloadPage: true,
    },
    {
      content: "Check if we are on the details page",
      trigger: `.donation-details-header h2:contains("${MOCK_TEST_DATA.product_name}")`,
    },
    {
      content: "Select 'Custom amount' radio button (this enables the empty input)",
      trigger: ".my2_donation_form input[name='custom_amount']",
      run: "click",
    },
    {
      content: "Stress Test: Click 'Add & check out' WITHOUT entering an amount",
      trigger: ".my2_donation_form button:contains('Add & check out')",
      run: "click",
    },
    {
      content: "Validation Check: Verify the custom amount is flagged invalid",
      trigger: ".my2_donation_form #custom-amount.is-invalid",
    },
  ],
});
