import ast
import json
import os
from pathlib import Path
import socket
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, mock_open, patch

from plogical.remoteTransferAddress import callback_address
from plogical.remoteTransferResponse import parse_remote_transfer_response


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

    @patch('plogical.remoteTransferAddress.socket.socket')
    @patch('plogical.remoteTransferAddress.socket.getaddrinfo')
    def test_private_source_uses_local_private_callback(self, lookup, route):
        # The source pushes backups back to this VM, so its public machineIP
        # must not override the address used to reach the private source.
        for source, local in (
                ('172.16.0.201', '172.16.0.202'),
                ('10.1.0.201', '10.1.0.202'),
                ('192.168.0.201', '192.168.0.202'),
                ('10.1.0.201', '172.31.255.202')):
            with self.subTest(source=source, local=local):
                lookup.return_value = [(socket.AF_INET, socket.SOCK_DGRAM, 0, '',
                                        (source, 8090))]
                route.return_value = FakeRoute(local)
                self.assertEqual(local, callback_address(source, '88.198.10.20'))

    @patch('plogical.remoteTransferAddress.socket.socket')
    @patch('plogical.remoteTransferAddress.socket.getaddrinfo')
    def test_private_hostname_uses_resolved_route(self, lookup, route):
        lookup.return_value = [(socket.AF_INET, socket.SOCK_DGRAM, 0, '',
                                ('172.16.0.201', 8090))]
        route.return_value = FakeRoute('172.16.0.202')
        self.assertEqual('172.16.0.202', callback_address('old-vm.internal', '88.198.10.20'))
        lookup.assert_called_once_with('old-vm.internal', 8090, type=socket.SOCK_DGRAM)

    @patch('plogical.remoteTransferAddress.socket.socket')
    @patch('plogical.remoteTransferAddress.socket.getaddrinfo')
    def test_special_use_addresses_do_not_override_configured_callback(self, lookup, route):
        for special in ('127.0.0.1', '169.254.1.2', '0.0.0.0', '192.0.2.2',
                        '100.64.0.2', '224.0.0.1', '172.32.0.2'):
            for source, local in ((special, '172.16.0.202'), ('172.16.0.201', special)):
                with self.subTest(source=source, local=local):
                    lookup.return_value = [(socket.AF_INET, socket.SOCK_DGRAM, 0, '',
                                            (source, 8090))]
                    route.return_value = FakeRoute(local)
                    self.assertEqual('88.198.10.20', callback_address(source, '88.198.10.20'))

    @patch('plogical.remoteTransferAddress.socket.socket')
    @patch('plogical.remoteTransferAddress.socket.getaddrinfo')
    def test_unreachable_private_route_keeps_configured_address(self, lookup, route):
        lookup.return_value = [(socket.AF_INET, socket.SOCK_DGRAM, 0, '',
                                ('172.16.0.201', 8090))]
        route.return_value.__enter__.return_value.connect.side_effect = OSError('No route to host')
        self.assertEqual('88.198.10.20', callback_address('172.16.0.201', '88.198.10.20'))

    @patch('plogical.remoteTransferAddress.socket.getaddrinfo', side_effect=OSError)
    def test_failed_route_keeps_configured_address(self, _):
        self.assertEqual('70.36.114.223', callback_address('source.example', '70.36.114.223'))


class CallbackRequestTests(unittest.TestCase):
    @patch('plogical.remoteTransferAddress.socket.socket')
    @patch('plogical.remoteTransferAddress.socket.getaddrinfo')
    def test_transfer_request_advertises_private_route_instead_of_machine_ip(self, lookup, route):
        # Compile the real entry point without importing Django or server-only
        # dependencies. No files, processes, or network connections are created.
        path = Path(__file__).resolve().parents[1] / 'backup/backupManager.py'
        tree = ast.parse(path.read_text())
        manager = next(node for node in tree.body
                       if isinstance(node, ast.ClassDef) and node.name == 'BackupManager')
        manager.body = [node for node in manager.body
                        if isinstance(node, ast.FunctionDef) and node.name == 'starRemoteTransfer']
        post = Mock(return_value=SimpleNamespace(
            status_code=200, text=json.dumps({'transferStatus': 1, 'dir': '1001'})))
        machine_ip = mock_open(read_data='88.198.10.20\n')
        namespace = {
            'json': json, 'open': machine_ip,
            'os': SimpleNamespace(path=SimpleNamespace(join=os.path.join, exists=lambda _: False)),
            'ACLManager': SimpleNamespace(loadedACL=lambda _: {}, currentContextPermission=lambda *_: 1),
            'ProcessUtilities': SimpleNamespace(outputExecutioner=Mock(return_value='2222\n'),
                                                executioner=Mock()),
            'requests': SimpleNamespace(post=post),
            'HttpResponse': json.loads,
            'callback_address': callback_address,
            'parse_remote_transfer_response': parse_remote_transfer_response,
        }
        exec(compile(ast.Module(body=[manager], type_ignores=[]), str(path), 'exec'), namespace)
        lookup.return_value = [(socket.AF_INET, socket.SOCK_DGRAM, 0, '',
                                ('172.16.0.201', 8090))]
        route.return_value = FakeRoute('172.16.0.202')
        result = namespace['BackupManager']().starRemoteTransfer(1, {
            'ipAddress': '172.16.0.201', 'password': 'test-password',
            'accountsToTransfer': ['example.com'],
        })
        self.assertEqual(1, result['remoteTransferStatus'])
        self.assertEqual('https://172.16.0.201:8090/api/remoteTransfer', post.call_args.args[0])
        payload = json.loads(post.call_args.kwargs['data'])
        self.assertEqual('172.16.0.202', payload['ipAddress'])
        self.assertEqual('2222', payload['port'])
        self.assertEqual(['example.com'], payload['accountsToTransfer'])
        machine_ip.assert_called_once_with('/etc/cyberpanel/machineIP')


if __name__ == '__main__':
    unittest.main()
