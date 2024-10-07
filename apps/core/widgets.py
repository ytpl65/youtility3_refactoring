from import_export import widgets as wg
from django.db.models import Q
from apps.onboarding import models as om
from apps.activity import models as am
from apps.peoples import models as pm

class TypeAssistEmployeeTypeFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.select_related().filter(
            Q(client__bucode__exact=row["Client*"]),
            Q(tatype__tacode__exact = 'PEOPLETYPE')| Q(tatype__tacode__exact='NONE'), 
        )
class TypeAssistWorkTypeFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.select_related().filter(
            Q(client__bucode__exact=row["Client*"]),
            tatype__tacode__exact = 'WORKTYPE'
        )
class TypeAssistDepartmentFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.select_related().filter(
            Q(client__bucode__exact=row["Client*"]),
            tatype__tacode__exact = 'DEPARTMENT'
        )
class TypeAssistDesignationFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.select_related().filter(
            Q(client__bucode__exact=row["Client*"]),
            tatype__tacode__exact = 'DESIGNATION'
        )
class BVForeignKeyWidget(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        client = om.Bt.objects.filter(bucode=row['Client*']).first()
        bu_ids = om.Bt.objects.get_whole_tree(client.id)
        qset = self.model.objects.select_related('parent', 'identifier').filter(
            id__in=bu_ids, identifier__tacode='SITE', parent__bucode=row['Client*'])
        ic(qset)
        return qset

class TypeAssistEmployeeTypeFKWUpdate(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        if 'Client' in row:
            return self.model.objects.select_related().filter(
                Q(client__bucode__exact=row["Client"]),
                Q(tatype__tacode__exact = 'PEOPLETYPE')| Q(tatype__tacode__exact='NONE'), 
            )
        return self.model.objects.none()
class TypeAssistWorkTypeFKWUpdate(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        if 'Client' in row:
            return self.model.objects.select_related().filter(
                Q(client__bucode__exact=row["Client"]),
                tatype__tacode__exact = 'WORKTYPE'
            )
        return self.model.objects.none()
class TypeAssistDepartmentFKWUpdate(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        if 'Client' in row:
            return self.model.objects.select_related().filter(
                Q(client__bucode__exact=row["Client"]),
                tatype__tacode__exact = 'DEPARTMENT'
            )
        return self.model.objects.none()
class TypeAssistDesignationFKWUpdate(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        if 'Client' in row:
            return self.model.objects.select_related().filter(
                Q(client__bucode__exact=row["Client"]),
                tatype__tacode__exact = 'DESIGNATION'
            )
        return self.model.objects.none()
    
class BVForeignKeyWidgetUpdate(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        if 'Client' in row:
            client = om.Bt.objects.filter(bucode=row['Client']).first()
            bu_ids = om.Bt.objects.get_whole_tree(client.id)
            qset = self.model.objects.select_related('parent', 'identifier').filter(
                id__in=bu_ids, identifier__tacode='SITE', parent__bucode=row['Client'])
            return qset
        return self.model.objects.none()
        
class QsetFKWUpdate(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        if 'Client' in row:
            return am.QuestionSet.objects.select_related().filter(
                Q(qsetname='NONE') | (Q(client__bucode = row['Client']) &  Q(enable=True))
            )
        return self.model.objects.none()
    
class TktCategoryFKWUpdate(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return om.TypeAssist.objects.select_related().filter(
            tatype__tacode="NOTIFYCATEGORY"
        )
    
class AssetFKWUpdate(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        if 'Client' in row:
            return am.Asset.objects.select_related().filter(
                Q(assetname='NONE') | (Q(client__bucode = row['Client']) & Q(enable=True))
            )
        return self.model.objects.none()
    
class PeopleFKWUpdate(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        if 'Client' in row:
            return pm.People.objects.select_related().filter(
                client__bucode = row['Client']
            )
        return self.model.objects.none()

class PgroupFKWUpdate(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        if 'Client' in row:
            return pm.Pgroup.objects.select_related().filter(
                (Q(client__bucode = row['Client']) & Q(enable=True)) | Q(groupname='NONE')
            )
        return self.model.objects.none()