/**
 * Time updater and Weather Fetcher for Child Profile Center
 * --------------------------------
 * This script keeps the current time of the child compassion center updated every minute and fetches the weather infos.
 * Key Features:
 * - Fetches weather data in via POST to `/my2/children/<childId>/center-weather`
 * - Use the injected time zone to display the current time in the center's locale
 * - Updates the time every 15 seconds in the client side
 * - Load the weather icon based on the fetched weather data
 * - Displays the container only after successful data fetch
 * Used in /templates/pages/my2_child_timeline.xml
 */
document.addEventListener("DOMContentLoaded", () => {
    const containerEl = document.querySelector(".center-info-card");
    const timelinePageEl = document.querySelector(".cd-weather-map-container");
    const currentTimeEl = document.getElementById("current_time");
    const currentTemperatureEl = document.getElementById("current_temperature");
    const childId = timelinePageEl.dataset.childId;
    const timezone = timelinePageEl.dataset.timezone;
    const weather_icon_el = document.getElementById("weather_icon");

    // Handles time computation and formating
    if (currentTimeEl) {
        //Formatting options for the time to be shown
        const options = {
            hour: "2-digit",
            minute: "2-digit",
            hour12: true,
            timeZone: timezone,
        };

        const updateTime = () => {
            try {
                const now = new Date();
                const centerTimeString = now
                    .toLocaleTimeString("en-US", options)
                    .replace("AM", "am")
                    .replace("PM", "pm");
                currentTimeEl.textContent = centerTimeString;
            } catch (error) {
                console.error("Invalid timezone identifier received from server:", centerTimezone, error);
                clearInterval(clockInterval);
            }
        };
        updateTime();
        const clockInterval = setInterval(updateTime, 1000 * 15); // Update every 15 seconds
    }
    // Fetch and update the current temperature and weather icon
    if (currentTemperatureEl && weather_icon_el) {
        fetch(`/my2/children/${childId}/center-weather`)
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Network response was not ok");
                }
                return response.json();
            })
            .then((data) => {
                const temperature = data.current_temperature;
                currentTemperatureEl.textContent = `${temperature}`;
                const icon_id = data.weather_icon_id;
                weather_icon_el.src = `/theme_compassion_2025/static/src/img/icons/${icon_id}`;

                //Upon successful fetch and update, ensure the container is visible
                if (containerEl) {
                    containerEl.style.display = "block";
                }
            })
            .catch((error) => {
                console.error("Failed to fetch temperature:", error);
                currentTimeEl.textContent = "Could not load temperature.";
            });
    } else {
        console.error("Required HTML element #current_temperature is missing.");
    }
});
