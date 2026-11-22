"""Only an administrator can start the server-wide installation of Apache and PHP-FPM."""
import json
import unittest
from unittest import mock

from websiteFunctions.test_apache_entitlements import child_data, website_data
from websiteFunctions.test_stored_domain_name import prepared_manager


class FirstSetupRuleTests(unittest.TestCase):
    def test_refused_only_for_another_user_while_apache_is_not_installed(self):
        apache_first_setup_error = prepared_manager()[1]['apache_first_setup_error']
        self.assertIsNone(apache_first_setup_error({'admin': 1}, 0))
        self.assertIsNone(apache_first_setup_error({'admin': 1}, 1))
        self.assertIsNone(apache_first_setup_error({'admin': 0}, 1))
        for acl in ({'admin': 0}, {'admin': '1'}, {'admin': 2}, {}, None):
            with self.subTest(acl=acl):
                payload = json.loads(apache_first_setup_error(acl, 0).content)
                self.assertEqual(0, payload['status'])
                self.assertEqual(0, payload['createWebSiteStatus'])
                self.assertIn('administrator', payload['error_message'])


class FirstApacheWebsiteTests(unittest.TestCase):
    def prepare(self, admin, installed):
        self.manager, self.ns, self.services, _, _ = prepared_manager(admin=admin)
        self.services['ApacheController'].checkIfApacheInstalled.return_value = installed
        self.services['validators'].domain.return_value = True
        self.services['validators'].email.return_value = True
        self.process = self.services['ProcessUtilities']
        # Website creation reserves a real status file; none is made here.
        patcher = mock.patch('plogical.statusUtilities.create_status_file', return_value='/home/cyberpanel/1000')
        patcher.start()
        self.addCleanup(patcher.stop)

    def requests(self):
        manager = self.manager
        return (
            ('switchServer', lambda: manager().switchServer(
                7, {'domainName': 'owned.example', 'phpSelection': 'PHP 8.3', 'server': 1})),
            ('submitWebsiteCreation', lambda: manager().submitWebsiteCreation(
                7, dict(website_data(), apacheBackend=1))),
            ('submitDomainCreation', lambda: manager().submitDomainCreation(
                7, dict(child_data(), apacheBackend=1))),
        )

    def started(self):
        return [call[0][0] for call in self.process.popenExecutioner.call_args_list]

    def test_another_user_cannot_start_the_first_installation(self):
        self.prepare(admin=0, installed=0)
        for name, request in self.requests():
            with self.subTest(request=name):
                payload = json.loads(request().content)
                self.assertEqual(0, payload['status'], payload)
                self.assertIn('administrator', payload['error_message'])
                self.assertEqual([], self.started())

    def test_an_administrator_starts_it(self):
        self.prepare(admin=1, installed=0)
        for name, request in self.requests():
            with self.subTest(request=name):
                self.process.reset_mock()
                self.assertEqual(1, json.loads(request().content)['status'])
                self.assertEqual(1, len(self.started()))

    def test_every_user_may_use_apache_once_it_is_installed(self):
        self.prepare(admin=0, installed=1)
        for name, request in self.requests():
            with self.subTest(request=name):
                self.process.reset_mock()
                self.assertEqual(1, json.loads(request().content)['status'])
                self.assertEqual(1, len(self.started()))

    def test_requests_that_install_nothing_are_not_held_back(self):
        self.prepare(admin=0, installed=0)
        manager = self.manager
        for name, request in (
                ('switch back to OpenLiteSpeed', lambda: manager().switchServer(
                    7, {'domainName': 'owned.example', 'phpSelection': 'PHP 8.3', 'server': 2})),
                ('website without Apache', lambda: manager().submitWebsiteCreation(
                    7, website_data())),
                ('child domain without Apache', lambda: manager().submitDomainCreation(
                    7, child_data()))):
            with self.subTest(request=name):
                self.process.reset_mock()
                self.assertEqual(1, json.loads(request().content)['status'])
                self.assertEqual(1, len(self.started()))
        self.services['ApacheController'].checkIfApacheInstalled.assert_not_called()

    def alias_of_a_master_on_apache(self):
        # The alias request names no backend; its master's Apache
        # configuration decides that the alias is created on Apache too.
        self.services['os'].path.exists.side_effect = \
            lambda path: path == '/etc/apache2/sites-enabled/owned.example.conf'
        return self.manager().submitDomainCreation(7, dict(child_data(), domainName='alias.example', alias=1))

    def test_an_alias_of_a_master_on_apache_is_held_to_the_same_rule(self):
        self.prepare(admin=0, installed=0)
        payload = json.loads(self.alias_of_a_master_on_apache().content)
        self.assertEqual(0, payload['status'], payload)
        self.assertIn('administrator', payload['error_message'])
        self.assertEqual([], self.started())

    def test_an_alias_of_a_master_on_apache_is_created_once_apache_is_installed_or_by_an_administrator(self):
        for admin, installed in ((0, 1), (1, 0), (1, 1)):
            with self.subTest(admin=admin, installed=installed):
                self.prepare(admin=admin, installed=installed)
                payload = json.loads(self.alias_of_a_master_on_apache().content)
                self.assertEqual(1, payload['status'], payload)
                command, = self.started()
                self.assertIn(' --apache 1 ', command)

    def test_an_alias_of_a_master_without_apache_is_not_held_back(self):
        self.prepare(admin=0, installed=0)
        payload = json.loads(self.manager().submitDomainCreation(
            7, dict(child_data(), domainName='alias.example', alias=1)).content)
        self.assertEqual(1, payload['status'], payload)
        command, = self.started()
        self.assertIn(' --apache 0 ', command)
        self.services['ApacheController'].checkIfApacheInstalled.assert_not_called()

    def test_a_server_that_is_not_a_number_starts_nothing(self):
        self.prepare(admin=1, installed=1)
        for server in ('1 --tempStatusPath /etc/x', 'apache', None, [1]):
            with self.subTest(server=server):
                payload = json.loads(self.manager().switchServer(
                    7, {'domainName': 'owned.example', 'phpSelection': 'PHP 8.3', 'server': server}).content)
                self.assertEqual(0, payload['status'])
        self.assertEqual([], self.started())


