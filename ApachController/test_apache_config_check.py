"""One website's virtual host or pool must not stop Apache or PHP-FPM for the other websites."""
import ast
import contextlib
import io
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from ApachController import apacheConfigCheck as checks
from managePHP import phpConfig
from plogical.test_php_restart_marker import OLS, PHPChange, load_methods
from plogical.test_server_switch_mail_php import method as worker_method
from plogical.vhostConfs import vhostConfs

ROOT = Path(__file__).resolve().parents[1]

# The accounts of the imagined server.
USERS = {'siteuser', 'other1234', 'nobody', 'www-data'}
GROUPS = {'siteuser', 'other1234', 'nogroup', 'www-data'}


def getpwnam(name):
    if name not in USERS:
        raise KeyError(name)
    return name


def getgrnam(name):
    if name not in GROUPS:
        raise KeyError(name)
    return name


def account_problem(user, group=None):
    return checks.account_problem(user, group, getpwnam, getgrnam)


def vhost_text(user, domain='example.test'):
    text = vhostConfs.apacheConf + vhostConfs.apacheConfSSL
    for key, value in (('{virtualHostName}', domain), ('{administratorEmail}', 'owner@example.test'),
                       ('{externalApp}', user), ('{sockPath}', '/var/run/php/'), ('{php}', '83'),
                       ('{SSLBase}', '/etc/apache2/conf-enabled/')):
        text = text.replace(key, value)
    return text


def pool_text(user, domain='example.test'):
    text = vhostConfs.phpFpmPool
    for key, value in (('{www}', phpConfig.fpm_pool_name(user, domain)), ('{Sock}', domain),
                       ('{externalApp}', user), ('{sockPath}', '/var/run/php/'), ('{group}', 'nogroup')):
        text = text.replace(key, value)
    return text


class Apache:
    """Apache's configuration test over a folder: it refuses a file that names an unknown account."""

    def __init__(self, folder):
        self.folder = str(folder)
        self.tests = 0

    def test(self):
        self.tests += 1
        for path in sorted(Path(self.folder).glob('*.conf')):
            text = path.read_text()
            if 'NotADirective' in text:
                return False, 'AH00526: Syntax error on line 1 of %s:\nInvalid command NotADirective' % path
            unknown = checks.unknown_accounts(checks.vhost_accounts(text), getpwnam, getgrnam)
            if unknown:
                return False, 'AH00543: apache2: bad user name %s' % unknown[0]
        return True, 'Syntax OK'


class AccountTests(unittest.TestCase):
    def test_an_account_needs_its_user_and_its_group(self):
        self.assertIsNone(account_problem('siteuser'))
        self.assertEqual('The system user Examp1234 does not exist on this server.', account_problem('Examp1234'))
        # nobody is a user everywhere, a group only on the RPM family.
        self.assertEqual('The system group nobody does not exist on this server.', account_problem('nobody'))
        self.assertIsNone(account_problem('nobody', 'nogroup'))
        for name in ('', None, 7):
            self.assertEqual('The website has no system user.', account_problem(name))

    def test_accounts_are_read_from_the_files_the_panel_writes(self):
        self.assertEqual([('examp1234', 'examp1234')] * 2, checks.vhost_accounts(vhost_text('examp1234')))
        for template in (vhostConfs.apacheConfChild, vhostConfs.apacheConfChildSSL):
            self.assertEqual([('examp1234', 'examp1234')],
                             checks.vhost_accounts(template.replace('{externalApp}', 'examp1234')))
        self.assertEqual([('examp1234', 'examp1234')], checks.pool_accounts(pool_text('examp1234')))
        # The socket's owner and a comment are not the account of the workers.
        self.assertEqual([('a', None)], checks.pool_accounts('[x]\n;user = b\nlisten.group = c\nuser = a\n'))
        self.assertEqual([], checks.pool_accounts('[global]\npid = /run/php-fpm.pid\n'))
        self.assertEqual([('a', 'b')], checks.vhost_accounts('  suexecusergroup "a" b\n#SuexecUserGroup c d\n'))

    def test_only_names_without_an_account_are_unknown(self):
        pairs = [('siteuser', 'siteuser'), ('gone1234', 'gone1234'), ('#1001', '#1001'), ('33', None),
                 ('gone1234', 'siteuser'), (None, 'nogroup')]
        self.assertEqual(['gone1234'], checks.unknown_accounts(pairs, getpwnam, getgrnam))
        self.assertEqual(['nobody'], checks.unknown_accounts([('nobody', 'nobody')], getpwnam, getgrnam))


