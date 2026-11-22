"""A website with a certificate answers with it on the IPv4 and the IPv6 HTTPS listener.

The configuration text is the main configuration the installer ships, with
websites added the way the panel adds them. Nothing outside a temporary
directory is read or written and no service is touched.

    python3 -m unittest plogical.test_https_listener_mapping -v
"""
import ast
import difflib
import os
import re
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from plogical.domainAliasUtilities import ensure_http_vhost_mapping
from plogical.httpsListenerMapping import (
    certificate_files, ensure_https_listeners, ensure_vhost_certificate, https_listener_vhosts,
    install_vhost_certificate, plan_listener_repair, reconcile_https_listener_maps,
)

HERE = Path(__file__).resolve().parent
INSTALLED_CONFIG = (HERE.parent / 'install/litespeed/conf/httpd_config.conf').read_text()

VHOST_DEFINITION = '''virtualHost %s {
  vhRoot                  /home/$VH_NAME
  configFile              $SERVER_ROOT/conf/vhosts/$VH_NAME/vhost.conf
  allowSymbolLink         1
  enableScript            1
  restrained              1
}
'''

VHOST_CONFIG = '''docRoot                   $VH_ROOT/public_html
vhDomain                  $VH_NAME
vhAliases                 www.$VH_NAME
adminEmails               owner@example.test
enableGzip                1

index  {
  useServer               0
  indexFiles              index.php, index.html
}

rewrite  {
  enable                  1
  autoLoadHtaccess        1
}
'''

# What the panel has always written for a listener and for a website's certificate.
LISTENER = '''
listener %(name)s {
  address                 %(address)s
  secure                  1
  keyFile                  /etc/letsencrypt/live/%(domain)s/privkey.pem
  certFile                 /etc/letsencrypt/live/%(domain)s/fullchain.pem
  certChain               1
  sslProtocol             24
  enableECDHE             1
  renegProtection         1
  sslSessionCache         1
  enableSpdy              15
  enableStapling           1
  ocspRespMaxAge           86400
%(maps)s}


'''

VHSSL = '''
vhssl  {
  keyFile                 /etc/letsencrypt/live/%(domain)s/privkey.pem
  certFile                /etc/letsencrypt/live/%(domain)s/fullchain.pem
  certChain               1
  sslProtocol             24
  enableECDHE             1
  renegProtection         1
  sslSessionCache         1
  enableSpdy              15
  enableStapling           1
  ocspRespMaxAge           86400
}
'''


def map_line(vhost, names=None):
    return '  map                     %s %s\n' % (vhost, names or vhost)


def listener(name, address, domain, *maps):
    return LISTENER % {'name': name, 'address': address, 'domain': domain,
                       'maps': ''.join(maps or (map_line(domain),))}


def ipv4(domain, *maps):
    return listener('SSL', '*:443', domain, *maps)


def ipv6(domain, *maps):
    return listener('SSL IPv6', '[ANY]:443', domain, *maps)


def server(*websites):
    """The installed configuration after these websites were created, before any certificate."""
    config = INSTALLED_CONFIG
    for website in websites:
        config = ensure_http_vhost_mapping(config, website) + VHOST_DEFINITION % website
    return config


def block(config, name):
    found = re.search(r'(?ms)^listener %s ?\{\n.*?^\}' % re.escape(name), config)
    return found.group(0) if found else None


def mapped(config, name):
    """The (virtual host, names) pairs a listener maps, one per map line."""
    pairs = []
    for line in block(config, name).splitlines():
        words = line.split('#')[0].split(None, 2)
        if words[:1] == ['map']:
            pairs.append((words[1], words[2].strip()))
    return pairs


