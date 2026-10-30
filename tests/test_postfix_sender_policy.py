"""Policy protocol tests use real local sockets and stub only Django/ORM dependencies.

Run with python3 -m unittest discover -s tests -p test_postfix_sender_policy.py -v.
No installed CyberPanel settings, database, Postfix configuration or mail is used.
"""
import importlib
import os
from pathlib import Path
import runpy
import select
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def install_stubs():
    django = types.ModuleType('django')
    django.setup = lambda: None
    models = types.ModuleType('emailPremium.models')
    for name in ('EmailLimits', 'DomainLimits', 'EmailLogs', 'Domains', 'EUsers'):
        cls = type(name, (), {'DoesNotExist': type(name + 'Missing', (Exception,), {})})
        cls.objects = mock.Mock()
        setattr(models, name, cls)
    mail_models = types.ModuleType('mailServer.models')
    mail_models.Domains = models.Domains
    mail_models.EUsers = models.EUsers
    logger = types.ModuleType('plogical.CyberCPLogFileWriter')
    logger.CyberCPLogFileWriter = mock.Mock()
    return {'django': django, 'emailPremium.models': models,
            'mailServer.models': mail_models, 'plogical.CyberCPLogFileWriter': logger}


STUBS = install_stubs()
with mock.patch.dict(sys.modules, STUBS):
    handler = importlib.import_module('postfixSenderPolicy.accept_traffic')
    server = importlib.import_module('postfixSenderPolicy.startServer')
    controller = importlib.import_module('postfixSenderPolicy.policyCTRL')
    constraints = importlib.import_module('postfixSenderPolicy.policyConstraint')

ALLOW = b'action=dunno\n\n'
DEFER = b'action=defer_if_permit Service temporarily unavailable\n\n'


def request(username='sender@example.test', recipient='target@example.test', **attrs):
    values = {'request': 'smtpd_access_policy', 'protocol_state': 'DATA',
              'sasl_username': username, 'recipient': recipient}
    values.update(attrs)
    return ('\n'.join(k + '=' + v for k, v in values.items()) + '\n\n').encode()