class ConfigTestTests(unittest.TestCase):
    def test_command_of_each_distribution_family(self):
        self.assertEqual(['/usr/sbin/apache2ctl', '-t'], checks.config_test_command(False))
        self.assertEqual(['/usr/sbin/httpd', '-t'], checks.config_test_command(True))

    def test_result_is_the_exit_status_and_what_apache_said(self):
        calls = []

        def run(command, **options):
            calls.append((command, options))
            return NS(returncode=status, stdout=output)

        for status, output, expected in ((0, 'Syntax OK\n', (True, 'Syntax OK')),
                                         (1, 'AH00543: apache2: bad user name x\n', (False, 'AH00543: apache2: bad user name x')),
                                         (1, None, (False, ''))):
            self.assertEqual(expected, checks.config_test(['/usr/sbin/apache2ctl', '-t'], run))
        command, options = calls[0]
        self.assertEqual(['/usr/sbin/apache2ctl', '-t'], command)
        # Both streams as text; nothing that needs a newer Python than 3.6.
        self.assertEqual({'stdin': subprocess.DEVNULL, 'stdout': subprocess.PIPE, 'stderr': subprocess.STDOUT,
                          'universal_newlines': True, 'timeout': 120}, options)

    def test_a_test_that_cannot_run_has_not_passed(self):
        def missing(command, **options):
            raise FileNotFoundError(2, 'No such file or directory')

        def slow(command, **options):
            raise subprocess.TimeoutExpired(command, 120)

        for run in (missing, slow):
            passed, output = checks.config_test(['/usr/sbin/httpd', '-t'], run)
            self.assertFalse(passed)
            self.assertIn('/usr/sbin/httpd could not be run', output)

    def test_message_is_one_line_and_keeps_the_end(self):
        self.assertEqual('a b c', checks.said(' a\n b\t\tc\n'))
        self.assertEqual('no message', checks.said(None))
        self.assertEqual(600, len(checks.said('x' * 5000)))


class ApplyChangeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='apache-check-test-')
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.other = self.folder / 'other.test.conf'
        self.other.write_text(vhost_text('other1234', 'other.test'))
        self.vhost = self.folder / 'example.test.conf'
        self.pool = self.folder / 'pool-example.test'
        self.apache = Apache(self.folder)
        self.restarts = []
        self.restart_problem = None

    def restart(self):
        self.restarts.append(sorted(path.name for path in self.folder.glob('*.conf')))
        return self.restart_problem

    def write(self, user='siteuser', pool=True):
        def change():
            self.vhost.write_text(vhost_text(user))
            if pool:
                self.pool.write_text(pool_text(user))
        return change

    def apply(self, change):
        return checks.apply_change([str(self.vhost), str(self.pool)], change, self.apache.test, self.restart)

    def test_an_accepted_virtual_host_stays_and_apache_is_restarted_once(self):
        self.assertEqual((1, 'None'), self.apply(self.write()))
        self.assertEqual(vhost_text('siteuser'), self.vhost.read_text())
        self.assertEqual(pool_text('siteuser'), self.pool.read_text())
        self.assertEqual([['example.test.conf', 'other.test.conf']], self.restarts)
        # Once before the change and once after it.
        self.assertEqual(2, self.apache.tests)

    def test_a_refused_virtual_host_is_removed_and_apache_is_not_restarted(self):
        status, reason = self.apply(self.write('Examp1234'))
        self.assertEqual(0, status)
        self.assertEqual('Apache refused this configuration, so it was not put in place: '
                         'AH00543: apache2: bad user name Examp1234', reason)
        self.assertFalse(self.vhost.exists())
        self.assertFalse(self.pool.exists())
        # The running Apache was left alone and still accepts what is there.
        self.assertEqual([], self.restarts)
        self.assertEqual((True, 'Syntax OK'), self.apache.test())
        self.assertEqual(vhost_text('other1234', 'other.test'), self.other.read_text())

    def test_a_refused_rewrite_puts_the_earlier_file_back_as_it_was(self):
        self.vhost.write_text(vhost_text('siteuser'))
        self.vhost.chmod(0o640)
        self.pool.write_text(pool_text('siteuser'))
        status, reason = self.apply(self.write('gone1234'))
        self.assertEqual(0, status)
        self.assertIn('bad user name gone1234', reason)
        self.assertEqual(vhost_text('siteuser'), self.vhost.read_text())
        self.assertEqual(0o640, stat.S_IMODE(self.vhost.stat().st_mode))
        self.assertEqual(pool_text('siteuser'), self.pool.read_text())
        self.assertEqual([], self.restarts)
        self.assertEqual(['example.test.conf', 'other.test.conf', 'pool-example.test'],
                         sorted(path.name for path in self.folder.iterdir()))

    def test_a_failure_that_was_there_before_is_not_blamed_on_the_change(self):
        # Another website's virtual host already keeps Apache from starting.
        self.other.write_text(vhost_text('gone1234', 'other.test'))
        status, reason = self.apply(self.write())
        self.assertEqual(0, status)
        self.assertEqual('Apache already refused its configuration before this change, so nothing was changed. '
                         'Correct this first: AH00543: apache2: bad user name gone1234', reason)
        self.assertFalse(self.vhost.exists())
        self.assertFalse(self.pool.exists())
        self.assertEqual([], self.restarts)
        # The other website's file is not this job's to remove.
        self.assertEqual(vhost_text('gone1234', 'other.test'), self.other.read_text())

    def test_a_failure_that_names_the_changed_file_is_the_change(self):
        self.other.write_text(vhost_text('gone1234', 'other.test'))
        # example.test.conf is read before other.test.conf.
        status, reason = self.apply(lambda: self.vhost.write_text('NotADirective\n') and None)
        self.assertEqual(0, status)
        self.assertTrue(reason.startswith('Apache refused this configuration, so it was not put in place: '), reason)
        self.assertIn(str(self.vhost), reason)
        self.assertFalse(self.vhost.exists())

    def test_a_change_that_corrects_a_failing_configuration_is_accepted(self):
        self.vhost.write_text('NotADirective\n')
        self.assertFalse(self.apache.test()[0])
        self.assertEqual((1, 'None'), self.apply(self.write(pool=False)))
        self.assertEqual(vhost_text('siteuser'), self.vhost.read_text())
        self.assertEqual(1, len(self.restarts))

    def test_apache_that_does_not_come_up_gets_its_earlier_configuration_back(self):
        self.restart_problem = 'Apache did not start; see "systemctl status apache2".'
        self.assertEqual((0, self.restart_problem), self.apply(self.write()))
        self.assertFalse(self.vhost.exists())
        self.assertFalse(self.pool.exists())
        # Restarted with the new file, then again with what it ran before.
        self.assertEqual([['example.test.conf', 'other.test.conf'], ['other.test.conf']], self.restarts)

    def test_a_change_that_cannot_be_made_leaves_nothing_behind(self):
        def half():
            self.vhost.write_text(vhost_text('siteuser'))
            raise FileNotFoundError(2, 'No such file or directory', '/etc/php/9.9/fpm/pool.d/example.test.conf')

        def said_why():
            self.vhost.write_text(vhost_text('siteuser'))
            return 'could not write the pool'

        for change, expected in ((half, 'No such file or directory'), (said_why, 'could not write the pool')):
            status, reason = self.apply(change)
            self.assertEqual(0, status)
            self.assertIn(expected, reason)
            self.assertFalse(self.vhost.exists())
            self.assertEqual([], self.restarts)


