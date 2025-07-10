from django.utils import timezone
import datetime

class CurrentDateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Formatea la fecha actual a 'YYYY-MM-DD' para una comparación consistente en el template
        today = timezone.localtime(timezone.now()).date().strftime('%Y-%m-%d')
        response.set_cookie('current_date', today)
        return response