import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from plogical import olsServiceControl as control


@unittest.skipUnless(os.geteuid() == 0, 'requires root-owned policy fixture')
class RecoveredJammyControllerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / 'bin').mkdir()
        (self.root / 'modules').mkdir()
        self.files = ('bin/openlitespeed', 'modules/cyberpanel_ols.so', 'modules/mod_security.so')
        self.hashes = {b'reviewed-controller': control.REVIEWED_JAMMY_CONTROLLER,
                       b'vendor-controller': next(iter(control.CONTROLLER_HASHES)),
                       b'environment': control.ENV_HASH}
        for name, checksum in zip(self.files, control.RECOVERED_JAMMY_BUNDLE):
            content = name.encode()
            self.hashes[content] = checksum
            (self.root / name).write_bytes(content)
        (self.root / 'bin/lswsctrl.open').write_bytes(b'reviewed-controller')
        (self.root / 'bin/lswsctrl').symlink_to('lswsctrl.open')
        (self.root / 'bin/lsws_env').write_bytes(b'environment')
        policy = self.root / control.RECOVERY_POLICY_NAME
        policy.write_bytes(control.RECOVERY_POLICY_BYTES)
        policy.chmod(0o600)
        for name, value in [('jammy_platform', lambda: True),
                            ('digest', lambda path: self.hashes.get(Path(path).read_bytes(), 'unknown'))]:
            patcher = patch.object(control, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_recovered_grant_is_explicit_and_needs_no_standalone_recovery_modules(self):
        service = control.OLSService(self.root)
        with self.assertRaisesRegex(RuntimeError, 'controller'):
            service.controller()
        with patch.dict('sys.modules', {'olsStockClassifier': None, 'installBundle': None}):
            service.authorize_recovered_jammy_controller()
            service.controller()
        self.assertEqual(service.unit, 'lshttpd.service')
        with self.assertRaises(RuntimeError):
            control.OLSService(self.root).controller()

    def test_reviewed_controller_grant_requires_the_recovery_policy(self):
        (self.root / control.RECOVERY_POLICY_NAME).unlink()
        with self.assertRaisesRegex(RuntimeError, 'policy'):
            control.OLSService(self.root).authorize_recovered_jammy_controller()

    def test_exact_bundle_os_and_manager_are_required(self):
        for name in self.files:
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(b'unknown')
            with self.assertRaisesRegex(RuntimeError, 'exact recovered Jammy bundle'):
                control.OLSService(self.root).authorize_recovered_jammy_controller()
            path.write_bytes(original)
        with patch.object(control, 'jammy_platform', return_value=False), self.assertRaises(RuntimeError):
            control.OLSService(self.root).authorize_recovered_jammy_controller()
        with self.assertRaisesRegex(RuntimeError, 'requires lshttpd.service'):
            control.OLSService(self.root, unit='lsws.service').authorize_recovered_jammy_controller()

    def test_grant_rechecks_bundle_environment_and_controller_identity(self):
        for name in (*self.files, 'bin/lsws_env', 'bin/lswsctrl.open'):
            service = control.OLSService(self.root)
            service.authorize_recovered_jammy_controller()
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(b'changed')
            with self.assertRaises(RuntimeError):
                service.controller()
            path.write_bytes(original)
            if name == 'bin/lswsctrl.open':
                with self.assertRaises(RuntimeError):
                    service.controller()
            else:
                service.controller()

    def test_grant_binds_the_command_symlink_and_not_only_its_old_target(self):
        service = control.OLSService(self.root)
        service.authorize_recovered_jammy_controller()
        replacement = self.root / 'bin/replacement'
        replacement.write_bytes(b'reviewed-controller')
        command = self.root / 'bin/lswsctrl'
        command.unlink()
        command.symlink_to('replacement')
        with self.assertRaises(RuntimeError):
            service.controller()
        with self.assertRaisesRegex(RuntimeError, 'command path is not pinned'):
            control.OLSService(self.root).authorize_recovered_jammy_controller()
        command.unlink()
        command.symlink_to('lswsctrl.open')
        with self.assertRaises(RuntimeError):
            service.controller()
        control.OLSService(self.root).authorize_recovered_jammy_controller()

    def test_standard_controller_does_not_need_recovered_bundle(self):
        (self.root / control.RECOVERY_POLICY_NAME).unlink()
        (self.root / 'bin/lswsctrl.open').write_bytes(b'vendor-controller')
        (self.root / self.files[0]).write_bytes(b'other-core')
        service = control.OLSService(self.root)
        with patch.object(control, 'jammy_platform', side_effect=AssertionError('unneeded platform check')):
            service.authorize_recovered_jammy_controller()
            service.controller()
        self.assertIsNone(service.unit)


@unittest.skipUnless(os.geteuid() == 0, 'requires root-owned policy fixture')
class StockRecoveryPolicyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / 'bin').mkdir()
        (self.root / 'bin/openlitespeed').write_bytes(b'policy-aware native core fixture')
        self.policy = self.root / control.RECOVERY_POLICY_NAME
        self.service = control.OLSService(self.root)
        for name, value in [('jammy_platform', lambda: True),
                            ('digest', lambda path: control.RECOVERED_JAMMY_BUNDLE[0])]:
            patcher = patch.object(control, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def create_policy(self):
        self.policy.write_bytes(control.RECOVERY_POLICY_BYTES)
        self.policy.chmod(0o600)

    def test_absent_policy_needs_no_core_hash_but_later_appearance_refuses(self):
        with patch.object(control, 'digest', side_effect=AssertionError('must not read absent policy core')):
            self.assertIsNone(self.service.verify_stock_recovery_policy())
        self.create_policy()
        with self.assertRaisesRegex(RuntimeError, 'appeared or disappeared'):
            self.service.verify_stock_recovery_policy()

    def test_exact_policy_binds_identity_and_requires_supported_selected_core(self):
        self.create_policy()
        identity = self.service.verify_stock_recovery_policy()
        self.assertTrue(identity)
        self.assertEqual(self.service.verify_stock_recovery_policy(control.RECOVERED_JAMMY_BUNDLE[0]), identity)
        with self.assertRaisesRegex(RuntimeError, 'does not support'):
            self.service.verify_stock_recovery_policy('0' * 64)
        self.policy.unlink()
        with self.assertRaisesRegex(RuntimeError, 'appeared or disappeared'):
            self.service.verify_stock_recovery_policy()

    def test_invalid_file_shapes_and_content_refuse(self):
        for mutation in ('permissions', 'owner', 'content', 'hardlink', 'symlink', 'fifo'):
            with self.subTest(mutation=mutation):
                self.create_policy()
                extra = self.root / 'extra'
                if mutation == 'permissions': self.policy.chmod(0o644)
                if mutation == 'owner': os.chown(self.policy, 1, 0)
                if mutation == 'content': self.policy.write_bytes(b'AUTO_SSL=enabled\n')
                if mutation == 'hardlink': os.link(self.policy, extra)
                if mutation == 'symlink':
                    self.policy.rename(extra)
                    self.policy.symlink_to(extra)
                if mutation == 'fifo':
                    self.policy.unlink()
                    os.mkfifo(self.policy, 0o600)
                with self.assertRaises(RuntimeError):
                    control.OLSService(self.root).verify_stock_recovery_policy()
                self.policy.unlink()
                if extra.exists(): extra.unlink()


class NativeDrainingStateTests(unittest.TestCase):
    """Exercise the actual /proc classifier when the stopped master exits first."""
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.binary = self.root / 'bin/openlitespeed'
        self.binary.parent.mkdir()
        self.binary.write_bytes(b'installed core fixture')
        self.proc = self.root / 'proc'
        self.proc.mkdir()
        self.worker(124, '22')
        self.service = control.OLSService(self.root, self.proc)
        self.service.draining = (123, '11', 'lshttpd.service')
        self.service._draining_processes = {123: '11', 124: '22'}
        for target, value in [('controller', None), ('verify_unit_claims', None), ('systemd', None)]:
            patcher = patch.object(self.service, target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(control, 'run', return_value=SimpleNamespace(stdout='OLS is running with PID 123.'))
        patcher.start()
        self.addCleanup(patcher.stop)

    def worker(self, pid, ticks, state='S', executable=None, group='lshttpd.service'):
        entry = self.proc / str(pid)
        entry.mkdir()
        (entry / 'comm').write_text('openlitespeed\n')
        (entry / 'exe').symlink_to(executable or self.binary)
        fields = [state, '1'] + ['0'] * 17 + [ticks]
        (entry / 'stat').write_text('%s (openlitespeed) %s\n' % (pid, ' '.join(fields)))
        (entry / 'cgroup').write_text('0::/system.slice/' + group + '\n')
        return entry

    def test_verified_stop_waits_when_master_disappears_before_known_worker(self):
        with self.assertRaises(control.OLSWorkersRemain):
            self.service._native_state()
        self.service.systemd.assert_not_called()

    def test_actual_stop_records_workers_and_waits_for_an_empty_proc_snapshot(self):
        self.worker(123, '11')
        worker_stat = self.proc / '124/stat'
        worker_stat.write_text(worker_stat.read_text().replace(') S 1 ', ') S 123 '))
        self.service.draining = None
        self.service._draining_processes = {}
        original = self.service._native_state()
        self.assertEqual(self.service._observed_processes, {123: '11', 124: '22'})

        def remove(pid):
            for path in (self.proc / str(pid)).iterdir(): path.unlink()
            (self.proc / str(pid)).rmdir()

        def stop(command, **kwargs):
            self.assertEqual(command, ['systemctl', 'stop', 'lshttpd.service'])
            remove(123)
            worker_stat.write_text(worker_stat.read_text().replace(') S 123 ', ') S 1 '))
            return SimpleNamespace(returncode=0)

        def finish_drain(delay):
            self.assertEqual(delay, .25)
            self.assertEqual(self.service._draining_processes, {123: '11', 124: '22'})
            remove(124)

        with patch.object(control.watchdog, 'inspect_watchdog', return_value=[]), \
                patch.object(self.service, 'verify_mapped_bundle'), \
                patch.object(control.subprocess, 'run', side_effect=stop), \
                patch.object(control.time, 'sleep', side_effect=finish_drain) as sleep:
            self.assertIsNone(self.service.change('stop', original))
        sleep.assert_called_once()
        self.assertEqual(self.service._draining_processes, {})

    def test_master_first_exit_is_not_treated_as_success_with_live_workers(self):
        with self.assertRaises(control.OLSWorkersRemain):
            self.service._native_state()
        for path in (self.proc / '124').iterdir():
            path.unlink()
        (self.proc / '124').rmdir()
        self.assertIsNone(self.service._native_state())
        self.service.systemd.assert_called_once_with(None)

    def test_unrelated_or_reused_pid_and_changed_cgroup_still_refuse(self):
        for mutation in ('not-stopping', 'other-master', 'unknown-worker', 'reused-worker', 'other-cgroup'):
            with self.subTest(mutation=mutation):
                self.service.draining = (123, '11', 'lshttpd.service')
                self.service._draining_processes = {123: '11', 124: '22'}
                if mutation == 'not-stopping': self.service.draining = None
                if mutation == 'other-master': self.service.draining = (999, '11', 'lshttpd.service')
                if mutation == 'unknown-worker': self.service._draining_processes = {123: '11'}
                if mutation == 'reused-worker': self.service._draining_processes[124] = 'different-start'
                group = 'other.service' if mutation == 'other-cgroup' else 'lshttpd.service'
                (self.proc / '124/cgroup').write_text('0::/system.slice/' + group + '\n')
                with self.assertRaises(RuntimeError) as error:
                    self.service._native_state()
                self.assertNotIsInstance(error.exception, control.OLSWorkersRemain)

    def test_foreign_litespeed_binary_still_refuses_during_known_stop(self):
        foreign = self.root / 'foreign'
        foreign.write_bytes(b'unrelated binary')
        self.worker(125, '33', executable=foreign)
        with self.assertRaisesRegex(RuntimeError, 'different or deleted'):
            self.service._native_state()


class NativeExitRaceTests(unittest.TestCase):
    setUp = NativeDrainingStateTests.setUp
    worker = NativeDrainingStateTests.worker

    def add_master(self):
        self.worker(123, '11')
        path=self.proc/'124/stat'
        path.write_text(path.read_text().replace(') S 1 ', ') S 123 '))

    def remove(self, pid):
        for path in (self.proc/str(pid)).iterdir():path.unlink()
        (self.proc/str(pid)).rmdir()

    def test_master_cgroup_disappearance_requires_fresh_empty_snapshot(self):
        self.add_master()
        read=Path.read_text
        fired=[]
        def disappear(path,*args,**kwargs):
            if path==self.proc/'123/cgroup' and not fired:
                fired.append(True);self.remove(123)
                raise FileNotFoundError('master exited between scan and cgroup read')
            return read(path,*args,**kwargs)
        with patch.object(Path,'read_text',disappear):
            with self.assertRaises(control.OLSWorkersRemain):self.service._native_state()
        self.service.systemd.assert_not_called()
        with self.assertRaises(control.OLSWorkersRemain):self.service._native_state()
        self.service.systemd.assert_not_called()
        self.remove(124)
        self.assertIsNone(self.service._native_state())
        self.service.systemd.assert_called_once_with(None)

    def test_real_stop_loop_retries_midscan_exit_before_returning_stopped(self):
        self.add_master();self.service.draining=None;self.service._draining_processes={}
        original=self.service._native_state()
        armed=[];fired=[];read=Path.read_text
        def stop(command,**kwargs):
            self.assertEqual(command,['systemctl','stop','lshttpd.service'])
            armed.append(True);return SimpleNamespace(returncode=0)
        def disappear(path,*args,**kwargs):
            if armed and not fired and path==self.proc/'123/cgroup':
                fired.append(True);self.remove(123)
                raise ProcessLookupError('master exited after scan')
            return read(path,*args,**kwargs)
        def drain(delay):
            self.assertEqual(delay,.25)
            self.assertEqual(self.service._draining_processes,{123:'11',124:'22'})
            self.remove(124)
        with patch.object(control.watchdog,'inspect_watchdog',return_value=[]), \
             patch.object(self.service,'verify_mapped_bundle'), \
             patch.object(control.subprocess,'run',side_effect=stop), \
             patch.object(Path,'read_text',disappear), \
             patch.object(control.time,'sleep',side_effect=drain) as sleep:
            self.assertIsNone(self.service.change('stop',original))
        sleep.assert_called_once();self.assertTrue(fired)

    def test_disappearance_does_not_waive_unknown_or_reused_process_identity(self):
        self.add_master();read=Path.read_text
        def absent(path,*args,**kwargs):
            if path==self.proc/'123/cgroup':raise FileNotFoundError('master disappeared')
            return read(path,*args,**kwargs)
        for case in ('not-stopping','other-master','reused-master','unknown-master','unknown-worker','reused-worker','foreign-worker'):
            with self.subTest(case=case):
                self.service.draining=(123,'11','lshttpd.service')
                self.service._draining_processes={123:'11',124:'22'}
                (self.proc/'124/cgroup').write_text('0::/system.slice/lshttpd.service\n')
                if case=='not-stopping':self.service.draining=None
                elif case=='other-master':self.service.draining=(999,'11','lshttpd.service')
                elif case=='reused-master':self.service.draining=(123,'different','lshttpd.service')
                elif case=='unknown-master':self.service._draining_processes.pop(123)
                elif case=='unknown-worker':self.service._draining_processes.pop(124)
                elif case=='reused-worker':self.service._draining_processes[124]='different'
                elif case=='foreign-worker':(self.proc/'124/cgroup').write_text('0::/system.slice/other.service\n')
                with patch.object(Path,'read_text',absent):
                    with self.assertRaises((FileNotFoundError,RuntimeError)) as error:self.service._native_state()
                self.assertNotIsInstance(error.exception,control.OLSWorkersRemain)

    def test_permission_errors_and_unknown_master_owner_remain_fatal(self):
        self.add_master();read=Path.read_text
        def denied(path,*args,**kwargs):
            if path==self.proc/'123/cgroup':raise PermissionError('access denied')
            return read(path,*args,**kwargs)
        with patch.object(Path,'read_text',denied):
            with self.assertRaises(PermissionError):self.service._native_state()
        (self.proc/'123/cgroup').write_text('0::/system.slice/other.service\n')
        with self.assertRaisesRegex(RuntimeError,'unrecognized systemd'):self.service._native_state()

    def test_repeated_pending_race_cannot_extend_stop_deadline(self):
        self.service.draining=None;self.service._draining_processes={}
        original=(123,'11',None)
        with patch.object(self.service,'state',side_effect=[original,control.OLSWorkersRemain('exit race')]), \
             patch.object(self.service,'verify_mapped_bundle'), \
             patch.object(control.subprocess,'run',return_value=SimpleNamespace(returncode=0)), \
             patch.object(control.time,'monotonic',side_effect=[0,0,26]), \
             patch.object(control.time,'sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError,'did not stop'):self.service.change('stop',original)
        sleep.assert_called_once_with(.25)


class ServiceControlTests(unittest.TestCase):
    def test_rejects_unknown_owners_and_unproven_cgroups(self):
        for cgroup in ('', '3:cpu:/foo', '0::/system.slice/other.service',
                       '0::/system.slice/lsws.service\n1:name=systemd:/manual.scope'):
            with self.subTest(cgroup=cgroup), self.assertRaises(RuntimeError):
                control.process_owner(cgroup)
        self.assertIsNone(control.process_owner('0::/user.slice/example.scope'))
        self.assertEqual(control.process_owner('1:name=systemd:/system.slice/lshttpd.service'), 'lshttpd.service')

    def test_stop_waits_for_last_worker_before_success(self):
        svc = control.OLSService()
        original = (123, '11', None)
        with patch.object(svc, 'state', side_effect=[original, control.OLSWorkersRemain('draining'), None]), \
                patch.object(svc, 'verify_mapped_bundle'), patch.object(control.time, 'sleep'), \
                patch.object(control.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as action:
            self.assertIsNone(svc.change('stop', original))
        action.assert_called_once()

    def test_active_registered_owner_must_agree_with_manual_or_managed_cgroup(self):
        svc = control.OLSService()
        result = SimpleNamespace(returncode=0, stdout='Id=lshttpd.service\nLoadState=loaded\nActiveState=active\nMainPID=123\n')
        with patch.object(Path, 'is_dir', return_value=True), patch.object(control, 'run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'disagree'):
                svc.verify_unit_claims(123, None)
            with self.assertRaisesRegex(RuntimeError, 'manager or PID'):
                svc.verify_unit_claims(None, None)
            svc.verify_unit_claims(123, 'lshttpd.service')

    def test_systemd_identity_hooks_and_file_must_all_match(self):
        with tempfile.TemporaryDirectory() as temp:
            unit = Path(temp) / 'lshttpd.service'
            unit.write_text('fixture unit\n')
            svc = control.OLSService(unit='lshttpd.service')
            props = dict(Id='lshttpd.service', LoadState='loaded', ActiveState='active',
                         MainPID='123', FragmentPath=str(unit), DropInPaths='', NeedDaemonReload='no')
            for prop, action in [('ExecStart', 'start'), ('ExecStop', 'delay-stop'), ('ExecReload', 'restart')]:
                props[prop] = '{ path=%s ; argv[]=%s %s ; }' % (svc.control, svc.control, action)

            def response(override):
                fields = dict(props, **override)
                return SimpleNamespace(returncode=0, stdout='\n'.join('%s=%s' % item for item in fields.items()))

            with patch.object(control, 'UNIT_HASH', control.digest(unit)):
                for override in ({}, {'MainPID': '37'}, {'ExecStopPost': '/bin/x'}, {'DropInPaths': '/override'},
                                 {'NeedDaemonReload': 'yes'}, {'ExecStart': 'unverified hook'}):
                    with self.subTest(override=override), patch.object(control, 'run', return_value=response(override)):
                        if override:
                            with self.assertRaises(RuntimeError):
                                svc.systemd(123)
                        else:
                            svc.systemd(123)

    def test_watchdog_and_unrelated_process_prevent_actions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            proc = root / 'proc'
            p = proc / '884'
            p.mkdir(parents=True)
            binary = root / 'bin/openlitespeed'
            binary.parent.mkdir()
            binary.write_bytes(b'fixture')
            other = root / 'other'
            other.write_bytes(b'foreign')
            (p / 'exe').symlink_to(other)
            svc = control.OLSService(root, proc)
            with patch.object(svc, 'controller'), patch.object(control, 'run', return_value=SimpleNamespace(stdout='is not running.')):
                for name in ('wswatch.sh', 'other-litespeed'):
                    (p / 'comm').write_text(name + '\n')
                    with self.subTest(name=name), patch.object(control.subprocess, 'run') as command, self.assertRaises(RuntimeError):
                        svc.change('start', None)
                    command.assert_not_called()

    def test_config_only_changes_are_restored_before_any_reload_on_invalid_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            conf = root / 'conf/httpd_config.conf'
            conf.parent.mkdir()
            conf.write_bytes(b'old\r\n')
            conf.chmod(0o640)
            svc = Mock(root=root)
            svc.state.return_value = svc.prepare_state.return_value = (123, '1', 'lshttpd.service')

            def validate():
                if conf.read_text() == 'broken\n':
                    raise ValueError('bad config')

            with self.assertRaisesRegex(ValueError, 'bad config'):
                control.apply_config_changes({str(conf): ('old\n', 'broken\n')}, validate, svc)
            self.assertEqual(conf.read_bytes(), b'old\r\n')
            self.assertEqual(conf.stat().st_mode & 0o777, 0o640)
            svc.reload.assert_not_called()
            svc.change.assert_not_called()

    def test_failed_reload_restores_config_then_reloads_the_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            conf = root / 'conf/httpd_config.conf'
            conf.parent.mkdir()
            conf.write_text('before')
            svc = Mock(root=root)
            svc.state.return_value = svc.prepare_state.return_value = (123, '4', None)
            svc.reload.side_effect = [RuntimeError('failed reload'), None]
            with self.assertRaisesRegex(RuntimeError, 'failed reload'):
                control.apply_config_changes({str(conf): ('before', 'after')}, Mock(), svc)
            self.assertEqual(conf.read_text(), 'before')
            self.assertEqual(svc.reload.call_count, 2)

    def test_concurrent_config_edit_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            conf = root / 'conf/httpd_config.conf'
            conf.parent.mkdir()
            conf.write_text('operator edit')
            svc = Mock(root=root)
            svc.state.return_value = svc.prepare_state.return_value = None
            with self.assertRaisesRegex(RuntimeError, 'changed during migration'):
                control.apply_config_changes({str(conf): ('old', 'another edit')}, Mock(), svc)
            self.assertEqual(conf.read_text(), 'operator edit')
            svc.reload.assert_not_called()

    def test_config_reload_preserves_stopped_service(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            conf = root / 'conf/httpd_config.conf'
            conf.parent.mkdir()
            conf.write_text('old')
            svc = Mock(root=root)
            svc.state.return_value = svc.prepare_state.return_value = None
            control.apply_config_changes({str(conf): ('old', 'new')}, Mock(), svc)
            self.assertEqual(conf.read_text(), 'new')
            svc.reload.assert_not_called()
            svc.change.assert_not_called()


class PreviousGenerationTests(unittest.TestCase):
    """A graceful restart leaves the old main and its busy worker running under init."""
    MAIN = b'openlitespeed (lshttpd - main)\x00'

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.binary = self.root / 'bin/openlitespeed'
        self.binary.parent.mkdir()
        self.binary.write_bytes(b'installed core fixture')
        self.proc = self.root / 'proc'
        self.proc.mkdir()
        # Live generation: master 200 with two workers. Old generation: 100 with worker 101.
        self.process(200, 1, '500')
        self.process(201, 200, '501', cmdline=b'openlitespeed (lshttpd - #01)\x00')
        self.process(202, 200, '502', cmdline=b'openlitespeed (lscgid)\x00')
        self.process(100, 1, '300')
        self.process(101, 100, '301', cmdline=b'openlitespeed (lshttpd - #03)\x00')
        self.service = control.OLSService(self.root, self.proc)
        for target in ('controller', 'verify_unit_claims', 'systemd'):
            patcher = patch.object(self.service, target, return_value=None)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(control, 'run', return_value=SimpleNamespace(stdout='litespeed is running with PID 200.'))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.killed = []
        self.service.kill = self.kill

    def process(self, pid, parent, ticks, cmdline=MAIN, group='lshttpd.service', executable=None):
        entry = self.proc / str(pid)
        entry.mkdir()
        (entry / 'comm').write_text('litespeed\n')
        (entry / 'exe').symlink_to(executable or self.binary)
        fields = ['S', str(parent)] + ['0'] * 17 + [ticks]
        (entry / 'stat').write_text('%s (litespeed) %s\n' % (pid, ' '.join(fields)))
        (entry / 'cgroup').write_text('0::/system.slice/' + group + '\n')
        (entry / 'cmdline').write_bytes(cmdline)

    def remove(self, pid):
        for path in (self.proc / str(pid)).iterdir():
            path.unlink()
        (self.proc / str(pid)).rmdir()

    def kill(self, pid, number):
        self.assertEqual(number, control.signal.SIGKILL)
        self.killed.append(pid)
        self.remove(pid)

    def clock(self):
        """Fake monotonic time: every sleep advances it; returns the sleep mock."""
        now = [1000.0]
        patchers = [patch.object(control.time, 'monotonic', side_effect=lambda: now[0]),
                    patch.object(control.time, 'sleep', side_effect=lambda delay: now.__setitem__(0, now[0] + delay))]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        return now

    def test_the_old_generation_is_recognised_and_named(self):
        with self.assertRaises(control.OLSPreviousGeneration) as raised:
            self.service._native_state()
        self.assertEqual(raised.exception.generation, {100: '300', 101: '301'})
        self.assertIn('PIDs 100, 101', str(raised.exception))
        self.service.systemd.assert_not_called()

    def test_anything_that_is_not_an_earlier_generation_of_this_service_stays_unmanaged(self):
        def mutate_parent():
            self.remove(100); self.process(100, 77, '300')
        def mutate_cmdline():
            self.remove(100); self.process(100, 1, '300', cmdline=b'openlitespeed -d\x00')
        def mutate_group():
            self.remove(100); self.process(100, 1, '300', group='lsws.service')
        def mutate_worker_group():
            self.remove(101); self.process(101, 100, '301', group='other.service')
        def mutate_younger():
            self.remove(100); self.process(100, 1, '900')
        def mutate_orphan_worker():
            self.remove(100)
        for name, mutate in [('parent is not init', mutate_parent), ('other command line', mutate_cmdline),
                             ('other service', mutate_group), ('worker in another service', mutate_worker_group),
                             ('started after the master', mutate_younger), ('worker without its main', mutate_orphan_worker)]:
            with self.subTest(name):
                self.setUp()
                mutate()
                with self.assertRaisesRegex(RuntimeError, 'unmanaged OLS process') as raised:
                    self.service._native_state()
                self.assertNotIsInstance(raised.exception, control.OLSPreviousGeneration)

    def test_a_known_stop_in_progress_keeps_the_strict_rule(self):
        self.service.draining = (200, '500', 'lshttpd.service')
        with self.assertRaisesRegex(RuntimeError, 'unmanaged OLS process') as raised:
            self.service._native_state()
        self.assertNotIsInstance(raised.exception, control.OLSPreviousGeneration)

    def test_a_generation_that_finishes_on_its_own_is_never_killed(self):
        now = self.clock()
        start = now[0]
        calls = []

        def check():
            calls.append(now[0])
            if now[0] - start >= 5:
                for pid in (101, 100):
                    if (self.proc / str(pid)).exists():
                        self.remove(pid)
            return self.service._native_state()

        state = self.service.settle_previous_generation(check)
        self.assertEqual(state[0], 200)
        self.assertEqual(self.killed, [])

    def test_after_the_wait_exactly_the_old_generation_is_ended_and_the_live_one_kept(self):
        now = self.clock()
        start = now[0]
        with patch('builtins.print') as said:
            state = self.service.settled_state()
        self.assertEqual(state[0], 200)
        self.assertEqual(sorted(self.killed), [100, 101])
        self.assertGreaterEqual(now[0] - start, control.OLSService.PREVIOUS_GENERATION_WAIT)
        for pid in (200, 201, 202):
            self.assertTrue((self.proc / str(pid)).exists())
        self.assertIn('PIDs 100, 101', said.call_args[0][0])

    def test_prepare_state_settles_the_old_generation_first(self):
        self.clock()
        with patch.object(control.watchdog, 'inspect_watchdog', return_value=[]), \
                patch.object(control.watchdog, 'prepare_watchdog'), \
                patch.object(self.service, 'verify_mapped_bundle'), patch('builtins.print'):
            state = self.service.prepare_state()
        self.assertEqual(state[0], 200)
        self.assertEqual(sorted(self.killed), [100, 101])

    def test_a_reused_pid_or_other_binary_is_not_killed_and_the_upgrade_still_stops(self):
        self.clock()
        foreign = self.root / 'foreign'
        foreign.write_bytes(b'unrelated')
        real_end = self.service._end_previous_generation

        def swap_identities(generation):
            # Between observation and the kill, 101 became another process and 100 another binary.
            self.remove(101); self.process(101, 100, '999', cmdline=b'openlitespeed (lshttpd - #03)\x00')
            (self.proc / '100/exe').unlink(); (self.proc / '100/exe').symlink_to(foreign)
            return real_end(generation)

        with patch.object(self.service, '_end_previous_generation', side_effect=swap_identities), \
                patch('builtins.print'), self.assertRaises(RuntimeError):
            self.service.settled_state()
        self.assertEqual(self.killed, [])
