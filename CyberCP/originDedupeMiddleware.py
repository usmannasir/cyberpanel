# coding=utf-8


class OriginDedupeMiddleware:
    """OpenLiteSpeed's proxy can forward a duplicated Origin header, which WSGI
    joins into 'https://host,https://host'. Django's CSRF origin check then
    matches nothing and 403s every POST. Collapse it to the first value."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.META.get('HTTP_ORIGIN')
        if origin and ',' in origin:
            request.META['HTTP_ORIGIN'] = origin.split(',')[0].strip()
        return self.get_response(request)
