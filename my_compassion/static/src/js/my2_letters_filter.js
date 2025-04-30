/**
 * Filters and displays child letters with date and direction options.
 * Is used in /templates/pages/my2_child_letters.xml
 *
 */
odoo.define("my_compassion.my2_letters_filter", function (require) {
  "use strict";

  var ajax = require("web.ajax");

  $(function () {
    // Initialize variables
    var isNewestFirst = true;
    var $container = $(".my2-letters-container");
    var childId = $container.attr("data-child-id");
    var currentDirection = null;

    /**
     * Display letters in container
     */
    function displayLetters(letters) {
      $container.empty();
      letters.forEach((letter) => $container.append(letter.html));
    }

    /**
     * Apply all filters together
     */
    function applyAllFilters() {
      var startMonth = parseInt($(".start-month").val());
      var startYear = parseInt($(".start-year").val());
      var endMonth = parseInt($(".end-month").val());
      var endYear = parseInt($(".end-year").val());

      var startDate = `${startYear}-${String(startMonth).padStart(2, "0")}-01`;
      var endDate = `${endYear}-${String(endMonth).padStart(2, "0")}-${new Date(
        endYear,
        endMonth,
        0
      ).getDate()}`;

      $container.html('<p class="text-center">Loading...</p>');

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
     * Update end date options
     */
    function updateEndDateOptions(startMonth, startYear) {
      var currentYear = new Date().getFullYear();
      var currentMonth = new Date().getMonth() + 1;

      var years = [];
      for (var year = currentYear; year >= startYear; year--) {
        years.push(`<option value="${year}">${year}</option>`);
      }
      $(".end-year").html(years.join(""));

      var months = [
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

      var monthsHtml =
        startYear === parseInt($(".end-year").val())
          ? months
              .slice(startMonth - 1)
              .map(
                (month, i) =>
                  `<option value="${i + startMonth}">${month}</option>`
              )
              .join("")
          : months
              .map((month, i) => `<option value="${i + 1}">${month}</option>`)
              .join("");

      $(".end-month").html(monthsHtml);

      // Set default end date
      $(".end-month").val(
        startYear === currentYear
          ? Math.max(startMonth, Math.min(currentMonth, 12))
          : 12
      );
      $(".end-year").val(currentYear);
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
          var currentYear = new Date().getFullYear();
          var minYear = minDate.getFullYear();

          // Populate months dropdown
          var months = [
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
          var monthsHtml = months
            .map(
              (month, index) => `<option value="${index + 1}">${month}</option>`
            )
            .join("");
          $(".start-month, .end-month").html(monthsHtml);

          // Populate years dropdown
          var yearsCount = currentYear - minYear + 1;
          var years = Array.from(
            { length: yearsCount },
            (_, i) => currentYear - i
          );
          var yearsHtml = years
            .map((year) => `<option value="${year}">${year}</option>`)
            .join("");
          $(".start-year, .end-year").html(yearsHtml);

          // Set initial values
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
