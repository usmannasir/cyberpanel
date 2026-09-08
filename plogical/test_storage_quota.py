"""Contract and failure-path tests; real kernel/mail acceptance is separate."""
import contextlib
import copy
import errno
import os
import stat
import struct
import tempfile
import types
import unittest
from unittest import mock

from plogical import storageQuota as quota


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = os.path.join(self.directory.name, 'web')
        os.mkdir(self.root)
        info = os.stat(self.root)
        self.roots = [{'path': self.root, 'kind': 'web', 'device': info.st_dev, 'inode': info.st_ino}]
        self.attributes = (quota.PROJINHERIT | 0x80, 0, 0, 51, 0)
        self.attribute_patch = mock.patch.object(quota, '_attrs', return_value=self.attributes)
        self.attribute_patch.start()
        self.addCleanup(self.attribute_patch.stop)

    def test_in_scope_hard_links_count_once_without_rejection(self):
        first = os.path.join(self.root, 'one')
        with open(first, 'w') as stream:
            stream.write('mail message')
        os.link(first, os.path.join(self.root, 'two'))
        self.assertEqual(len(quota._inventory(self.roots, 51)), 3)

    def test_off_scope_hard_link_refused(self):
        first = os.path.join(self.root, 'one')
        with open(first, 'w') as stream:
            stream.write('mail message')
        os.link(first, os.path.join(self.directory.name, 'outside'))
        with self.assertRaisesRegex(quota.StorageQuotaError, 'hard link outside'):
            quota._inventory(self.roots, 51)

    def test_symbolic_link_refused_even_if_target_is_inside(self):
        os.symlink(self.root, os.path.join(self.root, 'link'))
        with self.assertRaisesRegex(quota.StorageQuotaError, 'symbolic links'):
            quota._inventory(self.roots, 51)

    def test_root_replacement_is_not_accepted_as_existing_scope(self):
        os.rename(self.root, self.root + '-old')
        os.mkdir(self.root)
        with self.assertRaisesRegex(quota.StorageQuotaError, 'replaced'):
            quota._inventory(self.roots, 51)

    def test_foreign_project_never_adopted(self):
        with mock.patch.object(quota, '_attrs', return_value=(quota.PROJINHERIT, 0, 0, 999, 0)):
            with self.assertRaisesRegex(quota.StorageQuotaError, 'foreign project'):
                quota._inventory(self.roots, 51, allow_unassigned=True)

    def test_unassigned_allowed_only_in_maintenance_inventory(self):
        with mock.patch.object(quota, '_attrs', return_value=(0, 0, 0, 0, 0)):
            self.assertEqual(len(quota._inventory(self.roots, 51, allow_unassigned=True)), 1)
            with self.assertRaisesRegex(quota.StorageQuotaError, 'foreign project'):
                quota._inventory(self.roots, 51)

    def test_lost_inheritance_refuses_active_status(self):
        with mock.patch.object(quota, '_attrs', return_value=(0, 0, 0, 51, 0)):
            with self.assertRaisesRegex(quota.StorageQuotaError, 'lost project inheritance'):
                quota._inventory(self.roots, 51)

    def test_different_root_filesystem_refused(self):
        roots = self.roots + [dict(self.roots[0], device=self.roots[0]['device'] + 1)]
        with self.assertRaisesRegex(quota.StorageQuotaError, 'single filesystem'):
            quota._inventory(roots, 51)

    def test_tag_preserves_owner_mode_and_unrelated_attributes(self):
        info = os.stat(self.root)
        old = (0x80, 128, 2, 0, 256)
        record = quota._inode_record(self.root, info)
        record['attrs'] = old
        state = [old]

        def ioctl(descriptor, command, data, *unused):
            if command == quota.FSGETXATTR:
                data[:] = struct.pack('=5I8x', *state[0])
            elif command == quota.FSSETXATTR:
                state[0] = struct.unpack('=5I8x', data)
            else:
                self.fail('Unexpected ioctl')

        with mock.patch.object(quota.fcntl, 'ioctl', side_effect=ioctl):
            quota._tag(record, 51)
        self.assertEqual(state[0], (old[0] | quota.PROJINHERIT, old[1], old[2], 51, old[4]))
        after = os.stat(self.root)
        self.assertEqual((after.st_uid, after.st_gid, after.st_mode), (info.st_uid, info.st_gid, info.st_mode))

    def test_tag_detects_replaced_inode_before_mutation(self):
        info = os.stat(self.root)
        record = quota._inode_record(self.root, info)
        record['inode'] += 1
        with mock.patch.object(quota.fcntl, 'ioctl') as ioctl:
            with self.assertRaisesRegex(quota.StorageQuotaError, 'changed during maintenance'):
                quota._tag(record, 51)
        ioctl.assert_not_called()


