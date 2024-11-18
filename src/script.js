document.getElementById('fileInput').addEventListener('change', async function (event) {
    const fileInput = document.getElementById('fileInput');
    const paceChanges = document.getElementById('paceChanges').value;
    const time = document.getElementById('time').value;
    const isLoop = document.getElementById('loops').checked;
    const algorithm = document.getElementById('plan-type').value;
    const filename = fileInput.files[0].name;
    console.log("UPLOAD");
    if (!fileInput.files.length) {
        document.getElementById('errorMessage').innerText = "Please select a GPX file.";
        fileInput.value = '';
        return;
    }

    // Error message container
    const errorMessage = document.getElementById('errorMessage');

    // Reset error messages
    errorMessage.innerText = "";

    // Check if required fields are filled
    if (!fileInput.files.length) {
        errorMessage.innerText = "Please select a GPX file.";
        fileInput.value = '';
        return;
    }

    if (!paceChanges || paceChanges <= 0) {
        errorMessage.innerText = "Please enter a valid number of pace changes.";
        fileInput.value = '';
        return;
    }

    if (!time || time <= 0) {
        errorMessage.innerText = "Please enter a valid time in minutes.";
        fileInput.value = '';
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('paces', paceChanges);
    formData.append('time', time);
    formData.append('loop', isLoop);
    formData.append('alg', algorithm);

    // Check if the file extension is .gpx
    const fileExtension = fileInput.files[0].name.split('.').pop().toLowerCase();
    if (fileExtension !== 'gpx') {
        errorMessage.textContent = 'Error: Please upload a .gpx file!';
        fileInput.value = '';
        return;
    }

    try {
        document.getElementById('loadingScreen').style.display = 'block';
        
        const url = 'https://perfect-pace-container.0pr6sav0peebr.us-east-2.cs.amazonlightsail.com:5000/upload';
        const response = await fetch(url, {
            method: "POST",
            body: formData
        })

        const blob = await response.blob();
        const zip = await JSZip.loadAsync(blob);

        // Extract the JSON file
        const jsonFile = await zip.file(/.*\.json$/)[0]?.async("text");

        // Extract the miles CSV file
        const mileJSON = await zip.file(/.*_miles\.json$/)[0]?.async("text");

        // Extract the regular segments TXT file
        const segmentsJSON = await zip.file(/.*_segments\.json$/)[0]?.async("text");
        const jsonData = JSON.parse(jsonFile);

        // right now I save the geojson data and text file content to local storage, might 
        // need to change it if this related data becomes > 5MB
        modifyGeoJSON(jsonData);
        // save in localstorage to pass to map
        console.log(segmentsJSON);
        sessionStorage.setItem('segments', segmentsJSON);
        sessionStorage.setItem('miles', mileJSON);

        await deleteFile(paceChanges, time, algorithm, filename);
        //console.log(mileJSON);
        //console.log(segmentsJSON)
    } catch (error) {
        console.error('Error:', error);
        // only feed in regular gpx file if algorithm fails for some reason
        const geojson = toGeoJSON.gpx(xmlDoc);
        modifyGeoJSON(geojson);
    } finally {
        sessionStorage.setItem('filename', filename);
        document.getElementById('loadingScreen').style.display = 'none';
        fileInput.value = '';
        window.location.href = 'map.html';
    }

    function deleteFile(paces, time, algorithm, filename) {
        // Construct the request URL (assuming the route for deletion is '/delete')
        const url = 'http://perfect-pace-container.0pr6sav0peebr.us-east-2.cs.amazonlightsail.com:5000/delete';

        // Send a DELETE request with JSON payload
        fetch(url, {
            method: 'DELETE', // Specify DELETE method
            headers: {
                'Content-Type': 'application/json', // Set content type to JSON
            },
            body: JSON.stringify({
                "paces": paces,         // Pace value
                "time": time,           // Time value
                "alg": algorithm, // Algorithm type (e.g., 'DP' or 'LP')
                "filename": filename    // Filename to delete
            })
        })
            .then(response => response.json()) // Parse the response as JSON
            .then(data => {
                if (data.success) {
                    console.log('File deleted successfully');
                } else {
                    console.error('Error deleting file:', data.error);
                }
            })
            .catch(error => {
                console.error('Error during DELETE request:', error);
            });
    }


    function modifyGeoJSON(geojson) {
        // Check if we have at least one feature
        if (geojson.features.length === 0) {
            console.error("No features available in the GeoJSON data.");
            return;
        }
        if (("pace" in geojson.features[0].properties)) {
            const brightColors = [
                '#FF0000', // Red (Bright)
                '#FFFF00', // Yellow
                '#00FF00', // Green
                '#00FFFF', // Cyan
                '#FF00FF', // Magenta
                '#FFA500', // Orange
                '#0000FF', // Blue
                '#800080', // Purple
                '#008000', // Dark Green (Dark)
            ];
            const paces = geojson.features.map(feature => feature.properties.pace);

            // Sort paces in ascending order (smallest to largest)
            const sortedPaces = [...paces].sort((a, b) => a - b);

            // Find the color corresponding to each pace
            geojson.features.forEach(feature => {
                const pace = feature.properties.pace;

                // Find the index of the pace in the sorted array
                const paceIndex = sortedPaces.indexOf(pace);

                // Map the pace index to a color in the brightColors array
                // Use modulo in case there are more paces than colors
                const color = brightColors[paceIndex % brightColors.length];

                // Assign the color to the feature's properties
                feature.properties.color = color;
            });

            // Loop through the segments array to split coordinates
            console.log("Updated GeoJSON with color assignments:", geojson);
        } else {
            // If no paces, just initialize with random pace
            geojson.features.forEach(feature => {
                feature.properties.pace = Math.floor(Math.random() * 5) + 1; // Random value between 1 and 5
                feature.properties.color = '#0000FF';
            });
        }

        // Add summary to the feature collection
        geojson.properties = {
            label: "pace"
        };

        // Store the modified GeoJSON in local storage
        sessionStorage.setItem('geoData', JSON.stringify(geojson));
        console.log(JSON.stringify(geojson))

        console.log("GeoJSON modified with segmented features and stored.");
    }
});

