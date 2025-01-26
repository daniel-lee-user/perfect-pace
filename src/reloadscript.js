import { updateFiles } from './updatefiles.js';
// shared variables
export var presetSegments;
export var optimalPaces;
export var segmentLengths;
export var coordinates;

// Add event listener for the segment type selection dropdown
document.getElementById('segment-select-widget').addEventListener('change', () => {
    console.log('Segment type changed.');
    console.log('Loading map data...');

    // Display the loading screen
    document.getElementById('loadingScreen').style.display = 'block';

    // Allow the DOM to update before starting computations
    setTimeout(() => {
        try {
            updateFiles(presetSegments, optimalPaces, segmentLengths, coordinates); // Perform necessary calculations

            // Trigger map update
            if (window.myApp && typeof window.myApp.loadMapData === 'function') {
                window.myApp.loadMapData();
            }

            console.log('Map data loaded.');
        } catch (error) {
            console.error('Error loading map data:', error);
        } finally {
            // Hide the loading screen once done
            document.getElementById('loadingScreen').style.display = 'none';
        }
    }, 100); // Short delay (100ms) to allow DOM to update
});


document.getElementById('submitBtn').addEventListener('click', async function (event) {
    event.preventDefault(); // Prevents the form from submitting and reloading immediately

    const fileInput = window.gpxFile;

    // Check if required fields are filled
    if (!fileInput.files.length) {
        fileInput.value = '';
        alert("Please upload a gpx file.");
        return;
    }

    // Check if the file extension is .gpx
    const fileExtension = fileInput.files[0].name.split('.').pop().toLowerCase();
    if (fileExtension !== 'gpx') {
        fileInput.value = '';
        alert("Please select a valid GPX file.");
        return;
    }

    const time = convertTimeToMinutes(document.getElementById('time').value);
    const filename = fileInput.files[0].name;
    const file = fileInput.files[0];

    console.log("UPLOAD");

    const formData = new FormData();

    formData.append('file', file);
    formData.append('time', time);

    try {
        document.getElementById('loadingScreen').style.display = 'block';

        // const url = 'https://perfect-pace-container.0pr6sav0peebr.us-east-2.cs.amazonlightsail.com/upload';
        const url =
            window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost"
                ? "http://127.0.0.1:5000/upload"
                : "https://perfect-pace-container.0pr6sav0peebr.us-east-2.cs.amazonlightsail.com/upload";

        const response = await fetch(url, {
            method: "POST",
            body: formData,
            signal: AbortSignal.timeout(400000) // timeout for 400 seconds
        })

        console.log("FINISHED UPLOAD");

        const blob = await response.blob();
        const zip = await JSZip.loadAsync(blob);

        // Specify the expected filenames
        const presetSegmentsFileName = "presetSegments.json";
        const optimalPacesFileName = "optimalPaces.json";
        const segmentLengthsFileName = "segmentLengths.json";
        const coordinatesFileName = "coordinates.json";

        // Extract each file from the zip
        const presetSegmentsTxt = await zip.file(presetSegmentsFileName)?.async("text");
        const optimalPacesTxt = await zip.file(optimalPacesFileName)?.async("text");
        const segmentLengthsTxt = await zip.file(segmentLengthsFileName)?.async("text");
        const coordinatesTxt = await zip.file(coordinatesFileName)?.async("text");

        if (!presetSegmentsTxt || !optimalPacesTxt || !segmentLengthsTxt || !coordinatesTxt) {
            throw new Error("Backend response missing required data.");
        }

        // Parse the JSON content of each file
        presetSegments = JSON.parse(presetSegmentsTxt);
        optimalPaces = JSON.parse(optimalPacesTxt);
        segmentLengths = JSON.parse(segmentLengthsTxt);
        coordinates = JSON.parse(coordinatesTxt);
        const courseName = fileInput.files[0].name.split('.')[0];
        const totalDistance = segmentLengths.reduce((a, b) => a + b, 0.0);
        const netElevation = coordinates[coordinates.length - 1][2] - coordinates[0][2];

        // Store all data in sessionStorage
        /*
        sessionStorage.setItem('presetSegments', JSON.stringify(presetSegments));
        sessionStorage.setItem('optimalPaces', JSON.stringify(optimalPaces));
        sessionStorage.setItem('segmentLengths', JSON.stringify(segmentLengths));
        sessionStorage.setItem('coordinates', JSON.stringify(coordinates));
        */
        sessionStorage.setItem('courseName', courseName);
        sessionStorage.setItem('targetTime', time);
        sessionStorage.setItem('totalDistance', totalDistance);
        sessionStorage.setItem('netElevation', netElevation);
        // Set segment method to default (Hill Detection)
        const segmentSelectWidget = document.getElementById('segment-select-widget');
        if (segmentSelectWidget) {
            segmentSelectWidget.value = 'HILL';
        }

        // Call updateFiles to generate the necessary files in sessionStorage
        updateFiles(presetSegments, optimalPaces, segmentLengths, coordinates);

        // Trigger map update
        if (window.myApp && typeof window.myApp.loadMapData === 'function') {
            window.myApp.loadMapData();
        }

        await deleteFile(filename);

    } catch (error) {
        console.error('Error:', error);
        alert("An error occurred while processing your request.");
    } finally {
        document.getElementById('loadingScreen').style.display = 'none';
        //fileInput.value = '';
    }

    async function deleteFile(filename) {
        // Construct the request URL (assuming the route for deletion is '/delete')
        // const url = 'https://perfect-pace-container.0pr6sav0peebr.us-east-2.cs.amazonlightsail.com/delete';
        const url =
            window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost"
                ? "http://127.0.0.1:5000/delete"
                : "https://perfect-pace-container.0pr6sav0peebr.us-east-2.cs.amazonlightsail.com/delete";

        // Send a DELETE request with JSON payload
        await fetch(url, {
            method: 'DELETE', // Specify DELETE method
            headers: {
                'Content-Type': 'application/json', // Set content type to JSON
            },
            body: JSON.stringify({ filename })
        })
            .then(response => response.json()) // Parse the response as JSON
            .then(data => {
                if (data.success) {
                    console.log('File deleted successfully');
                }
            })
            .catch(error => {
                console.error('Error during DELETE request:', error);
            });
    }
});

