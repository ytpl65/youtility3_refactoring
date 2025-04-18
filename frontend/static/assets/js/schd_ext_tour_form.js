// add classes to label tags.
$("label").removeClass("col-form-label col-md-2 col-sm-2 text-sm-right");
var d2geocoder;
var d2map;
var d2oms;
var d2markersArray = [];
var _shiftMinute = 0;
var d2siteMarkersArray = [];
var d2markerCluster = undefined;
var d2PolyLine = undefined;

function reversedFpoints(DDE, data, breaktime) {
  DDE = DDE.reverse();
  var j = 0;
  var R = [];
  for (let i = 0; i < data.slice().reverse().length; i++) {
    if (i === data.length - 1) {
      data[i]["distance"] =
        data[i]["duration"] =
        data[i]["expirytime"] =
        data[i]["breaktime"] =
          0;
    } else {
      data[i]["distance"] = DDE[j][0];
      data[i]["duration"] = DDE[j][1];
      data[i]["expirytime"] = DDE[j][2];
      j++;
    }
    R.push(data[i]);
  }
  R[R.length - 1]["breaktime"] = breaktime;
  return R;
}

function checkFrequenciedData(data, F, DDE, breaktime) {
  var t = [...data];
  for (let i = 0; i < F - 1; i++) {
    let r = reversedFpoints(DDE, data, breaktime).reverse();
    data.push(...r);
  }
  return data;
}

function spreadColNames() {
  return [
    { name: "bu", targets: 1 },
    { name: "buname", targets: 2 },
    { name: "bu__gpslocation", targets: 3 },
    { name: "distance", targets: 6 },
    { name: "duration", targets: 7 },
    { name: "breaktime", targets: 8 },
    { name: "expirytime", targets: 9 },
    { name: "qset_name", targets: 10 },
    { name: "qset", targets: 11 },
    { name: "starttime", targets: 4 },
    { name: "endtime", targets: 5 },
  ];
}

function update_site_form(data) {
  $("#edit_assigned_site #id_br_time").val(data[7]);
  $("#edit_assigned_site #id_checklist").val(data[11]).change();
  reCaclTime();
}

function updateAssignedSitesTable(btime, checkListId, checkListName) {
  newData = asgdsites_table.row(".selected").data();

  newData["breaktime"] = btime;
  newData["qsetid"] = checkListId;
  newData["qsetname"] = checkListName;

  asgdsites_table.row(".selected").data(newData).draw();
}

function calculateAndDisplayRoute(data, routeFreq, optimize=false) {
  var directionService = new google.maps.DirectionsService();
  if (data.length > 1) {
    directionService.route(
      getDirectionConfig(data, optimize),
      function (response, status) {
        if (status === "OK") {
          data = calculateLatLngPoints(response, data, routeFreq);
          data = calculateDistanceDuration(response, data);
          var rowData = data//routeFreq > 1 ? fpoint : data;
          reloadAssignedSitesTable(rowData);
          reCaclTime();
          isDirectionSaved = true;
        } else {
          show_error_alert(
            `Directions request failed due to ${status}, Please check your coordinates of your checkpoints`,
            "GMaps Error!"
          );
        }
      }
    );
  }
}

function getDirectionConfig(data, optimize) {
  var gpsStartCoords = JSON.parse(data[0]["bu__gpslocation"])["coordinates"];
  var gpsEndCoords = JSON.parse(data[data.length - 1]["bu__gpslocation"])[
    "coordinates"
  ];

  var startPoint = {
    lat: Number(gpsStartCoords[1]),
    lng: Number(gpsStartCoords[0]),
  };
  var endPoint = { lat: Number(gpsEndCoords[1]), lng: Number(gpsEndCoords[0]) };

  var wayPoints = [];
  for (var i = 1; i < data.length - 1; i++) {
    if(!data[i]['bu__gpslocation']){
      Swal.fire(
        'No coordinates found!',
        'Some of your checkpoints has not assigned GPG coords yet.',
        'warning'
      )
      break
    }
    let wpCoords = JSON.parse(data[i]["bu__gpslocation"])["coordinates"];
    wayPoints.push({
      location: new google.maps.LatLng(
        Number(wpCoords[1]),
        Number(wpCoords[0])
      ),
      stopover: true,
    });
  }

  return {
    origin: startPoint,
    destination: endPoint,
    waypoints: wayPoints,
    travelMode: "DRIVING",
    optimizeWaypoints: optimize,
  };
}

