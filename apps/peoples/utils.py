def upload_peopleimg(instance, filename):
    from os.path import expanduser, join
    from django.conf import settings
    
    #if "username" in request.session:
    peoplecode = instance.peoplecode
    foldertype = 'people'
    home_dir   = basedir=  fyear= fmonth= None
    home_dir   = join(expanduser('~'), '/')
    basedir    = "master"
    filepath = join(settings.MEDIA_ROOT, basedir, foldertype, peoplecode)
    filepath = str(filepath).lower()[1:]
    fullpath = home_dir + filepath
    return fullpath