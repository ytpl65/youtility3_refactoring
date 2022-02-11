// add classes to label tags.
$('label').removeClass("col-form-label col-md-2 col-sm-2 text-sm-right")
var d2geocoder;
var d2map;
var d2oms;
var d2markersArray     = [];
var _shiftMinute= 0;
var d2siteMarkersArray = [];
var d2markerCluster    = undefined;
var directionsRenderer = new google.maps.DirectionsRenderer({suppressMarkers: true});
var directionService  = new google.maps.DirectionsService();
var d2bounds = new google.maps.LatLngBounds();
var d2infowindow = new google.maps.InfoWindow({content:"",maxWidth: 350});
var d2PolyLine= undefined;


function spreadColNames(){
    return [
        { "name" : "bu",        "targets" : 1 },
        { "name" : "buname",      "targets" : 2 },
        { "name" : "gpslocation", "targets" : 3 },
        { "name" : "distance",    "targets" : 6 },
        { "name" : "duration",    "targets" : 7 },
        { "name" : "breaktime",   "targets" : 8 },
        { "name" : "expirytime",  "targets" : 9 },
        { "name" : "qset_name",   "targets" : 10},
        { "name" : "qset",      "targets" : 11},
        { "name" : "starttime",   "targets" : 4 },
        { "name" : "endtime",     "targets" : 5 }
    ]
}

function update_site_form(data){
    $("#edit_assigned_site #id_br_time").val(data[7])
    $("#edit_assigned_site #id_checklist").val(data[11]).change()
    reCaclTime()
}


function updateAssignedSitesTable(btime, checkListId, checkListName){
    newData     = asgdsites_table.row('.selected').data()
    console.log(newData, "before")
    newData['8']  = btime
    newData['11'] = checkListId
    newData['10'] = checkListName
    console.log(newData, "newData")
    asgdsites_table.row('.selected').data(newData).draw();
}

function calculateAndDisplayRoute(data, routeFreq){
    if(data.length > 1){
        if(routeFreq > 1){
            //copy first obj
            let copiedFirstObject = JSON.parse(JSON.stringify(data[0]));
            data[data.length] = copiedFirstObject
        }
        directionService.route(getDirectionConfig(data), function(response, status){
            if(status === 'OK'){
                data = calculateLatLngPoints(response, data, routeFreq)
                data = calculateDistanceDuration(response, data)
                fpoint = ManageFrequenciedRoutes(data, routeFreq)
                var rowData = routeFreq > 1? fpoint : data
                reloadAssignedSitesTable(rowData)
                reCaclTime()
            }else{
                //google maps fetching error
                show_error_alert(`Directions request failed due to ${status}`, "GMaps Error!")
            }
        })
    }
}


function getDirectionConfig(data){
    var startPoint = { lat: Number(data[0]['3'].split(",")[0]),  lng: Number(data[0]['3'].split(",")[1]) };
    var endPoint   = { lat: Number(data[data.length - 1]['3'].split(",")[0]),  lng: Number(data[data.length - 1]['3'].split(",")[1]) };
    var wayPoints  = [];
    for(var i = 1; i < data.length - 1; i++){
        console.log(`data[i] ${data[i]['3']}`)
        wayPoints.push({
            location: new google.maps.LatLng(Number(data[i]['3'].split(",")[0]), Number(data[i]['3'].split(",")[1])),
            stopover: true
        });
    }
    console.log(`startpoint ${startPoint} endPoint ${endPoint} waypoints ${wayPoints}`)
    return  {
        origin           : startPoint,
        destination      : endPoint,
        waypoints        : wayPoints,
        travelMode       : "DRIVING",
        optimizeWaypoints: true,
    }
}

