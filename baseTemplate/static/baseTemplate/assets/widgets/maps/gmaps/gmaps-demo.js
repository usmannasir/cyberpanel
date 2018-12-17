$(document).ready(function() {

    map1 = new GMaps({
        div: '#map-basic',
        lat: -12.043333,
        lng: -77.028333
    });

    map2 = new GMaps({
        div: '#map-marker',
        lat: -12.043333,
        lng: -77.028333
    });
    map2.addMarker({
        lat: -12.043333,
        lng: -77.03,
        title: 'Lima',
        details: {
            database_id: 42,
            author: 'HPNeo'
        },
        click: function(e) {
            if (console.log)
                console.log(e);
            alert('You clicked in this marker');
        }
    });
    map2.addMarker({
        lat: -12.042,
        lng: -77.028333,
        title: 'Marker with InfoWindow',
        infoWindow: {
            content: '<p>HTML Content</p>'
        }
    });


    map3 = new GMaps({
        div: '#map-polygon',
        lat: -12.043333,
        lng: -77.028333
    });

    var path = [
        [-12.040397656836609, -77.03373871559225],
        [-12.040248585302038, -77.03993927003302],
        [-12.050047116528843, -77.02448169303511],
        [-12.044804866577001, -77.02154422636042]
    ];

    polygon = map3.drawPolygon({
        paths: path,
        strokeColor: '#BBD8E9',
        strokeOpacity: 1,
        strokeWeight: 3,
        fillColor: '#BBD8E9',
        fillOpacity: 0.6
    });

});

var map;

// Update position
$(document).on('submit', '.edit_marker', function(e) {
    e.preventDefault();

    var $index = $(this).data('marker-index');

    $lat = $('#marker_' + $index + '_lat').val();
    $lng = $('#marker_' + $index + '_lng').val();

    var template = $('#edit_marker_template').text();

    // Update form values
    var content = template.replace(/{{index}}/g, $index).replace(/{{lat}}/g, $lat).replace(/{{lng}}/g, $lng);

    map.markers[$index].setPosition(new google.maps.LatLng($lat, $lng));
    map.markers[$index].infoWindow.setContent(content);

    $marker = $('#markers-with-coordinates').find('li').eq(0).find('a');
    $marker.data('marker-lat', $lat);
    $marker.data('marker-lng', $lng);
});

// Update center
$(document).on('click', '.pan-to-marker', function(e) {
    e.preventDefault();

    var lat, lng;

    var $index = $(this).data('marker-index');
    var $lat = $(this).data('marker-lat');
    var $lng = $(this).data('marker-lng');

    if ($index != undefined) {
        // using indices
        var position = map.markers[$index].getPosition();
        lat = position.lat();
        lng = position.lng();
    } else {
        // using coordinates
        lat = $lat;
        lng = $lng;
    }

    map.setCenter(lat, lng);
});

$(document).ready(function() {
    map = new GMaps({
        div: '#map-interaction',
        lat: -12.043333,
        lng: -77.028333
    });

    GMaps.on('marker_added', map, function(marker) {
        $('#markers-with-index').append('<li><a href="#" class="pan-to-marker" data-marker-index="' + map.markers.indexOf(marker) + '">' + marker.title + '</a></li>');

        $('#markers-with-coordinates').append('<li><a href="#" class="pan-to-marker" data-marker-lat="' + marker.getPosition().lat() + '" data-marker-lng="' + marker.getPosition().lng() + '">' + marker.title + '</a></li>');
    });

    GMaps.on('click', map.map, function(event) {
        var index = map.markers.length;
        var lat = event.latLng.lat();
        var lng = event.latLng.lng();

        var template = $('#edit_marker_template').text();

        var content = template.replace(/{{index}}/g, index).replace(/{{lat}}/g, lat).replace(/{{lng}}/g, lng);

        map.addMarker({
            lat: lat,
            lng: lng,
            title: 'Marker #' + index,
            infoWindow: {
                content: content
            }
        });
    });
});

var panorama;
$(document).ready(function() {
    panorama = GMaps.createPanorama({
        el: '#map-street',
        lat: 42.3455,
        lng: -71.0983
    });
});
