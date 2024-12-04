// Map Initialization
window.addEventListener('load', () => {
    var map = L.map('map').setView([42.446, -76.4808], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data &copy; <a href="http://www.osm.org">OpenStreetMap</a>'
    }).addTo(map);

    // Retrieve the GPX data from localStorage
    const geoData = sessionStorage.getItem('geoData');
    if (geoData) {
        const geojson = JSON.parse(geoData);
        console.log(geoData);
        geojson.features.forEach((feature, index) => {
            let coordinates = feature.geometry.coordinates;
            let startPoint = coordinates[0];
            L.marker([startPoint[1], startPoint[0]]).addTo(map).bindPopup(`Start of Segment ${index + 1}: Pace = ${feature.properties.pace.toFixed(2)} min/mi`);
            if (index == geojson.features.length - 1) {
                let endPoint = coordinates[coordinates.length - 1];
                L.marker([endPoint[1], endPoint[0]]).addTo(map).bindPopup(`End of Segment ${index + 1}: Pace = ${feature.properties.pace.toFixed()} min/mi`);
            }
        });

        var el = L.control.elevation();
        el.addTo(map);
        const geoJsonLayer = L.geoJSON(geojson, {
            onEachFeature: el.addData.bind(el),
            style: function (feature) {
                return { color: feature.properties.color }
            }
        }).addTo(map);
        map.fitBounds(geoJsonLayer.getBounds());
    }

    // Fetch and parse text data from segments.txt

    const segmentData = sessionStorage.getItem('segments');
    const mileData = sessionStorage.getItem('miles');
    console.log(mileData);
    console.log(segmentData);
    if (segmentData) {
        parseSegmentData(segmentData);
    }

    // Parse and display JSON data
    function parseSegmentData(jsonData) {
        const data = JSON.parse(jsonData);

        data.segments.forEach(segment => {
            const row = document.createElement('tr');

            const segmentNumber = segment.segment_num;
            const startDistanceMi = parseFloat(segment.start_distance);
            const pace = segment.pace;
            const segmentLengthMi = parseFloat(segment.distance);

            // Convert distances to kilometers
            const startDistanceKm = (startDistanceMi * 1.60934).toFixed(2);
            const segmentLengthKm = (segmentLengthMi * 1.60934).toFixed(2);

            // Convert pace to km/min if needed
            const paceMinutesTotal = convertPaceToKmPerMinute(pace, 'mile');

            // Determine display values based on selected units
            const displayStartDistance = document.getElementById('unit-select').value === 'imperial'
                ? `${startDistanceMi} mi`
                : `${startDistanceKm} km`;
            const displaySegmentLength = document.getElementById('unit-select').value === 'imperial'
                ? `${segmentLengthMi} mi`
                : `${segmentLengthKm} km`;
            const displayPace = document.getElementById('unit-select').value === 'imperial'
                ? `${pace}/mile`
                : `${paceMinutesTotal}/km`;

            // Append cells to the row
            [segmentNumber, displayStartDistance, displayPace, displaySegmentLength].forEach(value => {
                const cell = document.createElement('td');
                cell.textContent = value;
                row.appendChild(cell);
            });

            document.getElementById('data-table').appendChild(row);
        });
    }

    function parseMileIndexData(data) {
        data.segments.forEach(segment => {
            const row = document.createElement('tr');

            const mileIndex = segment.mile_index;
            const elapsedTime = formatTime(segment.elapsed_time);
            const pacePerMile = segment.pace_per_mile;
            const timePerMile = formatTime(segment.time_per_mile);

            // Append row to table
            [mileIndex, `${elapsedTime}`, `${pacePerMile}/mile`, `${timePerMile}`].forEach(value => {
                const cell = document.createElement('td');
                cell.textContent = value;
                row.appendChild(cell);
            });

            document.getElementById('data-table').appendChild(row);
        });
    }
    // Helper function to format time in minutes to "HH:MM:SS"
    function formatTime(minutes) {
        const totalSeconds = Math.floor(minutes * 60);
        const hours = Math.floor(totalSeconds / 3600);
        const minutesPart = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        return `${String(hours).padStart(2, '0')}:${String(minutesPart).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }
    // Convert pace from minutes/mile to minutes/km
    function convertPaceToKmPerMinute(paceMinutes, paceMiles) {
        const [mins, secs] = paceMinutes.split(':').map(Number);
        const totalMinutes = mins + secs / 60;
        const paceMinutesPerKm = (totalMinutes / 1.60934).toFixed(2);
        return paceMinutesPerKm.replace('.', ':');
    }

    document.getElementById('unit-select').addEventListener('change', () => {
        const segmentType = document.getElementById('segment-select').value;
        const headers = segmentType === 'segments'
            ? ["Segment", "Start Distance", "Pace", "Segment Length"]
            : ["Mile", "Elapsed Time", "Avg Pace", "Time/Mile"];

        // Update table headers
        document.getElementById('data-table').innerHTML = `
            <tr>
                <th>${headers[0]}</th>
                <th>${headers[1]}</th>
                <th>${headers[2]}</th>
                <th>${headers[3]}</th>
            </tr>
        `;
        const geojsonEdited = JSON.parse(geoData);
        if (document.getElementById('unit-select').value === 'metric') {
            geojsonEdited.features.forEach(feature => {
                const paceMinPerMile = feature.properties.pace;
                const paceMinPerKm = paceMinPerMile / 1.60934;
                feature.properties.pace = paceMinPerKm;
            });
        }
        if (geojsonEdited) {
            map.off();
            map.remove();
            map = L.map('map').setView([51.505, -0.09], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: 'Map data &copy; <a href="http://www.osm.org">OpenStreetMap</a>'
            }).addTo(map);
            geojsonEdited.features.forEach((feature, index) => {
                let coordinates = feature.geometry.coordinates;
                let startPoint = coordinates[0];
                L.marker([startPoint[1], startPoint[0]]).addTo(map).bindPopup(`Start of Segment ${index + 1}: Pace = ${feature.properties.pace.toFixed(4)} min/mi`);
                if (index == geojsonEdited.features.length - 1) {
                    let endPoint = coordinates[coordinates.length - 1];
                    L.marker([endPoint[1], endPoint[0]]).addTo(map).bindPopup(`End of Segment ${index + 1}: Pace = ${feature.properties.pace.toFixed(4)} min/mi`);
                }
            });
            var el = L.control.elevation();
            el.addTo(map);
            const geoJsonLayer = L.geoJSON(geojsonEdited, {
                onEachFeature: el.addData.bind(el),
                style: function (feature) {
                    return { color: feature.properties.color }
                }
            }).addTo(map);
            map.fitBounds(geoJsonLayer.getBounds());
        }
        if (segmentData || mileData) {
            if (document.getElementById('segment-select').value === 'segments') {
                parseSegmentData(segmentData);
            } else {
                const data = JSON.parse(mileData);
                parseMileIndexData(data);
            }
        }
    });
    document.getElementById('segment-select').addEventListener('change', () => {
        // Set table headers based on the selected segment type
        const segmentType = document.getElementById('segment-select').value;
        const headers = segmentType === 'segments'
            ? ["Segment", "Start Distance", "Pace", "Segment Length"]
            : ["Mile", "Elapsed Time", "Avg Pace", "Time/Mile"];
        const tableLabel = document.getElementById('table-label');
        tableLabel.textContent = segmentType === 'segments' ? "Segment Data" : "Mile Data";
        // Update table headers
        document.getElementById('data-table').innerHTML = `
            <tr>
                <th>${headers[0]}</th>
                <th>${headers[1]}</th>
                <th>${headers[2]}</th>
                <th>${headers[3]}</th>
            </tr>
        `;

        // Parse and display data based on selected type

        if (segmentType === 'segments') {
            parseSegmentData(segmentData);
        } else {
            const data = JSON.parse(mileData);
            parseMileIndexData(data);
        }
    });
    document.getElementById('gpxFile').addEventListener('change', async function (event) {
        const fileInput = document.getElementById('gpxFile');
        if (!fileInput.files.length) {
            fileInput.value = '';
            alert("Please select a valid GPX file.");
            return;
        }
        // Check if the file extension is .gpx
        const fileExtension = fileInput.files[0].name.split('.').pop().toLowerCase();
        if (fileExtension !== 'gpx') {
            fileInput.value = '';
            alert("Please select a valid GPX file.");
            return;
        }
        window.gpxFile = fileInput;
    });
});
