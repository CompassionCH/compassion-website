/*
 * Handles child pool filtering functionalities
 *
 * Used in /templates/pages/my2_sponsorships.xml
 */
document.addEventListener("DOMContentLoaded", function (event) {
    odoo.define("my_compassion.sponsorships", function (require) {
        "use strict";

        var publicWidget = require("web.public.widget");
        var rpc = require("web.rpc");

        publicWidget.registry.Sponsorships = publicWidget.Widget.extend({
            selector: ".sponsorships-body-container",

            events: {
                "change .SelectComponent": "_onCountryChange",
                'change input[type="radio"][name="gender"]': "_onGenderChange",
                "click #btn-more": "_onShowMore",
                "click #btn-choose": "_onChooseRandom",
            },

            custom_events: {
                range_changed: "_onRangeChange",
            },

            /**
             * @override
             */
            start: function () {
                var def = this._super.apply(this, arguments);

                // Create RangeInput element
                var rangeInputElement = this.$(".range-input-component");
                var rangeInput = new publicWidget.registry.RangeInput(this, 0, 18);
                rangeInput.replace(rangeInputElement);

                this.genderFilter = this.$("input[name=gender]:checked").val();
                this.ageFilter = { low: 0, high: 18 };
                this.countryFilter = this.$(".SelectComponent").find("option:selected").val();

                this.resultsPerBatch = 20;
                this.resultsLoaded = 0;
                this.totalResults = 0;

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
                this.resultsLoaded = 0;
                this.totalResults = 0;
                this._updateTotalResultsLabel();
                this._updateShowMoreButton();
                this._fetchSponsorships();
            },

            /**
             * Appends HTML to a container and applies a staggered animation.
             * * @param {string} htmlContent - The raw HTML string (e.g., data.html)
             * @param {jQuery} $container  - The jQuery object to append to (e.g., $resultsContainer)
             */
            _appendAndAnimate: function (htmlContent, $container) {
                // 1. Create jQuery objects from the HTML and add the initial class
                const $newItems = $(htmlContent).addClass("animate-in");

                // 2. Append the new results to the container
                $container.append($newItems);

                // 3. Loop over each new item to apply the staggered delay
                $newItems.each(function (index) {
                    var self = this;
                    // Apply 100ms base delay + 50ms per item
                    setTimeout(function () {
                        $(self).addClass("show");
                    }, 100 + index * 50);
                });
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

                rpc.query({
                    route: "/my2/sponsorships/fetch",
                    params: {
                        limit: this.resultsPerBatch,
                        offset: this.resultsLoaded,
                        gender: this.genderFilter,
                        age_min: this.ageFilter.low,
                        age_max: this.ageFilter.high,
                        country: this.countryFilter,
                        sponsorship_type: this.sponsorship_type,
                        global_pool: global_pool,
                    },
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
                    .guardedCatch(
                        function () {
                            // Re-enable buttons and remove spinner in case of error
                            this.$(".btn").prop("disabled", false);
                            $spinner.remove();
                        }.bind(this)
                    );
            },

            /**
             * Updates the total number of results reported by the label.
             * @private
             */
            _updateTotalResultsLabel: function () {
                this.$("#total-results").text(this.totalResults);
            },

            /**
             * Hides the "Choose for me" button if no results are found.
             * @private
             */
            _updateChooseForMeButton: function () {
                if (this.totalResults == 0) {
                    this.$("#btn-choose").hide();
                } else {
                    this.$("#btn-choose").show().prop("disabled", false);
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
             * Handles the custom 'range_changed' event from the range input widget.
             * @private
             * @param {OdooEvent} ev The Odoo event object, which contains the data payload.
             */
            _onRangeChange: function (ev) {
                // The data payload from trigger_up is available in ev.data
                this.ageFilter = ev.data;
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

                rpc.query({
                    route: "/my2/sponsorships/fetch-random",
                    params: {
                        gender: this.genderFilter,
                        age_min: this.ageFilter.low,
                        age_max: this.ageFilter.high,
                        country: this.countryFilter,
                    },
                })
                    .then(
                        function (data) {
                            if (data.child_id) {
                                // Delete all the current results
                                this.$(".sponsorships-results-content").empty();
                                this._appendAndAnimate(data.html, this.$(".sponsorships-results-content"));
                            }
                            this.$(".btn").prop("disabled", false);
                        }.bind(this)
                    )
                    .guardedCatch(
                        function () {
                            // Re-enable buttons in case of error
                            this.$(".btn").prop("disabled", false);
                        }.bind(this)
                    );
            },
        });

        return publicWidget.registry.Sponsorships;
    });
});