class ApacheWorker:
    """The real ApacheVhost methods over a folder of their own, with the services and accounts replaced."""

    def __init__(self, distro='ubuntu'):
        self.temp = tempfile.TemporaryDirectory(prefix='apache-vhost-test-')
        root = Path(self.temp.name)
        self.sites = root / 'sites-enabled'
        self.pools = root / 'pool.d'
        self.main = root / 'httpd_config.conf'
        for folder in (self.sites, self.pools / '8.3', self.pools / '8.1'):
            folder.mkdir(parents=True)
        self.main.write_text('serverName example\n')
        self.apache = Apache(self.sites)
        self.commands = []
        self.process = mock.Mock(centos='centos', cent8='cent8', debugPath=str(root / 'no-debug'))
        self.process.decideDistro.return_value = distro
        self.process.normalExecutioner.side_effect = lambda command: self.commands.append(command) or 1
        self.log = mock.Mock()
        self.sites_table = {'example.test': NS(externalApp='siteuser')}
        self.vhost = NS(configBasePath=str(self.sites) + '/', serviceName='httpd' if distro == 'cent8' else 'apache2',
                        fpmReload='reload-or-restart', sslBasePath=str(root) + '/', lswsMainConf=str(self.main),
                        GenerateSelfSignedSSL=mock.Mock(), DecidePHPPath=self.pool_path,
                        configTest=self.apache.test, deletePHPPath=mock.Mock())
        self.checks = NS(account_problem=account_problem, apply_change=checks.apply_change, said=checks.said,
                         pools_set_aside=lambda name, rpm: sorted(
                             str(path) for path in self.pools.rglob(name + checks.DISABLED_SUFFIX)))
        namespace = dict(
            ProcessUtilities=self.process, ApacheVhost=self.vhost, vhostConfs=vhostConfs, logging=self.log,
            apacheConfigCheck=self.checks, fpm_service_for_selection=phpConfig.fpm_service_for_selection,
            fpm_pool_name=phpConfig.fpm_pool_name, re=re, os=os,
            PHPManager=NS(getPHPString=lambda text: text.split()[1].replace('.', '')),
            Websites=NS(objects=NS(get=lambda domain: self.sites_table[domain])), ChildDomains=mock.Mock())
        names = ['DecideFPMServiceName', 'fpmServiceCommand', 'changePHP', 'perHostVirtualConf',
                 'perHostVirtualConfChild', 'restartApache', 'restartService', 'checkedSetup', 'setupApacheVhost',
                 'setupApacheVhostChild', 'enableProxyInMainConf', 'DeleteApacheVhost']
        for name, loaded in zip(names, load_methods('ApachController/ApacheVhosts.py', 'ApacheVhost',
                                                    names, namespace)):
            setattr(self.vhost, name, loaded)

    def pool_path(self, php, name):
        return str(self.pools / ('%s.%s' % (php[0], php[1:])) / (name + '.conf'))

    def site(self, domain='example.test'):
        return self.sites / (domain + '.conf')

    def close(self):
        self.temp.cleanup()


