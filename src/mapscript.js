// Ensure global namespace and initialize map
window.myApp = window.myApp || {};
window.myApp.map = null;
window.myApp.routeLayer = null; // Placeholder for the route layer
window.myApp.elevationControl = null; // Placeholder for the elevation control
window.myApp.markers = []; // Placeholder for segment markers
window.myApp.loadMapData = loadMapData;

window.addEventListener('load', () => {
    // Check if the map already exists
    if (!window.myApp.map) {
        window.myApp.map = L.map('map').setView([42.446, -76.4808], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: 'Map data &copy; <a href="http://www.osm.org">OpenStreetMap</a>'
        }).addTo(window.myApp.map);
    }

    // Call a function to load the data
    loadMapData();
});

function loadMapData() {
    const geoData = sessionStorage.getItem('geoData');

    // Remove existing route layer and elevation control if they exist
    if (window.myApp.routeLayer) {
        window.myApp.map.removeLayer(window.myApp.routeLayer);
        window.myApp.routeLayer = null;
    }
    if (window.myApp.elevationControl) {
        window.myApp.map.removeControl(window.myApp.elevationControl);
        window.myApp.elevationControl = null;
    }

    // Remove existing segment markers
    window.myApp.markers.forEach(marker => window.myApp.map.removeLayer(marker));
    window.myApp.markers = []; // Clear the markers array

    if (geoData) {
        const geojson = JSON.parse(geoData);

        // Add elevation control
        const el = L.control.elevation();
        el.addTo(window.myApp.map);
        window.myApp.elevationControl = el;

        // Plot the route and add markers for start and end points
        const routeLayer = L.geoJSON(geojson, {
            onEachFeature: el.addData.bind(el),
            style: function (feature) {
                return { color: feature.properties.color };
            }
        }).addTo(window.myApp.map);
        window.myApp.routeLayer = routeLayer;


        const unit = document.getElementById('unit-select').value === 'imperial' ? 'Mile' : 'Kilometer';
        const segmentType = document.getElementById('segment-select').value;
        const headers = segmentType === 'segments'
            ? ["Segment", "Start Distance", "Pace", "Segment Length"]
            : [unit, "Elapsed Time", "Pace", "Segment Time"];

        const table = document.getElementById('data-table');
        table.innerHTML = ''; // Clear existing rows
        const tableLabel = document.getElementById('table-label');
        tableLabel.textContent = segmentType === 'segments' ? "Segment Data" : "Miles/Km Data";
        // Update table headers
        table.innerHTML = `
            <tr>
                <th>${headers[0]}</th>
                <th>${headers[1]}</th>
                <th>${headers[2]}</th>
                <th>${headers[3]}</th>
            </tr>
        `;

        const mins_per_unit = document.getElementById('unit-select').value === 'imperial' ? '/mi' : '/km';
        const conversion = document.getElementById('unit-select').value === 'imperial' ? 1 : 1.60934;
        geojson.features.forEach((feature, index) => {
            const coordinates = feature.geometry.coordinates;
            const startPoint = coordinates[0];
            const startMarker = L.marker([startPoint[1], startPoint[0]])
                .addTo(window.myApp.map)
                .bindPopup(`Start of Segment ${index + 1}: Pace = ${formatTime((feature.properties.pace / conversion).toFixed(3))} ${mins_per_unit}`);
            window.myApp.markers.push(startMarker); // Store the marker reference

            if (index === geojson.features.length - 1) {
                const endPoint = coordinates[coordinates.length - 1];
                const endMarker = L.marker([endPoint[1], endPoint[0]])
                    .addTo(window.myApp.map)
                    .bindPopup(`End of Segment ${index + 1}: Pace = ${formatTime((feature.properties.pace / conversion).toFixed(3))} ${mins_per_unit}`);
                window.myApp.markers.push(endMarker); // Store the marker reference
            }
        });

        // Fit the map to the route bounds
        window.myApp.map.fitBounds(routeLayer.getBounds());

        loadCourseInformation();
    }

    // Fetch and parse segment and mile data
    const segmentData = sessionStorage.getItem('segmentPaces');
    const mileData = sessionStorage.getItem('milePaces');
    const kilometerData = sessionStorage.getItem('kilometerPaces');

    if (segmentData || mileData) {
        if (document.getElementById('segment-select').value === 'segments') {
            parseSegmentData(segmentData);
        } else {
            if (document.getElementById('unit-select').value === 'imperial') {
                parseMileIndexData(mileData);
            } else {
                parseMileIndexData(kilometerData);
            }
        }
    }
}

