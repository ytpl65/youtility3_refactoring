from django.db import models

class FeatureManager(models.Manager):
    
    def get_feature_list(self, request):
        return self.values(
            'name', 'description', 'defaultprice',
            'isactive', 'id'
        ).order_by('-mdtz')