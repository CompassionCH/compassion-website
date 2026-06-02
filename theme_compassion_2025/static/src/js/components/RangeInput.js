/** @odoo-module **/

/**
 * Double-ended range slider.
 *
 * Renders a `.slider-container` holding two overlaid `input[type=range]` thumbs
 * (`.slider-low`, `.slider-high`), a `.slider-track`, a `.slider-range` fill, and
 * two numeric labels (`.label-low`, `.label-high`). The selected range is kept at
 * least `minGap` wide: dragging one thumb past the gap pushes the other. The
 * container's `--progress-ratio-low` / `--progress-ratio-high` CSS variables are
 * updated as the thumbs move; the stylesheet uses them to position the fill and
 * labels. The active thumb is raised above the other via z-index so it stays
 * grabbable where they overlap.
 *
 * Props:
 * - min (number, default 0): low bound of the track.
 * - max (number, default 100): high bound of the track.
 * - initialMin (number, default min): starting low value.
 * - initialMax (number, default max): starting high value.
 * - minGap (number, default 0): smallest allowed interval between the two values.
 * - thumbColor (string, default "mid-yellow"): thumb color class suffix.
 * - labelColor (string, default "low-black"): label text color class suffix.
 * - rangeColor (string, default "low-yellow"): in-range track color class suffix.
 * - trackColor (string, default "low-eggshell"): out-of-range track color class suffix.
 * - onRangeChange (function, default no-op): called with `{ min, max }` once the
 *   user finishes moving a thumb.
 *
 * Mounted declaratively via
 * `<owl-component name="theme_compassion_2025.RangeInput" props='{...}'/>`.
 */
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class RangeInput extends Component {
    static template = "theme_compassion_2025.RangeInput";
    static props = {
        min: { type: Number, optional: true },
        max: { type: Number, optional: true },
        initialMin: { type: Number, optional: true },
        initialMax: { type: Number, optional: true },
        minGap: { type: Number, optional: true },
        thumbColor: { type: String, optional: true },
        labelColor: { type: String, optional: true },
        rangeColor: { type: String, optional: true },
        trackColor: { type: String, optional: true },
        onRangeChange: { type: Function, optional: true },
    };
    static defaultProps = {
        min: 0,
        max: 100,
        minGap: 0,
        thumbColor: "mid-yellow",
        labelColor: "low-black",
        rangeColor: "low-yellow",
        trackColor: "low-eggshell",
        onRangeChange: () => {},
    };

    setup() {
        const low =
            this.props.initialMin !== undefined ? this.props.initialMin : this.props.min;
        const high =
            this.props.initialMax !== undefined ? this.props.initialMax : this.props.max;
        this.state = useState({ low, high, frontThumb: "low" });
    }

    getLow() {
        return parseInt(this.state.low);
    }

    getHigh() {
        return parseInt(this.state.high);
    }

    get progressRatioLow() {
        return (this.getLow() - this.props.min) / (this.props.max - this.props.min);
    }

    get progressRatioHigh() {
        return (this.getHigh() - this.props.min) / (this.props.max - this.props.min);
    }

    _slideLow(ev) {
        let low = parseInt(ev.target.value);
        if (this.getHigh() - low < this.props.minGap) {
            low = this.getHigh() - this.props.minGap;
        }
        this.state.low = low;
        this.state.frontThumb = "low";
    }

    _slideHigh(ev) {
        let high = parseInt(ev.target.value);
        if (high - this.getLow() < this.props.minGap) {
            high = this.getLow() + this.props.minGap;
        }
        this.state.high = high;
        this.state.frontThumb = "high";
    }

    _onRangeChange() {
        this.props.onRangeChange({ min: this.getLow(), max: this.getHigh() });
    }
}

registry.category("public_components").add("theme_compassion_2025.RangeInput", RangeInput);
