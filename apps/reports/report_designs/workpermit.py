from apps.reports.utils import BaseReportsExport
from apps.core.utils import runrawsql, get_timezone
from apps.core.report_queries import get_query
from apps.onboarding.models import Bt
from apps.work_order_management.models import Wom
from django.conf import settings
from django.http.response import JsonResponse

class WorkPermit(BaseReportsExport):
    
    def __init__(self, filename, client_id, request=None, context=None, data=None, additional_content=None, returnfile=False, formdata=None):
        super().__init__(filename, client_id, design_file=self.design_file, request=request, context=context, data=data, additional_content=additional_content, returnfile=returnfile, formdata=formdata)

    def set_context_data(self):
        '''
        context data is the info that is passed in templates
        used for pdf/html reports
        '''
        wp_info, wp_sections, rwp_section, sitename = Wom.objects.wp_data_for_report(self.formdata.get('id'))
        self.context = {
            'base_path': settings.BASE_DIR,
            'main_title':sitename,
            'report_subtitle':self.report_title,
            'wp_info' : wp_info,
            'wp_sections': wp_sections,
            'rwp_info':rwp_section,
            'report_title': self.report_title,
            'client_logo':self.get_client_logo(),
            'app_logo':self.ytpl_applogo,
        }


    def set_args_required_for_query(self):
        self.args = [
            get_timezone(self.formdata['ctzoffset']),
            self.formdata['site'],
            self.formdata['fromdate'].strftime('%d/%m/%Y'),
            self.formdata['uptodate'].strftime('%d/%m/%Y'),
            ]

    def execute(self):
        self.set_context_data()
        #return self.get_html_output()
        return self.get_pdf_output()



class ColdWorkPermit(WorkPermit):
    report_title = 'COLD WORK PERMIT'
    design_file = "reports/pdf_reports/cold_workpermit.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'ColdWorkPermit'
    
class HotWorkPermit(WorkPermit):
    report_title = 'HOT WORK PERMIT'
    design_file = "reports/pdf_reports/hot_workpermit.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'HotWorkPermit'

class HeightWorkPermit(WorkPermit):
    report_title = 'HEIGHT WORK PERMIT'
    design_file = "reports/pdf_reports/height_workpermit.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'HeightWorkPermit'

class ConfinedWorkPermit(WorkPermit):
    report_title = 'CONFINED WORK PERMIT'
    design_file = "reports/pdf_reports/confined_workpermit.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'ConfinedWorkPermit'

class ElectricalWorkPermit(WorkPermit):
    report_title = 'ELECTRICAL WORK PERMIT'
    design_file = "reports/pdf_reports/electrical_workpermit.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'ElectricalWorkPermit'

    
