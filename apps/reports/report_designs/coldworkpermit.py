from apps.reports.utils import BaseReportsExport
from apps.core.utils import runrawsql, get_timezone
from apps.core.report_queries import get_query
from apps.onboarding.models import Bt
from django.conf import settings

class ColdWorkPermit(BaseReportsExport):
    report_title = 'COLD WORK PERMIT'
    design_file = "reports/pdf_reports/cold_workpermit.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'ColdWorkPermit'
    
    def __init__(self, filename, client_id, request=None, context=None, data=None, additional_content=None, returnfile=False, formdata=None):
        super().__init__(filename, client_id, design_file=self.design_file, request=request, context=context, data=data, additional_content=additional_content, returnfile=returnfile, formdata=formdata)

    
    def set_context_data(self):
        '''
        context data is the info that is passed in templates
        used for pdf/html reports
        '''
        sitename = Bt.objects.get(id=self.formdata['site']).buname
        self.set_args_required_for_query()
        self.context = {
            'base_path': settings.BASE_DIR,
            'data' : runrawsql(get_query(self.report_name), args=self.args),
            'report_title': self.report_title,
            'client_logo':self.get_client_logo(),
            'app_logo':self.ytpl_applogo,
            'report_subtitle':f"Site: {sitename}, From: {self.formdata.get('fromdate')} To {self.formdata.get('uptodate')}"
        }


    def set_args_required_for_query(self):
        self.args = [
            get_timezone(self.formdata['ctzoffset']),
            self.formdata['site'],
            self.formdata['fromdate'].strftime('%d/%m/%Y'),
            self.formdata['uptodate'].strftime('%d/%m/%Y'),    
            ]
        
