"""Tuning a website's PHP-FPM pool: the pool file it writes and the service it restarts."""
import json
from types import SimpleNamespace
import unittest

from managePHP import phpConfig
from plogical.vhostConfs import vhostConfs
from websiteFunctions.test_stored_domain_name import Rows
from websiteFunctions.test_wordpress_entitlements import Response, load_wordpress_manager

UBUNTU_POOL = '/etc/php/8.1/fpm/pool.d/owned.example.conf'
REMI_POOL = '/etc/opt/remi/php81/php-fpm.d/owned.example.conf'
OLD_REMI_POOL = '/opt/remi/php54/root/etc/php-fpm.d/owned.example.conf'


def tuning_data(pool, **changes):
    data = dict(domainName='owned.example', pmMaxChildren=20, pmStartServers=2, pmMinSpareServers=2,
                pmMaxSpareServers=6, phpPath=pool)
    data.update(changes)
    return data


class PoolTuning(unittest.TestCase):
    """The real WebsiteManager.tuneSettings with the database, files and the privileged helper replaced."""

    def setUp(self):
        self.manager, self.ns, self.services = load_wordpress_manager()
        self.ns['vhostConfs'] = vhostConfs
        acl = self.services['ACLManager']
        acl.CheckForPremFeature.return_value = 1
        acl.loadedACL.return_value = {'admin': 0}
        acl.checkOwnership.return_value = 1
        acl.loadErrorJson.return_value = Response(json.dumps({'status': 0, 'error_message': 'ACL denied'}))
        self.services['Administrator'].objects.get.return_value = SimpleNamespace(pk=7, userName='owner')
        self.site = SimpleNamespace(domain='owned.example', externalApp='owned1234')
        self.ns['Websites'] = SimpleNamespace(objects=Rows(self.site))
        self.ns['ChildDomains'] = SimpleNamespace(objects=Rows())
        paths = self.services['os'].path
        paths.realpath.side_effect = lambda path: path
        paths.basename.side_effect = lambda path: path.rsplit('/', 1)[-1]
        paths.exists.return_value = False
        self.process = self.services['ProcessUtilities']
        self.process.executioner.return_value = 1
        self.process.outputExecutioner.return_value = ''
        self.distro('ubuntu')
        self.services['ApacheVhost'].fpmServiceCommand.side_effect = self.service_command


    def distro(self, name):
        self.rpm_family = name != 'ubuntu'
        self.process.decideDistro.return_value = self.process.centos if self.rpm_family else name

    def service_command(self, action, selection):
        return ['systemctl', action, '--', phpConfig.fpm_service_for_selection(selection, self.rpm_family)]

    def tune(self, data):
        self.process.reset_mock()
        self.services['open'].reset_mock()
        return json.loads(self.manager().tuneSettings(7, data).content)

    def helper_commands(self):
        return [call[0][0] for call in self.process.executioner.call_args_list]

    def written(self):
        return ''.join(self.services['open'].return_value.writelines.call_args[0][0])


class PoolServiceRestartTests(PoolTuning):
    def assert_restarts(self, pool, unit):
        result = self.tune(tuning_data(pool))
        self.assertEqual({'status': 1}, result)
        self.assertEqual(['sudo mv /home/cyberpanel/1000 ' + pool,
                          'systemctl stop -- ' + unit, 'systemctl restart -- ' + unit], self.helper_commands())
        # The web process cannot control services; nothing is attempted from it.
        self.process.normalExecutioner.assert_not_called()

    def test_ubuntu_pool_restarts_the_service_of_its_own_version(self):
        self.assert_restarts(UBUNTU_POOL, 'php8.1-fpm')

    def test_remi_pool_restarts_the_service_of_its_own_version(self):
        self.distro('cent8')
        self.assert_restarts(REMI_POOL, 'php81-php-fpm')

    def test_old_remi_layout_restarts_the_service_of_its_own_version(self):
        self.distro('centos')
        self.assert_restarts(OLD_REMI_POOL, 'php54-php-fpm')


class PoolNameOnTuningTests(PoolTuning):
    legacy = '[%s]\nlisten = /var/run/php/owned.example.sock\nuser = owned1234\n'

    def test_a_pool_keeps_the_name_it_already_has(self):
        # Names given by earlier versions, and the name new pools get.
        for name in ('owned1234', 'ownedex', phpConfig.fpm_pool_name('owned1234', 'owned.example')):
            with self.subTest(name=name):
                self.process.outputExecutioner.return_value = self.legacy % name
                self.assertEqual({'status': 1}, self.tune(tuning_data(UBUNTU_POOL)))
                self.process.outputExecutioner.assert_called_once_with('sudo cat ' + UBUNTU_POOL)
                self.assertEqual('[%s]' % name, self.written().splitlines()[0])

    def test_a_pool_file_without_a_usable_name_gets_a_unique_one(self):
        unique = '[%s]' % phpConfig.fpm_pool_name('owned1234', 'owned.example')
        for content in ('', 'cat: %s: No such file or directory' % UBUNTU_POOL, '[global]\nx = 1\n', '[www]\n',
                        '[a b]\n', 'pm = dynamic\n'):
            with self.subTest(content=content):
                self.process.outputExecutioner.return_value = content
                self.assertEqual({'status': 1}, self.tune(tuning_data(UBUNTU_POOL)))
                self.assertEqual(unique, self.written().splitlines()[0])

    def test_tuned_values_and_the_site_identity_are_written_as_before(self):
        self.process.outputExecutioner.return_value = self.legacy % 'owned1234'
        self.tune(tuning_data(UBUNTU_POOL, pmMaxChildren='40', pmStartServers='3', pmMinSpareServers='3',
                              pmMaxSpareServers='9'))
        self.assertEqual(
            '[owned1234]\nlisten = /var/run/php/owned.example.sock\nlisten.owner = nobody\n'
            'listen.group = nogroup\nlisten.mode = 0660\nuser = owned1234\ngroup = owned1234\npm = dynamic\n'
            'pm.max_children = 40\npm.start_servers = 3\npm.min_spare_servers = 3\npm.max_spare_servers = 9\n',
            self.written())


class PoolOfTheStoredWebsiteTests(PoolTuning):
    def test_another_spelling_of_the_domain_cannot_name_a_second_pool_file(self):
        other = UBUNTU_POOL.replace('owned.example', 'OWNED.EXAMPLE')
        result = self.tune(tuning_data(other, domainName='OWNED.EXAMPLE'))
        self.assertEqual(0, result['status'])
        self.assertEqual([], self.helper_commands())
        # The stored name's own pool file is still tuned under that spelling.
        self.assertEqual({'status': 1}, self.tune(tuning_data(UBUNTU_POOL, domainName='OWNED.EXAMPLE')))
        self.assertIn('listen = /var/run/php/owned.example.sock\n', self.written())


if __name__ == '__main__':
    unittest.main()
