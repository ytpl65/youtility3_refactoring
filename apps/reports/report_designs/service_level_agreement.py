from apps.reports.utils import BaseReportsExport
from apps.reports.utils import BaseReportsExport
from apps.core.utils import runrawsql, get_timezone
from apps.core.report_queries import get_query
from apps.onboarding.models import Bt
from apps.work_order_management.models import Wom,Vendor
from apps.work_order_management.utils import get_last_3_months_sla_reports,get_sla_report_approvers
from django.conf import settings
from django.http.response import JsonResponse
from datetime import datetime
from dateutil.relativedelta import relativedelta
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
        wom_details = Wom.objects.filter(id=self.formdata.get('id')).values_list('vendor_id','bu_id','bu_id__buname','other_data','vendor_id__name','vendor_id__description','workpermit')
        vendor_id = wom_details[0][0]
        site_id = wom_details[0][1]
        sitename = wom_details[0][2]
        sla_report_approvers = get_sla_report_approvers(wom_details[0][3]['wp_approvers'])
        vendor_name = wom_details[0][4]
        vendor_description = wom_details[0][5]
        workpermit_status = wom_details[0][6]
        sla_last_three_month_report = get_last_3_months_sla_reports(vendor_id=vendor_id,bu_id=site_id)
        month = (datetime.now() - relativedelta(months=1)).strftime('%B')
        current_year = datetime.now().year
        month_year = f"{month} {current_year}"
            
        #approvers = 
        self.context = {
                'question_answer': question_ans,
                'sla_answer_data': sla_answers_data,
                'overall_score':overall_score,
                'average_score':all_average_score,
                'remarks':remarks,
                'vendor_name':vendor_name,
                'vendor_description':vendor_description,
                'sitename':sitename,
                'sla_last_three_month_report':sla_last_three_month_report,
                'sla_report_approvers':sla_report_approvers,
                'month_year':month_year,
                'workpermit_status':workpermit_status
        }
    
    def execute(self):
        self.set_context_data()
        return self.get_pdf_output()
    


    