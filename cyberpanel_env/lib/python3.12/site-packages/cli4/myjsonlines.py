""" helper functions for jsonlines usage """

class myjsonlines():
    """ myjsonlines """

    _jsonlines = None

    def __init__(self):
        """ __init__ """
        if not myjsonlines._jsonlines:
            try:
                import jsonlines
                myjsonlines._jsonlines = jsonlines
            except ImportError as e:
                raise ImportError from e

    def Writer(self, fd):
        """ Writer() """
        return myjsonlines._jsonlines.Writer(fd)
