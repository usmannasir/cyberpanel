from django.conf import settings
from django.shortcuts import HttpResponse

class secMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST':
            if request.body.find(';') > -1 or request.body.find('&&') > -1 or request.body.find('|') > -1 or request.body.find('...') > -1:
                return HttpResponse('Bad input.')
        response = self.get_response(request)
        return response