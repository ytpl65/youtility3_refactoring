
if (Object.prototype.hasOwnProperty.call(session, 'wizard_data')) {
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
              
              //open draft wizard
              populateWizard();
            } else if (result.isDenied) {
              
              //open new wizard from start
              window.location.href = newWizardUrl;
              
            }
          });
        }
      $("#id_quitwizard").click(() => {
        
        Swal.fire(quitwizard_config).then((result) => {
          if (result.isConfirmed) {
            
            //save as draft execution
            saveAsDraft();
          } else if (result.isDenied) {
            
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
      
      let data = { wizard_data: wizard_data };
      return data;
    };
  
    const saveAsDraft = () => {
      
      data = getFormData();
      
      localStorage.setItem("formData", JSON.stringify(data));
    };
  
    let form_url = "";
  
    const populateWizard = () => {
      
      if (localStorage.key("formData")) {
        
        const savedData = JSON.parse(localStorage.getItem("formData"));
        
        if (setSessionInRequest(savedData) == true) {
          
          const message = "wizard has been continued from last saved location";
          Swal.fire({
            title: "Wizard Loaded",
            text: message,
            confirmButtonText: "Okay Got It!",
          });
          //remove key after form loaded
          localStorage.removeItem("formData");
          
          loadWizard(savedData["wizard_data"], true);
        }
        window.location.href = newWizardUrl;
      }
    };
  
    $("#save_wizard_form").click(() => {
      
      saveAsDraft();
      
    });
  }