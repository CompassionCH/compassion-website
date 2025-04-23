odoo.define('my_compassion.my2_letters_filter', function (require) {
    'use strict';

    var ajax = require('web.ajax');

    $(function() {
        console.log('DOM ready');

        // Simple click handlers
        $('#filter-from, #filter-to').click(function(e) {
            e.preventDefault();
            var direction = $(this).data('direction');
            var $container = $('.my2-letters-container');
            var childId = $container.attr('data-child-id');

            console.log('Filter clicked:', {
                direction: direction,
                childId: childId,
                buttonId: this.id
            });

            if (!childId) {
                console.error('No child ID found');
                return;
            }

            $container.html('<p class="text-center">Loading...</p>');

            ajax.jsonRpc(`/my2/children/${childId}/filter_${direction}`, 'call', {})
                .then(function(result) {
                    console.log('Response received');
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