import logging
from typing import Type
import os
from django.http import response as rp
from django.shortcuts import  render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.db.models import Q
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.db.utils import IntegrityError
from django.conf import settings
from django.db import transaction
from django.http.request import QueryDict
from icecream import ic
from .models import Shift,  TypeAssist, Bt, GeofenceMaster
from apps.peoples.utils import save_userinfo
from apps.core import utils
import apps.onboarding.forms as obforms
import apps.peoples.utils as putils
from apps.peoples import admin as people_admin
from apps.onboarding import admin as ob_admin
from django.db import IntegrityError
import apps.activity.models as am
import apps.attendance.models as atm
from apps.y_helpdesk.models import Ticket
from apps.work_order_management.models import Wom
from django.core.exceptions import ObjectDoesNotExist
from pprint import pformat
import uuid
from tablib import Dataset
CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)
logger = logging.getLogger('django')

def get_caps(request):  # sourcery skip: extract-method
    logger.info('get_caps requested')
    selected_parents = request.GET.getlist('webparents[]')
    logger.info(f'selected_parents {selected_parents}')
    cfor = request.GET.get('cfor')
    logger.info(f'cfor {cfor}')
    if selected_parents:
        from apps.peoples.models import Capability
        import json
        childs = []
        for i in selected_parents:
            child = Capability.objects.get_child_data(i, cfor)
            childs.extend({'capscode': j.capscode} for j in child)
        logger.info(f'childs = [] {childs}')
        return rp.JsonResponse(data=childs, safe=False)


def handle_pop_forms(request):
    if request.method != 'POST':
        return
    form_name = request.POST.get('form_name')
    form_dict = {
        'ta_form': obforms.TypeAssistForm,
    }
    form = form_dict[form_name](request.POST, request=request)
    ic(request.POST)
    if not form.is_valid():
        ic(form.errors)
        return rp.JsonResponse({'saved': False, 'errors': form.errors})
    ta = form.save(commit=False)
    ta.enable = True
    form.save(commit=True)
    save_userinfo(ta, request.user, request.session)
    if request.session.get('wizard_data'):
        request.session['wizard_data']['taids'].append(ta.id)
        print(ta.id)
    return rp.JsonResponse({'saved': True, 'id': ta.id, 'tacode': ta.tacode})

# -------------------- END Client View Classes ------------------------------#

# ---------------------------- END client onboarding   ---------------------------#


