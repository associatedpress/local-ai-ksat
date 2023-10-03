import django
from django.apps import AppConfig

class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    # TODO: Can't import GlobalConfig because it causes a circular dependency
    # on initial bootstrapping of project
    # Enables signal functionality
    def ready(self):
        import dashboard.signals

        # This ensures on startup that there is always a GlobalConfig
        try:
            from .models import GlobalConfig
            if GlobalConfig.objects.count() == 0:
                GlobalConfig.objects.create()
        except django.db.utils.ProgrammingError:
            pass
