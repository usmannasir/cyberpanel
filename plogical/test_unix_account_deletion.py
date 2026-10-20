"""Actual deletion methods with all accounts, models, files and processes isolated."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace as NS
import types
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent


class UnixAccountDeletionTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.logs = []
        self.user_exists = True
        self.group_exists = True
        self.user_remains = False
        self.group_remains = False
        self.user_removes_group = False
        self.user_lookup_error = None
        self.group_lookup_error = None
        self.normal_result = 1
        self.server = 1
        self.distro = 3
        self.child_node = False
        self.row_exists = True
        self.username = 'fixtureunixonly'
        self.user_command = 'deluser ' + self.username

        def normal(command, *args):
            self.events.append(command)
            if command.startswith(('deluser ', 'userdel ')) and not self.user_remains:
                self.user_exists = False
                if self.user_removes_group:
                    self.group_exists = False
            if command.startswith('groupdel ') and not self.group_remains:
                self.group_exists = False
            return self.normal_result

        self.process = NS(OLS=1, centos=1, cent8=2, debugPath='fixture-absent-debug',
                          decideServer=lambda: self.server, decideDistro=lambda: self.distro,
                          normalExecutioner=mock.Mock(side_effect=normal))
        # Execute the real root transport: its unconditional return 1 is part
        # of the regression, not a test substitute for checking cleanup.
        process_tree = ast.parse((HERE / 'processUtilities.py').read_text())
        process_method = next(n for n in ast.walk(process_tree)
                              if isinstance(n, ast.FunctionDef) and n.name == 'executioner')
        process_scope = {'ProcessUtilities': self.process, 'getpass': NS(getuser=lambda: 'root'),
                         'os': NS(path=NS(exists=lambda p: False)),
                         'logging': NS(writeToFile=self.logs.append)}
        exec(compile(ast.Module(body=[process_method], type_ignores=[]), 'process-fixture', 'exec'), process_scope)
        self.process.executioner = process_scope['executioner'].__func__

        def user_lookup(name):
            self.assertEqual(self.username, name)
            if self.user_lookup_error:
                raise self.user_lookup_error
            if not self.user_exists:
                raise KeyError(name)
            return NS(pw_name=name, pw_uid=1011, pw_gid=1011, pw_dir='/home/fixture.test')

        def group_lookup(name):
            self.assertEqual(self.username, name)
            if self.group_lookup_error:
                raise self.group_lookup_error
            if not self.group_exists:
                raise KeyError(name)
            return NS(gr_name=name, gr_gid=1011)

        def delete_row():
            self.events.append('website-row-delete')
            self.row_exists = False

        self.site = NS(externalApp=self.username, childdomains_set=NS(all=lambda: [NS(domain='child.fixture.test')]),
                       delete=delete_row)
        self.resource_module = types.ModuleType('plogical.resourceLimits')
        self.resource_module.resource_manager = NS(remove_user_limits=lambda user: self.events.append('resource-limits'))
        scope = {
            'ProcessUtilities': self.process, 'pwd': NS(getpwnam=mock.Mock(side_effect=user_lookup)),
            'grp': NS(getgrnam=mock.Mock(side_effect=group_lookup)),
            'Websites': NS(objects=NS(count=lambda: 1, get=lambda **kwargs: self.site)),
            'ChildDomains': NS(objects=NS(count=lambda: 1)),
            'Databases': NS(objects=NS(filter=lambda **kwargs: [NS(dbName='fixturedb', dbUser='fixturedbuser')])),
            'WPSites': NS(objects=NS(filter=lambda **kwargs: [])),
            'ACLManager': NS(FindIfChild=lambda: int(self.child_node)),
            'mysqlUtilities': NS(deleteDatabase=lambda *args: self.events.append('database-delete') or 1),
            'DNS': NS(deleteDNSZone=lambda domain: self.events.append('dns-delete')),
            'installUtilities': NS(installUtilities=NS(reStartLiteSpeed=lambda: self.events.append('restart'))),
            'os': NS(path=NS(exists=lambda path: False, isabs=os.path.isabs), listdir=lambda path: []),
            'shutil': NS(rmtree=mock.Mock(side_effect=AssertionError('No filesystem deletion allowed'))),
            'subprocess': NS(call=lambda argv: self.events.append('mail-directory-delete') or 0),
            'shlex': NS(split=lambda command: command.split()),
            'logging': NS(CyberCPLogFileWriter=NS(writeToFile=self.logs.append)),
        }
        source = Path(os.environ.get('VHOST_FIXTURE_SOURCE', str(HERE / 'vhost.py')))
        tree = ast.parse(source.read_text())
        original_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'vhost')
        methods = [n for n in original_class.body if isinstance(n, ast.FunctionDef)
                   and n.name in ('_wait_for_php_workers', '_delete_unix_account', 'deleteVirtualHostConfigurations')]
        fixture_class = ast.ClassDef(name='vhost', bases=[], keywords=[], body=methods, decorator_list=[])
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fixture_class], type_ignores=[])), str(source), 'exec'), scope)
        self.vhost = scope['vhost']
        self.vhost.redisConf = 'fixture-absent-redis'
        self.vhost.deleteCoreConf = lambda domain, count: self.events.append('conf-delete:' + domain) or 1
        self.scope = scope

    def helper(self):
        return self.vhost._delete_unix_account(self.username, self.user_command)

    def deletion(self):
        with mock.patch.dict('sys.modules', {'plogical.resourceLimits': self.resource_module}):
            return self.vhost.deleteVirtualHostConfigurations('fixture.test')

    def test_helper_success_requires_user_then_group_absence(self):
        self.assertEqual(1, self.helper())
        self.assertEqual([self.user_command, 'groupdel ' + self.username], self.events)
        self.assertFalse(self.user_exists or self.group_exists)

    def test_real_root_executor_discards_nonzero_normal_result(self):
        self.normal_result = 0
        self.user_remains = True
        self.assertEqual(1, self.process.executioner(self.user_command))
        self.assertTrue(self.user_exists)

    def test_residual_user_rejects_even_with_successful_transport(self):
        self.user_remains = True
        with self.assertRaisesRegex(RuntimeError, 'Unix user .* remains'):
            self.helper()
        self.assertEqual([self.user_command], self.events)

    def test_nonzero_normal_result_cannot_hide_residual_user(self):
        self.normal_result = 0
        self.user_remains = True
        with self.assertRaisesRegex(RuntimeError, 'Unix user .* remains'):
            self.helper()
        self.assertEqual([self.user_command], self.events)

    def test_raw_zero_transport_cannot_hide_residual_user(self):
        self.process.executioner = lambda command: self.events.append(command) or 0
        with self.assertRaisesRegex(RuntimeError, 'Unix user .* remains'):
            self.helper()
        self.assertEqual([self.user_command], self.events)

    def test_residual_group_rejects_after_user_is_absent(self):
        self.group_remains = True
        with self.assertRaisesRegex(RuntimeError, 'Unix group .* remains'):
            self.helper()
        self.assertFalse(self.user_exists)
        self.assertEqual([self.user_command, 'groupdel ' + self.username], self.events)

    def test_already_absent_user_and_group_skip_commands(self):
        self.user_exists = self.group_exists = False
        self.assertEqual(1, self.helper())
        self.assertEqual([], self.events)

    def test_absent_user_only_removes_existing_group(self):
        self.user_exists = False
        self.assertEqual(1, self.helper())
        self.assertEqual(['groupdel ' + self.username], self.events)

    def test_absent_group_skips_groupdel(self):
        self.group_exists = False
        self.assertEqual(1, self.helper())
        self.assertEqual([self.user_command], self.events)

    def test_deluser_already_removed_private_group(self):
        self.user_removes_group = True
        self.assertEqual(1, self.helper())
        self.assertEqual([self.user_command], self.events)

    def test_user_lookup_failure_does_not_run_command(self):
        self.user_lookup_error = OSError('fixture lookup failure')
        with self.assertRaises(OSError):
            self.helper()
        self.assertEqual([], self.events)

    def test_group_lookup_failure_is_not_absence(self):
        self.user_exists = False
        self.group_lookup_error = OSError('fixture lookup failure')
        with self.assertRaises(OSError):
            self.helper()
        self.assertEqual([], self.events)

    def test_post_command_lookup_error_does_not_report_success(self):
        lookup = self.scope['pwd'].getpwnam.side_effect
        def after_command(name):
            if self.events:
                raise OSError('fixture lookup failure')
            return lookup(name)
        self.scope['pwd'].getpwnam.side_effect = after_command
        with self.assertRaises(OSError):
            self.helper()
        self.assertEqual([self.user_command], self.events)

    def test_command_exception_stops_group_deletion(self):
        self.process.executioner = mock.Mock(side_effect=OSError('fixture launch failure'))
        with self.assertRaises(OSError):
            self.helper()
        self.process.executioner.assert_called_once_with(self.user_command)

    def test_ols_residual_user_cannot_report_complete(self):
        self.user_remains = True
        self.normal_result = 0
        self.assertEqual(0, self.deletion())
        self.assertFalse(self.row_exists)
        self.assertTrue(self.user_exists)
        self.assertNotIn('groupdel ' + self.username, self.events)
        self.assertTrue(any('Unix user' in line for line in self.logs))

    def test_lsws_residual_user_cannot_report_complete(self):
        self.server = 2
        self.user_remains = True
        self.normal_result = 0
        self.assertEqual(0, self.deletion())
        self.assertFalse(self.row_exists)
        self.assertTrue(self.user_exists)
        self.assertNotIn('groupdel ' + self.username, self.events)

    def test_both_servers_preserve_commands_and_existing_deletion_order(self):
        for server in (1, 2):
            for distro in (1, 2, 3):
                with self.subTest(server=server, distro=distro):
                    self.events.clear()
                    self.server, self.distro = server, distro
                    self.user_exists = self.group_exists = self.row_exists = True
                    self.assertEqual(1, self.deletion())
                    command = ('userdel -r -f ' if distro in (1, 2) else 'deluser ') + self.username
                    expected = ['conf-delete:fixture.test', 'conf-delete:child.fixture.test',
                                'database-delete', 'website-row-delete', 'dns-delete', 'restart',
                                'mail-directory-delete', command, 'groupdel ' + self.username]
                    positions = [self.events.index(event) for event in expected]
                    self.assertEqual(sorted(positions), positions)
                    if server == 2:
                        self.assertLess(self.events.index('/usr/sbin/cagefsctl --disable ' + self.username),
                                        self.events.index('conf-delete:child.fixture.test'))
                    self.assertFalse(self.row_exists or self.user_exists or self.group_exists)

    def test_child_node_still_retains_shared_metadata(self):
        for server in (1, 2):
            with self.subTest(server=server):
                self.events.clear()
                self.server = server
                self.child_node = True
                self.user_exists = self.group_exists = True
                self.assertEqual(1, self.deletion())
                self.assertTrue(self.row_exists)
                self.assertNotIn('website-row-delete', self.events)
                self.assertNotIn('dns-delete', self.events)
                self.assertNotIn('database-delete', self.events)


if __name__ == '__main__':
    unittest.main()
