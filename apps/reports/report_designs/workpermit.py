from apps.reports.utils import BaseReportsExport
from apps.core.utils import runrawsql, get_timezone
from apps.core.report_queries import get_query
from apps.onboarding.models import Bt
from apps.work_order_management.models import Wom
from django.conf import settings
from django.http.response import JsonResponse
import logging
logger = logging.getLogger('__main__')
log = logger


class WorkPermit(BaseReportsExport):
    
    def __init__(self, filename, client_id, request=None, context=None, data=None, additional_content=None, returnfile=False, formdata=None):
        super().__init__(filename, client_id, design_file=self.design_file, request=request, context=context, data=data, additional_content=additional_content, returnfile=returnfile, formdata=formdata)

    def set_context_data(self):
        '''
        context data is the info that is passed in templates
        used for pdf/html reports
        '''
        id = self.formdata.get('id')
        wp_info, wp_sections, rwp_section, sitename = Wom.objects.wp_data_for_report(id)
        approvers = WorkPermit.__get_approvers_name(id)
        verifiers = WorkPermit.__get_verifiers_name(id)
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
            'approvers':approvers,
            'verifiers':verifiers
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
    
    def __get_approvers_name(id):
        obj = Wom.objects.filter(id=id).values('other_data').first()
        approver = ''
        for record in obj['other_data']['wp_approvers']:
            if record['status'] == 'APPROVED':
                approver+= record['name'] + ', '
        return approver

    def __get_verifiers_name(id):
        obj = Wom.objects.filter(id=id).values('other_data').first()
        verifier = ''
        for record in obj['other_data']['wp_verifiers']:
            if record['status'] == 'APPROVED':
                verifier+= record['name'] + ', '
        return verifier



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

class ConfinedSpaceWorkPermit(WorkPermit):
    report_title = 'CONFINED SPACE WORK PERMIT'
    design_file = "reports/pdf_reports/confined_space_workpermit.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'ConfinedSpaceWorkPermit'

class ElectricalWorkPermit(WorkPermit):
    report_title = 'ELECTRICAL WORK PERMIT'
    design_file = "reports/pdf_reports/electrical_workpermit.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'ElectricalWorkPermit'

class EntryRequest(WorkPermit):
    report_title = 'Entry Request'
    design_file = "reports/pdf_reports/entry_request.html"
    ytpl_applogo =  'frontend/static/assets/media/images/logo.png'
    report_name = 'EntryRequest'

class GeneralWorkPermit(BaseReportsExport):
    report_title = 'GENERAL PERMIT TO WORK AND ENTRY'
    design_file  = "reports/pdf_reports/general_permit_to_work_and_entry.html"
    report_name  = "GeneralPermitToWorkAndEntry"
    
    def __init__(self, filename, client_id=None, request=None, context=None, data=None, additional_content=None, returnfile=False, formdata=None):
        super().__init__(filename, client_id=client_id, design_file=self.design_file, request=request, context=context, data=data, additional_content=additional_content, returnfile=returnfile, formdata=formdata)

    
    def set_context_data(self):
        log.info("Form Data: %s",self.formdata)
        approval_status = self.formdata.get('workpermit','')
        log.info("Approval Status: %s",approval_status)
        wp_answers_data,permit_no = Wom.objects.wp_data_for_report(self.formdata.get('id'),approval_status)
        name_of_persons_involved = wp_answers_data['name_of_persons_involved'].split(',')
        name_of_persons_involved = [ x for x in name_of_persons_involved if len(x)!=0 ]
        name_of_supervisor = wp_answers_data['name_of_supervisor'].split(',')
        name_of_supervisor = [ x for x in name_of_supervisor if len(x)!=0 ]
        sitename = self.formdata.get('bu__buname','')
        self.context = {
            'permit_authorized_by':wp_answers_data['permit_authorized_by'],
            'permit_initiated_by':wp_answers_data['permit_initiated_by'],
            'name_of_supervisor':name_of_supervisor,
            'name_of_persons_involved':name_of_persons_involved,
            'other_control_measures':wp_answers_data['other_control_measures'],
            'debris_cleared':wp_answers_data['debris_cleared'],
            'new_section_details_two':wp_answers_data['new_section_details_two'],
            'new_section_details_three':wp_answers_data['new_section_details_three'],
            'workmen_fitness':wp_answers_data['workmen_fitness'],
            'area_building':wp_answers_data['area_building'],
            'location':wp_answers_data['location'],
            'job_description':wp_answers_data['job_description'],
            'employees_contractors':wp_answers_data['employees_contractors'],
            'workmen_fitness':wp_answers_data['workmen_fitness'],
            'area_building':wp_answers_data['area_building'],
            'department':wp_answers_data['department'],
            'workpermit':wp_answers_data['workpermit'],
            'permit_valid_from':wp_answers_data['permit_valid_from'],
            'permit_valid_upto':wp_answers_data['permit_valid_upto'],
            'permit_no':permit_no,
            'sitename':sitename,
            'permit_returned_at':wp_answers_data['permit_returned_at'],
            'work_checked_at':wp_answers_data['work_checked_at'],
            'name_of_requester':wp_answers_data['name_of_requester'],

        }
        log.info("Context Data: %s",self.context)
        self.permit_no = permit_no    
    def set_args_required_for_query(self):
        self.args = [
            get_timezone(self.formdata['ctzoffset']),
            self.formdata['site'],
            self.formdata['fromdate'].strftime('%d/%m/%Y'),
            self.formdata['uptodate'].strftime('%d/%m/%Y'),
            ]

    def execute(self):  
        self.set_context_data()
        return self.get_pdf_output()



    
