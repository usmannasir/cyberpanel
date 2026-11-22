"""Website limits reach root's commands and configuration only as plain numbers and known units."""
import ast
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SOURCE = Path(__file__).resolve().parent / 'views.py'
LIMITS = {'domain': 'shop.example', 'cpuPers': 50, 'IO': 10, 'IOPS': 1000, 'memory': 512,
          'networkSpeed': 100, 'networkHandle': 'mbit', 'enforce': True}


def save(**changes):
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    view = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'saveWebsiteLimits')
    view.decorator_list = []
    services = {name: mock.Mock(name=name) for name in (
        'ACLManager', 'Websites', 'ContainerLimits', 'ProcessUtilities', 'ContainerManager', 'httpProc', 'os')}
    services['ACLManager'].loadedACL.return_value = {'admin': 1}
    services['httpProc'].AJAX.side_effect = lambda status, message: (status, message)
    services['Websites'].objects.get.return_value = SimpleNamespace(domain='stored.example', externalApp='store1234')
    services['ContainerLimits'].objects.get.return_value = mock.Mock(enforce=1, id=4, networkHexValue='0x10004')
    services['ContainerManager'].prepConf.return_value = 'group store1234 {}\n'
    services['ProcessUtilities'].outputExecutioner.return_value = ''
    scope = dict(services, json=json, HttpResponse=mock.Mock(), redirect=mock.Mock(), loadLoginPage=mock.Mock(),
                 randint=lambda low, high: 4321, multiprocessing=SimpleNamespace(cpu_count=lambda: 2),
                 open=mock.mock_open())
    exec(compile(ast.Module(body=[view], type_ignores=[]), 'views.py', 'exec'), scope)
    request = SimpleNamespace(session={'userID': 1}, body=json.dumps(dict(LIMITS, **changes)).encode())
    return scope['saveWebsiteLimits'](request), services


class LimitValueTests(unittest.TestCase):
    def assert_refused(self, **changes):
        answer, services = save(**changes)
        self.assertEqual(0, answer[0], changes)
        services['Websites'].objects.get.assert_not_called()
        services['ProcessUtilities'].executioner.assert_not_called()
        services['ContainerManager'].assert_not_called()

    def test_a_limit_that_is_not_a_whole_number_is_refused(self):
        for field in ('cpuPers', 'IO', 'IOPS', 'memory', 'networkSpeed'):
            for value in ('5; id', '5', 1.5, -1, True, None, [5], {'a': 1}, '5\n}', 10 ** 10):
                with self.subTest(field=field, value=value):
                    self.assert_refused(**{field: value})

    def test_an_unknown_unit_is_refused(self):
        for unit in ('mbit; id', 'mbit burst 1', '', None, 7, ['mbit'], 'MBIT', 'mbit\n'):
            with self.subTest(unit=unit):
                self.assert_refused(networkHandle=unit)

    def test_the_units_the_page_offers_are_accepted(self):
        for unit in ('kbps', 'mbit'):
            with self.subTest(unit=unit):
                answer, services = save(networkHandle=unit)
                arguments = services['ContainerManager'].call_args[0][3]
                self.assertEqual('100' + unit, arguments['rateLimit'])

    def test_the_configuration_file_is_named_after_the_stored_website(self):
        answer, services = save(domain='STORED.example ')
        services['Websites'].objects.get.assert_called_once_with(domain='STORED.example ')
        commands = [call[0][0] for call in services['ProcessUtilities'].executioner.call_args_list]
        self.assertIn('sudo mv /home/cyberpanel/4321 /etc/cgconfig.d/stored.example', commands)
        for command in commands:
            self.assertNotIn('STORED', command)

    def test_removing_the_limits_names_the_stored_website_too(self):
        answer, services = save(domain='STORED.example ', enforce=False)
        commands = [call[0][0] for call in services['ProcessUtilities'].executioner.call_args_list]
        self.assertIn('sudo rm /etc/cgconfig.d/stored.example', commands)

    def test_the_cpu_limit_is_still_capped_at_one_hundred(self):
        answer, services = save(cpuPers=101)
        self.assertEqual((0, 'CPU Percentage can not be greater then 100%'), answer)


if __name__ == '__main__':
    unittest.main(verbosity=2)
