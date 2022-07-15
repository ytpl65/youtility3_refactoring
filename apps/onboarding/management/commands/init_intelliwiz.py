from django.core.management.base import BaseCommand
from apps.core import utils
from django.db import transaction
import logging

from apps.onboarding.models import Bt
log = logging.getLogger('__main__')


def create_dummy_clientandsite():
    """
    creates a dummy client:SPS and site:YTPL

    Returns:
        _type_: _description_
    """
    from apps.onboarding.models import TypeAssist
    try:
        #clienttype = TypeAssist.objects.get(tatype__tacode = 'BVIDENTIFIER', tacode='CLIENT')
        #sitetype = TypeAssist.objects.get(tatype__tacode = 'BVIDENTIFIER', tacode='SITE')

        client = Bt.objects.get_or_create(
            bucode='SPS', buname = "Security Personnel Services",
            enable = True,
            defaults={
                'bucode': "SPS", 'buname': "Security Personnel Services", 'enable':True
                }            
        )

        site = Bt.objects.get_or_create(
            bucode='YTPL', buname = "Youtility Technologies Pvt Ltd",
            enable = True, defaults={
                'bucode': 'SPS', 'buname': 'Security Personnel Services', 'enable':True
            }
        )
        return client, site
    except Exception as e:
        log.error("Failed create_dummy_clientandsite", exc_info= True)
        raise




def insert_default_entries_in_typeassist():
    """
    Inserts Default rows in TypeAssist Table
    """
    from apps.onboarding.models import TypeAssist
    from django.conf import settings
    from tablib import Dataset
    from import_export import resources
    BASEDIR = settings.BASE_DIR

    try:
        filepath = f'{BASEDIR}/docs/default_types.xlsx'
        with open(filepath, 'rb') as f:
            utils.set_db_for_router(utils.get_current_db_name())
            log.info(f'current db when importing data from file {utils.get_current_db_name()}')
            default_types = Dataset().load(f)
            ta_resource = resources.modelresource_factory(model = TypeAssist)()
            ta_resource.import_data(default_types, dry_run = False)
    except Exception as e:
        log.error('FAILED insert_default_entries', exc_info = True)
        raise



class Command(BaseCommand):
    #run commands as django init_intelliwiz test or python manage.py init_intelliwiz <db name>

    help = '''
    This command creates None entries in specified DB\n
    Creates a Dummpy Client and Site for SUPERADMIN\n
    Create one superuser for client and site\n
    Insert Default Entries in TypeAssist.
    '''


    def add_arguments(self, parser) -> None:
        parser.add_argument('db', nargs = 1, type = str)


    def handle(self, *args, **options):

        try:
            db = options['db'][0]
            utils.set_db_for_router(db)
            # if isexist := TypeAssist.objects.all():
            #     raise utils.RecordsAlreadyExist

            with transaction.atomic(using = db):
                utils.set_db_for_router(db)
                self.stdout.write(self.style.SUCCESS(f"current db selected is {utils.get_current_db_name()}"))

                #create NONE entries in the tables
                id = utils.create_none_entries()
                print(Bt.objects.get(id = id).bucode, "%%%%%%%%%%%%%5")
                self.stdout.write(self.style.SUCCESS('None Entries created successfully!'))

                #insert default entries for TypeAssist
                insert_default_entries_in_typeassist()
                self.stdout.write(self.style.SUCCESS('Default Entries Created..'))

                #create dummy client: SPS and site: YTPL
                create_dummy_clientandsite()
                self.stdout.write(self.style.SUCCESS('Dummy client and site created successfully'))

                #create superadmin
                #TODO

        except utils.RecordsAlreadyExist as ex:
            self.stdout.write(self.style.WARNING('Database with this alias "%s" is not empty so cannot create -1 extries operation terminated!' % db))

        except utils.NoDbError:
            self.stdout.write(
                self.style.ERROR(
                    "Database with this alias '%s' not exist operation can't be performed"%(db)))
        except Exception as e:
            self.stdout.write(self.style.ERROR("something went wrong...!"))
            log.error('FAILED init_intelliwiz', exc_info = True)
