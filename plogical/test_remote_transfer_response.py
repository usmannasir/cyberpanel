import unittest

from plogical.remoteTransferResponse import parse_remote_transfer_response


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class RemoteTransferResponseTests(unittest.TestCase):
    def test_accepts_success_with_numeric_transfer_id(self):
        result = parse_remote_transfer_response(
            FakeResponse('{"transferStatus": 1, "dir": "1234"}')
        )

        self.assertEqual(result, (1, '1234', 'None'))

    def test_returns_remote_error_when_status_schema_is_legacy_or_missing(self):
        result = parse_remote_transfer_response(
            FakeResponse('{"status": 0, "error_message": "API Access Disabled."}')
        )

        self.assertEqual(result, (0, '', 'API Access Disabled.'))

    def test_rejects_an_invalid_transfer_id(self):
        result = parse_remote_transfer_response(
            FakeResponse('{"transferStatus": 1, "dir": "1234;rm -rf /"}')
        )

        self.assertEqual(result, (0, '', 'Remote server returned an invalid transfer identifier.'))

    def test_reports_non_json_response_without_raising_key_error(self):
        result = parse_remote_transfer_response(FakeResponse('<html>Bad gateway</html>', 502))

        self.assertEqual(result, (0, '', 'Remote server returned an invalid response (HTTP 502).'))
