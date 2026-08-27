import os
import tempfile
from unittest import mock

from django.test import SimpleTestCase

from plogical.modSec import modSec


class OWASPConfigurationTests(SimpleTestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(
            self.directory.name, 'httpd_config.conf'
        )
        self.master_path = os.path.join(
            self.directory.name, 'owasp-master.conf'
        )
        with open(self.master_path, 'w') as master:
            master.write('include rules.conf\n')

    def tearDown(self):
        self.directory.cleanup()

    def write_config(self, content):
        with open(self.config_path, 'w') as config:
            config.write(content)

    def test_enables_owasp_after_the_base_rules_file_once(self):
        self.write_config(
            'module mod_security {\n'
            'modsecurity on\n'
            'modsecurity_rules_file /usr/local/lsws/conf/modsec/rules.conf\n'
            '}\n'
        )
        with mock.patch.object(
            modSec,
            'OWASP_DIRECTIVE',
            'modsecurity_rules_file ' + self.master_path,
        ):
            modSec.enableOWASPForOLS(self.config_path)
            modSec.enableOWASPForOLS(self.config_path)
            self.assertTrue(modSec.isOWASPEnabled(self.config_path))

        with open(self.config_path) as config:
            body = config.read()
        self.assertEqual(1, body.count(self.master_path))
        self.assertLess(body.index('rules.conf'), body.index(self.master_path))

    def test_enables_owasp_inside_a_module_without_base_rules_line(self):
        self.write_config('module mod_security {\nmodsecurity on\n}\n')
        with mock.patch.object(
            modSec,
            'OWASP_DIRECTIVE',
            'modsecurity_rules_file ' + self.master_path,
        ):
            modSec.enableOWASPForOLS(self.config_path)

        with open(self.config_path) as config:
            lines = config.read().splitlines()
        self.assertEqual(
            'modsecurity_rules_file ' + self.master_path,
            lines[-2],
        )
        self.assertEqual('}', lines[-1])

    def test_rejects_activation_when_modsecurity_is_not_configured(self):
        self.write_config('listener Default {\n}\n')
        with self.assertRaisesRegex(RuntimeError, 'must be installed'):
            modSec.enableOWASPForOLS(self.config_path)

    def test_commented_directive_is_not_treated_as_enabled(self):
        self.write_config('# ' + modSec.OWASP_DIRECTIVE + '\n')
        self.assertFalse(modSec.isOWASPEnabled(self.config_path))

    def test_detects_active_directive_from_privileged_config_output(self):
        config_lines = [
            'module mod_security {',
            modSec.OWASP_DIRECTIVE,
            '}',
        ]
        self.assertTrue(modSec.hasActiveOWASPDirective(config_lines))
