"""The older PHP settings interface (cloud API): unknown versions stop early, files are installed as root's."""
import json
import os
import re
import shlex
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from managePHP import phpConfig
from plogical.test_php_restart_marker import load_methods

INI = '[PHP]\n; memory_limit = 1\nmemory_limit = 128M\ndisplay_errors = On\n'
VALUES = dict(allow_url_fopen=True, display_errors=False, file_uploads=True, allow_url_include=False,
              memory_limit='256M', max_execution_time='30', upload_max_filesize='64M', max_input_time='60',
              post_max_size='128M')
NOT_MANAGED = ('PHP 8.3', 'PHP 7.4', 'PHP 7.3 ', 'PHP 7.3; id', 'PHP 9.9', 'php 7.3', '7.3', '', None, 73)
NAMES = ['FindPHPFPMPath', 'getPHPString', 'installPHPIni', 'getCurrentPHPConfig', 'savePHPConfigBasic',
         'fetchPHPSettingsAdvance', 'savePHPConfigAdvance']


class CloudPHPSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cloud-php-test-')
        self.addCleanup(self.temp.cleanup)
        self.commands = []
        self.staged = []
        self.process = mock.Mock()
        self.process.outputExecutioner.return_value = INI
        self.process.executioner.side_effect = self.helper
        self.manager = NS()
        namespace = dict(
            PHPManager=self.manager, ProcessUtilities=self.process, json=json, re=re, shlex=shlex, os=os,
            tempfile=NS(mkstemp=self.mkstemp), HttpResponse=lambda text: NS(content=text),
            matches_directive=phpConfig.matches_directive,
            apply_basic_php_settings=phpConfig.apply_basic_php_settings,
            checked_basic_php_settings=phpConfig.checked_basic_php_settings)
        for name, loaded in zip(NAMES, load_methods('managePHP/phpManager.py', 'PHPManager', NAMES, namespace)):
            setattr(self.manager, name, loaded)

    def mkstemp(self, dir=None, prefix=None):
        self.assertEqual(('/home/cyberpanel', 'phpini.'), (dir, prefix))
        return tempfile.mkstemp(dir=self.temp.name, prefix=prefix)

    def helper(self, command):
        self.commands.append(command)
        words = shlex.split(command)
        if words[0] == 'install':
            with open(words[-2]) as staged:
                self.staged.append(staged.read())
        return 1

    def assert_nothing_done(self):
        self.assertEqual([], self.process.mock_calls)
        self.assertEqual([], os.listdir(self.temp.name))

    def test_a_version_this_interface_does_not_manage_stops_before_any_command(self):
        requests = (
            lambda version: self.manager.getCurrentPHPConfig(version),
            lambda version: self.manager.fetchPHPSettingsAdvance(version),
            lambda version: self.manager.savePHPConfigBasic(dict(VALUES, phpVersion=version)),
            lambda version: self.manager.savePHPConfigAdvance({'phpVersion': version, 'configData': 'x = y\n'}),
        )
        for version in NOT_MANAGED:
            for request in requests:
                with self.subTest(version=version):
                    with self.assertRaisesRegex(ValueError, 'not managed here'):
                        request(version)
        self.assert_nothing_done()

    def test_basic_save_installs_a_file_of_root_and_removes_its_copy(self):
        response = self.manager.savePHPConfigBasic(dict(VALUES, phpVersion='PHP 7.3'))
        self.assertEqual({'status': 1}, json.loads(response.content))
        install = shlex.split(self.commands[0])
        self.assertEqual(['install', '-o', 'root', '-g', 'root', '-m', '644', '--'], install[:8])
        self.assertEqual('/etc/opt/remi/php73/php.ini', install[-1])
        self.assertTrue(os.path.basename(install[-2]).startswith('phpini.'))
        self.assertEqual(['systemctl stop php73-php-fpm', 'systemctl start php73-php-fpm'], self.commands[1:])
        self.assertTrue(self.staged[0].startswith(
            '[PHP]\n; memory_limit = 1\nmemory_limit = 256M\ndisplay_errors = Off\n'))
        self.assertEqual([], os.listdir(self.temp.name))

    def test_basic_save_refuses_a_value_that_is_not_one_word_of_its_kind(self):
        for directive in phpConfig.PHP_SIZES + phpConfig.PHP_SECONDS:
            for value in ('256M\rauto_prepend_file = /tmp/x', '256M\nx = y', '1 2', '', None):
                with self.subTest(directive=directive, value=value):
                    with self.assertRaisesRegex(ValueError, 'Invalid value for %s' % directive):
                        self.manager.savePHPConfigBasic(dict(VALUES, phpVersion='PHP 7.3', **{directive: value}))
        self.assert_nothing_done()

    def test_advanced_save_installs_the_text_and_removes_its_copy(self):
        response = self.manager.savePHPConfigAdvance({'phpVersion': 'PHP 5.6', 'configData': 'memory_limit = 64M\n'})
        self.assertEqual({'status': 1}, json.loads(response.content))
        install = shlex.split(self.commands[0])
        self.assertEqual(['install', '-o', 'root', '-g', 'root', '-m', '644', '--'], install[:8])
        self.assertEqual('/etc/opt/remi/php56/php.ini', install[-1])
        self.assertEqual(['memory_limit = 64M\n'], self.staged)
        self.assertEqual(['systemctl stop php56-php-fpm', 'systemctl start php56-php-fpm'], self.commands[1:])
        self.assertEqual([], os.listdir(self.temp.name))

    def test_the_copy_is_removed_when_the_helper_fails(self):
        self.process.executioner.side_effect = RuntimeError('helper unavailable')
        with self.assertRaises(RuntimeError):
            self.manager.savePHPConfigAdvance({'phpVersion': 'PHP 7.3', 'configData': 'x = y\n'})
        self.assertEqual([], os.listdir(self.temp.name))

    def test_advanced_save_takes_text_only(self):
        for content in (None, ['x'], {'x': 1}, 7):
            with self.assertRaises(ValueError):
                self.manager.savePHPConfigAdvance({'phpVersion': 'PHP 7.3', 'configData': content})
        self.assert_nothing_done()

    def test_reader_answers_when_a_directive_is_absent(self):
        data = json.loads(self.manager.getCurrentPHPConfig('PHP 7.3').content)
        self.assertEqual((1, '128M', '', '1'), (data['fetchStatus'], data['memory_limit'], data['post_max_size'],
                                               data['display_errors']))


if __name__ == '__main__':
    unittest.main()
