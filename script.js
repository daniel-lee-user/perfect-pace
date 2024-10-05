document.getElementById('fileInput').addEventListener('change', function(event) {
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

    reader.onload = function(e) {
        // what to do with file contents
        const fileContents = e.target.result;

        // Parse the GPX file into an XML DOM
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(fileContents, "text/xml");
        const geojson = toGeoJSON.gpx(xmlDoc);
        // after creating the geojson, we would probably modify it with 
        // values from perfect pace for each segment (we would split up the segments)
        // Modify the GeoJSON features
        geojson.features.forEach(feature => {
            // Add a random attributeType value (1 to 5)
            feature.properties.attributeType = Math.floor(Math.random() * 5) + 1; // Random value between 1 and 5
        });

        // Add summary to the feature collection
        geojson.properties = {
            label: "Pace"
        };

        localStorage.setItem('geoData', JSON.stringify(geojson));

        // Clear the file input value to allow re-uploading the same file
        event.target.value = '';

        // change window to map.html
        window.location.href = 'map.html';
    };

    reader.readAsText(file);
});
