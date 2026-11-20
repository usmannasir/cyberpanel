"""Status polling may only read the status files the panel itself creates."""
import ast
import io
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from plogical import statusUtilities
from plogical.statusUtilities import create_status_file, read_status_file, valid_status_path
from plogical.test_child_domain_conversion import load_method

ROOT = Path(__file__).resolve().parents[1]

HOSTILE_PATHS = (
    '/etc/shadow /tmp/1',
    '/tmp/1 /etc/shadow',
    '/etc/cyberpanel/mysqlPassword /home/cyberpanel/1',
    '/etc/shadow\n/tmp/1',
    '/tmp/1\n',
    ' /tmp/1',
    '/tmp/1 ',
    '/tmp/../etc/1',
    '/home/cyberpanel/../../etc/1',
    '/tmp//1',
    '/tmp/./1',
    '/tmp/1;id',
    '/tmp/$(id)',
    '/tmp/+1',
    '/tmp/-1',
    '/tmp/1_0',
    '/tmp/１２',
    '/tmp/',
    '/tmp',
    'tmp/1',
    '/var/tmp/1',
    '/home/cyberpanel/sub/1',
    '/home/cyberpanel/.my.cnf',
    '/home/cyberpanel/fakePath',
    '/usr/local/CyberCP/CyberCP/settings.py',
    '/usr/local/CyberCP/1',
    '/home/cyberpanel/' + '1' * 65,
    '',
)


class StatusPathValidationTests(unittest.TestCase):
    def test_paths_created_by_the_panel_are_accepted(self):
        for path in ('/home/cyberpanel/1000', '/home/cyberpanel/9999', '/tmp/4821',
                     '/usr/local/CyberCP/tmp/9000',
                     '/home/cyberpanel/' + str(2 ** 128 - 1)):
            self.assertTrue(valid_status_path(path), path)

    def test_reserved_status_file_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(statusUtilities, 'STATUS_DIRECTORIES', (directory,)):
                self.assertTrue(valid_status_path(create_status_file(directory)))

    def test_extra_arguments_traversal_and_foreign_files_are_rejected(self):
        for path in HOSTILE_PATHS:
            self.assertFalse(valid_status_path(path), repr(path))

    def test_values_that_are_not_text_are_rejected(self):
        for path in (None, 1234, b'/tmp/1', ['/tmp/1'], {'statusFile': '/tmp/1'}, 12.5):
            self.assertFalse(valid_status_path(path), repr(path))

    def test_backup_log_must_be_the_exact_file_of_that_domain(self):
        log = '/home/cyberpanel/example.com_rustic_backup_log'
        self.assertTrue(valid_status_path(log, 'example.com'))
        self.assertFalse(valid_status_path(log))
        self.assertFalse(valid_status_path(log, 'other.example'))
        self.assertFalse(valid_status_path('/etc/shadow ' + log, 'example.com'))
        self.assertFalse(valid_status_path('/tmp/example.com_rustic_backup_log', 'example.com'))
        for domain in ('../etc/passwd', 'a b.com', 'a/b.com', 'example..com', '.example.com',
                       '-example.com', 'example.com\n', '', None, 7):
            path = '/home/cyberpanel/%s_rustic_backup_log' % (domain,)
            self.assertFalse(valid_status_path(path, domain), repr(domain))

    def test_numeric_status_file_stays_valid_when_a_domain_is_given(self):
        self.assertTrue(valid_status_path('/home/cyberpanel/1234', 'example.com'))

    def test_panel_permission_check_applies_the_same_rule(self):
        check = load_method('plogical/acl.py', 'ACLManager', 'CheckStatusFilleLoc', {})
        self.assertEqual(1, check('/home/cyberpanel/1234'))
        self.assertEqual(1, check('/home/cyberpanel/example.com_rustic_backup_log', 'example.com'))
        for path in HOSTILE_PATHS:
            self.assertEqual(0, check(path), repr(path))
        self.assertEqual(0, check(None))


class StatusFileReadTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.directory = Path(holder.name, 'status')
        self.directory.mkdir()
        self.outside = Path(holder.name, 'secret')
        self.outside.write_text('root:$6$secret-hash\n')
        allowed = patch.object(statusUtilities, 'STATUS_DIRECTORIES', (str(self.directory),))
        allowed.start()
        self.addCleanup(allowed.stop)

    def path(self, name='1234'):
        return str(self.directory / name)

    def test_plain_status_file_is_returned(self):
        Path(self.path()).write_text('Creating website..,40\n')
        self.assertEqual('Creating website..,40\n', read_status_file(self.path()))

    def test_missing_status_file_reads_as_empty(self):
        self.assertEqual('', read_status_file(self.path()))

    def test_symbolic_link_is_refused_and_its_target_is_not_read(self):
        os.symlink(str(self.outside), self.path())
        with self.assertRaises(ValueError):
            read_status_file(self.path())

    def test_hard_link_to_another_file_is_refused(self):
        os.link(str(self.outside), self.path())
        with self.assertRaises(ValueError):
            read_status_file(self.path())

    def test_named_pipe_is_refused_without_waiting_for_a_writer(self):
        os.mkfifo(self.path())
        with self.assertRaises(ValueError):
            read_status_file(self.path())

    def test_directory_is_refused(self):
        os.mkdir(self.path())
        with self.assertRaises(ValueError):
            read_status_file(self.path())

    def test_only_the_end_of_an_oversized_file_is_returned(self):
        Path(self.path()).write_text('a' * 5000 + '\nFinished. [200]\n')
        with patch.object(statusUtilities, 'MAX_STATUS_BYTES', 64):
            text = read_status_file(self.path())
        self.assertEqual(64, len(text))
        self.assertTrue(text.endswith('Finished. [200]\n'))

    def test_invalid_path_is_refused_before_any_file_is_opened(self):
        with patch.object(statusUtilities.os, 'open') as opened:
            for path in HOSTILE_PATHS + (str(self.outside), None):
                with self.assertRaises(ValueError):
                    read_status_file(path)
        opened.assert_not_called()

    def root_helper(self, result):
        helper = Mock(return_value=result)
        module = SimpleNamespace(ProcessUtilities=SimpleNamespace(outputExecutioner=helper))
        denied = patch.object(statusUtilities, '_read_plain_file',
                              side_effect=PermissionError(13, 'Permission denied'))
        modules = patch.dict(sys.modules, {'plogical.processUtilities': module})
        denied.start()
        modules.start()
        self.addCleanup(denied.stop)
        self.addCleanup(modules.stop)
        return helper

    def test_unreadable_file_is_read_by_the_checked_root_reader(self):
        helper = self.root_helper((1, 'Installing..,10\n'))
        self.assertEqual('Installing..,10\n', read_status_file(self.path()))
        helper.assert_called_once_with(
            '/usr/local/CyberCP/bin/python -I /usr/local/CyberCP/plogical/statusUtilities.py read '
            + shlex.quote(self.path()), retRequired=True)

    def test_unexpected_root_reader_reply_reads_as_empty(self):
        self.root_helper(0)
        self.assertEqual('', read_status_file(self.path()))

    def test_root_reader_refusal_is_reported_as_invalid(self):
        self.root_helper((0, statusUtilities.REFUSED + '\n'))
        with self.assertRaises(ValueError):
            read_status_file(self.path())

    def test_root_reader_failure_reads_as_empty(self):
        self.root_helper((0, 'Connection failed'))
        self.assertEqual('', read_status_file(self.path()))


class RootReaderCommandTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.directory = Path(holder.name)
        allowed = patch.object(statusUtilities, 'STATUS_DIRECTORIES', (str(self.directory),))
        allowed.start()
        self.addCleanup(allowed.stop)

    def run_reader(self, *arguments):
        output = io.StringIO()
        with patch.object(sys, 'stdout', output), patch.object(sys, 'stderr', output):
            code = statusUtilities.main(list(arguments))
        return code, output.getvalue()

    def test_reader_prints_the_status_file(self):
        path = self.directory / '77'
        path.write_text('Restoring..,60\n')
        self.assertEqual((0, 'Restoring..,60\n'), self.run_reader('read', str(path)))

    def test_reader_prints_nothing_for_a_missing_file(self):
        self.assertEqual((0, ''), self.run_reader('read', str(self.directory / '78')))

    def test_reader_refuses_links_and_foreign_paths_without_printing_them(self):
        secret = self.directory / 'secret'
        secret.write_text('root:$6$secret-hash\n')
        link = self.directory / '79'
        os.symlink(str(secret), str(link))
        for arguments in (('read', str(link)), ('read', str(secret)), ('read', '/etc/shadow'),
                          ('read', '/etc/shadow', str(link)), ('read',), (), ('write', str(link))):
            code, output = self.run_reader(*arguments)
            self.assertEqual(3, code, arguments)
            self.assertEqual(statusUtilities.REFUSED + '\n', output, arguments)


class StatusEndpointTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.directory = Path(holder.name)
        allowed = patch.object(statusUtilities, 'STATUS_DIRECTORIES', (str(self.directory),))
        allowed.start()
        self.addCleanup(allowed.stop)
        self.root_helper = Mock()
        self.removed = Mock()
        check = load_method('plogical/acl.py', 'ACLManager', 'CheckStatusFilleLoc', {})
        self.poll = load_method('websiteFunctions/website.py', 'WebsiteManager',
                                'installWordpressStatus', dict(
            ACLManager=SimpleNamespace(CheckStatusFilleLoc=check),
            ProcessUtilities=SimpleNamespace(outputExecutioner=self.root_helper),
            HttpResponse=lambda content: SimpleNamespace(content=content.encode()),
            json=json, shlex=shlex, subprocess=SimpleNamespace(call=self.removed)))

    def status(self, path):
        return json.loads(self.poll(None, userID=7, data={'statusFile': path}).content)

    def test_hostile_status_paths_are_rejected_without_running_a_root_command(self):
        secret = self.directory / 'secret'
        secret.write_text('root:$6$secret-hash\n')
        os.symlink(str(secret), str(self.directory / '500'))
        for path in HOSTILE_PATHS + (str(secret), str(self.directory / '500'),
                                     '%s %s' % (secret, self.directory / '501')):
            result = self.status(path)
            self.assertEqual('Invalid status file.', result.get('currentStatus'), repr(path))
            self.assertEqual(1, result['abort'], repr(path))
            self.assertNotIn('secret-hash', json.dumps(result))
        self.root_helper.assert_not_called()
        self.removed.assert_not_called()

    def test_progress_is_reported_from_the_last_line(self):
        path = self.directory / '600'
        path.write_text('Starting..,0\nCreating website..,40\n')
        self.assertEqual({'abort': 0, 'installStatus': 0, 'installationProgress': '40',
                          'currentStatus': 'Creating website..'}, self.status(str(path)))
        self.root_helper.assert_not_called()

    def test_status_file_that_is_not_written_yet_keeps_polling(self):
        result = self.status(str(self.directory / '601'))
        self.assertEqual(0, result['abort'])
        self.assertEqual(0, result['installStatus'])

    def test_success_is_reported_and_the_status_file_removed(self):
        path = self.directory / '602'
        path.write_text('Working..,90\nSuccessfully Installed. [200]\n')
        result = self.status(str(path))
        self.assertEqual(1, result['installStatus'])
        self.assertEqual(1, result['abort'])
        self.removed.assert_called_once_with(['rm', '-f', str(path)])

    def test_failure_returns_the_whole_status_file(self):
        path = self.directory / '603'
        path.write_text('Working..,30\nCould not create database. [404]\n')
        result = self.status(str(path))
        self.assertEqual(1, result['abort'])
        self.assertEqual(0, result['installStatus'])
        self.assertEqual(['Working..,30', 'Could not create database. [404]'], result['error_message'])
        self.removed.assert_not_called()


class RequestSuppliedStatusPathTests(unittest.TestCase):
    """No status endpoint may hand a request value to a root file command."""
    # File -> the name its status endpoint gives the value taken from the request.
    ENDPOINTS = {'websiteFunctions/website.py': 'statusFile', 'backup/backupManager.py': 'statusFile',
                 'cloudAPI/cloudManager.py': 'statusFile', 'IncBackups/views.py': 'status',
                 'dns/views.py': 'statusfile', 'ftp/views.py': 'statusfile'}

    def test_status_endpoints_read_through_the_checked_reader(self):
        for relative, name in self.ENDPOINTS.items():
            source = (ROOT / relative).read_text()
            unsafe = re.compile(r"""cat ["']\s*\+\s*%s\b|open\(\s*%s\b""" % (name, name))
            self.assertIsNone(unsafe.search(source), relative)
            self.assertIn('read_status_file(%s' % name, source, relative)

    def test_reset_status_endpoints_refuse_a_foreign_path_before_any_root_command(self):
        for relative in ('dns/views.py', 'ftp/views.py'):
            tree = ast.parse((ROOT / relative).read_text())
            view = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == 'getresetstatus')
            root_helper = Mock()
            namespace = dict(
                json=json, redirect=Mock(), loadLoginPage=Mock(),
                HttpResponse=lambda content: SimpleNamespace(content=content.encode()),
                ACLManager=SimpleNamespace(loadedACL=lambda user: {'admin': 1}, loadErrorJson=Mock()),
                ProcessUtilities=SimpleNamespace(outputExecutioner=root_helper, executioner=root_helper))
            exec(compile(ast.Module(body=[view], type_ignores=[]), relative, 'exec'), namespace)
            for path in ('/etc/shadow /tmp/1', '/etc/shadow', '/home/cyberpanel/.my.cnf'):
                request = SimpleNamespace(session={'userID': 1},
                                          body=json.dumps({'statusfile': path}).encode())
                result = json.loads(namespace['getresetstatus'](request).content)
                self.assertEqual(1, result['abort'], (relative, path))
                self.assertEqual(0, result['installed'], (relative, path))
                self.assertEqual('Invalid status file.', result['requestStatus'], (relative, path))
            root_helper.assert_not_called()


if __name__ == '__main__':
    unittest.main()
