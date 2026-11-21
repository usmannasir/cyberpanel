"""Every new PHP-FPM pool has a section name no other pool has."""
import unittest

from managePHP.phpConfig import existing_fpm_pool_name, fpm_pool_name
from plogical.test_fpm_service_commands import ApacheVhostLoader

VHOST = '/usr/local/lsws/conf/vhosts/%s/vhost.conf'


def section(text):
    return text.splitlines()[0]


class PoolNameTests(unittest.TestCase):
    def test_domains_that_shared_a_name_before_get_different_names(self):
        # The old name was the first seven letters of the domain.
        domains = ('shop1.example.test', 'shop2.example.test', 'shop.example.test', 'shopexa.test',
                   'example.test', 'Example.test')
        names = {fpm_pool_name('siteuser', domain) for domain in domains}
        self.assertEqual(len(domains), len(names))

    def test_name_is_the_site_user_and_a_digest_of_the_domain(self):
        name = fpm_pool_name('examp1234', 'example.test')
        self.assertRegex(name, r'^examp1234-[0-9a-f]{12}$')
        self.assertEqual(name, fpm_pool_name('examp1234', 'example.test'))
        self.assertNotEqual(name, fpm_pool_name('other5678', 'example.test'))

    def test_new_names_cannot_equal_a_name_given_by_an_earlier_version(self):
        # Earlier names were the site user alone or up to seven letters.
        for old in ('examp1234', 'example', 'shopexa', 'www', 'global'):
            self.assertNotEqual(old.lower(), fpm_pool_name('examp1234', 'example.test').lower())
            self.assertIn('-', fpm_pool_name(old, 'example.test'))

    def test_a_site_user_that_would_break_the_section_line_is_refused(self):
        for user in ('', 'a b', 'x]\n[global', 'x]', '[x', 'a;b', '-x', 'u' * 80):
            with self.subTest(user=user):
                with self.assertRaisesRegex(ValueError, 'Invalid PHP-FPM pool name'):
                    fpm_pool_name(user, 'example.test')

    def test_existing_name_is_read_from_the_first_section_line(self):
        pool = '; tuned\n\n[%s]\nlisten = /var/run/php/example.test.sock\nuser = siteuser\n'
        for name in ('siteuser', 'example', 'siteuser-0123456789ab', 'my.pool_1'):
            self.assertEqual(name, existing_fpm_pool_name(pool % name))

    def test_no_existing_name_from_other_content(self):
        for text in ('', None, 'listen = x\n[later]\n', '[global]\n', '[GLOBAL]\n', '[www]\n', '[a b]\n',
                     '[x] ; note\n', '[]\n', '[x\n', '[%s]\n' % ('n' * 65), 'cat: /etc/php: No such file\n'):
            with self.subTest(text=text):
                self.assertIsNone(existing_fpm_pool_name(text))


class WrittenPoolTests(unittest.TestCase):
    def setUp(self):
        self.loader = ApacheVhostLoader()
        self.addCleanup(self.loader.close)
        self.apache = self.loader.vhost

    def pool(self, domain, php='8.3'):
        return self.loader.text('/etc/php/%s/fpm/pool.d/%s.conf' % (php, domain))

    def test_website_and_child_domains_get_pools_of_their_own(self):
        self.assertEqual([1, 'None'], self.apache.perHostVirtualConf(
            'owner@example.test', 'siteuser', 'siteuser', 'PHP 8.3', 'example.test'))
        for child in ('shop1.example.test', 'shop2.example.test'):
            self.assertEqual([1, 'None'], self.apache.perHostVirtualConfChild(
                'owner@example.test', 'siteuser', 'siteuser', 'PHP 8.3', child, '/home/example.test/' + child))
        sections = [section(self.pool(domain))
                    for domain in ('example.test', 'shop1.example.test', 'shop2.example.test')]
        self.assertEqual(3, len(set(sections)))
        for domain, line in zip(('example.test', 'shop1.example.test', 'shop2.example.test'), sections):
            self.assertEqual('[%s]' % fpm_pool_name('siteuser', domain), line)
            # The rest of the pool is what it was: own socket, the site's user.
            self.assertIn('listen = /var/run/php/%s.sock\n' % domain, self.pool(domain))
            self.assertIn('user = siteuser\ngroup = siteuser\n', self.pool(domain))

    def test_php_change_of_a_child_does_not_reuse_the_name_of_its_website(self):
        self.apache.perHostVirtualConf('owner@example.test', 'siteuser', 'siteuser', 'PHP 8.1', 'example.test')
        self.assertEqual(1, self.apache.changePHP('PHP 8.1', VHOST % 'shop1.example.test'))
        website, child = self.pool('example.test', '8.1'), self.pool('shop1.example.test', '8.1')
        self.assertNotEqual(section(website), section(child))
        self.assertEqual('[%s]' % fpm_pool_name('siteuser', 'shop1.example.test'), section(child))


if __name__ == '__main__':
    unittest.main()