class VirtualHostSetupTests(unittest.TestCase):
    def worker(self, distro='ubuntu'):
        worker = ApacheWorker(distro)
        self.addCleanup(worker.close)
        return worker

    def test_virtual_host_and_pool_name_the_account_of_the_website(self):
        for distro, service, sockets, group in (('ubuntu', 'apache2', '/var/run/php/', 'nogroup'),
                                                ('cent8', 'httpd', '/var/run/php-fpm/', 'nobody')):
            with self.subTest(distro=distro):
                worker = self.worker(distro)
                self.assertEqual([1, 'None'], worker.vhost.setupApacheVhost(
                    'owner@example.test', 'siteuser', 'siteuser', 'PHP 8.3', 'example.test'))
                site = worker.site().read_text()
                self.assertEqual(2, site.count('SuexecUserGroup siteuser siteuser\n'))
                self.assertEqual([('siteuser', 'siteuser')] * 2, checks.vhost_accounts(site))
                self.assertIn('<VirtualHost *:8083>', site)
                self.assertIn('<VirtualHost *:8082>', site)
                self.assertEqual(2, site.count(
                    '<Proxy "unix:%sexample.test.sock|fcgi://php-fpm-siteuser">' % sockets))
                self.assertEqual(2, site.count('DocumentRoot /home/example.test/public_html/\n'))
                pool = Path(worker.pool_path('83', 'example.test')).read_text()
                self.assertEqual(
                    '[%s]\nlisten = %sexample.test.sock\nlisten.owner = nobody\nlisten.group = %s\n'
                    'listen.mode = 0660\nuser = siteuser\ngroup = siteuser\n'
                    % (phpConfig.fpm_pool_name('siteuser', 'example.test'), sockets, group),
                    pool[:pool.index('pm = ')])
                # Apache was asked whether it accepts the files and then restarted, once.
                self.assertEqual(['systemctl restart %s' % service], worker.commands)
                self.assertEqual(2, worker.apache.tests)
                self.assertEqual(1, worker.main.read_text().count('extprocessor apachebackend {'))

    def test_child_domain_runs_as_the_account_of_its_website(self):
        worker = self.worker()
        self.assertEqual([1, 'None'], worker.vhost.setupApacheVhostChild(
            'owner@example.test', 'siteuser', 'siteuser', 'PHP 8.1', 'shop.example.test', '/home/example.test/shop'))
        site = worker.site('shop.example.test').read_text()
        self.assertEqual([('siteuser', 'siteuser')] * 2, checks.vhost_accounts(site))
        self.assertEqual(2, site.count('DocumentRoot /home/example.test/shop\n'))
        self.assertIn('user = siteuser\ngroup = siteuser\n',
                      Path(worker.pool_path('81', 'shop.example.test')).read_text())
        self.assertEqual(['systemctl restart apache2'], worker.commands)

    def test_a_website_without_its_account_is_refused_before_anything_is_written(self):
        worker = self.worker()
        for setup in (lambda: worker.vhost.setupApacheVhost('owner@example.test', 'Examp1234', 'Examp1234',
                                                            'PHP 8.3', 'example.test'),
                      lambda: worker.vhost.setupApacheVhostChild('owner@example.test', 'Examp1234', 'Examp1234',
                                                                 'PHP 8.3', 'shop.example.test', '/home/x/shop')):
            self.assertEqual([0, 'The system user Examp1234 does not exist on this server. '
                                 'Apache and PHP-FPM cannot run this website without it.'], setup())
        self.assertEqual([], list(worker.sites.iterdir()))
        self.assertEqual([], list((worker.pools / '8.3').iterdir()))
        self.assertEqual([], worker.commands)
        self.assertEqual(0, worker.apache.tests)
        self.assertEqual('serverName example\n', worker.main.read_text())

    def test_a_php_version_without_php_fpm_is_refused_before_anything_is_written(self):
        worker = self.worker()
        status, reason = worker.vhost.setupApacheVhost('owner@example.test', 'siteuser', 'siteuser', 'PHP 7.4',
                                                       'example.test')
        self.assertEqual(0, status)
        self.assertIn('PHP-FPM for PHP 7.4 is not installed on this server', reason)
        self.assertEqual([], list(worker.sites.iterdir()))
        self.assertEqual([], worker.commands)

    def test_a_virtual_host_apache_refuses_is_removed_and_the_others_keep_running(self):
        worker = self.worker()
        worker.site('other.test').write_text(vhost_text('other1234', 'other.test'))
        # The account is there when it is looked up and gone when Apache reads the file.
        worker.checks.account_problem = lambda user: None
        status, reason = worker.vhost.setupApacheVhost('owner@example.test', 'gone1234', 'gone1234', 'PHP 8.3',
                                                       'example.test')
        self.assertEqual(0, status)
        self.assertEqual('Apache refused this configuration, so it was not put in place: '
                         'AH00543: apache2: bad user name gone1234', reason)
        self.assertEqual(['other.test.conf'], [path.name for path in worker.sites.iterdir()])
        self.assertEqual([], list((worker.pools / '8.3').iterdir()))
        # Apache was not restarted and OpenLiteSpeed was given no backend.
        self.assertEqual([], worker.commands)
        self.assertEqual('serverName example\n', worker.main.read_text())

    def test_a_server_whose_apache_already_fails_gets_no_new_virtual_host(self):
        worker = self.worker()
        worker.site('other.test').write_text(vhost_text('gone1234', 'other.test'))
        status, reason = worker.vhost.setupApacheVhost('owner@example.test', 'siteuser', 'siteuser', 'PHP 8.3',
                                                       'example.test')
        self.assertEqual(0, status)
        self.assertTrue(reason.startswith('Apache already refused its configuration before this change'), reason)
        self.assertIn('bad user name gone1234', reason)
        self.assertEqual(['other.test.conf'], [path.name for path in worker.sites.iterdir()])
        self.assertEqual([], worker.commands)

    def test_proxy_backends_are_defined_once(self):
        worker = self.worker()
        for unused in range(3):
            self.assertEqual([1, 'None'], worker.vhost.enableProxyInMainConf())
        text = worker.main.read_text()
        self.assertEqual(1, text.count('extprocessor apachebackend {'))
        self.assertEqual(1, text.count('extprocessor proxyApacheBackendSSL {'))
        self.assertTrue(text.startswith('serverName example\n'))


