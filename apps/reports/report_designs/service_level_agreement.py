from apps.reports.utils import BaseReportsExport
from apps.reports.utils import BaseReportsExport
from apps.core.utils import runrawsql, get_timezone
from apps.core.report_queries import get_query
from apps.onboarding.models import Bt
from apps.work_order_management.models import Wom,Vendor
from django.conf import settings
from django.http.response import JsonResponse


import logging
logger = logging.getLogger('__main__')
log = logger


class ServiceLevelAgreement(BaseReportsExport):
    report_title = 'Service Level Agreement'
    design_file = "reports/pdf_reports/service_level_agreement.html"
    report_name = "ServiceLevelAgreement"

    def __init__(self, filename, client_id=None, request=None, context=None, data=None, additional_content=None, returnfile=False, formdata=None):
        super().__init__(filename, client_id=client_id, design_file=self.design_file, request=request, context=context, data=data, additional_content=additional_content, returnfile=returnfile, formdata=formdata)

    
    def set_context_data(self):
        log.info("Form Data: %s", self.formdata)
        sla_answers_data,overall_score,question_ans,all_average_score,remarks = Wom.objects.sla_data_for_report(self.formdata.get('id'))
        vendor_description = ''
        vendor_id = Wom.objects.get(id=self.formdata.get('id')).vendor_id
        vendor_description = Vendor.objects.get(id=vendor_id).description
        self.context = {
                'question_answer': question_ans,
                'sla_answer_data': sla_answers_data,
                'overall_score':overall_score,
                'average_score':all_average_score,
                'remarks':remarks,
                'vendor_description':vendor_description


        }
    
    def execute(self):
        self.set_context_data()
        return self.get_pdf_output()
    


    