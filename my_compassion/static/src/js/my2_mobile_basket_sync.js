odoo.define("compassion_website.mobile_cart_sync", function (require) {
    "use strict";

    $(document).ready(function () {
        // Listen to all background network requests
        $(document).ajaxSuccess(function (event, xhr, settings) {
            // If Odoo just updated the shopping cart...
            if (settings.url && settings.url.indexOf("/my2/gift-package/delete-item") !== -1) {
                try {
                    const response = JSON.parse(xhr.responseText);

                    // Grab the fresh quantity from the server response
                    if (response && response.result) {
                        const mobileBadges = document.querySelectorAll(".my2-bottom-nav .my_cart_quantity");

                        // Force our mobile badge to match reality
                        mobileBadges.forEach(function (badge) {
                            if (response.result.is_order_empty) {
                                badge.textContent = "0";
                                badge.classList.add("d-none");
                            } else {
                                badge.textContent = String(parseInt(badge.textContent || "0", 10) - 1);
                                badge.classList.remove("d-none");
                            }
                        });
                    }
                } catch (e) {
                    console.log("Could not update mobile cart badge", e);
                }
            }
        });
    });
});