class _PolicyFixture(unittest.TestCase):
    def setUp(self):
        self.policy = {'disk_space': 10, 'inode_limit': 100, 'enforce': True}
        self.website = types.SimpleNamespace(pk=7, domain='example.test',
            package=types.SimpleNamespace(diskSpace=10, inodeLimit=100, enforceDiskLimits=True))
        self.record = {'state': 'active', 'revision': 3, 'project_id': 51,
                       'identity': {'site_id': 7}, 'roots': [], 'mount': {'source': '/dev/fixture'},
                       'policy': copy.deepcopy(self.policy)}
        self.registry = {'version': 1, 'next_id': 52, 'sites': {'7': self.record}}
        self.saves = []

        @contextlib.contextmanager
        def registry(*unused, **kwargs):
            yield self.registry

        patches = [mock.patch.object(quota, '_registry', side_effect=registry),
                   mock.patch.object(quota, '_binding', return_value=self.record['mount']),
                   mock.patch.object(quota, '_site', return_value=self.website),
                   mock.patch.object(quota, '_save_registry', side_effect=lambda value: self.saves.append(copy.deepcopy(value))),
                   mock.patch.object(quota, '_set_limits', return_value={'verified': True})]
        self.mocks = [patch.start() for patch in patches]
        for patch in patches:
            self.addCleanup(patch.stop)

    def plan(self, **changes):
        plan = {key: copy.deepcopy(self.record[key]) for key in
                ('revision', 'project_id', 'identity', 'roots', 'mount')}
        plan.update(site_id=7, policy=copy.deepcopy(self.policy))
        plan.update(changes)
        return plan