class PolicySocketTests(unittest.TestCase):
    def setUp(self):
        self.clients = []
        self.workers = []
        self.directory = tempfile.TemporaryDirectory()
        self.purge = mock.patch.object(handler.HandleRequest, 'cleaningPath',
                                       self.directory.name + '/purge')
        self.purge.start()
        self.email = constraints.emailConstraints('sender@example.test', 10, 0, 5, 0, 1, 0)
        self.domain = constraints.policyConstraints('example.test', 100, 0, 1)
        self.domain.emails[self.email.emailAddress] = self.email
        handler.cacheManager.domains = {'example.test': self.domain}
        for name in ('Domains', 'DomainLimits', 'EUsers'):
            getattr(handler, name).objects.reset_mock(side_effect=True)

    def tearDown(self):
        for client in self.clients:
            client.close()
        for worker in self.workers:
            worker.join(2)
            self.assertFalse(worker.is_alive(), 'handler leaked after disconnect')
        self.purge.stop()
        self.directory.cleanup()

    def connect(self):
        client, connection = socket.socketpair()
        client.settimeout(2)
        worker = handler.HandleRequest(connection)
        worker.requestTimeout = 0.3
        worker.start()
        self.clients.append(client)
        self.workers.append(worker)
        return client

    def receive(self, client, count=1):
        reply = b''
        while reply.count(b'\n\n') < count:
            data = client.recv(4096)
            if not data:
                break
            reply += data
        return reply

    def test_allowed_and_hourly_limit_over_real_socket(self):
        client = self.connect()
        self.email.hourlyLimits = 1
        client.sendall(request())
        self.assertEqual(self.receive(client), ALLOW)
        client.sendall(request())
        self.assertEqual(self.receive(client), DEFER)
        self.assertEqual((self.email.hourlyUsed, self.email.monthlyUsed, self.domain.monthlyUsed), (1, 1, 1))

    def test_fragmented_short_reads_wait_for_blank_line(self):
        client = self.connect()
        frame = request()
        for chunk in (frame[:7], frame[7:40], frame[40:-1]):
            client.sendall(chunk)
            self.assertFalse(select.select([client], [], [], 0.02)[0])
        client.sendall(frame[-1:])
        self.assertEqual(self.receive(client), ALLOW)
        self.assertEqual(self.email.hourlyUsed, 1)

    def test_exact_64_byte_request(self):
        client = self.connect()
        frame = b'request=smtpd_access_policy\nsasl_username=\nx=' + b'a' * 17 + b'\n\n'
        self.assertEqual(len(frame), 64)
        client.sendall(frame)
        self.assertEqual(self.receive(client), ALLOW)

    def test_coalesced_requests_preserve_boundaries(self):
        client = self.connect()
        client.sendall(request() * 3)
        self.assertEqual(self.receive(client, 3), ALLOW * 3)
        self.assertEqual(self.email.hourlyUsed, 3)

    def test_multiple_recipients_still_enforce_limits(self):
        client = self.connect()
        self.email.hourlyUsed = self.email.hourlyLimits
        client.sendall(request(recipient='', recipient_count='2'))
        self.assertEqual(self.receive(client), DEFER)

    def test_omitted_recipient_counts_authenticated_message(self):
        client = self.connect()
        frame = request().replace(b'recipient=target@example.test\n', b'')
        client.sendall(frame)
        self.assertEqual(self.receive(client), ALLOW)
        self.assertEqual(self.email.hourlyUsed, 1)

    def test_unauthenticated_mail_bypasses_limits(self):
        client = self.connect()
        self.domain.monthlyUsed = 1000
        client.sendall(request(username=''))
        self.assertEqual(self.receive(client), ALLOW)
        self.assertEqual(self.domain.monthlyUsed, 1000)
        handler.EUsers.objects.get.assert_not_called()

    def test_absent_sasl_username_is_unauthenticated(self):
        client = self.connect()
        client.sendall(request().replace(b'sasl_username=sender@example.test\n', b''))
        self.assertEqual(self.receive(client), ALLOW)

    def test_domain_and_email_monthly_limit(self):
        for obj, attribute, value in ((self.domain, 'monthlyUsed', 100), (self.email, 'monthlyUsed', 10)):
            with self.subTest(attribute=attribute, value=value):
                setattr(obj, attribute, value)
                client = self.connect()
                client.sendall(request())
                self.assertEqual(self.receive(client), DEFER)
                setattr(obj, attribute, 0)

    def test_explicitly_disabled_limits_still_count(self):
        self.domain.limitStatus = 0
        self.email.hourlyUsed = 20
        client = self.connect()
        client.sendall(request())
        self.assertEqual(self.receive(client), ALLOW)
        self.assertEqual(self.email.hourlyUsed, 21)

    def test_database_failure_defers_instead_of_allowing(self):
        handler.cacheManager.domains = {}
        handler.Domains.objects.get.side_effect = RuntimeError('database unavailable')
        client = self.connect()
        client.sendall(request())
        self.assertEqual(self.receive(client), DEFER)

    def test_unconfigured_domain_preserves_no_policy_behavior(self):
        handler.cacheManager.domains = {}
        handler.Domains.objects.get.side_effect = handler.Domains.DoesNotExist()
        client = self.connect()
        client.sendall(request())
        self.assertEqual(self.receive(client), ALLOW)

    def test_malformed_request_receives_defer(self):
        for frame in (b'garbage\n\n', b'request=unknown\n\n', request(username='invalid'),
                      b'request=smtpd_access_policy\nx=\xff\n\n'):
            with self.subTest(frame=frame):
                client = self.connect()
                client.sendall(frame)
                self.assertEqual(self.receive(client), DEFER)

    def test_incomplete_request_times_out_without_counting(self):
        client = self.connect()
        client.sendall(request()[:-1])
        self.assertEqual(self.receive(client), DEFER)
        self.assertEqual(client.recv(1), b'')
        self.assertEqual(self.email.hourlyUsed, 0)

    def test_idle_connection_closes_without_unsolicited_defer(self):
        client = self.connect()
        self.assertEqual(client.recv(100), b'')
        self.assertEqual(self.email.hourlyUsed, 0)

    def test_oversized_request_is_bounded(self):
        client = self.connect()
        self.workers[-1].maxRequestBytes = 128
        client.sendall(b'x=' + b'a' * 129)
        self.assertEqual(self.receive(client), DEFER)
        self.assertEqual(self.email.hourlyUsed, 0)

    def test_attribute_values_can_contain_equals(self):
        client = self.connect()
        address = 'sender=tag@example.test'
        self.domain.emails[address] = self.email
        client.sendall(request(username=address))
        self.assertEqual(self.receive(client), ALLOW)
        self.assertEqual(self.email.hourlyUsed, 1)

    def test_simultaneous_connections_do_not_exceed_limit(self):
        self.email.hourlyLimits = 1
        clients = [self.connect() for _ in range(8)]
        for client in clients:
            client.sendall(request())
        replies = [self.receive(client) for client in clients]
        self.assertEqual(replies.count(ALLOW), 1)
        self.assertEqual(replies.count(DEFER), 7)
        self.assertEqual(self.email.hourlyUsed, 1)


