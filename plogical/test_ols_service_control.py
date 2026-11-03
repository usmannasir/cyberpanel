import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from plogical import olsServiceControl as control


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
            svc.state.return_value = (123, '1', 'lshttpd.service')

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
            svc.state.return_value = (123, '4', None)
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
            svc.state.return_value = None
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
            svc.state.return_value = None
            control.apply_config_changes({str(conf): ('old', 'new')}, Mock(), svc)
            self.assertEqual(conf.read_text(), 'new')
            svc.reload.assert_not_called()
            svc.change.assert_not_called()
