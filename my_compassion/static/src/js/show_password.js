document.addEventListener("DOMContentLoaded", function (event) {

    odoo.define('my_compassion.show_password', function (require) {
    'use strict';

        function togglePasswordVisibility(inputId, icon) {
            const input = document.getElementById(inputId);
            if (input) {
                if (input.type === "password") {
                    input.type = "text";
                    icon.classList.add("fa-eye-slash");
                    icon.classList.remove("fa-eye");
                } else {
                    input.type = "password";
                    icon.classList.add("fa-eye");
                    icon.classList.remove("fa-eye-slash");
                }
            }
        }

        function addPasswordToggleListener(eyeId, inputId) {
            const eyeIcon = document.getElementById(eyeId);
            if (eyeIcon) {
                eyeIcon.addEventListener("click", function () {
                    togglePasswordVisibility(inputId, eyeIcon);
                });
            }
        }

        addPasswordToggleListener("eye_password", "password");
        addPasswordToggleListener("eye_confirm_password", "confirm_password");
    });
});
