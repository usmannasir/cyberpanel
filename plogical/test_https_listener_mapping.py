"""A website with a certificate answers with it on the IPv4 and the IPv6 HTTPS listener.

The configuration text is the main configuration the installer ships, with
websites added the way the panel adds them. Nothing outside a temporary
directory is read or written and no service is touched.

    python3 -m unittest plogical.test_https_listener_mapping -v
"""
import ast
import difflib
import functools
import locale
import os
import re
import shlex
import stat
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

import plogical.httpsListenerMapping as subject
from plogical.domainAliasUtilities import ensure_http_vhost_mapping
from plogical.httpListenerMapping import rewrite_config
from plogical.httpsListenerMapping import (
    ChangeRefused, certificate_files, certificate_serves, classify_listener_vhosts, ensure_https_listeners,
    ensure_vhost_certificate, holds_original, https_listener_vhosts, install_vhost_certificate,
    reconcile_https_listener_maps, repair_https_listeners,
)


# The panel's log file is outside the temporary directories: every test passes its own report.
PANEL_LOG = mock.patch.object(subject, '_log', side_effect=AssertionError('the panel log was used'))


def setUpModule():
    PANEL_LOG.start()


def tearDownModule():
    PANEL_LOG.stop()

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


class LineEndingTests(unittest.TestCase):
    """A configuration saved with Windows line endings keeps them, also in what is added."""

    def crlf(self, text):
        return text.replace('\n', '\r\n')

    def test_listeners_and_block_are_added_in_the_line_endings_of_the_file(self):
        config = self.crlf(server('a.test'))
        updated = ensure_https_listeners(config, 'a.test')
        self.assertTrue(updated.startswith(config))
        self.assertEqual(updated, config + self.crlf(ipv4('a.test') + ipv6('a.test')))
        vhost = self.crlf(VHOST_CONFIG)
        self.assertEqual(ensure_vhost_certificate(vhost, 'a.test'), vhost + self.crlf(VHSSL % {'domain': 'a.test'}))

    def test_reconciliation_reads_and_writes_windows_line_endings(self):
        config = self.crlf(server('a.test', 'b.test') + (
            ipv4('a.test', '  map                     a.test a.test # main site\n')
            + ipv6('b.test', map_line('b.test'), map_line('a.test', 'a.test, alias.test'))))
        updated, completed = reconcile_https_listener_maps(config, {'a.test', 'b.test'})
        self.assertEqual(completed, [('SSL', 'a.test'), ('SSL', 'b.test')])
        self.assertNotIn('\n', updated.replace('\r\n', ''))
        self.assertIn('  map                     a.test a.test, alias.test  # main site\r\n', updated)
        self.assertEqual(updated.replace('\r\n', '\n'), reconcile_https_listener_maps(
            config.replace('\r\n', '\n'), {'a.test', 'b.test'})[0])


KEY = ec.generate_private_key(ec.SECP256R1(), default_backend())
KEY_PEM = KEY.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                            serialization.NoEncryption())


def certificate(common_name, alternative=(), starts=-1, ends=30, issuer=None):
    """A certificate in PEM; it names itself as issuer unless another issuer is given."""
    def name(value):
        return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, value)])
    now = datetime.now(timezone.utc)
    builder = (x509.CertificateBuilder().subject_name(name(common_name)).issuer_name(name(issuer or common_name))
               .public_key(KEY.public_key()).serial_number(x509.random_serial_number())
               .not_valid_before(now + timedelta(days=starts)).not_valid_after(now + timedelta(days=ends)))
    if alternative:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(value) for value in alternative]), critical=False)
    return builder.sign(KEY, hashes.SHA256(), default_backend()).public_bytes(serialization.Encoding.PEM)


