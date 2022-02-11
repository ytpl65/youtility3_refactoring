//ajax start and ajaxStop events
$(document).on({
  ajaxStart: function(){ startBlockUi(); },
  ajaxStop: function() { endBlockUi(); } 
  
})

// $(window).load(function () {
//   endBlockUi();
// })

//creating environment for wizard
function make_env_for_wizard(session) {
  const wizard = session["wizard_data"];
  $(document).ready(function () {
    if (wizard != null) {
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

function alertuser_to_saveform(styles=""){
  Swal.fire({
    title:"Form Modified",
    html:`<p style="font-size:${styles.fs};color:${styles.cl}">Form is modified please save/update it first!</p>`,
    icon:"warning",
    color:"red"

  })
}

const  first_show_parent = (id) => {
  $(id).show()
}

//removes required attr from field specified.
function removeRequiredAttr(cls){
  if(cls === "numeric"){
      $("#id_min, #id_max").prop("required", false)
      $("#id_options, #id_alerton").prop("required", true)
      $("label[for='id_options'], label[for='id_alerton']").addClass("required")
      
      console.log("numeric are not required")
  }else if(cls === 'optionGrp'){
      $("#id_options, #id_alerton").prop("required", false)
      $("#id_options").prev().prop("required",false)
      $("#id_min, #id_max").prop("required", true)
      $("label[for='id_min'], label[for='id_max']").addClass("required")
      console.log("optionGRp is not required")
  }else{
    $("#id_options, #id_alerton, #id_min, #id_max").prop("required", false)
    console.log("all are not required")
  }
}

function showHideFields(selected){
    if(typeof selected!=="undefined"){
    var selectedText = selected.toUpperCase();
    if(selectedText.toUpperCase() === 'NUMERIC'){
        $(".numeric").show()
        $('.optionGrp').hide()
        removeRequiredAttr('optionGrp')
    }else if((selectedText === "DROPDOWN") || (selectedText === "RADIOGROUP" || (selectedText === "CHECKBOX"))){
        $('.optionGrp').show()
        $(".numeric").hide()
        removeRequiredAttr('numeric')
    }else{
        $(".numeric").hide()
        $('.optionGrp').hide()
        removeRequiredAttr('')

    }
  }
}

function populateAlertOn(txt){
  var data = {
      id:txt,
      text:txt}
  var newOption = new Option(data.text, data.id, false, false);
  $('#id_alerton').append(newOption).trigger('change');
}

function removeElmtFromAlertOn(txt){
  if(txt!==""){
  $(`#id_alerton option[value=${txt}]`).remove();}
}

function init_alerton(){

  $("#id_alerton").select2({
      placeholder: 'Select an option',
      closeOnSelect:false,
      allowClear:true,
      multiple:true
  })
}

function handle_rendering_of_menus(session) {
  const exceptions = {
    'config':"#configuration", 'admin':"#admin" 
  }
  if (session["is_superadmin"]) {
    //show every item if superadmin
    $(".menu-item").show();
  } else {
    //show menu-item based on user or client capabilites
    caps = session["is_admin"] ? session['client_webcaps'] : session['people_webcaps']; 
    console.log(session["people_webcaps"].length);
    console.log("caps length ",caps.length);
    console.log("caps ", caps);
    for (var i = 0; i < caps.length; i++) {
      parent = caps[i][0];
      childs = caps[i][1];
      console.log("parent", parent)
      console.log("childs", childs)
      if(parent.startsWith("CONFIG_")){
        first_show_parent(exceptions['config'])
      }else if(parent.startsWith('ADMIN_')){
        first_show_parent(exceptions['admin'])
      }
      parent = parent.replace(" ", "_");
      //creating 'id'
      parent_id = "#".concat(parent.toLowerCase());
      console.log("parent", parent_id);
      $(parent_id).show();
      //sub-items within parent
      parent_items = parent_id + " .menu-item";
      $(parent_items).hide();
      for (var j = 0; j < childs.length; j++) {
        //showing every child inside the parent
        child = childs[j][0];
        child_id = "#".concat(child.toLowerCase());
        console.log("child", child_id);
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

function handle_alerts_msgs(msg, alertype){
  $("#alert_msg").show()
  $("#alert_msg > button").show()
  $("#alert_msg").removeAttr('class')
  $("#alert_msg").addClass(alertype)
  $(".prepended").remove()
  $("#alert_msg").prepend("<span class='prepended'>" + msg +"</span>")
  if(alertype.includes("success")){
    $("#alert_msg").fadeTo(2000, 500).slideUp(500, function(){
      $("#alert_msg").slideUp(700);
    })
  }
  
}


function display_form_errors(errors) {
  /*display errors on respective fields*/
  console.log("started")
  $('p.errors').remove();
  for (let key in errors) {
    if (errors.hasOwnProperty(key)) {
      if(errors.hasOwnProperty("__all__")){
        display_non_field_errors(errors)//non-field errors
      }
      let error = "<p class='errors'>" + errors[key] + "</p>";
      let field = "[name='" + key + "']";
      if($(field).is(":visible")){
        handle_alerts_msgs("Please resolve the following errors!", "alert alert-danger")
        $(field).addClass("is-invalid")
        $(error).insertAfter(field);
        console.log("inserted")
        $(field).next("p").css(
          {"color":"red", "font-size":"15px"}
          );
      }
    }
  }
}
// ====== BEGIN single page CRUD ajax functions ======= //
function show_error_alert(msg, title=""){
  heading = title!=="" ? title : "Error"
  Swal.fire(
    heading,
    msg,
    'error'
  )
}


function show_successful_delete_alert(){
  Swal.fire({
    icon: 'success',
    title: 'Deleted successfully',
    showConfirmButton: false,
    timer: 1500
  })
}

function show_warning(msg){
  if(msg){
    return Swal.fire({
      icon:'warning',
      title:msg,
      showConfirmButton:false,
      timer:1000,
    })
  }
}

function show_alert_before_delete(data){
 return Swal.fire({
      title:`Delete ${data}`,
      html:`Are you sure you want to delete this <b>${data.toLowerCase()}</b>`,
      icon:"warning",
      showCancelButton: true,
      confirmButtonText: 'Yes, delete it!'
    })
}

function show_alert_before_update(data){
  return Swal.fire({
    title:`Upadate/Delete ${data}`,
    html:`Are you sure you want to update this record`,
    icon:'warning',
    showCancelButton:true,
    showDenyButton:true,
    denyButtonText: `Delete`,
    confirmButtonText:"Yes Update"
  })
}

function submit_form_alert(){
  return Swal.fire({
    title:"Submit Form?",
    icon:"question",
    showCancelButton:true,
    confirmButtonText:"Yes, Submit"
  })
}

function show_alert_before_update_jn(data){
  return Swal.fire({
    title:`Upadate/Delete ${data}`,
    html:`Are you sure you want to update this record<br>OR<br><a id="jnd>View Details</a>`,
    icon:'warning',
    showCancelButton:true,
    showDenyButton:true,
    denyButtonText: `Delete`,
    confirmButtonText:"Yes Update"
  })
}

function display_non_field_errors(errors){
  var errstr = ""
  var brtag = "<br>"
  for(let i=0; i< errors.length; i++){
    if(!i=== errors.length -1){
      var msg = errors[i] + brtag
    }else{
      var msg = errors[i]
    }
    errstr += msg 
  }
  console.log(errstr)
  $("#nonfield_errors").show()
  $("#nonfield_errors > span").text(errstr)
}


function display_modelform_errors(errors){
  $('p.errors').remove();
  //non field errors
  if(errors.hasOwnProperty("__all__") || (errors instanceof String)){
    display_non_field_errors(errors.__all__)
  }else if (errors instanceof String){
    display_non_field_errors(errors)
  }else{
  //field errors
  for(let key in errors){
    error = "<p class='errors'>" + errors[key] + "</p>";
    lookup = "[name='" + key + "']";
    field = $(".modal-body").find(lookup)
    if($(field).is("select") === true){
      $(field).next().find(".select2-selection").addClass("is-invalid")
      var tag = $(field).next()
      $(error).insertAfter(tag);
    }else if(key === 'options'){
      var tag = $(field).prev()
      $(erros).insertAfter(tag)
    }
    else{
      $(field).addClass("is-invalid")
      $(error).insertAfter(field);
    }
  }}

}


function fire_ajax_form_post(params, payload){
  return $.ajax({
    url:params['url'],
    type:"post",
    data:payload
  }).fail((xhr, status, error) =>{
    console.log(xhr)
    console.log(status)
    console.log(error)
    if(params.modal === true){
    display_modelform_errors(xhr.responseJSON.errors)
    }else{
      display_form_errors(xhr.responseJSON.errors)
    }
  })
}


function fire_ajax_get(params){
  return $.ajax({
    url:params['url'],
    type:"get",
    beforeSend:params['beforeSend'](),
  })
}

function request_ajax_form_delete(params){
  return $.ajax({
    url:params['url'],
    type:"get",
  }).fail((xhr, status, error) =>{
    console.log(xhr)
    console.log(status)
    console.log(error)
    display_form_errors(xhr.responseJSON.errors)
  }).done((data, status, xhr) => {
      //hide modal
      $(params.modal_id).modal('hide');
      $(params.formid).html(data.html)
    console.log(data)
    console.log(status)
    console.log(xhr)
    handle_alerts_msgs(data.success, "alert alert-success")

  })
}

// ====== END single page CRUD ajax functions =======  //


function auto_select_the_newly_created(field_id, data) {
  console.log("called");
  console.log(data);
  //remove errors text if there are any
  if($(".input-grp > p").length>0){
    $(".input-grp .form-control, .input-grp select").removeClass("is-invalid")
    $(".input-grp > p").remove()
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
    $("form select[name='tatype']").prop("disabled", false)
    $.ajax({
      type: "POST",
      url: param["url"],
      data: $(param["form"]).serialize(),
      success: function (data, status, xhr) {
        console.log("data:", data);
        if (data["saved"] != true) {
          console.log("errors occured");
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

console.log("session", session);

const check_if_form_in_draft = (callback) => {
  console.log("check_if_form_in_draft is initiated....");
  $.ajax({
    url: WizardViewUrl,
    type: "get",
    success: function (data, status, xhr) {
      console.log(`reponse:data = ${data} status = ${status} xhr=${xhr}`);
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
  console.log(`get the wizard: ${response.url}`);
  Swal.fire(wizardOpenedFromDraft).then(() => {
    window.location.href = response.url;
  });
  console.log("wizard continued from previous stage");
};

const saveAsDraft = (toquit = false, callback) => {
  $.ajax({
    url: saveAsDraftUrl,
    type: "get",
    data: { "quit": toquit },
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
      console.log("res", res);
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
    title:"Attendance Capture",
    icon:"warning",
    html:`<p>Attendance will be captured, please follow the instructions before proceed further.</p><br>
      <span class="text-danger">1.Scan your QR code.<br>
      2.For face capture, please align your face properly, improper alignment will affect the face recognition</span>`,
    showCancelButton: true,
    confirmButtonText: "Proceed",
    denyButtonText: "Cancel",
  })
}

function performIntersection(arr1, arr2){
  const intersectionResult = arr1.filter(x => arr2.indexOf(x) !== -1);
  return intersectionResult;
}

function load_alerton_field(optionsData, selected){
  console.log(optionsData.length, optionsData)
  $("#id_alerton").empty();
  for(let i=0; i<optionsData.length; i++){
      var data = {id:optionsData[i], text:optionsData[i]}
      var opt  = new Option(data.text, data.id, false, false)
      $('#id_alerton').append(opt).trigger('change');
      console.log(i, opt)
  }
  $('#id_alerton').val(selected).trigger('change');
}


function initialize_alerton_field(_optionsData, alertonData, questype, cleaned){
    console.log(_optionsData, alertonData)
    _optionsData = _optionsData.length ? JSON.parse(_optionsData) : ""
    optionsData  = []
    if(!cleaned && _optionsData !== ""){
      _optionsData.forEach((item) => {
      optionsData.push(item.value.toUpperCase())
  })
  console.log("not cleaned")}else{optionsData = _optionsData
  console.log("cleaned")}
    console.log(optionsData, alertonData)
    if(optionsData.length && alertonData.length){
    let selected = performIntersection(optionsData, alertonData)
    console.log(selected)
    load_alerton_field(optionsData, selected)
    }
  
}

function column_filtering(targets){
  return function () {
    var api = this.api();

    // For each column
    api
        .columns(targets)
        .eq(0)
        .each(function (colIdx) {
            // Set the header cell to contain the input element
            var cell = $('.filters th').eq(
                $(api.column(colIdx).header()).index()
            );
            var title = $(cell).text();
            $(cell).html('<input type="text" style="width:100%" placeholder="' + title + '" />');

            // On every keypress in this input
            $(
                'input',
                $('.filters th').eq($(api.column(colIdx).header()).index())
            )
                .off('keyup change')
                .on('keyup change', function (e) {
                    e.stopPropagation();

                    // Get the search value
                    $(this).attr('title', $(this).val());
                    var regexr = '({search})'; //$(this).parents('th').find('select').val();

                    var cursorPosition = this.selectionStart;
                    // Search the column for that value
                    api
                        .column(colIdx)
                        .search(
                            this.value != ''
                                ? regexr.replace('{search}', '(((' + this.value + ')))')
                                : '',
                            this.value != '',
                            this.value == ''
                        )
                        .draw();

                    $(this)
                        .focus()[0]
                        .setSelectionRange(cursorPosition, cursorPosition);
                });
        });
}
}

//=============================== DOCUMENT READY =============================//
$(document).ready(() => {
  $("#client_onboarding").click((e) => {
    console.log("menu clicked");
    e.preventDefault();
    check_if_form_in_draft((response) => {
      if (response.draft) {
        console.log("wizard found in draft");
        //open popup options
        Swal.fire(openWizardConfig).then((res) => {
          //user choses open from draft
          if (res.isConfirmed) {
            console.log("open wizard from draft requested...");
            get_the_wizard(response);
          } else if (res.isDenied) {
            console.log("open wizard from draft denied...");
            //user denied open from draft
            deniedDraft((response) => {
              console.log(
                "open wizard from draft denied from user therefore starting a new wizard"
              );
              if (response.isgranted) {
                window.location.href = response.url;
                console.log(
                  "wizard opened from start, old wizard data deleted from draft successfully"
                );
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
    console.log("save_wizard_form is clicked ...");
    saveAsDraft(false, (res) => {
      if (res.saved) {
        console.log(`Draft wizard is ${res.status}`);
      } else {
        console.log("saveAsDraft() failed to save in draft");
      }
    });
    console.log("saveAsDraft() is terminated...");
  });

  $("#id_quitwizard").click(() => {
    console.log("id_quitwizard clicked....");
    Swal.fire(quitwizard_config).then((result) => {
      if (result.isConfirmed) {
        console.log("save as draft requested....");
        //save as draft execution
        saveAsDraft(true, (res) => {
          console.log(`Draft wizard is ${res.status}`);
          Swal.fire(wizardSavedInDraft).then((res) => {
            window.location.href = "/dashboard/";
          });
        });
      } else if (result.isDenied) {
        delete_from_draft((res) => {
          console.log(`wizard is ${res.status}`);
          console.log("delete wizard requested....");
          Swal.fire(wizardDeletedFromDraft).then(() => {
          window.location.href = deleteWizardUrl;
        });
        });
        
      }
    });
  });
});
//=============================== END DOCUMENT READY =============================//
