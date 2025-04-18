//ajax start and ajaxStop events
$(document).on({
  ajaxStart: function () {
    startBlockUi();
  },
  ajaxStop: function () {
    endBlockUi();
  },
});

// $(window).load(function () {
//   endBlockUi();
// })

//check if a normal select field is enhanced by select2
function isSelect2(element) {
  var instance = jQuery(element).data("select2");
  return instance !== undefined;
}

function getAddressOfPoint(geocoder, point, callback) {
  geocoder.geocode({ location: point }).then((res) => {
    if (res.results[0]) {
      const addressComponents = res.results[0].address_components;
      let city = "";
      let state = "";
      let country = "";
      let formattedAddress = "";

      for (let i = 0; i < addressComponents.length; i++) {
        const types = addressComponents[i].types;

        if (types.includes("locality")) {
          city = addressComponents[i].long_name;
        } else if (types.includes("administrative_area_level_1")) {
          state = addressComponents[i].long_name;
        } else if (types.includes("country")) {
          country = addressComponents[i].long_name;
        }
      }

      formattedAddress = res.results[0].formatted_address;

      const address = {
        city: city,
        state: state,
        country: country,
        formattedAddress: formattedAddress,
        latlng: `${point.lat}, ${point.lng}`,
      };
      callback(address);
    }
  });
}

function parseGeoJson(data){
  let coords = typeof data === 'string' && data.length > 0 ? JSON.parse(data): 'NONE'
  return coords !== 'NONE' ? `${coords['coordinates'][1]}, ${coords['coordinates'][0]}` : 'NONE'
}

function pluginsForFormValidations(){
  return {
    trigger: new FormValidation.plugins.Trigger(),
    bootstrap: new FormValidation.plugins.Bootstrap5({
        rowSelector: '.fv-row',
        eleInvalidClass: 'is-invalid',
        eleValidClass: '',
        eleValidatedClass:'was-validated'
    })
  }
}

function simplifyData(e, data, action) {
  if (action !== "remove") {
    var rowData = data.data;
    var simplifiedData = {};

    for (var key in rowData) {
      var row = rowData[key];
      for (var field in row) {
        simplifiedData[field] = row[field];
      }
    }

    data.data = simplifiedData;
  }
}

function dataTablesExcelConfig(title, columns, filename, moreConfig = {}) {
  return {
    extend: "excelHtml5",
    text: '<i class="bi bi-file-earmark-excel-fill text-success fs-5"></i>',
    titleAttr: "EXCEL",
    title: title,
    filename: filename,
    exportOptions: {
      modifier: {
        page: "all",
      },
      columns: columns,
    },
    ...moreConfig,
  };
}

function dataTablesPDFConfig(
  title,
  columns,
  filename,
  pageSize = "A4",
  mode = "landscape",
  moreConfig = {},

) {
  return {
    extend: 'pdfHtml5',
                        title:title,
						text: '<i class="bi text-danger fs-5 bi-file-earmark-pdf-fill"></i>',
    					titleAttr: "PDF",
                        exportOptions: {
                            columns: columns
                        },
                        filename: filename,
						orientation: mode,
            pageSize: pageSize,
						customize: function (doc) {
							doc.defaultStyle.fontSize = 7;
							doc.styles.tableHeader.fontSize = 8;
              // Set table widths
              doc.content[1].table.widths = Array(doc.content[1].table.body[0].length).fill('*');

              doc.content[1].table.headerRows = 1; // Ensure only the first row is considered as headers
              doc.content[1].table.body.forEach(function(row) {
                row.forEach(function(cell) {
                  cell.alignment = 'center';
        });
      });
            },
    ...moreConfig,
  };
}

function dataTablesColumnVisibilityConfig() {
  return {
    extend: "colvis",
    columns: ":not(.noVis)",
    collectionLayout: "fixed columns",
    collectionTitle: "Column visibility control",
    text: '<i class="bi bi-gear-fill fs-4 text-dark"></i>',
    titleAttr: "Select columns to be included",
    postfixButtons: ["colvisRestore"],
  };
}

function makeRangeReadonly(selector) {
  var rangeInput = document.querySelector(selector);
  if (rangeInput && rangeInput.type === 'range') {
    rangeInput.addEventListener('mousedown', preventDefaultEvent);
    rangeInput.addEventListener('keydown', preventDefaultEvent);
  }
}

function preventDefaultEvent(event) {
  event.preventDefault();
} 

function makeReadonlyFields() {
  // Disable checkboxes
  $("input[type='checkbox']").prop("disable=d", true);
  // Disable text fields
  $("input, textarea").prop("readonly", "readonly");
  $("select").prop("disabled", true);
  // Disable select2 fields (assuming select2 has been initialized)
  $("select.django-select2").select2({ disabled: "readonly" });
}

function makeWorkPermitDetailsReadonly() {
  // Target the container
  const container = document.querySelector('.workpermit-details-section');
  
  if (container) {
      // Make all input fields readonly
      container.querySelectorAll('input').forEach(input => {
          input.setAttribute('readonly', true);
          
          // Special handling for flatpickr date inputs
          if (input.classList.contains('datetimes') && input._flatpickr) {
              input._flatpickr.set('clickOpens', false);  // Prevent calendar from opening
          }
      });

      // Make all textarea fields readonly
      container.querySelectorAll('textarea').forEach(textarea => {
          textarea.setAttribute('readonly', true);
      });

      // Make all select fields disabled
      container.querySelectorAll('select').forEach(select => {
          select.setAttribute('disabled', true);
          // Optionally add a class to maintain the normal appearance
          select.classList.add('form-select-readonly');
      });
  }
}

function makeReadonlyFieldsUnderClass(className) {

  console.log("Class Name: ",className)
  // Disable checkboxes
  $("." + className + " input[type='checkbox']").prop("disabled", true);
  // Disable text fields
  $("." + className + " input, ." + className + " textarea").prop("readonly", true);
  $("." + className + " select").prop("disabled", true);
  // Disable select2 fields (assuming select2 has been initialized)
  $("." + className + " select.django-select2").select2({ disabled: true });
}

function toggleRequiredAttribute(fieldId, set = true) {
  const field = document.getElementById(fieldId);
  const label = document.querySelector(`label[for="${fieldId}"]`);

  if (field && label) {
    if (set) {
      label.classList.add("required");
      field.setAttribute("required", "");
    } else {
      label.classList.remove("required");
      field.removeAttribute("required");
    }
  } else {
    console.warn(`Field or label with ID ${fieldId} not found.`);
  }
}

//upload file using dropzone
function getDropzoneObject() {
  return new Dropzone("#dropzone_file", {
    url: fileUploadUrl,
    paramName: "file",
    maxFiles: 5,
    maxFileSize: 10,
    addRemoveLinks: true,
    accept: function (file, done) {
      console.log(file, done);
    },
    action:"bla.html"
  });
}

function getArrayFromString(input_str) {
  return [undefined, "", null].includes(input_str)
    ? []
    : input_str.split(",").map((word) => word.trim());
}

function getAssetsOfLocation(locationid, url) {
  fire_ajax_get({
    url: `${url}?action=loadAssets&locationid=${locationid}`,
  }).done((data, status, xhr) => {
    // Remove existing options
    var asset_select = $("#id_asset");
    asset_select.empty();

    // Add the first option
    var firstOption = new Option("--------------------", "");
    asset_select.append(firstOption);

    // Add new options to the select element
    data.options.forEach(function (option) {
      var newOption = new Option(option.text, option.id);
      asset_select.append(newOption);
    });

    asset_select.trigger("change");
  });
}

function populateQsetForm(questionid, url) {
  const params = {
    url: `${url}?action=getquestion&questionid=${questionid}`,
    modal: false,
  };
  fire_ajax_get(params).done((data, status, xhr) => {
    if (status == "success") {
      const qsetbng = data.qsetbng[0];
      $("#DTE_Field_min").val(qsetbng.min);
      $("#DTE_Field_max").val(qsetbng.max);
      $("#DTE_Field_options").val(qsetbng.options);
      $("#DTE_Field_avpttype").val(qsetbng.avpttype);
      $("#DTE_Field_isavpt").val(`${qsetbng.isavpt}`);
      if ($("#DTE_Field_isavpt").val() == "true") {
        $(".DTE_Field_Name_avpttype").show();
      }

      if (qsetbng.options && qsetbng.alerton) {
        let optionArr = getArrayFromString(qsetbng.options);
        let alertonArr = getArrayFromString(qsetbng.alerton);
        let selected = performIntersection(optionArr, alertonArr);
        load_alerton_field(optionArr, selected, "#DTE_Field_alerton");
      }
      if (qsetbng.alerton) {
        adjust_above_below(
          qsetbng.alerton,
          (for_table = false),
          (foreditor = true)
        );
      }
    }
  });
}