class VirtualHostRemovalTests(unittest.TestCase):
    def setUp(self):
        self.worker = ApacheWorker()
        self.addCleanup(self.worker.close)

    def test_removal_takes_the_virtual_host_and_the_pool_an_upgrade_set_aside(self):
        self.worker.site().write_text(vhost_text('siteuser'))
        aside = self.worker.pools / '8.3' / ('example.test.conf' + checks.DISABLED_SUFFIX)
        other = self.worker.pools / '8.3' / ('other.test.conf' + checks.DISABLED_SUFFIX)
        for path in (aside, other):
            path.write_text('kept by an upgrade\n')
        self.worker.vhost.DeleteApacheVhost('example.test')
        self.assertFalse(self.worker.site().exists())
        self.assertEqual([False, True], [aside.exists(), other.exists()])
        self.worker.vhost.deletePHPPath.assert_called_once_with('example.test')
        self.assertEqual(['systemctl restart apache2'], self.worker.commands)

    def test_a_website_that_was_not_on_apache_does_not_restart_it(self):
        self.worker.vhost.DeleteApacheVhost('example.test')
        self.assertEqual([], self.worker.commands)
        self.assertEqual(0, self.worker.apache.tests)

    def test_apache_is_not_restarted_with_a_configuration_it_refuses(self):
        self.worker.site().write_text(vhost_text('siteuser'))
        self.worker.site('other.test').write_text(vhost_text('gone1234', 'other.test'))
        self.worker.vhost.DeleteApacheVhost('example.test')
        self.assertFalse(self.worker.site().exists())
        self.assertEqual([], self.worker.commands)
        self.assertIn('Apache was not restarted because it refuses its configuration: '
                      'AH00543: apache2: bad user name gone1234', self.worker.log.writeToFile.call_args[0][0])

    def test_removing_the_refused_virtual_host_lets_apache_restart(self):
        self.worker.site().write_text(vhost_text('gone1234'))
        self.worker.site('other.test').write_text(vhost_text('other1234', 'other.test'))
        self.worker.vhost.DeleteApacheVhost('example.test')
        self.assertEqual(['systemctl restart apache2'], self.worker.commands)


class PHPChangeTests(unittest.TestCase):
    VHOST = '/usr/local/lsws/conf/vhosts/example.test/vhost.conf'

    def setUp(self):
        self.worker = ApacheWorker()
        self.addCleanup(self.worker.close)
        self.worker.site().write_text(vhost_text('siteuser'))
        self.old = Path(self.worker.pool_path('81', 'example.test'))
        self.old.write_text(pool_text('siteuser'))

    def test_change_writes_the_pool_of_the_new_version(self):
        self.assertEqual(1, self.worker.vhost.changePHP('PHP 8.3', self.VHOST))
        self.worker.vhost.deletePHPPath.assert_called_once_with('example.test')
        self.assertIn('user = siteuser\ngroup = siteuser\n',
                      Path(self.worker.pool_path('83', 'example.test')).read_text())
        self.assertEqual([['systemctl', 'reload-or-restart', '--', 'php8.3-fpm'], 'systemctl restart apache2'],
                         self.worker.commands)

    def test_nothing_is_changed_for_a_website_without_its_account(self):
        self.worker.sites_table['example.test'] = NS(externalApp='gone1234')
        result = self.worker.vhost.changePHP('PHP 8.3', self.VHOST)
        self.assertEqual('The system user gone1234 does not exist on this server. '
                         'The PHP version of example.test was not changed.', result)
        self.assert_untouched()

    def test_nothing_is_changed_for_a_version_without_php_fpm(self):
        result = self.worker.vhost.changePHP('PHP 7.4', self.VHOST)
        self.assertIn('PHP-FPM for PHP 7.4 is not installed on this server', result)
        self.assertTrue(result.endswith('The PHP version of example.test was not changed.'))
        self.assert_untouched()

    def assert_untouched(self):
        self.worker.vhost.deletePHPPath.assert_not_called()
        self.assertEqual(pool_text('siteuser'), self.old.read_text())
        self.assertEqual([], list((self.worker.pools / '8.3').iterdir()))
        self.assertEqual([], self.worker.commands)

    def test_website_worker_reports_what_the_apache_worker_refused(self):
        change = PHPChange(OLS, apache_backend=True)
        self.addCleanup(change.close)
        change.apache.changePHP.return_value = 'The system user gone1234 does not exist on this server.'
        result, output = change.run(self.VHOST, 'PHP 8.1')
        self.assertEqual(0, result[0])
        self.assertIn('The system user gone1234 does not exist on this server.', result[1])
        self.assertTrue(output.splitlines()[-1].startswith('0 The system user gone1234'), output)
        self.assertEqual([], change.events)


