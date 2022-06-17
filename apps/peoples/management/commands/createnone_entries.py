from sys import exc_info
from django.core.management.base import BaseCommand
from apps.core import utils
from django.db import transaction


class Command(BaseCommand):
    help = 'creates none entries in the followning tables:\n\
    People, Capability, QuestionSet, Job, Asset, Jobneed, Bt, Typeassist Asset'
    
    def add_arguments(self, parser) -> None:
        parser.add_argument('db', nargs = 1, type=str)
    
    
    def handle(self, *args, **options):
        from apps.onboarding.models import TypeAssist
        try:
            db = options['db'][0]
            utils.set_db_for_router(db)
            if isexists := TypeAssist.objects.exists():
                raise ValueError
            with transaction.atomic(using=db):
                utils.get_or_create_none_typeassist()
                utils.get_or_create_none_people()
                utils.get_or_create_none_bv()
                utils.get_or_create_none_cap()
                utils.get_or_create_none_pgroup()
                utils.get_or_create_none_job()
                utils.get_or_create_none_jobneed()
                utils.get_or_create_none_qset()
                utils.get_or_create_none_asset()
                utils.get_or_create_none_tenant()
                utils.get_or_create_none_question()
                utils.get_or_create_none_qsetblng()
                self.stdout.write(self.style.SUCCESS('Successfully created none entries in "%s" '%db))
        except NameError:
            self.stdout.write(self.style.WARNING("Database with this alias '%s' not exist operation can't be performed"%(db)))
        except ValueError:
            self.stdout.write(self.style.ERROR('Database with this alias "%s" is not empty so cannot create -1 extries operation terminated!'%(db)))
        except Exception:
            self.stdout.write(self.style.ERROR("something went wrong!", exc_info = True))
            raise
            
                
        
        