function getDirectionConfig(data) {
  //start point
  var start = data["path"][0];
  //end point
  var end = data["path"][data["path"].length - 1];
  //waypoints
  var inBetweenPoints = data["waypoints"];
  console.log(inBetweenPoints.length);
  var waypoints = [];
  for (let i = 0; i < inBetweenPoints.length; i++) {
    waypoints.push({
      location: inBetweenPoints[i],
      stopover: false,
    });
  }

  return {
    travelMode: "DRIVING",
    origin: start,
    destination: end,
    //waypoints: waypoints,
    transitOptions: {
      arrivalTime: new Date(data["punchintime"]),
      departureTime: new Date(data["punchouttime"]),
      //modes:['OTHER']//data['transportmodes'],
    },
  };
}

function getRoute(directionService, directionConfig, callback) {
  directionService
    .route(directionConfig)
    .then((response) => {
      callback(response);
    })
    .catch((e) => console.error(e));
}

function clearAllMarkers(markers) {
  // Clear out the old markers.
  markers.forEach((marker) => {
    marker.setMap(null);
  });
}

//creating environment for wizhaard
function make_env_for_wizard(session) {
  $(document).ready(function () {
    if (
      session.hasOwnProperty("wizard_data") &&
      session["wizard_data"] !== null
    ) {
      //minimize sidebar
      //$('#kt_body').attr('data-kt-aside-minimize', 'on')
      //hide the pagebreadcumb
      $("#kt_toolbar").hide();
      //disable pointer events
      $("#kt_aside_toggle, .aside-menu, #user-info").css(
        "pointer-events",
        "none"
      );
    }
  });
}

function validateCode(bucode) {
  // validate bucode return false bucode has special characters and contains space
  var regex = /^[a-zA-Z0-9]+$/;
  if (!regex.test(bucode)) {
    return false;
  }
  return true;
}

function validateEmail(email) {
  //validate email return false if email is invalid
  var regex = /^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$/;
  if (!regex.test(email)) {
    return false;
  }
  return true;
}

function validatePhone(phone) {
  var regex = /^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$/im;
  if (!regex.test(phone)) {
    return false;
  }
  return true;
}

function alertuser_to_saveform(styles = "") {
  Swal.fire({
    title: "Form Modified",
    html: `<p style="font-size:${styles.fs};color:${styles.cl}">Form is modified please save/update it first!</p>`,
    icon: "warning",
    color: "red",
  });
}

const first_show_parent = (id) => {
  $(id).show();
};

//removes required attr from field specified.
function removeRequiredAttr(cls) {
  if (cls === "numeric") {
    $("#id_min, #id_max").removeAttr("required");
    $("#id_options").attr("required", true);
    $("label[for='id_options']").addClass("required");
    console.log("removed...");
  } else if (cls === "optionGrp") {
    $("#id_options").removeAttr("required");
    $("label[for='id_options']").removeClass("required");
    $("#id_min, #id_max").attr("required", true);
    $("label[for='id_min'], label[for='id_max']").addClass("required");
    console.log("added again...");
  } else {
    $("#id_options, #id_alerton, #id_min, #id_max").removeAttr("required");
  }
}

function showHideFields(selected) {
  if (typeof selected !== "undefined") {
    var selectedText = selected.toUpperCase();

    if (selectedText.toUpperCase() === "NUMERIC") {
      $(".numeric").show();
      $(".optionGrp").hide();
      removeRequiredAttr("optionGrp");
    } else if (
      selectedText === "DROPDOWN" ||
      selectedText === "RADIOGROUP" ||
      selectedText === "CHECKBOX"
    ) {
      $(".optionGrp").show();
      $(".numeric").hide();
      removeRequiredAttr("numeric");
    } else if (selectedText.toUpperCase() === "RATING") {
      $(".numeric").hide();
      $(".rating.numeric").show();
      $(".optionGrp").hide();
      removeRequiredAttr("optionGrp");
    } else {
      $(".numeric").hide();
      $(".optionGrp").hide();
      removeRequiredAttr("");
    }
  }
}

function populateAlertOn(txt) {
  var data = {
    id: txt,
    text: txt,
  };
  var newOption = new Option(data.text, data.id, false, false);
  $("#id_alerton").append(newOption).trigger("change");
}

function removeElmtFromAlertOn(txt) {
  if (txt !== "") {
    $(`#id_alerton option[value=${txt}]`).remove();
  }
}

function init_alerton() {
  $("#id_alerton").select2({
    placeholder: "Select an option",
    closeOnSelect: false,
    allowClear: true,
    multiple: true,
  });
}

function handle_rendering_of_menus(session) {
  const exceptions = {
    tracking: "#TRACKING",
    admin: "#ADMIN",
    reports:'#REPORTS',
    onboarding: "#ONBOARDING",
    companysetup: "#COMPANYSETUP",
    sitesurvey: "#SITESURVEY",
    helpdesk: "#HELPDESK",
    scheduling: "#SCHEDULING",
    comparisions: "#COMPARISIONS",
    wom: "#WOM",
    calendar: "#CALENDAR",
  };
  if (session["is_superadmin"]) {
    //show every item if user is superadmin
    $(".menu-item").show();
  } else {
    /*======show menu-item based on user or client capabilites======*/

    //if user is admin show client webcaps else people webcaps
    caps = session["people_webcaps"].length
      ? session["people_webcaps"]
      : session["client_webcaps"];

    //for every cap
    for (var i = 0; i < caps.length; i++) {
      code = caps[i][0];

      if (code.includes("TR_") && $(exceptions["tracking"]).is(":hidden")) {
        $(exceptions["tracking"]).show();
        $(`${exceptions["tracking"]} .menu-item`).hide();
      }
      if (code.includes("SS_") && $(exceptions["sitesurvey"]).is(":hidden")) {
        $(exceptions["sitesurvey"]).show();
        $(`${exceptions["sitesurvey"]} .menu-item`).hide();
      }

      if (code.includes("AD_") && $(exceptions["admin"]).is(":hidden")) {
        $(exceptions["admin"]).show();
        $(`${exceptions["admin"]} .menu-item`).hide();
      }
      if (code.includes("RP_") && $(exceptions["reports"]).is(":hidden")) {
        $(exceptions["reports"]).show();
        $(`${exceptions["reports"]} .menu-item`).hide();
      }
      if (code.includes("CMP_") && $(exceptions["comparisions"]).is(":hidden")) {
        $(exceptions["comparisions"]).show();
        $(`${exceptions["comparisions"]} .menu-item`).hide();
      }

      if (code.includes("OB_") && $(exceptions["onboarding"]).is(":hidden")) {
        $(exceptions["onboarding"]).show();
        $(`${exceptions["onboarding"]} .menu-item`).hide();
        $("#COMPANYSETUP").show();
      }
      if (code.includes("WOM_") && $(exceptions["wom"]).is(":hidden")) {
        $(exceptions["wom"]).show();
        $(`${exceptions["wom"]} .menu-item`).hide();
      }

      /*if (code.includes("CS_") && $(exceptions["companysetup"]).is(':hidden')) {
        $(exceptions["companysetup"]).show();
        $(`${exceptions["companysetup"]} .menu-item`).hide()
      }*/
      if (code.includes("SHD_") && $(exceptions["scheduling"]).is(":hidden")) {
        $(exceptions["scheduling"]).show();
        $(`${exceptions["scheduling"]} .menu-item`).hide();
      }
      if (code.includes("HD_") && $(exceptions["helpdesk"]).is(":hidden")) {
        $(exceptions["helpdesk"]).show();
        $(`${exceptions["helpdesk"]} .menu-item`).hide();
      }
      if (code.includes("CALENDAR_") && $(exceptions["calendar"]).is(":hidden")) {
        $(exceptions["calendar"]).show();
        $(`${exceptions["calendar"]} .menu-item`).hide();
      }

      menu_id = "#".concat(code.toUpperCase());

      //first show the parent
      $(menu_id).show();
    }
  }
}

