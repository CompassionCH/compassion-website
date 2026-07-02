/** @odoo-module **/

/**
 * Step progress bar with animated flowing stripes.
 *
 * Renders a `.progress-bar-container` holding a `.progress` stripe element and a
 * `.progress-text` label. The stripe pattern, flow animation, and clip-path
 * reveal are driven by the stylesheet: the `density-<density>` class selects the
 * stripe density, the `--flow-speed` CSS variable sets the animation duration,
 * and the `is-flowing` class starts the flow. JS keeps the active step and
 * exposes the reveal width and label as computed values bound into the template.
 *
 * The bar is divided equally among `steps`; reaching step index `i` reveals
 * `(i + 1) / steps.length` of the bar and shows `steps[i]` as the label.
 *
 * Props:
 * - steps (string[], default ["Step 1".."Step 4"]): step labels; the bar is
 *   split equally among them.
 * - density (string, default "medium"): stripe density, one of "low", "medium",
 *   "high"; selects the `density-<density>` class.
 * - flowSpeed (string, default "4s"): CSS duration for the stripe flow animation.
 * - step (number, default 0): zero-based index of the active step, clamped to
 *   the bounds of `steps`.
 * - totalSteps (number, default steps.length): number of equal segments the bar
 *   is divided into.
 * - flowing (boolean, default true): initial state of the flow animation.
 *
 * Mounted declaratively via
 * `<owl-component name="theme_compassion_2025.ProgressBar" props='{...}'/>`.
 */
import {Component, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";

export class ProgressBar extends Component {
  static template = "theme_compassion_2025.ProgressBar";
  static props = {
    steps: {type: Array, element: String, optional: true},
    density: {type: String, optional: true},
    flowSpeed: {type: String, optional: true},
    step: {type: Number, optional: true},
    totalSteps: {type: Number, optional: true},
    flowing: {type: Boolean, optional: true},
  };
  static defaultProps = {
    steps: ["Step 1", "Step 2", "Step 3", "Step 4"],
    density: "medium",
    flowSpeed: "4s",
    step: 0,
    flowing: true,
  };

  setup() {
    this.state = useState({step: this.props.step, flowing: this.props.flowing});
  }

  /**
   * Number of equal segments the bar is divided into.
   */
  get totalSteps() {
    return this.props.totalSteps ?? this.props.steps.length;
  }

  /**
   * Active step index clamped to the bounds of the bar.
   */
  get currentStep() {
    const total = this.totalSteps;
    if (total === 0) {
      return 0;
    }
    return Math.max(0, Math.min(this.state.step, total - 1));
  }

  /**
   * Fraction of the bar revealed at the active step, as a percentage:
   * `(currentStep + 1) / totalSteps`.
   */
  get progressPct() {
    const total = this.totalSteps;
    if (total === 0) {
      return 0;
    }
    return ((this.currentStep + 1) / total) * 100;
  }

  /**
   * Label shown under the bar for the active step.
   */
  get progressText() {
    const steps = this.props.steps;
    return steps.length ? steps[this.currentStep] : "";
  }

  /**
   * `clip-path` inset that reveals the portion of the bar reached at the
   * active step.
   */
  get clipPath() {
    return `inset(0 ${100 - this.progressPct}% 0 0)`;
  }

  /**
   * Start the flow animation and reveal the first step.
   */
  startProgress() {
    this.state.flowing = true;
    this.goToStep(0);
  }

  /**
   * Move the bar to a specific step. The index is clamped via `currentStep`.
   * @param {Number} stepIndex zero-based index of the step to reveal.
   */
  goToStep(stepIndex) {
    this.state.step = stepIndex;
  }
}

registry
  .category("public_components")
  .add("theme_compassion_2025.ProgressBar", ProgressBar);
