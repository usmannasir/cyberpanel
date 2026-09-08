"""Filesystem quota tests use fake accounts, mount records and command results."""
import json
import contextlib
import io
import os
import shlex
import stat
import subprocess
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from plogical import filesystemQuota as quota


def result(code=0, stdout='', stderr=''):
    return NS(returncode=code, stdout=stdout, stderr=stderr)


class QuotaStateTests(unittest.TestCase):
    def test_raw_active_status_and_verbose_enforcement(self):
        for filesystem, state, allowed in (
                ('ext4', 'on', True), ('ext4', 'on (enforced)', True),
                ('xfs', 'on (enforced)', True), ('xfs', 'on', False),
                ('xfs', 'on (accounting)', False), ('ext4', 'on (accounting)', False),
                ('ext4', 'off', False), ('btrfs', 'on (enforced)', False)):
            with self.subTest(filesystem=filesystem, state=state):
                output = 'user quota on /home (/dev/loop7) is ' + state + '\n'
                self.assertEqual(allowed, quota.quota_enforced(result(1, output), '/home', filesystem))

    def test_ambiguous_error_and_wrong_mount_states_are_rejected(self):
        good = 'user quota on /home (/dev/loop7) is on\n'
        for code, output, error in (
                (0, good, ''), (2, good, ''), (137, good, ''), (None, '', ''),
                (1, good, 'warning'), (1, '', 'Permission denied'),
                (1, good + good, ''), (1, good + 'unexpected\n', ''),
                (1, good.replace('/home', '/'), ''),
                (1, good.replace('user', 'group'), ''),
                (1, good.replace('on\n', 'enabled\n'), ''),
                (1, good.replace('on\n', 'on\x00\n'), '')):
            with self.subTest(code=code, output=output, error=error):
                self.assertFalse(quota.quota_enforced(result(code, output, error), '/home', 'ext4'))

    def test_run_preserves_raw_status_and_readonly_locale(self):
        with patch.object(quota.subprocess, 'run', return_value=result(1)) as run:
            self.assertEqual(1, quota._run(['/sbin/quotaon', '--print-state']).returncode)
        self.assertFalse(run.call_args.kwargs['check'])
        self.assertEqual(30, run.call_args.kwargs['timeout'])
        for name in ('LC_ALL', 'LANG', 'LANGUAGE'):
            self.assertEqual('C', run.call_args.kwargs['env'][name])