function stepper_controller(session) {
  if (session["wizard_data"]) {
    all_steps_except_last_one = $(
      "#stepper_body >  .stepper-item:not(:last-child)"
    );
    $(all_steps_except_last_one).addClass("completed");
  }
}

function handle_alerts_msgs(msg, alertype) {
  $("#alert_msg").show();
  $("#alert_msg > button").show();
  $("#alert_msg").removeAttr("class");
  $("#alert_msg").addClass(alertype);
  $(".prepended").remove();
  $("#alert_msg").prepend("<span class='prepended'>" + msg + "</span>");
  if (alertype.includes("success")) {
    $("#alert_msg")
      .fadeTo(2000, 500)
      .slideUp(500, function () {
        $("#alert_msg").slideUp(700);
      });
  }
}

function display_field_error(key, value) {
  let error = "<p class='errors'>" + value + "</p>";
  let fieldselector = "[name='" + key + "']";
  var field = $(fieldselector);
  if (field.is(":visible")) {
    handle_alerts_msgs(
      "Please resolve the following errors!",
      "alert alert-danger"
    );
    if (field.is("select") === true) {
      if (!field.next().find(".select2-selection").hasClass("is-invalid")) {
        field.next().find(".select2-selection").addClass("is-invalid");
        var tag = field.next();
        $(error).insertAfter(tag);
      }
    } else if(field.parent().hasClass("d-flex")) {
      let newField = field.parent('.d-flex')
      $(error).insertAfter(newField)
    }else {
      if (!field.hasClass("is-invalid")) {
        field.addClass("is-invalid");
        $(error).insertAfter(field);
      }
    }
  }
}

function display_form_errors(errors) {
  $("p.errors").remove();
  if (typeof errors == "string") {
    console.log("errors is a string");
    display_non_field_errors([errors]);
  }
  for (let key in errors) {
    console.log("errors is an object");
    if (Object.prototype.hasOwnProperty.call(errors, key)) {
      if (Object.prototype.hasOwnProperty.call(errors, "__all__")) {
        console.log("errors has non field errors");
        display_non_field_errors(errors["__all__"]); //non-field errors
      }
      display_field_error(key, errors[key]);
    }
  }
}
// ========= BEGIN single page CRUD ajax functions ========== //
function show_error_alert(msg, title = "") {
  heading = title !== "" ? title : "Error";
  Swal.fire(heading, msg, "error");
}

function show_successful_delete_alert() {
  Swal.fire({
    icon: "success",
    title: "Deleted successfully",
    showConfirmButton: false,
    timer: 1500,
  });
}

function show_successful_save_alert(update = false) {
  Swal.fire({
    icon: "success",
    title: update ? "Updated successfully!" : "Saved Successfully!",
    showConfirmButton: false,
    timer: 1500,
  });
}

function show_warning(msg) {
  if (msg) {
    return Swal.fire({
      icon: "warning",
      title: msg,
      showConfirmButton: false,
      timer: 1000,
    });
  }
}

function show_alert_before_delete(data) {
  return Swal.fire({
    title: `Delete ${data}`,
    html: `Are you sure you want to delete this <b>${data.toLowerCase()}</b>`,
    icon: "warning",
    showCancelButton: true,
    confirmButtonText: "Yes, delete it!",
  });
}

function show_alert_before_update(data) {
  return Swal.fire({
    title: `Upadate/Delete ${data}`,
    html: `Are you sure you want to update this record`,
    icon: "warning",
    showCancelButton: true,
    showDenyButton: true,
    denyButtonText: `Delete`,
    confirmButtonText: "Yes Update",
  });
}

function submit_form_alert(text = null, title = null) {
  console.log(title);
  return Swal.fire({
    title: title || "Submit Form?",
    html: text,
    icon: "question",
    showCancelButton: true,
    confirmButtonText: "Yes, Submit",
  });
}

function show_alert_before_update_jn(data) {
  return Swal.fire({
    title: `Upadate/Delete ${data}`,
    html: `Are you sure you want to update this record<br>OR<br><a id="jnd>View Details</a>`,
    icon: "warning",
    showCancelButton: true,
    showDenyButton: true,
    denyButtonText: `Delete`,
    confirmButtonText: "Yes Update",
  });
}

function display_non_field_errors(errors) {
  console.log(errors, "errors");
  $("#nonfield_errors").hide();
  var errstr = typeof errors === 'object' ? errors[0] : errors;

  $("#nonfield_errors").show();
  $("#nonfield_errors > span").text(errstr);
}

function display_modelfield_error(key, value) {
  error = "<p class='errors'>" + value + "</p>";
  lookup = "[name='" + key + "']";
  field = $(".modal-body").find(lookup);
  if ($(field).is("select") === true) {
    if ($(field).next().find(".select2-selection").hasClass("is-invalid")) {
      $(field).next().find(".select2-selection").addClass("is-invalid");
      var tag = $(field).next();
      $(error).insertAfter(tag);
    }
  } else if(field.parent().hasClass("d-flex")) {
    let newField = field.parent('.d-flex')
    $(error).insertAfter(newField)
  }else {
    if (!$(field).hasClass("is-invalid")) {
      $(field).addClass("is-invalid");
      $(error).insertAfter(field);
    }
  }
}

function display_modelform_errors(errors) {
  $("p.errors").remove();
  //non field errors
  if (
    Object.prototype.hasOwnProperty.call(errors, "__all__") ||
    typeof errors == "string" 
  ) {
    display_non_field_errors(errors.__all__ || errors);
  } else {
    //field errors
    for (let key in errors) {
      display_modelfield_error(key, errors[key]);
    }
  }
}

function fire_ajax_form_post(params, payload) {
  return $.ajax({
    url: params["url"],
    type: "post",
    data: payload,
  }).fail((xhr, status, error) => {
    console.log("xhr", xhr);
    if (
      typeof xhr.responseJSON.errors === "object" ||
      typeof xhr.responseJSON.errors === "string"
    ) {
      if (params.modal === true) {
        display_modelform_errors(xhr.responseJSON.errors);
      } else {
        display_form_errors(xhr.responseJSON.errors);
      }
    }else{
      show_error_alert("Something went wrong at server!", "ERROR")
    }
  });
}

function fire_ajax_fileform_post(params, payload) {
  return $.ajax({
    url: params["url"],
    type: "post",
    data: payload,
    processData: false,
    contentType: false,
  }).fail((xhr, status, error) => {
    console.log("xhr", xhr);
    console.log('payload', payload)
    console.log('params', params)
    if (
      typeof xhr.responseJSON.errors === "object" ||
      typeof xhr.responseJSON.errors === "string"
    ) {
      if (params.modal === true) {
        display_modelform_errors(xhr.responseJSON.errors);
      } else {
        console.log("not modal")
        display_form_errors(xhr.responseJSON.errors);
      }
    }
  });
}

function fire_ajax_get(params) {
  let data = Object.prototype.hasOwnProperty.call(params, "data")
    ? params.data
    : {};
  let callback = Object.prototype.hasOwnProperty.call(params, "beforeSend")
    ? params.beforeSend
    : function () {};
  return $.ajax({
    url: params.url,
    type: "get",
    data: data,
    beforeSend: callback(),
  });
}

function request_ajax_form_delete(params) {
  return $.ajax({
    url: params["url"],
    type: "get",
  })
    .fail((xhr, status, error) => {
      display_form_errors(xhr.responseJSON.errors);
    })
    .done((data, status, xhr) => {
      //hide modal
      $(params.modal_id).modal("hide");
      $(params.formid).html(data.html);

      handle_alerts_msgs(data.success, "alert alert-success");
    });
}

// ========= END single page CRUD ajax functions ==========  //