class PolicyTests(_PolicyFixture):
    def test_unenrolled_prepare_does_not_probe_mount_or_mutate(self):
        self.registry['sites'].clear()
        self.assertIsNone(quota._prepare_policy(self.website, 10, 100))
        self.mocks[1].assert_not_called()
        self.mocks[4].assert_not_called()

    def test_pending_prepare_refuses_policy_changes(self):
        self.record['state'] = 'pending'
        with self.assertRaisesRegex(quota.StorageQuotaError, 'pending'):
            quota._prepare_policy(self.website, 10, 100)
        self.mocks[4].assert_not_called()

    def test_prospective_policy_can_be_prepared_without_database_save(self):
        plan = quota._prepare_policy(self.website, 20, 200, enforce=False)
        self.assertEqual(plan['policy'], {'disk_space': 20, 'inode_limit': 200, 'enforce': False})
        self.assertEqual(self.website.package.diskSpace, 10)

    def test_stale_revision_rejected_before_kernel_mutation(self):
        with self.assertRaisesRegex(quota.StorageQuotaError, 'stale'):
            quota._apply_policy(self.plan(revision=2))
        self.mocks[4].assert_not_called()

    def test_changed_current_package_rejected_before_kernel_mutation(self):
        self.website.package.diskSpace = 20
        with self.assertRaisesRegex(quota.StorageQuotaError, 'Package policy changed'):
            quota._apply_policy(self.plan())
        self.mocks[4].assert_not_called()

    def test_apply_marks_pending_before_kernel_then_active_after_verified_success(self):
        quota._apply_policy(self.plan())
        self.assertEqual([item['sites']['7']['state'] for item in self.saves], ['pending', 'active'])
        self.mocks[4].assert_called_once_with(self.record['mount'], 51, 10, 100)

    def test_failed_kernel_update_stays_pending(self):
        self.mocks[4].side_effect = OSError('injected quota failure')
        with self.assertRaises(OSError):
            quota._apply_policy(self.plan())
        self.assertEqual(self.record['state'], 'pending')
        self.assertEqual(self.saves[-1]['sites']['7']['state'], 'pending')

    def test_disabled_policy_clears_only_registered_project_limits(self):
        self.website.package.enforceDiskLimits = False
        plan = self.plan()
        plan['policy']['enforce'] = False
        quota._apply_policy(plan)
        self.mocks[4].assert_called_once_with(self.record['mount'], 51, 0, 0)

    def test_restore_is_refused_for_pending_and_disabled_enrollments(self):
        for state in ('active', 'pending', 'disabled'):
            self.record['state'] = state
            with self.assertRaisesRegex(quota.StorageQuotaError, 'legacy restore'):
                quota._assert_restore_allowed(self.website)

    def test_unenrolled_legacy_restore_unchanged(self):
        self.registry['sites'].clear()
        self.assertIsNone(quota._assert_restore_allowed(self.website))

    def test_domain_lifecycle_keeps_any_existing_enrollment(self):
        for state in ('active', 'pending', 'disabled'):
            self.record['state'] = state
            self.assertTrue(quota._has_enrollment(self.website))
        self.registry['sites'].clear()
        self.assertFalse(quota._has_enrollment(self.website))

    def test_unenrolled_status_never_claims_enforcement(self):
        self.registry['sites'].clear()
        result = quota._status(self.website)
        self.assertEqual(result['state'], 'unconfigured')
        self.assertFalse(result['enforced'])
        self.mocks[1].assert_not_called()

    def test_active_status_requires_matching_current_kernel_limits(self):
        with mock.patch.object(quota, '_get_quota', return_value={
                'bhard': 20480, 'bsoft': 20480, 'ihard': 100, 'isoft': 100,
                'space': 0, 'inodes': 1}):
            result = quota._status(self.website)
        self.assertEqual(result['state'], 'unsupported')
        self.assertFalse(result['enforced'])

    def test_active_status_requires_current_owned_roots(self):
        self.mocks[1].side_effect = quota.StorageQuotaError('root replaced')
        result = quota._status(self.website)
        self.assertEqual(result['state'], 'unsupported')
        self.assertFalse(result['enforced'])

    def test_active_status_exposes_capacity_not_security_boundary(self):
        with mock.patch.object(quota, '_get_quota', return_value={
                'bhard': 10240, 'bsoft': 10240, 'ihard': 100, 'isoft': 100,
                'space': 4096, 'inodes': 1}):
            result = quota._status(self.website)
        self.assertEqual(result['state'], 'active')
        self.assertTrue(result['enforced'])
        self.assertFalse(result['security_boundary'])

    def test_enrollment_requires_explicit_quiesced_confirmation(self):
        with mock.patch.object(quota, '_roots') as roots:
            with self.assertRaisesRegex(quota.StorageQuotaError, '--quiesced'):
                quota._enroll(self.website)
        roots.assert_not_called()


