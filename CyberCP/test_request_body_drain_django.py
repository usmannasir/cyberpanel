"""Django itself, wrapped as CyberCP/wsgi.py wraps it: nothing of a body is left, and no answer changes.

The cases are the ones in which Django answers without reading the request's body, and the ones in which
it reads it, each served twice from the same request: by Django alone and by Django wrapped.
"""
import logging
import os
import unittest

from django.core.handlers.wsgi import WSGIHandler
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.test.utils import override_settings
from django.urls import path
from django.views.decorators.http import require_GET

from CyberCP.requestBodyDrain import CHUNK, reading_bodies_to_the_end
from CyberCP.test_request_body_drain import WorkerStream

PRODUCED = []


def ignores(request):
    return HttpResponse('the body was not looked at')


def reads_part(request):
    return HttpResponse(request.read(10))


def reads_all(request):
    return HttpResponse(request.body)


def reads_form(request):
    return HttpResponse(repr(sorted(request.POST.items())))


@require_GET
def get_only(request):
    return HttpResponse('only for GET')


def fails(request):
    raise RuntimeError('the view failed')


def streams(request):
    def pieces():
        for number in range(3):
            PRODUCED.append(number)
            yield b'piece %d;' % number
    return StreamingHttpResponse(pieces())


def sends_file(request):
    return FileResponse(open(os.path.abspath(__file__), 'rb'))


urlpatterns = [
    path('ignores/', ignores),
    path('reads-part/', reads_part),
    path('reads-all/', reads_all),
    path('reads-form/', reads_form),
    path('get-only/', get_only),
    path('fails/', fails),
    path('streams/', streams),
    path('sends-file/', sends_file),
]


class FileWrapper(object):
    """The worker's wsgi.file_wrapper: it sends the file itself when the response is exactly this type."""

    def __init__(self, filelike, block_size=8192):
        self.filelike, self.block_size = filelike, block_size

    def __iter__(self):
        return iter(lambda: self.filelike.read(self.block_size), b'')

    def close(self):
        self.filelike.close()


def setUpModule():
    # Not a name of this module: the test loader looks at every one of them, before any settings exist.
    from django.conf import settings
    if not settings.configured and not os.environ.get('DJANGO_SETTINGS_MODULE'):
        settings.configure(SECRET_KEY='only for these tests')


