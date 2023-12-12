from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from io import BytesIO
from django.template.loader import render_to_string
from django_weasyprint.views import WeasyTemplateResponseMixin
import pandas as pd
from django.http import HttpResponse
from apps.activity.models import Attachment
from django.conf import settings
from django.shortcuts import render
from apps.onboarding.models import Bt
from django.shortcuts import render
from .forms import ReportForm
import logging
from decimal import Decimal
log = logging.getLogger('__main__')



class BaseReportsExport(WeasyTemplateResponseMixin):
    '''
    A class which contains logic for Report Exports
    irrespective of report design and type. 
    '''
    
    pdf_stylesheets = [
        settings.STATIC_ROOT + 'assets/css/local/reports.css'
    ]
    no_data_error = "No Data"
    report_export_form = ReportForm
    
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
        log.info(f"pdf is executing {self.request.build_absolute_uri()}")
        html_string = render_to_string(self.design_file, context=self.context, request=self.request)
        html = HTML(string=html_string, base_url=self.request.build_absolute_uri())
        css = CSS(filename='frontend/static/assets/css/local/reports.css')
        font_config = FontConfiguration()
        pdf_output = html.write_pdf(stylesheets=[css], font_config=font_config, presentational_hints=True)
        if self.returnfile: return pdf_output
        response = HttpResponse(
            pdf_output, content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{self.filename}.pdf"'
        return response
    
    def excel_layout(self, worksheet, workbook, df, writer, output):
        '''
        This method is get overriden in inherited/child class
        '''
        log.info("designing the layout...")
    
    
    def get_excel_output(self):
        worksheet, workbook, df, writer, output = self.set_data_excel()
        output = self.excel_layout(workbook=workbook, worksheet=worksheet,
                          df=df, writer=writer, output=output)
        return output
    
    
    def get_xls_output(self):
        log.info("xls is executing")
        output = self.get_excel_output()
        if self.returnfile: return output
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{self.filename}.xls"'
        return response
    
    
    def get_xlsx_output(self):
        log.info("xlsx is executing")
        output = self.get_excel_output()
        if self.returnfile: return output
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{self.filename}.xlsx"'
        return response
        
    
    def get_csv_output(self):
        log.info("csv is executing")
        df = pd.DataFrame(data=list(self.data))
        df = self.excel_columns(df)
        output = BytesIO()
        df.to_csv(output, index=False, date_format='%Y-%m-%d %H:%M:%S')
        output.seek(0)
        if self.returnfile: return output
        response = HttpResponse(output, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename={self.filename}.csv'
        return response
    
    def get_html_output(self):
        log.info("html is executing")
        html_output = render_to_string(self.design_file, context=self.context, request=self.request)
        if self.returnfile: return html_output
        response = render(self.request, self.design_file, self.context)
        return response
    
    def get_json_output(self):
        log.info("json is executing")
        df = pd.DataFrame(list(self.data))
        output = BytesIO()
        df.to_json(output, orient='records', date_format='iso')
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

    
    def excel_columns(self, df):
        '''
        Override this method in inherited class
        '''
        pass
    
    
    def set_data_excel(self):
        df = pd.DataFrame(list(self.data))
        # Convert the Decimal objects to floats using the float() function
        df = df.applymap(lambda x: float(x) if isinstance(x, Decimal) else x)
        df = self.excel_columns(df)
        # Create a Pandas Excel writer using XlsxWriter as the engine and BytesIO as file-like object
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter',  datetime_format="mmm d yyyy hh:mm:ss", date_format="mmm dd yyyy",)
        df.to_excel(writer, index=False, sheet_name='Sheet1', startrow=2, header=False)
        
        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        return worksheet, workbook, df, writer, output
    
    def write_custom_mergerange(self, worksheet, workbook, custom_merge_ranges):
        for merge_item in custom_merge_ranges:
            format = workbook.add_format = merge_item['format']
            range = merge_item['range']
            content = merge_item.get('content')
            worksheet.merge_range(range, content, format)
        return worksheet, workbook
                
            

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
    SiteReport = 'SiteReport'
    ListOfTours = 'ListOfTours'
    WorkOrderList = 'WorkOrderList'
    SiteVisitReport = 'SiteVisitReport'
    PeopleQR = 'PeopleQR'
    AssetQR = 'AssetQR'
    CheckpointQR = 'CheckpointQR'
    AssetwiseTaskStatus = 'AssetwiseTaskStatus'
    DetailedTourSummary = 'DetailedTourSummary'

    
    def __init__(self, report_name):
        self.report_name = report_name

    def get_report_export_object(self):
        # Report Design Files
        from apps.reports.report_designs.task_summary import TaskSummaryReport
        from apps.reports.report_designs.tour_summary import TourSummaryReport
        from apps.reports.report_designs.ppm_summary import PPMSummaryReport
        from apps.reports.report_designs.sitereport import SiteReportFormat
        from apps.reports.report_designs.list_of_task import ListofTaskReport
        from apps.reports.report_designs.list_of_tickets import ListofTicketReport
        from apps.reports.report_designs.list_of_tours import ListofTourReport
        from apps.reports.report_designs.work_order_list import WorkOrderList
        from apps.reports.report_designs.site_visit_report import SiteVisitReport
        from apps.reports.report_designs.qrcode_report import PeopleQR
        from apps.reports.report_designs.qrcode_report import AssetQR
        from apps.reports.report_designs.qrcode_report import CheckpointQR
        from apps.reports.report_designs.assetwise_task_status import AssetwiseTaskStatus
        from apps.reports.report_designs.detailed_tour_summary import DetailedTourSummaryReport
        return {
            self.TaskSummary: TaskSummaryReport,
            self.TourSummary:TourSummaryReport,
            self.PPMSummary:PPMSummaryReport,
            self.SiteReport:SiteReportFormat,
            self.ListOfTasks:ListofTaskReport,
            self.ListOfTickets:ListofTicketReport,
            self.ListOfTours:ListofTourReport,
            self.WorkOrderList:WorkOrderList,
            self.SiteVisitReport:SiteVisitReport,
            self.PeopleQR:PeopleQR,
            self.AssetQR:AssetQR,
            self.CheckpointQR:CheckpointQR,
            self.AssetwiseTaskStatus:AssetwiseTaskStatus,
            self.DetailedTourSummary:DetailedTourSummaryReport
        }.get(self.report_name)
    
    @property
    def behaviour_json(self):
        report = self.get_report_export_object()
        return {
            'unsupported_formats': report.unsupported_formats,
            'fields':report.fields
        }
    
        