class CertificateOnDiskTests(unittest.TestCase):
    def serves(self, pem, name):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'fullchain.pem')
            Path(path).write_bytes(pem)
            return certificate_serves(path, name)

    def test_in_date_certificate_that_names_the_website(self):
        self.assertTrue(self.serves(certificate('a.test'), 'a.test'))
        self.assertTrue(self.serves(certificate('A.Test'), 'a.test'))
        self.assertTrue(self.serves(certificate('other.test', alternative=('x.test', 'a.test')), 'a.test'))
        self.assertTrue(self.serves(certificate('a.test', issuer='Fixture CA'), 'a.test'))
        self.assertTrue(self.serves(certificate('a.test') + certificate('Fixture CA'), 'a.test'))

    def test_wildcard_covers_one_label(self):
        wildcard = certificate('*.example.test')
        self.assertTrue(self.serves(wildcard, 'shop.example.test'))
        self.assertFalse(self.serves(wildcard, 'example.test'))
        self.assertFalse(self.serves(wildcard, 'a.shop.example.test'))

    def test_other_name_or_wrong_time_does_not_serve(self):
        self.assertFalse(self.serves(certificate('b.test', alternative=('www.b.test',)), 'a.test'))
        self.assertFalse(self.serves(certificate('a.test', starts=-30, ends=-1), 'a.test'))
        self.assertFalse(self.serves(certificate('a.test', starts=1, ends=30), 'a.test'))

    def test_unreadable_certificate_raises(self):
        with self.assertRaises(Exception):
            self.serves(b'fixture\n', 'a.test')


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
        self.notes = []

    def vhost(self, website):
        return os.path.join(self.root, 'conf/vhosts', website, 'vhost.conf')

    def add(self, website, certificate_pem=None, config=VHOST_CONFIG):
        """A website; its certificate is in date and names it unless another (or False) is given."""
        os.makedirs(os.path.dirname(self.vhost(website)))
        Path(self.vhost(website)).write_text(config)
        os.chmod(self.vhost(website), 0o600)
        Path(self.main).write_text(
            ensure_http_vhost_mapping(Path(self.main).read_text(), website) + VHOST_DEFINITION % website)
        if certificate_pem is not False:
            os.makedirs(os.path.join(self.certificates, website))
            Path(self.certificates, website, 'privkey.pem').write_bytes(KEY_PEM)
            Path(self.certificates, website, 'fullchain.pem').write_bytes(certificate_pem or certificate(website))

    def listener(self, name, address, website, *maps):
        with open(self.main, 'a') as target:
            target.write(listener(name, address, website, *maps).replace('/etc/letsencrypt/live', self.certificates))

    def config(self):
        return Path(self.main).read_text()

    def vhssl(self, website):
        return VHSSL.replace('/etc/letsencrypt/live', self.certificates) % {'domain': website}

    def install(self, website):
        install_vhost_certificate(website, self.root, self.certificates, self.notes.append)

    def repair(self, apply=None):
        return repair_https_listeners(apply or write_like_the_upgrade, self.notes.append, self.root, self.certificates)

    def files(self):
        return {str(path): path.read_bytes() for path in Path(self.root).rglob('*') if path.is_file()}

    def assert_served(self, case, *websites):
        """Both listeners map exactly these websites and each has one vhssl block for its own certificate."""
        for name in ('SSL', 'SSL IPv6'):
            case.assertEqual(sorted(mapped(self.config(), name)), sorted((site, site) for site in websites))
        for website in websites:
            text = Path(self.vhost(website)).read_text()
            case.assertEqual(text.count('vhssl'), 1)
            case.assertEqual(certificate_files(text), (os.path.join(self.certificates, website, 'privkey.pem'),
                                                       os.path.join(self.certificates, website, 'fullchain.pem')))


def write_like_the_upgrade(changes):
    """What the upgrade's validated configuration change does with a change it accepts."""
    for path, (before, after) in changes.items():
        if Path(path).read_text() != before:
            raise AssertionError('the change does not start from the text of ' + path)
        Path(path).write_bytes(after.encode(locale.getpreferredencoding(False)))


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.server = Server(directory.name)


class InstalledCertificateTests(ServerTestCase):
    def test_websites_get_certificates_one_after_another(self):
        for website in ('a.test', 'b.test', 'c.test'):
            self.server.add(website)
        self.server.install('a.test')
        self.server.assert_served(self, 'a.test')
        self.server.install('b.test')
        self.server.assert_served(self, 'a.test', 'b.test')
        self.server.install('c.test')
        self.server.assert_served(self, 'a.test', 'b.test', 'c.test')
        before = self.server.files()
        for website in ('b.test', 'a.test', 'c.test'):
            self.server.install(website)
        self.assertEqual(self.server.files(), before)
        self.assertEqual(self.server.config().count('listener SSL'), 2)
        self.assertEqual(self.server.notes, [])

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
        self.assertEqual([path.name for path in Path(self.server.root).rglob('.config-*')], [])

    def test_second_certificate_completes_a_server_that_has_the_ipv4_listener_only(self):
        # The first website was served with the certificate of the IPv4 listener and has no vhssl block.
        for website in ('a.test', 'b.test'):
            self.server.add(website)
        self.server.listener('SSL', '*:443', 'a.test')
        self.server.install('b.test')
        self.server.assert_served(self, 'a.test', 'b.test')
        self.assertIn(os.path.join(self.server.certificates, 'b.test', 'fullchain.pem'),
                      block(self.server.config(), 'SSL IPv6'))

    def test_later_certificate_completes_websites_that_are_on_one_family_each(self):
        for website in ('a.test', 'b.test', 'c.test'):
            self.server.add(website)
        self.server.listener('SSL', '*:443', 'a.test')
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test')
        self.server.install('c.test')
        self.server.assert_served(self, 'a.test', 'b.test', 'c.test')

    def test_website_being_installed_gets_its_block_whatever_its_certificate_is(self):
        self.server.add('a.test', certificate_pem=b'fixture\n')
        self.server.install('a.test')
        self.server.assert_served(self, 'a.test')

    def test_website_without_configuration_is_refused_before_anything_is_written(self):
        self.server.add('a.test')
        before = self.server.files()
        with self.assertRaisesRegex(ValueError, 'Website configuration not found'):
            self.server.install('missing.test')
        self.assertEqual(self.server.files(), before)

    def test_failed_listener_update_leaves_the_main_configuration_as_it_was(self):
        self.server.add('a.test')
        before = self.server.config()
        with mock.patch.object(subject, 'ensure_https_listeners', side_effect=RuntimeError('fixture')):
            with self.assertRaises(RuntimeError):
                self.server.install('a.test')
        self.assertEqual(self.server.config(), before)


