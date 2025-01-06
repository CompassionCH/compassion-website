/**
 * A customizable progress bar widget with animated flowing stripes.
 *
 * This widget can be controlled by advancing it to specific steps.
 * It controls the rendering and animation of the
 * `theme_compassion_2025.ProgressBarComponent` QWeb template.
 *
 * Usage:
 * ```js
 * const ProgressBarWidget = publicWidget.registry.ProgressBarWidget;
 * const widget = new ProgressBarWidget(this, {
 * density: 'high',
 * flowSpeed: '3s',
 * steps: [
 * "Connecting to server...",
 * "Uploading files...",
 * "Finalizing process..."
 * ]
 * });
 * await widget.appendTo($("#some-container"));
 * widget.startProgress(); // Initializes the bar to step 0
 *
 * // Later, you can advance the progress bar programmatically
 * widget.goToStep(1); // Moves to "Uploading files..."
 * widget.goToStep(2); // Moves to "Finalizing process..."
 * ```
 *
 * Props (options object):
 * {string} density
 * Stripe density. One of: `"low"`, `"medium"`, `"high"`.
 * Controls how dense the stripe pattern is.
 *
 * {string} flowSpeed
 * CSS duration (e.g., `"2s"`, `"4s"`) that defines how fast
 * stripes flow across the bar.
 *
 * {string[]} steps
 * Array of step messages shown under the bar. The progress is
 * divided equally among these steps.
 */

odoo.define("theme_compassion_2025.ProgressBarWidget", function (require) {
    "use strict";

    var publicWidget = require("web.public.widget");

    var ProgressBarWidget = publicWidget.Widget.extend({
        template: "theme_compassion_2025.ProgressBarComponent",
        xmlDependencies: ["/theme_compassion_2025/static/src/xml/ProgressBar.xml"],

        defaults: {
            steps: ["Step 1", "Step 2", "Step 3", "Step 4"],
            density: "medium",
            flowSpeed: "4s",
        },

        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.options = _.defaults(options || {}, this.defaults);
        },

        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var densityClass = "density-" + self.options.density;
                var $bar = self.$(".progress");
                $bar.addClass(densityClass);
                if (self.options.flowSpeed) {
                    $bar.css("--flow-speed", self.options.flowSpeed);
                }
            });
        },

        /**
         * Initializes the progress bar and sets it to the first step.
         */
        startProgress: function () {
            this.$(".progress").addClass("is-flowing");
            this.goToStep(0);
        },

        /**
         * Moves the progress bar to a specific step.
         * @param {Number} stepIndex - The zero-based index of the step to go to.
         */
        goToStep: function (stepIndex) {
            var steps = this.options.steps;
            var totalSteps = steps.length;
            var $progressText = this.$(".progress-text");
            var $progressBar = this.$(".progress");

            if (totalSteps === 0) {
                return; // Do nothing if there are no steps
            }

            // Clamp the index to be within the valid bounds of the steps array
            var clampedIndex = Math.max(0, Math.min(stepIndex, totalSteps - 1));

            // Update the text to the message for the current step
            $progressText.text(steps[clampedIndex]);

            // Calculate the percentage completion *after* this step is reached
            var progress = (clampedIndex + 1) / totalSteps;
            var newWidth = progress * 100;

            // Update the visual width of the progress bar
            $progressBar.css("clip-path", "inset(0 " + (100 - newWidth) + "% 0 0)");
        },
    });

    publicWidget.registry.ProgressBarWidget = ProgressBarWidget;

    return ProgressBarWidget;
});
