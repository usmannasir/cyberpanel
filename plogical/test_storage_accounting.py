"""Website storage accounting regressions with isolated model and disk fixtures."""
import ast
import contextlib
import datetime
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace as NS
import sys
import unittest
from unittest.mock import Mock, patch

from plogical import storageAccounting as accounting


class Related:
    def __init__(self, *rows):
        self.rows = rows

    def all(self):
        return self.rows


def scheduler_function(namespace):
    source = Path(__file__).with_name('IncScheduler.py').read_text()
    scheduler = next(node for node in ast.parse(source).body
                     if isinstance(node, ast.ClassDef) and node.name == 'IncScheduler')
    method = next(node for node in scheduler.body
                  if isinstance(node, ast.FunctionDef) and node.name == 'CalculateAndUpdateDiskUsage')
    method.decorator_list = []
    code = ast.Module(body=[method], type_ignores=[])
    exec(compile(ast.fix_missing_locations(code), str(Path(__file__).with_name('IncScheduler.py')), 'exec'), namespace)
    return namespace['CalculateAndUpdateDiskUsage']


def fixture():
    website = NS(pk=1, domain='site.test', config=json.dumps({'DiskUsage': 999, 'keep': 'value'}),
                 package=NS(diskSpace=200, bandwidth=300), save=Mock())
    child = NS(pk=2, domain='child.test', master_id=1, master=website)
    direct = NS(domain='mail.site.test', domainOwner_id=1, domainOwner=website,
                childOwner_id=None, childOwner=None)
    child_domain = NS(domain='child.test', domainOwner_id=None, domainOwner=None,
                      childOwner_id=2, childOwner=child)
    first = NS(email='first@mail.site.test', emailOwner_id=direct.domain,
               emailOwner=direct, DiskUsage='99', save=Mock(),
               mail='maildir:/home/vmail/mail.site.test/first/Maildir')
    second = NS(email='second@child.test', emailOwner_id=child_domain.domain,
                emailOwner=child_domain, DiskUsage='98', save=Mock(),
                mail='maildir:/home/vmail/child.test/second/Maildir')
    direct.eusers_set = Related(first)
    child_domain.eusers_set = Related(second)
    child.domains_set = Related(child_domain)
    website.domains_set = Related(direct)
    website.childdomains_set = Related(child)
    return website, child, direct, child_domain, first, second