function auto_select_the_newly_created(field_id, data) {
  //remove errors text if there are any
  if ($(".input-grp > p").length > 0) {
    $(".input-grp .form-control, .input-grp select").removeClass("is-invalid");
    $(".input-grp > p").remove();
  }
  // Set the value, creating a new option if necessary
  if ($(field_id).find("option[value='" + data.id + "']").length) {
    $(field_id).val(data.id).trigger("change");
  } else {
    // Create a DOM Option and pre-select by default
    var newOption = new Option(data.tacode, data.id, true, true);
    // Append it to the select
    $(field_id).append(newOption).trigger("change");
  }
}

//return true if valid json string else false
function isValidJSON(jsonString) {
  try {
    JSON.parse(jsonString);
    return true;
  } catch (error) {
    return false;
  }
}

function sumit_popup_form(param) {
  $(param["form"]).on("submit", function (e) {
    e.preventDefault();
    $("form select[name='tatype']").prop("disabled", false);
    $.ajax({
      type: "POST",
      url: param["url"],
      data: $(param["form"]).serialize(),
      success: function (data, status, xhr) {
        if (data["saved"] !== true) {
          display_form_errors(data["errors"]);
        } else {
          auto_select_the_newly_created(param["field"], data);
          $(param["modal"]).modal("hide");
        }
      },
    });
  });
}

const openWizardConfig = {
  title: "Onboarding Wizard",
  html: "<p>Do you want to continue the wizard saved in draft or start a new wizard</p>",
  icon: "info",
  showDenyButton: true,
  showCancelButton: true,
  confirmButtonText: "Continue the wizard",
  denyButtonText: "Start a new wizard",
};

const wizardOpenedFromDraft = {
  title: "Success",
  icon: "success",
  html: "<h6>Wizard opened from draft</h6>",
};

const check_if_form_in_draft = (callback) => {
  $.ajax({
    url: WizardViewUrl,
    type: "get",
    success: function (data, status, xhr) {
      callback(data);
    },
  });
};
const deniedDraft = (callback) => {
  $.ajax({
    url: WizardViewUrl,
    data: {
      denied: true,
    },
    type: "get",
    success: function (data, status, xhr) {
      callback(data);
    },
  });
};

function initializeListOfPeoplesModal(ajaxData, urlname){
  $('#id_people_list').on('shown.bs.modal', function (event) {
    $.fn.dataTable.tables({visible: true, api: true}).columns.adjust();
    $('#id_people_list').modal({
        keyboard: false
    })
    peopleList = $("#tabListOfPeoples").DataTable({
      ajax:{
        url:urlname,
        data:function(d){
          return $.extend(d, ajaxData)
        }
      },
      retrieve: true,
      columns:[
        {data:'id', visible:false},
        {data:'people__peoplecode', title:'Code'},
        {data:'people__peoplename', title:'Name'}
      ],
      ordering:false, 
      deferRender: true,
      scrollX: true,
      dom:'rti',
    })
  })

}

const get_the_wizard = (response) => {
  Swal.fire(wizardOpenedFromDraft).then(() => {
    window.location.href = response.url;
  });
};

const saveAsDraft = (toquit = false, callback) => {
  $.ajax({
    url: saveAsDraftUrl,
    type: "get",
    data: { quit: toquit },
    success: function (res) {
      callback(res);
    },
  });
};

const quitwizard_config = {
  title: "Quit Wizard",
  html: "<p>Do you want to save changes.</p>",
  icon: "warning",
  showDenyButton: true,
  showCancelButton: true,
  confirmButtonText: "Save As Draft",
  denyButtonText: "Don't Save",
};

const delete_from_draft = (callback) => {
  $.ajax({
    url: deleteFromDraftUrl,
    type: "get",
    success: function (res) {
      callback(res);
    },
  });
};

const wizardSavedInDraft = {
  title: "Wizard has been saved in draft successfully",
  icon: "success",
  showDenyButton: false,
  showCancelButton: false,
};

const wizardDeletedFromDraft = {
  title: "Wizard has been deleted successfully",
  icon: "success",
  showDenyButton: false,
  showCancelButton: false,
};

const alert_before_attendance = () => {
  return Swal.fire({
    title: "Attendance Capture",
    icon: "warning",
    html: `<p>Attendance will be captured, please follow the instructions before proceed further.</p><br>
      <span class="text-danger">1.Scan your QR code.<br>
      2.For face capture, please align your face properly, improper alignment will affect the face recognition</span>`,
    showCancelButton: true,
    confirmButtonText: "Proceed",
    denyButtonText: "Cancel",
  });
};

function performIntersection(arr1, arr2) {
  const intersectionResult = arr1.filter((x) => arr2.indexOf(x) !== -1);
  return intersectionResult;
}

function load_alerton_field(optionsData, selected, id_ele) {
  console.log("id_ele", id_ele);
  $(id_ele).empty();
  for (let i = 0; i < optionsData.length; i++) {
    var data = { id: optionsData[i], text: optionsData[i] };
    var opt = new Option(data.text, data.id, false, false);
    $(id_ele).append(opt).trigger("change");
  }
  console.log("selected", selected);
  console.log("id_ele", id_ele);
  $(id_ele).val(selected).trigger("change");
}

function initialize_alerton_field(_optionsData, alertonData, cleaned, id) {
  if (!cleaned && _optionsData.length) {
    optionsData = _optionsData.split(",");
  }
  optionsData =
    typeof _optionsData == "string" ? _optionsData.split(",") : _optionsData;
  console.log(alertonData, "alertondata1");
  if (optionsData.length) {
    alertonData =
      alertonData.length > 0 && typeof alertonData == "string"
        ? alertonData.split(",")
        : alertonData;
    console.log(alertonData, optionsData, "alertondata");
    let selected = performIntersection(optionsData, alertonData);
    console.log(selected, "selected");
    load_alerton_field(optionsData, selected, id);
  }
}

function column_filtering(targets) {
  return function () {
    var api = this.api();

    // For each column
    api
      .columns(targets)
      .eq(0)
      .each(function (colIdx) {
        // Set the header cell to contain the input element
        var cell = $(".filters th").eq($(api.column(colIdx).header()).index());
        var title = $(cell).text();
        $(cell).html(
          '<input type="text" style="width:100%" placeholder="' + title + '" />'
        );

        // On every keypress in this input
        $("input", $(".filters th").eq($(api.column(colIdx).header()).index()))
          .off("keyup change")
          .on("keyup change", function (e) {
            e.stopPropagation();

            // Get the search value
            $(this).attr("title", $(this).val());
            var regexr = "({search})"; //$(this).parents('th').find('select').val();

            var cursorPosition = this.selectionStart;
            // Search the column for that value
            api
              .column(colIdx)
              .search(
                this.value !== ""
                  ? regexr.replace("{search}", "(((" + this.value + ")))")
                  : "",
                this.value !== "",
                this.value == ""
              )
              .draw();

            $(this)
              .focus()[0]
              .setSelectionRange(cursorPosition, cursorPosition);
          });
      });
  };
}
//return selected value of a field
function getSelectedValue(id, val = false) {
  var data = $(id).select2("data")[0];
  if (typeof data !== "undefined") {
    return val ? data.id : data.text;
  }
  return "NONE";
}

//on changing the question field of questionform
//select the readonly answertype field
function assignQuesType(text) {
  $("#id_answertype").val(text);
}

//check options field is valid before submit
function validate_optionsField() {
  var options =
    $("#id_options").val() !== "" ? JSON.parse($("#id_options").val()) : "";
  if (options.length > 0) {
    return true;
  } else {
    var errors = {
      options: "At least 2 options should be selected",
    };
    display_modelform_errors(errors);
  }
}

function showToastMsg(msg, icon, position = "bottom-end") {
  return Swal.fire({
    toast: true,
    html: `<strong>${msg}</strong>`,
    timer: 3500,
    showConfirmButton: false,
    position: position,
    icon: icon,
    timerProgressBar: true,
  });
}

//check alerton field is valid before submit
function validate_alertonField() {
  var options =
    $("#id_options").val() !== "" ? JSON.parse($("#id_options").val()) : "";
  if (options.length > 0) {
    var alerton =
      typeof $("id_alerton").val() !== "undefined"
        ? $("#id_alerton").val()
        : "";
    if (alerton.length > 0) {
      return true;
    } else {
      var errors = {
        alerton: "Please provide for the options you created",
      };
      display_modelform_errors(errors);
    }
  }
}

