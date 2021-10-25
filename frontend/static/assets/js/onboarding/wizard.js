
if (session.hasOwnProperty("wizard_data")) {
    //Alert config for quit wizard
    const quitwizard_config = {
      title: "Quit Wizard",
      text: "Do you want to save changes.",
      icon: "warning",
      showDenyButton: true,
      showCancelButton: true,
      confirmButtonText: "Save As Draft",
      denyButtonText: "Don't Save",
    };
  
    //Alert config for quit wizard
    const openWizardConfig = {
      title: "Onboarding Wizard",
      text: "Do you want to continue the wizard saved in draft or start a new wizard",
      icon: "info",
      showDenyButton: true,
      showCancelButton: true,
      confirmButtonText: "Continue the wizard",
      denyButtonText: "Start a new wizard",
    };
  
    
  
    $(document).ready(() => {
        if (checkWizardInDraft) {
          /*display options to load from 
          draft or start a new wizard*/
          Swal.fire(openWizardConfig).then((result) => {
            if (result.isConfirmed) {
              console.log("open wizard from draft requested...");
              //open draft wizard
              populateWizard();
            } else if (result.isDenied) {
              console.log("open wizard from draft denied...");
              //open new wizard from start
              window.location.href = newWizardUrl;
              console.log("new wizard redirected...");
            }
          });
        }
      $("#id_quitwizard").click(() => {
        console.log("id_quitwizard clicked....");
        Swal.fire(quitwizard_config).then((result) => {
          if (result.isConfirmed) {
            console.log("save as draft requested....");
            //save as draft execution
            saveAsDraft();
          } else if (result.isDenied) {
            console.log("delete wizard requested....");
            window.location.href = deleteWizardUrl;
          }
        });
      });
    });
  
    let formId = session["wizard_data"]["formid"];
    const current_location = currentUrl;
    const formIdentifier = `${current_location} ${formId}`;
    const wizard_data = session["wizard_data"];
    let form = $(`#${formId}`);
  
    const getFormData = () => {
      console.log("getFormData is initiated...");
      let data = { wizard_data: wizard_data };
      return data;
    };
  
    const saveAsDraft = () => {
      console.log("saveAsDraft is initiated...");
      data = getFormData();
      console.log("getFormData is terminated...");
      localStorage.setItem("formData", JSON.stringify(data));
    };
  
    let form_url = "";
  
    const populateWizard = () => {
      console.log("populated wizard started...");
      if (localStorage.key("formData")) {
        console.log("found formData inside local storage...");
        const savedData = JSON.parse(localStorage.getItem("formData"));
        console.log("formData parsed from json parse...");
        if (setSessionInRequest(savedData) == true) {
          console.log("setSessionInRequest returned true...");
          const message = "wizard has been continued from last saved location";
          Swal.fire({
            title: "Wizard Loaded",
            text: message,
            confirmButtonText: "Okay Got It!",
          });
          //remove key after form loaded
          localStorage.removeItem("formData");
          console.log("formData key removed from localstorage...");
          loadWizard(savedData["wizard_data"], true);
        }
        window.location.href = newWizardUrl;
      }
    };
  
    $("#save_wizard_form").click(() => {
      console.log("save_wizard_form is clicked ...");
      saveAsDraft();
      console.log("saveAsDraft is terminated...");
    });
  }