function calculateLatLngPoints(response, data, routeFreq){
    var optimizedPoints = []
    directionsRenderer.setDirections(response);
    var waypoint_order= response.routes[0].waypoint_order;
    
    //start point
    data[0]["slno"] = 0 + 1;
    d2DrawMarker(data[0], 0, routeFreq);
    optimizedPoints.push(data[0])
    optimizedPoints[0]["6"] = optimizedPoints[0]['7'] = optimizedPoints[0]["9"] = 0

    //waypoint
    for(var i=0;i<waypoint_order.length;i++){
        data[i + 1]["slno"] = (i + 1) + 1;
        d2DrawMarker(data[waypoint_order[i] + 1], (i + 1), routeFreq);
        optimizedPoints.push(data[waypoint_order[i] + 1]);
    }
    //endpoint
    data[data.length - 1]["slno"] = data.length - 1 + 1;
    d2DrawMarker(data[data.length - 1], data.length - 1, routeFreq, true);
    optimizedPoints.push(data[data.length - 1]);

    // if(routeFreq > 1){
    //     var slicedData = data.slice(1,data.length-1)  
    //     var totalSites = data.length - 1
    //     var SL = slicedData.length
    //     for(let i=0; i<slicedData.length; i++){
    //         d2DrawMarker(slicedData[i], i, routeFreq, remain=true, no = totalSites, left=SL)
    //         SL++
    //     }
    // }
    return optimizedPoints
}

function calculateDistanceDuration(response, data){
    optimizedPoints = data
    var legs= response.routes[0].legs;
    for(var i= 0; i < legs.length; i++){
        optimizedPoints[i+1]["6"] = parseFloat(legs[i]["distance"]["value"] / 1000).toFixed(2);
        optimizedPoints[i+1]["7"] = secondsToString(legs[i]["duration"]["value"]);
        optimizedPoints[i+1]["9"] = parseInt(legs[i]["duration"]["value"] / 60);
    }
    return optimizedPoints
}

function d2DrawMarker(row, idx, routeFreq=1, end=false, remain=false, no=null, left=null) {
    if(end && routeFreq > 1){
        var max = idx+1
        nStr = `${max - idx},${max}`
    }else if (remain && no){
        var L = no-left+1
        var R = left + no
        nStr = `${L},${R}`
    }
    else{
        nStr = `${idx+1}`
    }
    var infoWindowHtml= ""
    var markerC= new google.maps.Marker({
        map:      d2map,
        title:    row["2"],
        position: new google.maps.LatLng(row["3"].trim().split(",")[0], row["3"].trim().split(",")[1]),
        //icon:     "https://chart.googleapis.com/chart?chst=d_map_spin&chld=0.8|0|00bfff|10|b|" + (idx + 1),
        icon:     "https://chart.googleapis.com/chart?chst=d_map_spin&chld=0.8|0|00bfff|10|b|"  + nStr,
    });
    google.maps.event.addListener(markerC, 'click', function () {
        //var infoWindowHtml= '<h3 style="background-color: #FFF8C9;font-weight:bold;">' + row["2"] + '</h3>';
        var infoWindowHtml= "<span style= 'font-weight: bold;font-size:16px'>" + row["2"] + "</span>";
        d2infowindow.setContent(infoWindowHtml);
        d2infowindow.open(d2map, markerC);
    });
    d2oms.addMarker(markerC);
    d2bounds.extend(markerC.getPosition());
    //add to array
    d2markersArray.push(markerC);
    //set map zoom
    //d2map.setZoom(20);
    d2map.fitBounds(d2bounds);
}

function secondsToString(seconds){
    var numyears = Math.floor(seconds / 31536000);
    var numdays = Math.floor((seconds % 31536000) / 86400);
    var numhours = Math.floor(((seconds % 31536000) % 86400) / 3600);
    var numminutes = Math.floor((((seconds % 31536000) % 86400) % 3600) / 60);
    var numseconds = (((seconds % 31536000) % 86400) % 3600) % 60;

    var readableTimeStr = "";
    if(numyears   > 0) readableTimeStr += numyears   + " yr ";
    if(numdays    > 0) readableTimeStr += numdays    + " d ";
    if(numhours   > 0) readableTimeStr += numhours   + " hr ";
    if(numminutes > 0) readableTimeStr += numminutes + " min";
    if(readableTimeStr.trim() == "") readableTimeStr= "--";
    return readableTimeStr;
}

function hitGmapsService(config){
    var result = {}
    directionService.route(config, function(response, status){
        result['response'] = response
        result['status'] = status
        console.log(response, status)
    })
    return result
}

function d2ClearMarker(){
    clearMarkerAndPolyline();
   for (var i=0; i<d2markersArray.length; i++) {
       d2markersArray[i].setMap(null);
   }
   d2markersArray= [];
}

