/**
 * Handles the dropdowns in the my2_child_letters.xml page's modal
 * Is used in /templates/pages/my2_child_letters.xml
 *
 */

document.addEventListener('DOMContentLoaded', function () {
    // Reference to the filter modal
    const modal = document.getElementById('filterModal');
    // Get all letter elements inside lettersContainer
    const allLetters = Array.from(document.querySelectorAll('#lettersContainer > div'));

    // Mapping month names to numbers for date filtering
    const monthToNumberMap = {
        January: 1, February: 2, March: 3, April: 4,
        May: 5, June: 6, July: 7, August: 8,
        September: 9, October: 10, November: 11, December: 12
    };

    const okBtn = document.getElementById('filterOkBtn');
    const cancelBtn = document.getElementById('filterCancelBtn');

    // Handle child dropdown change - redirect to child-specific page
    const dropdown = document.getElementById('childrenDropdown');
    if (dropdown) {
        dropdown.addEventListener('change', function () {
            const selectedChildId = this.value;
            if (selectedChildId) {
                window.location.href = `/my2/children/letters/${selectedChildId}`;
            }
        });
    }

    // Pagination variables and elements
    const lettersPerPage = 24;
    let currentPage = 1;
    const totalPages = Math.ceil(allLetters.length / lettersPerPage);

    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');
    const pageIndicator = document.getElementById('pageIndicator');

    // Function to show letters for the current page only
    function showPage(page) {
        currentPage = page;

        // Hide all letters initially
        allLetters.forEach(el => el.style.display = 'none');

        // Calculate start and end indexes for current page slice
        const start = (currentPage - 1) * lettersPerPage;
        const end = start + lettersPerPage;

        // Show only letters in current page range
        allLetters.slice(start, end).forEach(el => el.style.display = 'block');

        // Update pagination buttons and page indicator
        if (prevBtn) prevBtn.disabled = currentPage === 1;
        if (nextBtn) nextBtn.disabled = currentPage === totalPages;
        if (pageIndicator) pageIndicator.textContent = `Page ${currentPage} of ${totalPages}`;
    }

    // Attach event listeners to pagination buttons if present
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentPage > 1) showPage(currentPage - 1);
        });
    }
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (currentPage < totalPages) showPage(currentPage + 1);
        });
    }

    // Show the first page on load
    showPage(1);

    // Apply filters and sorting when OK button is clicked
    if (okBtn) {
        okBtn.addEventListener('click', function () {
            const letters = allLetters;

            const filterYearFrom = document.getElementById('yearDropdownFrom')?.value;
            const filterYearTo = document.getElementById('yearDropdownTo')?.value;
            const filterMonthFrom = document.getElementById('monthDropdownFrom')?.value;
            const filterMonthTo = document.getElementById('monthDropdownTo')?.value;

            const sortNewestFirst = (document.querySelector('input[name="sortOptions"]:checked')?.value || 'newest') === 'newest';
            const selectedType = document.querySelector('input[name="typeOptions"]:checked')?.value;

            // Build from and to Date objects for filtering
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

            // Filter cards by date range and type
            letters.forEach(card => {
                const cardDate = new Date(card.dataset.create_date);
                const inRange = cardDate >= fromDate && cardDate <= toDate;
                const rightType = card.dataset.type === selectedType || !selectedType;
                card.style.display = (inRange && rightType) ? 'block' : 'none';
            });

            // Sort cards by creation date (in place)
            letters.sort((a, b) => {
                const dateA = new Date(a.dataset.create_date);
                const dateB = new Date(b.dataset.create_date);
                return sortNewestFirst ? dateB - dateA : dateA - dateB;
            });

            // Update the filter count badge
            let filtersCount = 0;
            if (filterYearFrom || filterMonthFrom || filterYearTo || filterMonthTo) filtersCount++;
            if (selectedType) filtersCount++;

            const filterBtn = document.querySelector('a[data-target="#filterModal"] button');
            if (filterBtn) {
                if (filtersCount > 0) {
                    document.querySelector('#filterToggleBtn button span:nth-of-type(2)').textContent = filtersCount + ' filters applied';
                } else {
                    document.querySelector('#filterToggleBtn button span:nth-of-type(2)').textContent = '0 filters applied';
                }
            }

            // Re-render filtered and sorted cards in the container
            const container = document.getElementById('lettersContainer');
            container.innerHTML = '';
            letters.forEach(el => container.appendChild(el));

            // Reset pagination variables after filtering
            currentPage = 1;
            showPage(currentPage);
        });
    }

    // Reset filters and restore default state when Cancel button clicked
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function () {
            // If child filter is active, just reload the base page to clear it
            const hasFilterChild = cancelBtn.dataset.filterChild === 'true';
            if (hasFilterChild) {
                window.location.href = '/my2/children/letters';
                return;
            }

            // Reset dropdowns to default first options
            document.getElementById('yearDropdownFrom').selectedIndex = 0;
            document.getElementById('yearDropdownTo').selectedIndex = 0;
            document.getElementById('monthDropdownFrom').selectedIndex = 0;
            document.getElementById('monthDropdownTo').selectedIndex = 0;

            // Reset type filter labels and inputs
            document.querySelectorAll('#filterTypeToggle label').forEach(label => {
                label.classList.remove('active');
                const input = label.querySelector('input');
                if (input) input.checked = false;
            });

            // Reset sort filter labels and inputs, set newest as active
            document.querySelectorAll('#sortToggle label').forEach(label => {
                label.classList.remove('active');
                const input = label.querySelector('input');
                if (input) input.checked = false;
            });
            const newestLabel = document.querySelector('#sortToggle input[value="newest"]')?.closest('label');
            if (newestLabel) newestLabel.classList.add('active');

            // Reset filter count display
            const filterCountSpan = document.querySelector('#filterToggleBtn button span:nth-of-type(2)');
            if (filterCountSpan) filterCountSpan.textContent = '0 filters applied';

            // Restore all letters to visible and re-append to container
            const container = document.getElementById('lettersContainer');
            container.innerHTML = '';
            allLetters.forEach(el => {
                el.style.display = 'block';
                container.appendChild(el);
            });

            // Reset pagination to first page after clearing filters
            currentPage = 1;
            showPage(currentPage);
        });
    }
});
