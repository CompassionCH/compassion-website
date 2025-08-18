/**
 * A customizable progress bar widget with animated flowing stripes.
 *
 * This widget controls the rendering and animation of the
 * `theme_compassion_2025.ProgressBarComponent` QWeb template.
 *
 * Usage:
 * ```js
 * const ProgressBarWidget = publicWidget.registry.ProgressBarWidget;
 * const widget = new ProgressBarWidget(this, {
 *   density: 'high',
 *   flowSpeed: '3s',
 *   loadSpeed: '5s',
 *   steps: [
 *     "Initializing...",
 *     "Loading modules...",
 *     "Finalizing..."
 *   ]
 * });
 * await widget.appendTo($("#some-container"));
 * widget.startProgress();
 * ```
 *
 * Props (options object):
 * {string} density
 *      Stripe density. One of: `"low"`, `"medium"`, `"high"`.
 *      Controls how dense the stripe pattern is.
 *
 * {string} flowSpeed
 *      CSS duration (e.g., `"2s"`, `"4s"`) that defines how fast
 *      stripes flow across the bar.
 *
 * {string} loadSpeed
 *      CSS duration (e.g., `"5s"`, `"10s"`) that defines the total
 *      simulated loading time for the progress bar.
 *
 * {string[]} steps
 *      Array of step messages shown under the bar while loading
 *      progresses.
 */

odoo.define("theme_compassion_2025.ProgressBarWidget", function (require) {
    "use strict";

    var publicWidget = require("web.public.widget");

    var ProgressBarWidget = publicWidget.Widget.extend({
        template: "theme_compassion_2025.ProgressBarComponent",
        xmlDependencies: ["/theme_compassion_2025/static/src/xml/ProgressBar.xml"],

        defaults: {
            steps: ["loading", "loading.", "loading..", "loading..."],
            density: "medium",
            flowSpeed: "4s",
            loadSpeed: "4s",
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

        startProgress: function () {
            var self = this;
            return new Promise(function (resolve) {
                var steps = self.options.steps;
                var $progressText = self.$(".progress-text");
                var $progressBar = self.$(".progress");

                const totalDuration = parseFloat(self.options.loadSpeed) * 1000;
                const updateInterval = 100;
                const startTime = Date.now();

                $progressBar.addClass("is-flowing");
                $progressBar.css("clip-path", "inset(0 100% 0 0)");

                function updateProgress() {
                    const elapsedTime = Date.now() - startTime;
                    const progress = Math.min(elapsedTime / totalDuration, 1.0);

                    if (progress < 1.0) {
                        var newWidth = progress * 100;
                        $progressBar.css("clip-path", "inset(0 " + (100 - newWidth) + "% 0 0)");

                        const textIndex = Math.min(Math.floor(progress * steps.length), steps.length - 1);
                        if (steps[textIndex] && $progressText.text() !== steps[textIndex]) {
                            $progressText.text(steps[textIndex]);
                        }

                        self.timeoutId = setTimeout(updateProgress, updateInterval);
                    } else {
                        $progressBar.css("clip-path", "inset(0 0% 0 0)");
                        resolve();
                    }
                }
                updateProgress();
            });
        },

        destroy: function () {
            clearTimeout(this.timeoutId);
            this._super.apply(this, arguments);
        },
    });

    publicWidget.registry.ProgressBarWidget = ProgressBarWidget;

    return ProgressBarWidget;
});