function calculateLatLngPoints(response, data, routeFreq) {
  var directionsRenderer = new google.maps.DirectionsRenderer({
    suppressMarkers: true,
  });
  var optimizedPoints = [];
  directionsRenderer.setDirections(response);
  var waypoint_order = response.routes[0].waypoint_order;

  //start point
  data[0]["seqno"] = 0 + 1;
  d2DrawMarker(data[0], 0, routeFreq);
  optimizedPoints.push(data[0]);
  optimizedPoints[0]["distance"] =
    optimizedPoints[0]["duration"] =
    optimizedPoints[0]["expirytime"] =
      0;

  //waypoint
  for (var i = 0; i < waypoint_order.length; i++) {
    data[i + 1]["seqno"] = i + 1 + 1;
    d2DrawMarker(data[waypoint_order[i] + 1], i + 1, routeFreq);
    optimizedPoints.push(data[waypoint_order[i] + 1]);
  }

  //endpoint
  data[data.length - 1]["seqno"] = data.length - 1 + 1;
  d2DrawMarker(data[data.length - 1], data.length - 1, routeFreq, true);
  optimizedPoints.push(data[data.length - 1]);

  return optimizedPoints;
}

function calculateDistanceDuration(response, data) {
  optimizedPoints = data;
  var DDE = [];
  var legs = response.routes[0].legs;
  for (var i = 0; i < legs.length; i++) {
    let l = [];
    optimizedPoints[i + 1]["distance"] = parseFloat(
      legs[i]["distance"]["value"] / 1000
    ).toFixed(2);
    l.push(optimizedPoints[i + 1]["distance"]);
    optimizedPoints[i + 1]["duration"] = secondsToString(
      legs[i]["duration"]["value"]
    );
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


function d2DrawMarker(
  
  row,
  idx,
  routeFreq = 1,
  end = false,
  remain = false,
  no = null,
  left = null
) {
  
  var latlng = JSON.parse(row["bu__gpslocation"])["coordinates"];
  if (end && routeFreq > 1) {
    var max = idx + 1;
    nStr = `${max - idx},${max}`;
  } else if (remain && no) {
    var L = no - left + 1;
    var R = left + no;
    nStr = `${L},${R}`;
  } else {
    nStr = `${idx + 1}`;
  }
  var infoWindowHtml = "";
  const status_color_code = {'ASSIGNED':"00bfff", 'AUTOCLOSED':"FB6D3E", 'COMPLETED':"7AD308"}
  let colorcode = status_color_code[row['jobstatus']] ?  status_color_code[row['jobstatus']] : '00bfff'
  const position = { lat: latlng[1], lng: latlng[0] };
  const pin = new google.maps.marker.PinElement({
    glyph: `${idx + 1}`,
    scale: 1.5,
    background: `#${colorcode}`,
    borderColor: "#FFFFFF",
  });
  var markerC = new google.maps.marker.AdvancedMarkerElement({
    map: d2map,
    title: row["bu__buname"],
    position: position, 
    content: pin.element,
    gmpClickable: true,
  });

  function convert_to_local(data) {
    if (data) {
      let datetime = moment(data, "YYYY-MM-DDTHH:mm:ss")
        .add(row["ctzoffset"], "m")
        .format("DD-MMM-YYYY HH:mm");
      return data ? datetime : "-";
    }
    return data;
  }

  google.maps.event.addListener(markerC, "click", function () {
    var d2infowindow = new google.maps.InfoWindow({ content: "", maxWidth: 350 });
    var infoWindowHtml =

    "<table style='border: 1px solid black;'>" +
    "<tr style='border: 1px solid black;'>" +
    "<td style='font-weight: bold; font-size: 16px;'>Location:</td> " + "<td>" +
    row["bu__buname"] + "</td>" + "</tr>" +
    "<tr style='border: 1px solid black;'>" +
    "<td style='font-weight: bold; font-size: 16px;'>Performed By:</td> " + "<td>" +
    row["people__peoplename"] + "</td>" + "</tr>" +
    "<tr style='border: 1px solid black;'>" +
    "<td style='font-weight: bold; font-size: 16px;'>StartTime:</td> " + "<td>" +
    row["starttime"] + "</td>" + "</tr>" +
    "<tr style='border: 1px solid black;'>" +
    "<td style='font-weight: bold; font-size: 16px;'>EndTime:</td> " + "<td>" +
    row["endtime"] + "</td>" + "</tr>" +
    "</table>";
    
    d2infowindow.setContent(infoWindowHtml);
    d2infowindow.open(d2map, markerC);
  });
  d2oms.addMarker(markerC);
  var d2bounds = new google.maps.LatLngBounds();
  d2bounds.extend(markerC.position);
  //add to array
  d2markersArray.push(markerC);
  //set map zoom
  //d2map.setZoom(12);
  //d2map.fitBounds(d2bounds);
}

function secondsToString(seconds) {
  var numyears = Math.floor(seconds / 31536000);
  var numdays = Math.floor((seconds % 31536000) / 86400);
  var numhours = Math.floor(((seconds % 31536000) % 86400) / 3600);
  var numminutes = Math.floor((((seconds % 31536000) % 86400) % 3600) / 60);
  var numseconds = (((seconds % 31536000) % 86400) % 3600) % 60;

  var readableTimeStr = "";
  if (numyears > 0) readableTimeStr += numyears + " yr ";
  if (numdays > 0) readableTimeStr += numdays + " d ";
  if (numhours > 0) readableTimeStr += numhours + " hr ";
  if (numminutes > 0) readableTimeStr += numminutes + " min";
  if (readableTimeStr.trim() === "") readableTimeStr = "--";
  return readableTimeStr;
}

function hitGmapsService(config) {
  var directionService = new google.maps.DirectionsService();
  var result = {};
  directionService.route(config, function (response, status) {
    result["response"] = response;
    result["status"] = status;
  });
  return result;
}

function d2ClearMarker() {
  clearMarkerAndPolyline();
  for (var i = 0; i < d2markersArray.length; i++) {
    d2markersArray[i].setMap(null);
  }
  d2markersArray = [];
}

function clearMarkerAndPolyline() {
  for (var i = 0; i < d2markersArray.length; i++) {
    d2markersArray[i].setMap(null);
  }
  d2markersArray = [];
}

function ManageFrequenciedRoutes(data, routeFreq) {
  var fCnt = 0;
  var fPoint = [];
  optimizedPoints = data;
  for (var f = 0; f < routeFreq; f++) {
    for (var i = 0; i < optimizedPoints.length - 1; i++) {
      if (f > 0 && i == 0) {
        fPoint[fCnt] = optimizedPoints[optimizedPoints.length - 1];
        fPoint[fCnt]["seqno"] = fCnt + 1;
        fPoint[fCnt]["distance"] =
          optimizedPoints[optimizedPoints.length - 1]["distance"];
        fPoint[fCnt]["duration"] =
          optimizedPoints[optimizedPoints.length - 1]["duration"];
        fPoint[fCnt]["expirytime"] =
          optimizedPoints[optimizedPoints.length - 1]["expirytime"];
      } else {
        fPoint[fCnt] = optimizedPoints[i];
        fPoint[fCnt]["seqno"] = fCnt + 1;
        fPoint[fCnt]["distance"] = optimizedPoints[i]["distance"];
        fPoint[fCnt]["duration"] = optimizedPoints[i]["duration"];
        fPoint[fCnt]["expirytime"] = optimizedPoints[i]["expirytime"];
      }
      fCnt++;
    }
  }
  var calDateTime = _cronDates[0];
  for (var i = 0; i < optimizedPoints.length; i++) {
    calDateTime = moment(calDateTime)
      .add(optimizedPoints[i]["expirytime"], "minutes")
      .format("YYYY-MM-DD HH:mm:ss");
  }
  return fPoint;
}

function reloadAssignedSitesTable(data) {
  asgdsites_table.rows().remove().draw();
  asgdsites_table.rows.add(data).draw();
}

function d2InitializeMap() {
  var directionsRenderer = new google.maps.DirectionsRenderer({
    suppressMarkers: true,
  });
  d2map = new google.maps.Map(document.getElementById("d2Map"), {
    zoom: 3,
    center: new google.maps.LatLng(23.248917, 77.651367), //locations[0],
    mapTypeId: google.maps.MapTypeId.ROADMAP,
    mapId : "DEMO_MAP_ID", // Map ID is required for advanced markers.
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


function reCaclTime() {
  var params = {
    data: asgdsites_table.rows().data().toArray(),
    prevBreakTime: 0,
    smin: 0,
    prevExpTime: 0,
    emin: 0,
    calDateTime: _cronDates[0],
    mapDistance: 0,
    duration_grace:
      parseInt($("#id_planduration").val(), 10) +
      parseInt($("#id_gracetime").val(), 10),
    mapDuration: 0,
    mapBreakTime: 0,
    timeSpendAtSite: 0,
  };
  //re-calculates starttime endtime duration breaktime etc
  asgdsites_table.rows().remove().draw();
  CalculateStimeEtimeDuration(params);
  populateTourDetailsCard(params);
}

function CalculateStimeEtimeDuration(params) {
  var data = params.data;
  for (var i = 0; i < data.length; i++) {
    data[i]["duration"] = secondsToString(
      parseInt(data[i]["expirytime"], 10) * 60
    );

    params.mapDistance += parseFloat(data[i]["distance"]);
    params.mapDuration += parseInt(data[i]["expirytime"], 10);
    params.timeSpendAtSite += params.duration_grace;
    if (
      typeof data[i]["breaktime"] === "undefined" ||
      data[i]["breaktime"] === null ||
      data[i]["breaktime"] === ""
    ) {
      data[i]["breaktime"] = 0;
    }
    params.mapBreakTime += parseInt(data[i]["breaktime"], 10);
    if (i > 0) {
      params.smin =
        params.prevExpTime +
        parseInt(data[i]["expirytime"], 10) +
        params.prevBreakTime;
      params.emin = params.smin + parseInt(params.duration_grace, 10);
      data[i]["starttime"] = moment(params.calDateTime)
        .add(params.smin, "minutes")
        .format("HH:mm");
      data[i]["endtime"] = moment(params.calDateTime)
        .add(params.emin, "minutes")
        .format("HH:mm");
      params.prevExpTime = params.emin;
      if (
        typeof data[i]["breaktime"] !== "undefined" &&
        data[i]["breaktime"] !== null &&
        data[i]["breaktime"] !== ""
      ) {
        params.prevBreakTime = parseInt(data[i]["breaktime"], 10);
      }
    } else {
      params.smin = parseInt(data[i]["expirytime"], 10);
      params.emin = params.smin + parseInt(params.duration_grace, 10);
      data[i]["starttime"] = moment(params.calDateTime)
        .add(params.smin, "minutes")
        .format("HH:mm");
      data[i]["endtime"] = moment(params.calDateTime)
        .add(params.emin, "minutes")
        .format("HH:mm");
      params.prevExpTime = params.emin;
      if (
        typeof data[i]["breaktime"] !== "undefined" &&
        data[i]["breaktime"] !== null &&
        data[i]["breaktime"] !== ""
      ) {
        params.prevBreakTime = parseInt(data[i]["breaktime"], 10);
      }
    }
  }
}

function populateTourDetailsCard(params) {
  var speed = parseFloat(
    params.mapDistance / (params.mapDuration / 60)
  ).toFixed(2);
  var rtime =
    parseInt(_shiftMinute, 10) -
    parseInt(params.mapDuration, 10) -
    parseInt(params.mapBreakTime, 10) -
    params.timeSpendAtSite;

  _fduration = isNaN(params.mapDuration)
    ? "--"
    : secondsToString(params.mapDuration * 60);
  _fdistance = isNaN(params.mapDistance)
    ? "--"
    : parseFloat(params.mapDistance).toFixed(2);
  _fbreaktime = isNaN(params.mapBreakTime)
    ? "--"
    : secondsToString(params.mapBreakTime * 60);

  $("#lblDistance").html(
    isNaN(params.mapDistance) || params.mapDistance === 0
      ? "--"
      : parseFloat(params.mapDistance).toFixed(2) + " Km"
  );
  $("#lblSpeed").html(isNaN(speed) ? "--" : speed + " Km/Hr");
  $("#lblRTime").html(isNaN(rtime) ? "--" : secondsToString(rtime * 60));
  $("#lblTravelTime").html(
    isNaN(params.mapDuration) ? "--" : secondsToString(params.mapDuration * 60)
  );
  $("#lblSiteTime").html(
    isNaN(params.timeSpendAtSite)
      ? "--"
      : secondsToString(params.timeSpendAtSite * 60)
  );
  $("#lblTourFrequency").html($("#id_tourfrequency").val());
  $("#lblBreakTime").html($("#id_breaktime").val());
  $("#lblIsRTour").html(israndom);

  asgdsites_table.rows.add(params.data).draw();
}

function setShiftMin(_shift) {
  if (typeof _shift !== "undefined") {
    var stime = _shift.starttime.split(":");
    var etime = _shift.endtime.split(":");

    stime = parseInt(stime[0] * 60, 10) + parseInt(stime[1], 10);
    etime = parseInt(etime[0] * 60, 10) + parseInt(etime[1], 10);

    _shiftMinute = stime > etime ? 1440 + etime - stime : etime - stime;

    $("#lblSTime").html(secondsToString(_shiftMinute * 60));
  }
}

function setFooter(api) {
  $(api.column(6).footer()).html(`${_fdistance}`);
  $(api.column(7).footer()).html(`${_fduration}`);
  $(api.column(8).footer()).html(`${_fbreaktime}`);
}

function getSitesData(params) {
  params["assignedSites"] = [];
  var sitesData = asgdsites_table.rows().data();
  for (let i = 0; i < sitesData.length; i++) {
    var obj = {};
    obj["seqno"] = i;
    obj["asset"] = sitesData["1"];
    obj["jobname"] = `${$("#id_jobname").val()} - ${i} - ${
      sitesData["buname"]
    }`;
    obj["expirytime"] = sitesData["expirytime"];
    obj["qset"] = sitesData["qsetid"];
    obj["distance"] = sitesData["distance"];
    obj["duration"] = sitesData["duration"];
    obj["breaktime"] = sitesData["breaktime"];
    params["assignedSites"].push(obj);
  }
  params["assignedSites"] = JSON.stringify(params["assignedSites"]);

  return params;
}
