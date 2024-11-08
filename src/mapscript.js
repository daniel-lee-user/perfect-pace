// Map Initialization
window.addEventListener('load', () => {
    var map = L.map('map').setView([51.505, -0.09], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data &copy; <a href="http://www.osm.org">OpenStreetMap</a>'
    }).addTo(map);

    // Retrieve the GPX data from localStorage
    const geoData = sessionStorage.getItem('geoData');
    if (geoData) {
        const geojson = JSON.parse(geoData);
        geojson.features.forEach((feature, index) => {
            let coordinates = feature.geometry.coordinates;
            let startPoint = coordinates[0];
            L.marker([startPoint[1], startPoint[0]]).addTo(map).bindPopup(`Start of Segment ${index + 1}: Pace = ${feature.properties.pace.toFixed(4)}`);
            if (index == geojson.features.length - 1) {
                let endPoint = coordinates[coordinates.length - 1];
                L.marker([endPoint[1], endPoint[0]]).addTo(map).bindPopup(`End of Segment ${index + 1}: Pace = ${feature.properties.pace.toFixed(4)}`);
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
    } else {
        alert('No GPX data found!');
    }

    // Fetch and parse text data from segments.txt
    /*
    fetch('segments.txt')
        .then(response => response.text())
        .then(text => parseTextData(text))
        .catch(error => console.error('Error loading text file:', error));
    */

    const txtData = sessionStorage.getItem('textFileContent');
    parseTextData(txtData);
    // Parse and display text data
    function parseTextData(text) {
        const lines = text.split('\n');
        lines.forEach(line => {
            const match = line.match(/(\d+):\s+([\d.]+)\s*mi\s+([\d:]+\/mile)\s*for\s+([\d.]+)\s*mi/);
            if (match) {
                const row = document.createElement('tr');
                const segmentNumber = match[1];
                const distanceMi = parseFloat(match[2]);
                const pace = match[3];
                const segmentLengthMi = parseFloat(match[4]);
                const distanceKm = (distanceMi * 1.60934).toFixed(2);
                const segmentLengthKm = (segmentLengthMi * 1.60934).toFixed(2);
                const paceParts = pace.split('/');
                const paceMinutes = paceParts[0];
                const paceMiles = paceParts[1].replace('mile', '');
                const paceMinutesTotal = convertPaceToKmPerMinute(paceMinutes, paceMiles);

                const displayDistance = document.getElementById('unit-select').value === 'imperial'
                    ? `${distanceMi} mi`
                    : `${distanceKm} km`;
                const displaySegmentLength = document.getElementById('unit-select').value === 'imperial'
                    ? `${segmentLengthMi} mi`
                    : `${segmentLengthKm} km`;
                const displayPace = document.getElementById('unit-select').value === 'imperial'
                    ? pace
                    : `${paceMinutesTotal}/km`;

                [segmentNumber, displayDistance, displayPace, displaySegmentLength].forEach(value => {
                    const cell = document.createElement('td');
                    cell.textContent = value;
                    row.appendChild(cell);
                });

                document.getElementById('data-table').appendChild(row);
            }
        });
    }

    // Convert pace from minutes/mile to minutes/km
    function convertPaceToKmPerMinute(paceMinutes, paceMiles) {
        const [mins, secs] = paceMinutes.split(':').map(Number);
        const totalMinutes = mins + secs / 60;
        const paceMinutesPerKm = (totalMinutes / 1.60934).toFixed(2);
        return paceMinutesPerKm.replace('.', ':');
    }

    document.getElementById('unit-select').addEventListener('change', () => {
        document.getElementById('data-table').innerHTML = "<tr>\
            <th>Segment</th>\
            <th>Distance (mi)</th>\
            <th>Pace (/mile)</th>\
            <th>Segment Length (mi)</th>\
        </tr>";
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
        parseTextData(txtData);
        /*
        fetch('segments.txt')
            .then(response => response.text())
            .then(text => parseTextData(text))
            .catch(error => console.error('Error loading text file:', error));
        */
    });
});
