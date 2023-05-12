from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext_lazy as _


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