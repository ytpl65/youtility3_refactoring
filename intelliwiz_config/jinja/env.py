from jinja2.environment import Environment
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from django.contrib import messages
from widget_tweaks.templatetags import widget_tweaks as wt



def debug(info):
    print("Printing=============", info)
    
def to_local(val):
    from django.utils.timezone import get_current_timezone
    return val.astimezone(get_current_timezone()).strftime('%d-%b-%Y %H:%M')


class JinjaEnvironment(Environment):
    keep_trailing_newline = True,  # newline-terminate generated files
    lstrip_blocks = True,  # so can indent control flow tags
    trim_blocks = True # so don't need {%- -%} everywhere
    
    def __init__(self, **kwargs):
        super(JinjaEnvironment, self).__init__(**kwargs)
        self.globals['static']  = staticfiles_storage.url
        self.globals['url'] = reverse
        self.filters["debug"] = debug
        self.globals['get_msgs'] = messages.get_messages
        self.filters['add_class']  = wt.add_class   
        self.filters['set_attr']  = wt.set_attr 
        self.filters['addlabel_class']  = wt.add_label_class 
        self.filters['to_local']  = to_local
