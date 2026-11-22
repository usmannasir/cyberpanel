"""Requests to the scanner's file endpoints are counted in the database, per time window, and never waved through."""
from unittest import mock

from django.test import SimpleTestCase

from aiScanner import api


class RateLimitTests(SimpleTestCase):

    def setUp(self):
        self.model = mock.Mock()
        self.row = mock.Mock(pk=11, request_count=0)
        self.model.objects.get_or_create.return_value = (self.row, True)
        self.counters = self.model.objects.filter.return_value
        self.expired = mock.Mock()
        self.open = mock.Mock()
        self.counters.filter.side_effect = lambda **query: self.expired if 'last_request_at__lt' in query else self.open
        self.open.update.return_value = 1
        patcher = mock.patch('aiScanner.models.ScannerAPIRateLimit', self.model)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_request_below_the_limit_is_counted_in_the_database(self):
        self.assertTrue(api.check_rate_limit('cp_scan', 'get-file', 5)[0])
        self.model.objects.filter.assert_called_once_with(pk=11)
        self.assertEqual({'request_count__lt': 5}, self.counters.filter.call_args_list[-1][1])
        expression = self.open.update.call_args[1]['request_count']
        self.assertEqual('CombinedExpression', type(expression).__name__)
        self.row.save.assert_not_called()

    def test_a_request_at_the_limit_is_refused(self):
        self.open.update.return_value = 0
        self.assertFalse(api.check_rate_limit('cp_scan', 'get-file', 5)[0])

    def test_a_window_that_is_over_starts_again(self):
        api.check_rate_limit('cp_scan', 'get-file', 5)
        query = self.counters.filter.call_args_list[0][1]
        self.assertEqual(['last_request_at__lt'], list(query))
        values = self.expired.update.call_args[1]
        self.assertEqual(0, values['request_count'])
        self.assertEqual(api.RATE_LIMIT_WINDOW, values['last_request_at'] - query['last_request_at__lt'])

    def test_a_failure_to_count_is_not_a_pass(self):
        self.model.objects.get_or_create.side_effect = RuntimeError('database gone')
        self.assertFalse(api.check_rate_limit('cp_scan', 'get-file', 5)[0])
