odoo.define("theme_compassion_2025.range_input", function (require) {
    "use strict";

    var publicWidget = require("web.public.widget");

    publicWidget.registry.RangeInput = publicWidget.Widget.extend({
        template: "theme_compassion_2025.RangeInputComponent",
        xmlDependencies: ["/theme_compassion_2025/static/src/xml/RangeInput.xml"],

        events: {
            "input .slider-low": "_slideLow",
            "input .slider-high": "_slideHigh",
            "change .slider-low, .slider-high": "_onRangeChange",
        },

        /**
         * @override
         */
        init(
            parent,
            minValue = 0,
            maxValue = 100,
            initialLow = null,
            initialHigh = null,
            minGap = 0,
            thumbColor = "mid-yellow",
            labelColor = "low-black",
            rangeColor = "low-yellow",
            trackColor = "low-eggshell"
        ) {
            this._super(parent);
            this.minValue = minValue;
            this.maxValue = maxValue;
            this.initialLow = initialLow ?? minValue;
            this.initialHigh = initialHigh ?? maxValue;
            this.minGap = minGap;
            this.thumbColor = thumbColor;
            this.labelColor = labelColor;
            this.rangeColor = rangeColor;
            this.trackColor = trackColor;
        },

        /**
         * @override
         */
        start: function () {
            // Store the promise from the super call in a variable.
            var def = this._super.apply(this, arguments);

            // Get references to widget elements
            this.sliderLow = this.$(".slider-low")[0];
            this.sliderHigh = this.$(".slider-high")[0];
            this.labelLow = this.$(".label-low")[0];
            this.labelHigh = this.$(".label-high")[0];
            this.sliderContainer = this.el;

            // Set initial values from attributes
            this.sliderLow.min = this.minValue;
            this.sliderLow.max = this.maxValue;
            this.sliderLow.value = this.initialLow;
            this.sliderHigh.min = this.minValue;
            this.sliderHigh.max = this.maxValue;
            this.sliderHigh.value = this.initialHigh;

            this._slideLow();
            this._slideHigh();

            // Return the promise.
            return def;
        },

        // --------------------------------------------------------------------------
        // Public
        // --------------------------------------------------------------------------

        getLow: function () {
            return parseInt(this.sliderLow.value);
        },

        getHigh: function () {
            return parseInt(this.sliderHigh.value);
        },

        // --------------------------------------------------------------------------
        // Private
        // --------------------------------------------------------------------------

        /**
         * @private
         */
        _slideLow: function () {
            if (this.getHigh() - this.getLow() < this.minGap) {
                this.sliderLow.value = this.getHigh() - this.minGap;
            }
            this._updateLabelLow();
            this._bringToFront(this.sliderLow);
        },

        /**
         * @private
         */
        _slideHigh: function () {
            if (this.getHigh() - this.getLow() < this.minGap) {
                this.sliderHigh.value = this.getLow() + this.minGap;
            }
            this._updateLabelHigh();
            this._bringToFront(this.sliderHigh);
        },

        /**
         * @private
         */
        _updateLabelLow: function () {
            const value = this.getLow();
            this.labelLow.textContent = value;
            const progressRatio = (value - this.minValue) / (this.maxValue - this.minValue);
            this.sliderContainer.style.setProperty("--progress-ratio-low", progressRatio);
        },

        /**
         * @private
         */
        _updateLabelHigh: function () {
            const value = this.getHigh();
            this.labelHigh.textContent = value;
            const progressRatio = (value - this.minValue) / (this.maxValue - this.minValue);
            this.sliderContainer.style.setProperty("--progress-ratio-high", progressRatio);
        },

        /**
         * @private
         */
        _bringToFront: function (element) {
            this.sliderLow.style.zIndex = 0;
            this.sliderHigh.style.zIndex = 0;
            element.style.zIndex = 1;
        },

        /**
         * Fires the custom range_changed event when the user is done moving one of the ends of the range.
         * @private
         */
        _onRangeChange: function () {
            this.trigger_up("range_changed", {
                low: this.getLow(),
                high: this.getHigh(),
            });
        },
    });

    return publicWidget.registry.RangeInput;
});