document.getElementById('clearButton').addEventListener('click', () => {
    if (!confirm('Are you sure you want to clear all data and reset the map?')) {
        return; // Do nothing if the user cancels
    }

    // Clear session storage
    sessionStorage.clear();

    // Reset the map
    if (window.myApp && window.myApp.map) {
        // Remove all layers from the map
        window.myApp.map.eachLayer((layer) => {
            if (!layer._url) {
                // Keep the base tile layer
                window.myApp.map.removeLayer(layer);
            }
        });
        if (window.myApp && window.myApp.elevationControl) {
            window.myApp.map.removeControl(window.myApp.elevationControl);
            window.myApp.elevationControl = null;
        }

        // Reset the map view to the default state
        window.myApp.map.setView([42.446, -76.4808], 13);
    }

    // Reset any UI elements
    document.getElementById('data-table').innerHTML = `
        <tr>
            <th>Segment</th>
            <th>Start Distance</th>
            <th>Pace</th>
            <th>Segment Length</th>
        </tr>
    `;

    // Clear file input field if it exists
    const fileInput = document.getElementById('gpxFile');
    if (fileInput) {
        fileInput.value = '';
    }

    // Reset course information widget
    document.getElementById('course-info-widget').innerHTML = `
        <h3>Course Information</h3>
        <ul>
            <li>Course Name: <span id="course-name">N/A</span></li>
            <li>Total Distance: <span id="total-distance">0 mi</span></li>
            <li>Elevation Change: <span id="elevation-change">0 ft</span></li>
            <li>Goal Time: <span id="goal-time">00:00:00</span></li>
        </ul>
        <div>
            <label for="segment-select-widget">Segment Method:</label>
            <select id="segment-select-widget">
                <option value="HILL">Hill Detection</option>
                <option value="APPM">Per Mile</option>
                <option value="APPKM">Per Kilometer</option>
                <option value="AP">No Segments</option>
            </select>
        </div>
    `;
});


function convertTimeToMinutes(time) {
    // Regular expression to validate time in HH:MM:SS or MM:SS format
    const timeRegex = /^((?:[0-1]?[0-9]|2[0-3]):)?([0-5]?[0-9]):([0-5][0-9])$/;

    // Check if the input matches the format
    const match = time.match(timeRegex);
    if (!match) {
        alert("Invalid time format. Please enter time in HH:MM:SS or MM:SS format.");
        return null;
    }

    // Extract hours, minutes, and seconds from the match
    const hours = match[1] ? parseInt(match[1].replace(":", ""), 10) : 0; // Default to 0 if no hours
    const minutes = parseInt(match[2], 10);
    const seconds = parseInt(match[3], 10);

    // Calculate the total time in minutes
    const totalMinutes = hours * 60 + minutes + seconds / 60;

    return totalMinutes;
}
