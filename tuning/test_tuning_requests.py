"""The tuning pages check every value and the selected website before the privileged worker is started."""
import ast
import json
from pathlib import Path
import shlex
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from plogical.test_tuning_values import (
    ENTERPRISE, NOT_A_DOMAIN, NOT_A_NUMBER, NOT_A_SIZE, NOT_A_SWITCH, OLS, load_tuning,
)
from websiteFunctions.test_stored_domain_name import Rows
from websiteFunctions.test_wordpress_entitlements import Response

SOURCE = Path(__file__).with_name('tuning.py')
PHP = dict(status='save', domainSelection='example.test', initTimeout='60', maxConns='20', memSoftLimit='1024M',
           memHardLimit='1024M', procSoftLimit='300', procHardLimit='400', persistConn='Enable')
SERVER = dict(status='save', maxConn=2000, maxSSLConn=1000, connTime=300, keepAlive=5, inMemCache=20,
              gzipCompression='Enable')


def load_manager(server=OLS, admin=1):
    """The real tuningManager with the database, the page renderer and the privileged helper replaced."""
    worker, process = load_tuning(server)
    process.outputExecutioner.return_value = '1,None'
    acl = mock.Mock()
    acl.loadedACL.return_value = {'admin': admin}
    acl.loadError.return_value = Response(json.dumps({'error_message': 'ACL denied'}))
    http = mock.Mock()
    namespace = dict(
        ACLManager=acl, ProcessUtilities=process, tuning=worker.tuning, httpProc=http, HttpResponse=Response,
        json=json, shlex=shlex, logging=mock.Mock(), virtualHostUtilities=NS(cyberPanel='/usr/local/CyberCP'),
        Websites=NS(objects=Rows(NS(domain='example.test'))),
        ChildDomains=NS(objects=Rows(NS(domain='shop.example.test'))))
    tree = ast.parse(SOURCE.read_text())
    wanted = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'tuningManager']
    exec(compile(ast.Module(body=wanted, type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace['tuningManager'](), NS(acl=acl, process=process, http=http, namespace=namespace)


class TuningRequestTests(unittest.TestCase):
    def setUp(self):
        self.manager, self.services = load_manager()
        self.process = self.services.process

    def commands(self):
        return [call[0][0] for call in self.process.outputExecutioner.call_args_list]

    def tune_php(self, **changes):
        self.process.reset_mock()
        return json.loads(self.manager.tunePHP(7, dict(PHP, **changes)).content)

    def tune_server(self, **changes):
        self.process.reset_mock()
        return json.loads(self.manager.tuneLitespeed(7, dict(SERVER, **changes)).content)

    def test_php_tuning_hands_the_worker_one_word_per_value(self):
        self.assertEqual(1, self.tune_php()['tuneStatus'])
        self.assertEqual(
            ['/usr/local/CyberCP/bin/python', '/usr/local/CyberCP/plogical/tuning.py', 'tunePHP', '--virtualHost',
             'example.test', '--initTimeout', '60', '--maxConns', '20', '--memSoftLimit', '1024M',
             '--memHardLimit', '1024M', '--procSoftLimit', '300', '--procHardLimit', '400', '--persistConn',
             'Enable'], shlex.split(self.commands()[0]))

    def test_php_tuning_names_the_website_as_it_is_stored(self):
        for spelling, stored in (('EXAMPLE.TEST', 'example.test'), ('Shop.Example.Test', 'shop.example.test')):
            self.assertEqual(1, self.tune_php(domainSelection=spelling)['tuneStatus'])
            words = shlex.split(self.commands()[0])
            self.assertEqual(stored, words[words.index('--virtualHost') + 1])

    def test_php_tuning_reaches_a_website_named_by_an_earlier_release(self):
        for name in ('my_shop.example.com', 'm\u00fcnchen.de'):
            self.services.namespace['Websites'].objects.rows.append(NS(domain=name))
            with self.subTest(name=name):
                self.assertEqual(1, self.tune_php(domainSelection=name.upper())['tuneStatus'])
                words = shlex.split(self.commands()[0])
                self.assertEqual(name, words[words.index('--virtualHost') + 1])

    def test_php_tuning_starts_no_worker_for_a_refused_value(self):
        cases = [('maxConns', NOT_A_NUMBER), ('initTimeout', NOT_A_NUMBER), ('procSoftLimit', NOT_A_NUMBER),
                 ('procHardLimit', NOT_A_NUMBER), ('memSoftLimit', NOT_A_SIZE), ('memHardLimit', NOT_A_SIZE),
                 ('persistConn', NOT_A_SWITCH)]
        for name, values in cases:
            for value in values:
                with self.subTest(name=name, value=value):
                    result = self.tune_php(**{name: value})
                    self.assertEqual(0, result['tuneStatus'])
                    self.assertEqual([], self.commands())

    def test_php_tuning_acts_only_on_a_website_of_this_server(self):
        for status in ('fetch', 'save'):
            for value in NOT_A_DOMAIN + ('other.test', {'a': 1}, 12):
                with self.subTest(status=status, value=value):
                    result = self.tune_php(status=status, domainSelection=value)
                    self.assertEqual(0, result['tuneStatus'])
                    self.assertEqual(0, result['fetch_status'])
                    self.assertEqual([], self.commands())

    def test_php_tuning_on_enterprise_takes_a_litespeed_php_only(self):
        self.manager, self.services = load_manager(ENTERPRISE)
        self.process = self.services.process
        self.assertEqual(1, self.tune_php(domainSelection='lsphp83')['tuneStatus'])
        for value in ('example.test', 'lsphp83 --maxConns 1', 'lsphp83</name>'):
            with self.subTest(value=value):
                self.assertEqual(0, self.tune_php(domainSelection=value)['tuneStatus'])
                self.assertEqual([], self.commands())

    def test_server_tuning_hands_the_worker_one_word_per_value(self):
        self.assertEqual(1, self.tune_server()['tuneStatus'])
        self.assertEqual(
            ['/usr/local/CyberCP/bin/python', '/usr/local/CyberCP/plogical/tuning.py', 'saveTuningDetails',
             '--maxConn', '2000', '--maxSSLConn', '1000', '--connTime', '300', '--keepAlive', '5',
             '--inMemCache', '20', '--gzipCompression', 'Enable'], shlex.split(self.commands()[0]))

    def test_server_tuning_starts_no_worker_for_a_refused_value(self):
        cases = [('maxConn', NOT_A_NUMBER), ('maxSSLConn', NOT_A_NUMBER), ('connTime', NOT_A_NUMBER),
                 ('keepAlive', NOT_A_NUMBER), ('inMemCache', NOT_A_SIZE), ('gzipCompression', NOT_A_SWITCH)]
        for name, values in cases:
            for value in values:
                with self.subTest(name=name, value=value):
                    result = self.tune_server(**{name: value})
                    self.assertEqual(0, result['tuneStatus'])
                    self.assertEqual([], self.commands())

    def test_a_value_that_is_not_text_never_becomes_part_of_the_command(self):
        # Text inside a list or an object is not seen by the request filter.
        for name in ('maxConn', 'maxSSLConn', 'connTime', 'keepAlive', 'inMemCache'):
            for value in (['1; id'], {'1; id': 1}, [1, '--gzipCompression', 'x']):
                self.assertEqual(0, self.tune_server(**{name: value})['tuneStatus'])
                self.assertEqual([], self.commands())


if __name__ == '__main__':
    unittest.main()