function clearMarkerAndPolyline(){
    for (var i=0; i<d2markersArray.length; i++) {
        d2markersArray[i].setMap(null);
    }
    d2markersArray= [];
}

function ManageFrequenciedRoutes(data, routeFreq){
    var fCnt   = 0;
    var fPoint = [];
    optimizedPoints = data
    for(var f= 0; f < routeFreq; f++) {
        for(var i= 0; i < optimizedPoints.length - 1; i++){
            console.log("f: ", f, " :: i: ", i, " :: fCnt: ", fCnt);
            if( f > 0 &&  i == 0) {
                fPoint[fCnt] = optimizedPoints[optimizedPoints.length - 1];
                fPoint[fCnt]["slno"] = fCnt + 1;
                fPoint[fCnt]["6"] = optimizedPoints[optimizedPoints.length - 1]["6"];
                fPoint[fCnt]["7"] = optimizedPoints[optimizedPoints.length - 1]["7"];
                fPoint[fCnt]["9"] = optimizedPoints[optimizedPoints.length - 1]["9"];
            } else {
                fPoint[fCnt] = optimizedPoints[i];
                fPoint[fCnt]["slno"] = fCnt + 1;
                fPoint[fCnt]["6"] = optimizedPoints[i]["6"];
                fPoint[fCnt]["7"] = optimizedPoints[i]["7"];
                fPoint[fCnt]["9"] = optimizedPoints[i]["9"];
            }
            fCnt++;
        }
    }
    var calDateTime= _cronDates[0];
    for(var i= 0; i < optimizedPoints.length; i++) {
        calDateTime= moment(calDateTime).add(optimizedPoints[i]["9"], 'minutes').format("YYYY-MM-DD HH:mm:ss");
    }
    return fPoint
}

function reloadAssignedSitesTable(data){
    asgdsites_table.rows().remove().draw()
    asgdsites_table.rows.add(data).draw()
}

function d2InitializeMap() {
    d2map = new google.maps.Map(document.getElementById("d2Map"), {
        zoom: 2,
        center: new google.maps.LatLng(23.248917,77.651367),  //locations[0],
        mapTypeId: google.maps.MapTypeId.ROADMAP
    });
    d2oms = new OverlappingMarkerSpiderfier(d2map, {
        markersWontMove: true,
        markersWontHide: true,
        keepSpiderfied: true,
        nearbyDistance: 10,
        legWeight: 5
    });
    d2geocoder = new google.maps.Geocoder();
    directionsRenderer.setMap(d2map);
}


function reCaclTime(){
    var params = {
        'data'          : asgdsites_table.rows().data().toArray(),
        'prevBreakTime' : 0, 'smin':0,
        'prevExpTime'   : 0, 'emin':0,
        'calDateTime'   : _cronDates[0], 'mapDistance':0,
        'duration_grace': parseInt($("#id_planduration").val()) + parseInt($("#id_gracetime").val()),
        'mapDuration':0,
        'mapBreakTime'  : 0, 'timeSpendAtSite':0
    }
    //re-calculates starttime endtime duration breaktime etc
    asgdsites_table.rows().remove().draw()
    CalculateStimeEtimeDuration(params);
    populateTourDetailsCard(params)
}

function CalculateStimeEtimeDuration(params){
    var data = params.data
    for(var i= 0; i < data.length; i++) {
        console.log(i, ": reCaclTime data: ", data[i]);
        data[i]['7'] = secondsToString(parseInt(data[i]["9"]) * 60);
        params.mapDistance += parseFloat(data[i]["6"]);
        params.mapDuration += parseInt(data[i]["9"]);
        params.timeSpendAtSite += params.duration_grace;
        if(data[i]["8"] == undefined || data[i]["8"] == null || data[i]["8"] == "") {
            data[i]["8"] = 0;
        }
        params.mapBreakTime += parseInt(data[i]["8"]);
        if(i > 0) {
            params.smin  = params.prevExpTime + parseInt(data[i]["9"]) + params.prevBreakTime;
            params.emin  = params.smin + parseInt(params.duration_grace);
            data[i]["4"] = moment(params.calDateTime).add(params.smin, 'minutes').format("HH:mm");
            data[i]["5"] = moment(params.calDateTime).add(params.emin, 'minutes').format("HH:mm");
            params.prevExpTime= params.emin;
            if(data[i]["8"] != undefined && data[i]["8"] != null && data[i]["8"] != ""){
                params.prevBreakTime= parseInt(data[i]["8"]);
            }
        }else {
            params.smin  = parseInt(data[i]["9"])
            params.emin  = params.smin + parseInt(params.duration_grace);
            data[i]["4"] = moment(params.calDateTime).add(params.smin, 'minutes').format("HH:mm");
            data[i]["5"] = moment(params.calDateTime).add(params.emin, 'minutes').format("HH:mm");
            params.prevExpTime= params.emin;
            if(data[i]["8"] != undefined && data[i]["8"] != null && data[i]["8"] != ""){
                params.prevBreakTime= parseInt(data[i]["8"]);
            }
        }
    }
}