class FilesystemQuotaTests(unittest.TestCase):
    def setUp(self):
        self.site = NS(pk=1, domain='one.test', externalApp='one', package_id=3)
        self.other = NS(pk=2, domain='other.test', externalApp='other', package_id=4)
        self.package = NS(pk=3, diskSpace=50, inodeLimit=70, enforceDiskLimits=1)
        self.accounts = {'one': NS(pw_name='one', pw_uid=2101),
                         'other': NS(pw_name='other', pw_uid=2102)}
        self.stats = NS(st_mode=stat.S_IFDIR | 0o755, st_uid=2101, st_ino=55, st_dev=9)
        self.sites = [self.site, self.other]
        self.mount = {'target': '/home', 'source': '/dev/loop7', 'fstype': 'ext4', 'options': 'rw,usrquota'}
        self.tmpfs = []
        self.device = NS(st_mode=stat.S_IFBLK | 0o600, st_rdev=9)
        actual_stat = os.stat
        def metadata(path):
            path = os.fspath(path)
            if path.startswith('/dev/loop') or path == '/dev/disk/alias':
                return self.device
            if path == 'tmpfs':
                raise FileNotFoundError('absent relative source')
            if path in ('/tmp', '/dev/shm', '/run'):
                return NS(st_mode=stat.S_IFDIR | 0o1777, st_dev={'/tmp': 20, '/dev/shm': 21, '/run': 22}[path])
            if path == '/home' or path.startswith('/home/'):
                return self.stats
            return actual_stat(path)
        self.metadata = metadata
        def command(arguments):
            if arguments[0].endswith('/findmnt'):
                return result(stdout=json.dumps({'filesystems': [self.mount] + (self.tmpfs if '--list' in arguments else [])}))
            if arguments[0].endswith('/quotaon'):
                return result(1, 'user quota on %s (%s) is on (enforced)\n' % (self.mount['target'], self.mount['source']))
            if arguments[0].endswith('/setquota'):
                return result()
            raise AssertionError('Unexpected command: ' + repr(arguments))
        self.command = Mock(side_effect=command)
        patches = [
            patch.object(quota, '_run', self.command),
            patch.object(quota, '_tool', side_effect=lambda name: '/sbin/' + name),
            patch.object(quota, '_sites', side_effect=lambda: self.sites),
            patch.object(quota, '_package', return_value=self.package),
            patch.object(quota.pwd, 'getpwnam', side_effect=lambda name: self.accounts[name]),
            patch.object(quota.pwd, 'getpwuid', side_effect=lambda uid: next(a for a in self.accounts.values() if a.pw_uid == uid)),
            patch.object(quota.pwd, 'getpwall', side_effect=lambda: list(self.accounts.values())),
            patch.object(quota.os, 'stat', side_effect=metadata),
            patch.object(quota.os.path, 'realpath', side_effect=lambda value, **kwargs: value),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def plan(self):
        return quota.prepare({'package_id': 3, 'disk_space': self.package.diskSpace,
                              'inode_limit': self.package.inodeLimit, 'site_ids': None})

    def quota_calls(self):
        return [call.args[0] for call in self.command.call_args_list
                if call.args[0][0].endswith('/setquota')]

    def test_package_selection_and_actual_mount_both_dimensions(self):
        plan = self.plan()
        self.assertEqual([1], [site['site_id'] for site in plan['sites']])
        self.assertEqual([], self.quota_calls())
        self.assertEqual(['one.test'], quota.apply(plan)['applied'])
        self.assertEqual([['/sbin/setquota', '-u', '2101', '51200', '51200', '70', '70', '/home']], self.quota_calls())
        state_calls = [c.args[0] for c in self.command.call_args_list if c.args[0][0].endswith('/quotaon')]
        self.assertTrue(all(c == ['/sbin/quotaon', '--print-state', '--verbose', '--user', '--', '/home'] for c in state_calls))

    def test_explicit_zero_and_xfs(self):
        self.package.diskSpace = self.package.inodeLimit = 0
        self.mount.update(fstype='xfs', options='rw,uquota')
        quota.apply(self.plan())
        self.assertEqual(['0', '0', '0', '0'], self.quota_calls()[0][3:7])

    def test_unsupported_readonly_and_accounting_mounts_do_not_write(self):
        for filesystem, options in (('btrfs', 'rw'), ('ext4', 'ro,usrquota'),
                                    ('xfs', 'rw,uqnoenforce'), ('ext4', 'rw,noquota')):
            with self.subTest(filesystem=filesystem, options=options):
                self.mount.update(fstype=filesystem, options=options)
                with self.assertRaises(quota.QuotaError):
                    self.plan()
                self.assertEqual([], self.quota_calls())

    def test_disabled_enforcement_and_unknown_findmnt_output_do_not_write(self):
        normal = self.command.side_effect
        for response in (result(0, 'user quota on /home (/dev/loop7) is off\n'),
                         result(1, 'user quota on /home (/dev/loop7) is on (accounting)\n')):
            with patch.object(quota, '_run', side_effect=lambda args: response if args[0].endswith('/quotaon') else normal(args)):
                with self.assertRaises(quota.QuotaError):
                    self.plan()
        with patch.object(quota, '_run', return_value=result(stdout='{"filesystems": []}')):
            with self.assertRaises(quota.QuotaError):
                self.plan()
        self.assertEqual([], self.quota_calls())

    def test_missing_tool_and_timeout_reject_before_mutation(self):
        with patch.object(quota, '_tool', side_effect=quota.QuotaError('missing tool')):
            with self.assertRaises(quota.QuotaError):
                self.plan()
        with patch.object(quota, '_run', side_effect=subprocess.TimeoutExpired('findmnt', 30)):
            with self.assertRaises(subprocess.TimeoutExpired):
                self.plan()
        self.assertEqual([], self.quota_calls())

    def test_shared_top_level_user_even_same_package_is_rejected(self):
        self.other.externalApp = 'one'
        self.other.package_id = 3
        with self.assertRaisesRegex(quota.QuotaError, 'shared'):
            self.plan()
        self.assertEqual([], self.quota_calls())

    def test_alias_root_and_wrong_home_owner_are_rejected(self):
        self.accounts['alias'] = NS(pw_name='alias', pw_uid=2101)
        with self.assertRaisesRegex(quota.QuotaError, 'dedicated'):
            self.plan()
        del self.accounts['alias']
        self.accounts['one'].pw_uid = 0
        with self.assertRaisesRegex(quota.QuotaError, 'non-root'):
            self.plan()
        self.accounts['one'].pw_uid = 2101
        self.stats.st_uid = 2102
        with self.assertRaisesRegex(quota.QuotaError, 'ownership'):
            self.plan()
        self.assertEqual([], self.quota_calls())

    def test_symlink_home_is_rejected(self):
        with patch.object(quota.os.path, 'realpath', return_value='/home/other.test'):
            with self.assertRaisesRegex(quota.QuotaError, 'symbolic link'):
                self.plan()

    def test_identity_mount_and_membership_changes_reject_entire_set(self):
        for change in ('uid', 'mount', 'member', 'policy'):
            with self.subTest(change=change):
                plan = self.plan()
                if change == 'uid':
                    self.accounts['one'].pw_uid = self.stats.st_uid = 2103
                elif change == 'mount':
                    self.stats.st_dev = 10
                elif change == 'member':
                    self.site.package_id = 4
                else:
                    self.package.diskSpace = 99
                with self.assertRaises(quota.QuotaError):
                    quota.apply(plan)
                self.assertEqual([], self.quota_calls())
                self.accounts['one'].pw_uid = self.stats.st_uid = 2101
                self.stats.st_dev, self.site.package_id, self.package.diskSpace = 9, 3, 50

    def test_failure_is_partial_and_identical_retry_reapplies(self):
        plan = self.plan()
        normal = self.command.side_effect
        def fail_setquota(arguments):
            return result(1, stderr='Permission denied') if arguments[0].endswith('/setquota') else normal(arguments)
        self.command.side_effect = fail_setquota
        with self.assertRaisesRegex(quota.QuotaError, '0 of 1.*one.test'):
            quota.apply(plan)
        self.command.side_effect = normal
        self.assertEqual(['one.test'], quota.apply(self.plan())['applied'])
        self.assertEqual(2, len(self.quota_calls()))

    def test_two_target_partial_failure_names_failed_site(self):
        self.other.package_id = 3
        normal_stat = self.metadata
        def metadata(path):
            if path == '/home/other.test':
                return NS(st_mode=stat.S_IFDIR | 0o755, st_uid=2102, st_ino=56, st_dev=9)
            return normal_stat(path)
        normal_command = self.command.side_effect
        def fail_second(arguments):
            if arguments[:3] == ['/sbin/setquota', '-u', '2102']:
                return result(1)
            return normal_command(arguments)
        with patch.object(quota.os, 'stat', side_effect=metadata):
            plan = self.plan()
            self.command.side_effect = fail_second
            with self.assertRaisesRegex(quota.QuotaError, '1 of 2.*other.test'):
                quota.apply(plan)
        self.assertEqual(2, len(self.quota_calls()))

    def warning_topology(self):
        self.tmpfs = [{'target': path, 'source': 'tmpfs', 'fstype': 'tmpfs',
                       'options': 'rw,usrquota' if path != '/run' else 'rw,nosuid'}
                      for path in ('/tmp', '/dev/shm', '/run')]

    def warning_commands(self, setter_code=0, setter_extra=''):
        normal = self.command.side_effect
        def command(arguments):
            response = normal(arguments)
            name = arguments[0].rsplit('/', 1)[-1]
            if name in ('quotaon', 'setquota'):
                response.stderr = (name + ': Cannot stat() mounted device tmpfs: No such file or directory\n') * 2
            if name == 'setquota':
                response.returncode = setter_code
                response.stderr += setter_extra
            return response
        self.command.side_effect = command

    def test_preserved_real_tmpfs_diagnostics_allow_exact_target_and_setter(self):
        self.site.domain = 'quota-20260908.test'
        self.mount.update(target='/home/quota-20260908.test', source='/dev/loop0')
        self.warning_topology()
        self.warning_commands()
        plan = self.plan()
        warning = plan['sites'][0]['mount']['diagnostics'][0]
        self.assertEqual('quotaon: Cannot stat() mounted device tmpfs: No such file or directory\n' * 2, warning['stderr'])
        self.assertEqual(['/dev/shm', '/tmp'], warning['mounts'])
        applied = quota.apply(plan)
        self.assertEqual(['quota-20260908.test'], applied['applied'])
        self.assertEqual('setquota', applied['diagnostics'][0]['tool'])
        self.assertEqual(1, len(self.quota_calls()))

    def test_quota_device_alias_matches_actual_block_device_only(self):
        normal = self.command.side_effect
        def alias(arguments):
            response = normal(arguments)
            if arguments[0].endswith('/quotaon'):
                response.stdout = response.stdout.replace('/dev/loop7', '/dev/disk/alias')
            return response
        self.command.side_effect = alias
        self.assertEqual(9, self.plan()['sites'][0]['mount']['device'])
        with patch.object(quota.os, 'stat', side_effect=lambda path: NS(st_mode=stat.S_IFBLK, st_rdev=99) if path == '/dev/disk/alias' else self.metadata(path)):
            with self.assertRaisesRegex(quota.QuotaError, 'enforcement'):
                self.plan()
        self.device.st_rdev = 99
        with self.assertRaises(quota.QuotaError):
            self.plan()
        self.assertEqual([], self.quota_calls())

    def test_unknown_warning_wrong_count_or_prefix_is_refused(self):
        self.warning_topology()
        normal = self.command.side_effect
        line = 'quotaon: Cannot stat() mounted device tmpfs: No such file or directory\n'
        for stderr in (line, line * 3, line * 2 + 'Permission denied\n',
                       line.replace('tmpfs', '/dev/loop7') * 2,
                       line.replace('quotaon:', 'setquota:') * 2,
                       line.replace('No such file or directory', 'Permission denied') * 2,
                       (line * 2).rstrip('\n')):
            with self.subTest(stderr=stderr):
                def response(arguments):
                    value = normal(arguments)
                    if arguments[0].endswith('/quotaon'):
                        value.stderr = stderr
                    return value
                self.command.side_effect = response
                with self.assertRaisesRegex(quota.QuotaError, 'diagnostic'):
                    self.plan()
        self.assertEqual([], self.quota_calls())

    def test_ambiguous_tmpfs_context_is_refused(self):
        for change in ('duplicate', 'type', 'quota', 'device', 'relative_source'):
            with self.subTest(change=change):
                self.warning_topology()
                if change == 'duplicate':
                    self.tmpfs.append(dict(self.tmpfs[0]))
                elif change == 'type':
                    self.tmpfs[0]['fstype'] = 'ext4'
                elif change == 'quota':
                    self.tmpfs[0]['options'] = 'rw,grpquota'
                original = self.metadata
                def metadata(path):
                    if change == 'device' and path == '/tmp':
                        return NS(st_mode=stat.S_IFDIR, st_dev=9)
                    if change == 'relative_source' and path == 'tmpfs':
                        return NS(st_mode=stat.S_IFREG)
                    return original(path)
                with patch.object(quota.os, 'stat', side_effect=metadata):
                    with self.assertRaisesRegex(quota.QuotaError, 'context'):
                        self.plan()
        self.assertEqual([], self.quota_calls())

    def test_context_change_during_quotaon_refuses_before_setter(self):
        self.warning_topology()
        normal = self.command.side_effect
        def changing(arguments):
            value = normal(arguments)
            if arguments[0].endswith('/quotaon'):
                self.tmpfs[0]['options'] = 'rw'
            return value
        self.command.side_effect = changing
        with self.assertRaisesRegex(quota.QuotaError, 'context changed'):
            self.plan()
        self.assertEqual([], self.quota_calls())

    def test_nonzero_or_unknown_setter_warning_never_reports_success(self):
        for code, extra in ((1, ''), (0, 'unrelated warning\n')):
            with self.subTest(code=code, extra=extra):
                self.warning_topology()
                normal = self.command.side_effect
                self.warning_commands(code, extra)
                with self.assertRaisesRegex(quota.QuotaError, '0 of 1'):
                    quota.apply(self.plan())
                self.command.side_effect = normal
        self.assertEqual(2, len(self.quota_calls()))

    def test_context_change_after_setter_reports_unverified_partial_outcome(self):
        self.warning_topology()
        self.warning_commands()
        normal = self.command.side_effect
        def changing(arguments):
            value = normal(arguments)
            if arguments[0].endswith('/setquota'):
                self.tmpfs[0]['options'] = 'rw'
            return value
        self.command.side_effect = changing
        with self.assertRaisesRegex(quota.QuotaError, '0 of 1.*context changed'):
            quota.apply(self.plan())
        self.assertEqual(1, len(self.quota_calls()))

    def test_empty_package_needs_no_quota_tools_or_commands(self):
        self.site.package_id = 4
        with patch.object(quota, '_tool', side_effect=AssertionError('no quota tools needed')):
            self.assertEqual([], quota.apply(self.plan())['applied'])
        self.command.assert_not_called()

    def test_wrapper_cli_roundtrip_preserves_plan_and_raw_command_status(self):
        commands = []
        def transport(command, **options):
            commands.append(command)
            arguments = shlex.split(command)[1:]
            output = io.StringIO()
            with patch.object(sys, 'argv', arguments), patch.object(quota.os, 'geteuid', return_value=0), contextlib.redirect_stdout(output):
                status = quota.main()
            return (1 if status == 0 else 0), output.getvalue()
        modules = {'plogical.processUtilities': NS(ProcessUtilities=NS(outputExecutioner=transport)),
                   'django': NS(setup=lambda: None)}
        with patch.dict(sys.modules, modules):
            plan = quota.prepare_package_quota(self.package)
            self.assertEqual(['one.test'], quota.apply_quota_plan(plan)['applied'])
        self.assertEqual(['prepare', 'apply'], [shlex.split(command)[2] for command in commands])
        self.assertEqual(1, len(self.quota_calls()))

    def test_limit_rejects_lossy_invalid_and_overflow_values(self):
        for value in (-1, 1.5, True, '1.5', '', None, 2147483648):
            with self.subTest(value=value), self.assertRaises(quota.QuotaError):
                quota.limit(value)
        self.assertEqual(0, quota.limit('0'))


class QuotaTransportTests(unittest.TestCase):
    def test_checked_transport_rejects_empty_ambiguous_and_failed_output(self):
        success = 'QUOTA_RESULT={"ok":true,"plan":{}}\n'
        for response in (None, (0, ''), (1, ''), (1, success + success),
                         (0, 'QUOTA_RESULT={"ok":false,"error":"enforcement off"}\n')):
            with self.subTest(response=response), patch('plogical.processUtilities.ProcessUtilities.outputExecutioner', return_value=response):
                with self.assertRaises(quota.QuotaError):
                    quota._transport('prepare', {})

    def test_helper_success_uses_existing_checked_transport(self):
        with patch('plogical.processUtilities.ProcessUtilities.outputExecutioner', return_value=(1, 'QUOTA_RESULT={"ok":true,"plan":{"sites":[]}}\n')) as transport:
            self.assertEqual({'sites': []}, quota._transport('prepare', {'package_id': 3}))
        self.assertEqual({'user': 'root', 'shell': False, 'retRequired': True}, transport.call_args.kwargs)

    def test_nonroot_transport_keeps_explicit_root_for_domain_substrings(self):
        from plogical.processUtilities import ProcessUtilities
        for domain in ('ordinary.example', 'sudo.example', 'exporter.example'):
            with self.subTest(domain=domain):
                sock = Mock()
                sock.recv.side_effect = [b'QUOTA_RESULT={"ok":true}\n\x00', b'']
                with patch('plogical.processUtilities.getpass.getuser', return_value='lscpd'), \
                        patch.object(ProcessUtilities, 'setupUDSConnection', return_value=[sock, 'None']), \
                        patch.object(ProcessUtilities, 'token', 'quota-test-token'):
                    self.assertTrue(quota._transport('apply', {'sites': [{'domain': domain}]})['ok'])
                wire = sock.sendall.call_args.args[0].decode()
                self.assertTrue(wire.startswith('quota-test-token-u root '), wire)
                self.assertIn(domain, wire)
