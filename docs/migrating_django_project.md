## BEGIN HOW TO APPLY MIGRATIONS 

``` diff - 
!NOTE: Following steps should perform after configuring databases in pgAdmin,and reflect the same configurations in settings.py DATABASES variable
```

- >1.python manage.py makemigrations peoples.
- >2.python manage.py migrate peoples --database= <name of db>.
- >3.follow step 1 & 2 for ohter apps.
- >4.python manage.py makemigrations.
- >5.python manage.py migrate --database= <name of db>.
- >6.follow step 5 for ohter databases.
