from django.db import models

class QuestionSetManager(models.Manager):
    use_in_migrations = True
    
    def get_template_list(self, bulist):
        if bulist:
            if qset := self.filter(bu_id__in=bulist).values_list('id', flat=True):
                return ','.join(list(qset))
        return ""