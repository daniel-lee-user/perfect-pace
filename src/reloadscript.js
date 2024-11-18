document.getElementById('submitBtn').addEventListener('click', async function (event) {
    event.preventDefault(); // Prevents the form from submitting and reloading immediately

    const paceChanges = document.getElementById('paceChanges').value;
    const time = document.getElementById('time').value;
    const isLoop = document.getElementById('loops').checked;
    const algorithm = document.getElementById('plan-type').value;
    const filename = sessionStorage.getItem("filename");
    console.log(filename);

    if (!paceChanges || paceChanges <= 0) {
        alert("Please enter a valid number of pace changes.");
        return;
    }

    if (!time || time <= 0) {
        alert("Please enter a valid time in minutes.");
        return;
    }

    const formData = new FormData();
    formData.append('filename', filename);
    formData.append('paces', paceChanges);
    formData.append('time', time);
    formData.append('loop', isLoop);
    formData.append('alg', algorithm);

    try {
        document.getElementById('loadingScreen').style.display = 'block';

        const url = 'https://perfect-pace-container.0pr6sav0peebr.us-east-2.cs.amazonlightsail.com/upload';
        const response = await fetch(url, {
            method: "POST",
            body: formData,
            signal: AbortSignal.timeout(30000)
        });

        const blob = await response.blob();
        const zip = await JSZip.loadAsync(blob);
        const jsonFile = await zip.file(/.*\.json$/)[0]?.async("text");
        const mileJSON = await zip.file(/.*_miles\.json$/)[0]?.async("text");
        const segmentsJSON = await zip.file(/.*_segments\.json$/)[0]?.async("text");
        const jsonData = JSON.parse(jsonFile);

        modifyGeoJSON(jsonData);
        sessionStorage.setItem('segments', segmentsJSON);
        sessionStorage.setItem('miles', mileJSON);

        await deleteFile(paceChanges, time, algorithm, filename);
    } catch (error) {
        console.error('Error:', error);
    } finally {
        sessionStorage.setItem('filename', filename);
        document.getElementById('loadingScreen').style.display = 'none';
        location.reload();
    }
});

function deleteFile(paces, time, algorithm, filename) {
    // Construct the request URL (assuming the route for deletion is '/delete')
    const url = 'https://perfect-pace-container.0pr6sav0peebr.us-east-2.cs.amazonlightsail.com/delete';

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
        }),
        signal: AbortSignal.timeout(30000)
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
    const brightColors = ['#FF0000', '#FFFF00', '#00FF00', '#00FFFF', '#FF00FF', '#FFA500', '#0000FF', '#800080', '#008000'];
    const paces = geojson.features.map(feature => feature.properties.pace);
    const sortedPaces = [...paces].sort((a, b) => a - b);

    geojson.features.forEach(feature => {
        const pace = feature.properties.pace;
        const paceIndex = sortedPaces.indexOf(pace);
        const color = brightColors[paceIndex % brightColors.length];
        feature.properties.color = color;
    });

    geojson.properties = { label: "pace" };
    sessionStorage.setItem('geoData', JSON.stringify(geojson));
    console.log("GeoJSON modified with segmented features and stored.");
}