class SchedulerAccountingTests(unittest.TestCase):
    def setUp(self):
        self.website, self.child, self.direct, self.child_domain, self.first, self.second = fixture()
        self.logger = NS(writeToFile=Mock())
        self.mail_paths = []
        def old_mail_usage(path):
            self.mail_paths.append(path)
            return {'/home/vmail/mail.site.test/first': '60',
                    '/home/vmail/child.test/second': '4'}.get(path, '0MB')
        self.namespace = {
            'json': json,
            'Websites': NS(objects=Related(self.website)),
            'logging': self.logger,
            'virtualHostUtilities': NS(getDiskUsage=Mock(return_value=[10, 5]),
                                      getDiskUsageofPath=old_mail_usage),
        }
        self.vhost = NS(vhost=NS(findDomainBW=Mock(return_value=(12, 4))))
        self.quota = NS(status=Mock(return_value={
            'state': 'unconfigured', 'enforced': False, 'reason': 'No combined limit configured'}))
        self.transaction = NS(atomic=Mock(side_effect=contextlib.nullcontext))
        self.module_patch = patch.dict(sys.modules, {
            'plogical.vhost': self.vhost, 'plogical.storageQuota': self.quota,
            'django.db': NS(transaction=self.transaction),
        })
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        self.package_patch = patch('plogical.storageQuota', self.quota, create=True)
        self.package_patch.start()
        self.addCleanup(self.package_patch.stop)

    def run_scheduler(self):
        # On the original source this fixture intentionally has no effect:
        # the scheduler never requests the combined website/mail measurement.
        fake_accounting = NS(measure_website_storage=Mock(return_value={
            'disk_usage_mb': 110,
            'disk_usage_percentage': 55,
            'mailbox_usage': [(self.first, '60'), (self.second, '4')],
            'mail_domains': (self.direct, self.child_domain),
        }))
        with patch.dict(sys.modules, {'plogical.storageAccounting': fake_accounting}), contextlib.redirect_stdout(io.StringIO()):
            scheduler_function(self.namespace)()

    def test_website_total_includes_direct_and_child_mail_domains(self):
        self.run_scheduler()
        saved = json.loads(self.website.config)
        self.assertEqual(110, saved['DiskUsage'])
        self.assertEqual(55, saved['DiskUsagePercentage'])
        self.assertEqual('value', saved['keep'])
        self.assertEqual(12, saved['bwInMB'])
        self.assertEqual('available', saved['storageUsageStatus'])
        self.assertNotIn('storageUsageError', saved)
        self.assertEqual('unconfigured', saved['storageQuotaStatus']['state'])
        self.assertFalse(saved['storageQuotaStatus']['enforced'])
        self.assertIsNotNone(datetime.datetime.fromisoformat(saved['storageUsageCheckedAt']).tzinfo)
        self.assertIsNotNone(datetime.datetime.fromisoformat(saved['storageQuotaStatus']['checked_at']).tzinfo)

    def test_mailbox_statistics_use_actual_mail_domain_and_include_children(self):
        self.run_scheduler()
        self.assertEqual('60', self.first.DiskUsage)
        self.assertEqual('4', self.second.DiskUsage)
        self.first.save.assert_called_once()
        self.second.save.assert_called_once()


    def test_failed_measurement_preserves_all_previous_statistics(self):
        old_config = json.loads(self.website.config)
        fake_accounting = NS(measure_website_storage=Mock(
            side_effect=accounting.StorageAccountingError('permission denied')))
        with patch.dict(sys.modules, {'plogical.storageAccounting': fake_accounting}):
            scheduler_function(self.namespace)()
        saved = json.loads(self.website.config)
        self.assertEqual(old_config['DiskUsage'], saved['DiskUsage'])
        self.assertEqual(old_config['keep'], saved['keep'])
        self.assertEqual('unavailable', saved['storageUsageStatus'])
        self.assertEqual('Unable to measure website and mail storage; check the server log.', saved['storageUsageError'])
        self.assertNotIn('permission denied', self.website.config)
        self.assertIsNotNone(datetime.datetime.fromisoformat(saved['storageUsageCheckedAt']).tzinfo)
        self.assertEqual('99', self.first.DiskUsage)
        self.assertEqual('98', self.second.DiskUsage)
        self.website.save.assert_called_once_with(update_fields=['config'])
        self.first.save.assert_not_called()
        self.second.save.assert_not_called()
        self.logger.writeToFile.assert_called_once()

    def test_new_success_clears_previous_failure_without_reusing_stale_quota_state(self):
        self.website.config = json.dumps({
            'DiskUsage': 999, 'storageUsageStatus': 'unavailable', 'storageUsageError': 'old failure',
            'storageQuotaStatus': {'state': 'active', 'enforced': True},
        })
        self.run_scheduler()
        saved = json.loads(self.website.config)
        self.assertEqual(110, saved['DiskUsage'])
        self.assertEqual('available', saved['storageUsageStatus'])
        self.assertNotIn('storageUsageError', saved)
        self.assertEqual('unconfigured', saved['storageQuotaStatus']['state'])
        self.assertFalse(saved['storageQuotaStatus']['enforced'])

    def test_mailbox_save_failure_still_persists_unavailable_status_and_old_total(self):
        self.first.save.side_effect = RuntimeError('private mailbox database error')
        self.run_scheduler()
        saved = json.loads(self.website.config)
        self.assertEqual(999, saved['DiskUsage'])
        self.assertEqual('unavailable', saved['storageUsageStatus'])
        self.assertNotIn('private mailbox', self.website.config)
        self.website.save.assert_called_once_with(update_fields=['config'])
        self.transaction.atomic.assert_called_once()
        self.second.save.assert_not_called()

    def test_quota_failure_is_sanitized_and_does_not_discard_valid_usage(self):
        self.quota.status.side_effect = RuntimeError('/private/customer/quota path')
        self.run_scheduler()
        saved = json.loads(self.website.config)
        self.assertEqual('available', saved['storageUsageStatus'])
        self.assertEqual(110, saved['DiskUsage'])
        self.assertEqual('unavailable', saved['storageQuotaStatus']['state'])
        self.assertFalse(saved['storageQuotaStatus']['enforced'])
        self.assertEqual('Unable to verify storage quota; check the server log.', saved['storageQuotaStatus']['reason'])
        self.assertNotIn('/private/customer', self.website.config)
        self.logger.writeToFile.assert_called_once()

    def test_quota_backend_timestamp_is_preserved(self):
        self.quota.status.return_value = {'state': 'pending', 'enforced': False,
                                        'checked_at': '2026-01-01T00:00:00+00:00'}
        self.run_scheduler()
        saved = json.loads(self.website.config)
        self.assertEqual('2026-01-01T00:00:00+00:00', saved['storageQuotaStatus']['checked_at'])

    def test_invalid_config_and_invalid_quota_result_do_not_leave_stale_success(self):
        self.website.config = '[]'
        self.quota.status.return_value = 'active'
        self.run_scheduler()
        saved = json.loads(self.website.config)
        self.assertEqual(110, saved['DiskUsage'])
        self.assertEqual('unavailable', saved['storageQuotaStatus']['state'])


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.website, self.child, self.direct, self.child_domain, self.first, self.second = fixture()

    def test_direct_and_child_domains_deduplicate_by_actual_domain(self):
        self.child_domain.domainOwner_id = self.website.pk
        self.website.domains_set = Related(self.direct, self.child_domain, self.direct)
        self.assertEqual((self.child_domain, self.direct), accounting.owned_mail_domains(self.website))
        self.assertEqual('/home/vmail/mail.site.test', accounting.mail_domain_path(self.direct))

    def test_foreign_direct_and_child_ownership_is_rejected(self):
        for change in ('direct', 'child', 'child_backlink', 'both_owners'):
            with self.subTest(change=change):
                self.setUp()
                if change == 'direct':
                    self.direct.domainOwner_id = 91
                elif change == 'child':
                    self.child.master_id = 91
                elif change == 'child_backlink':
                    self.child_domain.childOwner_id = 91
                else:
                    self.direct.childOwner_id = 91
                    self.direct.childOwner = NS(pk=91, master_id=92)
                with self.assertRaises(accounting.StorageAccountingError):
                    accounting.owned_mail_domains(self.website)

    def test_conflicting_duplicate_domain_records_are_rejected(self):
        self.child_domain.domain = self.direct.domain
        with self.assertRaises(accounting.StorageAccountingError):
            accounting.owned_mail_domains(self.website)

    def test_directory_names_never_establish_unrecorded_ownership(self):
        self.website.domains_set = Related()
        self.website.childdomains_set = Related()
        self.assertEqual((), accounting.owned_mail_domains(self.website))

    def test_unsafe_domain_components_are_rejected(self):
        for domain in ('..', '../other.test', '/foreign', 'one/test', 'one\\test', 'one\nline', 'one\x00test'):
            with self.subTest(domain=domain):
                self.direct.domain = domain
                with self.assertRaises(accounting.StorageAccountingError):
                    accounting.owned_mail_domains(self.website)


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.website, self.child, self.direct, self.child_domain, self.first, self.second = fixture()
        temporary = tempfile.TemporaryDirectory(prefix='storage accounting ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / 'home'
        self.mail = self.home / 'vmail'
        self.site_path = self.home / self.website.domain
        self.direct_path = self.mail / self.direct.domain
        self.child_path = self.mail / self.child_domain.domain
        self.first_path = self.direct_path / 'first'
        self.second_path = self.child_path / 'second'
        self.first.mail = 'maildir:' + str(self.first_path / 'Maildir')
        self.second.mail = 'maildir:' + str(self.second_path / 'Maildir')
        for path in (self.site_path, self.first_path, self.second_path):
            path.mkdir(parents=True)

    def measure(self):
        return accounting.measure_website_storage(self.website, str(self.home), str(self.mail))

    def test_combined_total_includes_mail_leftovers_without_double_counting_mailboxes(self):
        def measured(paths):
            if paths == [str(self.first_path)]:
                return 60 * accounting.MEBIBYTE
            if paths == [str(self.second_path)]:
                return 4 * accounting.MEBIBYTE
            self.assertEqual({str(self.site_path), str(self.direct_path), str(self.child_path)}, set(paths))
            return 110 * accounting.MEBIBYTE
        with patch.object(accounting, 'measure_paths_bytes', side_effect=measured) as measure:
            result = self.measure()
        self.assertEqual(110, result['disk_usage_mb'])
        self.assertEqual(55, result['disk_usage_percentage'])
        self.assertEqual([(self.second, '4'), (self.first, '60')], result['mailbox_usage'])
        self.assertEqual(3, measure.call_count)
        self.first.save.assert_not_called()
        self.website.save.assert_not_called()

    def test_missing_mail_directories_count_as_zero(self):
        self.first_path.rmdir()
        self.direct_path.rmdir()
        with patch.object(accounting, 'measure_paths_bytes', return_value=0) as measure:
            result = self.measure()
        self.assertEqual([(self.second, '0'), (self.first, '0')], result['mailbox_usage'])
        self.assertEqual([str(self.site_path), str(self.child_path)], measure.call_args.args[0])

    def test_custom_or_empty_stored_maildirs_are_not_silently_omitted(self):
        for location in ('', None, 'maildir:/foreign/mailbox/Maildir',
                         'maildir:' + str(self.second_path / 'Maildir'),
                         'maildir:' + str(self.first_path / 'Maildir') + ':INDEX=/foreign/index',
                         str(self.first_path / 'Maildir')):
            with self.subTest(location=location):
                self.first.mail = location
                with patch.object(accounting, 'measure_paths_bytes', return_value=0):
                    with self.assertRaisesRegex(accounting.StorageAccountingError, 'canonical'):
                        self.measure()

    def test_standard_stored_maildir_is_measured_at_its_actual_domain(self):
        with patch.object(accounting, 'measure_paths_bytes', return_value=accounting.MEBIBYTE) as measure:
            result = self.measure()
        self.assertEqual('1', dict((email.email, usage) for email, usage in result['mailbox_usage'])[self.first.email])
        self.assertIn(([str(self.first_path)],), [call.args for call in measure.call_args_list])

    def test_no_mail_server_directory_is_zero_but_missing_website_is_an_error(self):
        self.website.domains_set = Related(self.direct)
        self.website.childdomains_set = Related()
        self.first_path.rmdir()
        self.direct_path.rmdir()
        self.second_path.rmdir()
        self.child_path.rmdir()
        self.mail.rmdir()
        with patch.object(accounting, 'measure_paths_bytes', return_value=0):
            self.assertEqual([(self.first, '0')], self.measure()['mailbox_usage'])
            self.site_path.rmdir()
            with self.assertRaises(accounting.StorageAccountingError):
                self.measure()

    def test_mailbox_address_owner_and_path_mismatches_are_rejected(self):
        for change in ('owner', 'domain', 'traversal'):
            with self.subTest(change=change):
                self.first.emailOwner_id = 'foreign.test' if change == 'owner' else self.direct.domain
                self.first.email = {'owner': 'first@mail.site.test', 'domain': 'first@foreign.test',
                                    'traversal': '../escape@mail.site.test'}[change]
                with patch.object(accounting, 'measure_paths_bytes', return_value=0):
                    with self.assertRaises(accounting.StorageAccountingError):
                        self.measure()

    def test_symlink_mail_domain_and_mailbox_roots_are_rejected(self):
        self.first_path.rmdir()
        self.direct_path.rmdir()
        self.direct_path.symlink_to(self.child_path, target_is_directory=True)
        with patch.object(accounting, '_run_du', return_value=0):
            with self.assertRaises(accounting.StorageAccountingError):
                self.measure()
        self.direct_path.unlink()
        self.direct_path.mkdir()
        self.first_path.symlink_to(self.second_path, target_is_directory=True)
        with patch.object(accounting, '_run_du', return_value=0):
            with self.assertRaises(accounting.StorageAccountingError):
                self.measure()

    def test_permission_error_does_not_become_empty_storage(self):
        real_lstat = accounting.os.lstat
        def metadata(path):
            if os.fspath(path) == str(self.direct_path):
                raise PermissionError('denied')
            return real_lstat(path)
        with patch.object(accounting.os, 'lstat', side_effect=metadata), patch.object(accounting, '_run_du', return_value=0):
            with self.assertRaises(accounting.StorageAccountingError):
                self.measure()
        self.first.save.assert_not_called()

    def test_rounding_happens_once_and_zero_allowance_keeps_zero_percentage(self):
        self.website.package.diskSpace = 0
        with patch.object(accounting, 'measure_paths_bytes', return_value=accounting.MEBIBYTE + 1):
            result = self.measure()
        self.assertEqual(2, result['disk_usage_mb'])
        self.assertEqual(0, result['disk_usage_percentage'])
        self.assertEqual('2', result['mailbox_usage'][0][1])
        self.website.package.diskSpace = 1
        with patch.object(accounting, 'measure_paths_bytes', return_value=2 * accounting.MEBIBYTE):
            self.assertEqual(200, self.measure()['disk_usage_percentage'])

    def test_nested_or_repeated_roots_are_only_passed_once(self):
        with patch.object(accounting, '_run_du', return_value=123) as run:
            value = accounting.measure_paths_bytes([str(self.first_path), str(self.direct_path), str(self.direct_path)])
        self.assertEqual(123, value)
        run.assert_called_once_with([str(self.direct_path)])

    def test_replaced_root_during_measurement_is_rejected(self):
        original = accounting._directory
        count = 0
        def identity(path, optional=False):
            nonlocal count
            count += 1
            return original(path, optional) if count == 1 else (99, 999)
        with patch.object(accounting, '_directory', side_effect=identity), patch.object(accounting, '_run_du', return_value=12):
            with self.assertRaises(accounting.StorageAccountingError):
                accounting.measure_paths_bytes([str(self.site_path)])


class DuContractTests(unittest.TestCase):
    def test_checked_argv_no_link_following_and_nul_total(self):
        reply = NS(returncode=0, stdout=b'123\t/path with spaces\x00123\ttotal\x00', stderr=b'')
        with patch.object(accounting.subprocess, 'run', return_value=reply) as run:
            self.assertEqual(123, accounting._run_du(['/path with spaces', '/second']))
        self.assertEqual(['du', '--summarize', '--block-size=1', '--no-dereference', '--total',
                          '--null', '--', '/path with spaces', '/second'], run.call_args.args[0])
        self.assertFalse(run.call_args.kwargs.get('shell', False))
        self.assertEqual('C', run.call_args.kwargs['env']['LC_ALL'])

    def test_failed_partial_warning_and_malformed_results_are_rejected(self):
        for status, stdout, stderr in (
                (1, b'100\ttotal\x00', b'Permission denied'),
                (0, b'100\ttotal\x00', b'warning'),
                (0, b'100\t/path\x00', b''), (0, b'100\ttotal', b''),
                (0, b'-1\ttotal\x00', b''), (0, b'nan\ttotal\x00', b''), (0, b'', b'')):
            with self.subTest(status=status, stdout=stdout, stderr=stderr):
                with patch.object(accounting.subprocess, 'run', return_value=NS(returncode=status, stdout=stdout, stderr=stderr)):
                    with self.assertRaises(accounting.StorageAccountingError):
                        accounting._run_du(['/owned'])

    def test_timeout_and_missing_tool_are_errors(self):
        for error in (FileNotFoundError('du'), subprocess.TimeoutExpired('du', 600)):
            with patch.object(accounting.subprocess, 'run', side_effect=error):
                with self.assertRaises(accounting.StorageAccountingError):
                    accounting._run_du(['/owned'])


@unittest.skipUnless(sys.platform.startswith('linux'), 'GNU du acceptance requires Linux')
class RealDiskMeasurementTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='storage-accounting-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.first = self.root / 'web'
        self.second = self.root / 'mail'
        self.foreign = self.root / 'foreign'
        for path in (self.first, self.second, self.foreign):
            path.mkdir()

    def test_hardlinks_across_web_and_mail_count_once(self):
        message = self.first / 'message'
        message.write_bytes(b'x' * 131072)
        os.link(message, self.second / 'linked-message')
        expected = sum(path.stat().st_blocks * 512 for path in (self.first, self.second, message))
        self.assertEqual(expected, accounting.measure_paths_bytes([str(self.first), str(self.second)]))

    def test_nested_symlink_never_counts_foreign_storage(self):
        foreign_message = self.foreign / 'message'
        foreign_message.write_bytes(b'x' * 131072)
        link = self.first / 'foreign-link'
        link.symlink_to(self.foreign, target_is_directory=True)
        expected = self.first.stat().st_blocks * 512 + link.lstat().st_blocks * 512
        self.assertEqual(expected, accounting.measure_paths_bytes([str(self.first)]))


if __name__ == '__main__':
    unittest.main()
