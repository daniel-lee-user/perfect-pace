export function updateFiles() {
    // Read required information from sessionStorage
    const presetSegments = JSON.parse(sessionStorage.getItem("presetSegments"));
    const optimalPaces = JSON.parse(sessionStorage.getItem("optimalPaces"));
    const segmentLengths = JSON.parse(sessionStorage.getItem("segmentLengths"));
    const coordinates = JSON.parse(sessionStorage.getItem("coordinates"));
    const courseName = sessionStorage.getItem("courseName");
    const targetTime = sessionStorage.getItem("targetTime");

    if (!optimalPaces || !segmentLengths || !coordinates) {
        console.error("Missing required information in sessionStorage.");
        return;
    }

    const selectedPlanName = document.getElementById('segment-select-widget').value;

    let segments;
    if (selectedPlanName === "CUSTOM") {
        // Fetch custom segments from sessionStorage
        const customSegments = JSON.parse(sessionStorage.getItem("customSegments"));
        if (!customSegments) {
            throw new Error("No custom segments found. Please define custom segments.");
        }
        segments = customSegments;
    } else {
        // Fetch preset segments
        if (!presetSegments) {
            console.error("Preset segments not available.");
            return;
        }
        segments = presetSegments[selectedPlanName];
        if (!segments) {
            throw new Error(`No segment plan found for type: ${selectedPlanName}`);
        }
    }

    // Store the selected segment plan in sessionStorage
    sessionStorage.setItem("segments", JSON.stringify(segments));

    // Update files and map data
    updateGeoData(segments, optimalPaces, coordinates);
    updateSegmentPaces(segments, optimalPaces, segmentLengths, courseName, targetTime);
    updateMiles(segments, optimalPaces, segmentLengths, courseName, targetTime);
    updateKilometers(segments, optimalPaces, segmentLengths, courseName, targetTime);
}

function updateGeoData(segments, optimalPaces, coordinates) {
    const geoData = {
        type: "FeatureCollection",
        features: []
    };

    for (let i = 0; i < segments.length - 1; i++) {
        const start = segments[i];
        const end = segments[i + 1];

        const coords = coordinates.slice(start, end + 1).map(([lat, lon, ele]) => [lon, lat, ele]);
        const pace = optimalPaces[start][end];

        const feature = {
            type: "Feature",
            geometry: {
                type: "LineString",
                coordinates: coords
            },
            properties: {
                pace: pace
            }
        };

        geoData.features.push(feature);
    }

    modifyGeoJSON(geoData);
}

function updateSegmentPaces(segments, optimalPaces, segmentLengths, courseName, targetTime) {
    const segmentPaces = {
        course_name: courseName,
        target_time: targetTime,
        segments: segments.slice(0, -1).map((start, index) => { // Exclude the last segment index
            const next = segments[index + 1]; // Guaranteed to exist since the loop excludes the last segment
            const pace = optimalPaces[start][next];
            const startDistance = segmentLengths.slice(0, start).reduce((a, b) => a + b, 0).toFixed(2);
            const segmentDistance = segmentLengths.slice(start, next).reduce((a, b) => a + b, 0).toFixed(2);

            return {
                segment_num: index,
                start_distance: startDistance,
                pace: pace.toFixed(2),
                distance: segmentDistance
            };
        }),
        total_time: targetTime
    };
    sessionStorage.setItem("segmentPaces", JSON.stringify(segmentPaces));
}

function updateMiles(segments, optimalPaces, segmentLengths, courseName, targetTime) {
    const totalDistance = segmentLengths.reduce((a, b) => a + b, 0.0);
    const nMileMarkers = Math.ceil(totalDistance);

    // Calculate distances for each mile marker
    const distances = Array.from({ length: nMileMarkers }, (_, i) =>
        i === nMileMarkers - 1 ? totalDistance - i : 1
    );
    const cumulativeDistances = segmentLengths.reduce((acc, length) => {
        acc.push((acc.length > 0 ? acc[acc.length - 1] : 0) + length);
        return acc;
    }, []);

    const timePerMile = distances.map((_, mileIndex) => {
        const mileStart = mileIndex;
        const mileEnd = mileIndex + 1;

        let totalLengthInMile = 0;
        let weightedPaceSum = 0;
        // Iterate through segments to find overlaps with the current mile
        for (let segIdx = 0; segIdx < segments.length - 1; segIdx++) {
            const segmentStartIdx = segments[segIdx];
            const segmentEndIdx = segIdx === segments.length - 1 ? segmentLengths.length : segments[segIdx + 1];

            const segmentStart = segmentStartIdx === 0 ? 0 : cumulativeDistances[segmentStartIdx - 1];
            const segmentEnd = cumulativeDistances[segmentEndIdx - 1];

            // Check if the segment overlaps with the mile
            if (segmentEnd <= mileStart || segmentStart >= mileEnd) {
                continue; // No overlap
            }

            // Determine the overlapping portion of the segment within the mile
            const overlapStart = Math.max(segmentStart, mileStart);
            const overlapEnd = Math.min(segmentEnd, mileEnd);
            const overlapLength = overlapEnd - overlapStart;

            // Get the optimal pace for this segment
            const segmentPace = optimalPaces[segmentStartIdx][segmentEndIdx];

            // Accumulate weighted paces
            weightedPaceSum += overlapLength * segmentPace;
            totalLengthInMile += overlapLength;
        }

        // Return time for the mile based on the weighted pace
        return weightedPaceSum;
    });

    const elapsedTime = timePerMile.reduce((acc, time) => {
        acc.push((acc.length > 0 ? acc[acc.length - 1] : 0) + time);
        return acc;
    }, []);

    const milePaces = {
        course_name: courseName,
        target_time: targetTime,
        segments: timePerMile.map((time, mileIndex) => ({
            mile_index: mileIndex,
            pace: (time / distances[mileIndex]).toFixed(2),
            time: time.toFixed(2),
            elapsed_time: elapsedTime[mileIndex].toFixed(2),
            distance: distances[mileIndex].toFixed(2),
        })),
        total_time: targetTime,
    };

    sessionStorage.setItem('milePaces', JSON.stringify(milePaces));
}

