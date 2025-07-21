/**
 * Handles the dropdowns in the my2_child_letters.xml page's modal
 * Is used in /templates/pages/my2_child_letters.xml
 *
 */

document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('filterModal');
    const allLetters = Array.from(document.querySelectorAll('#lettersContainer > div'));

    const monthToNumberMap = {
        January: 1, February: 2, March: 3, April: 4,
        May: 5, June: 6, July: 7, August: 8,
        September: 9, October: 10, November: 11, December: 12
    };

    const okBtn = document.getElementById('filterOkBtn');
    const cancelBtn = document.getElementById('filterCancelBtn');

    // Apply filters and sorting when OK is clicked
    if (okBtn) {
        okBtn.addEventListener('click', function () {
            const letters = allLetters;

            const filterYearFrom = document.getElementById('yearDropdownFrom')?.value;
            const filterYearTo = document.getElementById('yearDropdownTo')?.value;
            const filterMonthFrom = document.getElementById('monthDropdownFrom')?.value;
            const filterMonthTo = document.getElementById('monthDropdownTo')?.value;

            const sortNewestFirst = (document.querySelector('input[name="sortOptions"]:checked')?.value || 'newest') === 'newest';
            const selectedType = document.querySelector('input[name="typeOptions"]:checked')?.value;

            const fromDate = new Date(
                parseInt(filterYearFrom || '1900'),
                (monthToNumberMap[filterMonthFrom] || 1) - 1,
                1
            );

            const toDate = new Date(
                parseInt(filterYearTo || '2100'),
                (monthToNumberMap[filterMonthTo] || 12) - 1,
                31
            );

            // Filter cards by date and type
            letters.forEach(card => {
                const cardDate = new Date(card.dataset.create_date);
                const inRange = cardDate >= fromDate && cardDate <= toDate;
                const rightType = card.dataset.type === selectedType || !selectedType;
                card.style.display = (inRange && rightType) ? 'block' : 'none';
            });

            // Sort cards by creation date
            letters.sort((a, b) => {
                const dateA = new Date(a.dataset.create_date);
                const dateB = new Date(b.dataset.create_date);
                return sortNewestFirst ? dateB - dateA : dateA - dateB;
            });

            // Update the filter count
            //let filtersCount = 0;
//
            //if (filterYearFrom) filtersCount++;
            //if (filterMonthFrom) filtersCount++;
            //if (filterYearTo) filtersCount++;
            //if (filterMonthTo) filtersCount++;
            //if (selectedType) filtersCount++;

            //let filterBtn = document.querySelector('a[data-target="#filterModal"] button');
            //if (filterBtn) {
            //    if (filtersCount > 0) {
            //        const baseLabel = '';
            //        filterBtn.querySelectorAll('span')[1].textContent = filtersCount > 0 ? `+${filtersCount}` : baseLabel;
            //    }
            //}

            // Re-render filtered and sorted cards
            const container = document.getElementById('lettersContainer');
            container.innerHTML = '';
            letters.forEach(el => container.appendChild(el));
        });
    }

    // Reset filters and restore default state
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function () {
            document.getElementById('yearDropdownFrom').selectedIndex = 0;
            document.getElementById('yearDropdownTo').selectedIndex = 0;
            document.getElementById('monthDropdownFrom').selectedIndex = 0;
            document.getElementById('monthDropdownTo').selectedIndex = 0;

            const container = document.getElementById('lettersContainer');
            container.innerHTML = '';
            allLetters.forEach(el => {
                el.style.display = 'block';
                container.appendChild(el);
            });
        });
    }
});