class ListenerCreationTests(unittest.TestCase):
    def test_first_certificate_creates_both_listeners_and_maps_the_website_on_each(self):
        config = server('a.test')
        updated = ensure_https_listeners(config, 'a.test')
        self.assertEqual(updated, config + ipv4('a.test') + ipv6('a.test'))
        self.assertEqual(mapped(updated, 'SSL'), [('a.test', 'a.test')])
        self.assertEqual(mapped(updated, 'SSL IPv6'), [('a.test', 'a.test')])
        self.assertEqual(ensure_https_listeners(updated, 'a.test'), updated)

    def test_cleartext_listeners_are_left_alone(self):
        config = server('a.test')
        updated = ensure_https_listeners(config, 'a.test')
        for name in ('Default', 'Default IPv6'):
            self.assertEqual(block(updated, name), block(config, name))
            self.assertIn('a.test', block(updated, name))

    def test_ipv4_listener_alone_gets_its_ipv6_twin_and_the_new_website_on_both(self):
        config = server('a.test', 'b.test') + ipv4('a.test')
        updated = ensure_https_listeners(config, 'b.test')
        self.assertEqual(mapped(updated, 'SSL'), [('a.test', 'a.test'), ('b.test', 'b.test')])
        self.assertEqual(mapped(updated, 'SSL IPv6'), [('b.test', 'b.test')])
        self.assertIn('/etc/letsencrypt/live/a.test/fullchain.pem', block(updated, 'SSL'))
        self.assertIn('/etc/letsencrypt/live/b.test/fullchain.pem', block(updated, 'SSL IPv6'))
        self.assertEqual(ensure_https_listeners(updated, 'b.test'), updated)

    def test_both_listeners_present_and_website_on_neither(self):
        config = server('a.test', 'c.test') + ipv4('a.test') + ipv6('a.test')
        updated = ensure_https_listeners(config, 'c.test')
        for name in ('SSL', 'SSL IPv6'):
            self.assertEqual(mapped(updated, name), [('a.test', 'a.test'), ('c.test', 'c.test')])
        self.assertEqual(updated.count('listener '), config.count('listener '))

    def test_website_on_one_listener_only_is_added_to_the_other_once(self):
        for present, absent in (('SSL', 'SSL IPv6'), ('SSL IPv6', 'SSL')):
            with self.subTest(present=present):
                here = (map_line('a.test'), map_line('b.test'))
                there = (map_line('a.test'),)
                config = server('a.test', 'b.test') + (
                    ipv4('a.test', *(here if present == 'SSL' else there))
                    + ipv6('a.test', *(here if present == 'SSL IPv6' else there)))
                self.assertNotIn(('b.test', 'b.test'), mapped(config, absent))
                updated = ensure_https_listeners(config, 'b.test')
                for name in ('SSL', 'SSL IPv6'):
                    self.assertEqual(mapped(updated, name), [('a.test', 'a.test'), ('b.test', 'b.test')])
                self.assertEqual(ensure_https_listeners(updated, 'b.test'), updated)

    def test_website_on_both_listeners_changes_nothing(self):
        maps = (map_line('a.test'), map_line('b.test', 'b.test, alias.test'))
        config = server('a.test', 'b.test') + ipv4('a.test', *maps) + ipv6('a.test', *maps)
        self.assertEqual(ensure_https_listeners(config, 'b.test'), config)

    def test_renamed_listeners_count_and_no_duplicate_is_created(self):
        config = server('a.test') + (ipv4('a.test') + ipv6('a.test')).replace(
            'listener SSL IPv6 {', 'listener IPv6TLS {').replace('listener SSL {', 'listener HTTPS {')
        updated = ensure_https_listeners(config, 'a.test')
        self.assertEqual(updated, config)

    def test_extra_listener_of_an_administrator_also_serves_the_new_website(self):
        custom = listener('Shop8443', '*:8443', 'shop.test')
        config = server('a.test', 'shop.test', 'c.test') + ipv4('a.test') + ipv6('a.test') + custom
        updated = ensure_https_listeners(config, 'c.test')
        self.assertEqual(mapped(updated, 'Shop8443'), [('shop.test', 'shop.test'), ('c.test', 'c.test')])
        self.assertEqual(mapped(updated, 'SSL'), [('a.test', 'a.test'), ('c.test', 'c.test')])
        self.assertEqual(mapped(updated, 'SSL IPv6'), [('a.test', 'a.test'), ('c.test', 'c.test')])


