/** @odoo-module **/

/**
 * Google Maps Widget
 *
 * publicWidget mounted on `.js-map-widget`. Reads latitude, longitude, API key,
 * and optional custom map ID from data-* attributes. Loads the Google Maps API
 * via a native script tag (singleton per page), then initialises the map with
 * terrain/hybrid controls, a custom Compassion pin, and a custom Pegman SVG for
 * the Street View control.
 *
 * Data attributes (all on the host element):
 *   data-lat          Latitude (float string)
 *   data-lng          Longitude (float string)
 *   data-api-key      Google Maps API key (required)
 *   data-custom-map-id   Cloud Map ID (optional; falls back to "YOUR_MAP_ID")
 *
 * Graceful degradation: adds `.map--load-failed` to the host element and logs to
 * the console if the API key is absent or the Maps API fails to load.
 */

/* global google */
import publicWidget from "@web/legacy/js/public/public_widget";

let googleMapsLoadPromise = null;

const POLL_INTERVAL = 150;
const POLL_TIMEOUT = 3000;
const SELECTORS = {
    STREET_VIEW_BUTTON: ".gm-svpc",
    MAP_SELECTOR_TERRAIN: 'button[aria-label="Show street map with terrain"]',
    MAP_SELECTOR_SATELLITE: 'button[aria-label="Show imagery with street names"]',
    GRABBED_PEGMAN: 'gmp-internal-use-am[aria-grabbed="true"]',
};