class PolicyLifecycleTests(unittest.TestCase):
    def test_direct_script_imports_have_package_context(self):
        with mock.patch.dict(sys.modules, STUBS):
            imported = runpy.run_path(str(ROOT / 'postfixSenderPolicy/startServer.py'))
        self.assertEqual(imported['__package__'], 'postfixSenderPolicy')
        self.assertEqual(imported['handle'].__name__, handler.__name__)
        self.assertEqual(imported['handle'].__file__, handler.__file__)

    def test_controller_uses_same_python_and_module(self):
        with mock.patch.object(controller.os.path, 'exists', return_value=False), mock.patch.object(controller.subprocess, 'Popen') as popen:
            controller.policyCTRL().start()
        popen.assert_called_once_with([sys.executable, '-m', 'postfixSenderPolicy.startServer'], cwd=str(ROOT))

    def test_binding_failure_is_not_reported_as_success(self):
        conn = server.SetupConn('/nonexistent/policy-test/socket')
        with self.assertRaises(OSError):
            conn.setup_conn()
        conn.sock.close()

    def test_main_failure_has_no_pid_file(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(server.SetupConn, 'applicationPath', directory + '/pid'), mock.patch.object(server.SetupConn, 'serverAddress', directory + '/missing/socket'), mock.patch.object(server, 'signal'):
            with self.assertRaises(OSError):
                server.Main()
            self.assertFalse(Path(directory + '/pid').exists())

    def test_actual_process_unix_socket_and_sigterm_exit(self):
        # Fresh process: all Django imports are stubbed BEFORE server import.
        # Every file/socket path points inside this temporary directory.
        with tempfile.TemporaryDirectory() as directory:
            script = """
import importlib.util, os, sys
from unittest import mock
spec = importlib.util.spec_from_file_location('fixture', sys.argv[1])
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
server = fixture.server
server.SetupConn.serverAddress = sys.argv[2] + '/socket'
server.SetupConn.applicationPath = sys.argv[2] + '/pid'
fixture.handler.HandleRequest.cleaningPath = sys.argv[2] + '/purge'
fixture.handler.cacheManager.domains = {}
with mock.patch.object(server.os, 'chown'), mock.patch.object(server.pwd, 'getpwnam', return_value=type('User', (), {'pw_uid': os.getuid()})()), mock.patch.object(server.grp, 'getgrnam', return_value=type('Group', (), {'gr_gid': os.getgid()})()):
    server.Main()
"""
            process = subprocess.Popen([sys.executable, '-c', script, __file__, directory], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 5
                while not Path(directory + '/pid').exists():
                    if process.poll() is not None or time.monotonic() > deadline:
                        self.fail('isolated daemon failed: ' + repr(process.communicate(timeout=2)))
                    time.sleep(0.01)
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.settimeout(2)
                    client.connect(directory + '/socket')
                    client.sendall(request(username=''))
                    self.assertEqual(client.recv(100), ALLOW)
                process.send_signal(signal.SIGTERM)
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, stderr.decode())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()


if __name__ == '__main__':
    unittest.main()
