from apps.reports.utils import BaseReportsExport
from apps.core.utils import runrawsql, get_timezone
from django.utils import timezone as dtimezone
from apps.core.report_queries import get_query
from apps.onboarding.models import Bt
from django.conf import settings
import pandas as pd

class DynamicTourDetailReport(BaseReportsExport):
    report_title = "Task Not Completed Report"
    design_file = "reports/pdf_reports/dynamic_tour_details.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'DynamicTourDetails'
    unsupported_formats = ['None']
    fields = ['site*', 'fromdate*', 'uptodate*']
    
    def __init__(self, filename, client_id, request=None, context=None, data=None, additional_content=None, returnfile=False, formdata=None):
        super().__init__(filename, client_id, design_file=self.design_file, request=request, context=context, data=data, additional_content=additional_content, returnfile=returnfile, formdata=formdata)
    
    def get_data(self):
        from django.db.models import Prefetch
        from datetime import datetime, timedelta
        from apps.activity.models import Jobneed
        from django.db.models import Q

        # Your imports here

        # Given values  


        task_data = Jobneed.objects.filter(Q(jobstatus='AUTOCLOSED') | Q(jobstatus='COMPLETED'),
                                       jobstatus = 'AUTOCLOSED').select_related('asset','qset').values(
                                           'jobdesc','jobtype','asset__assetname',
                                           'qset__qsetname','jobstatus','planedatetime'
                                       )
        
        return task_data
    
    
    
    def set_context_data(self):
        '''
        context data is the info that is passed in templates
        used for pdf/html reports
        '''
        sitename = Bt.objects.get(id=self.formdata['site']).buname
        self.set_args_required_for_query()
        self.context = {
            'base_path': settings.BASE_DIR,
            'data' : self.get_data(),
            'report_title': self.report_title,
            'client_logo':self.get_client_logo(),
            'app_logo':self.ytpl_applogo,
            'report_subtitle':f"Site: {sitename}, From: {self.formdata.get('fromdate')} To {self.formdata.get('uptodate')}"
        }
        return len(self.context['data']) > 0
        
    def set_args_required_for_query(self):
        self.args = [
            get_timezone(self.formdata['ctzoffset']),
            self.formdata['site'],
            self.formdata['fromdate'].strftime('%d/%m/%Y'),
            self.formdata['uptodate'].strftime('%d/%m/%Y'),    
            ]
    
    def set_data(self):
        '''
        setting the data which is shown on report
        '''
        self.data = self.get_data()
        return len(self.data) > 0

    def excel_columns(self,df):
        df = df[['Tour/Route','checkpoints','Start Datetime','End Datetime','Status',
                 'Assigned To','Performed By']]
        return df

        
    def set_additional_content(self):
        bt = Bt.objects.filter(id=self.client_id).values('id', 'buname').first()
        self.additional_content = f"Client: {bt['buname']}; Report: {self.report_title}; From: {self.formdata['fromdate']} To: {self.formdata['uptodate']}"

    def excel_layout(self, worksheet, workbook, df, writer, output):
        super().excel_layout(worksheet, workbook, df, writer, output)

        df = df.rename(columns={'Tour/Route':'Tour Name','checkpoints':'Checkpoint Name','Start Datetime': 'Start Datetime','End Datetime':'End Datetime','Status':'Status',
                 'Assigned To':'Assigned To','Performed By':'Performed By'})

        import xlsxwriter
        worksheet.autofit()
        header_format = workbook.add_format({'bold': True, 'bg_color': '#01579B', 'border': 1, 'color': 'white', 'font_size': 10})
        tour_cell_format = workbook.add_format({'bold': True, 'bg_color': '#eff7fc', 'border': 1, 'font_size': 10})
        parent_row_format = workbook.add_format({'bg_color': '#eff7fc', 'border': 1, 'font_size': 10, 'num_format': 'yyyy-mm-dd hh:mm:ss'})
        child_row_format = workbook.add_format({'font_size': 10, 'num_format': 'yyyy-mm-dd hh:mm:ss'})
        count_row_format = workbook.add_format({'border': 1, 'font_size': 10, 'bold': True, 'bg_color': '#eff7fc', 'font_size': 10})
        merge_format = workbook.add_format({ 'bg_color': '#E2F4FF',})

        worksheet.merge_range("B1:H1", self.additional_content, merge_format)

        headers = df
        
        #worksheet.write_row('B2', headers, header_format)

        worksheet.autofit()
        datetime_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})


        row_num = 2
        for tour in self.data:
            worksheet.autofit()
            worksheet.write_row(f'B{row_num}', headers, header_format)
            # Write parent row
            worksheet.merge_range(f'B{row_num +1}:C{row_num +1}', tour["Tour/Route"], tour_cell_format)
            worksheet.write_row(row_num, 3, [tour["Start Datetime"], tour["End Datetime"], tour["Status"], tour["Assigned To"], tour["Performed By"]], parent_row_format)
            row_num += 1

            for cp in tour["checkpoints"]:
                worksheet.autofit()
                worksheet.write(row_num, 2, cp["assetname"], child_row_format)

                if cp["starttime"] is None and cp['endtime'] is None:
                    time_status = ["Not Started", "Not Started", cp["jobstatus"]]
                else:
                    time_status = [cp["starttime"], cp["endtime"], cp["jobstatus"]]

                worksheet.write_row(row_num, 3, time_status, child_row_format)
                row_num += 1

            worksheet.write(row_num, 1, "", count_row_format)
            worksheet.write(row_num, 2, "Checkpoints count", count_row_format)
            worksheet.write(row_num, 3, tour["Count of Checkpoint"], count_row_format)
            worksheet.write(row_num, 4, "Passed Percentage", count_row_format)
            worksheet.write(row_num, 5, tour["Passed Ratio"], count_row_format)
            worksheet.write(row_num, 6, "Missed Percentage", count_row_format)
            worksheet.write(row_num, 7, tour["Missed Ratio"], count_row_format)
            row_num += 1

            worksheet.write(row_num, 1, "", count_row_format)
            worksheet.write(row_num, 2, "", count_row_format)
            worksheet.write(row_num, 3, "", count_row_format)
            worksheet.write(row_num, 4, "Passed Percentage", count_row_format)
            worksheet.write(row_num, 5, tour["Passed Ratio"], count_row_format)
            worksheet.write(row_num, 6, "Missed Percentage", count_row_format)
            worksheet.write(row_num, 7, tour["Missed Ratio"], count_row_format)
            row_num += 1

            row_num += 4
            

        # Close the Pandas Excel writer and output the Excel file
        writer.save()

        # Rewind the buffer
        output.seek(0)
        return output
    
    
    def execute(self):
        export_format = self.formdata.get('format')
        # context needed for pdf, html
        if export_format in ['pdf', 'html']:
            has_data = self.set_context_data()
        else:
            self.set_additional_content()
            has_data = self.set_data()
        
        if not has_data:
            return None
        
        # preview in pdf
        if self.formdata.get('preview') == 'true':
            export_format = 'pdf'
        
        if export_format == 'pdf':
            return self.get_pdf_output()
        elif export_format == 'xls':
            return self.get_xls_output(orm=True)
        elif export_format == 'xlsx':
            return self.get_xlsx_output(orm=True)
        elif export_format == 'csv':
            return self.get_csv_output()
        elif export_format == 'html':
            return self.get_html_output()
        else:
            return self.get_json_output()
        