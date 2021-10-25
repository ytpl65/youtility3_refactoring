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

function handle_rendering_of_menus(session) {
  console.log("called");
  if (session["is_superadmin"]) {
    //show every item if superadmin
    $(".menu-item").show();
  } else {
    //show menu-item based on user or client capabilites
    caps =
      session["people_webcaps.length"] != 0
        ? session["people_webcaps"]
        : session["client_webcaps"];
    console.log(session["people_webcaps"].length);
    console.log(caps.length);
    for (var i = 0; i < caps.length; i++) {
      parent = caps[i][0];
      childs = caps[i][1];
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

function display_form_errors(errors) {
  /*display errors on respective fields*/
  for (let key in errors) {
    if (errors.hasOwnProperty(key)) {
      error = "<p>" + errors[key] + "</p>";
      field = "input[name='" + key + "']";
      console.log("fields", field);
      $(field).next("p").remove();
      $(error).insertAfter(field);
      $(field).next("p").css("color", "red");
    }
  }
}

function auto_select_the_newly_created(field_id, data) {
  console.log("called");
  console.log(data);
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
    console.log("triggered");
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

const saveAsDraft = (quit = false, callback) => {
  $.ajax({
    url: saveAsDraftUrl,
    type: "get",
    data: { quit: quit },
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
    saveAsDraft((res) => {
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
