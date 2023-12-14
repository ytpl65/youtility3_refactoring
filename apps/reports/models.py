from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext_lazy as _
from apps.peoples.models import BaseModel
from django.contrib.postgres.fields import ArrayField

def now():
    return timezone.now().replace(microsecond = 0)

# Create your models here.
class ReportHistory(models.Model):
    class ExportType(models.TextChoices):
        D = ('DOWNLOAD', 'Download')
        E = ('EMAIL', 'Email')
    
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_(""), on_delete=models.RESTRICT)
    datetime    = models.DateTimeField(default= now)
    export_type = models.CharField(max_length=55, default=ExportType.D.value)
    report_name = models.CharField(max_length=100)
    params      = models.JSONField(encoder=DjangoJSONEncoder, null=True)
    format      = models.CharField(max_length=55, default='pdf')
    bu          = models.ForeignKey('onboarding.Bt', null=True, on_delete=models.RESTRICT)
    ctzoffset   = models.IntegerField(_("TimeZone"), default=-1)
    cc_mails    = models.TextField(max_length=250, null=True)
    to_mails    = models.TextField(max_length=250, null=True)
    email_body  = models.TextField(max_length=500, null=True)
    traceback = models.CharField(max_length=1000, null=True)
    
    class Meta:
        db_table = 'report_history'
    
    def __str__(self):
        return f'User: {self.user.peoplename} Report: {self.report_name}'
    


def report_params_json():
    return {'report_params':{}}

class ScheduleReport(BaseModel):
    REPORT_TEMPLATES = [
        ('', 'Select Report'),
        ('TaskSummary', 'Task Summary'),
        ('TourSummary', 'Tour Summary'),
        ('ListOfTasks', 'List of Tasks'),
        ('ListOfTours', 'List of Internal Tours'),
        ('PPMSummary', 'PPM Summary'),
        ('ListOfTickets', 'List of Tickets'),
        ('WorkOrderList', 'Work Order List'),
        ('SiteReport', 'Site Report'),
        ('PeopleQR', 'People-QR'),
        ('AssetQR', 'Asset-QR'),
        ('CheckpointQR', 'Checkpoint-QR'),
        ('AssetwiseTaskStatus','Assetwise Task Status'),
        ('DetailedTourSummary','Detailed Tour Summary')
    ]
    report_type = models.CharField(_("Report Type"), max_length=50, choices=REPORT_TEMPLATES)
    report_name = models.CharField(_("Report Name"), max_length=55)
    cron = models.CharField(_("Scheduler"), max_length=50, default='* * * * *')
    report_sendtime = models.TimeField(_("Send Time"), auto_now=False, auto_now_add=False)
    cc      = ArrayField(models.CharField(max_length = 90, blank = True, null=True), null = True, blank = True, verbose_name= _("Email-CC"))
    to_addr = ArrayField(models.CharField(max_length = 90, blank = True, null=True), null = True, blank = True, verbose_name= _("Email=TO"))
    enable = models.BooleanField(_("Enable"), default=True)
    lastgeneratedon = models.DateTimeField(_("Last Generated On"), default=now)
    report_params = models.JSONField(null=True, blank=True, default=report_params_json)
    bu          = models.ForeignKey('onboarding.Bt', null=True, on_delete=models.RESTRICT, related_name='schd_sites')
    client          = models.ForeignKey('onboarding.Bt', null=True, on_delete=models.RESTRICT, related_name='schd_clients')
    