class ServerSwitchTests(unittest.TestCase):
    """The worker that moves a website between OpenLiteSpeed and the Apache backend."""

    def run_switch(self, result, child=False):
        master = NS(domain='example.test', adminEmail='owner@example.test', externalApp='siteuser', state=1)
        website = mock.Mock(domain='shop.example.test' if child else 'example.test', adminEmail='owner@example.test',
                            externalApp='siteuser', path='/home/example.test/shop', master=master, state=1)
        websites, children = mock.Mock(), mock.Mock()
        if child:
            websites.objects.get.side_effect = LookupError()
            children.objects.get.return_value = website
        else:
            websites.objects.get.return_value = website
        self.apache = mock.Mock(fpmReload='reload-or-restart', serviceName='apache2')
        self.apache.setupApacheVhost.return_value = result
        self.apache.setupApacheVhostChild.return_value = result
        self.process, self.logger, self.install, self.website = mock.Mock(), mock.Mock(), mock.Mock(), website
        self.inner = mock.Mock(apache=1)
        controller = mock.Mock()
        controller.checkIfApacheInstalled.return_value = 1
        switch = worker_method('_switchServer', dict(
            Websites=websites, ChildDomains=children, logging=self.logger, vhost=mock.Mock(Server_root='/usr/local/lsws'),
            os=os, sslUtilities=mock.Mock(), ApacheVhost=self.apache, ApacheController=controller,
            PHPManager=mock.Mock(), ProcessUtilities=self.process, installUtilities=self.install,
            virtualHostUtilities=self.inner))
        with mock.patch('os.path.exists', return_value=True), mock.patch('os.remove') as self.remove:
            switch(website.domain, 'PHP 8.3', 1, '/unused')
        return self.logger.CyberCPLogFileWriter.statusWriter.call_args[0][1]

    def test_a_refused_virtual_host_leaves_the_website_on_openlitespeed(self):
        for child in (False, True):
            with self.subTest(child=child):
                status = self.run_switch([0, 'The system user siteuser does not exist on this server.'], child)
                self.assertEqual('The system user siteuser does not exist on this server.[404]', status)
                # Its OpenLiteSpeed virtual host is neither removed nor replaced.
                self.remove.assert_not_called()
                self.apache.perHostVirtualConfOLS.assert_not_called()
                self.process.normalExecutioner.assert_not_called()
                self.install.installUtilities.reStartLiteSpeed.assert_not_called()
                self.website.save.assert_not_called()

    def test_an_accepted_virtual_host_replaces_the_openlitespeed_one_afterwards(self):
        for child in (False, True):
            with self.subTest(child=child):
                self.assertIn('[200]', self.run_switch([1, 'None'], child))
                self.remove.assert_called_once_with('/usr/local/lsws/conf/vhosts/%s/vhost.conf' % self.website.domain)
                names = [call[0] for call in self.apache.method_calls]
                setup = 'setupApacheVhostChild' if child else 'setupApacheVhost'
                self.assertLess(names.index(setup), names.index('perHostVirtualConfOLS'))
                self.install.installUtilities.reStartLiteSpeed.assert_called_once_with()


