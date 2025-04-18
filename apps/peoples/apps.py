from django.apps import AppConfig


class PeoplesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.peoples'
    
    def ready(self) -> None:
        from .import signals
