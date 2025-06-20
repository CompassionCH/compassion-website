document.addEventListener("DOMContentLoaded", function () {
    odoo.define("my_compassion.letters_filter", function (require) {
        "use strict";

        // Owl components and utilities
        const { Component, mount, useState} = owl;
        const { xml } = owl.tags;
        const OwlLetterCard = require("my_compassion.OwlLetterCard");
        let owlLetterList;

        // Ajax utility for making RPC calls
        const ajax = require("web.ajax");

        // Constants for date filtering dropdown options
        const MONTHS = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ];
        const CURRENT_YEAR = new Date().getFullYear();
        const CURRENT_MONTH = new Date().getMonth() + 1;
        // Store global values to avoid to recompute them unless it's needed
        let START_YEAR;
        let START_MONTH;
        let startDateFilter;
        let endDateFilter;
        // Default sort order
        let isNewestFirst = true;
        let currentDirection = null;

            
        /**
         * Owl component for displaying a list of letters.
         * This component renders a list of letter cards using the OwlLetterCard component.
         */
        class OwlLetterList extends Component {
            static template = xml`
            <div>
                <t t-foreach="state.letters" t-as="letter" t-key="letter.uuid">
                    <div class="col-12 mx-auto mb-2">
                        <OwlLetterCard letter="letter"/>
                    </div>
                </t>
          </div>`
          ;

            static components = {OwlLetterCard};

        constructor() {
            super(...arguments);
            this.state = useState({
                letters: this.props.letters || []
            });
        }

        // Method to update the letters (and thereby re-render the component)
        setLetters(newLetters) {
            this.state.letters = newLetters;
        }

        get letters(){
            return this.state.letters;
        }

        // Getter to access the original letter list
        // This returns a copy of the original letter list to avoid direct mutation
        get originalLetterList(){
            return this.props.originalLetterList.slice();
        }
    }

        // Fetch letters from the backend
        async function importLetter(childId, $container) {
            try {
                const result = await ajax.jsonRpc(`/my2/children/${childId}/get_letters`, "call", {});
                if (result && result.letters) {
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

        // Initialize and mount the component
        async function initializeComponent() {
            const $container = $(".my2-letters-container");
            // You may want to get childId from a global variable or DOM
            const childId = $container.attr("data-child-id");
            let letters = await importLetter(childId, $container);        
            if (letters.length > 0) {
                // Add a field date to each letter retrieved from scanned date
                letters.forEach((letter) =>
                    letter.date = new Date(letter.scanned_date)
                );               

                owlLetterList = await mount(OwlLetterList, {
                    target: $container[0],
                    props: { 
                        letters: letters,
                        originalLetterList: letters // Store the original list before filtering
                    },
                }); 
            }
        }

        /**
         * Set up constants from the letters, populate the date filter options,
         * and set default values for the date filter.
         */
        function initializeDateFilter() {
            // Retrieve start year and month on letters
            if (owlLetterList){
                let startDate = owlLetterList.letters.at(-1)?.scanned_date;
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
        * Initialize the owl Component and the date picker
        */  
        async function init(){
            await initializeComponent();
            initializeDateFilter();
        }


        /**
         * Applies date filtering based on the selected start and end dates.
         *
         */
        function applyFilter() {
            // Filter letters based on the selected date range
            // Start from the original list
            let letters = owlLetterList.originalLetterList;
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

            owlLetterList.setLetters(letters);    
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
            // Retrive the triggered element
            let changedElement = $(this).attr("class");
            console.log("Changed element:", changedElement);
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
            owlLetterList.letters.reverse();
        });

        // Call the initialization
        init();

  });
});