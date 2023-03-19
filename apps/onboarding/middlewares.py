from django.utils import timezone
from datetime import timezone as dttimezone, timedelta

class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz = dttimezone(timedelta(minutes = int(request.session.get('ctzoffset', '0'))))
        # Set the time zone for the current request
        timezone.activate(tz)

        response = self.get_response(request)

        # Reset the time zone to the default after processing the request
        timezone.deactivate()

        return response
