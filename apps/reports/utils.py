from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from io import BytesIO
from django.template.loader import render_to_string
import pandas as pd
from django.http import HttpResponse
from apps.activity.models import Attachment
from django.conf import settings
from apps.onboarding.models import Bt
from django.shortcuts import render




class BaseReportsExport(object):
    '''
    A class which contains logic for Report Exports
    irrespective of report design and type. 
    '''
    def __init__(self, filename, client_id, design_file=None, request=None, context=None,
                 data=None, additional_content=None,
                 returnfile=False,  formdata=None):       
        self.design_file = design_file
        self.request = request
        self.context = context
        self.formdata = formdata
        self.data = data
        self.client_id = client_id
        self.additional_content=additional_content
        self.filename = filename
        self.returnfile = returnfile
    
    
    def get_pdf_output(self):
        html_string = render_to_string(self.design_file, context=self.context, request=self.request)
        html = HTML(string=html_string)
        css = CSS(filename='frontend/static/assets/css/local/reports.css')
        font_config = FontConfiguration()
        pdf_output = html.write_pdf(stylesheets=[css], font_config=font_config)
        if self.returnfile: return pdf_output
        response = HttpResponse(
            pdf_output, content_type='application/pdf'
        )
        response['Content-Disposition'] = f'filename="{self.filename}.pdf"'
        return response
    
    
    def get_excel_output(self):
        df = pd.DataFrame(list(self.data))
        
        # Create a Pandas Excel writer using XlsxWriter as the engine and BytesIO as file-like object
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Sheet1', startrow=2, header=True)
        
        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        
        # Autofit the columns to fit the data
        for i, width in enumerate(self.get_col_widths(df)):
            worksheet.set_column(i, i, width)
            
        # Define the format for the merged cell
        merge_format = workbook.add_format({
            'bg_color': '#c1c1c1',
            'bold': True,
        })
        
        worksheet.merge_range("A1:E1", self.additional_content, merge_format)
        
        # Close the Pandas Excel writer and output the Excel file
        writer.save()

        # Rewind the buffer
        output.seek(0)
        return output
    
    
    def get_xls_output(self):
        output = self.get_excel_output()
        if self.returnfile: return output
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{self.filename}.xls"'
    
    
    def get_xlsx_output(self):
        output = self.get_excel_output()
        if self.returnfile: return output
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{self.filename}.xlsx"'
        
    
    def get_csv_output(self):
        df = pd.DataFrame(data=list(self.data))
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        if self.returnfile: return output
        response = HttpResponse(output, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={self.filename}.csv'
        return response
    
    def get_html_output(self):
        ic(self.context)
        html_output = render_to_string(self.design_file, context=self.context, request=self.request)
        if self.returnfile: return html_output
        response = render(self.request, self.design_file, self.context)
        return response
    
    def get_json_output(self):
        df = pd.DataFrame(list(self.data))
        output = BytesIO()
        df.to_json(output, orient='records')
        output.seek(0)
        if self.returnfile: return output
        # Create the HttpResponse object with JSON content type and file name
        response = HttpResponse(output, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{self.filename}.json"'
        return response
    
    def get_client_logo(self):
        bt = Bt.objects.get(id=self.client_id)
        uuid, buname = bt.uuid, bt.buname
        att = Attachment.objects.get_att_given_owner(uuid)
        if att:
            clientlogo_filepath = settings.MEDIA_URL + att[0]['filepath'] + att[0]['filename']
        else:
            clientlogo_filepath = buname
        return clientlogo_filepath
    
    
    def get_col_widths(self, dataframe):
        """
        Get the maximum width of each column in a Pandas DataFrame.
        """
        return [max([len(str(s)) for s in dataframe[col].values] + [len(col)]) for col in dataframe.columns]


class ReportEssentials(object):
    '''
    Report Essentials are the details
    requred by ReportExport functioning.
    '''
    
    # report_names
    TaskSummary = 'TaskSummary'
    TourSummary = 'TourSummary'
    ListOfTasks = 'ListOfTasks'
    ListOfTickets = 'ListOfTickets'
    PPMSummary = 'PPMSummary'
    
    def __init__(self, formdata,  request=None, session=None):
        self.report_name = formdata.get('report_name')
        self.request = request
        self.session = dict(request.session) if request else session
        self.form_data = formdata

    def get_report_export_object(self):
        # Report Design Files
        from apps.reports.report_designs.task_summary import TaskSummaryReport
        
        return {
            self.TaskSummary: TaskSummaryReport
        }.get(self.report_name)
    
        
