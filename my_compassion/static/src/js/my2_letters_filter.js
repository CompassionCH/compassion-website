odoo.define('my_compassion.my2_letters_filter', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var core = require('web.core');
        var DateRangePicker = core.serviceRegistry.get('my_compassion.my2_date_picker');
        console.log('DateRangePicker:', DateRangePicker);

    $(function() {
        console.log('DOM ready');
        var isNewestFirst = true;var $container = $('.my2-letters-container');
        console.log('Container found:', $container.length);
        var childId = $container.attr('data-child-id');
        console.log('Child ID:', childId);

        // Get minimum date and populate dropdowns
        function initializeDatePickers() {
            return ajax.jsonRpc(`/my2/children/${childId}/get_min_date`, 'call', {})
                .then(function(result) {
                    var minDate = result.min_date ? new Date(result.min_date) : new Date();
                    var currentYear = new Date().getFullYear();
                    var minYear = minDate.getFullYear();

                    // Populate months
                    var months = ['January', 'February', 'March', 'April', 'May', 'June',
                                 'July', 'August', 'September', 'October', 'November', 'December'];
                    var monthsHtml = months.map(function(month, index) {
                        return `<option value="${index + 1}">${month}</option>`;
                    }).join('');
                    $('.start-month, .end-month').html(monthsHtml);

                    // Populate years from min date to current
                    var yearsCount = currentYear - minYear + 1;
                    var years = Array.from({length: yearsCount}, (_, i) => currentYear - i);
                    var yearsHtml = years.map(function(year) {
                        return `<option value="${year}">${year}</option>`;
                    }).join('');
                    $('.start-year, .end-year').html(yearsHtml);

                    // Set default values
                    var now = new Date();
                    $('.start-month').val(now.getMonth() + 1);
                    $('.start-year').val(now.getFullYear());
                    $('.end-month').val(now.getMonth() + 1);
                    $('.end-year').val(now.getFullYear());

                    console.log('Date-pickers initialized');
                    return true;
                });
        }

        // Initialize in sequence
        initializeDatePickers().then(function() {

            if (DateRangePicker) {
                var datePicker = new DateRangePicker(null, {
                    childId: childId,
                    onDateChange: function(dates) {
                        console.log('Date changed:', dates);
                        if (dates) {
                            filterLettersByDate(dates.start_date, dates.end_date);
                        } else {
                            loadAllLetters();
                        }
                    }
                });
                console.log('DatePicker instance created');
                datePicker.appendTo('.date-picker-container');
                console.log('DatePicker appended to container');
            }
        });

        function filterLettersByDate(startDate, endDate) {
            $container.html('<p class="text-center">Loading...</p>');
            ajax.jsonRpc(`/my2/children/${childId}/filter_letters_by_date`, 'call', {
                start_date: startDate,
                end_date: endDate
            })
            .then(function(result) {
                if (result && result.letters && result.letters.length) {
                    displayLetters(result.letters);
                } else {
                    $container.html('<p class="text-center">No letters found in this date range</p>');
                }
            });
        }

        // Set initial state and load all letters
        $('#filter-from, #filter-to').removeClass('active').addClass('inactive');
        $('#toggle-date-order').removeClass('active').addClass('inactive');
        loadAllLetters();

        function loadAllLetters() {
            var $container = $('.my2-letters-container');
            var childId = $container.attr('data-child-id');

            if (childId) {
                $container.html('<p class="text-center">Loading...</p>');

                ajax.jsonRpc(`/my2/children/${childId}/get_all_letters`, 'call', {})
                    .then(function(result) {
                        if (result && result.letters && result.letters.length) {
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

        function displayLetters(letters) {
            var $container = $('.my2-letters-container');
            $container.empty();

            // Sort letters based on current order
            letters.sort(function(a, b) {
                var dateA = new Date(a.scanned_date);
                var dateB = new Date(b.scanned_date);
                return isNewestFirst ? dateB - dateA : dateA - dateB;
            });

            letters.forEach(function(letter) {
                $container.append(letter.html);
            });
        }

        // Date order toggle handler
        $('#toggle-date-order').click(function() {
            isNewestFirst = !isNewestFirst;
            $(this).text(isNewestFirst ? 'Newest First' : 'Oldest First');
            $(this).toggleClass('active inactive');

            // Reorder current letters
            var $container = $('.my2-letters-container');
            var letters = $container.children().toArray();
            letters.reverse();
            $container.append(letters);
        });

        $('#filter-from, #filter-to').click(function(e) {
            e.preventDefault();
            var $this = $(this);
            var $container = $('.my2-letters-container');
            var childId = $container.attr('data-child-id');

            // Toggle this button's state
            $this.toggleClass('active inactive');

            var fromActive = $('#filter-from').hasClass('active');
            var toActive = $('#filter-to').hasClass('active');

            // If no button is active, show all letters
            if (!fromActive && !toActive) {
                loadAllLetters();
                return;
            }

            // If both buttons are active, show filtered letters for both directions
            if (fromActive && toActive) {
                loadAllLetters();
                return;
            }

            // Otherwise filter based on active button
            var direction = fromActive ? 'supporter_to_beneficiary' : 'beneficiary_to_supporter';

            $container.html('<p class="text-center">Loading...</p>');

            ajax.jsonRpc(`/my2/children/${childId}/filter_${direction}`, 'call', {})
                .then(function(result) {
                    if (result && result.letters && result.letters.length) {
                        $container.empty();
                        result.letters.forEach(function(letter) {
                            $container.append(letter.html);
                        });
                    } else {
                        $container.html('<p class="text-center">No letters found</p>');
                    }
                })
                .guardedCatch(function(error) {
                    console.error('Ajax error:', error);
                    $container.html('<p class="text-danger text-center">Error loading letters</p>');
                });
        });
    });
});