odoo.define('my_compassion.my2_letters_filter', function (require) {
    'use strict';

    var ajax = require('web.ajax');

    $(function() {
        console.log('DOM ready');
        var isNewestFirst = true;

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