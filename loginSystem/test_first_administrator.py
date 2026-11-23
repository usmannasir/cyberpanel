"""The sign-in page creates no account.

While it had no administrator, the panel created "admin" with the password
1234567 on the first request it got, from whoever sent it. The page now has
the first administrator made on the server, by adminPass.py as root, with a
password that nobody chose and that only root there can read, and says where
it is until "admin" has signed in. No test here needs a database.
"""
import inspect
import json
import os
import tempfile
from types import SimpleNamespace
from unittest import mock

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from loginSystem import first_administrator, views

COMMAND = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/adminPass.py --first-administrator'


class MarkerCase(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.marker = os.path.join(directory.name, 'adminPassGenerated')
        patcher = mock.patch.object(first_administrator, 'GENERATED_PASSWORD_MARKER', self.marker)
        patcher.start()
        self.addCleanup(patcher.stop)

    def mark(self):
        open(self.marker, 'w').close()


class SignInPageTests(MarkerCase):
    def page(self, count, made=True, marked=False, path='/'):
        if marked:
            self.mark()
        manager = mock.Mock()
        manager.count.return_value = count
        manager.exists.return_value = made
        rules = mock.Mock()
        rules.count.return_value = 1
        cosmetic = SimpleNamespace(MainDashboardCSS='')
        cosmetics = mock.Mock()
        cosmetics.get.return_value = cosmetic
        shown = {}

        def render(request, template, context):
            shown.update(template=template, context=context)
            return HttpResponse('page')

        request = RequestFactory().get(path)
        request.session = SessionStore()
        with mock.patch.object(views.Administrator, 'objects', manager), \
                mock.patch('firewall.models.FirewallRules.objects', rules), \
                mock.patch('baseTemplate.models.CyberPanelCosmetic.objects', cosmetics), \
                mock.patch('plogical.processUtilities.ProcessUtilities.executioner') as executioner, \
                mock.patch('plogical.hashPassword.hash_password') as hashing, \
                mock.patch.object(views, 'render', render):
            views.loadLoginPage(request)
        self.assertEqual('loginSystem/login.html', shown['template'])
        self.assertIs(cosmetic, shown['context']['cosmetic'])
        hashing.assert_not_called()
        return shown['context'], executioner

    def test_without_an_administrator_the_first_one_is_made_on_the_server(self):
        context, executioner = self.page(0, made=True, marked=True)
        executioner.assert_called_once_with(COMMAND)
        self.assertTrue(context.get('generated_password'))
        self.assertNotIn('no_administrator', context)

    def test_nothing_of_the_request_reaches_the_command(self):
        context, executioner = self.page(0, path="/?user=x;id&next=$(reboot)")
        executioner.assert_called_once_with(COMMAND)
        self.assertEqual(COMMAND, first_administrator.FIRST_ADMINISTRATOR_COMMAND)

    def test_when_none_could_be_made_the_page_says_what_to_run(self):
        context, executioner = self.page(0, made=False)
        executioner.assert_called_once_with(COMMAND)
        self.assertTrue(context.get('no_administrator'))
        self.assertNotIn('generated_password', context)

    def test_a_helper_that_raises_is_a_panel_without_an_administrator(self):
        manager = mock.Mock()
        manager.exists.return_value = False
        with mock.patch.object(views.Administrator, 'objects', manager), \
                mock.patch('plogical.processUtilities.ProcessUtilities.executioner', side_effect=OSError('no helper')):
            self.assertFalse(first_administrator.ensure_first_administrator())
        manager.exists.side_effect = RuntimeError('no database')
        with mock.patch.object(views.Administrator, 'objects', manager), \
                mock.patch('plogical.processUtilities.ProcessUtilities.executioner'):
            self.assertFalse(first_administrator.ensure_first_administrator())

    def test_with_an_administrator_nothing_is_run_and_the_notice_follows_the_marker(self):
        context, executioner = self.page(1)
        executioner.assert_not_called()
        self.assertEqual(['cosmetic'], sorted(context))
        context, executioner = self.page(1, marked=True)
        executioner.assert_not_called()
        self.assertTrue(context.get('generated_password'))

    def test_the_page_holds_no_password(self):
        source = inspect.getsource(views.loadLoginPage)
        self.assertNotIn('1234567', source)
        self.assertNotIn('hash_password', source)
        self.assertNotIn('Administrator(', source)
        self.assertNotIn('createDefaultACLs', source)


class CreateFirstAdministratorTests(SimpleTestCase):
    def test_the_account_rows_are_saved_together_after_the_acls(self):
        events = []

        class Atomic:
            def __enter__(self):
                events.append('begin')

            def __exit__(self, kind, value, trace):
                events.append('rollback' if kind else 'commit')
                return False

        def model(name, fail=False):
            def make(**fields):
                def save():
                    events.append('save ' + name)
                    if fail:
                        raise RuntimeError('fixture: refused')
                return SimpleNamespace(save=save, **fields)
            return make

        def run(package_fails):
            del events[:]
            with mock.patch.object(first_administrator.transaction, 'atomic', Atomic), \
                    mock.patch.object(first_administrator.ACLManager, 'createDefaultACLs',
                                      side_effect=lambda: events.append('acls')), \
                    mock.patch.object(first_administrator.ACL, 'objects', mock.Mock()), \
                    mock.patch.object(first_administrator, 'Administrator', model('admin')), \
                    mock.patch.object(first_administrator, 'version', model('version')), \
                    mock.patch.object(first_administrator, 'Package', model('package', package_fails)), \
                    mock.patch.object(first_administrator.hashPassword, 'hash_password', return_value='hash'), \
                    mock.patch.object(first_administrator.hashPassword, 'generateToken', return_value='token'):
                return first_administrator.create_first_administrator('Generated0123456789ab')

        admin = run(False)
        self.assertEqual(['acls', 'begin', 'save admin', 'save version', 'save package', 'commit'], events)
        self.assertEqual('admin', admin.userName)
        self.assertEqual('hash', admin.password)
        with self.assertRaises(RuntimeError):
            run(True)
        self.assertEqual(['acls', 'begin', 'save admin', 'save version', 'save package', 'rollback'], events)


class NoticeTemplateTests(SimpleTestCase):
    def render(self, **context):
        return render_to_string('loginSystem/login.html', dict(cosmetic=SimpleNamespace(MainDashboardCSS=''),
                                                                **context))

    def test_generated_password_notice(self):
        page = self.render(generated_password=True)
        self.assertIn('id="cp-generated-password"', page)
        self.assertIn('/etc/cyberpanel/adminPass', page)
        self.assertNotIn('id="cp-no-administrator"', page)

    def test_no_administrator_notice(self):
        page = self.render(no_administrator=True)
        self.assertIn('id="cp-no-administrator"', page)
        self.assertIn("adminPass 'a password of your choice'", page.replace('&#x27;', "'").replace('&#39;', "'"))
        self.assertNotIn('id="cp-generated-password"', page)

    def test_no_notice_on_an_ordinary_page(self):
        page = self.render()
        self.assertNotIn('cp-generated-password', page.split('</style>')[-1])
        self.assertNotIn('cp-no-administrator', page.split('</style>')[-1])


class SignInEndsTheNoticeTests(MarkerCase):
    def sign_in(self, user_name, password_right):
        admin = SimpleNamespace(pk=7, userName=user_name, password='stored-password-hash', state='ACTIVE',
                                twoFA=False, secretKey='')
        request = RequestFactory().post('/verifyLogin', data=json.dumps({'username': user_name, 'password': 'x'}),
                                        content_type='application/json')
        request.META['REMOTE_ADDR'] = '192.0.2.1'
        request.session = SessionStore()
        with mock.patch('loginSystem.views.Administrator.objects.get', return_value=admin), \
                mock.patch('loginSystem.views.hashPassword.check_password', return_value=password_right):
            return json.loads(views.verifyLogin(request).content)['loginStatus']

    def test_admin_who_signs_in_ends_the_notice(self):
        self.mark()
        self.assertEqual(1, self.sign_in('admin', True))
        self.assertFalse(os.path.lexists(self.marker))

    def test_a_refused_sign_in_keeps_the_notice(self):
        self.mark()
        self.assertEqual(0, self.sign_in('admin', False))
        self.assertTrue(os.path.lexists(self.marker))

    def test_another_account_keeps_the_notice(self):
        self.mark()
        self.assertEqual(1, self.sign_in('reseller', True))
        self.assertTrue(os.path.lexists(self.marker))

    def test_a_sign_in_without_a_marker_is_not_troubled(self):
        self.assertEqual(1, self.sign_in('admin', True))

    def test_an_account_object_without_a_name_signs_in_as_before(self):
        # As the older sign-in tests give it: the notice is not touched.
        self.mark()
        admin = SimpleNamespace(pk=7, password='stored-password-hash', state='ACTIVE', twoFA=False, secretKey='')
        request = RequestFactory().post('/verifyLogin', data=json.dumps({'username': 'admin', 'password': 'x'}),
                                        content_type='application/json')
        request.META['REMOTE_ADDR'] = '192.0.2.1'
        request.session = SessionStore()
        with mock.patch('loginSystem.views.Administrator.objects.get', return_value=admin), \
                mock.patch('loginSystem.views.hashPassword.check_password', return_value=True):
            self.assertEqual(1, json.loads(views.verifyLogin(request).content)['loginStatus'])
        self.assertTrue(os.path.lexists(self.marker))
