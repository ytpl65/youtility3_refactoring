from import_export import widgets as wg
from django.db.models import Q
from apps.onboarding import models as om


class TypeAssistEmployeeTypeFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.select_related().filter(
            Q(client__bucode__exact=row["Client*"]),
            tatype__tacode__exact = 'PEOPLETYPE'
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