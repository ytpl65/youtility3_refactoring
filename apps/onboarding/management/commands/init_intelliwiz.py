from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import IntegrityError
from apps.core import utils
from apps.onboarding.models import Bt, TypeAssist
from apps.peoples.models import People
from apps.onboarding.admin import TaResource
from apps.peoples.admin import CapabilityResource
from django.conf import settings
from tablib import Dataset
import logging
import psycopg2
from psycopg2 import sql

log = logging.getLogger(__name__)

MAX_RETRY = 5
DEFAULT_PASSWORD = 'superadmin@2022#'

def create_dummy_client_and_site():
    client_type = TypeAssist.objects.get(tatype__tacode = 'BVIDENTIFIER', tacode='CLIENT')
    site_type = TypeAssist.objects.get(tatype__tacode = 'BVIDENTIFIER', tacode='SITE')

    client, _ = Bt.objects.get_or_create(
        bucode='SPS', 
        defaults={'buname': "Security Personnel Services", 'enable': True, 'identifier':client_type, 'parent_id':1}
    )

    site, _ = Bt.objects.get_or_create(
        bucode='YTPL', 
        defaults={'buname': 'Youtility Technologies Pvt Ltd', 'enable': True, 'identifier':site_type, 'parent_id':client.id}
    )
    return client, site

def create_sql_functions(db):
    from apps.core.raw_sql_functions import get_sqlfunctions
    sql_functions_list = get_sqlfunctions().values()
    # Connect to the database
    DBINFO = settings.DATABASES[db]
    conn = psycopg2.connect(
        database=DBINFO['NAME'],
        user=DBINFO['USER'],
        password=DBINFO['PASSWORD'],
        host=DBINFO['HOST'],
        port=DBINFO['PORT'])
    
    # Create a new cursor object
    cur = conn.cursor()
    
    for function in sql_functions_list:
        cur.execute(function)
        conn.commit()
    
    # Close the cursor and connection
    cur.close()
    conn.close()

    
    

def insert_default_entries():
    BASE_DIR = settings.BASE_DIR
    filepaths_and_resources = {
        f'{BASE_DIR}/docs/default_types.xlsx': TaResource,
        f'{BASE_DIR}/docs/caps.xlsx': CapabilityResource
    }

    for filepath, Resource in filepaths_and_resources.items():
        with open(filepath, 'rb') as f:
            default_types = Dataset().load(f)
            resource = Resource(is_superuser=True)
            resource.import_data(default_types, dry_run=False, use_transactions=True, raise_errors = True)

def create_superuser(client, site):
    user = People.objects.create(
        peoplecode='SUPERADMIN', loginid="superadmin", peoplename='Super Admin',
        dateofbirth='1111-11-11', dateofjoin='1111-11-11',
        email='superadmin@youtility.in', isverified=True,
        is_staff=True, is_superuser=True,
        isadmin=True, client=client, bu=site
    )
    user.set_password(DEFAULT_PASSWORD)
    user.save()
    log.info(f"Superuser created successfully with loginid: {user.loginid} and password: {DEFAULT_PASSWORD}")

class Command(BaseCommand):
    help = 'This command creates None entries, a dummy Client and Site, a superuser, and inserts default entries in TypeAssist.'

    def add_arguments(self, parser) -> None:
        parser.add_argument('db', type=str)

    def handle(self, *args, **options):
        db = options['db']

        for _ in range(MAX_RETRY):
            try:
                utils.set_db_for_router(db)
                self.stdout.write(self.style.SUCCESS(f"Current DB selected is {utils.get_current_db_name()}"))

                utils.create_none_entries()
                self.stdout.write(self.style.SUCCESS('None Entries created successfully!'))

                insert_default_entries()
                self.stdout.write(self.style.SUCCESS('Default Entries Created..'))

                client, site = create_dummy_client_and_site()
                self.stdout.write(self.style.SUCCESS('Dummy client and site created successfully'))

                create_superuser(client, site)
                self.stdout.write(self.style.SUCCESS('Superuser created successfully'))
                
                create_sql_functions(db=db)
                break  # operation was successful, break the loop

            except utils.RecordsAlreadyExist as ex:
                self.stdout.write(self.style.WARNING(f'Database with this alias "{db}" is not empty. Operation terminated!'))
                break

            except utils.NoDbError:
                self.stdout.write(self.style.ERROR(f"Database with alias '{db}' does not exist. Operation cannot be performed."))
                break

            except IntegrityError as e:
                # optionally, handle the integrity error here
                pass

            except Exception as e:
                log.critical('FAILED init_intelliwiz', exc_info = True)

           
