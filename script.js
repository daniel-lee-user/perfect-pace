document.getElementById('fileInput').addEventListener('change', async function(event) {
    const file = event.target.files[0];
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = ''; // Clear any previous error messages

    if (!file) {
        return;
    }

    // Check if the file extension is .gpx
    const fileExtension = file.name.split('.').pop().toLowerCase();
    if (fileExtension !== 'gpx') {
        errorMessage.textContent = 'Error: Please upload a .gpx file!';
        return;
    }


    const reader = new FileReader();

    reader.onload = async function(e) {
        // what to do with file contents
        await showLoadingScreen();
        const fileContents = e.target.result;
    
        // Parse the GPX file into an XML DOM
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(fileContents, "text/xml");
        const geojson = toGeoJSON.gpx(xmlDoc);

        // Only fetch "segments.json" if it's been generated by the 
        if(file.name.split('.')[0] === "Lakefront-Loops-5K") {
    
            // Fetch the segments.txt file
            const response = await fetch('segments.json');

            // Check if the response is OK (status code 200)
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const jsonFile = await response.json();
            console.log(jsonFile)
            modifyGeoJSON(jsonFile);
            console.log(JSON.stringify(geojson))
            console.log(JSON.stringify(jsonFile))
    
            // Clear the file input value to allow re-uploading the same file
            event.target.value = '';
    
            window.location.href = 'map.html';
        } else {
            // Proceed with modifying GeoJSON without fetched data
            modifyGeoJSON(geojson);
    
            // Clear the file input value to allow re-uploading the same file
            event.target.value = '';
    
            window.location.href = 'map.html';
        }
    };
    
    function modifyGeoJSON(geojson) {
        // Check if we have at least one feature
        if (geojson.features.length === 0) {
            console.error("No features available in the GeoJSON data.");
            return;
        }
        if(("pace" in geojson.features[0].properties)) {
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
                feature.properties.color = '#00FF00';
            });
        }
    
        // Add summary to the feature collection
        geojson.properties = {
            label: "pace"
        };
    
        // Store the modified GeoJSON in local storage
        localStorage.setItem('geoData', JSON.stringify(geojson));
    
        console.log("GeoJSON modified with segmented features and stored.");
    }
       
    
    reader.readAsText(file);
});

async function showLoadingScreen() {
    // Display the loading screen
    const loadingScreen = document.getElementById('loadingScreen');
    loadingScreen.style.display = 'block';
    await sleep(10);

    loadingScreen.style.display = 'none';
}


function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