class OtherWebsitesTests(ServerTestCase):
    """Completing the websites already served is best effort; the installation stands on its own."""

    def one_family_each(self):
        for website in ('a.test', 'x.test', 'b.test'):
            self.server.add(website)
        self.server.listener('SSL', '*:443', 'a.test', map_line('a.test'), map_line('x.test'))

    def test_website_whose_file_cannot_be_replaced_is_reported_and_the_rest_completed(self):
        self.one_family_each()

        def refuse(path, transform):
            if path == self.server.vhost('x.test'):
                raise PermissionError(1, 'Operation not permitted', path)
            return rewrite_config(path, transform)

        with mock.patch.object(subject, 'rewrite_config', side_effect=refuse):
            self.server.install('b.test')
        self.assertEqual(sorted(mapped(self.server.config(), 'SSL IPv6')), [('a.test', 'a.test'), ('b.test', 'b.test')])
        self.assertEqual(sorted(mapped(self.server.config(), 'SSL')),
                         [('a.test', 'a.test'), ('b.test', 'b.test'), ('x.test', 'x.test')])
        self.assertEqual(Path(self.server.vhost('x.test')).read_text(), VHOST_CONFIG)
        self.assertEqual(Path(self.server.vhost('a.test')).read_text().count('vhssl'), 1)
        self.assertEqual(len(self.server.notes), 1)
        self.assertIn('x.test was left without its own certificate block', self.server.notes[0])

    def test_website_that_cannot_be_examined_is_reported_and_the_rest_completed(self):
        self.one_family_each()
        Path(self.server.certificates, 'x.test', 'fullchain.pem').write_bytes(b'fixture\n')
        self.server.install('b.test')
        self.assertEqual(sorted(mapped(self.server.config(), 'SSL IPv6')), [('a.test', 'a.test'), ('b.test', 'b.test')])
        self.assertEqual(Path(self.server.vhost('x.test')).read_text(), VHOST_CONFIG)
        self.assertEqual(len(self.server.notes), 1)
        self.assertIn('x.test was not examined', self.server.notes[0])

    def test_failure_of_the_whole_completion_is_reported_not_raised(self):
        self.one_family_each()
        for broken in ('classify_listener_vhosts', 'reconcile_https_listener_maps'):
            with self.subTest(broken=broken):
                del self.server.notes[:]
                with mock.patch.object(subject, broken, side_effect=OSError('fixture')):
                    self.server.install('b.test')
                self.assertIn(('b.test', 'b.test'), mapped(self.server.config(), 'SSL'))
                self.assertIn(('b.test', 'b.test'), mapped(self.server.config(), 'SSL IPv6'))
                self.assertEqual(Path(self.server.vhost('b.test')).read_text().count('vhssl'), 1)
                self.assertEqual(self.server.notes, ['Other websites were not completed on the HTTPS listeners: fixture'])

    def test_files_are_changed_from_what_they_hold_when_they_are_written(self):
        # Another operation changes a website's file and the main configuration
        # after they were examined and before they are written.
        self.one_family_each()
        examine = classify_listener_vhosts

        def examine_then_change(*arguments):
            result = examine(*arguments)
            with open(self.server.vhost('a.test'), 'a') as target:
                target.write('# suspended meanwhile\n')
            self.server.add('new.test')
            return result

        with mock.patch.object(subject, 'classify_listener_vhosts', side_effect=examine_then_change):
            self.server.install('b.test')
        self.assertEqual(Path(self.server.vhost('a.test')).read_text(),
                         VHOST_CONFIG + '# suspended meanwhile\n' + self.server.vhssl('a.test'))
        self.assertIn(VHOST_DEFINITION % 'new.test', self.server.config())
        self.assertIn(('new.test', 'new.test'), mapped(self.server.config(), 'Default'))
        self.assertIn(('a.test', 'a.test'), mapped(self.server.config(), 'SSL IPv6'))

    def test_expired_or_foreign_certificate_does_not_bring_a_block(self):
        # These websites have no vhssl block and answer with the listener's certificate.
        self.server.add('a.test')
        self.server.add('old.test', certificate_pem=certificate('old.test', starts=-400, ends=-30))
        self.server.add('wild.test', certificate_pem=certificate('*.example.test'))
        self.server.add('b.test')
        self.server.listener('SSL', '*:443', 'a.test', map_line('a.test'), map_line('old.test'),
                             map_line('wild.test'))
        self.server.install('b.test')
        for website in ('old.test', 'wild.test'):
            self.assertEqual(Path(self.server.vhost(website)).read_text(), VHOST_CONFIG)
            self.assertNotIn((website, website), mapped(self.server.config(), 'SSL IPv6'))
        self.assertEqual(sorted(mapped(self.server.config(), 'SSL IPv6')), [('a.test', 'a.test'), ('b.test', 'b.test')])
        self.assertEqual(self.server.notes, [])

    def test_self_signed_certificate_in_date_brings_a_block(self):
        self.server.add('a.test', certificate_pem=certificate('a.test', ends=3650))
        self.server.add('b.test')
        self.server.listener('SSL', '*:443', 'a.test')
        self.server.install('b.test')
        self.server.assert_served(self, 'a.test', 'b.test')


