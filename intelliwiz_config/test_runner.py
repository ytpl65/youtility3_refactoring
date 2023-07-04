from django.test.runner import DiscoverRunner

class MyTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        result = super().setup_databases(**kwargs)
        # Perform setup steps here
        # start automated initialization
        from django.core.management import call_command
        call_command('init_intelliwiz', 'default')
        return result