class DjangoBodiesTests(unittest.TestCase):
    BODY = b'filler=' + b'x' * (CHUNK + 1000)

    def setUp(self):
        overridden = override_settings(
            ROOT_URLCONF=__name__, MIDDLEWARE=['django.middleware.common.CommonMiddleware'], ALLOWED_HOSTS=['*'],
            DEBUG=False, APPEND_SLASH=True, DATA_UPLOAD_MAX_MEMORY_SIZE=2147483648, TEMPLATES=[])
        overridden.enable()
        self.addCleanup(overridden.disable)
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        del PRODUCED[:]

    def environ(self, method, address, body, **more):
        self.stream = WorkerStream(body or b'')
        environ = {
            'REQUEST_METHOD': method, 'PATH_INFO': address, 'SCRIPT_NAME': '', 'QUERY_STRING': '',
            'SERVER_NAME': 'panel.example.com', 'SERVER_PORT': '8090', 'HTTP_HOST': 'panel.example.com:8090',
            'SERVER_PROTOCOL': 'HTTP/1.1', 'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'wsgi.input': self.stream, 'wsgi.url_scheme': 'https', 'wsgi.file_wrapper': FileWrapper,
        }
        if body is not None and method != 'GET':
            environ['CONTENT_LENGTH'] = str(len(body))
        environ.update(more)
        return environ

    def serve(self, application, method, address, body, **more):
        """One request: what was left of its body when the response came back, and the whole answer."""
        started = []
        result = application(self.environ(method, address, body, **more),
                             lambda status, headers, exc_info=None: started.append((status, sorted(headers))))
        served = {'left': self.stream.left, 'asked': list(self.stream.asked), 'kind': type(result),
                  'produced': list(PRODUCED)}
        try:
            served['answer'] = (started, b''.join(result))
        finally:
            result.close()
        return served

    def both(self, method, address, body=BODY, **more):
        alone = self.serve(WSGIHandler(), method, address, body, **more)
        del PRODUCED[:]
        wrapped = self.serve(reading_bodies_to_the_end(WSGIHandler()), method, address, body, **more)
        self.assertEqual(alone['answer'], wrapped['answer'])
        self.assertIs(alone['kind'], wrapped['kind'])
        self.assertEqual(0, wrapped['left'])
        return alone, wrapped

    def status(self, served):
        return served['answer'][0][0][0][:3]

    def test_a_redirect_issued_before_the_view(self):
        alone, wrapped = self.both('POST', '/ignores')
        self.assertEqual('301', self.status(wrapped))
        self.assertEqual(len(self.BODY), alone['left'])

    def test_a_refused_host(self):
        alone, wrapped = self.both('POST', '/ignores/', HTTP_HOST='not a host name')
        self.assertEqual('400', self.status(wrapped))
        self.assertEqual(len(self.BODY), alone['left'])

    def test_an_address_that_does_not_exist(self):
        alone, wrapped = self.both('POST', '/no-such-address/')
        self.assertEqual('404', self.status(wrapped))
        self.assertEqual(len(self.BODY), alone['left'])

    def test_a_method_the_view_refuses(self):
        alone, wrapped = self.both('POST', '/get-only/')
        self.assertEqual('405', self.status(wrapped))
        self.assertEqual(len(self.BODY), alone['left'])

    def test_a_body_under_a_method_that_has_none(self):
        for method in ('GET', 'HEAD', 'DELETE', 'OPTIONS'):
            alone, wrapped = self.both(method, '/ignores/', CONTENT_LENGTH=str(len(self.BODY)))
            self.assertEqual('200', self.status(wrapped), method)
            self.assertEqual(len(self.BODY), alone['left'], method)

    def test_a_view_that_never_looks_at_the_body(self):
        alone, wrapped = self.both('POST', '/ignores/')
        self.assertEqual('200', self.status(wrapped))
        self.assertEqual(len(self.BODY), alone['left'])

    def test_a_view_that_reads_part_of_the_body(self):
        alone, wrapped = self.both('POST', '/reads-part/')
        self.assertEqual(b'filler=xxx', wrapped['answer'][1])
        self.assertEqual(len(self.BODY) - 10, alone['left'])

    def test_a_view_that_fails(self):
        alone, wrapped = self.both('POST', '/fails/')
        self.assertEqual('500', self.status(wrapped))
        self.assertEqual(len(self.BODY), alone['left'])

    def test_a_body_larger_than_django_accepts(self):
        with override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=1000):
            alone, wrapped = self.both('POST', '/reads-all/')
        self.assertIn(self.status(wrapped), ('400', '413'))
        self.assertEqual(len(self.BODY), alone['left'])

    def test_a_view_that_reads_the_whole_body_gets_all_of_it(self):
        alone, wrapped = self.both('POST', '/reads-all/')
        self.assertEqual(self.BODY, wrapped['answer'][1])
        self.assertEqual(0, alone['left'])
        # Django read it; all that is asked after that is one read, answered empty.
        self.assertEqual(alone['asked'] + [(CHUNK,)], wrapped['asked'])

    def test_a_view_that_reads_a_form_gets_all_of_it(self):
        alone, wrapped = self.both('POST', '/reads-form/', b'user=admin&word=secret')
        self.assertEqual(b"[('user', 'admin'), ('word', 'secret')]", wrapped['answer'][1])
        self.assertEqual(0, alone['left'])

    def test_a_request_without_a_body_costs_one_empty_read(self):
        for method, address in (('GET', '/ignores/'), ('GET', '/ignores'), ('POST', '/reads-all/'), ('HEAD', '/x')):
            alone, wrapped = self.both(method, address, None)
            self.assertEqual([], alone['asked'], (method, address))
            self.assertEqual([(CHUNK,)], wrapped['asked'], (method, address))

    def test_a_length_python_does_not_read_as_the_number_the_web_server_counted(self):
        # The stream, not the declared length, says where the body ends.
        for declared in ('%dabc' % len(self.BODY), '%d, %d' % (len(self.BODY), len(self.BODY)), '0x%x' % len(self.BODY),
                         '%d.0' % len(self.BODY), '7', ''):
            alone, wrapped = self.both('POST', '/ignores/', CONTENT_LENGTH=declared)
            self.assertEqual('200', self.status(wrapped), declared)
            self.assertEqual(len(self.BODY), alone['left'], declared)
            alone, wrapped = self.both('POST', '/reads-all/', CONTENT_LENGTH=declared)
            self.assertGreater(alone['left'], 0, declared)

    def test_a_streamed_response_is_not_started_when_it_is_returned(self):
        alone, wrapped = self.both('POST', '/streams/')
        self.assertEqual([], wrapped['produced'])
        self.assertEqual(b'piece 0;piece 1;piece 2;', wrapped['answer'][1])
        self.assertEqual(len(self.BODY), alone['left'])

    def test_a_file_is_still_handed_to_the_worker_to_send(self):
        alone, wrapped = self.both('POST', '/sends-file/')
        self.assertIs(FileWrapper, wrapped['kind'])
        with open(os.path.abspath(__file__), 'rb') as handle:
            self.assertEqual(handle.read(), wrapped['answer'][1])


if __name__ == '__main__':
    unittest.main()
