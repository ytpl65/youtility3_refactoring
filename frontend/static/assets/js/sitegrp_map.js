var d2geocoder;
var d2map;
var d2oms;
var d2markersArray = [];

    /*Initializes the map and related objects for the application.
        This function creates a Google Map centered on a specified location, 
        initializes an OverlappingMarkerSpiderfier instance to manage overlapping markers,
        creates a Geocoder object for geocoding purposes, and sets the directionsRenderer 
        on the map.*/
    function d2InitializeMap() {
        var directionsRenderer = new google.maps.DirectionsRenderer({
            suppressMarkers: true,
          });
        d2map = new google.maps.Map(document.getElementById("d2Map"), {
          zoom: 2,
          center: new google.maps.LatLng(23.248917, 77.651367), //locations[0],
          mapTypeId: google.maps.MapTypeId.ROADMAP,
        });
        d2oms = new OverlappingMarkerSpiderfier(d2map, {
          markersWontMove: true,
          markersWontHide: true,
          keepSpiderfied: true,
          nearbyDistance: 10,
          legWeight: 5,
        });
        d2geocoder = new google.maps.Geocoder();
        directionsRenderer.setMap(d2map);
      }
    
    /*Configures the directions request based on provided data.
        This function takes an array of data points and an optional `optimize` flag. 
        It parses the GPS coordinates from each data point, creating objects for the 
        origin, destination, and optional waypoints. The function then returns an 
        object suitable for use with Google Maps Directions Service.*/
    function directionconfig(data, optimize) {
        const gpsStartCoords = JSON.parse(data[0]["gps"])["coordinates"];
        const gpsEndCoords = JSON.parse(data[data.length - 1]["gps"])["coordinates"];
        const startPoint = { lat: Number(gpsStartCoords[1]), lng: Number(gpsStartCoords[0]) };
        const endPoint = { lat: Number(gpsEndCoords[1]), lng: Number(gpsEndCoords[0]) };

        const wayPoints = data.slice(1, -1).map(item => {
            const wpCoords = JSON.parse(item["gps"])["coordinates"];
            return {
                location: new google.maps.LatLng(Number(wpCoords[1]), Number(wpCoords[0])),
                stopover: true,
            };
        });
        return {
            origin: startPoint,
            destination: endPoint,
            waypoints: wayPoints,
            travelMode: "DRIVING",
            optimizeWaypoints: optimize,
        };
    }
    
    /*Calculates distance and duration for optimized waypoints based on Directions Service response.
        This function takes a response object from the Google Maps Directions Service 
        and an array of optimized waypoints (`data`). It iterates through the legs of 
        the first route in the response, calculating distance in kilometers (rounded 
        to two decimal places) and duration in minutes (rounded to nearest integer). 
        The calculated distance and duration are then added as properties ("distance" 
        and "expirytime") to the corresponding waypoint objects in the `data` array. 
        Finally, the modified `data` array is returned.*/
    function calculateDistanceDuration(response, data) {
        optimizedPoints = data;
        var DDE = [];
        var legs = response.routes[0].legs;
        for (var i = 0; i < legs.length; i++) {
            let l = [];
            optimizedPoints[i + 1]["distance"] = parseFloat(
            legs[i]["distance"]["value"] / 1000
            ).toFixed(2);
            l.push(optimizedPoints[i + 1]["duration"]);
            optimizedPoints[i + 1]["expirytime"] = parseInt(
            legs[i]["duration"]["value"] / 60,
            10
            );
            l.push(optimizedPoints[i + 1]["expirytime"]);
            DDE.push(l);
        }
        return optimizedPoints;
        }
    
    /*// Calculates total distance and travel time for a set of assigned sites.
    function calculate_distance_and_time(assigned_sites,optimize=false,callback){
        assigned_sites = tabAssigned_sites.rows().data().toArray()
        console.log('assigned sites',assigned_sites)
        var directionService = new google.maps.DirectionsService();
        if (assigned_sites.length > 1) {
            directionService.route(
                directionconfig(assigned_sites,optimize),
                function (response, status) {
                    if (status === "OK") {
                    data = calculateDistanceDuration(response, assigned_sites);
                    const km = " kms"
                    const min = " mins"
                    const extract_distance = [];
                    const extract_time = [];
                    for(const item of data) {
                        const num1 = Number(item['distance'])
                        const num2 = Number(item['expirytime'])
                        extract_distance.push(num1);
                        extract_time.push(num2);
                    }
                    const filtered_distance = extract_distance.slice(1)
                    const filtered_duration = extract_time.slice(1)
                    const distance = filtered_distance.reduce((acc, val) => acc + val, 0)
                    const total_duration = filtered_duration.reduce((acc,val) => acc + val,0) + min
                    const total_distance = distance.toFixed(2) + km
                    isDirectionSaved = true;

                    callback(total_duration, total_distance);

                    }
                     else {
                    show_error_alert(
                        `Directions request failed due to ${status}, Please check your coordinates of your checkpoints`,
                        "GMaps Error!"
                    );
                    }
                }

            );
        }

    }*/

    // Function to handle distance calculation
    function calculate_distance_and_time(assigned_sites, optimize=false, callback) {
        try {
            const sites = assigned_sites.rows().data().toArray();
            
            // Check if we have enough points to calculate distance
            if (!sites || sites.length < 2) {
                console.warn('Not enough valid sites to calculate distance');
                return;
            }

            const directionService = new google.maps.DirectionsService();
            
            // Get valid points with GPS data
            const validSites = sites.filter(site => {
                const latLng = getLatLngFromGPSData(site.gps);
                return latLng !== null;
            });

            if (validSites.length < 2) {
                console.warn('Not enough valid GPS coordinates to calculate distance');
                return;
            }

            directionService.route(
                directionconfig(validSites, optimize),
                function(response, status) {
                    if (status === "OK") {
                        const data = calculateDistanceDuration(response, validSites);
                        const km = " kms";
                        const min = " mins";
                        
                        // Extract and calculate distances
                        const distances = data
                            .slice(1)
                            .map(item => Number(item.distance || 0));
                        
                        const durations = data
                            .slice(1)
                            .map(item => Number(item.expirytime || 0));

                        const totalDistance = distances.reduce((a, b) => a + b, 0).toFixed(2) + km;
                        const totalDuration = durations.reduce((a, b) => a + b, 0) + min;

                        callback(totalDuration, totalDistance);
                    } else {
                        console.warn('Directions request failed:', status);
                    }
                }
            );
        } catch (error) {
            console.error('Error calculating distance and time:', error);
        }
    }

    //Add distance and duration Data to innerHTML
    function handleDistanceAndTimeData(duration, distance) {
        const distance_duration = document.getElementById("distance_duration_button")
        distance_duration.classList.remove("d-none");
        document.getElementById("total_duration_display").innerHTML = duration;
        document.getElementById("total_distance_display").innerHTML = distance;
    }   

    //returns assgined sites starts initializing map
    function get_assigned_sites_data(table, id){
        const params = {url:`${urlname}?action=loadSites&id=${id}`, 'beforeSend':function(){}
        }
        fire_ajax_get(params)
        .done((data, status, xhr) => {
            if(xhr.status === 200){
                let table = $("#assigned_sites").dataTable().api();
				table.rows.add(data['assigned_sites']).draw()
                var assigned_sites = tabAssigned_sites.rows().data().toArray()                
			}
        })
    }

    //clear exisiting plotings 
    function clearMarkerAndPolyline() {
        d2markersArray.forEach(marker => marker.setMap(null));
        d2markersArray.length = 0;
    }

    //clear exisiting plotings 
    function d2ClearMarker() {
        clearMarkerAndPolyline();
        for (var i = 0; i < d2markersArray.length; i++) {
            d2markersArray[i].setMap(null);
        }
        d2markersArray = [];
    }

    /*//Extracts latitudes and longitudes data 
    function getLatLngFromGPSData(gpsLocationData) {
        if (typeof gpsLocationData === 'string' && gpsLocationData.length > 0) {
            const coords = JSON.parse(gpsLocationData)["coordinates"];
            if (coords) {
            return new google.maps.LatLng(coords[1], coords[0]); 
            }
        }
        return null
    }*/
   // Extracts latitudes and longitudes data 
    function getLatLngFromGPSData(gpsLocationData, siteName = '') {
        try {
            // Return null if data is null, undefined, or empty
            if (!gpsLocationData) {
                console.warn(`Missing GPS data for site: ${siteName}`);
                return null;
            }

            // Parse JSON if it's a string, otherwise use the data as is
            const data = typeof gpsLocationData === 'string' ? 
                JSON.parse(gpsLocationData) : gpsLocationData;

            // Check if coordinates exist and are valid
            if (data && Array.isArray(data.coordinates) && 
                data.coordinates.length >= 2 &&
                !isNaN(data.coordinates[0]) && 
                !isNaN(data.coordinates[1])) {
                
                return new google.maps.LatLng(
                    parseFloat(data.coordinates[1]), // latitude
                    parseFloat(data.coordinates[0])  // longitude
                );
            }
            console.warn(`Invalid GPS coordinates for site: ${siteName}`);
            return null;
        } catch (error) {
            console.warn(`Error parsing GPS data for site ${siteName}:`, error);
            return null;
        }
    }


    /*//plots LatLng data into map
    function plotLocationsOnMap(tabAssigned_sites) {
        const assignedSites = tabAssigned_sites.rows().data().toArray()
        console.log('assigned site in sitegroup',assignedSites)
        const mapBounds = new google.maps.LatLngBounds();
        const infoWindow = new google.maps.InfoWindow();
        d2ClearMarker();
        assignedSites.forEach(site => {
            const latLng = getLatLngFromGPSData(site.gps);
            if (latLng) {
            const marker = new google.maps.Marker({
                position: latLng,
                map: d2map, 
                title: site.buname 
            });
            d2markersArray.push(marker); 
            
            mapBounds.extend(latLng);

            google.maps.event.addListener(marker, 'click', function() {
                const siteName = this.title; 
                infoWindow.setContent("Site Name: " + siteName);
                infoWindow.open(d2map, this);
            });
            }
        });
        if (!mapBounds.isEmpty()) {
            d2map.fitBounds(mapBounds);
        }
    }*/

    // Plots LatLng data into map
    // function plotLocationsOnMap(tabAssigned_sites) {
    //     try {
    //         const assignedSites = tabAssigned_sites.rows().data().toArray();
    //         const mapBounds = new google.maps.LatLngBounds();
    //         const infoWindow = new google.maps.InfoWindow();
            
    //         // Clear existing markers
    //         d2ClearMarker();
    
    //         // Track valid and invalid markers
    //         let validMarkersCount = 0;
    //         let sitesWithoutGPS = [];
    
    //         assignedSites.forEach(site => {
    //             if (!site) return;
    //             console.log("Site: ",site)
    //             const latLng = getLatLngFromGPSData(site.gps, site.buname);
    //             if (latLng) {
    //                 validMarkersCount++;
    //                 const marker = new google.maps.Marker({
    //                     position: latLng,
    //                     map: d2map,
    //                     title: site.solid || 'Unnamed Site'
    //                 });
                    
    //                 d2markersArray.push(marker);
    //                 mapBounds.extend(latLng);
    
    //                 google.maps.event.addListener(marker, 'click', function() {
    //                     infoWindow.setContent("Site Name: " + this.title);
    //                     infoWindow.open(d2map, this);
    //                 });
    //             } else {
    //                 // Collect sites with missing or invalid GPS data
    //                 sitesWithoutGPS.push(site.buname || 'Unnamed Site');
    //             }
    //         });
    
    //         // Show warning for sites without GPS data
    //         if (sitesWithoutGPS.length > 0) {
    //             const sitesList = sitesWithoutGPS.join('\n• ');
    //             Swal.fire({
    //                 title: 'Missing GPS Data',
    //                 html: `The following sites have missing or invalid GPS coordinates:<br/><br/>• ${sitesList}`,
    //                 icon: 'warning',
    //                 confirmButtonText: 'OK'
    //             });
    //         }
    
    //         // Only adjust bounds if we have valid markers
    //         if (validMarkersCount > 0) {
    //             d2map.fitBounds(mapBounds);
    //         } else {
    //             Swal.fire({
    //                 title: 'No Valid Locations',
    //                 text: 'None of the selected sites have valid GPS coordinates.',
    //                 icon: 'error',
    //                 confirmButtonText: 'OK'
    //             });
    //         }
    //     } catch (error) {
    //         console.error('Error plotting locations:', error);
    //         Swal.fire({
    //             title: 'Error',
    //             text: 'An error occurred while plotting locations on the map.',
    //             icon: 'error',
    //             confirmButtonText: 'OK'
    //         });
    //     }
    // }




    function plotLocationsOnMap(tabAssigned_sites) {
        try {
            const assignedSites = tabAssigned_sites.rows().data().toArray();
            const mapBounds = new google.maps.LatLngBounds();
            
            // Clear existing markers
            d2ClearMarker();
    
            let validMarkersCount = 0;
            let sitesWithoutGPS = [];
    
            // First, extend bounds for all valid locations
            assignedSites.forEach(site => {
                if (!site) return;
                const latLng = getLatLngFromGPSData(site.gps, site.buname);
                if (latLng) {
                    // Add extra padding around each point
                    const padding = 0.01; // Approximately 1km at equator
                    mapBounds.extend(new google.maps.LatLng(
                        latLng.lat() + padding,
                        latLng.lng() + padding
                    ));
                    mapBounds.extend(new google.maps.LatLng(
                        latLng.lat() - padding,
                        latLng.lng() - padding
                    ));
                }
            });
    
            // Then create markers
            assignedSites.forEach(site => {
                if (!site) return;
                console.log("Site:", site);
                const latLng = getLatLngFromGPSData(site.gps, site.buname);
                if (latLng) {
                    validMarkersCount++;
                    
                    // Create marker with offset labels for overlapping markers
                    const marker = new google.maps.Marker({
                        position: latLng,
                        map: d2map,
                        label: {
                            text: site.solid || 'Unnamed',
                            color: '#000000',
                            fontSize: '12px',
                            fontWeight: 'bold',
                            // Offset the label position slightly based on position
                            // This will help prevent complete overlap of labels
                            anchor: new google.maps.Point(
                                (validMarkersCount % 2) * 20 - 10, 
                                (Math.floor(validMarkersCount / 2) % 2) * 20 - 10
                            )
                        }
                    });
                    
                    d2markersArray.push(marker);
                } else {
                    sitesWithoutGPS.push(site.buname || 'Unnamed Site');
                }
            });
    
            // Show warning for sites without GPS data
            if (sitesWithoutGPS.length > 0) {
                const sitesList = sitesWithoutGPS.join('\n• ');
                Swal.fire({
                    title: 'Missing GPS Data',
                    html: `The following sites have missing or invalid GPS coordinates:<br/><br/>• ${sitesList}`,
                    icon: 'warning',
                    confirmButtonText: 'OK'
                });
            }
    
            // Only adjust bounds if we have valid markers
            if (validMarkersCount > 0) {
                // Fit the map to the extended bounds
                d2map.fitBounds(mapBounds);
                
                // Add a small delay before adjusting the zoom
                setTimeout(() => {
                    // Get the current zoom and decrease it slightly to show all markers
                    const currentZoom = d2map.getZoom();
                    d2map.setZoom(currentZoom - 1);
                    
                    // Center the map on the bounds
                    d2map.setCenter(mapBounds.getCenter());
                }, 100);
            } else {
                Swal.fire({
                    title: 'No Valid Locations',
                    text: 'None of the selected sites have valid GPS coordinates.',
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            }
        } catch (error) {
            console.error('Error plotting locations:', error);
            Swal.fire({
                title: 'Error',
                text: 'An error occurred while plotting locations on the map.',
                icon: 'error',
                confirmButtonText: 'OK'
            });
        }
    }