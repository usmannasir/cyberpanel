"""Opening phpMyAdmin from the panel: who may, by which request, and what is named after the user."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from cryptography.fernet import Fernet
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from databases import views


class Session(dict):
    modified = False


class PhpMyAdminViewTests(SimpleTestCase):
    def setUp(self):
        self.admin = SimpleNamespace(pk=7, userName='reseller1', state='ACTIVE')
        self.acl = {'admin': 0, 'listDatabases': 1}
        database = SimpleNamespace(dbName='exam_shop')
        self.sites = [SimpleNamespace(databases_set=SimpleNamespace(all=lambda: [database]))]
        self.records = mock.Mock()
        self.records.objects.filter.return_value = []
        self.session = Session(userID=7)
        patches = {
            'admin_get': mock.patch.object(views.Administrator.objects, 'get', side_effect=lambda **kw: self.admin),
            'loaded': mock.patch.object(views.ACLManager, 'loadedACL', side_effect=lambda user: self.acl),
            'find_sites': mock.patch.object(views.ACLManager, 'findWebsiteObjects',
                                            side_effect=lambda acl, user: self.sites),
            'records': mock.patch.object(views, 'GlobalUserDB', self.records),
            'command': mock.patch.object(views.ProcessUtilities, 'executioner'),
            'output': mock.patch.object(views.ProcessUtilities, 'outputExecutioner'),
            'retire': mock.patch.object(views.phpmyadminAccess, 'retire_earlier', return_value=1),
            'write_key': mock.patch.object(views.phpmyadminAccess, 'write_key'),
            'read_key': mock.patch.object(views.phpmyadminAccess, 'read_key'),
            'account': mock.patch.object(views.mysqlUtilities, 'addUserToDB', return_value=1),
            'log': mock.patch.object(views.logging, 'writeToFile'),
        }
        for name, item in patches.items():
            setattr(self, name, item.start())
            self.addCleanup(item.stop)

    def call(self, view, method='post', data=None):
        factory = RequestFactory()
        if method == 'post' and data is None:
            request = factory.post('/dataBases/x', data='{}', content_type='application/json')
        else:
            request = getattr(factory, method)('/dataBases/x', data or {})
        request.session = self.session
        return view(request)

    def answer(self, view, method='post'):
        return json.loads(self.call(view, method).content.decode())

    # generateAccess

    def test_access_is_prepared_under_the_user_number_only(self):
        answer = self.answer(views.generateAccess)
        self.assertEqual(1, answer['status'])
        self.assertEqual('reseller1', answer['username'])
        self.retire.assert_called_once_with(self.admin)
        (user_id, key), unused = self.write_key.call_args
        self.assertEqual(7, user_id)
        unused, saved = self.records.call_args
        self.assertEqual('cp-pma-7', saved['username'])
        self.assertEqual(answer['token'], saved['token'])
        password = Fernet(key).decrypt(saved['password'].encode()).decode()
        self.assertEqual([mock.call(None, 'cp-pma-7', password, 1), mock.call('exam_shop', 'cp-pma-7', password, 0)],
                         self.account.call_args_list)
        self.records.objects.filter.assert_called_with(username='cp-pma-7')

    def test_no_command_carries_the_user_name(self):
        for name in ('reseller1', 'John Smith', 'john.doe', 'john@example.com', 'jürgen', 'root', 'cyberpanel'):
            self.admin.userName = name
            self.command.reset_mock()
            self.account.reset_mock()
            self.assertEqual(1, self.answer(views.generateAccess)['status'], name)
            self.assertEqual([mock.call('chmod 640 /usr/local/lscp/cyberpanel/logs/access.log')],
                             self.command.call_args_list, name)
            for call in self.account.call_args_list:
                self.assertEqual('cp-pma-7', call[0][1])
        self.output.assert_not_called()

    def test_name_that_cannot_be_carried_is_refused_before_anything_is_done(self):
        for name in ('x /etc/shadow', 'x & id', "x' OR '1", 'a/../../b', 'x\nid', ' x', 'x;id', 'x|id', '$(id)',
                     '`id`', 'x>y', '-rf', ''):
            self.admin.userName = name
            answer = self.answer(views.generateAccess)
            self.assertEqual(0, answer['status'], repr(name))
            self.assertNotIn('token', answer)
        self.command.assert_not_called()
        self.output.assert_not_called()
        self.retire.assert_not_called()
        self.write_key.assert_not_called()
        self.account.assert_not_called()
        self.records.assert_not_called()

    def test_request_that_is_not_a_post_is_refused(self):
        for method in ('get', 'head', 'put', 'delete'):
            self.assertEqual(405, self.call(views.generateAccess, method).status_code, method)
        self.admin_get.assert_not_called()
        self.command.assert_not_called()
        self.account.assert_not_called()

    def test_user_who_may_not_list_databases_is_refused(self):
        for acl in ({'admin': 0, 'listDatabases': 0}, {'admin': 0}):
            self.acl = acl
            answer = self.answer(views.generateAccess)
            self.assertEqual(0, answer['status'])
            self.assertNotIn('token', answer)
        self.command.assert_not_called()
        self.write_key.assert_not_called()
        self.account.assert_not_called()
        self.records.assert_not_called()

    def test_failed_account_leaves_no_record_and_no_token(self):
        stale = mock.Mock()
        self.records.objects.filter.return_value = [stale]
        self.account.return_value = 0
        answer = self.answer(views.generateAccess)
        self.assertEqual(0, answer['status'])
        self.assertNotIn('token', answer)
        self.assertEqual(1, self.account.call_count)
        self.assertEqual(2, stale.delete.call_count)

    def test_administrator_gets_a_record_under_the_user_number_and_no_account(self):
        self.acl = {'admin': 1}
        answer = self.answer(views.generateAccess)
        self.assertEqual(1, answer['status'])
        unused, saved = self.records.call_args
        self.assertEqual('cp-pma-7', saved['username'])
        self.retire.assert_called_once_with(self.admin)
        self.account.assert_not_called()
        self.write_key.assert_not_called()

    # the sign-in page

    def sign_in(self, token='the-token', username='reseller1'):
        key = Fernet.generate_key()
        self.read_key.return_value = key
        record = SimpleNamespace(token='the-token', password=Fernet(key).encrypt(b'account-password').decode())
        self.records.objects.get.return_value = record
        rendered = {}

        def page(request, template, data=None, permission=None):
            rendered.update(template=template, data=data, permission=permission)
            return SimpleNamespace(render=lambda: HttpResponse('page'))

        with mock.patch('plogical.httpProc.httpProc', side_effect=page):
            response = self.call(views.fetchDetailsPHPMYAdmin, data={'token': token, 'username': username})
        return response, rendered

    def test_sign_in_page_names_the_numbered_account_and_is_not_stored(self):
        response, rendered = self.sign_in()
        self.assertEqual('no-store', response['Cache-Control'])
        self.assertEqual('databases/AutoLogin.html', rendered['template'])
        self.assertEqual({'userName': 'cp-pma-7', 'password': 'account-password', 'token': 'the-token'},
                         rendered['data'])
        self.records.objects.get.assert_called_once_with(username='cp-pma-7')
        self.read_key.assert_called_once_with(7)
        self.account.assert_called_once_with('exam_shop', 'cp-pma-7', 'account-password', 0)
        self.assertEqual('cp-pma-7', self.session['phpmyadmin_handoff']['username'])
        self.output.assert_not_called()
        self.command.assert_not_called()

    def test_sign_in_page_needs_the_token_of_the_record(self):
        response, rendered = self.sign_in(token='another-token')
        self.assertNotEqual('databases/AutoLogin.html', rendered.get('template'))
        self.assertNotIn('no-store', response.get('Cache-Control', ''))
        self.account.assert_not_called()
        self.assertNotIn('phpmyadmin_handoff', self.session)

    def test_sign_in_page_has_no_script_from_elsewhere(self):
        page = (Path(views.__file__).parent / 'templates' / 'databases' / 'AutoLogin.html').read_text()
        self.assertNotIn('src=', page)
        self.assertNotIn('http', page.replace('/phpmyadmin/phpmyadminsignin.php', ''))
        self.assertNotIn('$(', page)
        self.assertIn('<input type="hidden" name="username" value="{{ userName }}"/>', page)
        self.assertIn('<input type="hidden" name="password" value="{{ password }}"/>', page)
        self.assertIn('<input type="hidden" name="handoff_token" value="{{ token }}"/>', page)
        self.assertIn('action="/phpmyadmin/phpmyadminsignin.php" method="post"', page)
        self.assertIn('document.forms["loginform"].submit();', page)
