from apps.reports.utils import BaseReportsExport
from apps.core.utils import runrawsql, get_timezone
from apps.onboarding.models import Bt
from django.conf import settings



class QRCodeBaseReport(BaseReportsExport):
    design_file = "reports/pdf_reports/qr_code_report.html"
    
    def __init__(self, filename, client_id, request=None, context=None, data=None, additional_content=None, returnfile=False, formdata=None):
        super().__init__(filename, client_id, design_file=self.design_file, request=request, context=context, data=data, additional_content=additional_content, returnfile=returnfile, formdata=formdata)

    def set_context_data(self):
        '''
        context data is the info that is passed in templates
        used for pdf/html reports
        '''        
        self.context = {
            'data' : self.data
        }
    
    def set_data(self):
        '''
        Should be overriden in child class
        '''
        pass
    
    def execute(self):
        self.set_data()
        self.set_context_data()
        return self.get_pdf_output()
    

class PeopleQR(QRCodeBaseReport):
    
    def set_data(self):
        from apps.peoples.models import People
        Pe