class ExactBytesTests(ServerTestCase):
    """Files with Windows line endings or bytes that are not UTF-8 keep every byte they had."""

    ODD = b'# caf\xe9 \xff\xfe\r\n'

    def make_odd(self, path):
        data = self.ODD + Path(path).read_bytes().replace(b'\n', b'\r\n')
        Path(path).write_bytes(data)
        return data

    def assert_only_added(self, before, after):
        """Every line of the file is still there, in order and byte for byte, and what came in ends in CRLF."""
        old, new = before.split(b'\n'), after.split(b'\n')
        position = 0
        for line in old:
            self.assertIn(line, new[position:])
            position = new.index(line, position) + 1
        self.assertGreater(len(new), len(old))
        self.assertNotIn(b'\n', after.replace(b'\r\n', b''))

    def test_installation_keeps_odd_bytes_and_line_endings(self):
        for website in ('a.test', 'b.test'):
            self.server.add(website)
        self.server.listener('SSL', '*:443', 'a.test')
        before = {path: self.make_odd(path) for path in (
            self.server.main, self.server.vhost('a.test'), self.server.vhost('b.test'))}
        self.server.install('b.test')
        for path, data in before.items():
            self.assert_only_added(data, Path(path).read_bytes())
        config = Path(self.server.main).read_bytes().decode('latin-1').replace('\r\n', '\n')
        for name in ('SSL', 'SSL IPv6'):
            self.assertEqual(sorted(mapped(config, name)), [('a.test', 'a.test'), ('b.test', 'b.test')])
        for website in ('a.test', 'b.test'):
            self.assertEqual(Path(self.server.vhost(website)).read_bytes().count(b'vhssl  {\r\n'), 1)
        self.assertEqual(self.server.notes, [])

    def test_unchanged_file_is_not_rewritten(self):
        self.server.add('a.test')
        self.server.install('a.test')
        self.make_odd(self.server.vhost('a.test'))
        identity = os.stat(self.server.vhost('a.test')).st_ino
        self.server.install('a.test')
        self.assertEqual(os.stat(self.server.vhost('a.test')).st_ino, identity)

    def test_upgrade_change_is_stated_the_way_the_validated_change_reads_and_writes(self):
        for website in ('a.test', 'b.test'):
            self.server.add(website)
        self.server.listener('SSL', '*:443', 'a.test')
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test')
        before = {}
        for path in (self.server.main, self.server.vhost('a.test'), self.server.vhost('b.test')):
            before[path] = Path(path).read_bytes().replace(b'\n', b'\r\n')
            Path(path).write_bytes(before[path])
        seen = []

        def apply(changes):
            for path, (text, changed) in changes.items():
                self.assertEqual(text, Path(path).read_text())
                self.assertNotIn('\r', text)
                seen.append(path)
            write_like_the_upgrade(changes)

        completed, blocks = self.server.repair(apply)
        self.assertEqual(seen, [self.server.vhost('a.test'), self.server.vhost('b.test'), self.server.main])
        self.assertEqual((completed, blocks), ([('SSL', 'b.test'), ('SSL IPv6', 'a.test')], ['a.test', 'b.test']))
        for path, data in before.items():
            self.assert_only_added(data, Path(path).read_bytes())

    @unittest.skipUnless(locale.getpreferredencoding(False).lower().replace('-', '') == 'utf8', 'needs a UTF-8 locale')
    def test_upgrade_leaves_out_a_website_whose_file_is_not_text_and_repairs_the_rest(self):
        for website in ('a.test', 'b.test'):
            self.server.add(website)
        self.server.listener('SSL', '*:443', 'a.test')
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test')
        odd = self.make_odd(self.server.vhost('a.test'))
        completed, blocks = self.server.repair()
        self.assertEqual((completed, blocks), ([('SSL', 'b.test')], ['b.test']))
        self.assertEqual(Path(self.server.vhost('a.test')).read_bytes(), odd)
        self.assertEqual(len(self.server.notes), 1)
        self.assertIn('a.test was left without its own certificate block', self.server.notes[0])


