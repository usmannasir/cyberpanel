"""The FTP user name shown after creation is the name that was stored and signs in."""
import ast
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from plogical.ftpConfiguration import ftp_user_name_prefix, stored_ftp_user_name

ROOT = Path(__file__).resolve().parents[1]


def method_of(source, class_name, name, scope):
    """One method of a panel class, run in ``scope`` instead of the module that needs Django."""
    tree = ast.parse((ROOT / source).read_text(encoding='utf-8'))
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == name)
    method.decorator_list = []
    exec(compile(ast.Module(body=[method], type_ignores=[]), source, 'exec'), scope)
    return scope[name]


class NameRuleTests(unittest.TestCase):

    def test_the_panel_form_stores_the_name_behind_the_panel_users_prefix(self):
        self.assertEqual('admin_qaftp', stored_ftp_user_name('admin', 'qaftp', '0'))
        self.assertEqual('reseller.one_site', stored_ftp_user_name('reseller.one', 'site', '0'))

    def test_the_preview_of_the_form_is_the_name_the_form_stores(self):
        for panel_user, typed in (('admin', 'qaftp'), ('reseller.one', 'site'), ('a_b', 'c_d')):
            self.assertEqual(stored_ftp_user_name(panel_user, typed, '0'),
                             ftp_user_name_prefix(panel_user) + typed)

    def test_the_command_line_and_api_callers_name_the_whole_account(self):
        for api in (None, '1', 1, 0):
            self.assertEqual('qaftp', stored_ftp_user_name('admin', 'qaftp', api), repr(api))

    def test_the_website_is_no_part_of_the_name(self):
        self.assertNotIn('panelqa.test', stored_ftp_user_name('admin', 'qaftp', '0'))


class StoredRow(object):
    """Stands for the row of the FTP users table; ``column_width`` is what the table keeps of a name."""
    column_width = 32
    saved = []

    def __init__(self, **fields):
        self.__dict__.update(fields)
        self.in_table = None

    def save(self):
        self.in_table = self.user[:self.column_width]
        StoredRow.saved.append(self)

    def refresh_from_db(self, fields=None):
        self.user = self.in_table


class CreationUtilityTests(unittest.TestCase):

    def setUp(self):
        StoredRow.saved = []
        StoredRow.column_width = 32
        self.website = SimpleNamespace(
            externalApp='panel1234',
            package=SimpleNamespace(ftpAccounts=0, diskSpace=1000),
            users_set=SimpleNamespace(all=lambda: SimpleNamespace(count=lambda: 0)))
        child_domains = mock.Mock()
        child_domains.objects.get.side_effect = LookupError('not a child domain')
        self.log = mock.Mock()
        scope = {
            'ChildDomains': child_domains,
            'Websites': SimpleNamespace(objects=SimpleNamespace(get=lambda domain: self.website)),
            'Administrator': SimpleNamespace(objects=SimpleNamespace(
                get=lambda userName: SimpleNamespace(userName=userName))),
            'Users': StoredRow,
            'pwd': SimpleNamespace(getpwnam=lambda name: SimpleNamespace(pw_uid=5001)),
            'grp': SimpleNamespace(getgrnam=lambda name: SimpleNamespace(gr_gid=5001)),
            'os': SimpleNamespace(path=SimpleNamespace(islink=lambda path: False)),
            'ProcessUtilities': SimpleNamespace(decideDistro=lambda: None, ubuntu22Check=0, alma9check=0),
            'hashlib': __import__('hashlib'),
            'datetime': __import__('datetime').datetime,
            'logging': SimpleNamespace(CyberCPLogFileWriter=SimpleNamespace(writeToFile=self.log)),
            'stored_ftp_user_name': stored_ftp_user_name,
            'print': lambda *args: None,
        }
        self.scope = scope
        self.create = method_of('plogical/ftpUtilities.py', 'FTPUtilities', 'submitFTPCreation', scope)

    def test_the_form_gets_back_the_name_of_the_stored_row(self):
        result = self.create('panelqa.test', 'qaftp', 'inert', 'None', 'admin', '0')
        self.assertEqual((1, 'None', 'admin_qaftp'), result)
        self.assertEqual(['admin_qaftp'], [row.in_table for row in StoredRow.saved])
        self.assertEqual('/home/panelqa.test', StoredRow.saved[0].dir)

    def test_the_command_line_gets_back_the_name_it_gave(self):
        result = self.create('panelqa.test', 'qaftp', 'inert', 'None', 'admin')
        self.assertEqual((1, 'None', 'qaftp'), result)
        self.assertEqual(['qaftp'], [row.in_table for row in StoredRow.saved])

    def test_a_name_the_table_shortened_is_reported_as_the_table_holds_it(self):
        StoredRow.column_width = 12
        result = self.create('panelqa.test', 'a-rather-long-name', 'inert', 'None', 'admin', '0')
        self.assertEqual((1, 'None', 'admin_a-rath'), result)

    def test_a_refused_creation_reports_no_name(self):
        self.website.package.ftpAccounts = 1
        self.website.users_set = SimpleNamespace(all=lambda: SimpleNamespace(count=lambda: 1))
        result = self.create('panelqa.test', 'qaftp', 'inert', 'None', 'admin', '0')
        self.assertEqual((0, 'Exceeded maximum amount of FTP accounts allowed for the package.'), result)
        self.assertEqual([], StoredRow.saved)
        self.log.assert_called_once()

    def test_a_symlinked_home_is_refused_with_a_reason(self):
        self.scope['os'] = SimpleNamespace(path=SimpleNamespace(islink=lambda path: True))
        result = self.create('panelqa.test', 'qaftp', 'inert', 'None', 'admin', '0')
        self.assertEqual((0, '/home/panelqa.test file is symlinked.'), result)
        self.assertEqual([], StoredRow.saved)


