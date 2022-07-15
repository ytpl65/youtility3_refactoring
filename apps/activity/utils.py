import apps.activity.models as av
from django.db.models import Value
from django.db.models.functions import Concat
from django.db.models import Q
import apps.peoples.utils as putils
import json
import logging
log = logging.getLogger("__main__")

def get_assetincludes_choices():
    qset = av.Asset.objects.filter(
         ~Q(assetcode='NONE'), identifier='CHECKPOINT', enable = True).select_related(
            'parent').annotate(
            checkpoint = Concat(
                'assetname', Value(" ("), 'assetcode', Value(")")))
    return qset.values_list('id', 'checkpoint')

def get_assetsmartplace_choices():
    qset = av.Asset.objects.filter(
         ~Q(assetcode='NONE') & Q(identifier='SMARTPLACE') | Q(identifier='ASSET'), enable = True).select_related(
            'parent').annotate(
            checkpoint = Concat(
                'assetname', Value(" ("), 'assetcode', Value(")")))
    return qset.values_list('id', 'checkpoint')



def initialize_alerton_field(val, choices = False):
    pass


def validate_alertbelow(forms, data):
    min, alertbelow = float(data['min']), float(data['alertbelow'])
    msg = 'Alert below should be greater than minimum value.'
    if alertbelow < min: raise forms.ValidationError(msg)
    return alertbelow


def validate_alertabove(forms, data):
    max, alertabove = float(data['max']), float(data['alertabove'])
    msg = 'Alert above should be smaller than maximum value.'
    if alertabove > max: raise forms.ValidationError(msg)
    print("utils", alertabove)
    return alertabove    


def validate_options(forms, val):
    obj = json.loads(val)
    options = []
    for i in obj:
        options.append(i['value'])
    return json.dumps(options).replace('"', "").replace("[", "").replace("]", "")


def validate_alerton(forms, val):
    ic('validate_alerton', val)
    v1          = val.replace("'", "")
    v2          = v1.replace("[", "")
    v3          = v2.replace("]", "")
    vlist       = v3.split(", ")
    list_string = json.dumps(vlist)
    list        = json.loads(list_string)
    return json.dumps([each_string for each_string in list]).replace('"', "").replace("[", "").replace("]", "")

def initialize_alertbelow_alertabove(instance, form):
    alerton, below, above, li = instance.alerton, "", "", []
    print(alerton)
    if alerton and ('<' in alerton or '>' in alerton):
        s1 = alerton.replace(">", "")
        s2 = s1.replace(",", "")
        s3 = s2.replace("<", "")
        li = s3.split(" ")
        print(li)
        form.fields['alertbelow'].initial = float(li[0])
        form.fields['alertabove'].initial = float(li[1])


def init_assetincludes(form):
    form.fields['assetincludes'].initial = form.instance.assetincldes



def insert_questions_to_qsetblng(assigned_questions, model, fields, request):
    from django.db import transaction
    try:
        with transaction.atomic():
            for ques in assigned_questions:
                log.info(f"""{" " * 8} saving question {ques[1]} for QuestionSet {fields['qsetname']} [started]""")

                qsetbng, created = model.objects.update_or_create(
                    question_id = ques[2], qset_id = fields['qset'], client_id = fields['client'],
                    defaults = { 
                    "seqno"       : ques[0],
                    "question_id"   : ques[2],
                    "answertype"   : ques[3],
                    "min"         : float(ques[4]),
                    "max"         : float(ques[5]),
                    "options"     : ques[6].replace('"', ''),
                    "alerton"     : ques[7].replace('"', ''),
                    "ismandatory" : ques[8],
                    "qset_id"   : fields['qset']}
                )
                qsetbng.save()
                log.debug(f"{qsetbng.cuser}, {qsetbng.muser}, {qsetbng.cdtz}, {qsetbng.mdtz}")
                putils.save_userinfo(qsetbng, request.user, request.session)
                log.debug(f"""{" " * 8} {created} question {ques[1]} for QuestionSet {fields['qsetname']} [ended]""")

    except Exception:
        log.critical("something went wrong", exc_info = True)
        raise
