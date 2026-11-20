"""Cron entries are selected by a whole number, and website users can start the panel's interpreter."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from plogical.test_child_domain_conversion import load_method

ROOT = Path(__file__).resolve().parents[1]


class CronLineTests(unittest.TestCase):
    def handler(self, name):
        self.commands = Mock()
        self.commands.outputExecutioner.return_value = '1,None'
        acl = Mock()
        acl.checkOwnership.return_value = 1
        acl.loadedACL.return_value = {'admin': 1}
        website = SimpleNamespace(externalApp='examp1234')
        return load_method('websiteFunctions/website.py', 'WebsiteManager', name, dict(
            ACLManager=acl, Administrator=Mock(), ProcessUtilities=self.commands, json=json,
            shlex=__import__('shlex'), Websites=SimpleNamespace(objects=SimpleNamespace(get=lambda **k: website)),
            virtualHostUtilities=SimpleNamespace(cyberPanel='/usr/local/CyberCP'),
            validators=Mock(), CronUtil=Mock(),
            HttpResponse=lambda content: SimpleNamespace(content=content.encode())))

    def data(self, line):
        return {'domain': 'example.com', 'line': line, 'minute': '0', 'hour': '1', 'monthday': '*',
                'month': '*', 'weekday': '*', 'cronCommand': 'php /home/example.com/public_html/cron.php'}

    def test_value_that_is_not_a_whole_number_runs_nothing(self):
        for name in ('saveCronChanges', 'remCronbyLine', 'getCronbyLine'):
            handler = self.handler(name)
            for line in ('1 --externalApp root', '1; id', {'a': '$(id)'}, ['1'], ' 2', 1.5, True, 0, -3, None):
                result = json.loads(handler(SimpleNamespace(domain='example.com'), userID=7,
                                            data=self.data(line)).content)
                self.assertNotEqual(1, result.get('getWebsiteCron'), (name, line))
                self.commands.outputExecutioner.assert_not_called()
                self.commands.executioner.assert_not_called()

    def test_whole_number_is_passed_on(self):
        for name in ('saveCronChanges', 'remCronbyLine'):
            handler = self.handler(name)
            handler(SimpleNamespace(domain='example.com'), userID=7, data=self.data('3'))
            command = self.commands.outputExecutioner.call_args.args[0]
            self.assertIn(' --externalApp examp1234 --line 3', command)


class RuntimeModeTests(unittest.TestCase):
    def test_installer_and_upgrader_leave_the_interpreter_configuration_readable_by_website_users(self):
        installer = (ROOT / 'cyberpanel.sh').read_text()
        self.assertNotIn('chmod 0640 /usr/local/CyberCP/pyvenv.cfg', installer)
        self.assertEqual(2, installer.count('chmod 0644 /usr/local/CyberCP/pyvenv.cfg'))
        upgrader = (ROOT / 'plogical' / 'upgrade.py').read_text()
        self.assertIn('command = "chmod 644 /usr/local/CyberCP/pyvenv.cfg"', upgrader)


if __name__ == '__main__':
    unittest.main()
