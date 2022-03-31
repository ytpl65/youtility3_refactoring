from apps.peoples.models import BaseModel
from apps.tenants.models import TenantAwareModel
from django.db import models
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.gis.db.models import LineStringField, PointField, PolygonField
from django.utils.translation import gettext_lazy as _

# Create your models here.


def peventlog_json():
    return {'fr_threshold': None, 'fr_score': None,
            'fr_timestamp': None, 'fr_service_resp': None, 'other_location': ""}

############## PeopleEventlog Table ###############


class PeopleEventlog(BaseModel, TenantAwareModel):

    
    class TransportMode(models.TextChoices):
        BICYCLE    = ('BICYCLE', 'Bicycle')
        MOTORCYCLE = ('MOTORCYCLE', 'MotorCycle')
        RICKSHAW   = ('RICKSHAW', 'Rickshaw')
        BUS        = ('BUS', 'Bus')
        TRAIN      = ('TRAIN', 'Train')
        FLITE      = ('FLITE', 'Flite')
        BOAT       = ('BOAT', 'Boat or Ship')
    

    people          = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.RESTRICT, verbose_name='People')
    client          = models.ForeignKey("onboarding.Bt",  null=True, blank=True, on_delete=models.RESTRICT, related_name='clients')
    bu              = models.ForeignKey("onboarding.Bt",  null=True, blank=True, on_delete=models.RESTRICT, related_name='bus')
    shift           = models.ForeignKey('onboarding.Shift', null=True, blank=True, on_delete=models.RESTRICT)
    verifiedby      = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.RESTRICT, related_name='verifiedpeoples', verbose_name='Verified By')
    geofence        = models.ForeignKey('onboarding.GeofenceMaster', null=True, blank=True, on_delete=models.RESTRICT)
    peventtype      = models.ForeignKey('onboarding.TypeAssist', null=True, blank=True, on_delete=models.RESTRICT)
    transportmodes  = models.TextField(max_length=500, null=True, blank=True)
    punchintime     = models.DateTimeField(null=True, blank=True, auto_now_add=True, editable=True)
    punchouttime    = models.DateTimeField(null=True, blank=True, auto_now = True)
    datefor         = models.DateField(_("Date"), null=True)
    distance        = models.IntegerField(_("Distance"), null=True, blank=True)
    duration        = models.IntegerField(_("Duration"), null=True, blank=True)
    expamt          = models.FloatField(_("exampt"), default=0.0  ,null=True, blank=True)
    duration        = models.IntegerField(_("duration"), null=True, blank=True)
    accuracy        = models.IntegerField(_("accuracy"), null=True, blank=True)
    deviceid        = models.CharField(_("deviceid"), max_length=50, null=True, blank=True)
    startlocation   = PointField(_("GPS-In"), null=True, geography=True, srid=4326)
    endlocation     = PointField(_("GPS-Out"), null=True, geography=True, blank=True, srid=4326)
    journeypath     = LineStringField(geography=True, null=True)
    remarks         = models.CharField(_("remarks"), null=True, max_length=500, blank=True)
    facerecognition = models.BooleanField(_("Enable Face-Recognition"), default=True)
    peventlogextras = models.JSONField(_("peventlogextras"), encoder=DjangoJSONEncoder, default=peventlog_json)

    class Meta(BaseModel.Meta):
        db_table = 'peopleeventlog'

#temporary table
class Tracking(models.Model):
    deviceid      = models.CharField(max_length=40)
    gpslocation   = PointField(geography=True, srid=4326)
    reference     = models.IntegerField()
    recieveddate  = models.DateTimeField(editable=True, null=True)
    people        = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.RESTRICT, verbose_name='People')
    transportmode = models.CharField(max_length=55)
    amount        = models.FloatField(default=0.0)
    identifier    = models.ForeignKey('onboarding.TypeAssist', null=True, blank=True, on_delete=models.RESTRICT) 
    
    class Meta:
        db_table = 'tracking'
    
class TestGeo(models.Model):
    code = models.CharField(max_length=15)
    poly = PolygonField(geography=True, null=True)
    point = PointField(geography=True, null=True)
    line = LineStringField(geography=True, null=True)
    