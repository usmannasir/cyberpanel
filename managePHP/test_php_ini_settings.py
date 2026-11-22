"""The PHP settings pages: which php.ini they name, which values they accept and what reaches the worker."""
import json
import shlex
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from managePHP import phpConfig
from managePHP.test_php_selection import NOT_A_SELECTION, OFFERED
from managePHP.test_request_methods import load_views, post

GOOD = dict(allow_url_fopen=True, display_errors=False, file_uploads=True, allow_url_include=False,
            memory_limit='256M', max_execution_time='30', upload_max_filesize='64M', max_input_time='-1',
            post_max_size='128M')
# Values an ini file may already hold, which the page shows and sends back unchanged.
KEPT_VALUES = {'memory_limit': ('-1', '128M', '1G', '2g', '512k', '+256M', '0', 268435456),
               'upload_max_filesize': ('2M', '0'), 'post_max_size': ('8M',),
               'max_execution_time': ('0', '30', '-1', '+60', 300), 'max_input_time': ('-1', '60')}
# One word of the wrong kind, or more than one word.
REFUSED_VALUES = ('256M\rauto_prepend_file = /tmp/x', '256M\nx = y', '256M auto_prepend_file=/x', '256M;x', '256MB',
                  '2.5M', 'M', '', ' 256M', '256M ', '--apache', '-', '1e3', '0x10', '12345678901M', None, True,
                  12.5, ['1'], {'a': 1})


def settings(**changes):
    values = dict(GOOD)
    values.update(changes)
    return values


class ManagedIniPathTests(unittest.TestCase):
    def test_path_is_built_from_the_digits_for_each_layout(self):
        self.assertEqual('/usr/local/lsws/lsphp83/etc/php.ini', phpConfig.managed_ini_path('PHP 8.3', False, True))
        self.assertEqual('/usr/local/lsws/lsphp83/etc/php/8.3/litespeed/php.ini',
                         phpConfig.managed_ini_path('PHP 8.3', False, False))
        self.assertEqual('/etc/opt/remi/php83/php.ini', phpConfig.managed_ini_path('PHP 8.3', True, True))
        self.assertEqual('/etc/php/8.3/fpm/php.ini', phpConfig.managed_ini_path('PHP 8.3', True, False))

    def test_every_offered_version_gives_a_managed_path(self):
        for selection in OFFERED:
            for apache in (False, True):
                for rpm_family in (False, True):
                    self.assertTrue(phpConfig.is_managed_ini(phpConfig.managed_ini_path(selection, apache, rpm_family)))

    def test_no_path_for_text_that_is_not_a_selection(self):
        for value in NOT_A_SELECTION + ('PHP ../../root/x', 'PHP 8.3/../../../etc/shadow x', 'PHP 8.3 /etc/shadow'):
            for apache in (False, True):
                for rpm_family in (False, True):
                    with self.subTest(value=value, apache=apache, rpm_family=rpm_family):
                        with self.assertRaises(ValueError):
                            phpConfig.managed_ini_path(value, apache, rpm_family)

    def test_only_the_four_layouts_are_managed(self):
        for path in ('/etc/shadow', '/etc/php/8.3/fpm/php.ini/../../../../shadow', '/etc/php/8.3/cli/php.ini',
                     '/etc/php/../shadow/fpm/php.ini', '/etc/php/8.3/fpm/php.ini ', ' /etc/php/8.3/fpm/php.ini',
                     '/etc/php/8.3/fpm/php.ini\n', 'etc/php/8.3/fpm/php.ini', '/usr/local/lsws/lsphp83/etc/php.ini.bak',
                     '/usr/local/lsws/lsphp/etc/php.ini', '/usr/local/lsws/conf/httpd_config.conf',
                     '/etc/opt/remi/php83/php-fpm.d/www.conf', '', None, 7):
            with self.subTest(path=path):
                self.assertFalse(phpConfig.is_managed_ini(path))


