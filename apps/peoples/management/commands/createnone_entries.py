from tokenize import String
from django.core.management.base import BaseCommand

from apps.core import utils


class Command(BaseCommand):
    help = 'creates none entries in the followning tables:\n\
    People, Capability, QuestionSet, Job, Asset, Jobneed, Bt, Typeassist Asset'
    
    def add_arguments(self, parser) -> None:
        parser.add_argument('db', nargs = 1, type=str)
    
    
    def handle(self, *args, **options):
        try:
            db = options['db'][0]
            utils.set_db_for_router(db)
        except Exception:
            self.stdout.write(self.style.WARNING("Database with this alias '%s' not exist operation can't be performed"%(db)))
        else:
            utils.get_or_create_none_typeassist()
            utils.get_or_create_none_people()
            utils.get_or_create_none_bv()
            utils.get_or_create_none_cap()
            utils.get_or_create_none_pgroup()
            utils.get_or_create_none_job()
            utils.get_or_create_none_jobneed()
            utils.get_or_create_none_qset()
            utils.get_or_create_none_asset()
            utils.get_or_create_none_question()
            utils.get_or_create_none_qsetblng()
            self.stdout.write(self.style.SUCCESS('Successfully created none entries in "%s" '%db))
        
        