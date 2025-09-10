
// This script fetches the timezone of a child's center and displays the current time there.
document.addEventListener('DOMContentLoaded', () => {
    const mapContainerEl = document.querySelector(".cd-weather-map-container");
    const currentTimeEl = document.getElementById('current_time');
    const currentTemperatureEl = document.getElementById('current_temperature');
    const childId = mapContainerEl.dataset.childId;
    const timezone = mapContainerEl.dataset.timezone;

    if (currentTimeEl) {

                //Formatting options for the time to be shown
                const options = {
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: true,
                    timeZone: timezone
                };

                console.log("Timezone for center:", timezone);

                const updateTime = () => {
                    try {
                        const now = new Date();
                        const centerTimeString = now.toLocaleTimeString('en-US', options)
                                                    .replace('AM', 'am')
                                                    .replace('PM', 'pm');
                        currentTimeEl.textContent = centerTimeString;
                    } catch (error) {
                        console.error("Invalid timezone identifier received from server:", centerTimezone, error);
                        currentTimeEl.textContent = "Error";
                        clearInterval(clockInterval);
                    }

                }
                updateTime();
                const clockInterval = setInterval(updateTime, 1000 * 60); // Update every minute




    }
    if (currentTemperatureEl) {

    fetch(`/my2/children/${childId}/center-weather`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            const temperature = data.current_temperature;
            currentTemperatureEl.textContent = `${temperature}°C`;
        })
        .catch(error => {

            console.error('Failed to fetch temperature:', error);
            currentTimeEl.textContent = 'Could not load temperature.';
        });
} else {
    console.error('Required HTML element #current_temperature is missing.');
}
































});