publicWidget.registry.GoogleMapEl = publicWidget.Widget.extend({
    selector: ".js-map-widget",

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);

        const { lat, lng, apiKey, customMapId } = this.el.dataset;
        const mapId = customMapId || "YOUR_MAP_ID";
        const latNum = parseFloat(lat);
        const lngNum = parseFloat(lng);

        if (!apiKey) {
            console.error("Google Maps API key not found.");
            this.el.classList.add("map--load-failed");
            return;
        }

        try {
            await this._loadGoogleMaps(apiKey);
            await this._initializeMap(latNum, lngNum, mapId);
        } catch (error) {
            console.error("Failed to load Google Maps:", error);
            this.el.classList.add("map--load-failed");
        }
    },

    /**
     * Injects a Google Maps script tag into the document head and returns a
     * promise that resolves when the script loads. Creates a singleton promise
     * so the script is injected only once per page, even when multiple map
     * widgets are present.
     *
     * @private
     * @param {String} apiKey
     * @returns {Promise}
     */
    _loadGoogleMaps(apiKey) {
        if (!googleMapsLoadPromise) {
            googleMapsLoadPromise = new Promise((resolve, reject) => {
                if (typeof google !== "undefined" && typeof google.maps !== "undefined") {
                    return resolve();
                }
                const script = document.createElement("script");
                script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&libraries=marker`;
                script.async = true;
                script.onload = () => resolve();
                script.onerror = (err) => reject(err);
                document.head.appendChild(script);
            });
        }
        return googleMapsLoadPromise;
    },

    /**
     * Initialises the map instance, creates the marker, and customises controls.
     *
     * @private
     * @param {Number} lat
     * @param {Number} lng
     * @param {String} mapId
     * @param {Number} [zoom=10]
     */
    async _initializeMap(lat, lng, mapId, zoom = 10) {
        const position = { lat: lat, lng: lng };

        const { Map } = await google.maps.importLibrary("maps");
        const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

        const map = new Map(this.el, {
            zoom: zoom,
            center: position,
            mapId: mapId,
            streetViewControl: true,
            mapTypeControl: true,
            mapTypeId: "terrain",
            mapTypeControlOptions: {
                mapTypeIds: ["terrain", "hybrid"],
                style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
            },
        });

        this._customizeControls(map);

        const pinElement = this._createCustomPin();

        new AdvancedMarkerElement({
            map,
            position,
            content: pinElement,
            title: "Compassion Center of Child",
        });
    },

    /**
     * Polls the DOM for a selector to appear, then executes a callback.
     * Required because elements added dynamically by the Google Maps API are not
     * present synchronously after map construction.
     *
     * @private
     * @param {String} selector
     * @param {Function} callback
     * @param {Element} [root=this.el]
     * @returns {Number} The interval timer ID.
     */
    _pollForElement(selector, callback, root = this.el) {
        let elapsedTime = 0;
        const timer = setInterval(() => {
            const element = root.querySelector(selector);
            if (element) {
                clearInterval(timer);
                callback(element);
            } else if (elapsedTime >= POLL_TIMEOUT) {
                clearInterval(timer);
                console.warn(`Element with selector "${selector}" not found after ${POLL_TIMEOUT}ms.`);
            }
            elapsedTime += POLL_INTERVAL;
        }, POLL_INTERVAL);
        return timer;
    },

    /**
     * Orchestrates all UI customisations for the map controls.
     * Called once the map is idle.
     *
     * @private
     * @param {google.maps.Map} map
     */
    _customizeControls(map) {
        const svgDataUrl = this._buildCustomStreetViewSvgDataUrl();

        google.maps.event.addListenerOnce(map, "idle", () => {
            this._pollForElement(SELECTORS.STREET_VIEW_BUTTON, (streetViewButton) => {
                const pegmanContainer = streetViewButton.firstChild;

                this._updateImagesInContainer(pegmanContainer, svgDataUrl);
                pegmanContainer.lastChild.className = "custom-steetview-button";

                streetViewButton.addEventListener("mousedown", () => {
                    this._pollForElement(
                        SELECTORS.GRABBED_PEGMAN,
                        (grabbedPegman) => {
                            grabbedPegman.className = "grapped-pogman-container";
                            grabbedPegman.querySelector("img").className = "grapped-pogman";

                            this._updateImagesInContainer(grabbedPegman, svgDataUrl);
                        },
                        document.body
                    );
                });
            });

            this._pollForElement(SELECTORS.MAP_SELECTOR_TERRAIN, (terrainButton) => {
                terrainButton.textContent = "Map";
            });

            this._pollForElement(SELECTORS.MAP_SELECTOR_SATELLITE, (hybridButton) => {
                hybridButton.textContent = "Satellite";
            });
        });
    },

    // --------------------------------------------------------------------------
    // Helpers
    // --------------------------------------------------------------------------

    /**
     * Creates and returns the DOM element for the custom map pin.
     *
     * @private
     * @returns {Element}
     */
    _createCustomPin() {
        const pinHtmlString = `
            <div class="custom-map-pin">
                <i class="icon icon-marker-pin01"></i>
            </div>
        `;
        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = pinHtmlString.trim();
        return tempDiv.firstChild;
    },

    /**
     * Builds a URL-encoded data URL from the custom Pegman SVG. The SVG is
     * injected into the Google Maps Street View control to replace the default
     * figure icon with the Compassion-branded one.
     *
     * @private
     * @returns {String} The generated data URL.
     */
    _buildCustomStreetViewSvgDataUrl() {
        const svgString = `
        <?xml version="1.0" encoding="iso-8859-1"?>
        <svg fill="#000000" height="800px" width="800px" version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
             viewBox="0 0 480 480" xml:space="preserve">
        <g>
            <g>
                <g>
                    <path d="M391.502,210.725c-5.311-1.52-10.846,1.555-12.364,6.865c-1.519,5.31,1.555,10.846,6.864,12.364
                        C431.646,243.008,460,261.942,460,279.367c0,12.752-15.51,26.749-42.552,38.402c-29.752,12.82-71.958,22.2-118.891,26.425
                        l-40.963-0.555c-0.047,0-0.093-0.001-0.139-0.001c-5.46,0-9.922,4.389-9.996,9.865c-0.075,5.522,4.342,10.06,9.863,10.134
                        l41.479,0.562c0.046,0,0.091,0.001,0.136,0.001c0.297,0,0.593-0.013,0.888-0.039c49.196-4.386,93.779-14.339,125.538-28.024
                        C470.521,316.676,480,294.524,480,279.367C480,251.424,448.57,227.046,391.502,210.725z"/>
                    <path d="M96.879,199.333c-5.522,0-10,4.477-10,10c0,5.523,4.478,10,10,10H138v41.333H96.879c-5.522,0-10,4.477-10,10
                        s4.478,10,10,10H148c5.523,0,10-4.477,10-10V148c0-5.523-4.477-10-10-10H96.879c-5.522,0-10,4.477-10,10s4.478,10,10,10H138
                        v41.333H96.879z"/>
                    <path d="M188.879,280.667h61.334c5.522,0,10-4.477,10-10v-61.333c0-5.523-4.477-10-10-10h-51.334V158H240c5.523,0,10-4.477,10-10
                        s-4.477-10-10-10h-51.121c-5.523,0-10,4.477-10,10v122.667C178.879,276.19,183.356,280.667,188.879,280.667z M198.879,219.333
                        h41.334v41.333h-41.334V219.333z"/>
                    <path d="M291.121,280.667h61.334c5.522,0,10-4.477,10-10V148c0-5.523-4.478-10-10-10h-61.334c-5.522,0-10,4.477-10,10v122.667
                        C281.121,276.19,285.599,280.667,291.121,280.667z M301.121,158h41.334v102.667h-41.334V158z"/>
                    <path d="M182.857,305.537c-3.567-4.216-9.877-4.743-14.093-1.176c-4.217,3.567-4.743,9.876-1.177,14.093l22.366,26.44
                        c-47.196-3.599-89.941-12.249-121.37-24.65C37.708,308.06,20,293.162,20,279.367c0-16.018,23.736-33.28,63.493-46.176
                        c5.254-1.704,8.131-7.344,6.427-12.598c-1.703-5.253-7.345-8.13-12.597-6.427c-23.129,7.502-41.47,16.427-54.515,26.526
                        C7.674,252.412,0,265.423,0,279.367c0,23.104,21.178,43.671,61.242,59.48c32.564,12.849,76.227,21.869,124.226,25.758
                        l-19.944,22.104c-3.7,4.1-3.376,10.424,0.725,14.123c1.912,1.726,4.308,2.576,6.696,2.576c2.731,0,5.453-1.113,7.427-3.301
                        l36.387-40.325c1.658-1.837,2.576-4.224,2.576-6.699v-0.764c0-2.365-0.838-4.653-2.365-6.458L182.857,305.537z"/>
                    <path d="M381.414,137.486h40.879c5.522,0,10-4.477,10-10V86.592c0-5.523-4.478-10-10-10h-40.879c-5.522,0-10,4.477-10,10v40.894
                        C371.414,133.009,375.892,137.486,381.414,137.486z M391.414,96.592h20.879v20.894h-20.879V96.592z"/>
                </g>
            </g>
        </g>
        </svg>`.trim();

        return "data:image/svg+xml," + encodeURIComponent(svgString);
    },

    /**
     * Finds all <img> tags within a given container and replaces their src.
     *
     * @private
     * @param {Element} container - The DOM element containing the images.
     * @param {String} dataUrl - The new src for the images.
     */
    _updateImagesInContainer(container, dataUrl) {
        const images = container.querySelectorAll("img");
        images.forEach((img) => {
            img.src = dataUrl;
        });
    },
});

export default publicWidget.registry.GoogleMapEl;
