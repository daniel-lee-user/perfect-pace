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
        const paces = [];
        const segments = [];

        // Only fetch "segments.txt" if it's the correct file
        if(file.name.split('.')[0] === "Lakefront-Loops-5K") {
    
            // Fetch the segments.txt file
            fetch("segments.txt")
            .then((res) => res.text())
            .then((text) => {
                console.log(text);
    
                // Parse text content into lines
                const lines = text.trim().split('\n');
                lines.forEach(line => {
                    const values = line.split(', ');
                    const segmentIndex = parseInt(values[0], 10);
                    const pace = parseFloat(values[1]);
    
                    // Add pace and segment index to arrays
                    if(!paces.includes(pace)) {
                        paces.push(pace);
                        segments.push(segmentIndex);
                    }
                });
                console.log(paces.length);
                console.log(segments.length);
    
                // Proceed with modifying GeoJSON based on fetched paces
                //console.log(geojson);
                modifyGeoJSON(geojson, paces, segments);
                console.log(geojson);
    
                // Clear the file input value to allow re-uploading the same file
                event.target.value = '';
    
                window.location.href = 'map.html';
            })
            .catch((e) => console.error(e));
        } else {
            // Proceed with modifying GeoJSON without fetched data
            modifyGeoJSON(geojson, paces, segments);
    
            // Clear the file input value to allow re-uploading the same file
            event.target.value = '';
    
            window.location.href = 'map.html';
        }
    };
    
    function modifyGeoJSON(geojson, paces, segments) {
        // Check if we have at least one feature
        if (geojson.features.length === 0) {
            console.error("No features available in the GeoJSON data.");
            return;
        }
        if(paces.length > 0) {
            // Get the coordinates of the original feature (assuming it's a LineString or Polygon)
            const originalFeature = geojson.features[0]; // Assuming only one feature initially
            const originalCoordinates = originalFeature.geometry.coordinates;
        
            // Create an array to store the new features
            const newFeatures = [];
        
            // Add an extra segment to ensure we include the last portion of the coordinates
            segments.push(originalCoordinates.length-1);
            
            // Function to generate a random hex color
            // Not used...
            /*
            function getRandomColor() {
                const letters = '0123456789ABCDEF';
                let color = '#';
                for (let i = 0; i < 6; i++) {
                    color += letters[Math.floor(Math.random() * 16)];
                }
                return color;
            }
            */
            const brightColors = [
                '#FF0000', // Red
                '#00FF00', // Green
                '#0000FF', // Blue
                '#FFFF00', // Yellow
                '#FF00FF', // Magenta
                '#00FFFF', // Cyan
                '#FFA500', // Orange
                '#800080', // Purple
                '#008000', // Dark Green
            ];

            // Loop through the segments array to split coordinates
            for (let i = 0; i < segments.length - 1; i++) {
                const startIdx = segments[i];
                const endIdx = segments[i + 1] + 1;
        
                // Get the slice of coordinates for the current segment
                const segmentCoordinates = originalCoordinates.slice(startIdx, endIdx);

                if (i === segments.length - 2 && document.getElementById('loops').checked) {
                    segmentCoordinates.push(originalCoordinates[0]);
                    // Close the loop for the last segment if it is a loop track
                }

                // Generate a random color for this segment
                //const randomColor = getRandomColor();

                // Create a new feature for this segment
                const newFeature = {
                    type: "Feature",
                    geometry: {
                        type: originalFeature.geometry.type,
                        coordinates: segmentCoordinates
                    },
                    properties: {
                        ...originalFeature.properties,
                        pace: paces[i], // Assign pace, looping if necessary
                        color: brightColors[i % brightColors.length] // Assign random color to the segment
                    }
                };
        
                // Add the new feature to the array
                newFeatures.push(newFeature);
            }
        
            // Replace the original feature with the new segmented features
            geojson.features = newFeatures;
        } else {
            // If no paces, just initialize with random pace
            geojson.features.forEach(feature => {
                feature.properties.pace = Math.floor(Math.random() * 5) + 1; // Random value between 1 and 5
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
    await sleep(3000);

    loadingScreen.style.display = 'none';
}


function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