class SavedVirtualHostTests(unittest.TestCase):
    """The Apache Manager's editor for a website's virtual host."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='apache-save-test-')
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.site = self.folder / 'example.test.conf'
        self.site.write_text(vhost_text('siteuser'))
        (self.folder / 'other.test.conf').write_text(vhost_text('other1234', 'other.test'))
        self.apache = Apache(self.folder)
        self.restarts = []
        vhost = NS(configTest=self.apache.test, restartService=lambda: self.restarts.append(1))
        self.save = worker_method('saveApacheConfigsToFile', dict(
            os=os, ApacheVhost=vhost, logging=mock.Mock(), print=print))

    def submit(self, text):
        upload = self.folder / 'upload'
        upload.write_text(text)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.save(str(self.site), str(upload))
        self.assertFalse(upload.exists())
        return output.getvalue()

    def test_an_accepted_edit_is_saved_and_apache_restarted(self):
        edited = vhost_text('siteuser').replace('Options Indexes FollowSymLinks', 'Options FollowSymLinks')
        self.assertEqual('1,None\n', self.submit(edited))
        self.assertEqual(edited, self.site.read_text())
        self.assertEqual([1], self.restarts)

    def test_a_refused_edit_is_undone_and_apache_keeps_running(self):
        output = self.submit(vhost_text('siteuser') + 'NotADirective\n')
        self.assertTrue(output.startswith('0,Apache refused this configuration, so it was not put in place: '), output)
        self.assertIn('Invalid command NotADirective', output)
        self.assertEqual(vhost_text('siteuser'), self.site.read_text())
        self.assertEqual([], self.restarts)


class WebsiteAccountTests(unittest.TestCase):
    def create(self, problem):
        vhost = NS(Server_root='/usr/local/lsws', addUser=mock.Mock(), createDirectories=mock.Mock(return_value=[1, 'None']),
                   perHostVirtualConf=mock.Mock(return_value=1))
        create, = load_methods('plogical/vhost.py', 'vhost', ['createDirectoryForVirtualHost'], dict(
            vhost=vhost, os=NS(path=NS(exists=lambda path: True)), ProcessUtilities=mock.Mock()))
        with mock.patch.object(checks, 'account_problem', return_value=problem) as lookup:
            result = create('Example.test', 'owner@example.test', 'Examp1234', 'PHP 8.3', 0)
        vhost.addUser.assert_called_once_with('Examp1234', '/home/Example.test')
        lookup.assert_called_once_with('Examp1234')
        return vhost, result

    def test_no_website_is_made_when_its_account_could_not_be_created(self):
        vhost, result = self.create('The system user Examp1234 does not exist on this server.')
        self.assertEqual([0, 'The system account of the website could not be created. '
                             'The system user Examp1234 does not exist on this server.'], result)
        vhost.createDirectories.assert_not_called()
        vhost.perHostVirtualConf.assert_not_called()

    def test_creation_goes_on_with_the_account(self):
        vhost, result = self.create(None)
        self.assertEqual([1, 'None'], result)
        vhost.createDirectories.assert_called_once()

    def test_account_names_are_made_in_lower_case(self):
        # Debian's adduser refuses a name with a capital letter.
        made = 0
        for relative in ('websiteFunctions/website.py', 'cli/cyberPanel.py', 'plogical/applicationInstaller.py',
                         'plogical/cPanelImporter.py'):
            for line in (ROOT / relative).read_text().splitlines():
                if 're.findall("[a-zA-Z]+"' in line and not line.lstrip().startswith('#'):
                    made += 1
                    self.assertRegex(line, r'\)\)\[:\d\]\.lower\(\)', relative)
        self.assertEqual(5, made)
        self.assertEqual('examp', ''.join(re.findall('[a-zA-Z]+', 'Example-1.TEST'))[:5].lower())


class UpgradeRepairTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='apache-repair-test-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.sites = root / 'sites-enabled'
        self.pools = root / 'etc' / 'php' / '8.3' / 'fpm' / 'pool.d'
        for folder in (self.sites, self.pools):
            folder.mkdir(parents=True)
        self.good = self.sites / 'other.test.conf'
        self.good.write_text(vhost_text('other1234', 'other.test'))
        (self.pools / 'other.test.conf').write_text(pool_text('other1234', 'other.test'))
        (self.pools / 'www.conf').write_text('[php83default]\nuser = www-data\ngroup = www-data\n')
        self.apache = Apache(self.sites)
        self.commands = []
        self.failing = set()
        self.messages = []

    def succeeds(self, *command):
        self.commands.append(list(command))
        return command[-1] not in self.failing

    def repair(self):
        return checks.repair(log=self.messages.append, rpm_family=False, vhost_folder=str(self.sites),
                             pool_folders=[str(self.pools) + '/'], test=self.apache.test, succeeds=self.succeeds,
                             getpwnam=getpwnam, getgrnam=getgrnam)

    def names(self, folder):
        return sorted(path.name for path in folder.iterdir())

    def test_a_healthy_server_is_left_alone(self):
        self.assertEqual('not needed', self.repair())
        self.assertEqual(['other.test.conf'], self.names(self.sites))
        self.assertEqual(['other.test.conf', 'www.conf'], self.names(self.pools))
        self.assertEqual(([], []), (self.commands, self.messages))

    def test_a_missing_account_no_longer_keeps_the_services_from_starting(self):
        bad = self.sites / 'example.test.conf'
        bad.write_text(vhost_text('Examp1234'))
        bad.chmod(0o640)
        (self.pools / 'example.test.conf').write_text(pool_text('Examp1234'))
        self.assertEqual('repaired', self.repair())
        # The virtual host stays under its own name, so its domain is not
        # answered by the virtual host of another website; only the line
        # Apache cannot load has become a comment.
        self.assertEqual(['example.test.conf', 'other.test.conf'], self.names(self.sites))
        self.assertEqual(2, bad.read_text().count(checks.DISABLED_LINE + 'SuexecUserGroup Examp1234 Examp1234\n'))
        self.assertEqual([], checks.vhost_accounts(bad.read_text()))
        self.assertEqual(vhost_text('Examp1234'), bad.read_text().replace(checks.DISABLED_LINE, ''))
        self.assertEqual(0o640, stat.S_IMODE(bad.stat().st_mode))
        self.assertEqual(vhost_text('other1234', 'other.test'), self.good.read_text())
        # PHP-FPM cannot run a pool as a missing user: the pool is set aside
        # with its content kept.
        self.assertEqual(['example.test.conf' + checks.DISABLED_SUFFIX, 'other.test.conf', 'www.conf'],
                         self.names(self.pools))
        self.assertEqual(pool_text('Examp1234'),
                         (self.pools / ('example.test.conf' + checks.DISABLED_SUFFIX)).read_text())
        self.assertEqual([['systemctl', 'reload-or-restart', '--', 'php8.3-fpm'], ['systemctl', 'restart', 'apache2']],
                         self.commands)
        self.assertEqual(3, len(self.messages))
        self.assertIn('names the missing system account Examp1234', self.messages[0])
        self.assertIn(str(bad), self.messages[1])
        self.assertEqual('Apache accepts its configuration again and was restarted.', self.messages[2])
        # A second upgrade finds nothing to do.
        del self.commands[:], self.messages[:]
        self.assertEqual('not needed', self.repair())
        self.assertEqual(([], []), (self.commands, self.messages))

    def test_a_configuration_that_fails_for_another_reason_is_reported_and_not_changed(self):
        broken = self.sites / 'example.test.conf'
        broken.write_text(vhost_text('siteuser') + 'NotADirective\n')
        self.assertEqual('failed', self.repair())
        self.assertEqual(['example.test.conf', 'other.test.conf'], self.names(self.sites))
        self.assertEqual([], self.commands)
        self.assertEqual(1, len(self.messages))
        self.assertTrue(self.messages[0].startswith('WARNING: Apache refuses its configuration'))
        self.assertIn('Invalid command NotADirective', self.messages[0])

    def test_files_that_are_not_the_panels_are_reported_and_left(self):
        own = self.sites.parent / 'sites-available.conf'
        own.write_text(vhost_text('gone1234', 'own.test'))
        (self.sites / 'own.test.conf').symlink_to(own)
        (self.pools / 'www.conf').write_text('[www]\nuser = gone1234\ngroup = gone1234\n')
        self.assertEqual('failed', self.repair())
        self.assertTrue((self.sites / 'own.test.conf').is_symlink())
        self.assertEqual(['other.test.conf', 'www.conf'], self.names(self.pools))
        self.assertEqual([], self.commands)
        self.assertEqual(3, len(self.messages))
        for message in self.messages:
            self.assertTrue(message.startswith('WARNING: '), message)
        self.assertIn('It was left as it is.', self.messages[0])
        self.assertIn('It was left as it is.', self.messages[1])

    def test_a_service_that_does_not_start_is_reported(self):
        (self.sites / 'example.test.conf').write_text(vhost_text('gone1234'))
        (self.pools / 'example.test.conf').write_text(pool_text('gone1234'))
        self.failing = {'php8.3-fpm', 'apache2'}
        self.assertEqual('failed', self.repair())
        self.assertIn('WARNING: php8.3-fpm did not start; see "systemctl status php8.3-fpm".', self.messages)
        self.assertIn('WARNING: Apache accepts its configuration but did not start; '
                      'see "systemctl status apache2".', self.messages)

    def test_service_of_a_pool_folder(self):
        for folder, unit in (('/etc/php/8.3/fpm/pool.d/', 'php8.3-fpm'), ('/etc/php/5.6/fpm/pool.d', 'php5.6-fpm'),
                             ('/etc/opt/remi/php83/php-fpm.d/', 'php83-php-fpm'),
                             ('/opt/remi/php54/root/etc/php-fpm.d/', 'php54-php-fpm'), ('/srv/pools/', None)):
            self.assertEqual(unit, checks.fpm_unit(folder))

    def test_nothing_is_done_on_a_server_without_apache(self):
        with mock.patch.object(checks.os.path, 'exists', return_value=False):
            self.assertEqual('not installed', checks.repair(log=self.messages.append, succeeds=self.succeeds))
        self.assertEqual(([], []), (self.commands, self.messages))

    def test_a_pool_that_was_set_aside_is_found_again_by_its_name(self):
        pool = self.pools / ('example.test.conf' + checks.DISABLED_SUFFIX)
        for path in (pool, self.pools / ('example.test2.conf' + checks.DISABLED_SUFFIX),
                     self.pools / 'example.test.conf'):
            path.write_text('kept\n')
        with mock.patch.object(checks, 'DEB_POOLS', (str(self.pools.parents[2]) + '/*/fpm/pool.d/',)):
            self.assertEqual([str(pool)], checks.pools_set_aside('example.test.conf', False))
            self.assertEqual([], checks.pools_set_aside('*.conf', False))

    def test_upgrade_runs_the_repair_before_its_own_apache_step(self):
        tree = ast.parse((ROOT / 'plogical' / 'upgrade.py').read_text())
        upgrade = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Upgrade')
        found = 0
        for function in upgrade.body:
            if not isinstance(function, ast.FunctionDef):
                continue
            called = {}
            for node in ast.walk(function):
                if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
                    name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr
                    called.setdefault(name, node.lineno)
            if 'repair_apache_backend' not in called:
                continue
            found += 1
            imported = [(alias.name, alias.asname) for node in ast.walk(function)
                        if isinstance(node, ast.ImportFrom) and node.module == 'ApachController.apacheConfigCheck'
                        for alias in node.names]
            self.assertEqual([('repair', 'repair_apache_backend')], imported)
            self.assertLess(called['repair_apache_backend'], called['fixApacheConfiguration'])
        self.assertEqual(1, found)


if __name__ == '__main__':
    unittest.main()
