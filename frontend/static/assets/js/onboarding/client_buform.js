$(document).ready(function(){
    //add form attribute to fields which are outside form element
    $("#id_webcapability").attr("form", "id_clientform")
    $("#id_reportcapability").attr("form", "id_clientform")
    $("#id_portletcapability").attr("form", "id_clientform")
    $("#id_mobilecapability").attr("form", "id_clientform")

    // submit the popup-butype-taform for validation and saving in db.
    $('#pop_butype_form').on('submit', sumit_popup_form(
        {'url':"{{ url('onboarding:ta_popup') }}",
        'form':"#pop_butype_form",
        'field':"#id_butype",
        'modal':"#butype_popup"}
    ))
    
})