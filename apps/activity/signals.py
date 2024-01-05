from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Asset, AssetLog
from django.utils import timezone

@receiver(post_save, sender=Asset)
def create_asset_log(sender, instance, created, **kwargs):
    if not created:
        last_log = AssetLog.objects.filter(asset_id=instance.id).order_by('-cdtz').first()
        if last_log and last_log.newstatus != instance.runningstatus:
            AssetLog.objects.create(
                asset_id=instance.id,
                oldstatus=last_log.newstatus,
                newstatus=instance.runningstatus,
                cdtz=timezone.now(),
                bu_id=instance.bu_id,
                client_id=instance.client_id,
                ctzoffset=instance.ctzoffset,
                people_id=instance.muser_id
            )
        elif not last_log:
            AssetLog.objects.create(
                asset_id=instance.id,
                oldstatus=None,
                newstatus=instance.runningstatus,
                cdtz=timezone.now(),
                people_id=instance.muser_id,
                bu_id=instance.bu_id,
                client_id=instance.client_id,
                ctzoffset=instance.ctzoffset
            )