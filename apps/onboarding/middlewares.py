import pytz
from django.utils import timezone

class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ic(timezone.now())
        ic(timezone.localtime())
        # Get the user's time zone from the request or the user's profile
        user_timezone = request.session.get('ctzoffset', 0)
        # Alternatively, you can get the user's time zone from their profile or preferences

        # Set the time zone for the current request
        timezone.activate(pytz.timezone(user_timezone))

        response = self.get_response(request)

        # Reset the time zone to the default after processing the request
        timezone.deactivate()

        return response