class KernelContractTests(unittest.TestCase):
    def test_xfs_accounting_only_is_not_enforced(self):
        mount = {'fstype': 'xfs', 'target': '/fixture', 'device': 123}
        result = types.SimpleNamespace(returncode=1, stdout='project quota on /fixture (/dev/loop1) is on\n')
        with mock.patch.object(quota.filesystemQuota, '_block_device', return_value=123):
            self.assertFalse(quota.project_enforced(result, mount))
            result.stdout = 'project quota on /fixture (/dev/loop1) is on (enforced)\n'
            self.assertTrue(quota.project_enforced(result, mount))

    def test_project_state_rejects_wrong_device_and_user_quota(self):
        mount = {'fstype': 'ext4', 'target': '/fixture', 'device': 123}
        result = types.SimpleNamespace(returncode=1, stdout='project quota on /fixture (/dev/loop1) is on\n')
        with mock.patch.object(quota.filesystemQuota, '_block_device', return_value=999):
            self.assertFalse(quota.project_enforced(result, mount))
        result.stdout = result.stdout.replace('project quota', 'user quota')
        with mock.patch.object(quota.filesystemQuota, '_block_device', return_value=123):
            self.assertFalse(quota.project_enforced(result, mount))

    def test_limit_setter_uses_block_units_and_does_not_overwrite_usage(self):
        captured = []

        def invoke(command, source, project_id, value):
            captured.append((command, source, project_id, value.valid, value.bhard,
                             value.bsoft, value.ihard, value.isoft, value.space, value.inodes))

        with mock.patch.object(quota, '_quota_call', side_effect=invoke), mock.patch.object(
                quota, '_get_quota', return_value={'bhard': 3072, 'bsoft': 3072, 'ihard': 40, 'isoft': 40}):
            quota._set_limits({'source': '/dev/fixture'}, 51, 3, 40)
        self.assertEqual(captured, [(0x800008, '/dev/fixture', 51, 5, 3072, 3072, 40, 40, 0, 0)])

    def test_limit_readback_mismatch_is_failure(self):
        with mock.patch.object(quota, '_quota_call'), mock.patch.object(
                quota, '_get_quota', return_value={'bhard': 0, 'bsoft': 0, 'ihard': 0, 'isoft': 0}):
            with self.assertRaisesRegex(quota.StorageQuotaError, 'readback'):
                quota._set_limits({'source': '/dev/fixture'}, 51, 3, 40)

    def test_allocator_skips_kernel_admin_and_previous_ids(self):
        registry = {'next_id': 50, 'sites': {'1': {'project_id': 52}}}
        with mock.patch.object(quota, '_reserved_ids', return_value={50}), mock.patch.object(
                quota, '_next_project', side_effect=lambda mount, candidate: 51 if candidate == 51 else None):
            self.assertEqual(quota._allocate(registry, {}), 53)
        self.assertEqual(registry['next_id'], 54)

    def test_next_project_accepts_both_end_of_enumeration_errors(self):
        for code in (errno.ENOENT, errno.ESRCH):
            with self.subTest(errno=code), mock.patch.object(
                    quota, '_quota_call', side_effect=OSError(code, 'No next quota record')):
                self.assertIsNone(quota._next_project({'source': '/dev/fixture'}, 51))

    def test_next_project_does_not_treat_other_kernel_failures_as_unused_ids(self):
        for code in (errno.EPERM, errno.EIO, errno.EINVAL):
            with self.subTest(errno=code), mock.patch.object(
                    quota, '_quota_call', side_effect=OSError(code, 'Quota query failed')):
                with self.assertRaises(quota.StorageQuotaError):
                    quota._next_project({'source': '/dev/fixture'}, 51)

    def test_allocator_refuses_unavailable_kernel_enumeration(self):
        registry = {'next_id': 50, 'sites': {}}
        with mock.patch.object(quota, '_reserved_ids', return_value=set()), mock.patch.object(
                quota, '_next_project', side_effect=quota.StorageQuotaError('unsupported')):
            with self.assertRaises(quota.StorageQuotaError):
                quota._allocate(registry, {})
        self.assertEqual(registry['next_id'], 50)

    def test_registry_does_not_follow_file_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            target = os.path.join(directory, 'target')
            with open(target, 'w') as stream:
                stream.write('private')
            link = os.path.join(directory, 'link')
            os.symlink(target, link)
            with self.assertRaises(OSError):
                quota._secure_open(link, os.O_RDONLY)

    def test_nested_same_device_mount_is_refused(self):
        roots = [{'path': '/fixture/web'}]
        mount = {'target': '/fixture'}
        result = types.SimpleNamespace(returncode=0, stderr='', stdout='{"filesystems":['
            '{"target":"/fixture","source":"/dev/loop1"},'
            '{"target":"/fixture/web/bind","source":"/dev/loop1[/foreign]"}]}')
        with mock.patch.object(quota.filesystemQuota, '_run', return_value=result), mock.patch.object(
                quota.filesystemQuota, '_tool', return_value='/usr/bin/findmnt'):
            with self.assertRaisesRegex(quota.StorageQuotaError, 'nested or changed mount'):
                quota._mount_tree(roots, mount)


