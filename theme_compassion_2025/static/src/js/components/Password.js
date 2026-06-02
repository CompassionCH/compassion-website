/** @odoo-module **/

/**
 * Password input with a show/hide toggle.
 *
 * Renders a `.password-container` wrapping a password input and an inline
 * `.password-show-toggle` FontAwesome icon. Clicking the icon swaps the input
 * between `password` and `text`, and swaps the icon between `fa-eye-slash` and
 * `fa-eye`.
 *
 * Props:
 * - inputName (string, default "password"): the input's `name` attribute.
 * - required (bool, default false): whether the input is mandatory.
 *
 * Mounted declaratively via
 * `<owl-component name="theme_compassion_2025.Password" props='{...}'/>`.
 */
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class Password extends Component {
    static template = "theme_compassion_2025.PasswordComponent";
    static props = {
        inputName: { type: String, optional: true },
        required: { type: Boolean, optional: true },
    };
    static defaultProps = {
        inputName: "password",
        required: false,
    };

    setup() {
        this.state = useState({ visible: false });
    }

    onTogglePasswordVisibility() {
        this.state.visible = !this.state.visible;
    }
}

registry.category("public_components").add("theme_compassion_2025.Password", Password);