class UpgradeRepairTests(ServerTestCase):
    def one_family_each(self):
        for website in ('a.test', 'b.test', 'c.test'):
            self.server.add(website, config=VHOST_CONFIG + (self.server.vhssl(website) if website == 'c.test' else ''))
        both = (map_line('c.test'),)
        self.server.listener('SSL', '*:443', 'a.test', map_line('a.test'), *both)
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test', map_line('b.test'), *both)

    def test_each_block_is_a_change_of_its_own_and_the_maps_follow(self):
        self.one_family_each()
        before = self.server.files()
        changes = []
        completed, blocks = self.server.repair(changes.append)
        self.assertEqual(self.server.files(), before)
        self.assertEqual([list(change) for change in changes],
                         [[self.server.vhost('a.test')], [self.server.vhost('b.test')], [self.server.main]])
        self.assertEqual((completed, blocks), ([('SSL', 'b.test'), ('SSL IPv6', 'a.test')], ['a.test', 'b.test']))
        self.assertEqual(changes[0][self.server.vhost('a.test')],
                         (VHOST_CONFIG, VHOST_CONFIG + self.server.vhssl('a.test')))
        self.assertTrue(all(holds_original(change) for change in changes))

    def test_repair_serves_every_website_on_both_families_and_is_final(self):
        self.one_family_each()
        self.server.repair()
        self.server.assert_served(self, 'a.test', 'b.test', 'c.test')
        after = self.server.files()
        self.assertEqual(self.server.repair(lambda changes: self.fail('nothing is left to change')), ([], []))
        self.assertEqual(self.server.files(), after)
        self.assertEqual(self.server.notes, [])

    def test_refused_block_leaves_that_website_out_and_repairs_the_rest(self):
        self.one_family_each()

        def apply(changes):
            if self.server.vhost('a.test') in changes:
                raise ChangeRefused('fixture refusal')
            write_like_the_upgrade(changes)

        completed, blocks = self.server.repair(apply)
        self.assertEqual((completed, blocks), ([('SSL', 'b.test')], ['b.test']))
        self.assertEqual(Path(self.server.vhost('a.test')).read_text(), VHOST_CONFIG)
        self.assertEqual(mapped(self.server.config(), 'SSL IPv6'), [('b.test', 'b.test'), ('c.test', 'c.test')])
        self.assertEqual(self.server.notes, ['a.test was left without its own certificate block: fixture refusal'])

    def test_website_under_a_linked_directory_is_left_out_and_the_rest_repaired(self):
        self.one_family_each()
        directory = os.path.dirname(self.server.vhost('a.test'))
        os.rename(directory, directory + '.real')
        os.symlink(directory + '.real', directory)
        completed, blocks = self.server.repair()
        self.assertEqual((completed, blocks), ([('SSL', 'b.test')], ['b.test']))
        self.assertEqual(Path(self.server.vhost('a.test')).read_text(), VHOST_CONFIG)
        self.assertEqual(len(self.server.notes), 1)
        self.assertIn('is reached through a symbolic link', self.server.notes[0])

    def test_linked_website_that_has_its_block_is_still_mapped(self):
        self.server.add('a.test', config=VHOST_CONFIG + self.server.vhssl('a.test'))
        self.server.add('b.test', config=VHOST_CONFIG + self.server.vhssl('b.test'))
        directory = os.path.dirname(self.server.vhost('a.test'))
        os.rename(directory, directory + '.real')
        os.symlink(directory + '.real', directory)
        self.server.listener('SSL', '*:443', 'a.test')
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test')
        self.assertEqual(self.server.repair(), ([('SSL', 'b.test'), ('SSL IPv6', 'a.test')], []))

    def test_change_that_could_not_be_taken_back_ends_the_repair(self):
        self.one_family_each()
        seen = []

        def apply(changes):
            seen.append(list(changes))
            raise RuntimeError('OpenLiteSpeed is unavailable after configuration reload')

        with self.assertRaisesRegex(RuntimeError, 'unavailable after configuration reload'):
            self.server.repair(apply)
        self.assertEqual(seen, [[self.server.vhost('a.test')]])

    def test_refused_map_change_is_passed_on_after_the_blocks_were_given(self):
        self.one_family_each()

        def apply(changes):
            if self.server.main in changes:
                raise ChangeRefused('fixture refusal')
            write_like_the_upgrade(changes)

        with self.assertRaisesRegex(ChangeRefused, 'fixture refusal'):
            self.server.repair(apply)
        self.assertEqual(Path(self.server.vhost('a.test')).read_text().count('vhssl'), 1)
        self.assertEqual(mapped(self.server.config(), 'SSL IPv6'), [('b.test', 'b.test'), ('c.test', 'c.test')])

    def test_website_without_a_usable_certificate_is_left_on_its_one_listener(self):
        self.server.add('a.test')
        self.server.add('plain.test', certificate_pem=False)
        self.server.add('old.test', certificate_pem=certificate('old.test', starts=-400, ends=-30))
        self.server.add('broken.test', certificate_pem=False, config=VHOST_CONFIG + self.server.vhssl('broken.test'))
        self.server.listener('SSL', '*:443', 'a.test', map_line('a.test'), map_line('plain.test'),
                             map_line('old.test'), map_line('broken.test'))
        self.server.listener('SSL IPv6', '[ANY]:443', 'a.test')
        before = self.server.files()
        self.assertEqual(self.server.repair(), ([], ['a.test']))
        self.assertEqual(mapped(self.server.config(), 'SSL IPv6'), [('a.test', 'a.test')])
        for website in ('plain.test', 'old.test', 'broken.test'):
            self.assertEqual(Path(self.server.vhost(website)).read_bytes(), before[self.server.vhost(website)])
        self.assertEqual(self.server.notes, [])

    def test_single_https_website_gets_its_own_certificate_block(self):
        self.server.add('a.test')
        self.server.listener('SSL', '*:443', 'a.test')
        self.assertEqual(self.server.repair(), ([], ['a.test']))

    def test_server_without_https_needs_nothing(self):
        self.server.add('a.test')
        self.assertEqual(self.server.repair(lambda changes: self.fail('nothing to change')), ([], []))

    def test_apache_backend_website_keeps_its_block(self):
        proxy = VHOST_CONFIG + self.server.vhssl('a.test')
        self.server.add('a.test', config=proxy)
        self.server.add('b.test')
        self.server.listener('SSL', '*:443', 'a.test')
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test')
        self.assertEqual(self.server.repair(), ([('SSL', 'b.test'), ('SSL IPv6', 'a.test')], ['b.test']))
        self.assertEqual(Path(self.server.vhost('a.test')).read_text(), proxy)

    def test_unsafe_name_in_a_map_is_ignored(self):
        self.server.add('a.test')
        self.server.add('b.test')
        self.server.listener('SSL', '*:443', 'a.test', map_line('a.test'), map_line('../a.test'))
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test')
        self.assertEqual(self.server.repair(), ([('SSL', 'b.test'), ('SSL IPv6', 'a.test')], ['a.test', 'b.test']))

    def test_custom_listener_is_not_part_of_the_repair(self):
        for website in ('a.test', 'b.test', 'shop.test'):
            self.server.add(website)
        self.server.listener('SSL', '*:443', 'a.test')
        self.server.listener('Shop8443', '*:8443', 'shop.test')
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test')
        custom = block(self.server.config(), 'Shop8443')
        self.server.repair()
        self.assertEqual(block(self.server.config(), 'Shop8443'), custom)
        self.assertEqual(Path(self.server.vhost('shop.test')).read_text(), VHOST_CONFIG)
        self.assertEqual(sorted(mapped(self.server.config(), 'SSL')), [('a.test', 'a.test'), ('b.test', 'b.test')])


