/**
 * Handles the pagination and adds filtering arguments in the url for the my2_child_letters.xml page.
 * Used in /templates/pages/my2_child_letters.xml.
 */

document.addEventListener('DOMContentLoaded', function () {
    const okBtn = document.getElementById('filterOkBtn');

    // Letter animation
    document.querySelectorAll('.my2-envelope').forEach(envelope => {
        envelope.addEventListener('click', function() {
            envelope.classList.add('open');
            const letter = envelope.querySelector('.env-letter');

            setTimeout(() => {
                if (letter) {
                    letter.style.zIndex = '3';
                }
            }, 800);

            setTimeout(function() {
                const href = envelope.getAttribute('href') || envelope.getAttribute('t-attf-href');
                if (href) {
                    window.location.href = href;
                }
            }, 1200);
        });
    });

    // Pagination: Next Page
    document.getElementById('nextPageBtn')?.addEventListener('click', () => {
        const currentUrl = new URL(window.location.href);
        const currentPage = parseInt(currentUrl.searchParams.get('page') || '1', 10);
        currentUrl.searchParams.set('page', currentPage + 1);
        window.location.href = currentUrl.toString();
    });

    // Pagination: Previous Page
    document.getElementById('prevPageBtn')?.addEventListener('click', () => {
        const currentUrl = new URL(window.location.href);
        const currentPage = parseInt(currentUrl.searchParams.get('page') || '1', 10);
        if (currentPage > 1) {
            currentUrl.searchParams.set('page', currentPage - 1);
            window.location.href = currentUrl.toString();
        }
    });

    // Apply filters and sorting when OK button is clicked
    if (okBtn) {
        okBtn.addEventListener('click', function () {
            const filterYearFrom = document.getElementById('yearDropdownFrom')?.value || '';
            const filterYearTo = document.getElementById('yearDropdownTo')?.value || '';
            const filterMonthFrom = document.getElementById('monthDropdownFrom')?.value || '';
            const filterMonthTo = document.getElementById('monthDropdownTo')?.value || '';
            const sort = document.querySelector('input[name="sortOptions"]:checked')?.value || 'newest';
            const redirect_child_id = document.getElementById('childrenDropdown')?.value || '';
            const selectedType = document.querySelector('input[name="type"]:checked')?.value || '';

            const url = new URL(window.location.origin + '/my2/children/letters');
            if (redirect_child_id) url.pathname += `/${redirect_child_id}`;
            if (filterYearFrom) url.searchParams.set('year_from', filterYearFrom);
            if (filterYearTo) url.searchParams.set('year_to', filterYearTo);
            if (filterMonthFrom) url.searchParams.set('month_from', filterMonthFrom);
            if (filterMonthTo) url.searchParams.set('month_to', filterMonthTo);
            if (selectedType) url.searchParams.set('type', selectedType);
            url.searchParams.set('sort', sort);
            url.searchParams.set('page', 1);

            window.location.href = url.toString();
        });
    }
});