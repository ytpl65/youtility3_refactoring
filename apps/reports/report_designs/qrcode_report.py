from apps.reports.utils import BaseReportsExport
from apps.core.utils import runrawsql, get_timezone
from apps.core.report_queries import get_query
import qrcode
from qrcode.image.svg import SvgImage
from tempfile import NamedTemporaryFile
import os, io, base64
from django.db.models import F
import shutil
from django.conf import settings

# Folder for temporary files
TEMP_FOLDER = 'temp_qr_codes'
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
            'data' : self.data,
            'qr_size':self.formdata.get('qrsize')
        }
    
    def set_data(self):
        '''
        Should be overriden in child class
        '''
        pass
    
    def generate_qr_code_images(self, data_list, size=1):
        def generate_qr_code_image(data):
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=size,
                border=4
            )
            qr.add_data(data)
            qr.make(fit=True)
            qr_code_img = qr.make_image(image_factory=SvgImage, fill_color="black", back_color="white")

            # Convert the SVG image to bytes
            img_bytes = io.BytesIO()
            qr_code_img.save(img_bytes)
            img_bytes.seek(0)

            # Encode image to base64 string
            img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
            return f"data:image/svg+xml;base64,{img_base64}"

        qr_code_images = [generate_qr_code_image(data) for data in data_list]
        return qr_code_images

    def delete_temp_folder(self):
        if os.path.exists(TEMP_FOLDER):
            shutil.rmtree(TEMP_FOLDER)
    
    def execute(self):
        self.set_data()
        self.set_context_data()
        return self.get_pdf_output()
        #return self.get_html_output()
        
    

class PeopleQR(QRCodeBaseReport):
    report_name = 'PeopleQR'
    
    def set_data(self):
        from apps.peoples.models import People
        site = self.formdata.get('site')
        peoples = self.formdata.get('mult_people')
        self.size = self.formdata.get('qrsize')
        filters = {'client_id':self.client_id}
        if site:
            filters.update({'bu_id':site})
        else:
            filters.update({'id__in':peoples.split(',')})
        qset = People.objects.annotate(name = F('peoplename'),code = F('peoplecode')).filter(**filters).distinct().values("code", 'name').order_by('code')
        self.data = qset.values_list('code', flat=True)
        self.peoplenames_and_codes = qset
    
    def set_context_data(self):
        super().set_context_data()
        qr_code_images = self.generate_qr_code_images(self.data, size=self.size)
        self.context.update({
            'qr_type':'peoples',
            'qr_file_paths': qr_code_images,
            'size':self.size,
            'names_and_codes':self.peoplenames_and_codes})
    
class AssetQR(QRCodeBaseReport):
    report_name = 'AssetQR'
    
    def set_data(self):
        from apps.activity.models import Asset
        site = self.formdata.get('site')
        assettype = self.formdata.get('assettype')
        assetcategory = self.formdata.get('assetcategory')
        self.size = self.formdata.get('qrsize')
        filters = {'client_id':self.client_id}
        if site:
            filters.update({'bu_id':site})
        if assettype:
            filters.update({'type':assettype})
        if assetcategory:
            filters.update({'category':assetcategory})
        qset = Asset.objects.annotate(
            code = F('assetcode'),name = F('assetname')
        ).filter(**filters, identifier = 'ASSET').distinct().values("code","name").order_by('code')
        self.data = qset.values_list('code', flat=True)
        self.assetcodes_and_names = qset
    
    def set_context_data(self):
        super().set_context_data()
        qr_code_images = self.generate_qr_code_images(self.data, size=self.size)
        self.context.update({
            'qr_type':'assets',
            'qr_file_paths': qr_code_images,
            'size':self.size,
            'names_and_codes':self.assetcodes_and_names})    
        

class CheckpointQR(QRCodeBaseReport):
    report_name = 'CheckpointQR'

    def set_data(self):
        from apps.activity.models import Asset
        site = self.formdata.get('site')
        checkpoint_type = self.formdata.get('checkpoint_type')
        self.size = self.formdata.get('qrsize')
        filters = {'client_id':self.client_id}
        if site:
            filters.update({'bu_id':site})
        if checkpoint_type:
            filters.update({'type':checkpoint_type})
        qset = Asset.objects.annotate(
            code=F('assetcode'), name=F('assetname')
                ).filter(**filters, identifier='CHECKPOINT').distinct().values("code", "name"
                                                                               ).order_by('code')
        self.data = qset.values_list('code', flat=True)
        self.checkpointcodes_and_names = qset

    def set_context_data(self):
        super().set_context_data()
        qr_code_images = self.generate_qr_code_images(self.data, size=self.size)
        self.context.update({
            'qr_type':'checkpoint',
            'qr_file_paths': qr_code_images,
            'size':self.size,
            'names_and_codes':self.checkpointcodes_and_names})  

 
