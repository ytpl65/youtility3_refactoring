from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from io import BytesIO
from django.template.loader import render_to_string
from django_weasyprint.views import WeasyTemplateResponseMixin
import pandas as pd
from django.http import HttpResponse
from apps.activity.models import Attachment
from django.contrib.staticfiles import finders
from django.conf import settings
from django.shortcuts import render
from apps.onboarding.models import Bt
from django.shortcuts import render
from .forms import ReportForm
from .models import ReportHistory
import logging, json
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
        log.info(f"pdf is executing {settings.HOST}")
        html_string = render_to_string(self.design_file, context=self.context)
        html = HTML(string=html_string, base_url=settings.HOST)
        css_path = finders.find('assets/css/local/reports.css')
        css = CSS(filename=css_path)
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
    
    
    def get_excel_output(self, orm):
        worksheet, workbook, df, writer, output = self.set_data_excel(orm=orm)
        output = self.excel_layout(workbook=workbook, worksheet=worksheet,
                          df=df, writer=writer, output=output)
        return output
    
    
    def get_xls_output(self, orm=False):
        log.info("xls is executing")
        output = self.get_excel_output(orm=orm)
        if self.returnfile: return output
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{self.filename}.xls"'
        return response
    
    
    def get_xlsx_output(self, orm=False):
        log.info("xlsx is executing")
        output = self.get_excel_output(orm=orm)
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
        html_output = render_to_string(self.design_file, context=self.context)
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
        Override this method in inherited classn
        '''
        return df
 
    
    def set_data_excel(self, orm=False):

        df = pd.DataFrame(list(self.data))
        # Convert the Decimal objects to floats using the float() function
        df = df.applymap(lambda x: float(x) if isinstance(x, Decimal) else x)
        df = self.excel_columns(df)
        # Create a Pandas Excel writer using XlsxWriter as the engine and BytesIO as file-like object
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter',  datetime_format='yyyy-mm-dd hh:mm:ss', date_format="mm dd yyyy",)
        workbook = writer.book
        if orm:
            worksheet = workbook.add_worksheet('Sheet1')
        else:
            df.to_excel(writer, index=False, sheet_name='Sheet1', startrow=2, header=False)
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
    TaskSummary                = 'TASKSUMMARY'
    TourSummary                = 'TOURSUMMARY'
    ListOfTasks                = 'LISTOFTASKS'
    ListOfTickets              = 'LISTOFTICKETS'
    PPMSummary                 = 'PPMSUMMARY'
    SiteReport                 = 'SITEREPORT'
    ListOfTours                = 'LISTOFTOURS'
    DynamicTourList            = 'DYNAMICTOURLIST'
    StaticTourList            = 'STATICTOURLIST'
    WorkOrderList              = 'WORKORDERLIST'
    SiteVisitReport            = 'SITEVISITREPORT'
    PeopleQR                   = 'PEOPLEQR'
    AssetQR                    = 'ASSETQR'
    CheckpointQR               = 'CHECKPOINTQR'
    LocationQR                 = 'LOCATIONQR'
    AssetwiseTaskStatus        = 'ASSETWISETASKSTATUS'
    StaticDetailedTourSummary  = 'STATICDETAILEDTOURSUMMARY'
    TourDetails                = 'TourDetails'
    StaticTourDetails          = 'STATICTOURDETAILS'
    DynamicTourDetails         = 'DYNAMICTOURDETAILS'
    DynamicDetailedTourSummary = 'DYNAMICDETAILEDTOURSUMMARY'
    LogSheet                   = 'LOGSHEET'
    RP_SiteVisitReport         = 'RP_SITEVISITREPORT'
    
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
        from apps.reports.report_designs.static_detailed_tour_summary import StaticDetailedTourSummaryReport
        from apps.reports.report_designs.dynamic_tour_details import DynamicTourDetailReport
        from apps.reports.report_designs.static_tour_details import StaticTourDetailReport
        from apps.reports.report_designs.dynamic_detailed_tour_summary import DynamicDetailedTourSummaryReport
        from apps.reports.report_designs.log_sheet import LogSheet
        from apps.reports.report_designs.RP_SiteVisitReport import RP_SITEVISITREPORT
        from apps.reports.report_designs.dynamic_tour_list import DynamicTourList
        from apps.reports.report_designs.static_tour_list import StaticTourList
        from apps.reports.report_designs.qrcode_report import LocationQR
        

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
            self.LocationQR:LocationQR,
            self.AssetwiseTaskStatus:AssetwiseTaskStatus,
            self.StaticDetailedTourSummary:StaticDetailedTourSummaryReport,
            self.DynamicDetailedTourSummary:DynamicDetailedTourSummaryReport,
            self.StaticTourDetails:StaticTourDetailReport,
            self.DynamicTourDetails:DynamicTourDetailReport,
            self.LogSheet:LogSheet,
            self.RP_SiteVisitReport:RP_SITEVISITREPORT,
            self.DynamicTourList:DynamicTourList,
            self.StaticTourList:StaticTourList
        }.get(self.report_name)
    
    @property
    def behaviour_json(self):
        report = self.get_report_export_object()
        return {
            'unsupported_formats': report.unsupported_formats,
            'fields':report.fields
        }
    
        
def create_report_history(
    has_data, params, report_name, export_type, 
    user_id, ctzoffset, bu_id, client_id, traceback=None, cc=None,
    to=None, email_body=None, 
):
    return ReportHistory.objects.create(
        has_data=has_data,
        params=json.dump(params),
        bu_id=bu_id,
        client_id=client_id,
        report_name=report_name,
        user_id=user_id,
        ctzoffset=ctzoffset,
        cc_mails=cc,
        to_mails=to,
        email_body=email_body,
        traceback=traceback,
        export_type=export_type
    )