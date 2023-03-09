function clearAllMarkers(markers){
    // Clear out the old markers.
    markers.forEach((marker) => {
        marker.setMap(null);
    });
}

function placeMarker(location) {
    if ( userMarker ) {
        userMarker.setPosition(location);
        userMarker.setMap(map);
        userMarker.setIcon('http://maps.google.com/mapfiles/ms/icons/red-dot.png')
        userMarker.setDraggable(true);
    } else {
        userMarker = new google.maps.Marker({
        position: location,
        map: map,
        icon: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png',
        draggable: true
        });
    }
    const infowindow = new google.maps.InfoWindow()
    const geocoder = new google.maps.Geocoder()
    geocoder.geocode({location:location})
    .then((response) => {
        if(response.results[0]){
            if(currinfowindow){
                currinfowindow.close();
            }
            currinfowindow = infowindow
            infowindow.setContent(response.results[0].formatted_address);
            infowindow.open(map, userMarker);
        }else{
            infowindow.setContent('No results found');
            infowindow.open(map, userMarker);
        }
    })

    
}

function initMap(id) {
    map = new google.maps.Map(document.getElementById(id), {
        center: getLatLng(),
        zoom: 3,
        mapTypeId: 'satellite'
    });
    //search-radius-form controls
    const controlDiv = document.createElement('DIV');
    controlDiv.id = "search_rad_controls";

    // Create the search box and link it to the UI element.
    const controlInput = document.createElement('input');
    controlInput.id = "pac-input";
    controlInput.className = "controls mt-2 form-control";
    controlInput.placeholder = 'Search any keyword..'
    controlInput.style = 'width: 170% !important;'

    controlDiv.appendChild(controlInput);
    map.controls[google.maps.ControlPosition.TOP_LEFT].push(controlDiv);

    const searchBox = new google.maps.places.SearchBox(controlInput);

    // Bias the SearchBox results towards current map's viewport.
    map.addListener("bounds_changed", () => {
        searchBox.setBounds(map.getBounds());
    });

    let markers = [];

    // Listen for the event fired when the user selects a prediction and retrieve
    // more details for that place.
    searchBox.addListener("places_changed", () => {
        const places = searchBox.getPlaces();

        if (places.length == 0) {
        return;
        }

        // Clear out the old markers.
        clearAllMarkers(markers)
        markers = [];

        // For each place, get the icon, name and location.
        const bounds = new google.maps.LatLngBounds();

        places.forEach((place, index) => {
            if (!place.geometry || !place.geometry.location) {
                console.log("Returned place contains no geometry");
                return;
            }

            const icon = {
                url: index == 0 ? 'http://maps.google.com/mapfiles/ms/icons/red-dot.png' : place.icon,
                size: new google.maps.Size(90, 90),
                origin: new google.maps.Point(0, 0),
                anchor: new google.maps.Point(17, 34),
                scaledSize: new google.maps.Size(25, 25),
            };
            
            let marker = new google.maps.Marker({
                map,
                icon,
                title: place.name,
                position: place.geometry.location,
                animation:google.maps.Animation.DROP
            })
            
            // Create a marker for each place.
            markers.push(
                marker
            );

            //on click marker zoom in
            marker.addListener("click", () => {
                map.setZoom(17);
                map.setCenter(marker.getPosition());
            });

                if (place.geometry.viewport) {
                    // Only geocodes have viewport.
                    bounds.union(place.geometry.viewport);
                } else {
                    bounds.extend(place.geometry.location);
                }
        });
        map.fitBounds(bounds);
        userMarker = markers.length ? markers[0] : null
    }); // searchBox.addListener

    //place marker when user clicks on map
    google.maps.event.addListener(map, 'click', function(event) {
        clearAllMarkers(markers)
        placeMarker(event.latLng);
    });
}// initMap end