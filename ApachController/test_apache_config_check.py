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
import time
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from ApachController import apacheConfigCheck as checks
from managePHP import phpConfig
from plogical.test_php_restart_marker import OLS, PHPChange, load_methods
from plogical.test_server_switch_mail_php import method as worker_method
from plogical import websiteAccount
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

    def test_only_literal_names_without_an_account_are_unknown(self):
        # An id, PHP-FPM's $pool and a variable are resolved by the service.
        pairs = [('siteuser', 'siteuser'), ('gone1234', 'gone1234'), ('#1001', '#1001'), ('33', None),
                 ('gone1234', 'siteuser'), (None, 'nogroup'), ('$pool', '$pool'),
                 ('${APACHE_RUN_USER}', '${APACHE_RUN_GROUP}')]
        self.assertEqual(['gone1234'], checks.unknown_accounts(pairs, getpwnam, getgrnam))
        self.assertEqual([], checks.unknown_accounts(
            checks.pool_accounts('[$pool]\nuser = $pool\ngroup = ${FPM_GROUP}\n'), getpwnam, getgrnam))
        self.assertEqual(['nobody'], checks.unknown_accounts([('nobody', 'nobody')], getpwnam, getgrnam))


class ConfigTestTests(unittest.TestCase):
    def test_command_of_each_distribution_family(self):
        self.assertEqual(['/usr/sbin/apache2ctl', '-t'], checks.config_test_command(False))
        self.assertEqual(['/usr/sbin/httpd', '-t'], checks.config_test_command(True))

    def test_result_is_the_exit_status_and_what_apache_said(self):
        calls = []

        def run(command, timeout):
            calls.append((command, timeout))
            return status, output

        for status, output, expected in ((0, 'Syntax OK\n', (True, 'Syntax OK')),
                                         (1, 'AH00543: apache2: bad user name x\n', (False, 'AH00543: apache2: bad user name x')),
                                         (1, '', (False, ''))):
            self.assertEqual(expected, checks.config_test(['/usr/sbin/apache2ctl', '-t'], run))
        self.assertEqual((['/usr/sbin/apache2ctl', '-t'], 120), calls[0])

    def test_a_test_that_cannot_run_has_not_passed(self):
        def missing(command, timeout):
            raise FileNotFoundError(2, 'No such file or directory')

        def slow(command, timeout):
            raise subprocess.TimeoutExpired(command, timeout)

        for run in (missing, slow):
            passed, output = checks.config_test(['/usr/sbin/httpd', '-t'], run)
            self.assertFalse(passed)
            self.assertIn('/usr/sbin/httpd could not be run', output)

    def test_command_output_and_status_are_returned(self):
        self.assertEqual((3, 'out\nerr\n'),
                         checks.bounded_run(['/bin/sh', '-c', 'echo out; echo err >&2; exit 3'], 30))

    def test_time_limit_ends_what_the_command_started(self):
        # apache2ctl is a shell that starts apache2; both hold the output.
        marker = tempfile.NamedTemporaryFile(prefix='apache-check-test-')
        self.addCleanup(marker.close)
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            checks.bounded_run(['/bin/sh', '-c', 'sleep 60 & echo $! > %s; wait' % marker.name], 1)
        self.assertLess(time.monotonic() - started, 20)
        child = int(Path(marker.name).read_text())
        for unused in range(50):
            if not Path('/proc/%d' % child).exists():
                break
            time.sleep(0.1)
        self.assertFalse(Path('/proc/%d' % child).exists())
        passed, output = checks.config_test(['/bin/sh', '-c', 'sleep 60 & wait'], timeout=1)
        self.assertEqual(False, passed)
        self.assertIn('could not be run', output)

    def test_apache_is_installed_with_its_control_program(self):
        for present, family in (({'/usr/sbin/httpd'}, True),
                                ({'/usr/sbin/apache2', '/usr/sbin/apache2ctl'}, False),
                                # What removing the apache2 package leaves.
                                ({'/usr/sbin/apache2'}, None), ({'/usr/sbin/apache2ctl'}, None), (set(), None)):
            self.assertIs(family, checks.installed_family(lambda path: path in present))

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

    def test_an_administrators_edit_is_kept_beside_another_failure(self):
        self.other.write_text(vhost_text('gone1234', 'other.test'))
        status, reason = checks.apply_change([str(self.vhost)], self.write(pool=False), self.apache.test,
                                             self.restart, keep_beside_other_failure=True)
        self.assertEqual(2, status)
        self.assertEqual('Apache was not restarted: it refused its configuration before this change already, '
                         'for a reason outside this file: AH00543: apache2: bad user name gone1234', reason)
        self.assertEqual(vhost_text('siteuser'), self.vhost.read_text())
        self.assertEqual([], self.restarts)

    def test_two_faulty_files_can_be_corrected_one_after_the_other(self):
        first, second = self.folder / 'a.test.conf', self.folder / 'b.test.conf'
        for path in (first, second):
            path.write_text('NotADirective\n')

        def correct(path):
            return checks.apply_change([str(path)], lambda: path.write_text(vhost_text('siteuser', path.stem)) and None,
                                       self.apache.test, self.restart, keep_beside_other_failure=True)

        # Apache names a.test.conf first; correcting b.test.conf is kept all the same.
        self.assertEqual(2, correct(second)[0])
        self.assertEqual(vhost_text('siteuser', 'b.test'), second.read_text())
        self.assertEqual([], self.restarts)
        self.assertEqual((1, 'None'), correct(first))
        self.assertEqual(1, len(self.restarts))

    def test_an_edit_that_apache_refuses_is_not_kept_either_way(self):
        self.other.write_text(vhost_text('gone1234', 'other.test'))
        self.vhost.write_text(vhost_text('siteuser'))
        status, reason = checks.apply_change(
            [str(self.vhost)], lambda: self.vhost.write_text('NotADirective\n') and None, self.apache.test,
            self.restart, keep_beside_other_failure=True)
        self.assertEqual(0, status)
        self.assertIn(str(self.vhost), reason)
        self.assertEqual(vhost_text('siteuser'), self.vhost.read_text())

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
                         with_proxy_backends=checks.with_proxy_backends, replace_file=checks.replace_file,
                         vhost_accounts=checks.vhost_accounts,
                         unknown_accounts=lambda pairs: checks.unknown_accounts(pairs, getpwnam, getgrnam),
                         reopen_virtual_host=lambda path: checks.reopen_virtual_host(path, getpwnam, getgrnam),
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
                 'setupApacheVhostChild', 'enableProxyInMainConf', 'DeleteApacheVhost', 'restoreVhost']
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
        self.assertEqual('serverName example\n' + vhostConfs.proxyApacheBackend + vhostConfs.proxyApacheBackendSSL,
                         text)

    def test_backends_point_at_the_ports_of_the_virtual_hosts(self):
        # Without SSL the virtual hosts are on 8083, with it on 8082.
        self.assertIn('<VirtualHost *:8083>', vhostConfs.apacheConf)
        self.assertIn('<VirtualHost *:8082>', vhostConfs.apacheConfSSL)
        self.assertIn('SSLEngine on', vhostConfs.apacheConfSSL)
        self.assertNotIn('SSLEngine', vhostConfs.apacheConf)
        self.assertRegex(vhostConfs.proxyApacheBackend, r'(?m)^\s*address\s+http://127\.0\.0\.1:8083$')
        self.assertRegex(vhostConfs.proxyApacheBackendSSL, r'(?m)^\s*address\s+https://127\.0\.0\.1:8082$')

    def test_repeated_and_exchanged_backends_of_earlier_releases_are_corrected(self):
        exchanged = ('\nextprocessor apachebackend {\n  type                    proxy\n'
                     '  address                 127.0.0.1:8082\n  maxConns                100\n}\n'
                     '\nextprocessor proxyApacheBackendSSL {\n  type                    proxy\n'
                     '  address                 https://127.0.0.1:8083\n  maxConns                100\n}\n')
        tuned = vhostConfs.proxyApacheBackend.replace('maxConns                100', 'maxConns                400')
        other = 'extprocessor lsphp83 {\n  type lsapi\n  address uds://tmp/lshttpd/lsphp.sock\n}\n'
        pair = (vhostConfs.proxyApacheBackend, vhostConfs.proxyApacheBackendSSL)
        for before, after in (
                # Once per website, as releases up to 3.0.12 wrote them.
                ('listener x {\n}\n' + ''.join(pair) * 3 + other, 'listener x {\n}\n' + ''.join(pair) + other),
                # The pair an earlier upgrade wrote, alone and beside a right pair.
                ('a 1\n' + exchanged, 'a 1\n\n\n' + ''.join(pair)),
                ('a 1\n' + exchanged + ''.join(pair), 'a 1\n\n\n' + ''.join(pair)),
                # A right block keeps what an administrator set in it.
                (tuned + pair[0] + pair[1], tuned + pair[1]),
                ('no final newline', 'no final newline\n' + ''.join(pair))):
            with self.subTest(before=before[:30]):
                self.assertEqual(after, checks.with_proxy_backends(before, *pair))
                # Nothing is left to do a second time.
                self.assertEqual(after, checks.with_proxy_backends(after, *pair))
        worker = self.worker()
        worker.main.write_text('serverName example\n' + exchanged + ''.join(pair) * 2)
        worker.main.chmod(0o640)
        self.assertEqual([1, 'None'], worker.vhost.enableProxyInMainConf())
        self.assertEqual('serverName example\n\n\n' + ''.join(pair), worker.main.read_text())
        self.assertEqual(0o640, stat.S_IMODE(worker.main.stat().st_mode))

    def test_virtual_host_of_a_backup_replaces_the_new_one_only_if_apache_accepts_it(self):
        worker = self.worker()
        made = vhost_text('siteuser')
        worker.site().write_text(made)
        backup = worker.sites.parent / 'apache.conf'
        # The account the website had on the server the backup was made on.
        backup.write_text(vhost_text('Examp1234'))
        status, reason = worker.vhost.restoreVhost(str(backup), str(worker.site()))
        self.assertEqual(0, status)
        self.assertIn('names the system account Examp1234, which does not exist on this server', reason)
        self.assertEqual(made, worker.site().read_text())
        self.assertEqual([], worker.commands)
        backup.write_text(made + 'NotADirective\n')
        status, reason = worker.vhost.restoreVhost(str(backup), str(worker.site()))
        self.assertEqual(0, status)
        self.assertIn('Invalid command NotADirective', reason)
        self.assertEqual(made, worker.site().read_text())
        custom = made.replace('Options Indexes FollowSymLinks', 'Options FollowSymLinks')
        backup.write_text(custom)
        self.assertEqual([1, 'None'], worker.vhost.restoreVhost(str(backup), str(worker.site())))
        self.assertEqual(custom, worker.site().read_text())
        self.assertEqual(['systemctl restart apache2'], worker.commands)


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
        self.assertIn('Apache was not restarted because its configuration test did not pass: '
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

    def test_change_reopens_a_website_an_upgrade_closed_once_its_account_exists(self):
        # The upgrade found the account missing; it has been created since.
        USERS.discard('siteuser')
        self.addCleanup(USERS.add, 'siteuser')
        checks.close_virtual_host(str(self.worker.site()), getpwnam, getgrnam)
        self.assertIn(checks.CLOSED_BEGIN, self.worker.site().read_text())
        aside = Path(checks.set_pool_aside(str(self.old)))
        USERS.add('siteuser')
        self.assertEqual(1, self.worker.vhost.changePHP('PHP 8.1', self.VHOST))
        self.assertEqual(vhost_text('siteuser'), self.worker.site().read_text())
        self.assertIn('user = siteuser\ngroup = siteuser\n', self.old.read_text())
        self.assertFalse(aside.exists())
        self.assertEqual([['systemctl', 'reload-or-restart', '--', 'php8.1-fpm'], 'systemctl restart apache2'],
                         self.worker.commands)

    def test_a_closed_website_stays_closed_while_its_account_is_missing(self):
        USERS.discard('siteuser')
        self.addCleanup(USERS.add, 'siteuser')
        checks.close_virtual_host(str(self.worker.site()), getpwnam, getgrnam)
        closed = self.worker.site().read_text()
        self.worker.sites_table['example.test'] = NS(externalApp='siteuser')
        result = self.worker.vhost.changePHP('PHP 8.3', self.VHOST)
        self.assertIn('The system user siteuser does not exist on this server.', result)
        self.assertEqual(closed, self.worker.site().read_text())
        self.assertFalse(checks.reopen_virtual_host(str(self.worker.site()), getpwnam, getgrnam))
        self.assertEqual(closed, self.worker.site().read_text())
        self.assertEqual([], self.worker.commands)

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


    def test_an_edit_is_kept_while_another_virtual_host_keeps_apache_from_starting(self):
        (self.folder / 'other.test.conf').write_text(vhost_text('gone1234', 'other.test'))
        edited = vhost_text('siteuser').replace('Options Indexes FollowSymLinks', 'Options FollowSymLinks')
        output = self.submit(edited)
        self.assertEqual('0,The virtual host was saved. Apache was not restarted: it refused its configuration '
                         'before this change already, for a reason outside this file: '
                         'AH00543: apache2: bad user name gone1234\n', output)
        self.assertEqual(edited, self.site.read_text())
        self.assertEqual([], self.restarts)


class ChildDomainCreationTests(unittest.TestCase):
    def create(self, setup):
        events = []
        master = NS(state=1, adminEmail='owner@example.test', externalApp='siteuser',
                    package=NS(allowedDomains=0, allowFullDomain=1, memoryLimitMB=0, maxConnections=10,
                               procSoftLimit=10, procHardLimit=10), childdomains_set=mock.MagicMock())
        websites, children = mock.MagicMock(), mock.MagicMock()
        websites.objects.get.return_value = master
        for model in (websites, children):
            model.objects.filter.return_value.count.return_value = 0
            model.objects.count.return_value = 1
        self.row = children.return_value
        self.row.save.side_effect = lambda: events.append('save row')
        self.row.delete.side_effect = lambda: events.append('delete row')
        vhost = mock.MagicMock(Server_root='/nonexistent-lsws')
        vhost.checkIfVirtualHostExists.return_value = 0
        vhost.checkIfAliasExists.return_value = 0
        vhost.createDirectoryForDomain.return_value = (1, 'None')
        vhost.createConfigInMainDomainHostFile.return_value = (1, 'None')
        vhost.deleteCoreConf.side_effect = lambda *args: events.append('delete configuration')
        acl = mock.MagicMock()
        acl.FindIfChild.return_value = 0
        process = mock.MagicMock(OLS=0)
        process.decideServer.return_value = 0
        apache, controller = mock.MagicMock(), mock.MagicMock()
        controller.checkIfApacheInstalled.return_value = 1
        apache.setupApacheVhostChild.return_value = setup
        inner = mock.MagicMock(redisConf='/nonexistent-lsws/redis.conf')
        inner.dkimServicesInstalled.return_value = False
        self.logger = mock.MagicMock()
        create = worker_method('_createDomain', dict(
            os=os, open=mock.MagicMock(), logging=self.logger, Administrator=mock.MagicMock(), Websites=websites,
            ChildDomains=children, DNS=mock.MagicMock(), mailUtilities=mock.MagicMock(),
            sslUtilities=mock.MagicMock(), ACLManager=acl, vhost=vhost, installUtilities=mock.MagicMock(),
            ProcessUtilities=process, ApacheController=controller, ApacheVhost=apache, PHPManager=mock.MagicMock(),
            virtualHostUtilities=inner))
        result = create('example.test', 'shop.example.test', 'PHP 8.3', '/home/example.test/shop', 0, 0, 0, 'admin', 1)
        return result, events

    def test_a_child_domain_apache_refuses_leaves_no_row_behind(self):
        result, events = self.create([0, 'Apache refused this configuration, so it was not put in place: x'])
        self.assertEqual((0, 'Apache refused this configuration, so it was not put in place: x'), result)
        self.assertEqual(['save row', 'delete configuration', 'delete row'], events)

    def test_an_accepted_child_domain_keeps_its_row(self):
        result, events = self.create([1, 'None'])
        self.assertEqual((1, 'None'), result)
        self.assertEqual(['save row'], events)


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

    def test_next_name_after_a_match_is_built_from_the_new_name(self):
        # The database also matches a stored Examp1234 for examp1234.
        text = (ROOT / 'websiteFunctions' / 'website.py').read_text()
        self.assertIn("externalApp = '%s%s' % (baseName, str(counter))", text)
        self.assertNotIn("externalApp = '%s%s' % (tWeb.externalApp, str(counter))", text)
        stored = {'examp1234', 'examp12340'}
        name = websiteAccount.new_name('Example.test', lambda name: name in stored, number=lambda low, high: 1234)
        self.assertEqual('examp12341', name)
        self.assertEqual('examp5678', websiteAccount.new_name('Example.test', lambda name: False,
                                                              number=lambda low, high: 5678))

    def test_a_name_the_servers_tool_refuses_is_known(self):
        for name, debian, rpm in (('examp1234', True, True), ('nobody', True, True), ('Examp1234', False, True),
                                  ('user.name', False, True), ('1site', False, True), ('', False, False),
                                  (None, False, False), ('a b', False, False), ('a/b', False, False),
                                  ('-x', False, False), ('u' * 33, False, False)):
            with self.subTest(name=name):
                self.assertEqual(debian, websiteAccount.acceptable(name, debian=True))
                self.assertEqual(rpm, websiteAccount.acceptable(name, debian=False))

    def test_a_restored_website_keeps_its_name_or_gets_one_this_server_takes(self):
        taken = {'examp1234'}.__contains__
        self.assertEqual('examp1234', websiteAccount.restored_name('examp1234', 'example.test', taken, debian=True))
        self.assertEqual('Examp1234', websiteAccount.restored_name('Examp1234', 'Example.test', taken, debian=False))
        name = websiteAccount.restored_name('Examp1234', 'Example.test', taken, debian=True)
        self.assertRegex(name, r'^examp\d{4,5}$')
        self.assertNotIn(name, ('examp1234', 'Examp1234'))
        self.assertTrue(websiteAccount.acceptable(name, debian=True))

    def test_configuration_of_a_backup_names_the_account_the_website_has_here(self):
        site = vhostConfs.olsMasterConf.replace('{virtualHostUser}', 'Examp1234')
        child = vhostConfs.olsChildConf.replace('{externalApp}', 'Examp12345678').replace(
            '{externalAppMaster}', 'Examp1234') + '# MyExamp1234 and Examp1234x stay\n'
        for text in (site, child):
            renamed = websiteAccount.renamed_in_configuration(text, 'Examp1234', 'examp5678')
            self.assertIn('  extUser                 examp5678\n  extGroup                examp5678\n', renamed)
            self.assertEqual(text.count('Examp1234') - (2 if text is child else 0), renamed.count('examp5678'))
        self.assertIn('extprocessor examp5678 {', websiteAccount.renamed_in_configuration(site, 'Examp1234', 'examp5678'))
        renamed = websiteAccount.renamed_in_configuration(child, 'Examp1234', 'examp5678')
        self.assertIn('extprocessor examp56785678 {', renamed)
        self.assertIn('# MyExamp1234 and Examp1234x stay\n', renamed)
        self.assertEqual(site, websiteAccount.renamed_in_configuration(site, 'Examp1234', 'Examp1234'))
        self.assertEqual(site, websiteAccount.renamed_in_configuration(site, '', 'examp5678'))

    def test_restore_uses_the_name_it_decided_on_and_no_other(self):
        text = (ROOT / 'plogical' / 'backupUtilities.py').read_text()
        # The name in the backup decides the name at creation; afterwards it
        # only says what to replace in the configuration files of the backup.
        self.assertEqual(1, text.count("externalApp = backupMetaData.find('externalApp').text"))
        self.assertEqual(1, text.count("accountInBackup = backupMetaData.find('externalApp').text"))
        self.assertEqual(2, text.count("backupMetaData.find('externalApp').text"))
        self.assertEqual(2, text.count('\n' + ' ' * 20 + 'useAccountHere(completPathToConf)\n')
                         + text.count('\n' + ' ' * 36 + 'useAccountHere(completPathToConf)\n'))
        decided = text.index('externalApp = restored_name(externalApp, domain, accountNameTaken)')
        created = text.index('result = virtualHostUtilities.createVirtualHost(domain, siteUser.email, '
                             'stored_php_selection(phpSelection), externalApp,')
        self.assertLess(text.index("externalApp = backupMetaData.find('externalApp').text"), decided)
        self.assertLess(decided, created)
        # The virtual host of the backup never replaces the new one unchecked.
        self.assertNotIn('copy(confPathApache, finalConfPathApache)', text)
        self.assertNotIn('copy(childConfPathinBKUPApache, finalConfPathApache)', text)
        self.assertEqual(2, text.count('ApacheVhost.restoreVhost('))

    def test_apache_counts_as_installed_only_with_its_control_program(self):
        source = ROOT / 'ApachController' / 'ApacheController.py'
        owner = [node for node in ast.parse(source.read_text()).body
                 if isinstance(node, ast.ClassDef) and node.name == 'ApacheController']
        for distro, present, expected in (
                ('ubuntu', {'/usr/sbin/apache2', '/usr/sbin/apache2ctl', '/etc/php/8.3/fpm/pool.d/'}, 1),
                ('ubuntu', {'/usr/sbin/apache2', '/etc/php/8.3/fpm/pool.d/'}, 0),
                ('ubuntu', {'/usr/sbin/apache2ctl', '/etc/php/8.3/fpm/pool.d/'}, 0),
                ('cent8', {'/usr/sbin/httpd', '/etc/opt/remi/php83/php-fpm.d/'}, 1),
                ('cent8', {'/etc/opt/remi/php83/php-fpm.d/'}, 0)):
            process = mock.Mock(centos='centos', cent8='cent8')
            process.decideDistro.return_value = distro
            namespace = dict(ProcessUtilities=process, logging=mock.Mock(), ApacheVhost=mock.Mock(),
                             os=NS(path=NS(exists=present.__contains__, isdir=present.__contains__)))
            exec(compile(ast.Module(body=owner, type_ignores=[]), str(source), 'exec'), namespace)
            with self.subTest(distro=distro, present=sorted(present)):
                self.assertEqual(expected, namespace['ApacheController'].checkIfApacheInstalled())


class UpgradeRepairTests(unittest.TestCase):
    """The upgrade step, on the Debian family unless a test says otherwise."""
    rpm_family = False
    service = 'apache2'
    unit = 'php8.3-fpm'
    pool_folder = ('etc', 'php', '8.3', 'fpm', 'pool.d')
    domains = ('example.test', 'other.test', 'shop.example.test')

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='apache-repair-test-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.sites = root / 'sites'
        self.pools = root.joinpath(*self.pool_folder)
        for folder in (self.sites, self.pools):
            folder.mkdir(parents=True)
        self.good = self.sites / 'other.test.conf'
        self.good.write_text(vhost_text('other1234', 'other.test'))
        (self.pools / 'other.test.conf').write_text(pool_text('other1234', 'other.test'))
        (self.pools / 'www.conf').write_text('[default]\nuser = www-data\ngroup = www-data\n')
        self.apache = Apache(self.sites)
        self.commands = []
        self.failing = set()
        self.disabled = set()
        self.messages = []

    def succeeds(self, *command):
        self.commands.append(list(command))
        if command[1] == 'is-enabled':
            return command[-1] not in self.disabled
        return command[-1] not in self.failing

    def repair(self):
        return checks.repair(self.domains, log=self.messages.append, rpm_family=self.rpm_family,
                             vhost_folder=str(self.sites), pool_folders=[str(self.pools) + '/'],
                             test=self.apache.test, succeeds=self.succeeds, getpwnam=getpwnam, getgrnam=getgrnam)

    def names(self, folder):
        return sorted(path.name for path in folder.iterdir())

    def started(self, unit, action):
        return [['systemctl', 'is-enabled', '--quiet', '--', unit], ['systemctl', action, '--', unit]]

    def break_example(self, user='Examp1234'):
        bad = self.sites / 'example.test.conf'
        bad.write_text(vhost_text(user))
        bad.chmod(0o640)
        (self.pools / 'example.test.conf').write_text(pool_text(user))
        return bad

    def test_a_healthy_server_is_left_alone(self):
        # $pool and a variable are PHP-FPM's to resolve, not names to look up.
        (self.pools / 'shop.example.test.conf').write_text('[shop]\nuser = $pool\ngroup = ${FPM_GROUP}\n')
        self.assertEqual('not needed', self.repair())
        self.assertEqual(['other.test.conf'], self.names(self.sites))
        self.assertEqual(['other.test.conf', 'shop.example.test.conf', 'www.conf'], self.names(self.pools))
        self.assertEqual(([], []), (self.commands, self.messages))

    def test_a_missing_account_no_longer_keeps_the_services_from_starting(self):
        bad = self.break_example()
        self.assertEqual('repaired', self.repair())
        # The virtual host stays under its own name, so its domain is not
        # answered by the virtual host of another website. Both of its
        # blocks refuse every request: without the SuexecUserGroup line
        # Apache would otherwise serve the website as its own user.
        self.assertEqual(['example.test.conf', 'other.test.conf'], self.names(self.sites))
        closed = bad.read_text()
        self.assertEqual([], checks.vhost_accounts(closed))
        for port in ('8083', '8082'):
            block = closed[closed.index('<VirtualHost *:%s>' % port):]
            block = block[:block.index('</VirtualHost>')]
            self.assertEqual(1, block.count(checks.DISABLED_LINE + 'SuexecUserGroup Examp1234 Examp1234\n'))
            self.assertRegex(block, r'(?m)^\s*%s\n\s*<Location "/">\n\s*Require all denied\n\s*</Location>\n\s*%s\n'
                             % (re.escape(checks.CLOSED_BEGIN), re.escape(checks.CLOSED_END)))
        self.assertEqual(0o640, stat.S_IMODE(bad.stat().st_mode))
        self.assertEqual(vhost_text('other1234', 'other.test'), self.good.read_text())
        # PHP-FPM cannot run a pool as a missing user: the pool is set aside
        # with its content kept.
        self.assertEqual(['example.test.conf' + checks.DISABLED_SUFFIX, 'other.test.conf', 'www.conf'],
                         self.names(self.pools))
        self.assertEqual(pool_text('Examp1234'),
                         (self.pools / ('example.test.conf' + checks.DISABLED_SUFFIX)).read_text())
        self.assertEqual(self.started(self.unit, 'reload-or-restart') + self.started(self.service, 'restart'),
                         self.commands)
        self.assertEqual(3, len(self.messages))
        self.assertIn('names the missing system account Examp1234', self.messages[0])
        self.assertIn(str(bad), self.messages[1])
        self.assertIn('Apache refuses every request to it', self.messages[1])
        self.assertIn('change the PHP version of the website in the panel', self.messages[1])
        self.assertEqual('Apache accepts its configuration again and was restarted.', self.messages[2])
        # A second upgrade finds nothing to do.
        del self.commands[:], self.messages[:]
        self.assertEqual('not needed', self.repair())
        self.assertEqual(([], []), (self.commands, self.messages))
        # Once the account exists the virtual host is what it was.
        self.assertFalse(checks.reopen_virtual_host(str(bad), getpwnam, getgrnam))
        USERS.add('Examp1234'), GROUPS.add('Examp1234')
        self.addCleanup(USERS.discard, 'Examp1234'), self.addCleanup(GROUPS.discard, 'Examp1234')
        self.assertTrue(checks.reopen_virtual_host(str(bad), getpwnam, getgrnam))
        self.assertEqual(vhost_text('Examp1234'), bad.read_text())
        self.assertEqual(0o640, stat.S_IMODE(bad.stat().st_mode))
        self.assertFalse(checks.reopen_virtual_host(str(bad), getpwnam, getgrnam))
        self.assertFalse(checks.reopen_virtual_host(str(self.sites / 'absent.test.conf'), getpwnam, getgrnam))

    def test_a_configuration_that_fails_for_another_reason_is_reported_and_not_changed(self):
        broken = self.sites / 'example.test.conf'
        broken.write_text(vhost_text('siteuser') + 'NotADirective\n')
        self.assertEqual('failed', self.repair())
        self.assertEqual(vhost_text('siteuser') + 'NotADirective\n', broken.read_text())
        self.assertEqual([], self.commands)
        self.assertEqual(1, len(self.messages))
        self.assertTrue(self.messages[0].startswith('WARNING: Apache refuses its configuration'))
        self.assertIn('Invalid command NotADirective', self.messages[0])

    def test_files_that_are_not_the_panels_are_reported_and_left(self):
        # An administrator's own virtual host and pool, as ordinary files
        # (all there is in /etc/httpd/conf.d), a link, and PHP-FPM's www.conf.
        own = self.sites / 'intranet.conf'
        own.write_text(vhost_text('gone1234', 'intranet.test'))
        linked = self.sites.parent / 'available-example.test.conf'
        linked.write_text(vhost_text('gone1234'))
        (self.sites / 'example.test.conf').symlink_to(linked)
        own_pool = self.pools / 'intranet.conf'
        own_pool.write_text(pool_text('gone1234', 'intranet.test'))
        (self.pools / 'www.conf').write_text('[www]\nuser = gone1234\ngroup = gone1234\n')
        self.assertEqual('failed', self.repair())
        self.assertEqual(vhost_text('gone1234', 'intranet.test'), own.read_text())
        self.assertTrue((self.sites / 'example.test.conf').is_symlink())
        self.assertEqual(vhost_text('gone1234'), linked.read_text())
        self.assertEqual(['intranet.conf', 'other.test.conf', 'www.conf'], self.names(self.pools))
        self.assertEqual(pool_text('gone1234', 'intranet.test'), own_pool.read_text())
        self.assertEqual([], self.commands)
        self.assertEqual(5, len(self.messages))
        for message in self.messages:
            self.assertTrue(message.startswith('WARNING: '), message)
        for message in self.messages[:4]:
            self.assertIn('It is not a file of the panel and was left as it is.', message)

    def test_a_service_that_does_not_start_is_reported(self):
        self.break_example('gone1234')
        self.failing = {self.unit, self.service}
        self.assertEqual('failed', self.repair())
        self.assertIn('WARNING: %s did not start; see "systemctl status %s".' % (self.unit, self.unit), self.messages)
        self.assertIn('WARNING: Apache did not start; see "systemctl status %s".' % self.service, self.messages)

    def test_a_service_that_is_not_enabled_is_not_started(self):
        bad = self.break_example('gone1234')
        self.disabled = {self.unit, self.service}
        self.assertEqual('repaired', self.repair())
        self.assertIn(checks.CLOSED_BEGIN, bad.read_text())
        self.assertEqual([['systemctl', 'is-enabled', '--quiet', '--', self.unit],
                          ['systemctl', 'is-enabled', '--quiet', '--', self.service]], self.commands)
        self.assertIn('%s is not enabled on this server, so it was not started.' % self.unit, self.messages)
        self.assertIn('Apache is not enabled on this server, so it was not started.', self.messages)
        self.assertNotIn('Apache accepts its configuration again and was restarted.', self.messages)

    def test_service_of_a_pool_folder(self):
        for folder, unit in (('/etc/php/8.3/fpm/pool.d/', 'php8.3-fpm'), ('/etc/php/5.6/fpm/pool.d', 'php5.6-fpm'),
                             ('/etc/opt/remi/php83/php-fpm.d/', 'php83-php-fpm'),
                             ('/opt/remi/php54/root/etc/php-fpm.d/', 'php54-php-fpm'), ('/srv/pools/', None)):
            self.assertEqual(unit, checks.fpm_unit(folder))

    def test_nothing_is_done_on_a_server_without_apache(self):
        # Also where only the binary of a removed package is left.
        with mock.patch.object(checks, 'installed_family', return_value=None):
            self.assertEqual('not installed', checks.repair(self.domains, log=self.messages.append,
                                                            succeeds=self.succeeds))
        self.assertEqual(([], []), (self.commands, self.messages))

    def test_a_pool_that_was_set_aside_is_found_again_by_its_name(self):
        pool = self.pools / ('example.test.conf' + checks.DISABLED_SUFFIX)
        for path in (pool, self.pools / ('example.test2.conf' + checks.DISABLED_SUFFIX),
                     self.pools / 'example.test.conf'):
            path.write_text('kept\n')
        pattern = str(self.pools.parent.parent) + '/*/' + self.pools.name + '/'
        with mock.patch.object(checks, 'DEB_POOLS', (pattern,)), mock.patch.object(checks, 'RPM_POOLS', (pattern,)):
            self.assertEqual([str(pool)], checks.pools_set_aside('example.test.conf', self.rpm_family))
            self.assertEqual([], checks.pools_set_aside('*.conf', self.rpm_family))


class RPMUpgradeRepairTests(UpgradeRepairTests):
    """The same on the RPM family: httpd, and the pool folders of the remi packages."""
    rpm_family = True
    service = 'httpd'
    unit = 'php83-php-fpm'
    pool_folder = ('etc', 'opt', 'remi', 'php83', 'php-fpm.d')


class UpgradeSourceTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / 'plogical' / 'upgrade.py').read_text()
        tree = ast.parse(self.text)
        self.upgrade = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Upgrade')

    def test_upgrade_runs_the_repair_with_the_panels_domains_before_its_own_apache_step(self):
        found = 0
        for function in self.upgrade.body:
            if not isinstance(function, ast.FunctionDef):
                continue
            called = {}
            for node in ast.walk(function):
                if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
                    name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr
                    called.setdefault(name, node)
            if 'repair_apache_backend' not in called:
                continue
            found += 1
            imported = [(alias.name, alias.asname) for node in ast.walk(function)
                        if isinstance(node, ast.ImportFrom) and node.module == 'ApachController.apacheConfigCheck'
                        for alias in node.names]
            self.assertIn(('repair', 'repair_apache_backend'), imported)
            call = called['repair_apache_backend']
            self.assertEqual('panel_domains', call.args[0].id)
            self.assertLess(call.lineno, called['fixApacheConfiguration'].lineno)
            self.assertLess(called['with_proxy_backends'].lineno, called['fixApacheConfiguration'].lineno)
        self.assertEqual(1, found)
        for model in ('Websites', 'ChildDomains'):
            self.assertIn("%s.objects.values_list('domain', flat=True)" % model, self.text)

    def test_upgrade_defines_the_backends_as_the_panel_does(self):
        # It used to write its own pair with the two ports exchanged.
        self.assertNotRegex(self.text, r'address\s+127\.0\.0\.1:8082')
        self.assertNotRegex(self.text, r'address\s+https://127\.0\.0\.1:8083')
        self.assertEqual(2, self.text.count('vhostConfs.proxyApacheBackend,'))
        self.assertEqual(2, self.text.count('vhostConfs.proxyApacheBackendSSL)'))


if __name__ == '__main__':
    unittest.main()
