""" Logging for Cloudflare API"""
import logging

# try:
#     import http.client as http_client
# except ImportError:
#     # Python 2
#     import httplib as http_client

DEBUG = 0
INFO = 1

class CFlogger(object):
    """ Logging for Cloudflare API"""

    def __init__(self, level):
        """ Logging for Cloudflare API"""
        self.logger_level = self._get_logging_level(level)
        #logging.basicConfig(level=self.logger_level)
        request_logger = logging.getLogger("requests.packages.urllib3")
        request_logger.setLevel(self.logger_level)
        request_logger.propagate = level

    def getLogger(self):
        """ Logging for Cloudflare API"""
        # create logger
        logger = logging.getLogger('Python Cloudflare API v4')
        logger.setLevel(self.logger_level)

        ch = logging.StreamHandler()
        ch.setLevel(self.logger_level)

        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        logger.addHandler(ch)

        # http_client.HTTPConnection.debuglevel = 1

        return logger

    def _get_logging_level(self, level):
        """ Logging for Cloudflare API"""
        if level is True:
            return logging.DEBUG
        return logging.INFO
