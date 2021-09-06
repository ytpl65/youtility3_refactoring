from jinja2.environment import Environment
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from django.contrib import messages


def debug(info):
    print("Printing=============", info)

class JinjaEnvironment(Environment):
    keep_trailing_newline=True,  # newline-terminate generated files
    lstrip_blocks=True,  # so can indent control flow tags
    trim_blocks=True # so don't need {%- -%} everywhere
    
    def __init__(self, **kwargs):
        super(JinjaEnvironment, self).__init__(**kwargs)
        self.globals['static']  = staticfiles_storage.url
        self.globals['url'] = reverse
        self.filters["debug"] = debug
        self.globals['get_msgs'] = messages.get_messages
    