class ReconciliationTests(unittest.TestCase):
    def one_family_each(self):
        """Two certificates issued by a release that gave each a listener of its own."""
        return server('a.test', 'b.test') + ipv4('a.test') + ipv6('b.test')

    def test_websites_mapped_on_one_family_are_completed_on_the_other(self):
        config = self.one_family_each()
        updated, completed = reconcile_https_listener_maps(config, {'a.test', 'b.test'})
        self.assertEqual(mapped(updated, 'SSL'), [('a.test', 'a.test'), ('b.test', 'b.test')])
        self.assertEqual(mapped(updated, 'SSL IPv6'), [('b.test', 'b.test'), ('a.test', 'a.test')])
        self.assertEqual(completed, [('SSL', 'b.test'), ('SSL IPv6', 'a.test')])
        self.assertEqual(reconcile_https_listener_maps(updated, {'a.test', 'b.test'}), (updated, []))

    def test_only_the_map_lines_change(self):
        config = self.one_family_each()
        updated, _ = reconcile_https_listener_maps(config, {'a.test', 'b.test'})
        difference = [line for line in difflib.ndiff(config.splitlines(), updated.splitlines())
                      if line[:1] in '+-?']
        self.assertEqual(difference, ['+ ' + map_line('b.test').rstrip('\n'), '+ ' + map_line('a.test').rstrip('\n')])

    def test_complete_maps_are_not_rewritten(self):
        maps = (map_line('a.test'), '  map\tb.test\tb.test, alias.test # keep\n')
        config = server('a.test', 'b.test') + ipv4('a.test', *maps) + ipv6('a.test', *maps)
        self.assertEqual(reconcile_https_listener_maps(config, {'a.test', 'b.test'}), (config, []))

    def test_website_without_its_own_certificate_is_not_mapped_anywhere_new(self):
        config = self.one_family_each()
        updated, completed = reconcile_https_listener_maps(config, {'b.test'})
        self.assertEqual(mapped(updated, 'SSL IPv6'), [('b.test', 'b.test')])
        self.assertEqual(mapped(updated, 'SSL'), [('a.test', 'a.test'), ('b.test', 'b.test')])
        self.assertEqual(completed, [('SSL', 'b.test')])

    def test_map_of_a_deleted_website_is_not_copied(self):
        config = server('a.test') + ipv4('a.test', map_line('a.test'), map_line('gone.test')) + ipv6('a.test')
        updated, completed = reconcile_https_listener_maps(config, {'a.test', 'gone.test'})
        self.assertEqual((updated, completed), (config, []))

    def test_aliases_follow_their_website(self):
        config = server('a.test', 'b.test') + (
            ipv4('a.test', map_line('a.test', 'a.test, alias.test'), map_line('b.test'))
            + ipv6('b.test', map_line('b.test', 'b.test, other.test'), map_line('a.test')))
        updated, completed = reconcile_https_listener_maps(config, {'a.test', 'b.test'})
        self.assertEqual(mapped(updated, 'SSL'),
                         [('a.test', 'a.test, alias.test'), ('b.test', 'b.test, other.test')])
        self.assertEqual(mapped(updated, 'SSL IPv6'),
                         [('b.test', 'b.test, other.test'), ('a.test', 'a.test, alias.test')])
        self.assertEqual(completed, [('SSL', 'b.test'), ('SSL IPv6', 'a.test')])

    def test_name_another_website_holds_on_that_listener_stays_with_it(self):
        config = server('a.test', 'b.test') + (
            ipv4('a.test', map_line('a.test', 'a.test, shared.test'))
            + ipv6('b.test', map_line('b.test', 'b.test, shared.test')))
        updated, _ = reconcile_https_listener_maps(config, {'a.test', 'b.test'})
        self.assertEqual(mapped(updated, 'SSL'), [('a.test', 'a.test, shared.test'), ('b.test', 'b.test')])
        self.assertEqual(mapped(updated, 'SSL IPv6'), [('b.test', 'b.test, shared.test'), ('a.test', 'a.test')])

    def test_catch_all_map_is_not_spread(self):
        config = server('a.test', 'b.test') + (
            ipv4('a.test', map_line('a.test', 'a.test, *')) + ipv6('b.test'))
        updated, _ = reconcile_https_listener_maps(config, {'a.test', 'b.test'})
        self.assertEqual(mapped(updated, 'SSL IPv6'), [('b.test', 'b.test'), ('a.test', 'a.test')])

    def test_repeated_map_lines_of_a_website_become_one(self):
        config = server('a.test', 'b.test') + (
            ipv4('a.test', map_line('a.test'), map_line('b.test'))
            + ipv6('b.test', map_line('b.test'), map_line('b.test', 'b.test, alias.test'), map_line('a.test'),
                   '  map                     b.test b.test  # second copy\n'))
        updated, completed = reconcile_https_listener_maps(config, {'a.test', 'b.test'})
        self.assertEqual(mapped(updated, 'SSL IPv6'), [('b.test', 'b.test, alias.test'), ('a.test', 'a.test')])
        self.assertEqual(mapped(updated, 'SSL'), [('a.test', 'a.test'), ('b.test', 'b.test, alias.test')])
        self.assertEqual(completed, [('SSL', 'b.test')])
        self.assertEqual(reconcile_https_listener_maps(updated, {'a.test', 'b.test'}), (updated, []))

    def test_comment_on_a_completed_line_is_kept(self):
        config = server('a.test') + (
            ipv4('a.test', '  map                     a.test a.test # main site\n')
            + ipv6('a.test', map_line('a.test', 'a.test, alias.test')))
        updated, _ = reconcile_https_listener_maps(config, {'a.test'})
        self.assertIn('  map                     a.test a.test, alias.test  # main site\n', block(updated, 'SSL'))

    def test_listeners_of_an_administrator_are_neither_changed_nor_copied_from(self):
        custom = (listener('Shop8443', '*:8443', 'shop.test')
                  + listener('Dedicated', '203.0.113.9:443', 'vip.test')
                  + listener('Dedicated6', '[2001:db8::9]:443', 'vip.test'))
        config = server('a.test', 'b.test', 'shop.test', 'vip.test') + ipv4('a.test') + custom + ipv6('b.test')
        everyone = {'a.test', 'b.test', 'shop.test', 'vip.test'}
        updated, completed = reconcile_https_listener_maps(config, everyone)
        for name in ('Shop8443', 'Dedicated', 'Dedicated6', 'Default', 'Default IPv6'):
            self.assertEqual(block(updated, name), block(config, name))
        self.assertEqual(mapped(updated, 'SSL'), [('a.test', 'a.test'), ('b.test', 'b.test')])
        self.assertEqual(mapped(updated, 'SSL IPv6'), [('b.test', 'b.test'), ('a.test', 'a.test')])
        self.assertEqual(https_listener_vhosts(config), ['a.test', 'b.test'])

    def test_other_spellings_of_the_wildcard_address_are_standard_listeners(self):
        config = server('a.test', 'b.test') + (
            ipv4('a.test').replace('*:443', '0.0.0.0:443').replace('listener SSL {', 'listener SSL{')
            + ipv6('b.test').replace('[ANY]:443', '[::]:443'))
        updated, completed = reconcile_https_listener_maps(config, {'a.test', 'b.test'})
        self.assertEqual(completed, [('SSL', 'b.test'), ('SSL IPv6', 'a.test')])
        for name in ('SSL', 'SSL IPv6'):
            self.assertEqual(sorted(mapped(updated, name)), [('a.test', 'a.test'), ('b.test', 'b.test')])

    def test_single_listener_or_none_needs_nothing(self):
        for config in (server('a.test'), server('a.test') + ipv4('a.test')):
            self.assertEqual(reconcile_https_listener_maps(config, {'a.test'}), (config, []))


