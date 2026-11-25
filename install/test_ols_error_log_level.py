"""A fresh install writes OpenLiteSpeed's server error log at NOTICE, kept 14 days."""
import ast
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).resolve().parent / 'installCyberPanel.py'

# The package's own httpd_config.conf as found on a fresh Ubuntu 26.04 install (3.0.21).
PACKAGE_CONFIG = """serverName
user                      nobody
errorlog logs/error.log {
        logLevel             DEBUG
        debugLevel           0
        rollingSize          10M
        enableStderrLog      1
}

accesslog logs/access.log {
        rollingSize          10M
        keepDays             30
        compressArchive      0
}
"""


def quiet_error_log():
    tree = ast.parse(SOURCE.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'quiet_error_log')
    namespace = {'re': re}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace['quiet_error_log']


class QuietErrorLogTests(unittest.TestCase):

    def setUp(self):
        self.quiet = quiet_error_log()

    def test_package_configuration(self):
        result = self.quiet(PACKAGE_CONFIG)
        error_block = result[result.index('errorlog'):result.index('}') + 1]
        self.assertIn('logLevel             NOTICE', error_block)
        self.assertNotIn('DEBUG', error_block)
        self.assertRegex(error_block, r'\n  keepDays\s+14\n}$')
        # Everything outside the error log block is unchanged.
        self.assertEqual(PACKAGE_CONFIG[PACKAGE_CONFIG.index('\naccesslog'):], result[result.index('\naccesslog'):])
        self.assertTrue(result.startswith('serverName\nuser                      nobody\nerrorlog logs/error.log {\n'))

    def test_running_it_again_changes_nothing(self):
        once = self.quiet(PACKAGE_CONFIG)
        self.assertEqual(once, self.quiet(once))

    def test_an_explicit_retention_and_level_are_kept(self):
        config = 'errorlog logs/error.log {\n  logLevel WARN\n  keepDays 3\n}\n'
        self.assertEqual(config, self.quiet(config))

    def test_a_configuration_without_an_error_log_is_unchanged(self):
        config = 'accesslog logs/access.log {\n  keepDays 30\n}\n'
        self.assertEqual(config, self.quiet(config))

    def test_the_install_step_uses_it(self):
        source = SOURCE.read_text()
        step = source[source.index('    def fix_ols_configs(self):'):source.index('    def changePortTo80(self):')]
        self.assertIn('quiet_error_log(', step)


if __name__ == '__main__':
    unittest.main()