class BasicSettingValueTests(unittest.TestCase):
    def test_page_values_become_one_word_each(self):
        self.assertEqual(
            [('allow_url_fopen', 'On'), ('display_errors', 'Off'), ('file_uploads', 'On'),
             ('allow_url_include', 'Off'), ('memory_limit', '256M'), ('max_execution_time', '30'),
             ('upload_max_filesize', '64M'), ('max_input_time', '-1'), ('post_max_size', '128M')],
            phpConfig.checked_basic_php_settings(GOOD))

    def test_values_already_in_use_are_still_accepted(self):
        for directive, values in KEPT_VALUES.items():
            for value in values:
                with self.subTest(directive=directive, value=value):
                    checked = dict(phpConfig.checked_basic_php_settings(settings(**{directive: value})))
                    self.assertEqual(str(value), checked[directive])

    def test_switches_are_on_or_off_only(self):
        for value, expected in ((True, 'On'), (1, 'On'), ('1', 'On'), (False, 'Off'), (0, 'Off'), ('0', 'Off')):
            checked = dict(phpConfig.checked_basic_php_settings(settings(display_errors=value)))
            self.assertEqual(expected, checked['display_errors'])
        for value in ('On', 'true', 'On\rauto_prepend_file=/x', 'display_errors = On', 2, None, 1.0, [], '1 '):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    phpConfig.checked_basic_php_settings(settings(display_errors=value))

    def test_a_value_that_is_not_one_word_of_its_kind_is_refused(self):
        for directive in phpConfig.PHP_SIZES + phpConfig.PHP_SECONDS:
            for value in REFUSED_VALUES + ('1234567890123',):
                with self.subTest(directive=directive, value=value):
                    with self.assertRaisesRegex(ValueError, 'Invalid value for %s' % directive):
                        phpConfig.checked_basic_php_settings(settings(**{directive: value}))
        for directive in phpConfig.PHP_SECONDS:
            with self.assertRaises(ValueError):
                phpConfig.checked_basic_php_settings(settings(**{directive: '30M'}))


class BasicSettingTextTests(unittest.TestCase):
    chosen = phpConfig.checked_basic_php_settings(GOOD)

    def test_assignments_are_replaced_and_comments_kept(self):
        before = ('[PHP]\n; display_errors = On is for development\n;memory_limit = 1\n'
                  'display_errors = On\n  memory_limit=128M ; per script\nmax_file_uploads = 20\n'
                  'allow_url_fopen = Off\nfile_uploads = Off\nallow_url_include = On\nmax_execution_time = 5\n'
                  'upload_max_filesize = 2M\nmax_input_time = 60\npost_max_size = 8M\n[Date]\n')
        after = phpConfig.apply_basic_php_settings(before, self.chosen)
        self.assertEqual(
            '[PHP]\n; display_errors = On is for development\n;memory_limit = 1\n'
            'display_errors = Off\nmemory_limit = 256M\nmax_file_uploads = 20\n'
            'allow_url_fopen = On\nfile_uploads = On\nallow_url_include = Off\nmax_execution_time = 30\n'
            'upload_max_filesize = 64M\nmax_input_time = -1\npost_max_size = 128M\n[Date]\n', after)

    def test_missing_directives_are_added_once_at_the_end(self):
        after = phpConfig.apply_basic_php_settings('[PHP]\nmemory_limit = 1M', self.chosen)
        self.assertTrue(after.startswith('[PHP]\nmemory_limit = 256M\n\n; Added by CyberPanel PHP Config Manager\n'))
        for directive, value in self.chosen:
            self.assertEqual(1, after.count('%s = %s\n' % (directive, value)), directive)
        self.assertEqual(after, phpConfig.apply_basic_php_settings(after, self.chosen))

    def test_other_lines_keep_their_line_endings(self):
        after = phpConfig.apply_basic_php_settings('[PHP]\r\nextension=a.so\r\nmemory_limit = 1M\r\n', self.chosen)
        self.assertTrue(after.startswith('[PHP]\r\nextension=a.so\r\nmemory_limit = 256M\n'))

    def test_no_accepted_value_can_put_a_second_directive_on_a_line_of_its_own(self):
        text = phpConfig.apply_basic_php_settings('', self.chosen)
        for line in text.splitlines():
            if line and not line.startswith(';'):
                name = line.split(' = ')[0]
                self.assertIn(name, phpConfig.BASIC_PHP_SETTINGS)
        self.assertNotIn('\r', text)


