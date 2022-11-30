var attTable;
$(document).ready(() => {
  
  
  $("#id_attachment").click(() => {
    $("#popup_attachment").modal("show");
  });
  
  $("#popup_attachment").on("shown.bs.modal", () => {
    //get attachement data from ajax get
    attTable = $("#tabAttachment").DataTable({
      ajax:{
        url:attachmentUrl + '?action=get_attachments_of_owner',
        data: { owner: attachmentOwner }
      },
      deferRender: true,
      responsive: true,
      dom: "lrtp",
      ordering:false,
      columns: [
        { data: "id", visible: false },
        {title:'SL No.', width:"5%", data:null, defaultContent:null, render:function (data, type, row, meta) { return meta.row  + 1; }},
        { data: "filepath",  width:"5%", title:'File', render:function (data, type, row, meta) { return `<img src="${media_url}${row.filepath.replace('youtility4_media/', "")}/${row.filename}" class="card-img-top" target="_blank" alt="" style="width: 30px;height: 30px;">`; }},
        { data: "filename",  title:'File Name' },
        { data: null, width:"5%", defaultContent:null, title:"Action", render:function(data, type, row, meta ){
          let file = `${media_url}${row.filepath.replace('youtility4_media/', "")}/${row.filename}`
          return `<a href="${file}" target="_blank" class=""><i class="ch4 fas fa-eye"></i></a>&nbsp;&nbsp;&nbsp;&nbsp;<a href="${file}" download="${row.filename}"><i class="ch4 fas fa-save"></i></a>`;
        } },
      ],
    });
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

// function getAttachmentData(uuid) {
//   fire_ajax_get({
//     url: attachmentUrl,
//     data: { owner: uuid },
//   }).done((data, status, xhr) => {
//     if (data) {
//       attTable.clear();
//       attTable.rows.add(data).draw();
//       console.log(attTable.rows().data().toArray())
//       console.log(data, attTable)
//     }
//   });
// }
