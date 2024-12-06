import { updateFiles } from './updatefiles.js';

document.getElementById('submitBtn').addEventListener('click', async function (event) {
    event.preventDefault(); // Prevents the form from submitting and reloading immediately

    const fileInput = window.gpxFile;
    if (!fileInput) {
        alert("Please upload a gpx file");
        return;
    }
    if (!fileInput.files.length) {
        fileInput.value = '';
        alert("Please select a valid GPX file.");
        return;
    }

    const time = document.getElementById('time').value;
    const filename = fileInput.files[0].name;

    console.log("UPLOAD");

    // Check if required fields are filled
    if (!fileInput.files.length) {
        fileInput.value = '';
        alert("Please select a valid GPX file.");
        return;
    }

    if (!time || time <= 0) {
        alert("Please enter a valid time in minutes.");
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('time', time);

    // Check if the file extension is .gpx
    const fileExtension = fileInput.files[0].name.split('.').pop().toLowerCase();
    if (fileExtension !== 'gpx') {
        fileInput.value = '';
        alert("Please select a valid GPX file.");
        return;
    }

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
        const presetSegments = JSON.parse(presetSegmentsTxt);
        const optimalPaces = JSON.parse(optimalPacesTxt);
        const segmentLengths = JSON.parse(segmentLengthsTxt);
        const coordinates = JSON.parse(coordinatesTxt);

        // console.log("presetSegments", presetSegments);
        // console.log("optimalPaces", optimalPaces);
        // console.log("segmentLengths", segmentLengths);
        // console.log("coordinates", coordinates);

        const courseName = fileInput.files[0].name.split('.')[0];

        // Store all data in sessionStorage
        sessionStorage.setItem('presetSegments', JSON.stringify(presetSegments));
        sessionStorage.setItem('optimalPaces', JSON.stringify(optimalPaces));
        sessionStorage.setItem('segmentLengths', JSON.stringify(segmentLengths));
        sessionStorage.setItem('coordinates', JSON.stringify(coordinates));
        sessionStorage.setItem('courseName', courseName);
        sessionStorage.setItem('targetTime', time);

        // Choose a default segment plan (e.g., first key in presetSegments)
        const defaultPlanName = 'HILL';
        const defaultSegments = presetSegments[defaultPlanName];

        if (!defaultSegments) {
            throw new Error("No default segment plan found.");
        }

        // Store the default segment plan in sessionStorage
        sessionStorage.setItem('segments', JSON.stringify(defaultSegments));
        sessionStorage.setItem('currentPlanName', defaultPlanName);

        // Call updateFiles to generate the necessary files in sessionStorage
        updateFiles();

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
        fileInput.value = '';
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