def function(filename, name, class_name=None):
    """The definition of a function, or of a method when a class is named, without decorators."""
    body = ast.parse(Path(__file__).with_name(filename).read_text()).body
    if class_name:
        body = next(node for node in body if isinstance(node, ast.ClassDef) and node.name == class_name).body
    node = next(node for node in body if isinstance(node, ast.FunctionDef) and node.name == name)
    node.decorator_list = []
    return node


def compiled(node, namespace):
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), '<panel>', 'exec'), namespace)
    return namespace[node.name]


def strings(node):
    """Every string constant in a piece of syntax tree."""
    values = []
    for item in ast.walk(node):
        kind = type(item).__name__
        if kind == 'Constant':
            values.append(item.value)
        elif kind == 'Str':
            values.append(item.s)
    return [value for value in values if isinstance(value, str)]


def calls_on(node, owner):
    """(method name, line) of every call made on the name `owner`."""
    return [(item.func.attr, item.lineno) for item in ast.walk(node)
            if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute)
            and isinstance(item.func.value, ast.Name) and item.func.value.id == owner]


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
        installer = compiled(function(filename, 'installSSLForDomain', 'sslUtilities'), namespace)
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
            constants = strings(function(filename, 'installSSLForDomain', 'sslUtilities'))
            self.assertEqual([value for value in constants if 'httpd_config' in value or 'listener' in value], [])


class OLSUpgradeFailure(RuntimeError):
    pass


