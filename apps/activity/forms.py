################## Activity app - Forms ###################
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
import apps.activity.models as am
import apps.peoples.models as pm
import apps.onboarding.models as om
from apps.core import utils
import apps.activity.utils as ac_utils
import django_select2.forms as s2forms
from django.contrib.gis.geos import GEOSGeometry
import json
import re
from django.http import QueryDict
from datetime import datetime