// Parse and display segment data
function parseSegmentData(jsonData) {
    const data = JSON.parse(jsonData);
    const table = document.getElementById('data-table');

    data.segments.forEach(segment => {
        const row = document.createElement('tr');

        const segmentNumber = segment.segment_num;
        const startDistanceMi = parseFloat(segment.start_distance);
        const pace = segment.pace;
        const segmentLengthMi = parseFloat(segment.distance);

        // Convert distances to kilometers
        const startDistanceKm = (startDistanceMi * 1.60934).toFixed(2);
        const segmentLengthKm = (segmentLengthMi * 1.60934).toFixed(2);

        // Determine display values based on selected units
        const displayStartDistance = document.getElementById('unit-select').value === 'imperial'
            ? `${startDistanceMi} mi`
            : `${startDistanceKm} km`;
        const displaySegmentLength = document.getElementById('unit-select').value === 'imperial'
            ? `${segmentLengthMi} mi`
            : `${segmentLengthKm} km`;
        const displayPace = document.getElementById('unit-select').value === 'imperial'
            ? `${formatTime(pace)} /mile`
            : `${formatTime(convertPaceToKmPerMinute(pace))} /km`;

        // Append cells to the row
        [segmentNumber, displayStartDistance, displayPace, displaySegmentLength].forEach(value => {
            const cell = document.createElement('td');
            cell.textContent = value;
            row.appendChild(cell);
        });

        table.appendChild(row);
    });
}

// Parse and display mile index data
function parseMileIndexData(jsonData) {
    const data = JSON.parse(jsonData);
    const table = document.getElementById('data-table');

    data.segments.forEach(segment => {
        const row = document.createElement('tr');

        const mileIndex = segment.mile_index || segment.kilometer_index || 0;
        const elapsedTime = formatTime(segment.elapsed_time);
        const pacePerMile = formatTime(segment.pace);
        const timePerMile = formatTime(segment.time);

        const unit = document.getElementById('unit-select').value === 'imperial' ? '/mile' : '/km';
        // Append row to table
        [mileIndex, `${elapsedTime}`, `${pacePerMile}${unit}`, `${timePerMile}`].forEach(value => {
            const cell = document.createElement('td');
            cell.textContent = value;
            row.appendChild(cell);
        });

        table.appendChild(row);
    });
}

// Helper function to format time in minutes to "HH:MM:SS"
function formatTime(minutes) {
    const totalSeconds = Math.floor(minutes * 60);
    const hours = Math.floor(totalSeconds / 3600);
    const minutesPart = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (hours === 0) {
        result = `${String(minutesPart).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    } else {
        result = `${String(hours).padStart(2, '0')}:${String(minutesPart).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }
    return result;
}

// Convert pace from minutes/mile to minutes/km
function convertPaceToKmPerMinute(paceMinutes) {
    return (paceMinutes / 1.60934).toFixed(2);
}

function loadCourseInformation() {
    const courseName = sessionStorage.getItem('courseName');
    const totalDistance = sessionStorage.getItem('totalDistance');
    const netElevation = sessionStorage.getItem('netElevation');
    const targetTime = sessionStorage.getItem('targetTime');

    const distanceUnit = document.getElementById('unit-select').value === 'imperial' ? ' mi' : ' km';
    const elevationUnit = document.getElementById('unit-select').value === 'imperial' ? ' ft' : ' m';
    const distanceConversion = document.getElementById('unit-select').value === 'imperial' ? 1 : 1.60934;
    const elevationConversion = document.getElementById('unit-select').value === 'imperial' ? 1 : 0.3048;

    const distanceTxt = (totalDistance * distanceConversion).toFixed(2) + distanceUnit;
    const elevationTxt = (netElevation * elevationConversion).toFixed(2) + elevationUnit;

    const courseNameElement = document.getElementById('course-name');
    courseNameElement.textContent = courseName;
    const distanceElement = document.getElementById('total-distance');
    distanceElement.textContent = distanceTxt;
    const elevationElement = document.getElementById('elevation-change');
    elevationElement.textContent = elevationTxt;
    const timeElement = document.getElementById('goal-time');
    timeElement.textContent = formatTime(targetTime);
}

// Handle unit selection changes
document.getElementById('unit-select').addEventListener('change', () => {
    loadMapData();
});

document.getElementById('segment-select').addEventListener('change', () => {
    loadMapData();
});
