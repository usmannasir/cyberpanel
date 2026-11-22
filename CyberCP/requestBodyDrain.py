"""Take every request's body from the web server to its end.

lscpd hands the panel's worker (lswsgi) a request as a header packet followed
by the body, on a connection it keeps for the request after it. The worker
ends a response without taking the part of the body the application left
unread, so that part stays on the connection and is read as the beginning of
the next request. Django leaves a body unread whenever nothing asks for it.

Nothing of one request may be left for the next, so once the application has
answered, what is left of the body is read and thrown away, before the
response goes back to the worker. Django's own development server does the
same (django.core.servers.basehttp.ServerHandler.close).
"""

CHUNK = 64 * 1024


def discard_unread_body(environ):
    """Read what is left of the request's body and throw it away.

    Never raises, and keeps at most CHUNK bytes at a time.

    The end of the body is the stream's own, not the length the request
    declares: lswsgi counts the body down from the length lscpd gave it and
    answers b'' once that count is used up, without touching the connection,
    also when the application has read all of it or there was no body. The
    declared length is not used.

    Every read asks for a positive number of bytes, because that stream fails
    for read() and read(0) while a body is left.
    """
    try:
        read = environ['wsgi.input'].read
        while read(CHUNK):
            pass
    except Exception:
        # The web server went away, or the stream cannot be read: there is
        # nothing more to take, and the response must still be returned.
        pass


def reading_bodies_to_the_end(application):
    """The WSGI application, with every request's body read to its end.

    The response is returned as the application made it: the same object, not
    wrapped and not started, so a streamed response still streams and a file
    is still sent by the worker itself.
    """
    def body_read_to_the_end(environ, start_response):
        try:
            return application(environ, start_response)
        finally:
            discard_unread_body(environ)
    return body_read_to_the_end