function updateKilometers(segments, optimalPaces, segmentLengths, courseName, targetTime) {
    const totalDistance = segmentLengths.reduce((a, b) => a + b, 0.0);
    const nKilometerMarkers = Math.ceil(totalDistance * 1.60934); // Convert miles to kilometers

    // Calculate distances for each kilometer marker
    const distances = Array.from({ length: nKilometerMarkers }, (_, i) =>
        i === nKilometerMarkers - 1 ? totalDistance * 1.60934 - i : 1
    );

    const cumulativeDistances = segmentLengths.reduce((acc, length) => {
        acc.push((acc.length > 0 ? acc[acc.length - 1] : 0) + length * 1.60934); // Convert miles to kilometers
        return acc;
    }, []);

    const timePerKilometer = distances.map((_, kmIndex) => {
        const kmStart = kmIndex
        const kmEnd = (kmIndex + 1)

        let totalLengthInKm = 0;
        let weightedPaceSum = 0;

        // Iterate through segments to find overlaps with the current kilometer
        for (let segIdx = 0; segIdx < segments.length - 1; segIdx++) {
            const segmentStartIdx = segments[segIdx];
            const segmentEndIdx = segIdx === segments.length - 1 ? segmentLengths.length : segments[segIdx + 1];

            const segmentStart = segmentStartIdx === 0 ? 0 : cumulativeDistances[segmentStartIdx - 1];
            const segmentEnd = cumulativeDistances[segmentEndIdx - 1];

            // Check if the segment overlaps with the kilometer
            if (segmentEnd <= kmStart || segmentStart >= kmEnd) {
                continue; // No overlap
            }

            // Determine the overlapping portion of the segment within the kilometer
            const overlapStart = Math.max(segmentStart, kmStart);
            const overlapEnd = Math.min(segmentEnd, kmEnd);
            const overlapLength = overlapEnd - overlapStart;

            // Get the optimal pace for this segment
            const segmentPace = optimalPaces[segmentStartIdx][segmentEndIdx] / 1.60934; // Convert miles to kilometers

            // Accumulate weighted paces
            weightedPaceSum += overlapLength * segmentPace;
            totalLengthInKm += overlapLength;
        }

        // Return time for the kilometer based on the weighted pace
        return weightedPaceSum;
    });

    const elapsedTime = timePerKilometer.reduce((acc, time) => {
        acc.push((acc.length > 0 ? acc[acc.length - 1] : 0) + time);
        return acc;
    }, []);

    const kilometerPaces = {
        course_name: courseName,
        target_time: targetTime,
        segments: timePerKilometer.map((time, kmIndex) => ({
            kilometer_index: kmIndex,
            pace: (time / distances[kmIndex]).toFixed(2),
            time: time.toFixed(2),
            elapsed_time: elapsedTime[kmIndex].toFixed(2),
            distance: distances[kmIndex].toFixed(2),
        })),
        total_time: targetTime,
    };

    sessionStorage.setItem('kilometerPaces', JSON.stringify(kilometerPaces));
}

function modifyGeoJSON(geojson) {
    // Check if we have at least one feature
    if (geojson.features.length === 0) {
        console.error("No features available in the GeoJSON data.");
        return;
    }
    if (("pace" in geojson.features[0].properties)) {
        const brightColors = [
            'rgba(255, 0, 0, 1)',    // Red
            'rgba(255, 255, 0, 1)',  // Yellow
            'rgba(0, 255, 0, 1)',    // Green
            'rgba(0, 255, 255, 1)',  // Cyan
            'rgba(255, 0, 255, 1)',  // Magenta
            'rgba(255, 165, 0, 1)',  // Orange
            'rgba(0, 0, 255, 1)',    // Blue
            'rgba(128, 0, 128, 1)',  // Purple
            'rgba(0, 128, 0, 1)'     // Dark Green
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
}

// Call the function to update files
updateFiles();
