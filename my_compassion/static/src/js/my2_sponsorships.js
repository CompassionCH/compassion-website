/** @odoo-module **/

/*
 * Handles child pool filtering functionalities
 *
 * Used in /templates/pages/my2_sponsorships.xml
 */

import {Component} from "@odoo/owl";
import publicWidget from "@web/legacy/js/public/public_widget";
import {rpc} from "@web/core/network/rpc";
import {mountComponent} from "@web/env";
import {RangeInput} from "@theme_compassion_2025/js/components/RangeInput";
import {toast} from "@my_compassion/js/toast_service";

export const Sponsorships = publicWidget.Widget.extend({
  selector: ".sponsorships-body-container",

  events: {
    "change .SelectComponent": "_onCountryChange",
    'change input[type="radio"][name="gender"]': "_onGenderChange",
    "click #btn-more": "_onShowMore",
    "click #btn-choose": "_onChooseRandom",
    "click #btn-choose-again": "_onChooseRandom",
    "click #btn-see-all-children": "_refreshResults",
  },

  /**
   * @override
   */
  start: function () {
    const def = this._super.apply(this, arguments);

    // Mount the theme RangeInput age slider. onRangeChange is a Function prop,
    // so this OWL public component is mounted imperatively rather than via an
    // <owl-component> JSON declaration. The container holds a server-rendered
    // loading skeleton (theme_compassion_2025.RangeInputLoadingComponent) that
    // is cleared before mounting the live slider.
    const rangeInputEl = this.el.querySelector(".range-input-component");
    if (rangeInputEl) {
      rangeInputEl.replaceChildren();
      mountComponent(RangeInput, rangeInputEl, {
        // Reuse the frontend env: mountComponent treats a missing env as a
        // new root and restarts services, which double-registers the global
        // main_components and throws. Component.env is set by the public root.
        env: Component.env,
        props: {
          min: 0,
          max: 18,
          initialMin: 0,
          initialMax: 18,
          minGap: 0,
          onRangeChange: (range) => {
            this.ageFilter = {low: range.min, high: range.max};
            this._refreshResults();
          },
        },
      });
    }

    const $genderInput = this.$("input[name=gender]:checked");
    this.genderFilter = $genderInput.length
      ? $genderInput.val()
      : this.$el.data("gender-filter") || "either";
    this.ageFilter = {low: 0, high: 18};

    const $countryInput = this.$(".SelectComponent").find("option:selected");
    this.countryFilter = $countryInput.length
      ? $countryInput.val()
      : this.$el.data("country-filter") || "";

    this.resultsPerBatch = this.$el.data("limit") || 20;
    this.resultsLoaded = 0;
    this.totalResults = 0;
    // Id of the randomly sampled child, mostly used to see if sampling happened and condition the UI (Button visibility)
    // If null, no child sampled. This is reset on each filter change.
    this.randomlySampledChildId = null;

    this.sponsorship_type = this.$el.data("sponsorship-type");

    this._fetchSponsorships();

    return def;
  },

  // --------------------------------------------------------------------------
  // Private Event Handlers
  // --------------------------------------------------------------------------

  /**
   * Refreshes the search results and applies new filters.
   * @private
   */
  _refreshResults: function () {
    this.$(".sponsorships-results-content").empty();
    this.randomlySampledChildId = null;
    this.resultsLoaded = 0;
    this.totalResults = 0;
    this._updateTotalResultsLabel();
    this._updateShowMoreButton();
    this._fetchSponsorships();
  },

  /**
   * Appends HTML to a container and applies a staggered animation.
   * @param {string} htmlContent - The raw HTML string (e.g., data.html)
   * @param {jQuery} $container  - The jQuery object to append to (e.g., $resultsContainer)
   */
  _appendAndAnimate: function (htmlContent, $container) {
    // 1. Create jQuery objects from the HTML and add the initial class
    const $newItems = $(htmlContent).addClass("animate-in");

    // 2. Append the new results to the container
    $container.append($newItems);

    // 3. Loop over each new item to apply the staggered delay
    $newItems.each(function (index) {
      const self = this;
      // Apply 100ms base delay + 50ms per item
      setTimeout(
        function () {
          $(self).addClass("show");
        },
        100 + index * 50
      );
    });
  },

  /**
   * Handles RPC errors by displaying the my_compassion2 error toast.
   *
   * @private
   * @param {Object} error The error object from .catch.
   * @param {jQuery} [$spinner] Optional spinner element to remove.
   */
  _handleError: function (error, $spinner) {
    this.$(".btn").prop("disabled", false);
    if ($spinner) $spinner.remove();
    if (error.event) error.event.preventDefault();

    // Display error toast
    toast.error(error.data?.message);
  },

  /**
   * Fetches and displays the next batch of sponsorships from the backend.
   * @private
   */
  _fetchSponsorships: function (global_pool = false) {
    // Disable buttons to avoid double clicks
    this.$(".btn").prop("disabled", true);

    const $resultsContainer = this.$(".sponsorships-results-content");
    const $spinner = $(
      '<div class="col-12 d-flex justify-content-center align-items-center my-3">' +
        '<div class="spinner-border text-core-blue" role="status">' +
        '<span class="sr-only">Loading...</span>' +
        "</div>" +
        "</div>"
    );

    // Add spinner while waiting for more results
    $resultsContainer.append($spinner);

    rpc("/my2/sponsorships/fetch", {
      limit: this.resultsPerBatch,
      offset: this.resultsLoaded,
      gender: this.genderFilter,
      age_min: this.ageFilter.low,
      age_max: this.ageFilter.high,
      country: this.countryFilter,
      sponsorship_type: this.sponsorship_type,
      global_pool: global_pool,
    })
      .then(
        function (data) {
          // Remove spinner
          $spinner.remove();

          if (data.count && data.html) {
            // Parse the HTML string into jQuery objects and add the initial animation class.
            this._appendAndAnimate(data.html, $resultsContainer);

            // Update the count of loaded results
            this.resultsLoaded += data.count;
            this.totalResults = data.total;

            // Update UI
            this._updateTotalResultsLabel();
            this._updateChooseForMeButton();
            this._updateShowMoreButton();

            // Re-enable buttons
            this.$(".btn").prop("disabled", false);
          } else {
            // Refetch using global pool if no results found
            if (!global_pool) {
              this._fetchSponsorships(true);
            } else {
              // No results found even in global pool, just update UI
              this.totalResults = 0;
              this._updateTotalResultsLabel();
              this._updateChooseForMeButton();
              this._updateShowMoreButton();
              this.$(".btn").prop("disabled", false);
            }
          }
        }.bind(this)
      )
      .catch((error) => this._handleError(error, $spinner));
  },

  /**
   * Updates the total number of results reported by the label.
   * @private
   */
  _updateTotalResultsLabel: function () {
    if (this.randomlySampledChildId) {
      // If a child has been randomly sampled, show the appropriate message
      this.$("#total-children-found-message").hide();
      this.$("#randomly-chosen-child-message").show();
    } else {
      this.$("#total-children-found-message").show();
      this.$("#randomly-chosen-child-message").hide();
      // Update the total results count
      this.$("#total-results").text(this.totalResults);
    }
  },

  /**
   * Hides the "Choose for me" button if no results are found.
   * @private
   */
  _updateChooseForMeButton: function () {
    if (this.randomlySampledChildId) {
      // A child has been randomly chosen
      this.$("#btn-choose").hide();
      this.$("#btn-choose-again").show();
      this.$("#btn-see-all-children").show();
    } else {
      // Normal view (all children or no results)
      this.$("#btn-choose-again").hide();
      this.$("#btn-see-all-children").hide();
      if (this.totalResults > 0) {
        this.$("#btn-choose").show().prop("disabled", false);
      } else {
        this.$("#btn-choose").hide();
      }
    }
  },

  /**
   * Hides the "Show more" button if all results have been loaded.
   * @private
   */
  _updateShowMoreButton: function () {
    if (this.resultsLoaded >= this.totalResults) {
      this.$("#btn-more").hide();
    } else {
      this.$("#btn-more").show().prop("disabled", false);
    }
  },

  /**
   * Handles the change event for the gender radio buttons.
   * @private
   * @param {Event} ev The jQuery event object.
   */
  _onGenderChange: function (ev) {
    this.genderFilter = this.$(ev.currentTarget).val();
    this._refreshResults();
  },

  /**
   * Handles the change event of the country select dropdown.
   * @private
   * @param {Event} ev The jQuery event object.
   */
  _onCountryChange: function (ev) {
    this.countryFilter = this.$(ev.currentTarget).find("option:selected").val();
    this._refreshResults();
  },

  /**
   * Handles the click event from the show more button.
   * @private
   * @param {Event} ev The jQuery event object.
   */
  _onShowMore: function (ev) {
    this._fetchSponsorships();
  },

  /**
   * Handles the click event from the choose for me button.
   * @private
   * @param {Event} ev The jQuery event object.
   */
  _onChooseRandom: function (ev) {
    // Disable buttons to avoid double clicks
    this.$(".btn").prop("disabled", true);

    rpc("/my2/sponsorships/fetch-random", {
      gender: this.genderFilter,
      age_min: this.ageFilter.low,
      age_max: this.ageFilter.high,
      country: this.countryFilter,
    })
      .then(
        function (data) {
          if (data.child_id) {
            this.randomlySampledChildId = data.child_id;
            this._updateChooseForMeButton();
            this._updateTotalResultsLabel();
            // Delete all the current results
            this.$(".sponsorships-results-content").empty();

            this._appendAndAnimate(data.html, this.$(".sponsorships-results-content"));
          }
          this.$(".btn").prop("disabled", false);
        }.bind(this)
      )
      .catch((error) => this._handleError(error));
  },
});

publicWidget.registry.Sponsorships = Sponsorships;
