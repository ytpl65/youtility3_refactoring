import threading
from django.db import connections
from .utils import tenant_db_from_request

THREAD_LOCAL = threading.local()

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        db = tenant_db_from_request(request)
        print(f"Database:{db}")
        setattr(THREAD_LOCAL, "DB", db)
        response = self.get_response(request)
        return response


def get_current_db_name():
    return getattr(THREAD_LOCAL, 'DB', None)


def set_db_for_router(db):
    setattr(THREAD_LOCAL, "DB", db)


class TenantDbRouter:
    def _multi_db(self):
        from django.http import Http404
        from django.conf import settings
        if hasattr(THREAD_LOCAL, 'DB'):
            if THREAD_LOCAL.DB in settings.DATABASES:
                return THREAD_LOCAL.DB
            else:
                raise Http404
        else:
            return 'default'

    def db_for_read(self, model, **hints):
        db = self._multi_db()
        print(f"DB FOR READ {db}")
        return db
    
    def db_for_write(self, model, **hints):
        db = self._multi_db()
        print(f"DB FOR WRITE {db}")
        return db
    
    def allow_relation(self, obj1, obj2, **hints):
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True