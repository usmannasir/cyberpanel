"""Every request's body is taken from the web server to its end, whatever the application read of it."""
import ast
import inspect
import os
import unittest

from CyberCP.requestBodyDrain import CHUNK, discard_unread_body, reading_bodies_to_the_end


class WorkerStream(object):
    """The request body as the panel's worker (lswsgi) offers it, with a record of what was asked and given.

    As in wsgiinput.c: b'' once the body is used up, whatever is asked; with a body left, read(n) gives
    at most n bytes and read() or read(0) fail with SystemError. readline(n) gives at most n - 1 bytes of
    a line and fails likewise without a number above 1.
    """

    def __init__(self, body, at_most=None, fails_after=None, error=SystemError):
        self.body, self.taken, self.asked, self.given = body, 0, [], []
        self.at_most, self.fails_after, self.error = at_most, fails_after, error

    @property
    def left(self):
        return len(self.body) - self.taken

    def read(self, *size):
        self.asked.append(size)
        if len(self.asked) > 1000:
            raise AssertionError('the stream was asked without end')
        if self.left <= 0:
            self.given.append(0)
            return b''
        if len(size) != 1 or size[0] <= 0:
            raise SystemError('read returned NULL without setting an error')
        if self.fails_after is not None and self.taken >= self.fails_after:
            raise self.error('the web server closed the connection')
        size = size[0] if self.at_most is None else min(size[0], self.at_most)
        if self.fails_after is not None:
            size = min(size, self.fails_after - self.taken)
        data = self.body[self.taken:self.taken + size]
        self.taken += len(data)
        self.given.append(len(data))
        return data

    def readline(self, *size):
        if self.left <= 0:
            return b''
        if len(size) != 1 or size[0] <= 1:
            raise SystemError('readline returned NULL without setting an error')
        end = self.body.find(b'\n', self.taken, self.taken + size[0] - 1) + 1
        data = self.body[self.taken:end or self.taken + size[0] - 1]
        self.taken += len(data)
        return data


def request(stream, length='absent', **more):
    environ = {'REQUEST_METHOD': 'POST', 'PATH_INFO': '/base', 'wsgi.input': stream}
    if length != 'absent':
        environ['CONTENT_LENGTH'] = length
    environ.update(more)
    return environ


def application_reading(count, answer=(b'answer',)):
    """An application that reads `count` bytes of the body (None: nothing at all) and then answers."""
    def application(environ, start_response):
        if count is not None:
            environ['wsgi.input'].read(count)
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return answer
    return application


def started(recorded):
    def start_response(status, headers, exc_info=None):
        recorded.append((status, headers))
    return start_response


class DiscardUnreadBodyTests(unittest.TestCase):

    def test_a_body_nobody_read_is_taken_whole(self):
        stream = WorkerStream(b'x' * 1000)
        discard_unread_body(request(stream, '1000'))
        self.assertEqual(0, stream.left)
        # The stream's own end stops the reading: one empty answer, nothing after it.
        self.assertEqual([(CHUNK,), (CHUNK,)], stream.asked)

    def test_a_large_body_is_taken_in_pieces_of_64_kib(self):
        stream = WorkerStream(b'x' * (3 * CHUNK + 5))
        discard_unread_body(request(stream, str(3 * CHUNK + 5)))
        self.assertEqual(64 * 1024, CHUNK)
        self.assertEqual(0, stream.left)
        self.assertEqual([(CHUNK,)] * 5, stream.asked)
        self.assertEqual([CHUNK, CHUNK, CHUNK, 5, 0], stream.given)

    def test_a_stream_that_gives_less_than_asked_is_read_until_the_body_ends(self):
        stream = WorkerStream(b'x' * 2500, at_most=1000)
        discard_unread_body(request(stream, '2500'))
        self.assertEqual(0, stream.left)
        self.assertEqual([1000, 1000, 500, 0], stream.given)

    def test_a_partly_read_body_is_taken_to_its_end_and_then_left_alone(self):
        stream = WorkerStream(b'x' * 1000)
        stream.read(400)
        discard_unread_body(request(stream, '1000'))
        self.assertEqual(0, stream.left)
        self.assertEqual([400, 600, 0], stream.given)

    def test_a_body_already_read_costs_one_empty_read(self):
        stream = WorkerStream(b'x' * 1000)
        stream.read(1000)
        discard_unread_body(request(stream, '1000'))
        self.assertEqual([(1000,), (CHUNK,)], stream.asked)

    def test_a_request_without_a_body_costs_one_empty_read(self):
        for length in ('absent', None, '', '0', '-5', '00'):
            stream = WorkerStream(b'')
            discard_unread_body(request(stream, length))
            self.assertEqual([(CHUNK,)], stream.asked, length)

    def test_the_end_of_the_body_is_the_one_the_stream_knows_not_the_declared_length(self):
        # The stream, not the declared length, says where the body ends.
        for length in ('absent', None, '', '0', '-5', 'ten', '70000abc', '70000, 70000', '0x11170', '70000.0', '7',
                       '69999', b'70000abc', object()):
            stream = WorkerStream(b'x' * 70000)
            discard_unread_body(request(stream, length))
            self.assertEqual(0, stream.left, length)
            self.assertEqual([CHUNK, 70000 - CHUNK, 0], stream.given, length)

    def test_every_read_asks_for_a_positive_number_of_bytes(self):
        # The worker's stream fails for read() and read(0) while a body is left.
        stream = WorkerStream(b'x' * (2 * CHUNK + 1))
        discard_unread_body(request(stream, str(2 * CHUNK + 1)))
        self.assertEqual(0, stream.left)
        self.assertTrue(stream.asked)
        for asked in stream.asked:
            self.assertEqual(1, len(asked))
            self.assertGreater(asked[0], 0)

    def test_a_failing_read_ends_it_quietly(self):
        for error in (SystemError, OSError, ValueError, RuntimeError):
            for fails_after in (0, 300):
                stream = WorkerStream(b'x' * 1000, fails_after=fails_after, error=error)
                discard_unread_body(request(stream, '1000'))
                self.assertEqual(fails_after, stream.taken)
                self.assertEqual(2 if fails_after else 1, len(stream.asked))

    def test_a_request_without_a_stream_is_left_alone(self):
        environ = request(None, '10')
        del environ['wsgi.input']
        discard_unread_body(environ)
        discard_unread_body(request(None, '10'))
        discard_unread_body(request(object(), '10'))