class SuperTypeAssist(LoginRequiredMixin, View):
    params = {
        'form_class': obforms.SuperTypeAssistForm,
        'template_form': 'onboarding/partials/partial_ta_form.html',
        'template_list': 'onboarding/supertypeassist.html',
        'partial_form': 'onboarding/partials/partial_ta_form.html',
        'related': ['parent',  'cuser', 'muser'],
        'model': TypeAssist,
        'fields': ['id', 'tacode', 'client__bucode', 'bu__bucode',
                   'taname', 'tatype__tacode', 'cuser__peoplecode'],
        'form_initials': {}}

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None
        ic(R)
        # first load the template
        if R.get('template'):
            return render(request, self.params['template_list'])
        # then load the table with objects for table_view
        if R.get('action') == 'list':
            ic(self.params)
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                ~Q(tacode='NONE'), enable=True
            ).values(*self.params['fields'])
            return rp.JsonResponse(data={'data': list(objs)})

        if R.get('action', None) == 'form':
            cxt = {'ta_form': self.params['form_class'](request=request),
                   'msg': "create supertypeassist requested"}
            resp = utils.render_form(request, self.params, cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = utils.render_form_for_delete(request, self.params, True)

        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            resp = utils.render_form_for_update(
                request, self.params, "ta_form", obj)
        print(f'return resp={resp}')
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        R = request.POST
        try:
            print(request.POST)
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            print(pk, type(pk))
            if pk:
                msg = "supertypeassist_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), {'request': request})
                print(form.data)
                create = False
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info('supertypeassist form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            ta = form.save()
            putils.save_userinfo(
                ta, request.user, request.session, create=create)
            logger.info("supertypeassist form saved")
            data = {'msg': f"{ta.tacode}",
                    'row': TypeAssist.objects.values(*self.params['fields']).get(id=ta.id)}
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return handle_intergrity_error("SuperTypeAssist")


class TypeAssistView(LoginRequiredMixin, View):
    params = {
        'form_class': obforms.TypeAssistForm,
        'template_form': 'onboarding/partials/partial_ta_form.html',
        'template_list': 'onboarding/typeassist.html',
        'partial_form': 'onboarding/partials/partial_ta_form.html',
        'related': ['parent',  'cuser', 'muser'],
        'model': TypeAssist,
        'fields': ['id', 'tacode', 'cdtz',
                   'taname', 'tatype__tacode', 'cuser__peoplecode'],
        'form_initials': {}}

    def get(self, request, *args, **kwargs):
        R, S, resp = request.GET, request.session, None
        ic(R)
        # first load the template
        if R.get('template'):
            return render(request, self.params['template_list'])
        # then load the table with objects for table_view
        if R.get('action') == 'list':
            ic(self.params)
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                    ~Q(tacode='NONE'), ~Q(tatype__tacode='NONE'), Q(client_id=S['client_id']) | Q(cuser_id=1), enable=True,
            ).values(*self.params['fields'])
            return rp.JsonResponse(data={'data': list(objs)})

        if R.get('action', None) == 'form':
            cxt = {'ta_form': self.params['form_class'](request=request),
                   'msg': "create typeassist requested"}
            resp = utils.render_form(request, self.params, cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = utils.render_form_for_delete(request, self.params, True)

        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            resp = utils.render_form_for_update(
                request, self.params, "ta_form", obj)
        print(f'return resp={resp}')
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        R = request.POST
        try:
            print(request.POST)
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            print(pk, type(pk))
            if pk:
                msg = "typeassist_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), {'request': request})
                print(form.data)
                create = False
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info('typeassist form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            ta = form.save()
            putils.save_userinfo(
                ta, request.user, request.session, create=create)
            logger.info("typeassist form saved")
            data = {'msg': f"{ta.tacode}",
                    'row': TypeAssist.objects.values(*self.params['fields']).get(id=ta.id)}
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return handle_intergrity_error("TypeAssist")


class ShiftView(LoginRequiredMixin, View):
    params = {
        'form_class': obforms.ShiftForm,
        'template_form': 'onboarding/partials/partial_shiftform.html',
        'template_list': 'onboarding/shift.html',
        'related': ['parent',  'cuser', 'muser'],
        'model': Shift,
        'fields': ['id', 'shiftname', 'starttime', 'endtime', 'nightshiftappicable'],
        'form_initials': {}}

    def get(self, request, *args, **kwargs):
        R, resp, P = request.GET, None, self.params

        # first load the template
        if R.get('template'):
            return render(request, self.params['template_list'])
        # then load the table with objects for table_view
        if R.get('action', None) == 'list':
            objs = self.params['model'].objects.shift_listview(
                request, P['related'], P['fields'])
            resp = rp.JsonResponse(data={
                'data': list(objs),
            }, status=200, safe=False)

        elif R.get('action', None) == 'form':
            cxt = {'shift_form': self.params['form_class'](request=request),
                   'msg': "create shift requested"}
            resp = utils.render_form(request, self.params, cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            print(f'resp={resp}')
            resp = utils.render_form_for_delete(request, self.params, False)
        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            resp = utils.render_form_for_update(
                request, self.params, "shift_form", obj)
        print(f'return resp={resp}')
        return resp

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            print(request.POST)
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            print(pk, type(pk))
            if pk:
                msg = "shift_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), {'request': request})
                create = False
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            logger.error("SHIFT saving error!", exc_info=True)
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info('shift form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            shift = form.save()
            shift.bu_id = int(request.session['client_id'])
            putils.save_userinfo(shift, request.user,
                                 request.session, create=create)
            logger.info("shift form saved")
            data = {'msg': f"{shift.shiftname}",
                    'row': Shift.objects.values(*self.params['fields']).get(id=shift.id)}
            return rp.JsonResponse(data, status=200)
        except IntegrityError:
            return handle_intergrity_error("Shift")


class EditorTa(LoginRequiredMixin, View):
    template = 'onboarding/testEditorTa.html'
    fields = ['id', 'tacode', 'taname', 'tatype__tacode', 'cuser__peoplecode']
    model = TypeAssist
    related = ['cuser', 'tatype']

    def get(self, request, *args, **kwargs):
        R = request.GET
        if R.get('template'):
            return render(request, self.template)

    def post(self, request, *args, **kwargs):
        R = request.POST
        ic(pformat(request.POST, compact=True))
        objs = self.model.objects.select_related(
            *self.related).filter(
        ).values(*self.fields)
        count = objs.count()
        logger.info(
            f'Shift objects {count or "No Records!"} retrieved from db')
        if count:
            objects, filtered = utils.get_paginated_results(
                R, objs, count, self.fields, self.related, self.model)
            logger.info('Results paginated'if count else "")
        return rp.JsonResponse(
            data={
                'draw': R['draw'], 'recordsTotal': count,
                'data': list(objects),
                'recordsFiltered': filtered}, status=200
        )


class GeoFence(LoginRequiredMixin, View):
    params = {
        'form_class': obforms.GeoFenceForm,
        'template_list': 'onboarding/geofence_list.html',
        'template_form': 'onboarding/geofence_form.html',
        'fields': ['id', 'gfcode',
                   'gfname', 'alerttogroup__groupname', 'alerttopeople__peoplename'],
        'related': ['alerttogroup', 'alerttopeople'],
        'model': GeofenceMaster
    }

    def get(self, request, *args, **kwargs):
        R = request.GET
        params = self.params
        ic(R)
        # first load the template
        if R.get('template'):
            return render(request, self.params['template_list'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = self.params['model'].objects.get_geofence_list(
                params['fields'], params['related'], request.session)
            return rp.JsonResponse(data={'data': list(objs)})

        if request.GET.get('perform') == 'editAssignedpeople':
            resp = am.Job.objects.handle_geofencepostdata(request)
            return rp.JsonResponse(resp, status=200)

        if R.get('action') == 'loadPeoples':
            objs = self.params['model'].objects.getPeoplesGeofence(request)
            return rp.JsonResponse(data={'items': list(objs)})

        if R.get('action') == "getAssignedPeople" and R.get('id'):
            objs = am.Job.objects.get_people_assigned_to_geofence(R['id'])
            return rp.JsonResponse(data={'data': list(objs)})

        if R.get('action', None) == 'form':
            NONE_P = utils.get_or_create_none_people()
            NONE_G = utils.get_or_create_none_pgroup()
            cxt = {'geofenceform': self.params['form_class'](
                initial={'alerttopeople': NONE_P, 'alerttogroup': NONE_G}, request=request)}
            return render(request, self.params['template_form'], context=cxt)

        if R.get('action') == 'drawgeofence':
            return get_geofence_from_point_radii(R)

        if R.get('id') not in [None, 'None']:
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'geofenceform': self.params['form_class'](request=request, instance=obj),
                   'edit': True,
                   'geofencejson': GeofenceMaster.objects.get_geofence_json(pk=obj.id)}
            return render(request, self.params['template_form'], context=cxt)

    def post(self, request, *args, **kwargs):
        resp = None
        try:
            data = QueryDict(request.POST.get('formData'))
            geofence = request.POST.get('geofence')
            if pk := request.POST.get('pk', None):
                msg = "geofence_view"
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), kwargs={'request': request})
            else:
                form = self.params['form_class'](data, request=request)
            if form.is_valid():
                resp = self.handle_valid_form(form, request, geofence)
            else:
                cxt = {'errors': form.errors}
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            logger.error('GEOFENCE saving error!', exc_info=True)
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, geofence):
        logger.info('geofence form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            with transaction.atomic(using=utils.get_current_db_name()):
                gf = form.save()
                self.save_geofence_field(gf, geofence)
                gf = putils.save_userinfo(gf, request.user, request.session)
                logger.info("geofence form saved")
                return rp.JsonResponse(data={'pk': gf.id}, status=200)
        except IntegrityError:
            return handle_intergrity_error("GeoFence")

    @staticmethod
    def save_geofence_field(gf, geofence):
        try:
            from django.contrib.gis.geos import LinearRing, Polygon
            import json
            geofencedata = json.loads(geofence)
            ic(geofencedata)
            ic(type(geofencedata))
            coords = [(i['lng'], i['lat']) for i in geofencedata]
            ic(coords)
            pg = Polygon(LinearRing(coords, srid=4326), srid=4326)
            gf.geofence = pg
            gf.save()
        except Exception:
            logger.error('geofence polygon field saving error', exc_info=True)
            raise


def get_geofence_from_point_radii(R):
    try:
        lat, lng, radii = R.get('lat'), R.get('lng'), R.get('radii')
        if all([lat, lng, radii]):
            from django.contrib.gis import geos
            point = geos.Point(float(lng), float(lat), srid=4326)
            point.transform(3857)
            geofence = point.buffer(int(radii))
            geofence.transform(4326)
            return rp.JsonResponse(data={'geojson': utils.getformatedjson(geofence)}, status=200)
        return rp.JsonResponse(data={'errors': "Invalid data provided unable to compute geofence!"}, status=404)
    except Exception:
        logger.error(
            "something went wrong while computing geofence..", exc_info=True)
        return rp.JsonResponse(data={'errors': 'something went wrong while computing geofence!'}, status=404)


class FileRemovalResponse(rp.FileResponse):
    def close(self):
        super().close()
        os.remove(self.filename)


class BulkImportData(LoginRequiredMixin, View):
    params = {
        'model_resource_map': {
            'TYPEASSIST': ob_admin.TaResource,
            'BV': ob_admin.BtResource,
            'PEOPLEGROUP': people_admin.PeopleResource,
            'SITEGROUP': people_admin.SiteGroupResource,
            'CAPABILITY': people_admin.Capability,
        },
        'form': obforms.ImportForm,
        'template': 'onboarding/import.html'
    }
    header_mapping = {
        'TYPEASSIST': ['Name*', 'Code*', 'Type*', 'BV*', 'Client*']
    }

    def get(self, request, *args, **kwargs):
        R, P = request.GET, self.params

        if (R.get('action') == 'form'):
            cxt = {'importform': P['form'](initial={'table': "TYPEASSIST"})}
            return render(request, P['template'], cxt)

        if (request.GET.get('action') == 'downloadTemplate') and request.GET.get('template'):
            import pandas as pd
            from io import BytesIO
            columns = self.header_mapping.get(R['template'])
            df = pd.DataFrame(columns=columns)
            # Write DataFrame to an in-memory BytesIO object
            buffer = BytesIO()
            df.to_excel(buffer, index=False, engine='openpyxl')
            buffer.seek(0)
            ic(R['template'], columns)
            return rp.FileResponse(
                buffer, as_attachment=True, filename=f'{R["template"]}.xlsx'
            )

    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        ic(R)
        form = P['form'](R, request.FILES)
        if not form.is_valid():
            return rp.JsonResponse({'errors': form.errors}, status=404)
        res, dataset = self.get_resource_and_dataset(request, form)
        if R.get('action') == 'confirmImport':
            results = res.import_data(dataset = dataset, dry_run = False, raise_errors = False)
            return rp.JsonResponse({'totalrows':results.total_rows}, status = 200)
        else:
            try:
                results = res.import_data(
                    dataset=dataset, dry_run=True, raise_errors=False, use_transactions=True)
                ic(res.get_error_result_class())
                if results.has_errors():
                    data = []
                    for rowerr in results.row_errors():
                        
                        row_data = {'Row#': rowerr[0]}
                        errors = []
                        for err in rowerr[1]:
                            ic(dir(err))
                            readable_error = self.get_readable_error(err.error)
                            errors.append(readable_error)
                            row_data |= err.row
                        row_data['Error'] = '<br>'.join(errors)
                        data.append(row_data)

                    columns = [{'title': col, 'data': col}
                            for col in data[0].keys()] if data else []
                    no_of_cols = len(data[0].keys()) if data else 0
                    return rp.JsonResponse({'data': data, 'columns': columns, 'no_of_cols': no_of_cols, 'rc': 1}, status=200)
                else:
                    columns = [{'title': col}
                            for col in dataset.dict[0].keys()] if dataset.dict else []
                    preview_data = [list(row) for row in dataset._data]
                    return rp.JsonResponse({'totalrows': results.total_rows, 'columns': columns, 'preview_data': preview_data}, status=200)
            except Exception as e:
                logger.error("error", exc_info=True)
                return rp.JsonResponse({"error": "something went wrong!"}, status=500)
    
    def get_resource_and_dataset(self, request, form):
        table = form.cleaned_data.get('table')
        file = request.FILES['importfile']
        dataset = Dataset().load(file)
        res = self.params['model_resource_map'][table](request=request)
        return res, dataset

    def get_readable_error(self, errors):
        if(isinstance(errors, ObjectDoesNotExist)):
            return "Related values does not exist, please check your data."
        if(isinstance(errors, IntegrityError)):
            return "Record already exist, please check your data."

class Client(LoginRequiredMixin, View):
    params = {
        'form_class': obforms.BtForm,
        'json_form': obforms.ClentForm,
        'template_form': 'onboarding/client_buform.html',
        'template_list': 'onboarding/client_bulist.html',
        'model': Bt,
        'fields': ['id', 'bucode', 'buname', 'enable'],
        'related': [],
    }

    def get(self, request, *args, **kwargs):
        from .utils import get_bt_prefform
        R, P = request.GET, self.params

        # first load the template
        if R.get('template'):
            return render(request, P['template_list'])

        # then load the table with objects for table_view
        if R.get('action', None) == 'list' or R.get('search_term'):
            objs = P['model'].objects.get_client_list(
                P['fields'], P['related'])
            return rp.JsonResponse(data={'data': list(objs)})

        if R.get('action', None) == 'form':
            cxt = {'clientform': P['form_class'](client=True, request=request),
                   'clientprefsform': P['json_form'](),
                   'ta_form': obforms.TypeAssistForm(auto_id=False, request=request),
                   'ownerid': uuid.uuid4()
                   }
            return render(request, P['template_form'], context=cxt)

        if R.get('action') == 'loadIdentifiers':
            qset = TypeAssist.objects.load_identifiers(request)
            return rp.JsonResponse({'items': list(qset), 'total_count': len(qset)}, status=200)

        if R.get('action') == 'loadParents':
            qset = Bt.objects.load_parent_choices(request)
            return rp.JsonResponse({'items': list(qset), 'total_count': len(qset)}, status=200)

        if R.get('action') == 'delete':
            return utils.render_form_for_delete(request, self.params, True)

        if R.get('action') == 'getlistbus':
            fields = ['id', 'bucode', 'buname', 'identifier__tacode', 'identifier_id',
                      'parent__buname', 'enable', 'parent_id']
            objs = P['model'].objects.get_allsites_of_client(
                request.GET.get('id'), fields=fields)
            ic(objs)
            return rp.JsonResponse(data={'data': list(objs)})

        if R.get('action') == 'getadmins':
            objs = P['model'].objects.get_listadmins(request)
            return rp.JsonResponse(data={'data': list(objs)})

        if R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            cxt = {'clientform': self.params['form_class'](request=request, instance=obj),
                   'edit': True, 'ta_form': obforms.TypeAssistForm(auto_id=False, request=request),
                   'clientprefsform': get_bt_prefform(obj), 'ownerid': obj.uuid}
            return render(request, self.params['template_form'], context=cxt)

    def post(self, request, *args, **kwargs):
        R, P = request.POST, self.params
        if R.get('bupostdata'):
            resp = P['model'].objects.handle_bupostdata(request)
            return rp.JsonResponse(resp, status=200)

        if R.get('adminspostdata'):
            resp = P['model'].objects.handle_adminspostdata(request)
            return rp.JsonResponse(resp, status=200)
        data = QueryDict(request.POST['formData'])

        try:
            if pk := request.POST.get('pk', None):
                msg, create = "client_view", False
                client = utils.get_model_obj(pk, request,  P)
                form = P['form_class'](
                    data, request.FILES, instance=client, request=request)
            else:
                form = P['form_class'](data, request=request)
            ic(form.instance.id)
            jsonform = P['json_form'](data, session=request.session)
            if form.is_valid() and jsonform.is_valid():
                resp = self.handle_valid_form(form, jsonform, request)
            else:
                cxt = {'errors': form.errors}
                if jsonform.errors:
                    cxt.update({'errors': jsonform.errors})
                resp = utils.handle_invalid_form(request, P, cxt)
        except Exception:
            resp = utils.handle_Exception(request)
        return resp

    @staticmethod
    def handle_valid_form(form, jsonform, request):
        logger.info('client form is valid')
        from .utils import save_json_from_bu_prefsform
        try:
            with transaction.atomic(using=utils.get_current_db_name()):
                client = form.save()
                client.uuid = request.POST.get('uuid')
                if save_json_from_bu_prefsform(client, jsonform):
                    client = putils.save_userinfo(
                        client, request.user, request.session)
                    logger.info("people form saved")
                data = {'pk': client.id}
                return rp.JsonResponse(data, status=200)
        except Exception:
            return utils.handle_Exception(request)


class BtView(LoginRequiredMixin, View):
    params = {
        'form_class': obforms.BtForm,
        'template_form': 'onboarding/bu_form.html',
        'template_list': 'onboarding/bu_list.html',
        'related': ['parent', 'identifier', 'butype'],
        'model': Bt,
        'fields': ['id', 'bucode', 'buname', 'butree', 'identifier__taname',
                   'enable', 'parent__buname', 'butype__taname', 'solid'],
        'form_initials': {}}

    def get(self, request, *args, **kwargs):
        R, resp = request.GET, None

        # first load the template
        if R.get('template'):
            return render(request, self.params['template_list'])
        # then load the table with objects for table_view
        if R.get('action', None) == 'list':
            buids = self.params['model'].objects.get_whole_tree(
                request.session['client_id'])
            objs = self.params['model'].objects.select_related(
                *self.params['related']).filter(
                    id__in=buids
            ).exclude(identifier__tacode='CLIENT').values(*self.params['fields'])
            return rp.JsonResponse(data={'data': list(objs)})

        elif R.get('action', None) == 'form':
            cxt = {'buform': self.params['form_class'](request=request),
                   'ta_form': obforms.TypeAssistForm(auto_id=False, request=request),
                   'msg': "create bu requested"}
            return render(request, self.params['template_form'], context=cxt)

        elif R.get('action', None) == "delete" and R.get('id', None):
            resp = utils.render_form_for_delete(request, self.params, True)

        elif R.get('id', None):
            obj = utils.get_model_obj(int(R['id']), request, self.params)
            initial = {'controlroom': obj.bupreferences.get('controlroom')}
            cxt = {'ta_form': obforms.TypeAssistForm(auto_id=False, request=request),
                   'buform': self.params['form_class'](request=request, instance=obj, initial=initial)}
        return render(request, self.params['template_form'], context=cxt)

    def post(self, request, *args, **kwargs):
        resp, create = None, True
        try:
            print(request.POST)
            data = QueryDict(request.POST['formData'])
            pk = request.POST.get('pk', None)
            print(pk, type(pk))
            if pk:
                msg = "bu_view"
                obj = utils.get_model_obj(pk, request, self.params)
                form = utils.get_instance_for_update(
                    data, self.params, msg, int(pk), kwargs={'request': request})
                create = False
            else:
                form = self.params['form_class'](data, request=request)

            if form.is_valid():
                resp = self.handle_valid_form(form, request, create)
            else:
                cxt = {'errors': form.errors}
                ic(len(form.errors), form.errors.get('gpslocation'))
                resp = utils.handle_invalid_form(request, self.params, cxt)
        except Exception:
            logger.error("BU saving error!", exc_info=True)
            resp = utils.handle_Exception(request)
        return resp

    def handle_valid_form(self, form, request, create):
        logger.info('bu form is valid')
        from apps.core.utils import handle_intergrity_error
        try:
            bu = form.save(commit=False)
            ic(form.cleaned_data)
            bu.gpslocation = form.cleaned_data['gpslocation']
            bu.bupreferences['permissibledistance'] = form.cleaned_data['permissibledistance']
            bu.bupreferences['controlroom'] = form.cleaned_data['controlroom']
            bu.bupreferences['address'] = form.cleaned_data['address']
            putils.save_userinfo(
                bu, request.user, request.session, create=create)
            logger.info("bu form saved")
            return rp.JsonResponse({'pk': bu.id}, status=200)
        except IntegrityError:
            return handle_intergrity_error("Bu")


class RPDashboard(LoginRequiredMixin, View):
    P = {
        "RP": "dashboard/RP_d/rp_dashboard.html",
        "pel_model": atm.PeopleEventlog,
        "jn_model": am.Jobneed
    }

    def get(self, request, *args, **kwargs):
        P, R = self.P, request.GET
        try:
            if R.get('action') == 'getCounts':
                objs = self.get_all_dashboard_counts(request, P)
                ic(objs)
                return rp.JsonResponse(objs, status=200)
            return render(request, P['RP'])
        except Exception as e:
            logger.error(
                "something went wrong RPDashboard view", exc_info=True)

    def get_all_dashboard_counts(self, request, P):
        R, S = request.GET, request.session
        if R['from'] and R['upto']:
            asset_chart_arr, asset_chart_total = am.Asset.objects.get_assetchart_data(
                request)
            alert_chart_arr, alert_chart_total = am.Jobneed.objects.get_alertchart_data(
                request)
            ticket_chart_arr, ticket_chart_total = Ticket.objects.get_ticket_stats_for_dashboard(
                request)
            wom_chart_arr, wom_chart_total = Wom.objects.get_wom_status_chart(
                request)
            ppmtask_arr = am.Jobneed.objects.get_ppmchart_data(request)
            task_arr = am.Jobneed.objects.get_taskchart_data(request)
            tour_arr = am.Jobneed.objects.get_tourchart_data(request)

            return {
                'counts': {
                    'totalschd_tasks_count': task_arr[-1],
                    'assigned_tasks_count': task_arr[0],
                    'completed_tasks_count': task_arr[1],
                    'autoclosed_tasks_count': task_arr[2],

                    'totalschd_ppmtasks_count': ppmtask_arr[-1],
                    'assigned_ppmtasks_count': ppmtask_arr[0],
                    'completed_ppmtasks_count': ppmtask_arr[1],
                    'autoclosed_ppmtasks_count': ppmtask_arr[2],

                    'totalscheduled_tours_count': tour_arr[-1],
                    'completed_tours_count': tour_arr[0],
                    'inprogress_tours_count': tour_arr[1],
                    'partiallycompleted_tours_count': tour_arr[2],

                    'assetchartdata': asset_chart_arr,
                    'alertchartdata': alert_chart_arr,
                    'ticketchartdata': ticket_chart_arr,
                    'womchartdata': wom_chart_arr,

                    'assetchart_total_count': asset_chart_total,
                    'alertchart_total_count': alert_chart_total,
                    'ticketchart_total_count': ticket_chart_total,
                    'wom_total_count': wom_chart_total,

                    'sos_count': P['pel_model'].objects.get_sos_count_forcard(request),
                    'IR_count': P['jn_model'].objects.get_ir_count_forcard(request),
                    'FR_fail_count': P['pel_model'].objects.get_frfail_count_forcard(request),
                    'route_count': P['jn_model'].objects.get_schdroutes_count_forcard(request)
                }
            }


class FileUpload(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        pass
