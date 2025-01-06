/**
 * Time updater and Weather Fetcher for Child Profile Center
 * --------------------------------
 * This script keeps the current time of the child compassion center updated every minute and fetches the weather infos.
 * Key Features:
 * - Fetches weather data via GET from `/my2/children/<childId>/center-weather`
 * - Use the injected time zone to display the current time in the center's locale
 * - Updates the time every 15 seconds in the client side
 * - Load the weather icon based on the fetched weather data
 * - Displays the container only after successful data fetch
 * Used in /templates/pages/my2_child_timeline.xml
 */

// Mapping of weather icon filenames to their corresponding CSS classes
const iconClassMap = {
    sun: "weather-icon-sun",
    "moon-star": "weather-icon-moon",
    "cloud-raining04": "weather-icon-rain",
    "cloud-lightning": "weather-icon-rain",
    waves: "weather-icon-mist",
    wind03: "weather-icon-mist",
    "cloud-blank02": "weather-icon-cloudy",
};
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

        let clockInterval;
        const updateTime = () => {
            try {
                const now = new Date();
                const centerTimeString = now
                    .toLocaleTimeString("en-US", options)
                    .replace("AM", "am")
                    .replace("PM", "pm");
                currentTimeEl.textContent = centerTimeString;
            } catch (error) {
                console.error("Invalid timezone identifier received from server:", timezone, error);
                clearInterval(clockInterval);
            }
        };
        updateTime();
        clockInterval = setInterval(updateTime, 1000 * 15); // Update every 15 seconds
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
                // Attach the fetched icon to the frontend
                weather_icon_el.classList.add("icon", `icon-${icon_id}`);
                //Attach the corresponding css class for the icon to allow color styling
                const iconClass = iconClassMap[icon_id];
                if (iconClass) {
                    weather_icon_el.classList.add(iconClass);
                }

                //Upon successful fetch and update, ensure the container is visible
                if (containerEl) {
                    containerEl.classList.remove("d-none");
                }
            })
            .catch((error) => {
                console.error("Failed to fetch temperature:", error);
                currentTemperatureEl.textContent = "--";
            });
    } else {
        console.error("HTML element #current_temperature  or #weather_icon is missing.");
    }
});