class ReadingBodiesToTheEndTests(unittest.TestCase):

    def serve(self, application, stream, length):
        recorded = []
        environ = request(stream, length)
        result = reading_bodies_to_the_end(application)(environ, started(recorded))
        return result, recorded

    def test_nothing_is_left_whatever_the_application_read(self):
        for count in (None, 1, 400, 999, 1000):
            stream = WorkerStream(b'x' * 1000)
            result, recorded = self.serve(application_reading(count), stream, '1000')
            self.assertEqual(0, stream.left, count)
            self.assertEqual((b'answer',), result)
            self.assertEqual([('200 OK', [('Content-Type', 'text/plain')])], recorded)

    def test_the_application_reads_the_body_first(self):
        def echo(environ, start_response):
            start_response('200 OK', [])
            return [environ['wsgi.input'].read(int(environ['CONTENT_LENGTH']))]

        stream = WorkerStream(b'what the client sent')
        result, recorded = self.serve(echo, stream, '20')
        self.assertEqual([b'what the client sent'], result)
        self.assertEqual([(20,), (CHUNK,)], stream.asked)

    def test_the_application_gets_the_request_as_it_came(self):
        seen = []

        def application(environ, start_response):
            seen.append((environ, start_response))
            return []

        stream = WorkerStream(b'')
        environ = request(stream)
        start_response = started([])
        before = dict(environ)
        reading_bodies_to_the_end(application)(environ, start_response)
        self.assertIs(environ, seen[0][0])
        self.assertIs(start_response, seen[0][1])
        self.assertEqual(before, environ)
        self.assertIs(stream, environ['wsgi.input'])
        self.assertEqual([(CHUNK,)], stream.asked)

    def test_the_response_is_returned_as_the_application_made_it(self):
        answer = object()   # not even iterable: the worker's own file wrapper is such an object
        stream = WorkerStream(b'x' * 10)
        result, recorded = self.serve(application_reading(None, answer), stream, '10')
        self.assertIs(answer, result)
        self.assertEqual(0, stream.left)

    def test_a_streamed_response_is_not_started(self):
        produced = []

        def download(environ, start_response):
            start_response('200 OK', [('Content-Type', 'application/octet-stream')])

            def pieces():
                for number in range(3):
                    produced.append(number)
                    yield b'piece %d' % number
            return pieces()

        stream = WorkerStream(b'x' * (2 * CHUNK))
        result, recorded = self.serve(download, stream, str(2 * CHUNK))
        # The body is gone before the first piece of the response exists.
        self.assertEqual(0, stream.left)
        self.assertEqual([], produced)
        self.assertEqual(inspect.GEN_CREATED, inspect.getgeneratorstate(result))
        self.assertEqual(b'piece 0', next(result))
        self.assertEqual([0], produced)
        self.assertEqual([b'piece 1', b'piece 2'], list(result))

    def test_an_application_that_raises_still_has_its_body_taken(self):
        failure = RuntimeError('the view failed')

        def application(environ, start_response):
            environ['wsgi.input'].read(10)
            raise failure

        stream = WorkerStream(b'x' * 1000)
        with self.assertRaises(RuntimeError) as raised:
            self.serve(application, stream, '1000')
        self.assertIs(failure, raised.exception)
        self.assertEqual(0, stream.left)

    def test_a_failing_read_does_not_change_the_response(self):
        for error in (SystemError, OSError):
            stream = WorkerStream(b'x' * 1000, fails_after=100, error=error)
            result, recorded = self.serve(application_reading(None), stream, '1000')
            self.assertEqual((b'answer',), result)
            self.assertEqual([('200 OK', [('Content-Type', 'text/plain')])], recorded)
            self.assertEqual(100, stream.taken)

    def test_a_failing_read_does_not_hide_the_error_of_the_application(self):
        failure = KeyError('the view failed')

        def application(environ, start_response):
            raise failure

        stream = WorkerStream(b'x' * 1000, fails_after=0)
        with self.assertRaises(KeyError) as raised:
            self.serve(application, stream, '1000')
        self.assertIs(failure, raised.exception)


class PanelEntryPointTests(unittest.TestCase):

    def test_the_wsgi_application_of_the_panel_is_the_wrapped_one(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wsgi.py')
        with open(path) as handle:
            tree = ast.parse(handle.read())
        assigned = [node.value for node in tree.body if isinstance(node, ast.Assign)
                    and [getattr(target, 'id', None) for target in node.targets] == ['application']]
        self.assertEqual(1, len(assigned))
        self.assertEqual('reading_bodies_to_the_end', assigned[0].func.id)
        self.assertEqual(['get_wsgi_application'], [argument.func.id for argument in assigned[0].args])
        self.assertEqual([[], []], [assigned[0].keywords, assigned[0].args[0].args])
        imported = [node for node in tree.body if isinstance(node, ast.ImportFrom)
                    and node.module == 'CyberCP.requestBodyDrain']
        self.assertEqual([['reading_bodies_to_the_end']], [[alias.name for alias in node.names] for node in imported])


if __name__ == '__main__':
    unittest.main()
