"""Exercise remote-transfer port isolation and real subprocess error logging.

Extract only the worker/API entry points to avoid loading panel models. Files
live in a temporary directory; SSH/SCP are replaced at the process boundary.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from plogical.securityUtils import is_safe_port, is_safe_remote_host


ROOT = Path(__file__).resolve().parents[1]


def load_definitions(path, names, namespace):
    tree = ast.parse(path.read_text())
    nodes = [node for node in tree.body
             if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)


class RemoteTransferTransportTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.commands = []
        self.children = []
        self.opened = []
        self.removed = []
        self.ssh_code = 0
        self.scp_code = 0
        self.error = ''

        def local(path):
            path = Path(path)
            return path if self.root in path.parents else self.root / str(path).lstrip('/')

        def fixture_open(path, *args, **kwargs):
            self.opened.append(str(path))
            mapped = local(path)
            mapped.parent.mkdir(parents=True, exist_ok=True)
            return open(mapped, *args, **kwargs)

        def remove(path):
            self.removed.append(str(path))
            os.remove(local(path))

        def child(**kwargs):
            self.children.append(kwargs)
            return SimpleNamespace(start=lambda: None, pid=12345)

        def call(command, **kwargs):
            self.commands.append(command)
            code = self.ssh_code if command[1] == 'ssh' else self.scp_code
            # A real child emits to stderr; the production stdout/stderr plumbing
            # must put the detail in the same log before the outcome message.
            script = 'import sys; sys.stderr.write(%r); sys.exit(%r)' % (self.error, code)
            return subprocess.call([sys.executable, '-c', script], **kwargs)

        self.local = local
        self.open = fixture_open
        self.os = SimpleNamespace(
            path=SimpleNamespace(exists=lambda path: local(path).exists()),
            makedirs=lambda path: local(path).mkdir(parents=True), remove=remove)
        self.env = {
            'os': self.os, 'open': fixture_open, 'time': time,
            'argparse': argparse, 'sys': sys, 'shlex': shlex,
            'subprocess': SimpleNamespace(call=call, STDOUT=subprocess.STDOUT),
            'logging': SimpleNamespace(CyberCPLogFileWriter=Mock()),
            'Process': child, 'ProcessUtilities': SimpleNamespace(executioner=Mock(), debugPath='/debug'),
            'backupSchedule': SimpleNamespace(createLocalBackup=Mock()),
            'move': lambda source, destination: shutil.move(str(local(source)), str(local(destination))),
        }
        load_definitions(ROOT / 'plogical/remoteTransferUtilities.py',
                         {'remoteTransferUtilities', 'main'}, self.env)
        self.worker = self.env['remoteTransferUtilities']

    def start(self, transfer='1001', port='2222'):
        accounts = self.root / ('accounts-' + transfer)
        accounts.write_text('example.com\n')
        self.worker.remoteTransfer('192.0.2.10', transfer, str(accounts), port)
        return self.local('/home/backup/transfer-' + transfer + '/backup_log')

    def test_preflight_uses_requested_port_and_passes_it_to_worker(self):
        self.start(port='2200')
        command = self.commands[0]
        self.assertEqual('2200', command[command.index('-p') + 1])
        self.assertEqual(['root@192.0.2.10', 'true'], command[-2:])
        self.assertIn('BatchMode=yes', command)
        self.assertIn('ConnectTimeout=10', command)
        self.assertEqual('2200', self.children[0]['args'][-1])
        self.assertNotIn('/home/cyberpanel/remote_port', self.opened)

    def test_failed_ssh_logs_detail_and_never_starts_backup(self):
        self.ssh_code = 255
        self.error = 'Permission denied (publickey).\n'
        log = self.start()
        content = log.read_text()
        self.assertIn(self.error, content)
        self.assertIn('on SSH port 2222 failed', content)
        self.assertIn('[5010]', content)
        self.assertFalse(self.children)

    def test_interleaved_jobs_keep_their_ports_through_backup_and_send(self):
        self.start('1001', '2222')
        self.start('1002', '2022')
        # Both initiations finish before either child runs, as with overlapping
        # requests. Each backup then creates and sends a real fixture archive.
        self.env['backupSchedule'].createLocalBackup.side_effect = self.create_archive
        for child in self.children:
            child['target'](*child['args'])
        ports = [cmd[cmd.index('-P') + 1] for cmd in self.commands if cmd[1] == 'scp']
        self.assertEqual(['2222', '2022'], ports)
        self.assertNotIn('/home/cyberpanel/remote_port', self.opened + self.removed)
        for transfer in ('1001', '1002'):
            content = self.local('/home/backup/transfer-' + transfer + '/backup_log').read_text()
            self.assertIn('Backups are successfully generated and received', content)

    def create_archive(self, domain, log):
        base = self.root / (Path(log).parent.name + '-backup')
        Path(str(base) + '.tar.gz').write_bytes(b'fixture archive')
        return 1, str(base)

    def test_failed_scp_preserves_archive_and_logs_stderr_in_order(self):
        self.scp_code = 1
        self.error = 'scp: dest open: No such file or directory\n'
        archive = self.root / 'backup with spaces.tar.gz'
        archive.write_bytes(b'complete local archive')
        log = self.root / 'send.log'
        with log.open('w') as stream:
            stream.write('Sending backup\n')
            sent = self.worker.sendBackup(str(archive), '192.0.2.10', '1001', stream, '2222')
        self.assertFalse(sent)
        self.assertEqual(b'complete local archive', archive.read_bytes())
        content = log.read_text()
        self.assertLess(content.index('Sending backup'), content.index(self.error))
        self.assertLess(content.index(self.error), content.index('FAILED (scp exit code 1)'))
        self.assertIn(str(archive), self.commands[-1])

    def test_successful_scp_removes_only_confirmed_archive(self):
        archive = self.root / 'complete.tar.gz'
        archive.write_bytes(b'archive')
        with (self.root / 'send.log').open('w') as stream:
            self.assertTrue(self.worker.sendBackup(str(archive), '192.0.2.10', '1001', stream))
        self.assertFalse(archive.exists())
        command = self.commands[-1]
        self.assertEqual('22', command[command.index('-P') + 1])

    def test_failed_send_does_not_claim_batch_success(self):
        self.scp_code = 1
        self.error = 'scp: write remote file: No space left on device\n'
        log = self.start()
        self.env['backupSchedule'].createLocalBackup.side_effect = self.create_archive
        child = self.children[0]
        child['target'](*child['args'])
        content = log.read_text()
        self.assertIn('Local Backup Completed', content)
        self.assertIn(self.error, content)
        self.assertIn('Backups were not fully generated or transferred', content)
        self.assertNotIn('Backups are successfully generated and received', content)
        self.assertEqual(1, len(list(log.parent.glob('*.tar.gz'))))

    def test_cli_passes_explicit_port_and_defaults_to_22(self):
        actual_argv = sys.argv
        self.addCleanup(setattr, sys, 'argv', actual_argv)
        mocked_worker = Mock()
        self.env['remoteTransferUtilities'] = mocked_worker
        for tail, port in (([], '22'), (['--port', '2222'], '2222')):
            sys.argv = ['worker', 'remoteTransfer', '--ipAddress', '192.0.2.10',
                        '--dir', '1001', '--accountsToTransfer', '/tmp/accounts'] + tail
            self.env['main']()
            mocked_worker.remoteTransfer.assert_called_with('192.0.2.10', '1001', '/tmp/accounts', port)

    def test_api_carries_each_validated_port_in_its_own_command(self):
        launch = Mock()
        ids = iter((1001, 3001, 1002, 3002))
        namespace = {
            'json': json, 'shlex': shlex, 'os': self.os, 'open': self.open,
            'csrf_exempt': lambda function: function,
            'HttpResponse': lambda value: json.loads(value),
            'get_api_admin': lambda *args: (object(), None),
            'is_safe_port': is_safe_port, 'is_safe_remote_host': is_safe_remote_host,
            'randint': lambda *args: next(ids),
            'mailUtilities': SimpleNamespace(checkHome=lambda: None),
            'virtualHostUtilities': SimpleNamespace(cyberPanel='/usr/local/CyberCP'),
            'ProcessUtilities': SimpleNamespace(popenExecutioner=launch),
        }
        load_definitions(ROOT / 'api/views.py', {'remoteTransfer'}, namespace)
        for port in ('2222', '2022'):
            request = SimpleNamespace(method='POST', body=json.dumps({
                'ipAddress': '192.0.2.10', 'accountsToTransfer': ['example.com'], 'port': port}))
            result = namespace['remoteTransfer'](request)
            self.assertEqual(1, result['transferStatus'])
            command = shlex.split(launch.call_args.args[0])
            self.assertEqual(port, command[command.index('--port') + 1])
        self.assertNotIn('/home/cyberpanel/remote_port', self.opened)


if __name__ == '__main__':
    unittest.main()
