L.Control.Elevation = L.Control.extend({
    options: {
        position: "topright",
        theme: "lime-theme",
        width: 600,
        height: 175,
        margins: {
            top: 20,
            right: 50,
            bottom: 30,
            left: 50
        },
        useHeightIndicator: true,
        interpolation: "linear",
        hoverNumber: {
            decimalsX: 3,
            decimalsY: 0,
            formatter: undefined
        },
        xTicks: undefined,
        yTicks: undefined,
        collapsed: false,
        yAxisMin: undefined,
        yAxisMax: undefined,
        forceAxisBounds: false
    },

    onRemove: function (map) {
        this._container = null;
    },

    onAdd: function (map) {
        this._map = map;
        var segmentIndex = this._segmentIndex = [];
        var allPaces = this._allPaces = [];
        var sections = this._sections = [];

        this._sectionColors = [];

        var opts = this.options;
        var margin = opts.margins;
        opts.xTicks = opts.xTicks || Math.round(this._width() / 75);
        opts.yTicks = opts.yTicks || Math.round(this._height() / 30);
        opts.hoverNumber.formatter = opts.hoverNumber.formatter || this._formatter;

        //append theme name on body
        d3.select("body").classed(opts.theme, true);

        var x = this._x = d3.scale.linear()
            .range([0, this._width()]);

        var y = this._y = d3.scale.linear()
            .range([this._height(), 0]);

        var y2 = this._y2 = d3.scale.linear()
            .range([this._height(), 0]);

        var paceOverlay = this._paceOverlay = false;

        var area = this._area = d3.svg.area()
            .interpolate(opts.interpolation)
            .x(function (d) {
                var xDiagCoord = x(d.dist);
                d.xDiagCoord = xDiagCoord;
                return xDiagCoord;
            })
            .y0(this._height())
            .y1(function (d) {
                return y(d.altitude);
            });

        var container = this._container = L.DomUtil.create("div", "elevation");

        this._initToggle();

        var cont = d3.select(container);
        cont.attr("width", opts.width);
        var svg = cont.append("svg");
        svg.attr("width", opts.width)
            .attr("class", "background")
            .attr("height", opts.height)
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        var g = d3.select(this._container).select("svg").select("g");

        this._areapath = g.append("path")
            .attr("class", "area");

        this._sectionsGroup = g.append("g").attr("class", "sections");
        this._verticalLinesGroup = g.append("g").attr("class", "vertical-lines");

        var background = this._background = g.append("rect")
            .attr("width", this._width())
            .attr("height", this._height())
            .style("fill", "none")
            .style("stroke", "none")
            .style("pointer-events", "all");

        this._createSection = function (point) {
            const xVal = this._x.invert(point[0]);
            const yVal = this._y.invert(point[1]);

            this._sections.push({
                x: point[0],
                y: point[1],
                dist: xVal,
                altitude: yVal
            });

            this._sections.sort((a, b) => a.x - b.x);
            this._updateSections();
        };

        this._updateSections = function () {
            this._sectionsGroup.selectAll("*").remove();
            this._verticalLinesGroup.selectAll("*").remove();

            // Check if there are sections, otherwise create a default full-course section
            const fullSections = this._sections.length > 0
                ? [
                    { x: 0, y: 0, dist: this._x.invert(0), altitude: this._y.invert(0) },
                    ...this._sections,
                    { x: this._width(), y: 0, dist: this._x.invert(this._width()), altitude: this._y.invert(0) }
                ]
                : [
                    { x: 0, y: 0, dist: this._x.invert(0), altitude: this._y.invert(0) },
                    { x: this._width(), y: 0, dist: this._x.invert(this._width()), altitude: this._y.invert(0) }
                ];

            // Add vertical lines
            this._verticalLinesGroup.selectAll(".vertical-line")
                .data(this._sections)
                .enter()
                .append("line")
                .attr("class", "vertical-line")
                .attr("x1", d => d.x)
                .attr("x2", d => d.x)
                .attr("y1", 0)
                .attr("y2", this._height())
                .style("stroke", "#000")
                .style("stroke-width", 2);

            // Create shaded sections
            for (let i = 0; i < fullSections.length - 1; i++) {
                const colorIndex = i % this._sectionColors.length;

                this._sectionsGroup.append("rect")
                    .attr("x", fullSections[i].x)
                    .attr("y", 0)
                    .attr("width", fullSections[i + 1].x - fullSections[i].x)
                    .attr("height", this._height())
                    .style("fill", this._sectionColors[colorIndex])
                    .style("pointer-events", "none");
            }
        };

        if (L.Browser.touch) {
            background.on("touchmove.drag", this._dragHandler.bind(this))
                .on("touchstart.drag", this._dragStartHandler.bind(this))
                .on("touchstart.focus", this._mousemoveHandler.bind(this));
            L.DomEvent.on(this._container, 'touchend', this._dragEndHandler, this);
        } else {
            background.on("mousemove.focus", this._mousemoveHandler.bind(this))
                .on("mouseout.focus", this._mouseoutHandler.bind(this))
                .on("mousedown.drag", this._dragStartHandler.bind(this))
                .on("mousemove.drag", this._dragHandler.bind(this));
            L.DomEvent.on(this._container, 'mouseup', this._dragEndHandler, this);
        }

        const controlContainer = L.DomUtil.create('div', 'control-container', container);
        controlContainer.style.backgroundColor = 'white';
        controlContainer.style.padding = '2px 0px';
        controlContainer.style.margin = 'auto';
        controlContainer.style.width = '100%';
        controlContainer.style.display = 'flex';
        controlContainer.style.flexDirection = 'column'; // Use column layout
        controlContainer.style.alignItems = 'center'; // Center items horizontally
        controlContainer.style.gap = '2px'; // Add spacing between items


        // Add radio buttons for display modes
        this._modeDiv = L.DomUtil.create('div', '', controlContainer);
        this._modeDiv.style.display = 'flex';
        this._modeDiv.style.alignItems = 'center';
        this._modeDiv.style.gap = '10px';


        const modes = [
            { id: 'elevationOnly', label: 'Elevation Only' },
            { id: 'showSegments', label: 'Show Segments' },
            { id: 'customSegments', label: 'Custom Segments' }
        ];

        modes.forEach(mode => {
            const modeContainer = L.DomUtil.create('div', '', this._modeDiv);
            const modeRadio = L.DomUtil.create('input', '', modeContainer);
            modeRadio.type = 'radio';
            modeRadio.name = 'displayMode';
            modeRadio.id = mode.id;
            modeRadio.style.marginRight = '5px';

            const submittingSegments = sessionStorage.getItem("submittingSegments") === "true";
            if (mode.id === 'customSegments' && submittingSegments === true || mode.id === 'elevationOnly') {
                modeRadio.checked = true;
            }

            const modeLabel = L.DomUtil.create('label', '', modeContainer);
            modeLabel.htmlFor = mode.id;
            modeLabel.innerText = mode.label;
        });

        // Add event listener for mode change
        this._modeDiv.addEventListener('change', (event) => {
            this._applyModeSelection()
        });

        // Create a div to hold the buttons
        this._buttonContainer = L.DomUtil.create('div', 'button-container', controlContainer);
        this._buttonContainer.style.display = 'none'; // Initially hidden
        this._buttonContainer.style.width = '100%'; // Full width
        this._buttonContainer.style.display = 'flex';
        this._buttonContainer.style.justifyContent = 'center'; // Center buttons horizontally
        this._buttonContainer.style.gap = '10px'; // Add spacing between buttons

        // Checkbox for Move Segments
        const moveDiv = L.DomUtil.create('div', '', this._buttonContainer);
        moveDiv.style.display = 'flex';
        moveDiv.style.alignItems = 'center';
        const moveSectionsCheckbox = L.DomUtil.create('input', '', moveDiv);
        moveSectionsCheckbox.type = 'checkbox';
        moveSectionsCheckbox.id = 'moveSectionsCheckbox';
        const moveSectionsLabel = L.DomUtil.create('label', '', moveDiv);
        moveSectionsLabel.htmlFor = 'moveSectionsCheckbox';
        moveSectionsLabel.innerText = 'Move Segments';
        moveSectionsLabel.style.marginLeft = '5px';

        // Clear Segments Button
        this._clearButton = L.DomUtil.create('button', '', this._buttonContainer);
        this._clearButton.innerHTML = 'Reset Segments';
        this._clearButton.onclick = () => {
            this._applyCurrentSegmentPlan();
        };

        // Submit Segments Button
        this._printSegmentsButton = L.DomUtil.create('button', '', this._buttonContainer);
        this._printSegmentsButton.innerHTML = 'Submit New Segments';
        sessionStorage.setItem("submittingSegments", false);
        this._printSegmentsButton.onclick = () => {
            sessionStorage.setItem("submittingSegments", true);
            // Existing logic for submitting segments
            const allPoints = [
                { dist: 0 },
                ...this._sections,
                { dist: this._x.invert(this._width()) }
            ];
            const unitSelect = document.getElementById('unit-select');
            const unit = unitSelect && unitSelect.value === "imperial" ? "imperial" : "metric";

            const segmentStartDistances = allPoints.map(point => {
                const distance = unit === "imperial" ? point.dist : point.dist / 1.60934; // Convert to miles if imperial
                return parseFloat(distance.toFixed(3)); // Round to 3 decimal places
            });

            const segmentLengths = JSON.parse(sessionStorage.getItem("segmentLengths"));
            if (!segmentLengths) {
                console.error("Missing required information in sessionStorage.");
                return;
            }

            const cumulativeDistances = segmentLengths.reduce((acc, length) => {
                acc.push((acc.length > 0 ? acc[acc.length - 1] : 0) + length);
                return acc;
            }, []);

            const segmentStartIndices = segmentStartDistances.map((startDist, index) => {
                if (index === segmentStartDistances.length - 1) {
                    return segmentLengths.length;
                }
                let closestIndex = 0;
                let minDifference = Infinity;

                cumulativeDistances.forEach((cumDist, idx) => {
                    const difference = Math.abs(cumDist - startDist);
                    if (difference < minDifference) {
                        minDifference = difference;
                        closestIndex = idx;
                    }
                });
                return closestIndex;
            });

            sessionStorage.setItem("customSegments", JSON.stringify(segmentStartIndices));
            const segmentSelectWidget = document.getElementById('segment-select-widget');
            if (segmentSelectWidget) {
                segmentSelectWidget.value = 'CUSTOM';
                segmentSelectWidget.dispatchEvent(new Event('change'));
            }
        };

        // Add instructional text under the buttons
        const instructionsDiv = L.DomUtil.create('div', 'instructions', controlContainer);
        instructionsDiv.style.textAlign = 'center'; // Center-align the text
        instructionsDiv.style.marginTop = '0px'; // Reduce spacing from the buttons
        instructionsDiv.style.fontSize = '10px'; // Make the text slightly smaller
        instructionsDiv.style.lineHeight = '0.25'; // Adjust line height for closer text spacing
        instructionsDiv.style.color = '#333'; // Set the text color
        instructionsDiv.style.display = 'none'; // Hide initially

        instructionsDiv.innerHTML = `
            <p>Click to create a divider, hold <strong>shift</strong> and click to delete.</p>
        `;

        moveSectionsCheckbox.addEventListener('change', () => {
            this._moveSectionsMode = moveSectionsCheckbox.checked;
        });

        L.DomEvent.disableClickPropagation(container); // Prevents dragging of underlying map

        this._xaxisgraphicnode = g.append("g");
        this._yaxisgraphicnode = g.append("g");
        this._yaxisgraphicnode2 = g.append("g");
        this._appendXaxis(this._xaxisgraphicnode);
        this._appendYaxis(this._yaxisgraphicnode);

        if (this._data) {
            this._applyData();
            this._applyCurrentSegmentPlan();
        }

        this._moveSectionsMode = false;
        this._draggedSection = null;

        var focusG = this._focusG = g.append("g");
        this._mousefocus = focusG.append('svg:line')
            .attr('class', 'mouse-focus-line')
            .attr('x2', '0')
            .attr('y2', '0')
            .attr('x1', '0')
            .attr('y1', '0');
        this._focuslabelX = focusG.append("svg:text")
            .style("pointer-events", "none")
            .attr("class", "mouse-focus-label-x");
        this._focuslabelY = focusG.append("svg:text")
            .style("pointer-events", "none")
            .attr("class", "mouse-focus-label-y");

        // Create a label for pace
        this._paceLabel = focusG.append("svg:text")
            .style("pointer-events", "none")
            .attr("class", "pace-label");

        if (this._data) {
            this._applyData();
            this._applyCurrentSegmentPlan();
        }

        background.on("mousemove.focus", this._mousemoveHandler.bind(this))
            .on("mouseout.focus", this._mouseoutHandler.bind(this));

        this._applyModeSelection();

        return container;
    },


    _dragHandler: function () {

        //we don´t want map events to occur here
        d3.event.preventDefault();
        d3.event.stopPropagation();

        this._gotDragged = true;

        this._drawDragRectangle();

    },

    /*
     * Draws the currently dragged rectabgle over the chart.
     */
    _drawDragRectangle: function () {

        if (!this._dragStartCoords) {
            return;
        }

        var dragEndCoords = this._dragCurrentCoords = d3.mouse(this._background.node());

        var x1 = Math.min(this._dragStartCoords[0], dragEndCoords[0]),
            x2 = Math.max(this._dragStartCoords[0], dragEndCoords[0]);

        if (!this._dragRectangle && !this._dragRectangleG) {
            var g = d3.select(this._container).select("svg").select("g");

            this._dragRectangleG = g.append("g");

            this._dragRectangle = this._dragRectangleG.append("rect")
                .attr("width", x2 - x1)
                .attr("height", this._height())
                .attr("x", x1)
                .attr('class', 'mouse-drag')
                .style("pointer-events", "none");
        } else {
            this._dragRectangle.attr("width", x2 - x1)
                .attr("x", x1);
        }

    },

    /*
     * Removes the drag rectangle and zoms back to the total extent of the data.
     */
    _resetDrag: function () {

        if (this._dragRectangleG) {

            this._dragRectangleG.remove();
            this._dragRectangleG = null;
            this._dragRectangle = null;

            this._hidePositionMarker();

            this._map.fitBounds(this._fullExtent);

        }

    },

    /*
     * Handles end of dragg operations. Zooms the map to the selected items extent.
     */
    _dragEndHandler: function () {

        if (!this._dragStartCoords || !this._gotDragged) {
            this._dragStartCoords = null;
            this._gotDragged = false;
            this._resetDrag();
            return;
        }

        this._hidePositionMarker();

        var item1 = this._findItemForX(this._dragStartCoords[0]),
            item2 = this._findItemForX(this._dragCurrentCoords[0]);

        this._fitSection(item1, item2);

        this._dragStartCoords = null;
        this._gotDragged = false;

    },

    _dragStartHandler: function () {

        d3.event.preventDefault();
        d3.event.stopPropagation();

        this._gotDragged = false;

        this._dragStartCoords = d3.mouse(this._background.node());

    },

    /*
     * Finds a data entry for a given x-coordinate of the diagram
     */
    _findItemForX: function (x) {
        var bisect = d3.bisector(function (d) {
            return d.dist;
        }).left;
        var xinvert = this._x.invert(x);
        return bisect(this._data, xinvert);
    },

    /*
     * Finds an item with the smallest delta in distance to the given latlng coords
     */
    _findItemForLatLng: function (latlng) {
        var result = null,
            d = Infinity;
        this._data.forEach(function (item) {
            var dist = latlng.distanceTo(item.latlng);
            if (dist < d) {
                d = dist;
                result = item;
            }
        });
        return result;
    },

    /** Make the map fit the route section between given indexes. */
    _fitSection: function (index1, index2) {

        var start = Math.min(index1, index2),
            end = Math.max(index1, index2);

        var ext = this._calculateFullExtent(this._data.slice(start, end));

        this._map.fitBounds(ext);

    },

    _initToggle: function () {

        /* inspired by L.Control.Layers */

        var container = this._container;

        //Makes this work on IE10 Touch devices by stopping it from firing a mouseout event when the touch is released
        container.setAttribute('aria-haspopup', true);

        if (!L.Browser.touch) {
            L.DomEvent
                .disableClickPropagation(container);
            //.disableScrollPropagation(container);
        } else {
            L.DomEvent.on(container, 'click', L.DomEvent.stopPropagation);
        }

        if (this.options.collapsed) {
            this._collapse();

            if (!L.Browser.android) {
                L.DomEvent
                    .on(container, 'mouseover', this._expand, this)
                    .on(container, 'mouseout', this._collapse, this);
            }
            var link = this._button = L.DomUtil.create('a', 'elevation-toggle', container);
            link.href = '#';
            link.title = 'Elevation';

            if (L.Browser.touch) {
                L.DomEvent
                    .on(link, 'click', L.DomEvent.stop)
                    .on(link, 'click', this._expand, this);
            } else {
                L.DomEvent.on(link, 'focus', this._expand, this);
            }

            this._map.on('click', this._collapse, this);
            // TODO keyboard accessibility
        }
    },

    _expand: function () {
        this._container.className = this._container.className.replace(' elevation-collapsed', '');
    },

    _collapse: function () {
        L.DomUtil.addClass(this._container, 'elevation-collapsed');
    },

    _width: function () {
        var opts = this.options;
        return opts.width - opts.margins.left - opts.margins.right;
    },

    _height: function () {
        var opts = this.options;
        return opts.height - opts.margins.top - opts.margins.bottom;
    },

    /*
     * Fromatting funciton using the given decimals and seperator
     */
    _formatter: function (num, dec, sep) {
        var res;
        if (dec === 0) {
            res = Math.round(num) + "";
        } else {
            res = L.Util.formatNum(num, dec) + "";
        }
        var numbers = res.split(".");
        if (numbers[1]) {
            var d = dec - numbers[1].length;
            for (; d > 0; d--) {
                numbers[1] += "0";
            }
            res = numbers.join(sep || ".");
        }
        return res;
    },

    _appendYaxis: function (y) {
        // Determine the current unit from the unit-select element
        const unitSelect = document.getElementById("unit-select");
        const currentUnit = unitSelect ? unitSelect.value : "metric"; // Default to metric
        const yAxisLabel = currentUnit === "imperial" ? "ft" : "m";

        y.attr("class", "y axis")
            .call(d3.svg.axis()
                .scale(this._y)
                .ticks(this.options.yTicks)
                .orient("left"))
            .append("text")
            .attr("x", -10)
            .attr("y", -5)
            .style("text-anchor", "end")
            .text(yAxisLabel);
    },

    _appendYaxis2: function (y) {
        // Determine the current unit from the unit-select element
        const unitSelect = document.getElementById("unit-select");
        const currentUnit = unitSelect ? unitSelect.value : "metric"; // Default to metric
        const y2AxisLabel = currentUnit === "imperial" ? "mi/min" : "km/min";

        y.attr("class", "y axis")
            .attr("transform", "translate(" + this._width() + " ,0)")
            .call(d3.svg.axis()
                .scale(this._y2)
                .ticks(this.options.yTicks)
                .orient("right")
                .tickFormat((d) => {
                    return this._formatTime(d); // Format pace as HH:MM:SS
                }))
            .append("text")
            .attr("x", 40)
            .attr("y", -5) // Adjusted to move the label upward
            .style("text-anchor", "end")
            .text(y2AxisLabel);
    },

    _appendXaxis: function (x) {
        // Determine the current unit from the unit-select element
        const unitSelect = document.getElementById("unit-select");
        const currentUnit = unitSelect ? unitSelect.value : "metric"; // Default to metric
        const xAxisLabel = currentUnit === "imperial" ? "mi" : "km";

        x.attr("class", "x axis")
            .attr("transform", "translate(0," + this._height() + ")")
            .call(d3.svg.axis()
                .scale(this._x)
                .ticks(this.options.xTicks)
                .orient("bottom"))
            .append("text")
            .attr("x", this._width() + 20)
            .attr("y", 15)
            .style("text-anchor", "end")
            .text(xAxisLabel);
    },

    _updateAxis: function () {
        this._xaxisgraphicnode.selectAll("g").remove();
        this._xaxisgraphicnode.selectAll("path").remove();
        this._xaxisgraphicnode.selectAll("text").remove();
        this._yaxisgraphicnode.selectAll("g").remove();
        this._yaxisgraphicnode.selectAll("path").remove();
        this._yaxisgraphicnode.selectAll("text").remove();
        this._appendXaxis(this._xaxisgraphicnode);
        this._appendYaxis(this._yaxisgraphicnode);
        this._yaxisgraphicnode2.selectAll("g").remove();
        this._yaxisgraphicnode2.selectAll("path").remove();
        this._yaxisgraphicnode2.selectAll("text").remove();
        this._appendYaxis2(this._yaxisgraphicnode2);
    },

    _mouseoutHandler: function () {

        this._hidePositionMarker();
    },

    /*
     * Hides the position-/heigth indication marker drawn onto the map
     */
    _hidePositionMarker: function () {

        if (this._marker) {
            this._map.removeLayer(this._marker);
            this._marker = null;
        }
        if (this._mouseHeightFocus) {
            this._mouseHeightFocus.style("visibility", "hidden");
            this._mouseHeightFocusLabel.style("visibility", "hidden");
        }
        if (this._pointG) {
            this._pointG.style("visibility", "hidden");
        }
        this._focusG.style("visibility", "hidden");

    },

    /*
     * Handles the moueseover the chart and displays distance and altitude level
     */
    _mousemoveHandler: function (d, i, ctx) {
        if (!this._data || this._data.length === 0) {
            return;
        }
        var coords = d3.mouse(this._background.node());
        var opts = this.options;
        var index = this._findItemForX(coords[0]);
        var item = this._data[index];
        // Check if item is defined and contains the necessary properties
        if (!item || typeof item.altitude === 'undefined' || typeof item.dist === 'undefined' || typeof item.latlng === 'undefined') {
            //console.warn("Item not found or missing properties at index:", index);
            return;
        }
        var item = this._data[this._findItemForX(coords[0])],
            alt = item.altitude,
            dist = item.dist,
            ll = item.latlng,
            numY = opts.hoverNumber.formatter(alt, opts.hoverNumber.decimalsY),
            numX = opts.hoverNumber.formatter(dist, opts.hoverNumber.decimalsX);
        this._showDiagramIndicator(item, coords[0]);

        var layerpoint = this._map.latLngToLayerPoint(ll);

        //if we use a height indicator we create one with SVG
        //otherwise we show a marker
        if (opts.useHeightIndicator) {

            if (!this._mouseHeightFocus) {

                var heightG = d3.select(".leaflet-overlay-pane svg")
                    .append("g");
                this._mouseHeightFocus = heightG.append('svg:line')
                    .attr('class', 'height-focus line')
                    .attr('x2', '0')
                    .attr('y2', '0')
                    .attr('x1', '0')
                    .attr('y1', '0');

                var pointG = this._pointG = heightG.append("g");
                pointG.append("svg:circle")
                    .attr("r", 6)
                    .attr("cx", 0)
                    .attr("cy", 0)
                    .attr("class", "height-focus circle-lower");

                this._mouseHeightFocusLabel = heightG.append("svg:text")
                    .attr("class", "height-focus-label")
                    .style("pointer-events", "none");

            }

            var normalizedAlt = this._height() / this._maxElevation * alt;
            var normalizedY = layerpoint.y - normalizedAlt;
            this._mouseHeightFocus.attr("x1", layerpoint.x)
                .attr("x2", layerpoint.x)
                .attr("y1", layerpoint.y)
                .attr("y2", normalizedY)
                .style("visibility", "visible");

            this._pointG.attr("transform", "translate(" + layerpoint.x + "," + layerpoint.y + ")")
                .style("visibility", "visible");

            const unitSelect = document.getElementById("unit-select");
            const currentUnit = unitSelect ? unitSelect.value : "metric"; // Default to metric
            const label = currentUnit === "imperial" ? "min/mi" : "min/km";

            const offsetX = 10; // Adjust this value to move text horizontally
            const offsetY = -5; // Adjust this value to move text vertically

            this._mouseHeightFocusLabel.attr("x", layerpoint.x + offsetX) // Move slightly to the right
                .attr("y", normalizedY + offsetY) // Move slightly above the label
                .text(this._formatTime(item.pace) + ' ' + label)
                .style("visibility", "visible");


        } else {

            if (!this._marker) {

                this._marker = new L.Marker(ll).addTo(this._map);

            } else {

                this._marker.setLatLng(ll);

            }

        }

    },

    /*
     * Parsing of GeoJSON data lines and their elevation in z-coordinate
     */
    _addGeoJSONData: function (coords) {
        if (coords) {
            var data = this._data || [];
            var dist = this._dist || 0;
            var ele = this._maxElevation || 0;

            // Determine the current unit
            const unitSelect = document.getElementById('unit-select');
            const unit = unitSelect && unitSelect.value === "imperial" ? "imperial" : "metric";

            for (var i = 0; i < coords.length; i++) {
                var s = new L.LatLng(coords[i][1], coords[i][0]);
                var e = new L.LatLng(coords[i ? i - 1 : 0][1], coords[i ? i - 1 : 0][0]);
                var newdist = s.distanceTo(e);

                dist += Math.round(newdist / 1000 * 100000) / 100000; // Distance in km
                ele = Math.max(ele, coords[i][2]); // Maximum elevation in meters

                // Convert units if needed
                var convertedDist = unit === "imperial" ? dist / 1.60934 : dist; // km to mi
                var convertedAlt = unit === "imperial" ? coords[i][2] * 3.28084 : coords[i][2]; // m to ft

                data.push({
                    dist: convertedDist,
                    altitude: convertedAlt,
                    x: coords[i][0],
                    y: coords[i][1],
                    latlng: s
                });
            }
            this._dist = dist;
            this._data = data;
            this._maxElevation = unit === "imperial" ? ele * 3.28084 : ele; // Update max elevation
        }
    },

    _addGeoJSONDataPace: function (coords, p) {
        if (coords) {
            var data = this._data || [];
            var dist = this._dist || 0;
            var ele = this._maxElevation || 0;

            // Determine the current unit
            const unitSelect = document.getElementById('unit-select');
            const unit = unitSelect && unitSelect.value === "imperial" ? "imperial" : "metric";

            for (var i = 0; i < coords.length; i++) {
                var s = new L.LatLng(coords[i][1], coords[i][0]);
                var e = new L.LatLng(coords[i ? i - 1 : 0][1], coords[i ? i - 1 : 0][0]);
                var newdist = s.distanceTo(e);

                dist += Math.round(newdist / 1000 * 100000) / 100000; // Distance in km
                ele = Math.max(ele, coords[i][2]); // Maximum elevation in meters

                // Convert units if needed
                var convertedDist = unit === "imperial" ? dist / 1.60934 : dist; // km to mi
                var convertedAlt = unit === "imperial" ? coords[i][2] * 3.28084 : coords[i][2]; // m to ft

                data.push({
                    dist: convertedDist,
                    altitude: convertedAlt,
                    pace: p,
                    x: coords[i][0],
                    y: coords[i][1],
                    latlng: s
                });
            }
            this._dist = dist;
            this._data = data;
            this._maxElevation = unit === "imperial" ? ele * 3.28084 : ele; // Update max elevation
        }
    },

    _addGPXdata: function (coords) {
        if (coords) {
            var data = this._data || [];
            var dist = this._dist || 0;
            var ele = this._maxElevation || 0;

            // Determine the current unit
            const unitSelect = document.getElementById('unit-select');
            const unit = unitSelect && unitSelect.value === "imperial" ? "imperial" : "metric";

            for (var i = 0; i < coords.length; i++) {
                var s = coords[i];
                var e = coords[i ? i - 1 : 0];
                var newdist = s.distanceTo(e);

                dist += Math.round(newdist / 1000 * 100000) / 100000; // Distance in km
                ele = Math.max(ele, s.meta.ele); // Maximum elevation in meters

                // Convert units if needed
                var convertedDist = unit === "imperial" ? dist / 1.60934 : dist; // km to mi
                var convertedAlt = unit === "imperial" ? s.meta.ele * 3.28084 : s.meta.ele; // m to ft

                data.push({
                    dist: convertedDist,
                    altitude: convertedAlt,
                    x: s.lng,
                    y: s.lat,
                    latlng: s
                });
            }
            this._dist = dist;
            this._data = data;
            this._maxElevation = unit === "imperial" ? ele * 3.28084 : ele; // Update max elevation
        }
    },

    _addGPXdataPace: function (coords, p) {
        if (coords) {
            var data = this._data || [];
            var dist = this._dist || 0;
            var ele = this._maxElevation || 0;

            // Determine the current unit
            const unitSelect = document.getElementById('unit-select');
            const unit = unitSelect && unitSelect.value === "imperial" ? "imperial" : "metric";

            for (var i = 0; i < coords.length; i++) {
                var s = coords[i];
                var e = coords[i ? i - 1 : 0];
                var newdist = s.distanceTo(e);

                dist += Math.round(newdist / 1000 * 100000) / 100000; // Distance in km
                ele = Math.max(ele, s.meta.ele); // Maximum elevation in meters

                // Convert units if needed
                var convertedDist = unit === "imperial" ? dist / 1.60934 : dist; // km to mi
                var convertedAlt = unit === "imperial" ? s.meta.ele * 3.28084 : s.meta.ele; // m to ft

                data.push({
                    dist: convertedDist,
                    altitude: convertedAlt,
                    pace: p,
                    x: s.lng,
                    y: s.lat,
                    latlng: s
                });
            }
            this._dist = dist;
            this._data = data;
            this._maxElevation = unit === "imperial" ? ele * 3.28084 : ele; // Update max elevation
        }
    },

    _addData: function (d) {
        var geom = d && d.geometry && d.geometry;
        var i;

        // Get the current unit from the 'unit-select' element
        const unitSelect = document.getElementById("unit-select");
        const currentUnit = unitSelect ? unitSelect.value : "metric"; // Default to metric if not found
        const isImperial = currentUnit === "imperial";

        if (geom && d.properties.pace !== undefined) {
            // Convert pace depending on the unit
            const convertedPace = isImperial
                ? d.properties.pace // Convert min/km to min/mi for imperial
                : d.properties.pace / 1.60934; // Convert min/mi to min/km for metric

            switch (geom.type) {
                case "LineString":
                    var data = this._data || [];
                    const start = data.length;
                    this._segmentIndex.push(start);
                    this._sectionColors.push(
                        d.properties.color.replace(/rgba\((\d+), (\d+), (\d+), [^)]+\)/, 'rgba($1, $2, $3, 0.4)')
                    );
                    this._allPaces.push(convertedPace);
                    this._addGeoJSONDataPace(geom.coordinates, convertedPace);
                    break;

                case "MultiLineString":
                    for (i = 0; i < geom.coordinates.length; i++) {
                        var data = this._data || [];
                        const start = data.length;
                        this._segmentIndex.push(start);

                        this._allPaces.push(convertedPace);
                        this._addGeoJSONDataPace(geom.coordinates[i], convertedPace);
                    }
                    break;

                default:
                    throw new Error("Invalid GeoJSON object.");
            }
        } else if (geom) {
            switch (geom.type) {
                case "LineString":
                    this._addGeoJSONData(geom.coordinates);
                    break;

                case "MultiLineString":
                    for (i = 0; i < geom.coordinates.length; i++) {
                        this._addGeoJSONData(geom.coordinates[i]);
                    }
                    break;

                default:
                    throw new Error("Invalid GeoJSON object.");
            }
        }
    },

    /*
     * Calculates the full extent of the data array
     */
    _calculateFullExtent: function (data) {

        if (!data || data.length < 1) {
            throw new Error("no data in parameters");
        }

        var ext = new L.latLngBounds(data[0].latlng, data[0].latlng);

        data.forEach(function (item) {
            ext.extend(item.latlng);
        });

        return ext;

    },

    /*
     * Add data to the diagram either from GPX or GeoJSON and
     * update the axis domain and data
     */
    addData: function (d, layer) {
        this._addData(d);
        if (this._container) {
            this._applyData();
            this._applyCurrentSegmentPlan();
        }
        if (layer === null && d.on) {
            layer = d;
        }
        if (layer) {
            layer.on("mousemove", this._handleLayerMouseOver.bind(this));
            layer.on("mouseout", this._handleLayerMouseOut.bind(this));
        }
    },

    /*
     * Handles mouseover events of the data layers on the map.
     */
    _handleLayerMouseOver: function (evt) {
        if (!this._data || this._data.length === 0) {
            return;
        }
        var latlng = evt.latlng;
        var item = this._findItemForLatLng(latlng);
        if (item) {
            var x = item.xDiagCoord;
            this._showDiagramIndicator(item, x);
            var layerpoint = this._map.latLngToLayerPoint(item.latlng);
            if (!this._pointM) {
                var heightG = d3.select(".leaflet-overlay-pane svg")
                    .append("g");
                var pointM = this._pointM = heightG.append("g");
                pointM.append("svg:circle")
                    .attr("r", 6)
                    .attr("cx", 0)
                    .attr("cy", 0)
                    .style("fill", "green")
                    .attr("class", "mouseDot circle-lower");
            }
            this._pointM.attr("transform", "translate(" + layerpoint.x + "," + layerpoint.y + ")")
                .style("visibility", "visible");
        }
    },

    _handleLayerMouseOut: function (evt) {
        if (this._pointM) {
            this._pointM.style("visibility", "hidden");
        }
    },

    _showPaceMarkers: function () {
        if (this._paceOverlay) {
            d3.select(this._container).select("svg").selectAll(".pace-line")
                .attr('visibility', 'visible');
            return;
        }
        var g = d3.select(this._container).select("svg").select("g");

        this._segmentIndex.forEach((element, index) => {
            var paceGroup = g.append("g");
            if (index == this._segmentIndex.length - 1) {
                // if its the last index just do the last line to the end
                var xCoordinate = this._data[element].xDiagCoord;
                var paceValue = this._data[element].pace.toFixed(2);
                var yValue = this._y2(paceValue);
                paceGroup.append('svg:line')
                    .attr('class', 'pace-line')
                    .attr('x1', xCoordinate)
                    .attr('y1', yValue)
                    .attr('x2', this._width())
                    .attr('y2', yValue)
                    .attr('stroke', 'red')
                    .attr('visibility', 'visible');
                return;
            }
            var xCoordinate = this._data[element].xDiagCoord;
            var xCoordinate2 = this._data[this._segmentIndex[index + 1]].xDiagCoord;
            var paceValue = this._data[element].pace.toFixed(2);
            var paceValue2 = this._data[this._segmentIndex[index + 1]].pace.toFixed(2);
            var yValue = this._y2(paceValue);
            var yValue2 = this._y2(paceValue2);
            // Group for each pace marker

            // Adding the pace line in red color
            paceGroup.append('svg:line')
                .attr('class', 'pace-line')
                .attr('x1', xCoordinate)
                .attr('y1', yValue)
                .attr('x2', xCoordinate2)
                .attr('y2', yValue)
                .attr('stroke', 'red')
                .attr('visibility', 'visible');
            paceGroup.append('svg:line')
                .attr('class', 'pace-line')
                .attr('x1', xCoordinate2)
                .attr('y1', yValue)
                .attr('x2', xCoordinate2)
                .attr('y2', yValue2)
                .attr('stroke', 'red')
                .attr('visibility', 'visible');
            this._paceOverlay = true;
        });
    },

    _hidePaceMarkers: function () {
        // Hide both lines and labels
        d3.select(this._container).select("svg").selectAll(".pace-line")
            .attr('visibility', 'hidden');
        //d3.select(this._container).select("svg").selectAll(".pace-label-line")
        //    .attr('visibility', 'hidden');
    },

    _showDiagramIndicator: function (item, xCoordinate) {
        var opts = this.options;

        // Get the current unit from the unit-select element
        const unitSelect = document.getElementById('unit-select');
        const unit = unitSelect && unitSelect.value === "imperial" ? "imperial" : "metric";

        // Set visibility for the focus group
        this._focusG.style("visibility", "visible");

        // Update the vertical cursor line position
        this._mousefocus.attr('x1', xCoordinate)
            .attr('y1', 0)
            .attr('x2', xCoordinate)
            .attr('y2', this._height())
            .classed('hidden', false);

        // Get and format the values based on the unit
        const altitude = item.altitude.toFixed(1); // Convert to feet if imperial
        const distance = item.dist.toFixed(2); // Convert to miles if imperial
        const pace = this._formatTime(item.pace);

        // Update labels with the proper units
        this._focuslabelX.attr("x", xCoordinate)
            .text(`${altitude} ${unit === "imperial" ? "ft" : "m"}`);

        this._focuslabelY.attr("y", this._height() - 5)
            .attr("x", xCoordinate)
            .text(`${distance} ${unit === "imperial" ? "mi" : "km"}`);

        this._paceLabel.attr("y", this._height() - 65)
            .attr("x", xCoordinate)
            .text(`${pace} ${unit === "imperial" ? "min/mi" : "min/km"}`);
    },

    _applyData: function () {
        const xdomain = d3.extent(this._data, function (d) {
            return d.dist;
        });

        const ydomain = d3.extent(this._data, function (d) {
            return d.altitude;
        });

        let pacedomain = d3.extent(this._allPaces);
        const opts = this.options;

        // Define a minimum range for the pace axis
        const minPaceRange = 0.75; // Minimum range in pace units (e.g., min/km or min/mi)

        // If the range is too small, adjust it
        if (pacedomain[1] - pacedomain[0] < minPaceRange) {
            const center = (pacedomain[0] + pacedomain[1]) / 2;
            pacedomain = [center - minPaceRange / 2, center + minPaceRange / 2];
        }

        // Add padding around the pace values
        const pacePadding = (pacedomain[1] - pacedomain[0]) * 0.025; // 10% padding
        pacedomain[0] -= pacePadding;
        pacedomain[1] += pacePadding;

        // Adjust elevation axis domain
        if (opts.yAxisMin !== undefined && (opts.yAxisMin < ydomain[0] || opts.forceAxisBounds)) {
            ydomain[0] = opts.yAxisMin;
        }
        if (opts.yAxisMax !== undefined && (opts.yAxisMax > ydomain[1] || opts.forceAxisBounds)) {
            ydomain[1] = opts.yAxisMax;
        }

        // Update the scales
        this._x.domain(xdomain);
        this._y2.domain(pacedomain);
        this._y.domain(ydomain);

        // Apply the data to the area path
        this._areapath.datum(this._data)
            .attr("d", this._area);

        // Update the axes
        this._updateAxis();

        // Update the full extent for the map
        this._fullExtent = this._calculateFullExtent(this._data);
    },

    /*
     * Reset data
     */
    _clearData: function () {
        this._data = null;
        this._dist = null;
        this._maxElevation = null;
    },

    /*
     * Reset data and display
     */
    clear: function () {

        this._clearData();

        if (!this._areapath) {
            return;
        }

        // workaround for 'Error: Problem parsing d=""' in Webkit when empty data
        // https://groups.google.com/d/msg/d3-js/7rFxpXKXFhI/HzIO_NPeDuMJ
        //this._areapath.datum(this._data).attr("d", this._area);
        this._areapath.attr("d", "M0 0");

        this._x.domain([0, 1]);
        this._y.domain([0, 1]);
        this._updateAxis();
    },

    _formatTime: function (minutes) {
        const totalSeconds = Math.floor(minutes * 60);
        const hours = Math.floor(totalSeconds / 3600);
        const minutesPart = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        if (hours === 0) {
            return `${minutesPart}:${String(seconds).padStart(2, '0')}`;
        } else {
            return `${hours}:${String(minutesPart).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }
    },

    _applyCurrentSegmentPlan: function () {
        // Retrieve the segment indices from sessionStorage
        const segments = JSON.parse(sessionStorage.getItem("segments"));

        if (!segments || segments.length < 2) {
            console.error("Segment data is missing or insufficient in sessionStorage.");
            return;
        }

        // Clear the existing sections
        this._sections = [];
        this._updateSections();

        // Exclude the first and last segment indices
        const segmentBoundaries = segments.slice(1, -1); // Remove the first and last indices

        // Calculate and apply sections based on the filtered segment indices
        segmentBoundaries.forEach(segmentIndex => {
            if (segmentIndex < 0 || segmentIndex >= this._data.length) {
                return;
            }

            // Calculate the x-coordinate on the graph
            const segmentData = this._data[segmentIndex];
            const xCoord = this._x(segmentData.dist); // Convert distance to x-pixel coordinate
            const yCoord = this._y(segmentData.altitude); // Convert altitude to y-pixel coordinate

            // Create the section on the graph
            this._createSection([xCoord, yCoord]);
        });

        this._applyModeSelection();
    },

    _hideSegmentsAndPaces: function () {
        // Clear segments and paces
        this._sectionsGroup.selectAll("*").remove();
        this._verticalLinesGroup.selectAll("*").remove();
        this._hidePaceMarkers(); // Use existing method to hide paces
        this._moveSectionsMode = false;
    },

    _showSegmentsAndPaces: function () {
        // Clear existing elements
        this._sectionsGroup.selectAll("*").remove();
        this._verticalLinesGroup.selectAll("*").remove();

        const fullSections = this._sections.length > 0
            ? [
                { x: 0, dist: this._x.invert(0) },
                ...this._sections.map(section => ({
                    x: section.x,
                    dist: this._x.invert(section.x),
                })),
                { x: this._width(), dist: this._x.invert(this._width()) }
            ]
            : [
                { x: 0, dist: this._x.invert(0) },
                { x: this._width(), dist: this._x.invert(this._width()) }
            ];

        // Iterate over each segment
        for (let i = 0; i < fullSections.length - 1; i++) {
            const colorIndex = i % this._sectionColors.length;

            // Start and end points for the current segment
            const startX = fullSections[i].x;
            const endX = fullSections[i + 1].x;

            // Determine the segment's pace (if available)
            const startIndex = this._segmentIndex[i] || 0;
            const segmentPace = this._data[startIndex]?.pace || 0; // Default to 0 if undefined
            const yPace = this._y2(segmentPace); // Convert pace to y-coordinate
            const rectHeight = this._height() - yPace; // Height from pace to the bottom
            // Draw the single rectangle for the segment
            this._sectionsGroup.append("rect")
                .attr("x", startX)
                .attr("y", yPace) // Start at the pace height
                .attr("width", endX - startX) // Width of the segment
                .attr("height", rectHeight) // Height from pace to the bottom
                .style("fill", this._sectionColors[colorIndex]) // Fill with section color
                .style("stroke", "black") // Black border
                .style("stroke-width", 2)
                .style("pointer-events", "none");
        }

        this._moveSectionsMode = false; // Disable section editing mode
    },

    _findClosestIndex: function (distance) {
        // Find the index of the data point closest to the given distance
        let closestIndex = 0;
        let minDifference = Infinity;

        this._data.forEach((point, index) => {
            const difference = Math.abs(point.dist - distance);
            if (difference < minDifference) {
                minDifference = difference;
                closestIndex = index;
            }
        });

        return closestIndex;
    },

    _enableCustomSegments: function () {
        // Allow editing of segments
        this._updateSections(); // Show existing segments
        this._hidePaceMarkers(); // Use existing method to hide paces

        this._background.on("click", (event) => {
            const mouseCoords = d3.mouse(this._background.node());
            if (d3.event.shiftKey) {
                const nearestSectionIndex = this._sections.findIndex(section =>
                    Math.abs(section.x - mouseCoords[0]) < 10
                );

                if (nearestSectionIndex !== -1) {
                    this._sections.splice(nearestSectionIndex, 1);
                    this._updateSections();
                }
            } else if (!this._moveSectionsMode) {
                const randomColor = `rgba(${Math.floor(Math.random() * 256)}, ${Math.floor(Math.random() * 256)}, ${Math.floor(Math.random() * 256)}, 0.4)`;

                // Push the random color with opacity 0.4 to sectionColors
                this._sectionColors.push(randomColor);    
                this._createSection(mouseCoords);
            }
        });

        this._background.on("mousedown", (event) => {
            if (this._moveSectionsMode) {
                const mouseCoords = d3.mouse(this._background.node());
                const nearestSection = this._sections.find(section =>
                    Math.abs(section.x - mouseCoords[0]) < 10
                );

                if (nearestSection) {
                    this._draggedSection = nearestSection;
                }
            }
        });

        this._background.on("mousemove", (event) => {
            if (this._moveSectionsMode && this._draggedSection) {
                const mouseCoords = d3.mouse(this._background.node());

                this._draggedSection.x = mouseCoords[0];
                this._draggedSection.dist = this._x.invert(mouseCoords[0]);

                this._sections.sort((a, b) => a.x - b.x);

                this._updateSections();
            }
        });

        this._background.on("mouseup", (event) => {
            this._draggedSection = null;
        });

    },

    _applyModeSelection: function () {
        const modeDiv = this._modeDiv;
        if (!modeDiv) {
            console.error('ModeDiv not found');
            return;
        }

        const selectedMode = modeDiv.querySelector('input[name="displayMode"]:checked');
        if (!selectedMode) {
            console.error('No mode selected. Defaulting to elevation only.');
            this._hideSegmentsAndPaces();
            return;
        }

        // Access buttons and container using `this`
        const buttonContainer = this._buttonContainer;
        const instructionsDiv = this._container.querySelector('.instructions');

        // Apply behavior based on the selected mode
        switch (selectedMode.id) {
            case 'elevationOnly':
                this._hideSegmentsAndPaces();
                buttonContainer.style.display = 'none';
                if (instructionsDiv) instructionsDiv.style.display = 'none';
                break;
            case 'showSegments':
                this._showSegmentsAndPaces();
                buttonContainer.style.display = 'none';
                if (instructionsDiv) instructionsDiv.style.display = 'none';
                break;
            case 'customSegments':
                this._enableCustomSegments();
                buttonContainer.style.display = 'flex';
                if (instructionsDiv) instructionsDiv.style.display = 'block';
                break;
            default:
                console.error('Invalid mode selected. Defaulting to elevation only.');
                this._hideSegmentsAndPaces();
                buttonContainer.style.display = 'none';
                if (instructionsDiv) instructionsDiv.style.display = 'none';
        }
    }

});

L.control.elevation = function (options) {
    return new L.Control.Elevation(options);
};