class VhostCertificateTests(unittest.TestCase):
    def test_block_is_added_once(self):
        updated = ensure_vhost_certificate(VHOST_CONFIG, 'a.test')
        self.assertEqual(updated, VHOST_CONFIG + VHSSL % {'domain': 'a.test'})
        self.assertEqual(ensure_vhost_certificate(updated, 'a.test'), updated)
        self.assertEqual(certificate_files(updated), ('/etc/letsencrypt/live/a.test/privkey.pem',
                                                      '/etc/letsencrypt/live/a.test/fullchain.pem'))

    def test_existing_block_is_kept_whatever_it_names(self):
        own = VHOST_CONFIG + 'vhssl {\n  keyFile /root/own.key\n  certFile /root/own.crt\n}\n'
        self.assertEqual(ensure_vhost_certificate(own, 'a.test'), own)
        self.assertEqual(certificate_files(own), ('/root/own.key', '/root/own.crt'))
        one_line = VHOST_CONFIG + 'vhssl { keyFile /root/own.key certFile /root/own.crt }\n'
        self.assertEqual(ensure_vhost_certificate(one_line, 'a.test'), one_line)
        self.assertEqual(certificate_files(one_line), ('', ''))

    def test_no_block(self):
        self.assertIsNone(certificate_files(VHOST_CONFIG))


