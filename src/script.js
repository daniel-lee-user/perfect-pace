document.getElementById('fileInput').addEventListener('change', async function (event) {
    const fileInput = document.getElementById('fileInput');
    const paceChanges = document.getElementById('paceChanges').value;
    const time = document.getElementById('time').value;
    const isLoop = document.getElementById('loops').checked;
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

    // Check if the file extension is .gpx
    const fileExtension = fileInput.files[0].name.split('.').pop().toLowerCase();
    if (fileExtension !== 'gpx') {
        errorMessage.textContent = 'Error: Please upload a .gpx file!';
        fileInput.value = '';
        return;
    }

    try {
        document.getElementById('loadingScreen').style.display = 'block';

        const response = await fetch("http://127.0.0.1:5000/upload", {
            method: "POST",
            body: formData
        })

        const blob = await response.blob();
        const zip = await JSZip.loadAsync(blob);

        // Extract the JSON file
        const jsonFile = await zip.file(/.*\.json$/)[0]?.async("text");

        // Extract the miles CSV file
        const mileCsvFile = await zip.file(/.*_miles\.csv$/)[0]?.async("text");

        // Extract the regular segments TXT file
        const regularTxtFile = await zip.file(/.*_segments\.txt$/)[0]?.async("text");

        const jsonData = JSON.parse(jsonFile);

        // right now I save the geojson data and text file content to local storage, might 
        // need to change it if this related data becomes > 5MB
        modifyGeoJSON(jsonData);
        // save in localstorage to pass to map
        sessionStorage.setItem('textFileContent', regularTxtFile);
        sessionStorage.setItem('mileTextContent', mileCsvFile);
        console.log(mileCsvFile);
        console.log(regularTxtFile)
    } catch (error) {
        console.error('Error:', error);
        // only feed in regular gpx file if algorithm fails for some reason
        const geojson = toGeoJSON.gpx(xmlDoc);
        modifyGeoJSON(geojson);
    } finally {
        document.getElementById('loadingScreen').style.display = 'none';
        fileInput.value = '';
        window.location.href = 'map.html';
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

