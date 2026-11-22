"""A restore recreates the owner of a website under the name it had, and says so when it cannot."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from plogical import databaseAccounts as accounts
from plogical.backupMetadata import backup_includes_mail_domain
from plogical.panelUserNames import new_name_refusal, restored_name_refusal
from plogical.test_backup_restore_ssl import load_method
from managePHP.phpConfig import stored_php_selection


class RestoredNameTests(unittest.TestCase):
    def test_names_earlier_releases_accepted_are_restored(self):
        for name in ('john', 'John Smith', 'jürgen', 'محمد', 'john+tag@example.com', '_john', 'John.Doe', 'x' * 50):
            self.assertIsNone(restored_name_refusal(name), name)

    def test_most_of_them_would_be_refused_for_a_new_user(self):
        for name in ('John Smith', 'john+tag@example.com', '_john'):
            self.assertIsNotNone(new_name_refusal(name), name)

    def test_names_of_the_server_are_never_restored(self):
        for name in ('root', 'Root', 'cyberpanel', 'mysql', 'public', 'cp-pma-5', 'CP-PMA-9'):
            self.assertIn('reserved', restored_name_refusal(name), name)

    def test_names_that_cannot_be_carried_are_not_restored(self):
        for name in ('', ' john', 'john ', "jo'hn", 'a/b', '../x', 'a;b', 'a&b', 'a|b', '$(x)', '`x`', 'a\nb',
                     '-x', '.x', 'x' * 51, None, 7, b'john'):
            refusal = restored_name_refusal(name)
            self.assertIsNotNone(refusal, repr(name))
            self.assertNotIn('reserved', refusal)


class Users:
    """The user table of the destination server: `admin` exists, the owner of the backup does not."""

    def __init__(self, refusal=None):
        self.refusal = refusal
        self.made = []
        self.saves = []
        self.admin = SimpleNamespace(userName='admin', email='admin@example.test')
        users = self

        class Administrator(SimpleNamespace):
            objects = SimpleNamespace(get=users.get)

            def __init__(self, **values):
                SimpleNamespace.__init__(self, **values)
                users.made.append(self)

            def save(self, **options):
                users.saves.append(options)
                if users.refusal is not None:
                    raise ValueError(users.refusal)

        self.model = Administrator

    def get(self, userName):
        if userName == 'admin':
            return self.admin
        raise LookupError('no such user')


def metadata(owner):
    fields = dict(userName=owner, userPassword='hash', firstName='John', lastName='Smith',
                  email='john@example.test', type='3', owner='1', token='t', api='0', securityLevel='0',
                  state='ACTIVE', initWebsitesLimit='0', aclName='user')
    if owner is None:
        fields = {}
    return ('<metaFile><masterDomain>example.test</masterDomain><phpSelection>PHP 8.3</phpSelection>'
            '<externalApp>example</externalApp><VERSION>3.0</VERSION><BUILD>11</BUILD>%s'
            '<Databases></Databases></metaFile>'
            % ''.join('<%s>%s</%s>' % (key, escape(value), key) for key, value in fields.items()))


class RestoredOwnerTests(unittest.TestCase):
    def restore(self, owner, refusal=None):
        self.users = Users(refusal)
        self.hosts = mock.Mock()
        self.hosts.createVirtualHost.return_value = (1, 'None')
        self.log = mock.Mock()
        namespace = dict(os=os, ElementTree=ElementTree, generate_pass=lambda length: 'starting-password',
                         stored_php_selection=stored_php_selection,
                         Administrator=self.users.model, databaseAccounts=accounts,
                         Websites=SimpleNamespace(objects=mock.Mock()),
                         ChildDomains=SimpleNamespace(objects=mock.Mock()),
                         virtualHostUtilities=self.hosts, DNS=mock.Mock(),
                         logging=SimpleNamespace(CyberCPLogFileWriter=self.log),
                         mysqlUtilities=SimpleNamespace(mysqlUtilities=mock.Mock()),
                         backup_includes_mail_domain=backup_includes_mail_domain,
                         backup_uses_database_users_schema=lambda *args: True)
        namespace['Websites'].objects.filter.return_value.count.return_value = 0
        namespace['ChildDomains'].objects.filter.return_value.count.return_value = 0
        create = load_method('backupUtilities.py', 'backupUtilities', 'createWebsiteFromBackup', namespace)
        roles = SimpleNamespace(ACL=SimpleNamespace(objects=SimpleNamespace(get=lambda name: 'acl:' + name)))
        with tempfile.TemporaryDirectory() as scratch:
            archive = Path(scratch) / 'fixture.tar.gz'
            archive.touch()
            (Path(scratch) / 'fixture').mkdir()
            (Path(scratch) / 'fixture' / 'meta.xml').write_text(metadata(owner), encoding='utf-8')
            self.status = str(Path(scratch) / 'fixture' / 'status')
            with mock.patch.dict('sys.modules', {'loginSystem.models': roles}):
                return create(str(archive), 'fixture')

    def website_owner(self):
        # createVirtualHost(domain, email, php, externalApp, ssl, dkim, openBasedir, owner, ...)
        return self.hosts.createVirtualHost.call_args[0][7]

    def test_owner_is_recreated_under_the_name_from_the_backup(self):
        for name in ('john', 'John Smith', 'jürgen'):
            self.assertEqual((1, 'None'), self.restore(name), name)
            user, = self.users.made
            self.assertEqual(name, user.userName)
            # The restore, and nothing else, asks for the rule of existing users.
            self.assertEqual([{'name_from_backup': True}], self.users.saves)
            self.assertEqual(name, self.website_owner())
            self.log.writeToFile.assert_not_called()

    def test_owner_that_cannot_be_recreated_is_named_in_the_log_and_the_status(self):
        self.assertEqual((1, 'None'), self.restore('root', refusal='This user name is reserved for the server.'))
        self.assertEqual('admin', self.website_owner())
        logged = self.log.writeToFile.call_args[0][0]
        self.assertIn("'root'", logged)
        self.assertIn('was not recreated', logged)
        self.assertIn('reserved for the server', logged)
        self.assertIn('given to admin', logged)
        path, shown = self.log.statusWriter.call_args[0]
        self.assertEqual(self.status, path)
        self.assertIn("'root'", shown)
        self.assertIn('given to admin', shown)

    def test_backup_without_an_owner_goes_to_admin_without_a_notice(self):
        self.assertEqual((1, 'None'), self.restore(None))
        self.assertEqual('admin', self.website_owner())
        self.log.writeToFile.assert_not_called()
        self.log.statusWriter.assert_not_called()


if __name__ == '__main__':
    unittest.main()