class Server(object):
    """An OpenLiteSpeed configuration tree and a certificate store in a temporary directory."""

    def __init__(self, directory):
        self.root = os.path.join(directory, 'lsws')
        self.certificates = os.path.join(directory, 'live')
        os.makedirs(os.path.join(self.root, 'conf/vhosts'))
        os.makedirs(self.certificates)
        self.main = os.path.join(self.root, 'conf/httpd_config.conf')
        Path(self.main).write_text(INSTALLED_CONFIG)
        os.chmod(self.main, 0o640)

    def vhost(self, website):
        return os.path.join(self.root, 'conf/vhosts', website, 'vhost.conf')

    def add(self, website, certificate=True, config=VHOST_CONFIG):
        os.makedirs(os.path.dirname(self.vhost(website)))
        Path(self.vhost(website)).write_text(config)
        os.chmod(self.vhost(website), 0o600)
        Path(self.main).write_text(server_text(Path(self.main).read_text(), website))
        if certificate:
            os.makedirs(os.path.join(self.certificates, website))
            for name in ('privkey.pem', 'fullchain.pem'):
                Path(self.certificates, website, name).write_text('fixture\n')

    def append(self, text):
        with open(self.main, 'a') as target:
            target.write(text)

    def listener(self, name, address, website, *maps):
        self.append(listener(name, address, website, *maps).replace('/etc/letsencrypt/live', self.certificates))

    def config(self):
        return Path(self.main).read_text()

    def vhssl(self, website):
        return VHSSL.replace('/etc/letsencrypt/live', self.certificates) % {'domain': website}

    def install(self, website):
        install_vhost_certificate(website, self.root, self.certificates)

    def plan(self):
        return plan_listener_repair(self.root, self.certificates)

    def files(self):
        return {str(path): path.read_text() for path in Path(self.root).rglob('*') if path.is_file()}


def server_text(config, website):
    return ensure_http_vhost_mapping(config, website) + VHOST_DEFINITION % website


class InstalledCertificateTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.server = Server(directory.name)

    def assert_served(self, *websites):
        config = self.server.config()
        for name in ('SSL', 'SSL IPv6'):
            self.assertEqual(sorted(mapped(config, name)), sorted((site, site) for site in websites))
        for website in websites:
            self.assertEqual(Path(self.server.vhost(website)).read_text().count('vhssl'), 1)
            self.assertEqual(certificate_files(Path(self.server.vhost(website)).read_text()),
                             (os.path.join(self.server.certificates, website, 'privkey.pem'),
                              os.path.join(self.server.certificates, website, 'fullchain.pem')))

    def test_websites_get_certificates_one_after_another(self):
        for website in ('a.test', 'b.test', 'c.test'):
            self.server.add(website)
        self.server.install('a.test')
        self.assert_served('a.test')
        self.server.install('b.test')
        self.assert_served('a.test', 'b.test')
        self.server.install('c.test')
        self.assert_served('a.test', 'b.test', 'c.test')
        before = self.server.files()
        for website in ('b.test', 'a.test', 'c.test'):
            self.server.install(website)
        self.assertEqual(self.server.files(), before)
        self.assertEqual(self.server.config().count('listener SSL'), 2)

    def test_first_website_file_holds_exactly_what_the_panel_writes(self):
        self.server.add('a.test')
        self.server.install('a.test')
        self.assertEqual(Path(self.server.vhost('a.test')).read_text(), VHOST_CONFIG + self.server.vhssl('a.test'))
        self.assertTrue(self.server.config().endswith(
            (ipv4('a.test') + ipv6('a.test')).replace('/etc/letsencrypt/live', self.server.certificates)))

    def test_owner_and_mode_of_the_files_are_kept(self):
        self.server.add('a.test')
        self.server.install('a.test')
        self.assertEqual(stat.S_IMODE(os.stat(self.server.main).st_mode), 0o640)
        self.assertEqual(stat.S_IMODE(os.stat(self.server.vhost('a.test')).st_mode), 0o600)
        leftovers = [path.name for path in Path(self.server.root).rglob('.config-*')]
        self.assertEqual(leftovers, [])

    def test_second_certificate_completes_a_server_that_has_the_ipv4_listener_only(self):
        # The first website was served with the certificate of the IPv4 listener and has no vhssl block.
        for website in ('a.test', 'b.test'):
            self.server.add(website)
        self.server.listener('SSL', '*:443', 'a.test')
        self.server.install('b.test')
        self.assert_served('a.test', 'b.test')
        self.assertIn(os.path.join(self.server.certificates, 'b.test', 'fullchain.pem'),
                      block(self.server.config(), 'SSL IPv6'))

    def test_renewal_completes_websites_that_are_on_one_family_each(self):
        for website in ('a.test', 'b.test', 'c.test'):
            self.server.add(website)
        self.server.listener('SSL', '*:443', 'a.test')
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test')
        self.server.install('c.test')
        self.assert_served('a.test', 'b.test', 'c.test')

    def test_website_without_configuration_is_refused_before_anything_is_written(self):
        self.server.add('a.test')
        before = self.server.files()
        with self.assertRaisesRegex(ValueError, 'Website configuration not found'):
            self.server.install('missing.test')
        self.assertEqual(self.server.files(), before)

    def test_failed_listener_update_leaves_the_main_configuration_as_it_was(self):
        self.server.add('a.test')
        before = self.server.config()
        with mock.patch('plogical.httpsListenerMapping.ensure_https_listeners', side_effect=RuntimeError('fixture')):
            with self.assertRaises(RuntimeError):
                self.server.install('a.test')
        self.assertEqual(self.server.config(), before)


class UpgradePlanTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.server = Server(directory.name)

    def apply(self, changes):
        for path, (current, repaired) in changes.items():
            self.assertEqual(Path(path).read_text(), current)
            Path(path).write_text(repaired)

    def one_family_each(self):
        for website in ('a.test', 'b.test', 'c.test'):
            self.server.add(website, config=VHOST_CONFIG + (self.server.vhssl(website) if website == 'c.test' else ''))
        both = (map_line('c.test'),)
        self.server.listener('SSL', '*:443', 'a.test', map_line('a.test'), *both)
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test', map_line('b.test'), *both)

    def test_plan_names_the_files_and_writes_nothing(self):
        self.one_family_each()
        before = self.server.files()
        changes, completed = self.server.plan()
        self.assertEqual(self.server.files(), before)
        self.assertEqual(list(changes), [self.server.vhost('a.test'), self.server.vhost('b.test'), self.server.main])
        self.assertEqual(completed, [('SSL', 'b.test'), ('SSL IPv6', 'a.test')])
        for path, (current, repaired) in changes.items():
            self.assertEqual(current, before[path])
        self.assertEqual(changes[self.server.vhost('a.test')][1], VHOST_CONFIG + self.server.vhssl('a.test'))

    def test_applied_plan_serves_every_website_on_both_families_and_is_final(self):
        self.one_family_each()
        self.apply(self.server.plan()[0])
        config = self.server.config()
        self.assertEqual(sorted(mapped(config, 'SSL')), sorted(mapped(config, 'SSL IPv6')))
        self.assertEqual(sorted(mapped(config, 'SSL')), [(site, site) for site in ('a.test', 'b.test', 'c.test')])
        for website in ('a.test', 'b.test', 'c.test'):
            self.assertEqual(Path(self.server.vhost(website)).read_text().count('vhssl'), 1)
        self.assertEqual(self.server.plan(), ({}, []))

    def test_website_without_certificate_files_is_left_on_its_one_listener(self):
        self.server.add('a.test')
        self.server.add('plain.test', certificate=False)
        self.server.add('broken.test', certificate=False, config=VHOST_CONFIG + self.server.vhssl('broken.test'))
        self.server.listener('SSL', '*:443', 'a.test', map_line('a.test'), map_line('plain.test'),
                             map_line('broken.test'))
        self.server.listener('SSL IPv6', '[ANY]:443', 'a.test')
        before = self.server.files()
        changes, completed = self.server.plan()
        self.assertEqual(list(changes), [self.server.vhost('a.test')])
        self.assertEqual(completed, [])
        self.apply(changes)
        self.assertEqual(mapped(self.server.config(), 'SSL IPv6'), [('a.test', 'a.test')])
        for website in ('plain.test', 'broken.test'):
            self.assertEqual(Path(self.server.vhost(website)).read_text(), before[self.server.vhost(website)])

    def test_single_https_website_gets_its_own_certificate_block(self):
        self.server.add('a.test')
        self.server.listener('SSL', '*:443', 'a.test')
        changes, completed = self.server.plan()
        self.assertEqual(list(changes), [self.server.vhost('a.test')])
        self.assertEqual(completed, [])

    def test_server_without_https_needs_nothing(self):
        self.server.add('a.test')
        self.assertEqual(self.server.plan(), ({}, []))

    def test_apache_backend_website_keeps_its_block(self):
        proxy = VHOST_CONFIG + self.server.vhssl('a.test')
        self.server.add('a.test', config=proxy)
        self.server.add('b.test')
        self.server.listener('SSL', '*:443', 'a.test')
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test')
        changes, completed = self.server.plan()
        self.assertNotIn(self.server.vhost('a.test'), changes)
        self.assertEqual(completed, [('SSL', 'b.test'), ('SSL IPv6', 'a.test')])

    def test_linked_website_configuration_and_unsafe_names_are_skipped(self):
        self.server.add('a.test')
        self.server.add('b.test')
        real = self.server.vhost('b.test') + '.real'
        os.rename(self.server.vhost('b.test'), real)
        os.symlink(real, self.server.vhost('b.test'))
        self.server.listener('SSL', '*:443', 'a.test', map_line('a.test'), map_line('../a.test'))
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test')
        changes, completed = self.server.plan()
        self.assertEqual(list(changes), [self.server.vhost('a.test'), self.server.main])
        self.assertEqual(completed, [('SSL IPv6', 'a.test')])

    def test_custom_listener_is_not_part_of_the_plan(self):
        for website in ('a.test', 'b.test', 'shop.test'):
            self.server.add(website)
        self.server.listener('SSL', '*:443', 'a.test')
        self.server.listener('Shop8443', '*:8443', 'shop.test')
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test')
        custom = block(self.server.config(), 'Shop8443')
        changes, _ = self.server.plan()
        self.assertNotIn(self.server.vhost('shop.test'), changes)
        self.apply(changes)
        self.assertEqual(block(self.server.config(), 'Shop8443'), custom)
        self.assertEqual(sorted(mapped(self.server.config(), 'SSL')), [('a.test', 'a.test'), ('b.test', 'b.test')])


def method(filename, class_name, name):
    tree = ast.parse(Path(__file__).with_name(filename).read_text())
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    node = next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == name)
    node.decorator_list = []
    return node


def compiled(node, namespace):
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), '<panel>', 'exec'), namespace)
    return namespace[node.name]


