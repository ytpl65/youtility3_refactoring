    var qsetbng_form_validator = FormValidation.formValidation(
        document.getElementById("qsetbng_form"),
        {
            fields:{
                'min':{
                    validators:{
                        notEmpty:{
                            message:"This field is required"
                        }
                    }
                },
                'max':{
                    validators:{
                        notEmpty:{
                            message:"This field is required"
                        },
                        callback:{
                            message:"Max value should be greater than Min value",
                            callback:function(input){
                                if(input.value.length>0){
                                    var max = parseFloat(input.value)
                                    var min = parseFloat(document.querySelector("#id_min").value)
                                    return max > min
                                }
                            },
                            
                        }
                    }
                },
                'alertbelow':{
                    validators:{
                        callback:{
                            callback:function(input){
                                var alertbelow = parseFloat(input.value)
                                var min        = parseFloat(document.querySelector("#id_min").value)
                                var max        = parseFloat(document.querySelector("#id_max").value)
                                var alertabove = parseFloat(document.querySelector("#id_alertabove").value)
                                if(alertbelow < min){
                                    return {valid:false, message:"Alert below should be greater than Min Value"}
                                }if(alertbelow > max){
                                    return {valid:false, message:"Alert below should be less than Max Value"}
                                }if(alertbelow > alertabove){
                                    return {valid:false, message:"Alert below should be less than Alertabove"}
                                }
                                return {valid:true, message:""}
                            },
                        }
                    }
                },
                'alertabove':{
                    validators:{
                        callback:{
                            callback:function(input){
                                var alertabove = parseFloat(input.value)
                                var max        = parseFloat(document.querySelector("#id_max").value)
                                var alertbelow = parseFloat(document.querySelector("#id_alertbelow").value)
                                var min        = parseFloat(document.querySelector("#id_min").value)
                                console.log(`min ${min} max ${max}, alertbelow ${alertbelow}, alertabove ${alertabove}`)
                                if(alertabove > max){
                                    //console.log("should return error")
                                    return {valid: false, message: "Alertabove should be smaller than Max value"}
                                }if(alertabove < min){
                                    return {valid: false, message: "Alertabove should be greater than Min value"}
                                }if(alertabove < alertbelow){
                                    //console.log("should return error")
                                    return {valid:false, message:"Alertabove should be grater than Alertbelow"}
                                }
                                return {valid:true, message:""}
                                
    
                            },
                        }
    
                    }
                },
    
            },
            plugins: {
                trigger: new FormValidation.plugins.Trigger(),
                bootstrap: new FormValidation.plugins.Bootstrap5({
                    rowSelector: '.fv-row',
                    eleInvalidClass: 'is-invalid',
                    eleValidClass: '',
                    eleValidatedClass:'was-validated'
                })
            }
        }
    )



