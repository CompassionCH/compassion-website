odoo.define('my_compassion.my2_letters_filter', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var core = require('web.core');

    $(function() {
        // Initialize variables
        var isNewestFirst = true;
        var $container = $('.my2-letters-container');
        var childId = $container.attr('data-child-id');

        /**
         * Initialize date pickers with available dates
         * Sets start date to earliest available date and end date to current date
         */
        function initializeDatePickers() {
            return ajax.jsonRpc(`/my2/children/${childId}/letter_dates`, 'call', {})
                .then(function(result) {
                    var minDate = result.min_date ? new Date(result.min_date) : new Date();
                    var currentYear = new Date().getFullYear();
                    var minYear = minDate.getFullYear();

                    // Populate months dropdown
                    var months = ['January', 'February', 'March', 'April', 'May', 'June',
                                'July', 'August', 'September', 'October', 'November', 'December'];
                    var monthsHtml = months.map(function(month, index) {
                        return `<option value="${index + 1}">${month}</option>`;
                    }).join('');
                    $('.start-month, .end-month').html(monthsHtml);

                    // Populate years dropdown
                    var yearsCount = currentYear - minYear + 1;
                    var years = Array.from({length: yearsCount}, (_, i) => currentYear - i);
                    var yearsHtml = years.map(function(year) {
                        return `<option value="${year}">${year}</option>`;
                    }).join('');
                    $('.start-year, .end-year').html(yearsHtml);

                    // Set initial values
                    $('.start-month').val(1);
                    $('.start-year').val(minYear);

                    var now = new Date();
                    updateEndDateOptions(1, minYear);

                    // Load initial letters
                    filterLettersByDate(1, minYear, now.getMonth() + 1, now.getFullYear());
                });
        }

        /**
         * Update end date options based on selected start date
         * Ensures end date cannot be before start date
         */
        function updateEndDateOptions(startMonth, startYear) {
            var currentYear = new Date().getFullYear();
            var currentMonth = new Date().getMonth() + 1;

            // Update end year options
            var yearsHtml = '';
            for (var year = currentYear; year >= startYear; year--) {
                yearsHtml += `<option value="${year}">${year}</option>`;
            }
            $('.end-year').html(yearsHtml);

            // Update end month options
            var months = ['January', 'February', 'March', 'April', 'May', 'June',
                         'July', 'August', 'September', 'October', 'November', 'December'];
            var monthsHtml = '';

            if (startYear === parseInt($('.end-year').val())) {
                // If same year, only show months after start month
                for (var i = startMonth - 1; i < months.length; i++) {
                    monthsHtml += `<option value="${i + 1}">${months[i]}</option>`;
                }
            } else {
                monthsHtml = months.map((month, index) =>
                    `<option value="${index + 1}">${month}</option>`
                ).join('');
            }
            $('.end-month').html(monthsHtml);

            // Set default end date
            if (startYear === currentYear) {
                $('.end-month').val(Math.max(startMonth, Math.min(currentMonth, 12)));
            } else {
                $('.end-month').val(12);
            }
            $('.end-year').val(currentYear);
        }

        /**
         * Filter letters by date range
         */
        function filterLettersByDate(startMonth, startYear, endMonth, endYear) {
            var startDate = `${startYear}-${String(startMonth).padStart(2, '0')}-01`;
            var endDate = `${endYear}-${String(endMonth).padStart(2, '0')}-${new Date(endYear, endMonth, 0).getDate()}`;

            return ajax.jsonRpc(`/my2/children/${childId}/filter_letters_by_date`, 'call', {
                start_date: startDate,
                end_date: endDate
            }).then(function(result) {
                if (result.letters) {
                    $('.my2-letters-container').empty();
                    result.letters.forEach(function(letter) {
                        $('.my2-letters-container').append(letter.html);
                    });
                }
            });
        }

        /**
         * Load all letters without filtering
         */
        function loadAllLetters() {
            if (childId) {
                $container.html('<p class="text-center">Loading...</p>');
                ajax.jsonRpc(`/my2/children/${childId}/get_all_letters`, 'call', {})
                    .then(function(result) {
                        if (result?.letters?.length) {
                            displayLetters(result.letters);
                        } else {
                            $container.html('<p class="text-center">No letters found</p>');
                        }
                    })
                    .guardedCatch(function(error) {
                        console.error('Ajax error:', error);
                        $container.html('<p class="text-danger text-center">Error loading letters</p>');
                    });
            }
        }

        /**
         * Display letters in container with current sort order
         */
        function displayLetters(letters) {
            $container.empty();
            letters.sort((a, b) => {
                var dateA = new Date(a.scanned_date);
                var dateB = new Date(b.scanned_date);
                return isNewestFirst ? dateB - dateA : dateA - dateB;
            }).forEach(letter => $container.append(letter.html));
        }

        // Event Handlers
        $('.start-month, .start-year').on('change', function() {
            var startMonth = parseInt($('.start-month').val());
            var startYear = parseInt($('.start-year').val());
            updateEndDateOptions(startMonth, startYear);

            var endMonth = parseInt($('.end-month').val());
            var endYear = parseInt($('.end-year').val());
            filterLettersByDate(startMonth, startYear, endMonth, endYear);
        });

        $('.end-month, .end-year').on('change', function() {
            var startMonth = parseInt($('.start-month').val());
            var startYear = parseInt($('.start-year').val());
            var endMonth = parseInt($('.end-month').val());
            var endYear = parseInt($('.end-year').val());
            filterLettersByDate(startMonth, startYear, endMonth, endYear);
        });

        // Initialize date pickers and load initial data
        initializeDatePickers();
    });
});