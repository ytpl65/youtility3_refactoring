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

//creating environment for wizard
function make_env_for_wizard(session) {
  const wizard = session["wizard_data"];
  $(document).ready(function () {
    if (wizard !== null) {
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
    $("#id_min, #id_max").prop("required", false);
    $("#id_options, #id_alerton").prop("required", true);
    $("label[for='id_options'], label[for='id_alerton']").addClass("required");
  } else if (cls === "optionGrp") {
    $("#id_options, #id_alerton").prop("required", false);
    $("#id_options").prev().prop("required", false);
    $("#id_min, #id_max").prop("required", true);
    $("label[for='id_min'], label[for='id_max']").addClass("required");
  } else {
    $("#id_options, #id_alerton, #id_min, #id_max").prop("required", false);
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
    config: "#configuration",
    admin: "#admin",
  };
  if (session["is_superadmin"]) {
    //show every item if user is superadmin
    $(".menu-item").show();
  } else {
    /*======show menu-item based on user or client capabilites======*/

    //if user is admin show client webcaps else people webcaps
    caps = session["is_admin"]
      ? session["client_webcaps"]
      : session["people_webcaps"];
    //console.log(session["people_webcaps"].length);
    //console.log("caps length ",caps.length);
    //console.log("caps ", caps);

    //for every cap
    for (var i = 0; i < caps.length; i++) {
      parent = caps[i][0];
      childs = caps[i][1];

      if (parent.startsWith("CONFIG_") || parent.startsWith("CONFIG")) {
        first_show_parent(exceptions["config"]);
      } else if (parent.startsWith("ADMIN_") || parent.startsWith("ADMIN")) {
        first_show_parent(exceptions["admin"]);
      }

      //replace spaces with underscores if there any...
      parent = parent.replace(" ", "_");
      //creating parent id
      parent_id = "#".concat(parent.toLowerCase());

      //first show the parent
      $(parent_id).show();

      //first hide all sub-items within parent
      parent_items = parent_id + " .menu-item";
      $(parent_items).hide();

      //then showing every child assigned inside that parent
      for (var j = 0; j < childs.length; j++) {
        child = childs[j][0];
        child_id = "#".concat(child.toLowerCase());

        $(child_id).show();
      }
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

function display_form_errors(errors) {
  /*display errors on respective fields*/

  $("p.errors").remove();
  if (errors instanceof String) {
    display_non_field_errors([errors]);
  }
  for (let key in errors) {
    if (Object.prototype.hasOwnProperty.call(errors, key)) {
      if (Object.prototype.hasOwnProperty.call(errors, "__all__")) {
        display_non_field_errors(errors); //non-field errors
      }
      let error = "<p class='errors'>" + errors[key] + "</p>";
      let field = "[name='" + key + "']";
      if ($(field).is(":visible")) {
        handle_alerts_msgs(
          "Please resolve the following errors!",
          "alert alert-danger"
        );
        $(field).addClass("is-invalid");
        $(error).insertAfter(field);

        $(field).next("p").css({ color: "red", "font-size": "15px" });
      }
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

function submit_form_alert() {
  return Swal.fire({
    title: "Submit Form?",
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
  $("#nonfield_errors").hide();
  var errstr = errors[0];

  $("#nonfield_errors").show();
  $("#nonfield_errors > span").text(errstr);
}

function display_modelform_errors(errors) {
  $("p.errors").remove();
  //non field errors
  if (
    Object.prototype.hasOwnProperty.call(errors, "__all__") ||
    errors instanceof String
  ) {
    display_non_field_errors(errors.__all__);
  } else if (errors instanceof String) {
    display_non_field_errors(errors);
  } else {
    //field errors
    for (let key in errors) {
      error = "<p class='errors'>" + errors[key] + "</p>";
      lookup = "[name='" + key + "']";
      field = $(".modal-body").find(lookup);
      if ($(field).is("select") === true) {
        $(field).next().find(".select2-selection").addClass("is-invalid");
        var tag = $(field).next();
        $(error).insertAfter(tag);
      } else if (key === "options") {
        var tag = $(field).prev();
        $(erros).insertAfter(tag);
      } else {
        $(field).addClass("is-invalid");
        $(error).insertAfter(field);
      }
    }
  }
}

function fire_ajax_form_post(params, payload) {
  return $.ajax({
    url: params["url"],
    type: "post",
    data: payload,
  }).fail((xhr, status, error) => {
    if (
      typeof xhr.responseJSON.errors === "object" ||
      typeof xhr.responseJSON.errors === "string"
    ) {
      if (params.modal === true) {
        display_modelform_errors(xhr.responseJSON.errors);
      } else {
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

function sumit_popup_form(param) {
  $(param["form"]).on("submit", function (e) {
    e.preventDefault();
    $("form select[name='tatype']").prop("disabled", false);
    $.ajax({
      type: "POST",
      url: param["url"],
      data: $(param["form"]).serialize(),
      success: function (data, status, xhr) {
        if (data["saved"] ! true) {
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

function load_alerton_field(optionsData, selected, id) {
  $(id).empty();
  for (let i = 0; i < optionsData.length; i++) {
    var data = { id: optionsData[i], text: optionsData[i] };
    var opt = new Option(data.text, data.id, false, false);
    $(id).append(opt).trigger("change");
  }
  $(id).val(selected).trigger("change");
}

function initialize_alerton_field(
  _optionsData,
  alertonData,
  questype,
  cleaned,
  id
) {
  _optionsData = _optionsData.length ? _optionsData.split(",") : "";
  optionsData = [];
  if (!cleaned && _optionsData !== "") {
    _optionsData = JSON.parse(_optionsData);
    _optionsData.forEach((item) => {
      optionsData.push(item.value);
    });
  } else {
    optionsData = _optionsData;
  }

  if (optionsData.length && alertonData.length) {
    alertonData = alertonData.split(",");
    let selected = performIntersection(optionsData, alertonData);

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
function getSelectedValue(id) {
  var data = $(id).select2("data")[0];
  if (typeof data !== "undefined") {
    return data.text;
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

function showToastMsg(msg, icon) {
  return Swal.fire({
    toast: true,
    html: `<strong>${msg}</strong>`,
    timer: 3500,
    showConfirmButton: false,
    position: "top-end",
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

  formData["id_options"] =
    $("#id_options").val() !== "" ? JSON.parse($("#id_options").val()) : "";
  //formData['id_question']      = getSelectedValue("#id_question")

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
  //clean options

  if (data.id_options !== "") {
    var options = [];
    data.id_options.forEach((ele) => {
      options.push(ele.value);
    });
    options = JSON.stringify(options);
    options = options.replace("[", "").replace("]", "").replace(/['"]+/g, "");
    data.id_options = options;
  }
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
    data.id_answertype !== "DROPDOWN"
  ) {
    data.id_min = data.id_max = "0.0";
    data.id_alerton = [];
  }

  return data;
}

function adjust_above_below(data, for_table = false) {
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
    $("#id_alertbelow").val(parseFloat(nums[0].replace(/[^0-9\.]+/g, "")));
    $("#id_alertabove").val(parseFloat(nums[1].replace(/[^0-9\.]+/g, "")));
  }
}

//reset's all data inside the questionform
function resetForm(tag_field) {
  $("#qsetbng_form").trigger("reset");
  $("#id_question, #id_answertype, #id_alerton").val(null).trigger("change");
  $("#id_alerton").empty();
  tag_field.removeAllTags();
}

//updates options in options field of questionform
function update_options_field(data, optionTag) {
  optionTag.removeAllTags();

  optionTag.addTags(data !== "" ? data.split(",") : "");
}

function update_qsetblng_form(data, optionTag, fortable = false) {
  $("#id_slno").val(parseInt(data[0], 10));
  $("select[name='question']")
    .val($(`select option:contains(${data[1]})`).val())
    .change();
  $("#id_answertype").val(data[3]);
  $("#id_min").val(data[4]);
  $("#id_max").val(data[5]);
  update_options_field(data[6], optionTag);
  initialize_alerton_field(data[6], data[7], data[3], (cleaned = true));
  data[8] = data[8] === "True" ? true : false;
  $("#id_ismandatory").attr("checked", data[8]);
  adjust_above_below(data[7], fortable);
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
  ];
  table.row(".toupdate").remove().draw(false);

  isduplicate = check_for_duplicates(table, rowdata);

  if (!isduplicate) {
    table.row.add(rowdata).draw();
    resetForm(optionTag);
    $("#deleteQuestion").hide();
  } else {
    let heading = "Duplicate Record";
    let msg = "This type ('Question and QuestionType') record is already exist";
    show_error_alert(msg, heading);
  }
}

function deleteQuestionRequest(question, answertype, qset) {
  const params = {
    quesname: question,
    url: `{{ url('activity:delete_qsb') }}?quesname=${question}&answertype=${answertype}&qset=${qset}`,
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
  } else if ("{{ masterqset_form.instance.id }}" !== ("None" || "")) {
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

function initDateRangeHtml() {
  $("div.customfields").html(`<div class="input-group pe-4">
            <span class="input-group-text" id="basic-addon1">From: </span>
            <input type="text" id="id_daterange"class="form-control">
          </div>`);
}

//global date range picker
function initDateRange(element) {
  //console.log("element", element, ">> ", $(element));
  return $(element).daterangepicker(
    {
      opens: "right",
      startDate: moment().subtract(7, "days"), //moment().subtract(7, 'days'),
      endDate: moment(),
      //minDate: '01/01/2012',
      //maxDate: '12/31/2014',
      dateLimit: {
        days: 90,
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
//============================================== END DOCUMENT READY ===========================================//
