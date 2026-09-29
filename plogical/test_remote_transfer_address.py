import socket
import unittest
from unittest.mock import patch

from plogical.remoteTransferAddress import callback_address


class FakeRoute:
    def __init__(self, local_address):
        self.local_address = local_address

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def connect(self, destination):
        self.destination = destination

    def getsockname(self):
        return self.local_address, 12345


class CallbackAddressTests(unittest.TestCase):
    @patch('plogical.remoteTransferAddress.socket.socket')
    @patch('plogical.remoteTransferAddress.socket.getaddrinfo')
    def test_public_route_overrides_stale_installer_address(self, lookup, route):
        lookup.return_value = [(socket.AF_INET, socket.SOCK_DGRAM, 0, '',
                                ('70.36.114.216', 8090))]
        route.return_value = FakeRoute('70.36.114.223')
        self.assertEqual('70.36.114.223', callback_address('70.36.114.216', '70.36.114.194'))

    @patch('plogical.remoteTransferAddress.socket.socket')
    @patch('plogical.remoteTransferAddress.socket.getaddrinfo')
    def test_private_route_keeps_configured_public_address(self, lookup, route):
        lookup.return_value = [(socket.AF_INET, socket.SOCK_DGRAM, 0, '',
                                ('70.36.114.216', 8090))]
        route.return_value = FakeRoute('10.0.0.3')
        self.assertEqual('70.36.114.223', callback_address('70.36.114.216', '70.36.114.223'))

    @patch('plogical.remoteTransferAddress.socket.getaddrinfo', side_effect=OSError)
    def test_failed_route_keeps_configured_address(self, _):
        self.assertEqual('70.36.114.223', callback_address('source.example', '70.36.114.223'))


if __name__ == '__main__':
    unittest.main()
