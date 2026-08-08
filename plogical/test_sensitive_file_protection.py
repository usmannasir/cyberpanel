import os
import stat
import tempfile
import unittest

from plogical.sensitiveFileProtection import BEGIN_MARKER, protect_vhost_file, protect_vhost_tree
from plogical.vhostConfs import vhostConfs


class SensitiveFileProtectionTests(unittest.TestCase):

    def test_new_vhost_templates_contain_denials(self):
        template_names = (
            'olsMasterConf', 'olsChildConf', 'lswsMasterConf', 'lswsChildConf',
            'apacheConf', 'apacheConfSSL', 'apacheConfChild', 'apacheConfChildSSL',
        )
        for name in template_names:
            self.assertIn(BEGIN_MARKER, getattr(vhostConfs, name), name)

    def test_existing_vhost_is_updated_once_and_preserves_mode(self):
        content = (
            'docRoot /tmp\n'
            'rewrite  {\n'
            '  enable                  1\n'
            '  autoLoadHtaccess        1\n'
            '}\n'
        )
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'vhost.conf')
            with open(path, 'w') as handle:
                handle.write(content)
            os.chmod(path, 0o640)

            self.assertEqual(1, protect_vhost_file(path))
            self.assertEqual(0, protect_vhost_file(path))
            with open(path) as handle:
                protected = handle.read()

            self.assertEqual(1, protected.count(BEGIN_MARKER))
            self.assertIn(r'RewriteRule (^|/)\.git(/|$) - [F,L]', protected)
            self.assertEqual(0o640, stat.S_IMODE(os.stat(path).st_mode))

    def test_existing_site_rules_remain_after_denials(self):
        content = (
            'rewrite  {\n'
            '  enable                  1\n'
            '  autoLoadHtaccess        1\n'
            '  rules                   <<<END_rules\n'
            'RewriteRule ^/old$ /new [L]\n'
            '  END_rules\n'
            '}\n'
        )
        with tempfile.NamedTemporaryFile('w', delete=False) as handle:
            handle.write(content)
            path = handle.name
        try:
            self.assertEqual(1, protect_vhost_file(path))
            with open(path) as handle:
                protected = handle.read()
            self.assertLess(protected.index(BEGIN_MARKER), protected.index('RewriteRule ^/old$'))
        finally:
            os.unlink(path)

    def test_nested_rules_are_not_used_for_global_denials(self):
        content = (
            'rewrite  {\n'
            '  enable                  1\n'
            '  autoLoadHtaccess        1\n'
            '}\n'
            'context /private {\n'
            '  rewrite {\n'
            '    enable                1\n'
            '    rules                 <<<END_private\n'
            'RewriteRule ^/old$ /new [L]\n'
            '    END_private\n'
            '  }\n'
            '}\n'
        )
        with tempfile.NamedTemporaryFile('w', delete=False) as handle:
            handle.write(content)
            path = handle.name
        try:
            self.assertEqual(1, protect_vhost_file(path))
            with open(path) as handle:
                protected = handle.read()
            self.assertLess(protected.index(BEGIN_MARKER), protected.index('context /private'))
        finally:
            os.unlink(path)

    def test_vhost_tree_reports_updates_and_skips(self):
        with tempfile.TemporaryDirectory() as root:
            for name in ('one.test', 'two.test'):
                directory = os.path.join(root, name)
                os.mkdir(directory)
                with open(os.path.join(directory, 'vhost.conf'), 'w') as handle:
                    handle.write('docRoot /tmp\n')
            first = protect_vhost_tree(root)
            second = protect_vhost_tree(root)
            self.assertEqual(2, first['updated'])
            self.assertEqual(2, second['skipped'])


if __name__ == '__main__':
    unittest.main()
