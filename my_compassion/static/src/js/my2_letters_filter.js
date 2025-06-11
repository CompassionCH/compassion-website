/**
 * Filters and displays child letters with date and direction options.
 * Is used in /templates/pages/my2_child_letters.xml
 *
 */
document.addEventListener("DOMContentLoaded", function () {
  odoo.define("my_compassion.my2_letters_filter", function (require) {
    "use strict";

    var ajax = require("web.ajax");

    $(function () {
      // Initialize variables
      var isNewestFirst = true;
      var $container = $(".my2-letters-container");
      var childId = $container.attr("data-child-id");
      var currentDirection = null;

      const MONTHS = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
      ];
      const CURRENT_YEAR = new Date().getFullYear();
      const CURRENT_MONTH = new Date().getMonth() + 1;

      // Utility to generate year options
      function getYearOptions(start, end) {
        return Array.from({ length: end - start + 1 }, (_, i) => end - i)
          .map((year) => `<option value="${year}">${year}</option>`)
          .join("");
      }

      // Utility to generate month options
      function getMonthOptions(startMonth = 1, months = MONTHS) {
        return months
          .slice(startMonth - 1)
          .map(
            (month, i) => `<option value="${i + startMonth}">${month}</option>`
          )
          .join("");
      }

      /**
       * Display letters in the container
       *
       * @param {Array} letters - Array of letter objects to display
       */
      function displayLetters(letters) {
        $container.empty();
        letters.forEach((letter) => $container.append(letter.html));
      }

      /**
       * Apply all filters and fetch letters based on selected criteria
       */
      function applyAllFilters() {
        var startMonth = parseInt($(".start-month").val());
        var startYear = parseInt($(".start-year").val());
        var endMonth = parseInt($(".end-month").val());
        var endYear = parseInt($(".end-year").val());

        var startDate = `${startYear}-${String(startMonth).padStart(
          2,
          "0"
        )}-01`;
        var endDate = `${endYear}-${String(endMonth).padStart(
          2,
          "0"
        )}-${new Date(endYear, endMonth, 0).getDate()}`;

        ajax
          .jsonRpc(`/my2/children/${childId}/filter_letters`, "call", {
            start_date: startDate,
            end_date: endDate,
            direction: currentDirection,
            sort_order: isNewestFirst ? "desc" : "asc",
          })
          .then(function (result) {
            if (result && result.letters && result.letters.length) {
              displayLetters(result.letters);
            } else {
              $container.html('<p class="text-center">No letters found</p>');
            }
          })
          .guardedCatch(function (error) {
            console.error("Ajax error:", error);
            $container.html(
              '<p class="text-danger text-center">Error loading letters</p>'
            );
          });
      }

      /**
       * Update end date options based on selected start date
       * @param {number} startMonth - Selected start month (1-12)
       * @param {number} startYear - Selected start year
       */
      function updateEndDateOptions(startMonth, startYear) {
        $(".end-year").html(getYearOptions(startYear, CURRENT_YEAR));
        var selectedEndYear = parseInt($(".end-year").val());

        var monthsHtml =
          startYear === selectedEndYear
            ? getMonthOptions(startMonth, MONTHS)
            : getMonthOptions(1, MONTHS);
        $(".end-month").html(monthsHtml);

        $(".end-month").val(
          startYear === CURRENT_YEAR
            ? Math.max(startMonth, Math.min(CURRENT_MONTH, 12))
            : 12
        );
        $(".end-year").val(CURRENT_YEAR);
      }

      /**
       * Initialize date pickers
       */
      function initializeDatePickers() {
        return ajax
          .jsonRpc(`/my2/children/${childId}/letter_dates`, "call", {})
          .then(function (result) {
            var minDate = result.min_date
              ? new Date(result.min_date)
              : new Date();
            var minYear = minDate.getFullYear();

            $(".start-month, .end-month").html(getMonthOptions(1, MONTHS));
            $(".start-year, .end-year").html(
              getYearOptions(minYear, CURRENT_YEAR)
            );

            $(".start-month").val(1);
            $(".start-year").val(minYear);

            updateEndDateOptions(1, minYear);
            applyAllFilters();
          });
      }

      // Date picker event handlers
      $(".start-month, .start-year").on("change", function () {
        var startMonth = parseInt($(".start-month").val());
        var startYear = parseInt($(".start-year").val());
        updateEndDateOptions(startMonth, startYear);
        applyAllFilters();
      });

      $(".end-month, .end-year").on("change", function () {
        applyAllFilters();
      });

      // Sort order toggle handler
      $("#toggle-date-order").click(function () {
        isNewestFirst = !isNewestFirst;
        $(this).text(isNewestFirst ? "Newest First" : "Oldest First");
        $(this).toggleClass("active inactive");
        applyAllFilters();
      });

      // Direction filter buttons handler
      $("#filter-from, #filter-to").click(function (e) {
        e.preventDefault();
        var $this = $(this);

        // Toggle button state
        $this.toggleClass("active inactive");

        var fromActive = $("#filter-from").hasClass("active");
        var toActive = $("#filter-to").hasClass("active");

        // Update current direction based on button states
        if ((!fromActive && !toActive) || (fromActive && toActive)) {
          currentDirection = null;
        } else {
          currentDirection = fromActive
            ? "supporter_to_beneficiary"
            : "beneficiary_to_supporter";
        }

        applyAllFilters();
      });

      // Initialize
      initializeDatePickers();
    });
  });
});