function populateTourDetailsCard(params){
    var speed= parseFloat((params.mapDistance) / (params.mapDuration / 60)).toFixed(2);
    var rtime= (parseInt(_shiftMinute) - parseInt(params.mapDuration) - parseInt(params.mapBreakTime) - (params.timeSpendAtSite));
    console.log("reCaclTime() rtime: ", rtime);

    _fduration= isNaN(params.mapDuration) ? "--" : secondsToString(params.mapDuration * 60);
    _fdistance= isNaN(params.mapDistance) ? "--" : parseFloat(params.mapDistance).toFixed(2);
    _fbreaktime= isNaN(params.mapBreakTime) ? "--" : secondsToString(params.mapBreakTime * 60);

            
    $("#lblDistance").html(isNaN(params.mapDistance)|| params.mapDistance == 0 ? "--" : parseFloat(params.mapDistance).toFixed(2) + " Km");
    $("#lblSpeed").html( isNaN(speed) ? "--" : speed + " Km/Hr");
    $("#lblRTime").html(isNaN(rtime) ? "--": secondsToString(rtime * 60));
    $("#lblTravelTime").html(isNaN(params.mapDuration) ? "--": secondsToString(params.mapDuration * 60));
    $("#lblSiteTime").html(isNaN(params.timeSpendAtSite) ? "--": secondsToString(params.timeSpendAtSite * 60));
    $("#lblTourFrequency").html($("#tour_frequency").val());
    $("#tour_frequency").val(1);
    console.log(params.data)
    asgdsites_table.rows.add(params.data).draw()
}


function setShiftMin(_shift) {
    if(_shift != undefined){
        var stime= _shift.starttime.split(":");
        var etime= _shift.endtime.split(":");
        console.log("before stime: ", stime);
        console.log("before etime: ", etime);
        stime= parseInt(stime[0] * 60) + parseInt(stime[1]);
        etime= parseInt(etime[0] * 60) + parseInt(etime[1]);
        console.log("after stime: ", stime);
        console.log("after etime: ", etime);
        _shiftMinute= (stime > etime) ? (1440 + etime - stime) : (etime - stime);
        console.log("_shiftMinute: ", _shiftMinute);

        //$("#lblSTime").html(_shiftMinute + " Min");
        $("#lblSTime").html(secondsToString(_shiftMinute * 60));
    }
}

function setFooter(api){
    $(api.column(6).footer() ).html(
        `${_fdistance}`
    );
    $(api.column(7).footer() ).html(
        `${_fduration}`
    );
    $(api.column(8).footer() ).html(
        `${_fbreaktime}`
    );
}

function getSitesData(params){
    params['assignedSites'] = []
    var sitesData = asgdsites_table.rows().data()
    for(let i = 0; i<sitesData.length; i++){
        var obj = {}
        obj['slno'] = i
        obj['asset'] = sitesData['1']
        obj['jobname'] = `${$("#id_jobname").val()} - ${i} - ${sitesData['2']}`
        obj['expirytime'] = sitesData['9']
        obj['qset'] = sitesData['11']
        obj['distance'] = sitesData['6']
        obj['duration'] = sitesData['7']
        obj['breaktime'] = sitesData['8']
        params['assignedSites'].push(obj)
    }
    params['assignedSites'] = JSON.stringify(params['assignedSites'])
    console.log("getSitesData()", params)
    return params
    
}
