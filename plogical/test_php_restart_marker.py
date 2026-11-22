"""A PHP change creates and removes the website's restart marker as the website's own user."""
import ast
import builtins
import contextlib
import io
from pathlib import Path
import re
import shlex
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from managePHP.phpConfig import php_selection_digits

ROOT = Path(__file__).resolve().parents[1]
OLS, ENTERPRISE = 'ols', 'lsws'


def load_methods(relative_path, class_name, names, namespace):
    """Run the named methods of a class from the source file with the given names in scope.

    A name the class does not have gives None, so the tests can also be run
    against a version of the source that lacks a helper.
    """
    source = ROOT / relative_path
    owner = next(node for node in ast.parse(source.read_text()).body
                 if isinstance(node, ast.ClassDef) and node.name == class_name)
    for node in owner.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            node.decorator_list = []
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
    return [namespace.get(name) for name in names]


class Missing(Exception):
    pass


class PHPChange:
    """The real vhost.changePHP with the database, the web server and every file replaced."""

    def __init__(self, server, master_user='siteuser', redis=False, apache_backend=False):
        self.temp = tempfile.TemporaryDirectory(prefix='php-change-test-')
        self.files = {}
        self.opened = []
        self.events = []
        self.sites = {'example.test': NS(domain='example.test', externalApp=master_user)}
        self.children = {'shop.example.test': NS(domain='shop.example.test', master=self.sites['example.test'])}
        self.process = mock.Mock()
        self.process.OLS = OLS
        self.process.decideServer.return_value = server
        self.process.normalExecutioner.side_effect = lambda command: self.events.append(command) or 1
        self.process.outputExecutioner.return_value = '{"phpVersion": 7.4, "uid": 1001}'
        self.process.executioner.side_effect = lambda command: self.events.append(command) or 1
        self.install = mock.Mock()
        self.install.installUtilities.reStartLiteSpeed.side_effect = lambda: self.events.append('restart web server')
        self.apache = mock.Mock()
        self.apache.changePHP.return_value = 1 if apache_backend else 0
        self.os = NS(path=NS(isfile=lambda path: True,
                             exists=lambda path: redis if path.endswith('dvhost_redis.conf') else True),
                     remove=mock.Mock(side_effect=AssertionError('the worker removed a file itself')))
        self.namespace = dict(
            Websites=NS(objects=NS(get=lambda domain: self.lookup(self.sites, domain))),
            ChildDomains=NS(objects=NS(get=lambda domain: self.lookup(self.children, domain))),
            PHPManager=NS(getPHPString=lambda text: text.split()[1].replace('.', '')),
            ProcessUtilities=self.process, ApacheVhost=self.apache, installUtilities=self.install,
            logging=mock.Mock(), os=self.os, shlex=shlex, open=self.open, print=print, re=re,
            php_selection_digits=php_selection_digits)
        self.namespace['vhost'] = NS(redisConf='/usr/local/lsws/conf/dvhost_redis.conf',
                                     Server_root='/usr/local/lsws')
        self.method, self.namespace['vhost'].phpRestartMarker = load_methods(
            'plogical/vhost.py', 'vhost', ['changePHP', 'phpRestartMarker'], self.namespace)

    @staticmethod
    def lookup(table, domain):
        if domain not in table:
            raise Missing(domain)
        return table[domain]

    def vhost_file(self, domain, content):
        path = '/usr/local/lsws/conf/vhosts/%s/vhost.conf' % domain
        self.files[path] = Path(self.temp.name) / (domain + '.conf')
        self.files[path].write_text(content)
        return path

    def open(self, path, *args, **kwargs):
        self.opened.append(str(path))
        if str(path) not in self.files:
            raise AssertionError('the worker opened %s itself' % path)
        return builtins.open(self.files[str(path)], *args, **kwargs)

    def run(self, path, selection='PHP 8.3'):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            result = self.method(path, selection)
        return result, output.getvalue()

    def close(self):
        self.temp.cleanup()


class PHPRestartMarkerTests(unittest.TestCase):
    ols_conf = 'extprocessor x {\n  path                    /usr/local/lsws/lsphp74/bin/lsphp\n}\n'
    lsws_conf = '<VirtualHost *>\n    AddHandler application/x-httpd-php74 .php\n</VirtualHost>\n'

    def change(self, server, domain, **options):
        change = PHPChange(server, **options)
        self.addCleanup(change.close)
        path = change.vhost_file(domain, self.ols_conf if server == OLS else self.lsws_conf)
        result, output = change.run(path)
        self.assertEqual((1, 'None'), tuple(result), output)
        self.assertIn('1,None', output)
        return change, path

    def assert_marker(self, change, path, user, home):
        marker = '/home/%s/.lsphp_restart.txt' % home
        self.assertEqual(['sudo -u %s touch -- %s' % (user, marker), 'restart web server',
                          'sudo -u %s rm -f -- %s' % (user, marker)], change.events)
        # Only the website's configuration file was opened by the worker.
        self.assertEqual({path}, set(change.opened))
        change.os.remove.assert_not_called()

    def test_enterprise_site_marker_is_touched_and_removed_as_the_site_user(self):
        change, path = self.change(ENTERPRISE, 'example.test')
        self.assert_marker(change, path, 'siteuser', 'example.test')
        self.assertIn('AddHandler application/x-httpd-php83 .php', change.files[path].read_text())

    def test_enterprise_child_domain_uses_its_master_home(self):
        change, path = self.change(ENTERPRISE, 'shop.example.test')
        self.assert_marker(change, path, 'siteuser', 'example.test')

    def test_openlitespeed_site_and_child_use_the_same_marker(self):
        for domain in ('example.test', 'shop.example.test'):
            with self.subTest(domain=domain):
                change, path = self.change(OLS, domain)
                self.assert_marker(change, path, 'siteuser', 'example.test')
                self.assertIn('/usr/local/lsws/lsphp83/bin/lsphp', change.files[path].read_text())

    def test_marker_command_keeps_every_stored_value_one_argument(self):
        change = PHPChange(ENTERPRISE)
        self.addCleanup(change.close)
        marker = change.namespace['vhost'].phpRestartMarker
        for user, path in (('site user', '/home/a b/.lsphp_restart.txt'),
                           ('u;id', '/home/x$(id)/.lsphp_restart.txt'),
                           ('-u', '-rf')):
            for action, program in (('touch', ['touch']), ('rm', ['rm', '-f'])):
                change.events[:] = []
                marker(action, user, path)
                self.assertEqual(['sudo', '-u', user] + program + ['--', path],
                                 shlex.split(change.events[0]))

    def test_marker_helper_runs_nothing_else(self):
        change = PHPChange(ENTERPRISE)
        self.addCleanup(change.close)
        with self.assertRaises(KeyError):
            change.namespace['vhost'].phpRestartMarker('chown', 'siteuser', '/home/example.test/x')
        self.assertEqual([], change.events)


if __name__ == '__main__':
    unittest.main()