class ApacheSetUpStateTests(unittest.TestCase):
    """Apache counts as set up when Apache, its control program and one PHP-FPM version of the set-up are there."""

    UBUNTU = ('/usr/sbin/apache2', '/usr/sbin/apache2ctl')

    def controller(self, distro, present):
        import ast
        from pathlib import Path
        from types import SimpleNamespace as NS
        source = Path(__file__).resolve().parents[1] / 'ApachController' / 'ApacheController.py'
        owner = [node for node in ast.parse(source.read_text()).body
                 if isinstance(node, ast.ClassDef) and node.name == 'ApacheController']
        process = mock.Mock(centos='centos', cent8='cent8')
        process.decideDistro.return_value = distro
        self.asked = []

        def exists(path):
            self.asked.append(path)
            return path in present

        namespace = dict(ProcessUtilities=process, logging=mock.Mock(), ApacheVhost=mock.Mock(),
                         os=NS(path=NS(exists=exists, isdir=exists)))
        exec(compile(ast.Module(body=owner, type_ignores=[]), str(source), 'exec'), namespace)
        return namespace['ApacheController']

    def test_any_one_fpm_version_beside_apache_counts(self):
        cases = (
            ('ubuntu', self.UBUNTU, ['/etc/php/%s/fpm/pool.d/' % version for version in (
                '5.6', '7.4', '8.0', '8.1', '8.3', '8.5')]),
            ('cent8', ('/usr/sbin/httpd',), ['/etc/opt/remi/php%s/php-fpm.d/' % version for version in (
                '56', '74', '80', '81', '83', '85')] + ['/opt/remi/php54/root/etc/php-fpm.d/']),
        )
        for distro, apache, pools in cases:
            for pool in pools:
                with self.subTest(distro=distro, pool=pool):
                    self.assertEqual(1, self.controller(distro, set(apache) | {pool}).checkIfApacheInstalled())

    def test_ubuntu_20_with_php_7_4_only_is_set_up(self):
        # Its PHP archive offers no PHP 8.0, so the set-up leaves 7.4 alone.
        present = set(self.UBUNTU) | {'/etc/php/7.4/fpm/pool.d/'}
        self.assertEqual(1, self.controller('ubuntu', present).checkIfApacheInstalled())

    def test_the_binary_without_its_control_program_is_not_set_up(self):
        # What removing the apache2 package leaves behind.
        present = {'/usr/sbin/apache2', '/etc/php/8.3/fpm/pool.d/'}
        self.assertEqual(0, self.controller('ubuntu', present).checkIfApacheInstalled())

    def test_apache_alone_or_php_fpm_alone_is_not_set_up(self):
        for distro, present in (
                ('ubuntu', set()), ('ubuntu', set(self.UBUNTU)), ('ubuntu', {'/etc/php/8.0/fpm/pool.d/'}),
                ('ubuntu', {'/etc/apache2', '/etc/php/8.0/fpm/pool.d/'}),
                ('ubuntu', set(self.UBUNTU) | {'/etc/php/8.9/fpm/pool.d/'}),
                ('ubuntu', {'/usr/sbin/httpd', '/etc/opt/remi/php80/php-fpm.d/'}),
                ('cent8', set()), ('cent8', {'/usr/sbin/httpd'}), ('cent8', {'/etc/opt/remi/php80/php-fpm.d/'}),
                ('cent8', {'/usr/sbin/apache2', '/etc/php/8.0/fpm/pool.d/'})):
            with self.subTest(distro=distro, present=sorted(present)):
                self.assertEqual(0, self.controller(distro, present).checkIfApacheInstalled())

    def test_the_gate_and_the_workers_ask_the_same_function(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        for relative_path in ('websiteFunctions/website.py', 'plogical/virtualHostUtilities.py'):
            text = (root / relative_path).read_text()
            self.assertIn('ApacheController.checkIfApacheInstalled()', text, relative_path)
            self.assertNotIn('php80Path', text, relative_path)


if __name__ == '__main__':
    unittest.main()