class UpgradeStepTests(ServerTestCase):
    """The step of the upgrade script, run against the temporary server."""

    def setUp(self):
        super(UpgradeStepTests, self).setUp()
        for website in ('a.test', 'b.test'):
            self.server.add(website)
        self.server.listener('SSL', '*:443', 'a.test')
        self.server.listener('SSL IPv6', '[ANY]:443', 'b.test')
        self.upgrade = mock.Mock()
        self.apply = mock.Mock(side_effect=write_like_the_upgrade)
        self.running = mock.Mock(return_value=True)
        self.installed = True
        namespace = {'os': SimpleNamespace(path=SimpleNamespace(exists=lambda path: self.installed)),
                     'Upgrade': self.upgrade, 'apply_ols_config_changes': self.apply,
                     'ols_service_running': self.running, 'OLSUpgradeFailure': OLSUpgradeFailure}
        self.step = compiled(function('upgrade.py', 'reconcileHTTPSListenerMaps', 'Upgrade'), namespace)
        here = mock.patch.object(subject, 'repair_https_listeners', functools.partial(
            repair_https_listeners, server_root=self.server.root, certificate_root=self.server.certificates))
        here.start()
        self.addCleanup(here.stop)

    def message(self):
        return self.upgrade.stdOut.call_args[0][0]

    def refuse(self, path, leave=None):
        """The validated change fails for one file; `leave` is what that file holds afterwards."""
        def apply(changes):
            if path in changes:
                if leave is not None:
                    Path(path).write_text(leave)
                raise OLSUpgradeFailure('OpenLiteSpeed configuration migration failed: fixture')
            write_like_the_upgrade(changes)
        self.apply.side_effect = apply

    def test_repair_goes_through_the_validated_configuration_change(self):
        self.step()
        self.assertEqual(self.apply.call_count, 3)
        self.server.assert_served(self, 'a.test', 'b.test')
        self.assertIn('2 mapping(s) completed, 2 website(s) given their own certificate block', self.message())
        self.assertIn('\n  SSL: b.test', self.message())
        self.assertIn('\n  SSL IPv6: a.test', self.message())

    def test_refused_and_restored_change_of_one_website_does_not_stop_the_others(self):
        self.refuse(self.server.vhost('a.test'))
        self.step()
        self.assertEqual(Path(self.server.vhost('a.test')).read_text(), VHOST_CONFIG)
        self.assertEqual(mapped(self.server.config(), 'SSL'), [('a.test', 'a.test'), ('b.test', 'b.test')])
        self.assertEqual(mapped(self.server.config(), 'SSL IPv6'), [('b.test', 'b.test')])
        self.assertIn('1 mapping(s) completed, 1 website(s) given', self.message())
        self.assertIn('a.test was left without its own certificate block', self.message())

    def test_refused_and_restored_map_change_is_a_warning(self):
        self.refuse(self.server.main)
        self.step()
        self.assertTrue(self.message().startswith('WARNING: HTTPS listener maps were not reconciled'))
        self.assertIn('fixture', self.message())

    def test_file_left_changed_by_a_failed_change_stops_the_upgrade(self):
        for path in (self.server.vhost('a.test'), self.server.main):
            with self.subTest(path=path):
                self.refuse(path, leave='half written\n')
                with self.assertRaisesRegex(OLSUpgradeFailure, 'fixture'):
                    self.step()

    def test_server_that_did_not_come_back_stops_the_upgrade(self):
        self.refuse(self.server.vhost('a.test'))
        self.running.side_effect = [True, False]
        with self.assertRaisesRegex(OLSUpgradeFailure, 'fixture'):
            self.step()
        self.upgrade.stdOut.assert_not_called()

    def test_state_that_cannot_be_established_after_a_failure_stops_the_upgrade(self):
        self.refuse(self.server.vhost('a.test'))
        self.running.side_effect = [True, RuntimeError('Cannot determine OpenLiteSpeed service state')]
        with self.assertRaisesRegex(OLSUpgradeFailure, 'fixture'):
            self.step()

    def test_stopped_server_that_stays_stopped_counts_as_restored(self):
        self.running.return_value = False
        self.refuse(self.server.vhost('a.test'))
        self.step()
        self.assertIn('a.test was left without its own certificate block', self.message())

    def test_state_that_cannot_be_established_beforehand_changes_nothing(self):
        before = self.server.files()
        self.running.side_effect = RuntimeError('Cannot determine OpenLiteSpeed service state')
        self.step()
        self.assertEqual(self.server.files(), before)
        self.apply.assert_not_called()
        self.assertTrue(self.message().startswith('WARNING: HTTPS listener maps were not reconciled'))

    def test_server_without_openlitespeed_is_skipped(self):
        self.installed = False
        self.step()
        self.apply.assert_not_called()
        self.upgrade.stdOut.assert_not_called()

    def test_upgrade_runs_the_step_once_the_new_release_is_in_place(self):
        calls = calls_on(function('upgrade.py', 'upgrade', 'Upgrade'), 'Upgrade')
        lines = dict(calls)
        self.assertEqual([name for name, _ in calls].count('reconcileHTTPSListenerMaps'), 1)
        self.assertLess(lines['downloadAndUpgrade'], lines['reconcileHTTPSListenerMaps'])

    def test_upgrade_started_from_the_cloud_runs_the_step_too(self):
        calls = calls_on(function('CyberPanelUpgrade.py', 'UpgardeNow', 'UpgradeCyberPanel'), 'Upgrade')
        lines = dict(calls)
        self.assertEqual([name for name, _ in calls].count('reconcileHTTPSListenerMaps'), 1)
        self.assertLess(lines['downloadAndUpgrade'], lines['reconcileHTTPSListenerMaps'])
        self.assertLess(lines['sensitiveFileProtectionMigration'], lines['reconcileHTTPSListenerMaps'])


