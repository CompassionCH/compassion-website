
// This script fetches the timezone of a child's center and displays the current time there.
document.addEventListener('DOMContentLoaded', () => {
    const mapContainerEl = document.querySelector(".cd-map-container");
    const currentTimeEl = document.getElementById('current_time');
    const childId = mapContainerEl.dataset.childId;

    if (currentTimeEl) {

        fetch(`/my2/children/${childId}/center-timezone`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {

                const centerTimezone = data.timezone;
                //Formatting options for the time to be shown
                const options = {
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: true,
                    timeZone: centerTimezone
                };

                const updateTime = () => {
                    try {
                        const now = new Date();
                        const centerTimeString = now.toLocaleTimeString('en-US', options)
                                                    .replace('AM', 'am')
                                                    .replace('PM', 'pm');
                        currentTimeEl.textContent = finalTimeString;
                    } catch (error) {
                        console.error("Invalid timezone identifier received from server:", centerTimezone, error);
                        currentTimeEl.textContent = "Error";
                        clearInterval(clockInterval);
                    }
                };

                updateTime();
                const clockInterval = setInterval(updateTime, 1000 * 60); // Update every minute
            })
            .catch(error => {

                console.error('Failed to fetch timezone:', error);
                currentTimeEl.textContent = 'Could not load time.';
            });
    } else {
        console.error('Required HTML element #current_time is missing.');
    }
});