class SettingsPageTests(unittest.TestCase):
    def setUp(self):
        names = ['getCurrentPHPConfig', 'savePHPConfigBasic', 'getCurrentAdvancedPHPConfig', 'savePHPConfigAdvance']
        self.staged = '/home/cyberpanel/phpini.test'
        self.temp = NS(mkstemp=mock.Mock(return_value=(9, self.staged)))
        self.views, self.services, _ = load_views(
            names, matches_directive=phpConfig.matches_directive,
            php_selection_digits=phpConfig.php_selection_digits,
            checked_basic_php_settings=phpConfig.checked_basic_php_settings,
            BASIC_PHP_SETTINGS=phpConfig.BASIC_PHP_SETTINGS, PHP_FLAGS=phpConfig.PHP_FLAGS, tempfile=self.temp)
        self.process = self.services['ProcessUtilities']
        self.process.outputExecutioner.return_value = '1,None'
        self.os = self.services['os']
        self.os.fdopen.return_value = mock.MagicMock()
        apache = NS(DecidePHPPathforManager=lambda apache, selection: phpConfig.managed_ini_path(
            selection, not (apache == 0 or apache is None), False))
        patcher = mock.patch.dict('sys.modules', {'ApachController.ApacheVhosts': NS(ApacheVhost=apache)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def save_basic(self, apache=False, **changes):
        self.process.reset_mock()
        body = dict(settings(**changes), phpSelection=changes.pop('phpSelection', 'PHP 8.3'))
        body.update(changes)
        response = self.views.savePHPConfigBasic(
            post('/managephp/savePHPConfigBasic' + ('?apache=apache' if apache else ''), body))
        return json.loads(response.content)

    def commands(self):
        return [call[0][0] for call in self.process.outputExecutioner.call_args_list]

    def test_basic_save_hands_the_worker_one_word_per_value(self):
        for apache in (False, True):
            with self.subTest(apache=apache):
                self.assertEqual({'saveStatus': 1}, self.save_basic(apache))
                words = shlex.split(self.commands()[0])
                self.assertEqual(
                    ['/usr/local/CyberCP/bin/python', '/usr/local/CyberCP/plogical/phpUtilities.py',
                     'savePHPConfigBasic', '--phpVers', 'PHP 8.3', '--allow_url_fopen=1', '--display_errors=0',
                     '--file_uploads=1', '--allow_url_include=0', '--memory_limit=256M',
                     '--max_execution_time=30', '--upload_max_filesize=64M', '--max_input_time=-1',
                     '--post_max_size=128M', '--apache', '1' if apache else '0'], words)

    def test_basic_save_starts_no_worker_for_a_refused_value(self):
        for directive in phpConfig.PHP_SIZES + phpConfig.PHP_SECONDS:
            for value in REFUSED_VALUES:
                with self.subTest(directive=directive, value=value):
                    result = self.save_basic(**{directive: value})
                    self.assertEqual(0, result['saveStatus'])
                    self.assertIn('Invalid value for %s' % directive, result['error_message'])
                    self.assertEqual([], self.commands())
        for value in ('On\rauto_prepend_file = /x', 'yes', None):
            result = self.save_basic(allow_url_include=value)
            self.assertEqual(0, result['saveStatus'])
            self.assertEqual([], self.commands())

    def test_basic_save_starts_no_worker_for_text_that_is_not_a_selection(self):
        for value in NOT_A_SELECTION:
            if isinstance(value, bytes):
                continue
            with self.subTest(value=value):
                result = self.save_basic(phpSelection=value)
                self.assertEqual(0, result['saveStatus'])
                self.assertEqual([], self.commands())

    def test_pages_read_the_file_built_from_the_digits_as_one_word(self):
        self.process.outputExecutioner.return_value = 'memory_limit = 128M\n'
        for view in (self.views.getCurrentPHPConfig, self.views.getCurrentAdvancedPHPConfig):
            for apache, path in ((False, '/usr/local/lsws/lsphp83/etc/php/8.3/litespeed/php.ini'),
                                 (True, '/etc/php/8.3/fpm/php.ini')):
                with self.subTest(view=view.__name__, apache=apache):
                    self.process.reset_mock()
                    request = post('/managephp/x' + ('?apache=apache' if apache else ''), {'phpSelection': 'PHP 8.3'})
                    self.assertEqual(1, json.loads(view(request).content)['fetchStatus'])
                    self.assertEqual(['sudo cat ' + path], self.commands())

    def test_pages_read_nothing_for_text_that_is_not_a_selection(self):
        for view in (self.views.getCurrentPHPConfig, self.views.getCurrentAdvancedPHPConfig):
            for value in ('PHP 8.3/../../../../etc/shadow x', '8.3 /etc/shadow', 'PHP 8.3 /etc/shadow', None):
                for apache in (False, True):
                    with self.subTest(view=view.__name__, value=value, apache=apache):
                        self.process.reset_mock()
                        request = post('/managephp/x' + ('?apache=apache' if apache else ''), {'phpSelection': value})
                        self.assertEqual(0, json.loads(view(request).content)['fetchStatus'])
                        self.assertEqual([], self.commands())

    def test_reader_answers_when_a_directive_is_absent_and_ignores_comments(self):
        self.process.outputExecutioner.return_value = \
            '; allow_url_fopen = On\n;display_errors = On\nmemory_limit = 128M\n; post_max_size = 1G\n'
        data = json.loads(self.views.getCurrentPHPConfig(
            post('/managephp/getCurrentPHPConfig', {'phpSelection': 'PHP 8.3'})).content)
        self.assertEqual(1, data['fetchStatus'], data)
        self.assertEqual(('0', '0', '128M', ''), (data['allow_url_fopen'], data['display_errors'],
                                                    data['memory_limit'], data['post_max_size']))

    def save_advanced(self, selection='PHP 8.3', content='memory_limit = 64M\n', apache=False):
        self.process.reset_mock()
        self.os.reset_mock()
        self.temp.mkstemp.reset_mock()
        self.os.fdopen.return_value = mock.MagicMock()
        response = self.views.savePHPConfigAdvance(
            post('/managephp/savePHPConfigAdvance' + ('?apache=apache' if apache else ''),
                 {'phpSelection': selection, 'configData': content}))
        return json.loads(response.content)

    def test_advanced_save_stages_the_text_in_a_file_of_its_own_and_removes_it(self):
        self.assertEqual(1, self.save_advanced(apache=True)['saveStatus'])
        self.temp.mkstemp.assert_called_once_with(dir='/home/cyberpanel', prefix='phpini.')
        self.os.fdopen.assert_called_once_with(9, 'w')
        self.os.fdopen.return_value.__enter__.return_value.write.assert_called_once_with('memory_limit = 64M\n')
        self.assertEqual(['/usr/local/CyberCP/bin/python', '/usr/local/CyberCP/plogical/phpUtilities.py',
                          'savePHPConfigAdvance', '--phpVers', '/etc/php/8.3/fpm/php.ini', '--tempPath',
                          self.staged], shlex.split(self.commands()[0]))
        self.os.remove.assert_called_once_with(self.staged)
        self.services['open'].assert_not_called()

    def test_advanced_save_removes_the_staged_text_when_the_worker_fails(self):
        self.process.outputExecutioner.side_effect = RuntimeError('helper unavailable')
        self.addCleanup(setattr, self.process.outputExecutioner, 'side_effect', None)
        self.assertEqual(0, self.save_advanced()['saveStatus'])
        self.os.remove.assert_called_once_with(self.staged)

    def test_advanced_save_stages_nothing_for_text_that_is_not_a_selection(self):
        for value in ('PHP 8.3 /etc/cron.d/x', 'PHP 8.3/../../x', None):
            for apache in (False, True):
                with self.subTest(value=value, apache=apache):
                    self.assertEqual(0, self.save_advanced(selection=value, apache=apache)['saveStatus'])
                    self.temp.mkstemp.assert_not_called()
                    self.assertEqual([], self.commands())


if __name__ == '__main__':
    unittest.main()