class CertificateInstallEntryTests(unittest.TestCase):
    """Both certificate installers of the panel hand OpenLiteSpeed to the same routine."""

    def run_installer(self, filename, server='ols', outcome=None):
        install = mock.Mock(side_effect=outcome)
        panel = SimpleNamespace(Server_root='/srv/lsws', redisConf='/nonexistent/dvhost_redis.conf',
                                isStagingCertificate=lambda certificate: False)
        namespace = {
            'install_vhost_certificate': install, 'sslUtilities': panel, 'logging': mock.MagicMock(),
            'ProcessUtilities': SimpleNamespace(decideServer=lambda: server, OLS='ols'),
            'Websites': mock.MagicMock(), 'ChildDomains': mock.MagicMock(), 'ACLManager': mock.MagicMock(),
            'os': os, 'open': mock.mock_open(read_data='<VirtualHost *:443>\n'),
        }
        installer = compiled(method(filename, 'sslUtilities', 'installSSLForDomain'), namespace)
        with mock.patch('OpenSSL.crypto.load_certificate'):
            return installer('a.test'), install

    def test_openlitespeed_uses_the_shared_routine(self):
        for filename in ('sslUtilities.py', 'sslv2.py'):
            with self.subTest(filename=filename):
                result, install = self.run_installer(filename)
                self.assertEqual(result, 1)
                install.assert_called_once_with('a.test', '/srv/lsws')

    def test_failure_is_reported_as_not_installed(self):
        for filename in ('sslUtilities.py', 'sslv2.py'):
            with self.subTest(filename=filename):
                result, _ = self.run_installer(filename, outcome=ValueError('Website configuration not found'))
                self.assertEqual(result, 0)

    def test_litespeed_enterprise_has_no_listener_maps_to_keep(self):
        for filename in ('sslUtilities.py', 'sslv2.py'):
            with self.subTest(filename=filename):
                result, install = self.run_installer(filename, server='lsws')
                self.assertEqual(result, 1)
                install.assert_not_called()

    def test_no_installer_keeps_listener_writing_of_its_own(self):
        for filename in ('sslUtilities.py', 'sslv2.py'):
            source = ast.get_source_segment(Path(__file__).with_name(filename).read_text(),
                                            method(filename, 'sslUtilities', 'installSSLForDomain'))
            self.assertNotIn('httpd_config.conf', source)


class UpgradeStepTests(unittest.TestCase):
    def step(self, installed=True):
        upgrade = mock.Mock()
        apply = mock.Mock()
        namespace = {'os': SimpleNamespace(path=SimpleNamespace(exists=lambda path: installed)),
                     'Upgrade': upgrade, 'apply_ols_config_changes': apply}
        return compiled(method('upgrade.py', 'Upgrade', 'reconcileHTTPSListenerMaps'), namespace), upgrade, apply

    def test_planned_changes_go_through_the_validated_configuration_change(self):
        step, upgrade, apply = self.step()
        changes = {'/usr/local/lsws/conf/httpd_config.conf': ('before', 'after')}
        with mock.patch('plogical.httpsListenerMapping.plan_listener_repair',
                        return_value=(changes, [('SSL', 'b.test')])) as plan:
            step()
        plan.assert_called_once_with()
        apply.assert_called_once_with(changes)
        message = upgrade.stdOut.call_args[0][0]
        self.assertIn('1 mapping(s) completed, 1 file(s) updated', message)
        self.assertIn('SSL: b.test', message)

    def test_refused_change_is_reported_and_does_not_stop_the_upgrade(self):
        step, upgrade, apply = self.step()
        apply.side_effect = RuntimeError('OpenLiteSpeed configuration migration failed: fixture')
        with mock.patch('plogical.httpsListenerMapping.plan_listener_repair', return_value=({'x': ('a', 'b')}, [])):
            step()
        message = upgrade.stdOut.call_args[0][0]
        self.assertTrue(message.startswith('WARNING: HTTPS listener maps were not reconciled'))
        self.assertIn('fixture', message)

    def test_server_without_openlitespeed_is_skipped(self):
        step, upgrade, apply = self.step(installed=False)
        with mock.patch('plogical.httpsListenerMapping.plan_listener_repair') as plan:
            step()
        plan.assert_not_called()
        apply.assert_not_called()

    def test_upgrade_runs_the_step(self):
        calls = [(node.func.attr, node.lineno) for node in ast.walk(method('upgrade.py', 'Upgrade', 'upgrade'))
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                 and isinstance(node.func.value, ast.Name) and node.func.value.id == 'Upgrade']
        lines = dict(calls)
        self.assertEqual([name for name, _ in calls].count('reconcileHTTPSListenerMaps'), 1)
        # The step is part of the new release, so it can only run once that source is in place.
        self.assertLess(lines['downloadAndUpgrade'], lines['reconcileHTTPSListenerMaps'])


if __name__ == '__main__':
    unittest.main()
