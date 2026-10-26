"""CSRF boundary for the optional ConfigServer CSF iframe integration.

The vendor view is csrf_exempt and accepts mutating GET commands. Never restore
its installer's substring-based secMiddleware exemption. This adapter preserves
the plugin files and requires admin authorization plus CSRF before any POST.
"""
from html import escape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.urls import Resolver404, resolve
from django.utils.cache import patch_cache_control, patch_vary_headers

PATH = '/configservercsf/iframe/'
# Only dispatches inspected in ConfigServer DisplayUI. Additional query fields
# (including duplicates) require confirmation, even for these display actions.
READ_ONLY_ACTIONS = frozenset(('readme', 'status', 'lfdstatus', 'temp'))


def _registered_view(request):
    try:
        view = resolve(request.path_info, urlconf=getattr(request, 'urlconf', None)).func
        return (view.__module__ == 'configservercsf.views'
                and view.__name__ == 'configservercsfiframe')
    except Resolver404:
        return False


def _is_admin(request):
    from plogical.acl import ACLManager
    try:
        return ACLManager.loadedACL(request.session['userID']).get('admin') == 1
    except (KeyError, TypeError, AttributeError):
        return False


def _private(response):
    patch_cache_control(response, private=True, no_store=True)
    patch_vary_headers(response, ('Cookie',))
    return response


def _hidden(name, value):
    return '<input type="hidden" name="%s" value="%s">' % (
        escape(name, quote=True), escape(value, quote=True))


def _confirmation(request):
    fields = ''.join(_hidden(key, value) for key, values in request.GET.lists()
                     if key != 'csrfmiddlewaretoken' for value in values)
    token = _hidden('csrfmiddlewaretoken', get_token(request))
    return _private(HttpResponse(
        '<!doctype html><html><head><title>Confirm CSF action</title></head>'
        '<body><h1>Confirm CSF action</h1>'
        '<p>This request may change firewall settings. Continue only if you '
        'requested this action.</p><p>Action: <strong>%s</strong></p>'
        '<form method="post" action="%s">%s%s'
        '<button type="submit">Confirm and continue</button></form>'
        '<p><a href="%s">Cancel and return to CSF</a></p></body></html>' % (
            escape(request.GET.get('action', '(unspecified)')), PATH, fields, token, PATH)))


def validate_request(request):
    """Return (validated CSF route, early response); never execute plugin here."""
    if request.path_info != PATH:
        return False, None
    if not _registered_view(request) or not _is_admin(request):
        return False, HttpResponseForbidden('CSF administrator access required.')
    if request.method not in ('GET', 'POST'):
        return False, HttpResponseNotAllowed(('GET', 'POST'))
    if request.method == 'GET':
        query = request.GET
        readonly = (not query or (set(query) == {'action'}
                    and len(query.getlist('action')) == 1
                    and query['action'] in READ_ONLY_ACTIONS))
        if not readonly:
            return False, _confirmation(request)
    else:
        if request.content_type not in ('application/x-www-form-urlencoded',
                                        'multipart/form-data') or request.FILES:
            return False, HttpResponseForbidden('CSF requires an ordinary form submission.')
        # Explicitly check against a non-exempt callback. The vendor's decorator
        # must not disable CSRF; nor should a previously accepted request flag.
        csrf = CsrfViewMiddleware(lambda unused: HttpResponse())
        csrf.process_request(request)
        request.csrf_processing_done = False
        request._dont_enforce_csrf_checks = False
        failure = csrf.process_view(request, lambda unused: None, (), {})
        if failure is not None:
            return False, failure
    return True, None


class _Forms(HTMLParser):
    """Collect replacements for form opening tags, preserving all other bytes."""
    def __init__(self, source, request, token):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.base = request.build_absolute_uri()
        self.origin = urlsplit(self.base)
        self.token = token
        self.offsets = [0]
        for line in source.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.replacements = []

    def handle_starttag(self, tag, attrs):
        if tag != 'form':
            return
        values = dict(attrs)
        target = urlsplit(urljoin(self.base, values.get('action') or self.base))
        if (target.scheme, target.netloc, target.path) != (
                self.origin.scheme, self.origin.netloc, PATH):
            return
        # A form action's query is ignored by the vendor POST handler; preserve
        # that behavior rather than quietly adding previously ignored commands.
        kept = [(key, value) for key, value in attrs if key not in ('method', 'action')]
        rendered = ''.join(' ' + key + ('' if value is None else
                          '="' + escape(value, quote=True) + '"') for key, value in kept)
        replacement = '<form%s method="post" action="%s">%s' % (
            rendered, PATH, _hidden('csrfmiddlewaretoken', self.token))
        line, column = self.getpos()
        start = self.offsets[line - 1] + column
        self.replacements.append((start, start + len(self.get_starttag_text()), replacement))


def adapt_response(request, response):
    """Add tokens to same-route vendor forms without changing plugin files."""
    if response.streaming or not response.get('Content-Type', '').startswith('text/html'):
        return _private(response)
    source = response.content.decode(response.charset)
    forms = _Forms(source, request, get_token(request))
    forms.feed(source)
    forms.close()
    for start, end, replacement in reversed(forms.replacements):
        source = source[:start] + replacement + source[end:]
    response.content = source.encode(response.charset)
    if response.has_header('Content-Length'):
        response['Content-Length'] = str(len(response.content))
    for header in ('ETag', 'Last-Modified'):
        if response.has_header(header):
            del response[header]
    return _private(response)
