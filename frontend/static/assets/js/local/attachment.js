var attTable;
$(document).ready(() => {
  attTable = $("#tabAttachment").DataTable({
    deferRender: true,
    responsive: true,
    dom: "lrtp",
    columns: [
      { data: "id", targets: 0 },
      { data: "filepath", targets: 1 },
      { data: "filename", targets: 2 },
      { data: "filename", targets: 2 },
    ],
  });
  $("#id_attachment").click(() => {
    $("#popup_attachment").modal("show");
  });
  $("#popup_attachment").on("shown.bs.modal", () => {
    //get attachement data from ajax get
    var data = getAttachmentData(attachmentOwner);

    if (data) {
      attTable.clear();
      attTable.rows.add(data).draw();
    }
  });

  $("#btnuploadattachment").click(function () {
    var uploadfile = $("#attachmentfile").val();
    if (uploadfile.length === 0) {
      $("#nonfield_errors span").html("Please select a file to upload.");
      $("#nonfield_errors").show();
    } else {
      formdata = new FormData();
      formdata.append("oper", "add");
      formdata.append("id", "");
      formdata.append("csrfmiddlewaretoken", csrf);
      formdata.append("img", $("#attachmentfile")[0].files[0]);
      formdata.append("dataSource", "attachment");
      formdata.append("foldertype", folderType);
      formdata.append("isDefault", isDefault);
      formdata.append("ownerid", attachmentOwner);
      formdata.append("attachmenttype", "ATTACHMENT");
      formdata.append("ownername", ownername);
      formdata.append("docnumber", docnumber);
      formdata.append("ctzoffset", $("#id_ctzoffset").val());
      formdata.append("doctype", "None");
      if (formdata) {
        $.ajax({
          url: attachmentUrl,
          type: "POST",
          data: formdata,
          processData: false,
          contentType: false,
          //csrfmiddlewaretoken: '{{ csrf_token }}',
          success: function (data) {
            if (data.rc === 1) {
              $("#nonfield_errors span").html("Upload Failed");
              $("#nonfield_errors").show();
            } else {
            }
          },
        });
      }
    }
  });

  $("#clearattachment").click(function () {
    $("input[type=file]").val("");
  });
});

function getAttachmentData(uuid) {
  fire_ajax_get({
    url: attachmentUrl,
    data: { owner: uuid },
  }).done((data, status, xhr) => {
    if (data) {
      attTable.clear();
      attTable.rows.add(data).draw();
    }
  });
}