class EnrollmentTests(_PolicyFixture):
    def setUp(self):
        super().setUp()
        self.record['roots'] = [{'path': '/fixture/web', 'kind': 'web', 'device': 1, 'inode': 4}]
        self.inventory = {'/fixture/web': {
            'path': '/fixture/web', 'device': 1, 'inode': 4, 'mode': stat.S_IFDIR | 0o700,
            'uid': 5001, 'gid': 5001, 'links': 2, 'size': 4096, 'mtime': 1,
            'attrs': (0, 0, 0, 0, 0)}}
        patches = [mock.patch.object(quota, '_roots', return_value=(self.record['identity'], self.record['roots'])),
                   mock.patch.object(quota, '_mount', return_value=self.record['mount']),
                   mock.patch.object(quota, '_mount_tree'),
                   mock.patch.object(quota, '_inventory', side_effect=lambda *args, **kwargs: copy.deepcopy(self.inventory)),
                   mock.patch.object(quota, '_tag'),
                   mock.patch.object(quota, '_identity', return_value=self.record['identity'])]
        self.enrollment_mocks = [patch.start() for patch in patches]
        for patch in patches:
            self.addCleanup(patch.stop)

    def test_stale_reviewed_plan_refused_before_assignment(self):
        with self.assertRaisesRegex(quota.StorageQuotaError, 'plan is stale'):
            quota._enroll(self.website, quiesced=True, plan={'inventory_sha256': 'stale'})
        self.enrollment_mocks[4].assert_not_called()
        self.assertEqual(self.saves, [])

    def test_interrupted_assignment_retains_pending_recoverable_record(self):
        self.enrollment_mocks[4].side_effect = OSError('injected interruption')
        with self.assertRaises(OSError):
            quota._enroll(self.website, quiesced=True)
        self.assertEqual(self.record['state'], 'pending')
        self.assertEqual(self.saves[-1]['sites']['7']['project_id'], 51)

    def test_unexpected_new_file_during_enrollment_stays_pending(self):
        changed = copy.deepcopy(self.inventory)
        changed['/fixture/web/new'] = dict(changed['/fixture/web'], path='/fixture/web/new', inode=9)
        self.enrollment_mocks[3].side_effect = [copy.deepcopy(self.inventory), changed]
        with self.assertRaisesRegex(quota.StorageQuotaError, 'membership changed'):
            quota._enroll(self.website, quiesced=True)
        self.assertEqual(self.record['state'], 'pending')
        self.mocks[4].assert_not_called()

    def test_duplicate_internal_hardlink_tagged_only_once(self):
        first = dict(self.inventory['/fixture/web'], path='/fixture/web/one', inode=9,
                     mode=stat.S_IFREG | 0o600, links=2)
        self.inventory['/fixture/web/one'] = first
        self.inventory['/fixture/web/two'] = dict(first, path='/fixture/web/two')
        quota._enroll(self.website, quiesced=True)
        self.assertEqual(self.enrollment_mocks[4].call_count, 2)
        self.assertEqual(self.record['state'], 'active')

    def test_pending_enrollment_resumes_using_same_project_id(self):
        self.record['state'] = 'pending'
        with mock.patch.object(quota, '_allocate') as allocate:
            result = quota._enroll(self.website, quiesced=True)
        allocate.assert_not_called()
        self.assertEqual(result['project_id'], 51)
        self.assertEqual(self.record['state'], 'active')