class Reply(object):
    def __init__(self, content):
        self.content = content


class CreationReplyTests(unittest.TestCase):

    def setUp(self):
        self.acl = mock.Mock()
        self.acl.currentContextPermission.return_value = 1
        self.acl.checkOwnership.return_value = 1
        self.utility = mock.Mock()
        self.utility.submitFTPCreation.return_value = (1, 'None', 'admin_qaftp')
        scope = {
            'ACLManager': self.acl,
            'Administrator': SimpleNamespace(objects=SimpleNamespace(
                get=lambda **unused: SimpleNamespace(userName='admin'))),
            'FTPUtilities': self.utility,
            'HttpResponse': Reply,
            'json': json,
        }
        self.submit = method_of('ftp/ftpManager.py', 'FTPManager', 'submitFTPCreation', scope)

    def reply(self, **sent):
        body = dict({'ftpDomain': 'panelqa.test', 'ftpUserName': 'qaftp', 'passwordByPass': 'inert'}, **sent)
        manager = SimpleNamespace(request=SimpleNamespace(session={'userID': 1}, body=json.dumps(body)))
        return json.loads(self.submit(manager).content)

    def test_the_reply_carries_the_stored_name(self):
        reply = self.reply()
        self.assertEqual({'status': 1, 'creatFTPStatus': 1, 'error_message': 'None', 'ftpUserName': 'admin_qaftp'},
                         reply)
        self.utility.submitFTPCreation.assert_called_once_with(
            'panelqa.test', 'qaftp', 'inert', 'None', 'admin', '0')

    def test_the_reply_to_an_api_caller_carries_the_name_it_gave(self):
        self.utility.submitFTPCreation.return_value = (1, 'None', 'qaftp')
        self.assertEqual('qaftp', self.reply(api='1')['ftpUserName'])
        self.assertEqual('1', self.utility.submitFTPCreation.call_args[0][5])

    def test_a_failed_creation_names_no_account(self):
        self.utility.submitFTPCreation.return_value = (0, 'Exceeded maximum amount of FTP accounts allowed.')
        reply = self.reply()
        self.assertEqual(0, reply['creatFTPStatus'])
        self.assertEqual('Exceeded maximum amount of FTP accounts allowed.', reply['error_message'])
        self.assertNotIn('ftpUserName', reply)


class PageTests(unittest.TestCase):

    def setUp(self):
        self.script = (ROOT / 'ftp' / 'static' / 'ftp' / 'ftp.js').read_text(encoding='utf-8')
        self.page = (ROOT / 'ftp' / 'templates' / 'ftp' / 'createFTPAccount.html').read_text(encoding='utf-8')

    def test_the_page_shows_the_name_of_the_reply(self):
        self.assertIn('$scope.createdFTPUsername = response.data.ftpUserName;', self.script)
        self.assertEqual(1, self.script.count('$scope.createdFTPUsername ='))
        self.assertIn('<strong>{$ createdFTPUsername $}</strong>', self.page)

    def test_the_script_builds_no_user_name_itself(self):
        self.assertNotIn('ftpDomain + "_"', self.script)
        self.assertNotIn('+ "_" + ftpUserName', self.script)

    def test_the_preview_uses_the_prefix_the_server_gives(self):
        self.assertIn('{{ ftpUserNamePrefix }}{$ ftpUserName $}', self.page)
        self.assertNotIn('}}_{$', self.page)
        manager = (ROOT / 'ftp' / 'ftpManager.py').read_text(encoding='utf-8')
        self.assertIn("'ftpUserNamePrefix': ftp_user_name_prefix(admin.userName)", manager)
        utility = (ROOT / 'plogical' / 'ftpUtilities.py').read_text(encoding='utf-8')
        self.assertIn('userName = stored_ftp_user_name(admin.userName, userName, api)', utility)
        self.assertNotIn('admin.userName + "_"', utility)

    def test_both_copies_of_the_script_are_the_same(self):
        self.assertEqual((ROOT / 'ftp' / 'static' / 'ftp' / 'ftp.js').read_bytes(),
                         (ROOT / 'static' / 'ftp' / 'ftp.js').read_bytes())

    def test_the_changed_script_is_fetched_again(self):
        for page in ('baseTemplate/templates/baseTemplate/index.html', 'ftp/templates/ftp/ResetFTPconf.html'):
            self.assertIn("{% static 'ftp/ftp.js' %}?v={{ CP_VERSION }}-created-name\"", (ROOT / page).read_text(encoding='utf-8'), page)


class OldestPythonTests(unittest.TestCase):

    def test_changed_modules_parse_on_python_3_6(self):
        options = {'feature_version': (3, 6)} if sys.version_info >= (3, 8) else {}
        for source in ('plogical/ftpConfiguration.py', 'plogical/ftpUtilities.py', 'ftp/ftpManager.py',
                       'ftp/test_created_user_name.py'):
            ast.parse((ROOT / source).read_text(encoding='utf-8'), **options)


if __name__ == '__main__':
    unittest.main()
