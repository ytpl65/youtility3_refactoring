from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core import utils
from django.db.utils import IntegrityError
from apps.onboarding.models import Bt
from apps.peoples.models import People
import logging
log = logging.getLogger('__main__')

def create_dummy_clientandsite():
    """
    creates a dummy client:SPS and site:YTPL

    Returns:
        _type_: _description_
    """
    from apps.onboarding.models import TypeAssist
    try:
        clienttype = TypeAssist.objects.get(tatype__tacode = 'BVIDENTIFIER', tacode='CLIENT')# 
        sitetype = TypeAssist.objects.get(tatype__tacode = 'BVIDENTIFIER', tacode='SITE')

        client, _ = Bt.objects.get_or_create(
            bucode='SPS', buname = "Security Personnel Services",
            enable = True,
            defaults={
                'bucode': "SPS", 'buname': "Security Personnel Services", 'enable':True,
                'identifier':clienttype, 'parent_id':1
            }            
        )

        site, _ = Bt.objects.get_or_create(
            bucode='YTPL', buname = "Youtility Technologies Pvt Ltd",
            enable = True, defaults={
                'bucode': 'YTPL', 'buname': 'Youtility Technologies Pvt Ltd', 'enable':True,
                'identifier':sitetype, 'parent_id':client.id
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
    from apps.onboarding.admin import TaResource
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
            ic(default_types)
            ta_resource = TaResource(is_superuser=True)
            ta_resource.import_data(default_types, dry_run = False, raise_errors = True)
    except Exception as e:
        log.error('FAILED insert_default_entries', exc_info = True)
        raise

def create_superuser(client, site):
    # sourcery skip: replace-interpolation-with-fstring, simplify-fstring-formatting
    user = People.objects.create(
        peoplecode='SUPERADMIN', peoplename='Super Admin',
        dateofbirth='1111-11-11', dateofjoin='1111-11-11',
        email='superadmin@youtility.in', isverified=True,
        is_staff=True, is_superuser=True,
        isadmin=True, client=client, bu=site
    )
    user.set_password('superadmin@2022#')
    user.save()
    log.info("Superuser created successfully with loginid: %s and password: superadmin@2022#" %(user.loginid))
    

def base_call(self):
    # create NONE entries in the tables
    utils.create_none_entries()
    self.stdout.write(self.style.SUCCESS('None Entries created successfully!'))
    
    # insert default entries for TypeAssist
    insert_default_entries_in_typeassist()
    self.stdout.write(self.style.SUCCESS('Default Entries Created..'))

    # create dummy client: SPS and site: YTPL
    client, site = create_dummy_clientandsite()
    self.stdout.write(self.style.SUCCESS('Dummy client and site created successfully'))

    # create superadmin
    create_superuser(client, site)



class Command(BaseCommand):
    # run commands as django init_intelliwiz test or python manage.py init_intelliwiz <db name>

    help = '''
    This command creates None entries in specified DB\n
    Creates a Dummpy Client and Site for SUPERADMIN\n
    Create one superuser for client and site\n
    Insert Default Entries in TypeAssist.
    '''

    @staticmethod
    def add_arguments(parser) -> None:
        parser.add_argument('db', nargs = 1, type = str)

    def handle(self, *args, **options):
        retry=5
        for _ in range(retry):
            try:
                db = options['db'][0]
                utils.set_db_for_router(db)

                with transaction.atomic(using = db):
                    utils.set_db_for_router(db)
                    self.stdout.write(self.style.SUCCESS(f"current db selected is {utils.get_current_db_name()}"))
                    base_call(self)
                    break

            except utils.RecordsAlreadyExist as ex:
                self.stdout.write(self.style.WARNING('Database with this alias "%s" is not empty so cannot create -1 extries operation terminated!' % db))

            except utils.NoDbError:
                self.stdout.write(
                    self.style.ERROR(
                        "Database with this alias '%s' not exist operation can't be performed"%(db)))

            except IntegrityError as e:
                log.warning("IntegrityError occured Retrying Again", exc_info = True)
                continue
            except Exception as e:
                self.stdout.write(self.style.ERROR("something went wrong...!"))
                log.error('FAILED init_intelliwiz', exc_info = True)