class MailScopeTests(_PolicyFixture):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.mail_root = os.path.realpath(self.directory.name)
        self.website.childdomains_set = types.SimpleNamespace(all=lambda: [])
        self.record['roots'] = [{'path': '/fixture/web', 'kind': 'web', 'device': 1, 'inode': 4}]
        patches = [mock.patch.object(quota, '_identity', return_value=self.record['identity']),
                   mock.patch.object(quota.storageAccounting, 'MAIL_ROOT', self.mail_root),
                   mock.patch.object(quota.storageAccounting, 'owned_mail_domains',
                                     return_value=[types.SimpleNamespace(domain='example.test')]),
                   mock.patch.object(quota, '_mount', return_value=self.record['mount']),
                   mock.patch.object(quota, '_mount_tree'), mock.patch.object(quota, '_inventory'),
                   mock.patch.object(quota, '_verify_limits'),
                   mock.patch.object(quota.pwd, 'getpwnam',
                                     return_value=types.SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid())),
                   mock.patch.object(quota, '_inode_record', return_value={'attrs': (0, 0, 0, 0, 0)}),
                   mock.patch.object(quota, '_tag'), mock.patch.object(quota.os, 'chown')]
        self.mail_mocks = [patch.start() for patch in patches]
        for patch in patches:
            self.addCleanup(patch.stop)

    def test_unowned_mail_domain_rejected_before_directory_creation(self):
        with self.assertRaisesRegex(quota.StorageQuotaError, 'does not belong'):
            quota._ensure_mail_domain('other.test', self.website)
        self.assertEqual(os.listdir(self.mail_root), [])
        self.mail_mocks[9].assert_not_called()

    def test_unenrolled_website_cannot_reuse_another_enrollments_mail_root(self):
        self.registry['sites'] = {'8': {'roots': [{'path': os.path.join(self.mail_root, 'example.test')}]}}
        with self.assertRaisesRegex(quota.StorageQuotaError, 'reserved by another'):
            quota._ensure_mail_domain('example.test', self.website)
        self.assertEqual(os.listdir(self.mail_root), [])

    def test_nonempty_unregistered_mail_root_requires_maintenance(self):
        target = os.path.join(self.mail_root, 'example.test')
        os.mkdir(target)
        with open(os.path.join(target, 'existing-mail'), 'w') as stream:
            stream.write('existing mail')
        with self.assertRaisesRegex(quota.StorageQuotaError, 'Existing mail data'):
            quota._ensure_mail_domain('example.test', self.website)
        self.assertEqual(self.saves, [])
        self.mail_mocks[9].assert_not_called()

    def test_new_root_tags_before_vmail_ownership_and_final_activation(self):
        order = []
        self.mail_mocks[9].side_effect = lambda *args: order.append('project')
        self.mail_mocks[10].side_effect = lambda *args, **kwargs: order.append('owner')
        result = quota._ensure_mail_domain('example.test', self.website)
        self.assertTrue(result['created'])
        self.assertEqual(order, ['project', 'owner'])
        self.assertEqual([value['sites']['7']['state'] for value in self.saves], ['pending', 'active'])

    def test_failed_new_root_preparation_stays_pending_before_account_activation(self):
        self.mail_mocks[10].side_effect = OSError('injected ownership failure')
        with self.assertRaises(OSError):
            quota._ensure_mail_domain('example.test', self.website)
        self.assertEqual(self.record['state'], 'pending')
        self.assertTrue(os.path.isdir(os.path.join(self.mail_root, 'example.test')))


if __name__ == '__main__':
    unittest.main()
