"""The tuning worker writes whole numbers, sizes and fixed words only, for a website or PHP it can name."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

OLS, ENTERPRISE = 'ols', 'lsws'
NOT_A_NUMBER = ('10 --persistConn Enable', '10;id', '10\n', '10\r5', '-1', '+1', '1.5', '1e3', '', ' 10', None, 1.5,
                True, [10], '1234567890123')
NOT_A_SIZE = ('2047M;id', '2047M 1', '2047MB', '-1M', '2.5G', 'M', '', None, 1.5, True, ['1M'])
NOT_A_SWITCH = ('enable', 'Enabled', 'Enable ', '1', 'Enable --maxConns 9', '', None, True, ['Enable'])
NOT_A_DOMAIN = ('example.test/../other.test', '../other.test', 'example.test other.test', 'example.test;id',
                'example.test\n', '', None, 7, ['example.test'])
VHOST = ('docRoot                   $VH_ROOT/public_html\nextprocessor example {\n  type                    lsapi\n'
         '  maxConns                10\n  initTimeout             600\n  persistConn             1\n'
         '  memSoftLimit            2047M\n  memHardLimit            2047M\n  procSoftLimit           400\n'
         '  procHardLimit           500\n}\n')


def load_tuning(server=OLS, root='/usr/local/lsws'):
    """plogical/tuning.py as a module, with the server and the other panel modules replaced."""
    process = mock.Mock(OLS=OLS)
    process.decideServer.return_value = server
    logger = mock.Mock()
    package = types.ModuleType('plogical')
    package.__path__ = []
    stubs = {'plogical': package}
    for name, attribute, value in (
            ('plogical.CyberCPLogFileWriter', 'CyberCPLogFileWriter', logger),
            ('plogical.installUtilities', 'installUtilities', types.SimpleNamespace(Server_root_path=root)),
            ('plogical.processUtilities', 'ProcessUtilities', process)):
        module = types.ModuleType(name)
        setattr(module, attribute, value)
        stubs[name] = module
        setattr(package, name.split('.')[-1], module)
    source = Path(__file__).with_name('tuning.py')
    spec = importlib.util.spec_from_file_location('_tuning_under_test', source)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict('sys.modules', stubs):
        spec.loader.exec_module(module)
    return module, process


class TuningValueTests(unittest.TestCase):
    def setUp(self):
        self.module, self.process = load_tuning()
        self.tuning = self.module.tuning

    def test_whole_numbers(self):
        for value, text in ((10, '10'), ('10', '10'), (0, '0'), ('007', '7')):
            self.assertEqual(text, self.tuning.wholeNumber(value, 'x'))
        for value in NOT_A_NUMBER:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'Invalid value for x'):
                    self.tuning.wholeNumber(value, 'x')

    def test_sizes(self):
        for value, text in (('2047M', '2047M'), ('512k', '512k'), ('1G', '1G'), (20, '20'), ('20', '20')):
            self.assertEqual(text, self.tuning.memorySize(value, 'x'))
        for value in NOT_A_SIZE:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'Invalid value for x'):
                    self.tuning.memorySize(value, 'x')

    def test_switches(self):
        self.assertEqual('Enable', self.tuning.enableOrDisable('Enable', 'x'))
        self.assertEqual('Disable', self.tuning.enableOrDisable('Disable', 'x'))
        for value in NOT_A_SWITCH:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.tuning.enableOrDisable(value, 'x')

    def test_target_is_a_domain_on_openlitespeed_and_a_litespeed_php_on_enterprise(self):
        self.assertEqual('example.test', self.tuning.phpTuningTarget('example.test'))
        for value in NOT_A_DOMAIN:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.tuning.phpTuningTarget(value)
        enterprise = load_tuning(ENTERPRISE)[0].tuning
        self.assertEqual('lsphp83', enterprise.phpTuningTarget('lsphp83'))
        for value in ('example.test', 'lsphp83</name>', 'lsphp', 'lsphp83 x', '../lsphp83', None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    enterprise.phpTuningTarget(value)


class TuningWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='tuning-worker-test-')
        self.addCleanup(self.temp.cleanup)
        self.module, self.process = load_tuning(root=self.temp.name)
        self.tuning = self.module.tuning
        self.vhost = Path(self.temp.name) / 'conf' / 'vhosts' / 'example.test' / 'vhost.conf'
        self.vhost.parent.mkdir(parents=True)
        self.vhost.write_text(VHOST)
        self.server = Path(self.temp.name) / 'httpd_config.conf'

    def tune(self, virtualHost='example.test', maxConns='20', initTimeout='60', persistConn='Disable',
             memSoftLimit='1024M', memHardLimit='1024M', procSoftLimit='300', procHardLimit='400'):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.tuning.tunePHP(virtualHost, maxConns, initTimeout, persistConn, memSoftLimit, memHardLimit,
                                procSoftLimit, procHardLimit)
        return output.getvalue()

    def test_checked_values_are_written(self):
        self.assertEqual('1,None\n', self.tune())
        lines = self.vhost.read_text().splitlines()
        self.assertEqual(VHOST.splitlines()[:3], lines[:3])
        self.assertEqual(
            [['maxConns', '20'], ['initTimeout', '60'], ['persistConn', '0'], ['memSoftLimit', '1024M'],
             ['memHardLimit', '1024M'], ['procSoftLimit', '300'], ['procHardLimit', '400'], ['}']],
            [line.split() for line in lines[3:]])

    def test_a_refused_value_leaves_the_configuration_alone(self):
        cases = [('maxConns', NOT_A_NUMBER), ('initTimeout', NOT_A_NUMBER), ('procSoftLimit', NOT_A_NUMBER),
                 ('procHardLimit', NOT_A_NUMBER), ('memSoftLimit', NOT_A_SIZE), ('memHardLimit', NOT_A_SIZE),
                 ('persistConn', NOT_A_SWITCH), ('virtualHost', NOT_A_DOMAIN)]
        with mock.patch.object(self.module, 'open', side_effect=AssertionError('a file was opened'), create=True):
            for name, values in cases:
                for value in values:
                    with self.subTest(name=name, value=value):
                        self.assertTrue(self.tune(**{name: value}).startswith('0,'))
        self.assertEqual(VHOST, self.vhost.read_text())

    def test_server_tuning_refuses_values_before_opening_the_configuration(self):
        good = dict(maxConn='2000', maxSSLConn='1000', connTime='300', keepAlive='5', inMemCache='20M',
                    gzip='Enable')
        cases = [('maxConn', NOT_A_NUMBER), ('maxSSLConn', NOT_A_NUMBER), ('connTime', NOT_A_NUMBER),
                 ('keepAlive', NOT_A_NUMBER), ('inMemCache', NOT_A_SIZE), ('gzip', NOT_A_SWITCH)]
        with mock.patch.object(self.module, 'open', side_effect=AssertionError('a file was opened'), create=True):
            for name, values in cases:
                for value in values:
                    with self.subTest(name=name, value=value):
                        arguments = dict(good, **{name: value})
                        with contextlib.redirect_stdout(io.StringIO()) as output:
                            self.tuning.saveTuningDetails(*[arguments[key] for key in (
                                'maxConn', 'maxSSLConn', 'connTime', 'keepAlive', 'inMemCache', 'gzip')])
                        self.assertTrue(output.getvalue().startswith('0,Invalid value'), output.getvalue())

    def test_reading_runs_one_command_for_a_domain_and_none_for_other_text(self):
        self.process.outputExecutioner.return_value = VHOST
        self.assertEqual('10', self.tuning.fetchPHPDetails('example.test')['maxConns'])
        self.process.outputExecutioner.assert_called_once_with(
            'sudo cat %s/conf/vhosts/example.test/vhost.conf' % self.temp.name)
        self.process.outputExecutioner.reset_mock()
        for value in NOT_A_DOMAIN:
            with self.subTest(value=value):
                self.assertEqual(0, self.tuning.fetchPHPDetails(value))
        self.process.outputExecutioner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