class LeftoverCertificateTests(unittest.TestCase):
    """What a failed public issuance does with certificate files that are already under the name."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.live = directory.name
        self.install = mock.Mock(return_value=1)
        self.openssl = mock.Mock(return_value=0)
        panel = SimpleNamespace(obtainSSLForADomain=mock.Mock(return_value=0), installSSLForDomain=self.install,
                                isStagingCertificate=lambda certificate: False)

        def here(path):
            return path.replace('/etc/letsencrypt/live', self.live)

        def under_live(check):
            return lambda path: path.startswith('/etc/letsencrypt/live') and check(here(path))

        files = SimpleNamespace(
            path=SimpleNamespace(exists=under_live(os.path.exists), lexists=under_live(os.path.lexists),
                                 dirname=os.path.dirname),
            makedirs=lambda path, exist_ok=False: os.makedirs(here(path), exist_ok=exist_ok))
        namespace = {'os': files, 'open': lambda path, *mode: open(here(path), *mode), 'shlex': shlex,
                     'subprocess': SimpleNamespace(call=self.openssl), 'sslUtilities': panel,
                     'logging': mock.MagicMock()}
        self.issue = compiled(function('sslUtilities.py', 'issueSSLForDomain'), namespace)

    def leave(self, pem):
        os.makedirs(os.path.join(self.live, 'a.test'), exist_ok=True)
        Path(self.live, 'a.test', 'privkey.pem').write_bytes(KEY_PEM)
        Path(self.live, 'a.test', 'fullchain.pem').write_bytes(pem)
        return self.left()

    def left(self):
        return {name: Path(self.live, 'a.test', name).read_bytes() for name in ('privkey.pem', 'fullchain.pem')}

    def create(self):
        return self.issue('a.test', 'owner@example.test', '/home/a.test/public_html', newWebsite=True)

    def test_first_creation_gets_a_self_signed_certificate(self):
        result = self.create()
        self.assertEqual(result[:2], [2, 'Public SSL issuance failed. A self-signed certificate was installed.'])
        self.assertEqual(result[2]['outcome'], 'self_signed')
        self.assertEqual(self.openssl.call_count, 1)
        self.install.assert_called_once_with('a.test')

    def test_creation_over_a_self_signed_leftover_gets_the_same_answer_and_keeps_the_files(self):
        first = self.create()
        self.openssl.reset_mock()
        self.install.reset_mock()
        before = self.leave(certificate('a.test', ends=3650))
        self.assertEqual(self.create(), first)
        self.assertEqual(self.left(), before)
        self.openssl.assert_not_called()
        self.install.assert_called_once_with('a.test')

    def test_creation_over_a_real_leftover_installs_it_and_never_replaces_it(self):
        before = self.leave(certificate('a.test', issuer='Fixture CA'))
        result = self.create()
        self.assertEqual(result[0], 2)
        self.assertEqual(result[2]['outcome'], 'existing_certificate')
        self.assertIn('existing date-valid certificate remains installed', result[1])
        self.assertEqual(self.left(), before)
        self.openssl.assert_not_called()
        self.install.assert_called_once_with('a.test')

    def test_creation_over_an_expired_leftover_is_refused_and_keeps_the_files(self):
        for issuer in (None, 'Fixture CA'):
            with self.subTest(issuer=issuer):
                self.setUp()
                before = self.leave(certificate('a.test', starts=-400, ends=-30, issuer=issuer))
                result = self.create()
                self.assertEqual(result[0], 0)
                self.assertIn('expired and has been preserved', result[1])
                self.assertEqual(self.left(), before)
                self.openssl.assert_not_called()
                self.install.assert_not_called()

    def test_creation_fails_when_the_leftover_cannot_be_installed(self):
        self.leave(certificate('a.test', ends=3650))
        self.install.return_value = 0
        self.assertEqual(self.create()[0], 0)
        self.openssl.assert_not_called()

    def test_issue_ssl_on_an_existing_website_still_reports_the_self_signed_certificate(self):
        before = self.leave(certificate('a.test', ends=3650))
        for arguments in ({}, {'forceIssue': True}):
            with self.subTest(arguments=arguments):
                result = self.issue('a.test', 'owner@example.test', '/home/a.test/public_html', **arguments)
                self.assertEqual(result[:2], [
                    0, 'New SSL issuance failed. The existing self-signed certificate has been preserved.'])
                self.assertEqual(self.left(), before)
        self.install.assert_not_called()
        self.openssl.assert_not_called()

    def test_websites_and_child_domains_say_when_they_are_being_created(self):
        source = ast.parse(Path(__file__).with_name('virtualHostUtilities.py').read_text())
        owner = next(node for node in source.body
                     if isinstance(node, ast.ClassDef) and node.name == 'virtualHostUtilities')
        flagged = {}
        for node in owner.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            for call in ast.walk(node):
                if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                        and call.func.attr == 'issueSSLForDomain' and getattr(call.func.value, 'id', '') == 'sslUtilities'):
                    flagged.setdefault(node.name, []).append(
                        any(keyword.arg == 'newWebsite' for keyword in call.keywords))
        self.assertEqual(flagged['createVirtualHost'], [True])
        self.assertEqual(flagged['_createDomain'], [True])
        self.assertEqual(sorted(name for name, flags in flagged.items() if any(flags)),
                         ['_createDomain', 'createVirtualHost'])




class HelperLocationTests(unittest.TestCase):
    """The upgrade script finds the helpers staged beside it after it has changed directory."""

    def test_a_script_started_by_a_relative_name_still_finds_its_helpers_later(self):
        body = ast.parse(Path(__file__).with_name('upgrade.py').read_text()).body
        wanted = [node for node in body
                  if (isinstance(node, ast.Assign)
                      and getattr(node.targets[0], 'id', '') == 'UPGRADE_SCRIPT_DIRECTORY')
                  or (isinstance(node, ast.FunctionDef) and node.name == 'load_ols_diagnostic_helper')]
        self.assertEqual(2, len(wanted))
        before = os.getcwd()
        with tempfile.TemporaryDirectory() as staged, tempfile.TemporaryDirectory() as elsewhere:
            Path(staged, 'helperForTest.py').write_text('VALUE = 7\n')
            try:
                os.chdir(staged)
                # Python 3.6 gives a script started as "python upgrade.py" this relative name.
                scope = {'os': os, '__file__': 'upgrade.py'}
                exec(compile(ast.Module(body=wanted, type_ignores=[]), 'upgrade.py', 'exec'), scope)
                os.chdir(elsewhere)
                self.assertEqual(7, scope['load_ols_diagnostic_helper']('helperForTest.py').VALUE)
            finally:
                os.chdir(before)


if __name__ == '__main__':
    unittest.main()
