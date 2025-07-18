/**
 * Handles the dropdowns in the my2_child_letters.xml page's modal
 * Is used in /templates/pages/my2_child_letters.xml
 *
 */

document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('filterModal');
    const allLetters = Array.from(document.querySelectorAll('#lettersContainer > div'));

    let filterYearFrom = null;
    let filterYearTo = null;
    let filterMonthFrom = null;
    let filterMonthTo = null;

    const monthToNumberMap = {
        January: 1, February: 2, March: 3, April: 4,
        May: 5, June: 6, July: 7, August: 8,
        September: 9, October: 10, November: 11, December: 12
    };

    const okBtn = document.getElementById('filterOkBtn');
    const cancelBtn = document.getElementById('filterCancelBtn');

    // Registers the variables chosen in the dropdowns
    document.querySelectorAll('#yearDropdownFrom + .dropdown-menu .dropdown-item').forEach(function (item) {
        item.addEventListener('click', function (e) {
            e.preventDefault();
            filterYearFrom = this.textContent.trim();
            document.getElementById('yearDropdownFrom').textContent = filterYearFrom;
        });
    });
    document.querySelectorAll('#yearDropdownTo + .dropdown-menu .dropdown-item').forEach(function (item) {
        item.addEventListener('click', function (e) {
            e.preventDefault();
            filterYearTo = this.getAttribute('data-year');
            document.getElementById('yearDropdownTo').textContent = filterYearTo;
        });
    });
    document.querySelectorAll('#monthDropdownFrom + .dropdown-menu .dropdown-item').forEach(function (item) {
        item.addEventListener('click', function (e) {
            e.preventDefault();
            filterMonthFrom = this.textContent.trim();
            document.getElementById('monthDropdownFrom').textContent = filterMonthFrom;
        });
    });
    document.querySelectorAll('#monthDropdownTo + .dropdown-menu .dropdown-item').forEach(function (item) {
        item.addEventListener('click', function (e) {
            e.preventDefault();
            filterMonthTo = this.textContent.trim();
            document.getElementById('monthDropdownTo').textContent = filterMonthTo;
        });
    });

    // Managing of the buttons
    if (okBtn) {
        okBtn.addEventListener('click', function () {
            const letters = allLetters;
            const sortNewestFirst = (document.querySelector('input[name="sortOptions"]:checked')?.value || 'newest') == 'newest';
            let selectedType = document.querySelector('input[name="typeOptions"]:checked')?.value;

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

            letters.forEach(card => {
                const cardDate = new Date(card.dataset.create_date);
                const inRange = cardDate >= fromDate && cardDate <= toDate;
                const rightType = card.dataset.type == selectedType || !selectedType;
                card.style.display = (inRange &&  rightType)? 'block' : 'none';
            });

            letters.sort((a, b) => {
                const dateA = new Date(a.dataset.create_date);
                const dateB = new Date(b.dataset.create_date);
                return sortNewestFirst ? dateB - dateA : dateA - dateB;
            });

            const container = document.getElementById('lettersContainer');
            container.innerHTML = '';
            letters.forEach(el => container.appendChild(el));
        });
    }
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function (e) {
            const letters = allLetters;

            filterYearFrom = null;
            filterYearTo = null;
            filterMonthFrom = null;
            filterMonthTo = null;

            document.getElementById('yearDropdownFrom').textContent = "Year";
            document.getElementById('yearDropdownTo').textContent = "Year";
            document.getElementById('monthDropdownFrom').textContent = "Month";
            document.getElementById('monthDropdownTo').textContent = "Month";

            const container = document.getElementById('lettersContainer');
            container.innerHTML = '';
            allLetters.forEach(el => {
                el.style.display = 'block';
                container.appendChild(el);
            });
        });
    }
});