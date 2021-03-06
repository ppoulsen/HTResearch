/**
 * Provides a means of initializing the heatmap of anti-trafficking organizations on a Google Map.
 *
 * @module heatmap
 */
define(['jquery', 'async!https://maps.googleapis.com/maps/api/js?sensor=false&libraries=visualization'], function($) {
    'use strict';

    var heatMap,
        map,
        orgCoordinates = [],
        heatMapGradient = [
        'rgba(0, 255, 255, 0)',
        'rgba(0, 255, 255, 1)',
        'rgba(0, 191, 255, 1)',
        'rgba(0, 127, 255, 1)',
        'rgba(0, 63, 255, 1)',
        'rgba(0, 0, 255, 1)',
        'rgba(0, 0, 223, 1)',
        'rgba(0, 0, 191, 1)',
        'rgba(0, 0, 159, 1)',
        'rgba(0, 0, 127, 1)',
        'rgba(63, 0, 91, 1)',
        'rgba(127, 0, 63, 1)',
        'rgba(191, 0, 31, 1)',
        'rgba(255, 0, 0, 1)'
        ],
        heatMapRadius = 30;

    //Creates the Organization Density information using cached coordinates from the server
    function createHeatMap() {
        var pointArray = new google.maps.MVCArray(orgCoordinates);
        heatMap = new google.maps.visualization.HeatmapLayer({
            data: pointArray,
            radius: heatMapRadius,
            gradient: heatMapGradient
        });
        heatMap.setMap(map);
    }

    //Use an AJAX request to retrieve cached coordinate information
    function loadCoordinates(success_cb) {
        // Clear array
        orgCoordinates.length = 0;
        $.ajax({
            type: 'GET',
            url: '/api/heatmap-coordinates/',
            data: {
                'csrfmiddlewaretoken': $('input[name=csrfmiddlewaretoken]').val()
            },
            success: function (json_string) {
                var coordinates = $.parseJSON(json_string);
                var i;
                for (i = 0; i < coordinates.length; i++) {
                    var coord = coordinates[i];
                    var lat = coord[0];
                    var lng = coord[1];
                    var gCoord = new google.maps.LatLng(lat, lng);
                    orgCoordinates.push(gCoord);
                }
                // Rebuild heatmap
                success_cb();
            },
            dataType: 'html'
        });
    }

    function initHeatmap() {
        // call load coordinates with a callback to createHeatMap
        loadCoordinates(createHeatMap);
    }

    //Toggles the organization density feature
    function toggleHeatMap() {
        // map is a variable from the file index.js
        if (heatMap != null) {
            heatMap.setMap(heatMap.getMap() ? null : map);
        }
    }

    /**
     * Initializes the heatmap.
     * @param {object} gMap The Google Maps instance to use.
     */
    function initialize(gMap) {
        map = gMap;

        initHeatmap();

        var heatmap_control_div = document.createElement('div');
        $(heatmap_control_div).attr('id', 'heatmap-button');

        var heatmap_toggle_control = document.createElement('button');
        $(heatmap_toggle_control).addClass('btn');
        $(heatmap_toggle_control).addClass('btn-default');
        $(heatmap_toggle_control).addClass('btn-sm');
        $(heatmap_toggle_control).addClass('active');
        $(heatmap_toggle_control).attr('data-toggle', 'button');
        $(heatmap_toggle_control).html('<span class="fa fa-building-o"></span> Organization Density');
        heatmap_control_div.appendChild(heatmap_toggle_control);

        google.maps.event.addDomListener(heatmap_toggle_control, 'click', function () {
            $(this).attr("disabled", "true");
            toggleHeatMap();
            $(this).removeAttr("disabled");
        });
        heatmap_control_div.index = -1;
        map.controls[google.maps.ControlPosition.LEFT_TOP].push(heatmap_control_div);
    }

    return { initialize: initialize };
});