//collect qsetblng data for insertion in
//table -> "List of Assigned Questions"
function get_question_formdata() {
  var formData = {};

  formData["id_slno"] = $("#id_slno").val();
  formData["id_answertype"] = $("#id_answertype").val();

  formData["id_alerton"] =
    typeof $("#id_alerton").val() !== "undefined" ? $("#id_alerton").val() : "";
  formData["id_alertbelow"] = $("#id_alertbelow").val();
  formData["id_alertabove"] = $("#id_alertabove").val();
  formData["id_min"] = $("#id_min").val();
  formData["id_max"] = $("#id_max").val();
  formData["id_ismandatory"] = $("#id_ismandatory").is(":checked");
  formData["id_question"] = getSelectedValue("#id_question");
  formData["question_id"] = $("#id_question").val();
  formData["isavpt"] = $("#id_isavpt").is(":checked");
  formData["avpttype"] = $("#id_avpttype").val();
  formData["id_options"] = $("#id_options").val();

  $("#id_alerton").empty();

  return formData;
}
function cleanOptionsField(tag) {
  var options = [];
  tag.value.forEach((ele) => {
    options.push(ele.value);
  });
  options = JSON.stringify(options);
  options = options.replace("[", "").replace("]", "").replace(/['"]+/g, "");
  return options;
}

//clean the form data before inserting it into
//"List of Assigned Questions"
function cleanData(data) {
  //clean question
  if (data.id_question !== "NONE") {
    data.id_question = data.id_question.split(" | ")[0];
  }

  //clean alerton
  data.id_alerton =
    data.id_alerton !== ""
      ? JSON.stringify(data.id_alerton)
          .replace("[", "")
          .replace("]", "")
          .replace(/['"]+/g, "")
      : "";
  data.id_ismandatory = data.id_ismandatory === true ? "True" : "False";

  //according to answertype clean data
  if (data.id_answertype === "NUMERIC") {
    data = adjust_above_below(data, (for_table = true));
    data.id_options = "";
  } else if (
    data.id_answertype !== "NUMERIC" &&
    data.id_answertype !== "CHECKBOX" &&
    data.id_answertype !== "DROPDOWN" &&
    data.id_answertype !== "RATING"
  ) {
    data.id_min = data.id_max = "0.0";
    data.id_alerton = [];
  }

  return data;
}

function adjust_above_below(data, for_table = false, foreditor = false) {
  console.log(data, foreditor);
  if (
    typeof data.id_alertbelow !== "undefined" ||
    (typeof data.id_alertabove !== "undefined" && for_table)
  ) {
    data.id_alerton = `<${data.id_alertbelow}, >${data.id_alertabove}`;
    return data;
  } else if (
    data.includes(">") ||
    data.includes("<") ||
    data.includes("&lt;") ||
    (data.includes("&gt;") && !for_table)
  ) {
    var nums = data.split(", ");
    if (foreditor) {
      console.log(foreditor);
      $("#DTE_Field_alertbelow").val(
        parseFloat(nums[0].replace(/[^0-9\.-]+/g, ""))
      );
      $("#DTE_Field_alertabove").val(
        parseFloat(nums[1].replace(/[^0-9\.-]+/g, ""))
      );
    } else {
      $("#id_alertbelow").val(parseFloat(nums[0].replace(/[^0-9\.-]+/g, "")));
      $("#id_alertabove").val(parseFloat(nums[1].replace(/[^0-9\.-]+/g, "")));
    }
  }
}

//reset's all data inside the questionform
function resetForm() {
  $("#qsetbng_form").trigger("reset");
  $("#id_question, #id_answertype, #id_alerton").val(null).trigger("change");
  $("#id_alerton").empty();
}

//updates options in options field of questionform
function update_options_field(data, optionTag) {
  optionTag.removeAllTags();

  optionTag.addTags(data ? data.split(",") : "");
}

function update_qsetblng_form(data, optionTag, fortable = false) {
  $("#id_slno").val(parseInt(data[0], 10));
  $("select[name='question']").val(data[2]).trigger("change");
  $("#id_answertype").val(data[3]);
  $("#id_min").val(data[4]);
  $("#id_max").val(data[5]);
  $("#id_options").val(data[6]);
  //update_options_field(data[6], optionTag);
  initialize_alerton_field(
    data[6],
    data[7],
    (cleaned = true),
    (id = "#id_alerton")
  );
  data[8] = data[8] === "True" ? true : false;
  $("#id_ismandatory").attr("checked", data[8]);
  adjust_above_below(data[7], fortable);
  $("#id_isavpt").attr("checked", data[9]);
  $("#id_avpttype").val(data[10]);
  $("#resetQsetB").show();

  //$("#id_alertbelow").val(data.id_alertbelow)
  //$("#id_alertabove").val(data.id_alertabove)
}

//checks duplicates before inserting into
//datatable -> "List of Assigned Questions"
function check_for_duplicates(table, dataToInsert) {
  var tableData = table.rows().data().toArray();

  for (var row in tableData) {
    if (tableData[row][1] === dataToInsert[1]) {
      return true;
    }
  }
  return false;
}

function check_for_duplicate_record(table, key, colIndex) {
  var tableData = table.rows().data().toArray();

  for (var row in tableData) {
    if (tableData[row][colIndex] === key) {
      return true;
    }
  }
  return false;
}

//process the valid form
function processValidForm() {
  data = get_question_formdata();

  data = cleanData(data);

  rowdata = [
    -1,
    data.id_question,
    data.question_id,
    data.id_answertype,
    data.id_min,
    data.id_max,
    data.id_options,
    data.id_alerton,
    data.id_ismandatory,
    data.isavpt,
    data.avpttype,
  ];
  table.row(".toupdate").remove().draw(false);

  isduplicate = check_for_duplicates(table, rowdata, 1);

  if (!isduplicate) {
    table.row.add(rowdata).draw();
    resetForm();
    $("#deleteQuestion").hide();
  } else {
    let heading = "Duplicate Record";
    let msg = "This type ('Question and QuestionType') record is already exist";
    show_error_alert(msg, heading);
  }
}

function deleteQuestionRequest(question, answertype, qset, url) {
  const params = {
    quesname: question,
    url: `${url}?quesname=${question}&answertype=${answertype}&qset=${qset}`,
    beforeSend: function () {},
  };
  fire_ajax_get(params)
    .done((data, status, xhr) => {
      show_successful_delete_alert();
    })
    .fail((xhr, status, error) => {
      show_error_alert("Something went wrong!");
    });
}
function addRemoveClass(ele) {
  if ($(ele).hasClass("selected")) {
    $(ele).removeClass("selected");
  } else {
    table.$("tr.selected").removeClass("selected");
    $(ele).addClass("selected");
  }
}

function checkQsetWoQuestions(table) {
  rows = table.rows().data().toArray();
  return rows.length < 1; //returns true if qset w/o questions else false
}

function questionsWoQuestionSetAlert() {
  return show_error_alert(
    "You have not submitted any Questions yet, for this Question Set.",
    (title = "QuestionSet Without Questions")
  );
}

function warnFormCLoseAlert() {
  return Swal.fire({
    title: `Close Form`,
    text: `Do you really want to close the form, you won't be able to revert it!`,
    icon: "question",
    showCancelButton: true,
    confirmButtonText: "Yes, close it!",
  });
}

function getSlnoFromTable() {
  var lastrow = table.row(table.rows().count() - 1).data();
  const seqno = lastrow.length > 0 ? parseInt(lastrow[0], 10) + 1 : {};
  return seqno;
}

function adjustSlnoInTable() {
  var tableData = table.rows().data().toArray();
  table.rows().remove().draw();
  var seq = 0;
  for (var row in tableData) {
    seq++;
    tableData[row][0] = seq;
  }
  table.rows.add(tableData).draw();
}

//Autoadjust seqno
function adjustSlno(seqno, table, reset) {
  if (reset) {
    var tableData = table.rows().data().toArray();
    var seq = 0;
    for (var row in tableData) {
      seq++;
      tableData[row][0] = seq;
    }
    table.rows.add(tableData).draw();
  } else if (("None" || "") !== "{{ masterqset_form.instance.id }}") {
    //update row
    var lastrow = table.row(table.rows().count() - 1).data();
    seqno = lastrow.length > 0 ? parseInt(lastrow[0], 10) + 1 : ++seqno;
  } else {
    //create row
    ++seqno;

    $("#id_slno").prop("readonly", true);
  }
}

//convert to local
function convert_to_local(type, data, row) {
  if (type === "sort" || type === "type") {
    return data ? data : "-";
  }
  if (data) {
    let datetime = moment(data, "YYYY-MM-DDTHH:mm:ss")
      .add(row["ctzoffset"], "m")
      .format("DD-MMM-YYYY HH:mm");
    return data ? datetime : "-";
  }
  return data;
}

function utc_to_local(offset, datetime, format = null) {
  return moment(datetime, format ? format : "YYYY-MM-DDTHH:mm:ss")
    .add(offset, "m")
    .format(format ? "DD-MMM-YYYY" : "DD-MMM-YYYY HH:mm");
}

function initDatetimes(ids) {
  $(ids).flatpickr({
    enableTime: true,
    time_24hr: true,
    dateFormat: "d-M-Y H:S",
  });
}

function init_select_field(kwargs) {
  if (Object.prototype.hasOwnProperty.call(kwargs, "client") && kwargs.client) {
    $(kwargs.id).select2({
      allowClear: true,
      multiple: Object.prototype.hasOwnProperty.call(kwargs, "multiple")
        ? kwargs.multiple
        : false,
      closeOnSelect: Object.prototype.hasOwnProperty.call(
        kwargs,
        "closeOnSelect"
      )
        ? kwargs.closeOnSelect
        : true,
      placeholder: "Select an Option!",
    });
  } else {
    $(kwargs.id).select2({
      ajax: {
        url: kwargs.url,
        closeOnSelect: Object.prototype.hasOwnProperty.call(
          kwargs,
          "closeOnSelect"
        )
          ? kwargs.closeOnSelect
          : true,
        allowClear: true,
        multiple: Object.prototype.hasOwnProperty.call(kwargs, "multiple")
          ? kwargs.multiple
          : false,
        delay: 500,
        data: function (args) {
          var query = {
            search: args.term,
            type: "public",
            page: args.page,
          };
          return query;
        },
        minimumInputLength: 2,
        processResults: function (data, args) {
          args.page = args.page || 1;
          return {
            results: data.items,
            pagination: { more: args.page * 15 < data.tota_lcount },
          };
        },
        cache: true,
        placeholder: `Search for ${kwargs.item}..`,
      },
    });
  }
}

function initDateRangeHtml(id = null, range_ele = null) {
  let ele = id !== null ? id : "div.customfields";
  let range_id = range_ele !== null ? range_ele : "id_daterange";
  $(ele).html(`<div class="input-group pe-4 mt-2">
            <span class="input-group-text" id="basic-addon1">From: </span>
            <input type="text" id="${range_id}"class="form-control">
          </div>`);
}

//global date range picker
function initDateRange(element, start = null, end = null) {
  //console.log("element", element, ">> ", $(element));
  return $(element).daterangepicker(
    {
      opens: "right",
      startDate:
        start === null
          ? moment().subtract(7, "days")
          : moment(start, "YYYY-MM-DD"), //moment().subtract(7, 'days'),
      endDate: end === null ? moment() : moment(end, "YYYY-MM-DD"),
      //minDate: '01/01/2012',
      //maxDate: '12/31/2014',
      dateLimit: {
        days: 92,
      },
      showDropdowns: true,
      showWeekNumbers: true,
      timePicker: false,
      timePickerIncrement: 1,
      timePicker12Hour: true,
      ranges: {
        Tomorrow: [moment().add(1, "days"), moment().add(1, "days")],
        Today: [moment(), moment()],
        Yesterday: [moment().subtract(1, "days"), moment().subtract(1, "days")],
        "Last 7 Days": [moment().subtract(6, "days"), moment()],
        "Last 30 Days": [moment().subtract(29, "days"), moment()],
        "This Month": [moment().startOf("month"), moment().endOf("month")],
        "Last Month": [
          moment().subtract(1, "month").startOf("month"),
          moment().subtract(1, "month").endOf("month"),
        ],
        "Last 2 Month": [
          moment().subtract(2, "month").startOf("month"),
          moment().subtract(1, "month").endOf("month"),
        ],
        "Last 3 Month": [
          moment().subtract(3, "month").startOf("month"),
          moment().subtract(1, "month").endOf("month"),
        ],
      },
      buttonClasses: ["btn"],
      cancelClass: "default",
      dateFormat: "YYYY-MM-DD",
      separator: " to ",
      locale: {
        format: "DD/M/YYYY",
        separator: " ~ ",
        applyLabel: "Apply",
        fromLabel: "From",
        toLabel: "To",
        customRangeLabel: "Custom Range",
        daysOfWeek: ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"],
        monthNames: [
          "January",
          "February",
          "March",
          "April",
          "May",
          "June",
          "July",
          "August",
          "September",
          "October",
          "November",
          "December",
        ],
        firstDay: 1,
      },
    },
    function (start, end) {
      //console.log("@@@@", start);
      //$('#reportrange span').html(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
      //$(element).html(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
    }
  );
}

//============================================== DOCUMENT READY ===========================================//
$(document).ready(() => {
  $("#client_onboarding").click((e) => {
    e.preventDefault();
    check_if_form_in_draft((response) => {
      if (response.draft) {
        //open popup options
        Swal.fire(openWizardConfig).then((res) => {
          //user choses open from draft
          if (res.isConfirmed) {
            get_the_wizard(response);
          } else if (res.isDenied) {
            //user denied open from draft
            deniedDraft((response) => {
              if (response.isgranted) {
                window.location.href = response.url;
              }
            });
          }
        });
      } //user dont have any drafts
      else if (!response.draft) {
        window.location.href = response.url;
      }
    });
  });

  $("#save_wizard_form").click(() => {
    saveAsDraft(false, (res) => {
      if (res.saved) {
      } else {
      }
    });
  });

  $("#id_quitwizard").click(() => {
    Swal.fire(quitwizard_config).then((result) => {
      if (result.isConfirmed) {
        //save as draft execution
        saveAsDraft(true, (res) => {
          Swal.fire(wizardSavedInDraft).then((res) => {
            window.location.href = "/dashboard/";
          });
        });
      } else if (result.isDenied) {
        delete_from_draft((res) => {
          Swal.fire(wizardDeletedFromDraft).then(() => {
            window.location.href = deleteWizardUrl;
          });
        });
      }
    });
  });

  //initialize google map
  function initialize() {
    var myLatlng = new google.maps.LatLng(13.0839, 80.27);
    var mapOptions = {
      zoom: 7,
      center: myLatlng,
    };
    map = new google.maps.Map(
      document.getElementById("map-canvas"),
      mapOptions
    );

    autocomplete();
  }
});

function setUpDropzone(params) {
  var myDropzone = new Dropzone(params.formId, {
    url: params.uploadUrl,
    paramName: "img",
    maxFiles: 5,
    maxFileSize: 3,
    addRemoveLinks: true,
    resizeWidth: params.width || null,
    resizeHeight: params.height || null,
    acceptedFiles: params.hasOwnProperty('acceptedFiles') ? params.acceptedFiles : ".mp4,.png,.jpeg,.jpg,.xlsx,.xls,.pdf",
  });

  myDropzone.on("sending", function (file, xhr, formData) {
    formData.append("csrfmiddlewaretoken", params.csrftoken);
    formData.append("foldertype", params.foldertype);
    formData.append("ownername", params.ownername);
    formData.append("attachmenttype", params.attachmenttype);
    formData.append("peopleid", params.peopleid);
    formData.append("ctzoffset", params.ctzoffset);
    formData.append("ownerid", params.ownerid);
  });

  // Handle file upload
  myDropzone.on("success", function (file, response) {
    file.id = response.id;
    return file.upload.filename
  });

  //handle remove item
  myDropzone.on("removedfile", function (file) {
    show_alert_before_delete("File").then((res) => {
      if (res.isConfirmed) {
        fire_ajax_get({
          url: params.uploadUrl,
          data: {
            id: file.id,
            action: "delete_att",
            ownerid: params.ownerid,
            ownername: params.ownername,
          },
        })
          .done((data, status, xhr) => {
            console.log(data);
          })
          .fail((xhr, status, error) => {
            console.log(error);
          });
      } else {
        location.reload();
      }
    });
  });

  if (params.create_or_update === "update") {
    fire_ajax_get({
      url: params.uploadUrl,
      data: { owner: params.ownerid, action: "get_attachments_of_owner" },
    }).done((resp, status, xhr) => {
      for (let i = 0; i < resp.data.length; i++) {
        let file = {
          name: resp.data[i].filename,
          accepted: true,
          id: resp.data[i].id,
          size: resp.data[i].size,
        };
        let filepath = `${params.media_url}${resp.data[i].filepath.replace(
          "youtility4_media/",
          ""
        )}${resp.data[i].filename}`;
        console.log(file, filepath);
        myDropzone.displayExistingFile(file, filepath);
      }
    });
  }
}

//============================================== END DOCUMENT READY ===========================================//

function convertSecondsToHumanReadable(seconds) {
  // Calculate the time units
  let days = Math.floor(seconds / (24 * 60 * 60));
  let hours = Math.floor((seconds % (24 * 60 * 60)) / (60 * 60));
  let minutes = Math.floor((seconds % (60 * 60)) / 60);
  let sec = Number(seconds % 60).toFixed(2); // limit decimal places to 2

  // Create a human readable string
  let result = [];
  if (days) result.push(days + " day" + (days == 1 ? "" : "s"));
  if (hours) result.push(hours + " hour" + (hours == 1 ? "" : "s"));
  if (minutes) result.push(minutes + " minute" + (minutes == 1 ? "" : "s"));
  if (sec) result.push(sec + " second" + (sec == 1 ? "" : "s"));

  return result.join(", ");
}

//============================================== QSB EDITOR FUNCTIONS START===========================================//
function getCurrentEditingRow(editor, table) {
  return table.row({ selected: true }).data() || "None";
}

function hideAndShowFields(selected, editor) {
  if (typeof selected !== "undefined") {
    if (
      selected === "DROPDOWN" || 
      selected === "MULTISELECT" || 
      (selected === "CHECKBOX" && typeof selected !== "undefined")
    ) {
      editor
        .hide(["min", "max", "alertbelow", "alertabove"], false)
        .show(["alerton", "options"], false);
    } else if (selected === "RATING") {
      editor
        .hide(["alerton", "options", "alertbelow", "alertabove"], false)
        .show(["min", "max"], false);
    } else if (selected === "NUMERIC") {
      editor
        .hide(["alerton", "options"], false)
        .show(["min", "max", "alertbelow", "alertabove"], false);
    } else {
      editor.hide([
        "alerton",
        "options",
        "min",
        "max",
        "alertabove",
        "alertbelow",
      ]);
    }
  }
}

function appenAlerton(options) {
  clearSelection("#DTE_Field_alerton");
  for (let i = 0; i < options.length; i++) {
    if (
      $("#DTE_Field_alerton").find("option[value='" + options[i] + "']").length
    ) {
      //$('#DTE_Field_alerton').val(options[i]).trigger('change');
    } else {
      // Create a DOM Option and pre-select by default
      var newOption = new Option(options[i], options[i], false, false);
      // Append it to the select
      $("#DTE_Field_alerton").append(newOption).trigger("change");
    }
  }
}

function clearSelection(id) {
  //$(id).val(null).trigger('change');
  $(id).empty().trigger("change");
}

function clearForm(editor) {
  ["min", "max", "alertbelow", "alertabove", "options"].forEach((ele) => {
    editor.field(ele).val("");
  });
  clearSelection("#DTE_Field_alerton");
  clearSelection("#DTE_Field_question");
}

function editorOnOpenActions(url, editor, table, action) {
  // on change options set alerton
  if (action === "create" || action === "edit") {
    $(".DTE_Form_Buttons").append(
      '<button type="button" class="btn btn-primary" id="btnLoad">Load Question Data</button>'
    );

    //onclick load button call populateQsetForm function
    $("#btnLoad").on("click", function () {
      populateQsetForm($("#DTE_Field_question").val(), url);
    });

    $('[data-dte-e="form"]').attr("id", "id_childform"); // add id to form
    $(".DTE_Field").addClass("p-1"); // add css to form fields
    $("#DTE_Field_alerton, #DTE_Field_question").addClass(
      "form-control form-select"
    ); // add css to alerton form field

    // initialize select field question
    init_select_field({
      url: `${url}?action=loadQuestions`,
      id: "#DTE_Field_question",
      item: "Questoins",
    });

    // initialize select field alerton
    init_select_field({
      id: "#DTE_Field_alerton",
      client: true,
      closeOnSelect: false,
      multiple: true,
    });

    // on change question select field, autoselect type field
    $("#DTE_Field_question.form-select").on("change", function () {
      var _selectedText = getSelectedValue("#DTE_Field_question");
      var selected = _selectedText.split(" | ")[1];
      //hide/show fields based on selected text..
      hideAndShowFields(selected, editor);
      editor.field("answertype").val(selected);
      //populateQsetForm($("#DTE_Field_question").val())
    });
  }
  if (action == "create") {
    editor.field("seqno").set(table.data().count() + 1); //update seqno for new entry
    clearForm(editor);

    //if isavpt is checked show attachment type field else hide it
    $("#DTE_Field_isavpt").on("change", function () {
      if ($("#DTE_Field_isavpt").val() == "true") {
        $(".DTE_Field_Name_avpttype").show();
      } else {
        $(".DTE_Field_Name_avpttype").hide();
      }
    });
  }
  if (action == "edit") {
    initializeQSBForm(table, editor);
  }
}

function editorOnOpenedActions() {
  $("#DTE_Field_options").on("focusout", function () {
    var options = $(this).val();
    if (options.length > 0) {
      appenAlerton(options.replaceAll(", ", ",").split(","));
    } else {
      clearSelection("#DTE_Field_alerton");
    }
  });

  $("#DTE_Field_alerton .selection").focus(function () {
    console.log("worked");
    if ($("#DTE_Field_alerton option").length === 0) {
      let optArrr = getArrayFromString($("#DTE_Field_options").val());
      for (let i = 0; i < optArrr.length; i++) {
        var data = { id: optArrr[i], text: optArrr[i] };
        var opt = new Option(data.text, data.id, false, false);
        $("#DTE_Field_alerton").append(opt).trigger("change");
      }
    }
  });

  $("#DTE_Field_alerton").on("hover", function () {
    console.log("hovered");
  });
}

function editorFieldsConfig() {
  return [
    { data: "pk", type: "hidden", name: "pk", def: "None" },
    { label: "SNo.", type:"readonly", name: "seqno", data: "seqno" },
    { label: "Question", name: "question", type: "select", data: "question" },
    { label: "Type", name: "answertype", type: "readonly", data: "answertype" },
    { label: "Min", name: "min", type: "text", def: null },
    { label: "Max", name: "max", type: "text", def: null },
    { label: "Alert below", name: "alertbelow", type: "text", def: null },
    { label: "Alert above", name: "alertabove", type: "text", def: null },
    {
      label: "Option",
      name: "options",
      type: "text",
      fieldInfo: "Enter text ',' (comma) separated",
    },
    { label: "Alert On", name: "alerton", type: "select" },
    {
      label: "Mandatory",
      name: "ismandatory",
      type: "select",
      def: 1,
      options: [
        { label: "True", value: true },
        { label: "False", value: false },
      ],
    },
    {
      label: "Is Attachment Required",
      name: "isavpt",
      type: "select",
      def: false,
      options: [
        { label: "True", value: true },
        { label: "False", value: false },
      ],
    },
    {
      label: "Attachment Type",
      name: "avpttype",
      type: "select",
      def: "BACKCAMPIC",
      options: [
        { label: "NONE", value: "NONE" },
        { label: "Back Camera Pic", value: "BACKCAMPIC" },
        { label: "Front Camera Pic", value: "FRONTCAMPIC" },
        { label: "Audio", value: "AUDIO" },
        { label: "Video", value: "VIDEO" },
      ],
    },
  ];
}

function editorAjaxData(d, editor, table, parentid, csrf) {
  let currentRow = getCurrentEditingRow(editor, table);
  console.log(currentRow);
  d.parent_id = parentid;
  d.csrfmiddlewaretoken = csrf;
  d.question = true;
  d.alerton = JSON.stringify($("#DTE_Field_alerton").val());
  d.question_id = $("#DTE_Field_question").val();
  d.min = $("#DTE_Field_min").val();
  d.max = $("#DTE_Field_max").val();
  d.alertbelow = $("#DTE_Field_alertbelow").val();
  d.alertabove = $("#DTE_Field_alertabove").val();
  d.answertype = $("#DTE_Field_answertype").val();
  d.seqno = $("#DTE_Field_seqno").val();
  d.ismandatory = $("#DTE_Field_ismandatory").val();
  d.options = $("#DTE_Field_options").val();
  d.isavpt = $("#DTE_Field_isavpt").val();
  d.avpttype = $("#DTE_Field_avpttype").val();
  d.pk = currentRow ? currentRow["pk"] : currentRow;
  d.ctzoffset = $("#id_ctzoffset").val();
}

function QSBTableColumnsConfig() {
  return [
    { data: "pk", defaultContent: null, visible: false },
    { data: "ctzoffset", defaultContent: null, visible: false },
    {
      title: "SNo",
      data: "seqno",
      render: function (data, type, row, meta) {
        return data ? data : meta.row + 1;
      },
    },
    { title: "Question", data: "quesname" },
    { data: "question_id", visible: false, defaultContent: null },
    { title: "Question Type", data: "answertype" },
    {
      title: "Min",
      data: "min",
      render: function (data, type, row, meta) {
        return row["answertype"] !== "NUMERIC" ? "NA" : data;
      },
    },
    {
      title: "Max",
      data: "max",
      render: function (data, type, row, meta) {
        return row["answertype"] !== "NUMERIC" ? "NA" : data;
      },
    },
    {
      title: "Option",
      data: "options",
      render: function (data, type, row, meta) {
        return row["answertype"] !== "CHECKBOX" &&
          row["answertype"] !== "DROPDOWN"
          ? "NA"
          : data;
      },
    },
    {
      title: "Alert On",
      data: "alerton",
      render: function (data, type, row, meta) {
        return row["answertype"] == "CHECKBOX" ||
          row["answertype"] == "DROPDOWN" ||
          row["answertype"] == "NUMERIC"
          ? data
          : "NA";
      },
    },
    { title: "Mandatory", data: "ismandatory" },
    { visible: false, data: "isavpt" },
    { visible: false, data: "avpttype" },
  ];
}

function editorPreSubmitActions(editor, action) {
  if (action !== "remove" && editor.field("answertype").val() == "NUMERIC") {
    let min = editor.field("min");
    let max = editor.field("max");
    let alertbelow = editor.field("alertbelow");
    let alertabove = editor.field("alertabove");
    console.log(!min.isMultiValue(), isNaN(parseInt(min.val(), 10)) == NaN);

    if (!min.isMultiValue() && isNaN(parseInt(min.val(), 10))) {
      min.error("value of min must be number");
    }
    if (!max.isMultiValue() && isNaN(parseInt(max.val(), 10))) {
      max.error("value of max must be number");
    }
    if (!alertbelow.isMultiValue() && isNaN(parseInt(alertbelow.val()))) {
      alertbelow.error("value of alert below must be number");
    }
    if (!alertabove.isMultiValue() && isNaN(parseInt(alertabove.val()))) {
      alertabove.error("value of alert above must be number");
    }

    if (
      !(min.isMultiValue() && max.isMultiValue()) &&
      parseInt(min.val(), 10) > parseInt(max.val(), 10)
    ) {
      min.error("Min value must be smaller than Max value");
    }
    if (
      !(min.isMultiValue() && alertbelow.isMultiValue()) &&
      parseInt(alertbelow.val(), 10) < parseInt(min.val(), 10)
    ) {
      alertbelow.error("Alert Below value must be greater than Min value");
    }
    if (
      !(max.isMultiValue() && alertabove.isMultiValue()) &&
      parseInt(alertabove.val()) > parseInt(max.val(), 10)
    ) {
      max.error("Alert Above value must be smaller than Max value");
    }
    if (
      !(alertbelow.isMultiValue() && alertabove.isMultiValue()) &&
      parseInt(alertbelow.val(), 10) > parseInt(alertabove.val(), 10)
    ) {
      alertabove.error(
        "Alert Below value must be smaller than Alert Above value"
      );
    }
    // If any error was reported, cancel the submission so it can be corrected
    if (editor.inError()) {
      return false;
    }
  } else if (
    editor.field("answertype").val() == "DROPDOWN" ||
    editor.field("answertype").val() == "CHECKBOX"
  ) {
    let alerton = editor.field("alerton");
    let options = editor.field("options");
    if (!options.isMultiValue() && !options.val()) {
      options.error("options must be given");
    }
    if (editor.inError()) {
      return false;
    }
  }
}

function initializeQSBForm(table, editor) {
  var data = getCurrentEditingRow(editor, table);
  if (data !== "None") {
    console.log(data, "data");
    hideAndShowFields(data.answertype, editor);
    //init question
    var newOption = new Option(
      data.quesname.split(" | ")[0],
      data.question_id,
      true,
      true
    );
    $("#DTE_Field_question").append(newOption);

    //init type
    var _selectedText = getSelectedValue("#DTE_Field_question");
    editor.field("answertype").val(_selectedText.split(" | ")[1]);

    //init options
    //editor.field('options').val(data.options)

    //init alerton
    var options = data.options
      ? data.options.replaceAll(", ", ",").split(",")
      : [];
    if (options.length > 0) {
      appenAlerton(options);
      let alerton = data.alerton
        ? data.alerton.replaceAll(", ", ",").replaceAll('" ', '"').split(",")
        : [];
      $("#DTE_Field_alerton").val(alerton).trigger("change");
    }

    if (data.answertype === "NUMERIC" && data.alerton.length > 0) {
      //init max
      editor.field("max").val(data.max);
      //init min
      editor.field("min").val(data.min);
      //init alertbelow and alertabove
      let alerton = data.alerton;
      let aa = alerton.split(",")[1].replaceAll(">", ""); //alert-above
      let ab = alerton.split(",")[0].replaceAll("<", ""); //alert-below
      editor.field("alertbelow").val(ab);
      editor.field("alertabove").val(aa);
    }
    //init isavpt & avpttype
    editor.field("isavpt").val(data.isavpt);
    editor.field("ismandatory").val(data.ismandatory);
    editor.field("avpttype").val(data.avpttype);
  }
}

function modifyWidgets(element, time = false, date = false, datetime = false) {
  if (time) {
    $(element).flatpickr({
      enableTime: true,
      noCalendar: true,
      dateFormat: "H:i",
      time_24hr: true,
    });
  } else if (date) {
    $(element).flatpickr({
      dateFormat: "d-M-Y",
    });
  } else {
    $(element).flatpickr({
      enableTime: false,
      noCalendar: false,
      dateFormat: "Y-m-d",
    });
  }
}

//============================================== QSB EDITOR FUNCTIONS END===========================================//


function dynamicFormBehaviour(data, forschedule=false) {
  $('.datafield').addClass('d-none')
  const { fields, unsupported_formats } = data.behaviour;

  // Function to toggle visibility and required attribute
  function toggleFieldBehavior(fieldname) {
      const id = 'id_' + fieldname.replace('*', '');
      const $element = $('#' + id);

      if ($element.length > 0) {
          const closestInputGroup = $element.closest(".input-group");
          closestInputGroup.toggleClass("d-none");
          
          if (fieldname.includes('*')) {
              toggleRequiredAttribute(id, set = true);
          }
      }
  }

  // Toggle behavior for each field
  fields.forEach(fieldname => toggleFieldBehavior(fieldname));

  // Hide options based on unsupported formats
  if (unsupported_formats[0] !== 'None') {
      $("#id_format option").each(function() {
          const optionValue = $(this).val();
          if (optionValue && unsupported_formats.includes(optionValue)) {
              $(this).prop('disabled', true);
          }
      });
  }
}