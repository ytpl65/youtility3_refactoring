from apps.peoples.models import BaseModel
from apps.tenants.models import TenantAwareModel
from django.db import models
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext_lazy as _

# Create your models here.


def peventlog_json():
    return {'fr_threshold': None, 'fr_score': None,
            'fr_timestamp': None, 'fr_service_resp': None, 'other_location': ""}

############## PeopleEventlog Table ###############


class PeopleEventlog(BaseModel, TenantAwareModel):
    class EventType(models.TextChoices):
        MARK       = ('MARK', 'Mark')
        SELF       = ('SELF', 'Self')
        SITE       = ('SITE', 'Site')
        CONVEYANCE = ('CONVEYANCE', 'Conveyance')
    
    class TransportMode(models.TextChoices):
        BICYCLE    = ('BICYCLE', 'Bicycle')
        MOTORCYCLE = ('MOTORCYCLE', 'MotorCycle')
        RICKSHAW   = ('RICKSHAW', 'Rickshaw')
        BUS        = ('BUS', 'Bus')
        TRAIN      = ('TRAIN', 'Train')
        FLITE      = ('FLITE', 'Flite')
        BOAT       = ('BOAT', 'Boat or Ship')
    

    peopleid        = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.RESTRICT, verbose_name='People')
    clientid        = models.ForeignKey("onboarding.Bt",  null=True, blank=True, on_delete=models.RESTRICT, related_name='clientids')
    buid            = models.ForeignKey("onboarding.Bt",  null=True, blank=True, on_delete=models.RESTRICT, related_name='buids')
    shift           = models.ForeignKey('onboarding.Shift', null=True, blank=True, on_delete=models.RESTRICT)
    verifiedby      = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,       on_delete=models.RESTRICT, related_name='verifiedpeoples', verbose_name='Verified By')
    gfid            = models.ForeignKey('onboarding.GeofenceMaster', null=True, blank=True, on_delete=models.RESTRICT)
    peventtype      = models.CharField(choices=EventType.choices, max_length=100, verbose_name='Attendance Type', null=True)
    transportmode   = models.CharField(choices=TransportMode.choices, max_length=100, verbose_name='Transport Mode', null=True)
    punch_intime    = models.DateTimeField(null=True)
    punch_outtime   = models.DateTimeField(null=True)
    datefor         = models.DateField(_("Date"), null=True)
    distance        = models.IntegerField(_("Distance"), null=True, blank=True)
    duration        = models.IntegerField(_("Duration"), null=True, blank=True)
    expamt          = models.IntegerField(_("exampt"), null=True, blank=True)
    duration        = models.IntegerField(_("duration"), null=True, blank=True)
    accuracy        = models.IntegerField(_("accuracy"), null=True, blank=True)
    deviceid        = models.CharField(_("deviceid"), max_length=50, null=True, blank=True)
    gpslocation_in  = models.CharField(_("GPS-In"), max_length=50, default='0.0,0.0')
    gpslocation_out = models.CharField(_("GPS-Out"), max_length=50, default='0.0,0.0')
    remarks         = models.CharField(_("remarks"), null=True, max_length=500, blank=True)
    facerecognition = models.BooleanField(_("Enable Face-Recognition"), default=True)
    peventlogextras = models.JSONField(_("peventlogextras"), encoder=DjangoJSONEncoder, default=peventlog_json)

    class Meta(BaseModel.Meta):
        db_table = 'people_eventlog'
