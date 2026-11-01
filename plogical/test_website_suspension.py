"""Configuration safety and rollback tests without an installed panel."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from plogical.websiteSuspension import (
    START, VhostUpdate, render_suspension, validate_domain, normalize_action,
)
from plogical.schemaMigration import ensure_child_domain_state


VHOST = '''docRoot /home/example/public_html
rewrite {
  enable 1
  autoLoadHtaccess 1
  rules <<<END_rules
RewriteCond %{REQUEST_URI} !^/health$
RewriteRule ^ /index.php [L]
END_rules
}
context /api {
  type proxy
  handler api
}
'''


class SuspensionRenderingTests(unittest.TestCase):
    def test_customized_legacy_page_is_preserved_and_missing_page_uses_bundled_default(self):
        with mock.patch('plogical.websiteSuspension.Path.is_file', return_value=True):
            self.assertIn('location /usr/local/CyberCP/websiteFunctions/suspension.html',
                          render_suspension(VHOST, True))
        with mock.patch('plogical.websiteSuspension.Path.is_file', return_value=False):
            self.assertIn('location /usr/local/CyberCP/websiteFunctions/suspension-default.html',
                          render_suspension(VHOST, True))
    def test_existing_api_and_cli_action_spellings_remain_supported(self):
        for value in ('Unsuspend', 'UnSuspend', 'Un-Suspend', 'UNSUSPEND'):
            self.assertEqual(normalize_action(value), 'Un-Suspend')
        self.assertEqual(normalize_action('SUSPEND'), 'Suspend')
    def test_repeated_suspend_and_restore_preserve_original_rules_exactly(self):
        suspended = render_suspension(VHOST, True)
        self.assertEqual(suspended, render_suspension(suspended, True))
        self.assertEqual(VHOST, render_suspension(suspended, False))
        self.assertEqual(VHOST, render_suspension(VHOST, False))
        self.assertEqual(suspended.count(START), 1)
        self.assertIn('context /api {', suspended)

    def test_rewrite_heredoc_literal_braces_and_hash_do_not_confuse_block_parser(self):
        original = VHOST.replace('RewriteCond %{REQUEST_URI} !^/health$',
            'RewriteRule ^literal\\{ /destination#fragment [L]\nRewriteRule ^literal} /other [L]')
        self.assertEqual(render_suspension(render_suspension(original, True), False), original)

    def test_crlf_rules_restore_without_changing_line_endings(self):
        original = VHOST.replace('\n', '\r\n')
        self.assertEqual(render_suspension(render_suspension(original, True), False), original)

    def test_existing_root_context_is_preserved_with_one_global_rewrite(self):
        original = VHOST + 'context / {\n  allowBrowse 1\n  rewrite {\n    enable 1\n  }\n}\n'
        suspended = render_suspension(original, True)
        self.assertEqual(suspended.count('\ncontext / {'), 1)
        self.assertEqual(suspended.count('\nrewrite {'), 1)
        self.assertEqual(render_suspension(suspended, False), original)

    def test_edits_to_unrelated_configuration_while_suspended_survive_restore(self):
        suspended = render_suspension(VHOST, True) + 'errorlog /tmp/new-error.log\n'
        self.assertEqual(render_suspension(suspended, False),
                         VHOST + 'errorlog /tmp/new-error.log\n')

    def test_legacy_disabled_rewrite_is_restored(self):
        legacy = ('# Website Suspension Configuration\ncontext / {\n}\n'
                  '# End Website Suspension Configuration\n'
                  '# Commented out during suspension\n#rewrite {\n#  enable 1\n#}\n'
                  '# Leave this unrelated comment disabled\n'
                  'docRoot /home/example/public_html\n')
        self.assertEqual(render_suspension(legacy, False),
                         'rewrite {\n  enable 1\n}\n# Leave this unrelated comment disabled\n'
                         'docRoot /home/example/public_html\n')

    def test_unclosed_rewrite_fails_before_any_configuration_is_returned(self):
        with self.assertRaisesRegex(ValueError, 'Unclosed'):
            render_suspension('rewrite {\n enable 1\n', True)

    def test_paths_and_shell_fragments_are_rejected(self):
        for domain in ('../example', 'example/other', 'example;id', 'a..test',
                       '-a.test', 'a-.test', 'x\n.test', '', None):
            with self.subTest(domain=domain), self.assertRaises(ValueError):
                validate_domain(domain)
        self.assertEqual(validate_domain('child.example.test'), 'child.example.test')


class VhostUpdateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.paths = {}
        for domain in ('parent.test', 'child.test', 'sibling.test'):
            path = self.root / 'conf' / 'vhosts' / domain / 'vhost.conf'
            path.parent.mkdir(parents=True)
            path.write_text(VHOST)
            self.paths[domain] = path
        self.check = mock.Mock()
        self.reload = mock.Mock()

    def update(self):
        return VhostUpdate(self.root, self.check, self.reload)

    def test_individual_child_update_leaves_parent_and_sibling_untouched(self):
        with self.update() as update:
            update.apply([('child.test', True)])
        self.assertIn(START, self.paths['child.test'].read_text())
        self.assertEqual(self.paths['parent.test'].read_text(), VHOST)
        self.assertEqual(self.paths['sibling.test'].read_text(), VHOST)
        self.check.assert_called_once_with()
        self.reload.assert_called_once_with()

    def test_identical_repeated_operation_needs_no_server_reload(self):
        with self.update() as update:
            update.apply([('child.test', True)])
        self.check.reset_mock()
        self.reload.reset_mock()
        with self.update() as update:
            update.apply([('child.test', True)])
        self.check.assert_not_called()
        self.reload.assert_not_called()

    def test_failed_config_validation_restores_all_originals(self):
        self.check.side_effect = [RuntimeError('invalid new configuration'), None]
        with self.assertRaisesRegex(RuntimeError, 'invalid new'):
            with self.update() as update:
                update.apply([('parent.test', True), ('child.test', True)])
        for path in self.paths.values():
            self.assertEqual(path.read_text(), VHOST)
        self.reload.assert_called_once_with()  # Recovery only.

    def test_failed_reload_restores_all_originals_and_reloads_original_config(self):
        self.reload.side_effect = [RuntimeError('reload failed'), None]
        with self.assertRaisesRegex(RuntimeError, 'reload failed'):
            with self.update() as update:
                update.apply([('parent.test', True), ('child.test', True)])
        for path in self.paths.values():
            self.assertEqual(path.read_text(), VHOST)
        self.assertEqual(self.reload.call_count, 2)

    def test_database_commit_failure_after_activation_rolls_back_configuration(self):
        with self.assertRaisesRegex(RuntimeError, 'database commit'):
            with self.update() as update:
                update.apply([('child.test', True)])
                raise RuntimeError('database commit failed')
        self.assertEqual(self.paths['child.test'].read_text(), VHOST)
        self.assertEqual(self.reload.call_count, 2)

    def test_missing_child_config_fails_before_parent_is_modified(self):
        with self.assertRaises(FileNotFoundError):
            with self.update() as update:
                update.apply([('parent.test', True), ('missing.test', True)])
        self.assertEqual(self.paths['parent.test'].read_text(), VHOST)
        self.check.assert_not_called()
        self.reload.assert_not_called()

    def test_mid_write_failure_rolls_back_already_written_vhosts(self):
        from plogical.websiteSuspension import atomic_write
        calls = [0]
        def flaky_write(*args):
            calls[0] += 1
            if calls[0] == 2:
                raise OSError('disk write failed')
            return atomic_write(*args)
        with mock.patch('plogical.websiteSuspension.atomic_write', side_effect=flaky_write):
            with self.assertRaisesRegex(OSError, 'disk write'):
                with self.update() as update:
                    update.apply([('parent.test', True), ('child.test', True)])
        for path in self.paths.values():
            self.assertEqual(path.read_text(), VHOST)


class ChildStateSchemaTests(unittest.TestCase):
    def test_existing_column_does_not_change_existing_states(self):
        connection, cursor = mock.Mock(), mock.Mock()
        cursor.fetchone.return_value = ('state',)
        ensure_child_domain_state(connection, cursor)
        self.assertFalse(any(call.args[0].startswith('ALTER') for call in cursor.execute.call_args_list))
        connection.commit.assert_not_called()

    def test_legacy_schema_gets_active_independent_default_and_readback(self):
        connection, cursor = mock.Mock(), mock.Mock()
        cursor.fetchone.side_effect = [None, ('state',)]
        ensure_child_domain_state(connection, cursor)
        self.assertIn('ADD state integer NOT NULL DEFAULT 1', cursor.execute.call_args_list[1].args[0])
        connection.commit.assert_called_once_with()

    def test_unsuccessful_column_creation_aborts_upgrade(self):
        connection, cursor = mock.Mock(), mock.Mock()
        cursor.fetchone.return_value = None
        with self.assertRaisesRegex(RuntimeError, 'state is missing'):
            ensure_child_domain_state(connection, cursor)


if __name__ == '__main__':
    unittest.main()
