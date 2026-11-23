"""The panel's pages do not link to guides that have moved.

The Restore Backup page linked to a knowledge-base address that answers
"not found"; so did a number of other pages, and four linked to forum topics
that are gone. Each address below was read once: the old one answered 404
and the new one 200. The check reads the templates as text and needs no
network.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KB = 'https://cyberpanel.net/KnowledgeBase/home/'

# The address a page used to link to, the guide's current address, and the pages that link to it.
MOVED = (
    (KB + 'backup-restore/', KB + '1-backup-restore/',
     ('backup/backup.html', 'backup/restore.html', 'backup/restoreOCBackups.html')),
    (KB + 'child-domains-launcher/', KB + '4-child-domains-launcher/', ('websiteFunctions/launchChild.html',)),
    (KB + 'creating-website/', KB + '2-creating-website/',
     ('websiteFunctions/createDomain.html', 'websiteFunctions/createWebsite.html')),
    (KB + 'cron-jobs/', KB + '7-cron-jobs/', ('websiteFunctions/listCron.html',)),
    (KB + 'cyberpanel-on-ssl/', KB + '2-cyberpanel-on-ssl/', ('manageSSL/sslForHostName.html',)),
    (KB + 'dkim-set-up-and-configurations/', KB + '1-dkim-set-up-and-configurations/',
     ('mailServer/dkimManager.html',)),
    (KB + 'dns-management-cyberpanel/', KB + 'manage-dns-in-cyberpanel/', ('manageServices/managePowerDNS.html',)),
    (KB + 'email-forwarding/', KB + '3-email-forwarding/', ('mailServer/emailForwarding.html',)),
    (KB + 'rewrite-rules/', KB + '6-rewrite-rules/', ('emailMarketing/website.html',)),
    (KB + 'spamassassin-configurations/', KB + '5-spamassassin-configurations/', ('emailPremium/SpamAssassin.html',)),
    (KB + 'website-management/', KB + 'website-management-2/', ('websiteFunctions/manageGIT.html',)),
    ('https://community.cyberpanel.net/t/1-convert-cyberpanel-to-cloudlinux-os-and-install-cagefs/174',
     KB + '1-convert-cyberpanel-to-cloudlinux-os-and-install-cagefs/',
     ('CLManager/notAvailable.html', 'firewall/notAvailable.html')),
    ('https://community.cyberpanel.net/t/2-mod-security-configurations/135',
     KB + '2-mod-security-configurations/', ('firewall/modSecurity.html',)),
    ('https://community.cyberpanel.net/t/4-mod-security-rules-packages/133',
     KB + '4-mod-security-rules-packages/',
     ('firewall/modSecurityRules.html', 'firewall/modSecurityRulesPacks.html')),
    ('https://community.cyberpanel.net/t/6-self-signed-ssl-error-on-outlook-thunderbird/207',
     KB + '6-self-signed-ssl-error-on-outlook-thunderbird/', ('mailServer/listEmails.html',)),
)


def templates():
    """Every template of the panel by the name a view gives it, with its text."""
    found = {}
    for folder in sorted(ROOT.glob('*/templates')):
        for path in sorted(folder.rglob('*.html')):
            found[path.relative_to(folder).as_posix()] = path.read_text(errors='replace')
    return found


class DocumentationLinks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.templates = templates()

    def test_the_templates_are_found(self):
        self.assertGreater(len(self.templates), 200)

    def test_the_restore_backup_page_links_to_the_current_guide(self):
        page = self.templates['backup/restore.html']
        self.assertIn('href="https://cyberpanel.net/KnowledgeBase/home/1-backup-restore/"', page)
        self.assertNotIn('KnowledgeBase/home/backup-restore/', page)

    def test_no_page_links_to_an_address_that_has_moved(self):
        for old, new, pages in MOVED:
            linking = sorted(name for name, text in self.templates.items() if old in text)
            self.assertEqual(linking, [], old)

    def test_each_page_links_to_the_current_address(self):
        for old, new, pages in MOVED:
            for name in pages:
                self.assertIn('href="%s"' % new, self.templates[name], '%s in %s' % (new, name))

    def test_no_page_sends_its_reader_to_the_forum_for_a_guide(self):
        linking = sorted(name for name, text in self.templates.items() if 'community.cyberpanel.net/t/' in text)
        self.assertEqual(linking, [])


if __name__ == '__main__':
    unittest.main()
