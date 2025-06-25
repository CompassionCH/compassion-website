document.addEventListener("DOMContentLoaded", function () {
    odoo.define("my_compassion.letters_filter", function (require) {
        "use strict";

        // Ajax utility for making RPC calls
        const ajax = require("web.ajax");

        // Import Qweb to render templates
        const core = require('web.core');
        const qweb = core.qweb;
        const $container = $(".my2-letters-container");

        // Constants for date filtering dropdown options
        const MONTHS = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ];
        const CURRENT_YEAR = new Date().getFullYear();
        const CURRENT_MONTH = new Date().getMonth() + 1;
        let START_YEAR;
        let START_MONTH;
        let startDateFilter;
        let endDateFilter;
        // Default sort order
        let isNewestFirst = true;
        let currentDirection = null;

        // Store letters in a global variable
        let originalLetterList = []; 
        // This will be used to store the filtered letters
        let letters = [];


        /**
         * Fetch letters for a specific child from the server using an AJAX call.
         * 
         * @param {number} childId The ID of the child we want to fetch letters for.
         * @param {Object} $container A reference to the container where we can display 
         * an error message if needed.
         * @returns The list of letters, or an empty array if there was an error.
         */
        async function importLetter(childId, $container) {
            try {
                const result = await ajax.jsonRpc(`/my2/children/${childId}/get_letters`, "call", {});
                if (result?.letters) {
                    return result.letters;
                }
            } catch (error) {
                console.error("Ajax error:", error);
                $container.html(
                    '<p class="text-danger text-center">Error loading letters</p>'
                );
            }
            return [];
        }

        /**
         * Import letters and initialize the letters list.
         */
        async function initializeLetters() {
            // Retrieve the child ID to import letters for
            const childId = $container.attr("data-child-id");

            originalLetterList = await importLetter(childId, $container);        
            if (originalLetterList.length > 0) {
                // Add a field date to each letter retrieved from scanned date
                originalLetterList.forEach((letter) =>
                    letter.date = new Date(letter.scanned_date)
                );
                letters = originalLetterList.slice(); // Copy the original list
            }
        }

        /**
         * Set up constants from the letters, populate the date filter options,
         * and set default values for the date filter.
         */
        function initializeDateFilter() {
            // Retrieve start year and month on letters
            if (letters.length > 0) {
                let startDate = letters.at(-1)?.scanned_date;
                if (startDate) {
                    START_YEAR = new Date(startDate).getFullYear();
                    START_MONTH = new Date(startDate).getMonth() + 1;
                }

                // Populate year options
                const yearOptions = getYearOptions(START_YEAR, CURRENT_YEAR);
                $(".start-year, .end-year").html(yearOptions);
                // Populate month options
                $(".start-month").html(getMonthOptions(START_MONTH));
                $(".end-month").html(getMonthOptions(1, CURRENT_MONTH));
                // Set default values
                $(".start-year").val(START_YEAR);
                $(".start-month").val(START_MONTH);
                $(".end-year").val(CURRENT_YEAR);
                $(".end-month").val(CURRENT_MONTH);
    
                startDateFilter = new Date(START_YEAR, START_MONTH - 1, 1);
                endDateFilter = new Date(CURRENT_YEAR, CURRENT_MONTH, 0); // Last day of the month
            }
        }

        /**
        * Entry point for the filtering.
        * Initializes the letters, loads the XML template, sets up the date filter,
        * and renders the letters.
        */  
        async function init(){
            await initializeLetters();
            await ajax.loadXML('/my_compassion/static/src/xml/my2_letter_card.xml', qweb);
            initializeDateFilter();
            renderLetters();
        }


        /**
         * Applies date filtering based on the selected start and end dates.
         * Once the filter is applied, it displays the letters.
         */
        function applyFilter() {
            // Filter letters based on the selected date range
            // Start from the original list
            letters = originalLetterList.slice();
            if (!isNewestFirst) {
                letters.reverse();
            }

            // Apply date filter
            letters = letters.filter((letter) => 
                startDateFilter <= letter.date && letter.date <= endDateFilter );
            
            // Filter according to current direction
            if (currentDirection) {
                letters = letters.filter((letter) =>
                    letter.direction === currentDirection
                );
            }  
            renderLetters();
        }

        /**
         * Renders the letters in the container using the Qweb template.
         */ 
        function renderLetters() {
            $container.empty();
            letters.forEach((letter) => {
                const letterCard = qweb.render("my_compassion.my2_letter_card_component", {
                    letter: letter,
                });
                $container.append(letterCard);
            });

        }

        /**
         * Populates the year options for the date filter.
         *
         * @param {number} startYear Starting year for the options.
         * @param {number} endYear Ending year for the options.
         * @returns A string of HTML option elements for years from startYear to endYear.
         */
        function getYearOptions(startYear, endYear) {
            return Array.from({ length: endYear - startYear + 1 }, (_, i) => endYear - i)
            .map((year) => `<option value="${year}">${year}</option>`)
            .join("");
        }


        /**
         * Populates the month options for the date filter.
         *
         * @param {number} startMonth Starting month for the options (1-12).
         * @param {number} endMonth Ending month for the options (1-12).
         * @returns A string of HTML option elements for months from startMonth to endMonth.
         */
        function getMonthOptions(startMonth = 1, endMonth = 12) {
            return MONTHS
            .slice(startMonth - 1, endMonth)
            .map((month, i) => `<option value="${i + startMonth}">${month}</option>`)
            .join("");
        }


        // Event handlers
        // Handle the change event on start date or end date
        $(".start-year, .start-month, .end-year, .end-month").change(function () {
            // Get the selected values from the dropdowns
            let startYear = parseInt($(".start-year").val());
            let startMonth = parseInt($(".start-month").val());
            let endYear = parseInt($(".end-year").val());
            let endMonth = parseInt($(".end-month").val());

            //Handle the constraints
            // 1) Start month constraint
            let startMonthMin = (startYear === START_YEAR) ? START_MONTH : 1;
            let startMonthMax = (startYear === CURRENT_YEAR) ? CURRENT_MONTH : 12;

            // 2) End month constraint
            let endMonthMin = (endYear === START_YEAR) ? START_MONTH : 1;
            let endMonthMax = (endYear === CURRENT_YEAR) ? CURRENT_MONTH : 12;


            // 3) By changing the “year” filter, we could end up with an inconsistent month.
            // We clamp to avoid that.
            startMonth = Math.min(Math.max(startMonth, startMonthMin), startMonthMax);
            endMonth = Math.min(Math.max(endMonth, endMonthMin), endMonthMax);

            // 4) Do not let start month range and end month range intersect when startYear == endYear
            if (startYear === endYear){
                // Check that the start month is before the end month
                if (startMonth > endMonth) {
                    startMonth = endMonth;
                }
                startMonthMax = Math.min(startMonthMax, endMonth);
                endMonthMin = Math.max(endMonthMin, startMonth);
            }

            const startMonthHtml = getMonthOptions(startMonthMin, startMonthMax);
            const endMonthHtml = getMonthOptions(endMonthMin, endMonthMax);

            $(".start-month").html(startMonthHtml).val(startMonth);
            $(".end-month").html(endMonthHtml).val(endMonth);

            const startYearHtml = getYearOptions(START_YEAR, endYear)
            const endYearHtml = getYearOptions(startYear, CURRENT_YEAR)

            $(".start-year").html(startYearHtml).val(startYear)
            $(".end-year").html(endYearHtml).val(endYear)

            startDateFilter = new Date(startYear, startMonth - 1, 1);
            endDateFilter = new Date(endYear, endMonth, 0); // Last day of the month

            applyFilter();
        });


        // Handle Received and Sent buttons
        // From: Supporter to Beneficiary (Received button)
        // To: Beneficiary to Supporter (Sent button)
        $("#filter-from, #filter-to").click(function (e) {
            e.preventDefault();
            let $this = $(this);
            // Toggle button state
            $this.toggleClass("active inactive");
            let fromActive = $("#filter-from").hasClass("active");
            let toActive = $("#filter-to").hasClass("active");
            currentDirection = null;
            // Update current direction based on button states
            if (fromActive !== toActive) {
            currentDirection = fromActive
                ? "Supporter To Beneficiary"
                : "Beneficiary To Supporter";
            }
            applyFilter();
        });

        // Handle the sort order button
        $("#toggle-date-order").click(function () {
            isNewestFirst = !isNewestFirst;
            $(this).text(isNewestFirst ? "Newest First" : "Oldest First");
            $(this).toggleClass("active inactive");
            // As letters are already sorted, we can just reverse them;
            letters.reverse();
            renderLetters();
        });

        // Call the initialization
        init();

  });
});