"""The pages where administrators give a server its role, pair two servers and end a link.

Requests go through the panel's own URL table and middleware, on a real MariaDB
with real sessions, on a server marked as a disposable test server
(multiServer/testing.py). The checks of the templates themselves run anywhere.
"""
import os
from pathlib import Path
import re
import secrets
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from install import multiserver_identity as provision
from multiServer import crypto, keys, msctl, pairing, stepup, test_gateway, test_links, testing, transport

SKIP = testing.unavailable()
if SKIP is None:
    from django.contrib.sessions.backends.db import SessionStore
    from django.contrib.sessions.models import Session
    from django.shortcuts import render
    from django.test import Client
    from loginSystem.models import Administrator
    from multiServer import controllers, entitlement, models
    Base = test_gateway.Panel
else:
    Base = unittest.TestCase

SECRET = 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP'
PASSWORD = 'correct horse; battery $taple'
LINK = test_gateway.LINK
IDENTITY, NODE_KEY, NODE = test_gateway.IDENTITY, test_gateway.NODE_KEY, test_gateway.NODE
PIN = 'd4' * 32
SIGNED_IN_TEXT = 'Confirmed. You can open your servers from here now.'
ADDRESS = '93.184.216.34'  # where a managed server is, as its pairing code says
CALLER = '203.0.113.9'  # the address a controller calls from
TEMPLATES = Path(__file__).resolve().parent / 'templates' / 'multiServer'
CODE = re.compile(r'CPMS1-PAIR(?:-[A-Z2-7]{1,8})+')
ALERT = re.compile(r'<p role="status"[^>]*>(.*?)</p>', re.S)
ROUTES = ('/multiserver/role', '/multiserver/controllers', '/multiserver/controllers/control',
          '/multiserver/nodes', '/multiserver/nodes/control', '/multiserver/nodes/add')


class Clock(object):
    def __init__(self):
        self.now = int(time.time()) // 30 * 30

    def time(self):
        return self.now + 0.4


class Shown(object):
    """In the place of the panel's page frame, which reads tables this database does not have."""

    def __init__(self, request, template, data=None, function=None):
        self.request, self.template, self.data = request, template, data

    def render(self):
        return render(self.request, self.template, dict(self.data or {}, admin=1))


class TemplateTests(unittest.TestCase):
    NEW = ('role.html', 'controllers.html', 'code.html', 'add.html')

    def test_the_pages_run_no_script_of_their_own_and_are_not_read_by_the_front_end(self):
        for name in self.NEW + ('nodes.html', 'confirm.html'):
            source = (TEMPLATES / name).read_text()
            self.assertNotIn('<script', source.lower(), name)
            self.assertIsNone(re.search(r'\son[a-z]+\s*=', source), name)
            self.assertNotIn('|safe', source, name)
            self.assertNotIn('autoescape off', source, name)
            self.assertNotIn('{$', source, name)
        for name in self.NEW:
            source = (TEMPLATES / name).read_text()
            # Everything a page shows is inside one element the front end does not evaluate.
            self.assertEqual(1, source.count('<div class="container-fluid" ng-non-bindable>'), name)
            self.assertLess(source.index('ng-non-bindable'), source.index('{{'), name)

    def test_every_form_is_a_post_with_the_token_and_no_field_fills_itself_in(self):
        for name in self.NEW + ('nodes.html', 'confirm.html'):
            source = (TEMPLATES / name).read_text()
            forms = re.findall(r'<form\b[^>]*>.*?</form>', source, re.S)
            for form in forms:
                self.assertIn('method="post"', form.split('>', 1)[0], name)
                self.assertIn('{% csrf_token %}', form, name)
            self.assertEqual(len(forms), source.count('<form'), name)
            for field in re.findall(r'<input[^>]*type="password"[^>]*>', source):
                self.assertNotIn('value=', field, name)
        self.assertEqual(0, (TEMPLATES / 'code.html').read_text().count('<form'))

    def test_where_a_licence_is_missing_or_needed_the_page_links_to_where_it_is_bought(self):
        link = re.compile(r'<a href="{{ buy_url }}" target="_blank" rel="noopener">Get a licence for this '
                          r'(?:server|controller)</a>')
        directory = TEMPLATES.parent.parent
        for name, view in (('role.html', 'role.py'), ('nodes.html', 'nodes.py'), ('inventory.html', 'lists.py')):
            source = (TEMPLATES / name).read_text()
            self.assertEqual(1, len(link.findall(source)), name)
            self.assertEqual(1, source.count('buy_url'), name)
            self.assertIn("'buy_url'", (directory / view).read_text(), view)
            self.assertIn('entitlement.purchase_url()', (directory / view).read_text(), view)
        # Only a controller without a licence is offered one on the lists of its servers.
        for name in ('nodes.html', 'inventory.html'):
            source = (TEMPLATES / name).read_text()
            self.assertLess(source.index('{% else %}'), source.index('buy_url'), name)
        # The price is the platform's to say, not the panel's.
        for name in ('role.html', 'nodes.html', 'inventory.html'):
            self.assertNotIn('$', (TEMPLATES / name).read_text(), name)

    def test_two_factor_is_set_up_on_the_role_page_and_nothing_asks_to_sign_out(self):
        role = (TEMPLATES / 'role.html').read_text()
        for action in ('setup', 'enrol'):
            self.assertEqual(1, role.count('<input type="hidden" name="action" value="%s">' % action), action)
        # The code is drawn as squares from the server: no script, no image from elsewhere.
        self.assertIn('{% for x, y, width in qr_runs %}', role)
        self.assertNotIn('<img', role)
        # A licensed server is not offered a licence.
        self.assertLess(role.index('{% if licensed %}'), role.index('buy_url'))
        nodes = (TEMPLATES / 'nodes.html').read_text()
        self.assertIn('<input type="hidden" name="action" value="confirm">', nodes)
        for name in ('role.html', 'nodes.html'):
            self.assertNotRegex((TEMPLATES / name).read_text().lower(), r'sign out and sign in|sign in again|then sign in', name)
        self.assertNotIn('SIGN_IN_AGAIN', (TEMPLATES.parent.parent / 'role.py').read_text())

    def test_the_base_template_includes_the_selector_only_when_there_is_one(self):
        source = (TEMPLATES.parent.parent.parent / 'baseTemplate' / 'templates' / 'baseTemplate' / 'index.html'
                  ).read_text()
        includes = re.findall(r'[^\n]*include "multiServer/selector.html"[^\n]*', source)
        self.assertEqual(2, len(includes))
        for line in includes:
            self.assertRegex(line, r'{% if ms_(server|create) %}{% include "multiServer/selector.html"')
        # The sidebar entry needs no route to exist: its address comes from the app itself.
        entry = source[source.index('{% if ms_menu %}'):source.index('{% if showManagedNodes %}')]
        self.assertIn('<a href="{{ ms_menu }}"', entry)
        self.assertNotIn('{% url', entry)
        self.assertLess(source.index('{% if admin %}'), source.index('{% if ms_menu %}'))


@unittest.skipIf(SKIP, SKIP)
class Pages(Base):
    """A signed-in full administrator with a password and a second factor, on the panel of test_gateway."""

    def setUp(self):
        super().setUp()
        from plogical import hashPassword
        from plogical.processUtilities import ProcessUtilities
        Administrator.objects.filter(pk=self.administrator.pk).update(
            password=hashPassword.hash_password(PASSWORD), twoFA=1, secretKey=SECRET)
        self.time = self.start(patch.object(stepup, 'time', Clock()))
        self.start(patch('plogical.httpProc.httpProc', Shown))
        self.directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.directory)
        os.mkdir(os.path.join(self.directory, 'revoked'))
        self.start(patch.object(keys, 'KEY_DIRECTORY', self.directory))
        self.start(patch.object(keys, 'OWNER', os.getuid()))
        self.commands, self.said = [], []
        self.executioner = self.start(patch.object(ProcessUtilities, 'executioner', side_effect=self.as_root))
        self.output = self.start(patch.object(ProcessUtilities, 'outputExecutioner', side_effect=self.as_root_said))
        self.sign_in()

    # Root, as the panel's helper would run it: msctl.py itself, with the counter of this test.

    def raise_counter(self):
        self.generation.return_value += 1
        return self.generation.return_value

    def as_root(self, command, *more, **options):
        self.commands.append(command)
        words = command.split(' ')
        self.assertEqual([msctl.PYTHON, msctl.PROGRAM], words[:2])
        with patch.object(provision, 'bump_generation', side_effect=self.raise_counter), \
                patch.object(provision, 'ensure_key_directory'), \
                patch.object(msctl, '_start_django'), patch.object(os, 'geteuid', return_value=0), \
                patch.object(msctl, 'set_role', side_effect=self.set_role):
            return 1 if msctl.main(words[2:], self.said.append) == 0 else 0

    def as_root_said(self, command, *more, **options):
        self.assertEqual({'retRequired': True}, options)
        del self.said[:]
        return self.as_root(command), '\n'.join(self.said) + '\n'

    def set_role(self, role, say):
        refusal = getattr(self, 'role_refusal', None)
        if refusal is not None:
            say(refusal)
            return 1
        self.role.return_value = role
        say(msctl.ROLE_SET % role)
        return 0

    # The administrator.

    def fresh(self):
        """A verification code that was not used before: the one of the next half minute."""
        import pyotp
        self.time.now += 30
        return pyotp.TOTP(SECRET).generate_otp(self.time.now // 30)

    def confirmed(self, **fields):
        return dict(dict(password=PASSWORD, code=self.fresh()), **fields)

    def post(self, path, follow=False, client=None, **fields):
        return (client or self.client).post(path, data=fields, follow=follow)

    def text(self, response):
        return response.content.decode('utf-8')

    # A whole page is not a helpful thing to print: a failure names what was looked for and what the page said.

    def assertIn(self, member, container, msg=None):
        if isinstance(container, str) and len(container) > 2000:
            if member not in container:
                self.fail('%r is not on the page; it says %r (%s)' % (member, ALERT.findall(container), msg))
        else:
            super().assertIn(member, container, msg)

    def assertNotIn(self, member, container, msg=None):
        if isinstance(container, str) and len(container) > 2000:
            if member in container:
                self.fail('%r is on the page (%s)' % (member, msg))
        else:
            super().assertNotIn(member, container, msg)

    def state(self):
        """Everything the pages can change."""
        tables = ('ms_links', 'ms_pairing_codes', 'ms_nodes', 'ms_sessions', 'ms_sso_tickets')
        return (tuple(self.database.run('SELECT * FROM `%s` ORDER BY 1' % table) for table in tables),
                self.database.run('SELECT COUNT(*) FROM ms_audit'),
                tuple(Administrator.objects.order_by('pk').values_list('pk', 'config', 'password', 'twoFA', 'acl_id')),
                self.role.return_value, self.generation.return_value, sorted(os.listdir(self.directory + '/revoked')),
                list(self.commands))

    def audited(self, since=0):
        return [(row.event, row.outcome, row.reason, row.link_id, row.actor)
                for row in models.AuditEntry.objects.filter(pk__gt=since).order_by('id')]

    def last_audit_id(self):
        row = models.AuditEntry.objects.order_by('-id').first()
        return row.pk if row else 0

    def nowhere(self, *secrets_, **more):
        """None of these was written down: not in the log, the audit trail, a session or a message."""
        written = repr(self.log) + repr(self.database.run('SELECT * FROM ms_audit')) + repr(self.commands)
        written += repr([SessionStore(session_key=key).load() for key in Session.objects.values_list('pk', flat=True)])
        written += repr(self.database.run('SELECT * FROM ms_links')) + repr(more.get('responses', ''))
        for secret in secrets_:
            self.assertNotIn(secret, written)

    def everyone_else(self):
        """(name, client) of each visitor the pages are not for; the administrator is put back afterwards."""
        def restore():
            Administrator.objects.filter(pk=self.administrator.pk).update(
                acl=self.full, twoFA=1, secretKey=SECRET, state='ACTIVE')
            models.LinkSession.objects.all().delete()
        self.addCleanup(restore)
        for name, change in (('a reseller', dict(acl=self.reseller)), ('a suspended administrator',
                                                                       dict(state='SUSPENDED')),
                             ('an administrator without a second factor', dict(twoFA=0)),
                             ('an administrator whose second factor has no secret', dict(secretKey='None'))):
            restore()
            Administrator.objects.filter(pk=self.administrator.pk).update(**change)
            yield name, self.client
        restore()
        # A session that a controller opened through a link.
        managed = Client()
        key = self.sign_in(managed)
        models.LinkSession.objects.create(session_key=key, link=self.link, created_at=int(time.time()))
        yield 'a session opened through a link', managed
        restore()


@unittest.skipIf(SKIP, SKIP)
class RolePageTests(Pages):
    def setUp(self):
        super().setUp()
        self.role.return_value = keys.OFF
        self.start(patch.object(entitlement, 'allowed', return_value=False))

    def change(self, role, follow=True, **fields):
        return self.post('/multiserver/role', follow=follow, **self.confirmed(role=role, **fields))

    def test_with_the_feature_off_a_full_administrator_finds_the_page_and_every_other_address_is_absent(self):
        response = self.client.get('/multiserver/role')
        self.assertEqual(200, response.status_code)
        page = self.text(response)
        self.assertIn('This server is: <strong>Off</strong>', page)
        for role in ('off', 'controller', 'node'):
            self.assertIn('name="role" value="%s"' % role, page)
        self.assertIn('no-cache', response['Cache-Control'])
        self.assertIn('href="/multiserver/role"', page)  # the sidebar entry
        self.assertIn('<a href="%s" target="_blank" rel="noopener">Get a licence for this server</a>'
                      % entitlement.purchase_url().replace('&', '&amp;'), page)
        for address in ROUTES[1:] + ('/multiserver/status', '/multiserver/', '/multiserver'):
            self.assertEqual(404, self.client.get(address).status_code, address)
            self.assertEqual(404, self.post(address, action='allow', controller_ip=CALLER).status_code, address)
        self.assertEqual([], self.commands)

    def test_the_role_is_changed_by_root_with_one_of_three_fixed_command_lines(self):
        for role, name in (('node', 'Managed server'), ('off', 'Off'), ('controller', 'Controller')):
            before = self.last_audit_id()
            page = self.text(self.change(role))
            self.assertIn('This server is now: %s.' % name, page)
            self.assertIn('This server is: <strong>%s</strong>' % name, page)
            self.assertEqual(msctl.ROLE_COMMANDS[role], self.commands[-1])
            self.assertEqual(role, self.role.return_value)
            self.assertEqual([('role', 'ok', '', '', 'admin')], self.audited(before))
        self.assertEqual(['%s %s role %s' % (msctl.PYTHON, msctl.PROGRAM, role)
                          for role in ('node', 'off', 'controller')], self.commands)
        self.executioner.assert_not_called()

    def test_nothing_a_visitor_sends_becomes_part_of_the_command(self):
        allowed = set(msctl.ROLE_COMMANDS.values())
        # Other fields, whatever they are called and whatever they hold, change nothing.
        self.change('node', command='reboot', arguments='-rf /', role2='controller', link_id='a1' * 16, user='root')
        self.assertEqual([msctl.ROLE_COMMANDS['node']], self.commands)
        # A role that is not one of the three words is not a request this page knows.
        for role in ('Node', 'node ', ' node', 'node off', 'node-off', 'both', '', 'controller,node', '../role',
                     'role node', 'off\tnode', 'nodes', 'node --help'):
            before = self.state()
            response = self.change(role, follow=False)
            self.assertEqual(404, response.status_code, role)
            self.assertEqual(before, self.state(), role)
        # Nor is one the panel's request filter refuses; what was typed with it is not written to the log.
        for role in ('node;id', 'node&&id', 'node|id', 'node`id`', 'node$(id)', "node'", 'node\nid', 'node>x'):
            before = self.state()
            response = self.post('/multiserver/role', role=role, password='planted-password', code='314159')
            self.assertIn('not accepted', self.text(response), role)
            self.assertEqual(before, self.state(), role)
        self.assertEqual(['Rejected node control input'] * 8, self.log)
        self.assertTrue(set(self.commands) <= allowed)
        self.assertEqual(1, len(self.commands))

    def test_the_role_is_changed_only_with_the_password_and_a_new_code(self):
        used = self.fresh()
        self.assertIn('This server is now: Managed server.',
                      self.text(self.post('/multiserver/role', follow=True, role='node', password=PASSWORD,
                                          code=used)))
        before = self.last_audit_id()
        for name, fields in (('a wrong password', dict(password='not it', code=self.fresh())),
                             ('no password', dict(code=self.fresh())),
                             ('the code used a moment ago', dict(password=PASSWORD, code=used)),
                             ('a wrong code', dict(password=PASSWORD, code='000000')),
                             ('no code', dict(password=PASSWORD))):
            page = self.text(self.post('/multiserver/role', follow=True, role='off', **fields))
            self.assertIn(stepup.WRONG, page, name)
            self.assertEqual('node', self.role.return_value, name)
        self.assertEqual([('role', 'refused', reason, '', 'admin') for reason in
                          ('password', 'password', 'two_factor', 'two_factor', 'two_factor')], self.audited(before))
        # The fifth wrong attempt shut the account out: now the right ones are not looked at either.
        self.assertIn(stepup.LOCKED, self.text(self.change('off')))
        self.assertEqual(('node', 1), (self.role.return_value, len(self.commands)))
        self.nowhere('not it', used, PASSWORD)

    def test_what_root_refuses_is_said_in_its_own_fixed_words_and_nothing_else_it_says_is_shown(self):
        for refusal in (msctl.HAS_SERVERS, msctl.HAS_CONTROLLERS, msctl.CANNOT_CHECK):
            self.role_refusal = refusal
            before = self.last_audit_id()
            page = self.text(self.change('controller'))
            self.assertIn(refusal.replace('"', '&quot;'), page)
            self.assertEqual(keys.OFF, self.role.return_value)
            self.assertEqual([('role', 'refused', 'not_allowed', '', 'admin')], self.audited(before))
        self.role_refusal = 'Traceback: <b>detail-from-root</b> {$ 7 * 7 $}'
        before = self.last_audit_id()
        page = self.text(self.change('controller'))
        self.assertIn('The role was not changed.', page)
        self.assertNotIn('detail-from-root', page)
        self.assertEqual([('role', 'error', 'internal', '', 'admin')], self.audited(before))
        # No answer from the helper at all is the same.
        self.output.side_effect = lambda *arguments, **options: None
        self.assertIn('The role was not changed.', self.text(self.change('controller')))

    def test_nobody_else_changes_the_role_or_sees_the_page(self):
        for name, client in self.everyone_else():
            before = self.state()
            shown = client.get('/multiserver/role')
            changed = self.post('/multiserver/role', client=client, **self.confirmed(role='node'))
            if 'without a second factor' in name or 'no secret' in name:
                # A full administrator sees the role and is told what to do first, and can change nothing.
                self.assertEqual(200, shown.status_code, name)
                self.assertNotIn('name="role"', self.text(shown), name)
                self.assertIn('name="action" value="setup"', self.text(shown), name)
            else:
                self.assertEqual(404, shown.status_code, name)
            self.assertEqual(404, changed.status_code, name)
            self.assertEqual(before, self.state(), name)
        self.assertEqual([], self.commands)

    def test_a_session_that_says_it_is_a_controllers_is_shown_out(self):
        self.role.return_value = keys.NODE
        for ask in (lambda: self.client.get('/multiserver/role'), lambda: self.change('off', follow=False)):
            session = SessionStore(session_key=self.sign_in())
            session['ms_managed'] = {'link': LINK}
            session.save()
            response = ask()
            self.assertEqual((403, b'Server login unavailable'), (response.status_code, response.content[:24]))
            # The panel ended that session there and then.
            self.assertFalse(Session.objects.filter(pk=session.session_key).exists())
        self.assertEqual(([], keys.NODE), (self.commands, self.role.return_value))

    def test_looking_at_the_page_changes_nothing_and_only_get_and_post_are_answered(self):
        before = self.state()
        for unused in range(3):
            self.assertEqual(200, self.client.get('/multiserver/role').status_code)
        self.assertEqual(200, self.client.get('/multiserver/role?role=node&password=x&code=1').status_code)
        for method in ('put', 'delete', 'patch'):
            self.assertEqual(405, getattr(self.client, method)('/multiserver/role').status_code)
        self.assertEqual(before, self.state())
        self.assertEqual([], self.commands)

    def test_the_form_is_refused_without_the_token_of_the_page(self):
        strict = Client(enforce_csrf_checks=True)
        self.sign_in(strict)
        before = self.state()
        self.assertEqual(403, self.post('/multiserver/role', client=strict, **self.confirmed(role='node')).status_code)
        self.assertEqual(before[:-1], self.state()[:-1])
        self.assertEqual([], self.commands)


@unittest.skipIf(SKIP, SKIP)
class TwoFactorSetUpTests(Pages):
    """A licensed administrator without two-factor login starts using the feature on one page, without signing out."""
    ROLE, NODES = '/multiserver/role', '/multiserver/nodes'

    def setUp(self):
        super().setUp()
        self.role.return_value = keys.OFF
        Administrator.objects.filter(pk=self.administrator.pk).update(twoFA=0, secretKey='None')
        self.licensed = self.start(patch.object(entitlement, 'allowed', return_value=True))
        self.start(patch.object(keys, 'master_key', return_value=test_links.MASTER))
        # The revision of the root-owned role file, which these tests do not write: like the file, it
        # names the role, and a role set again (which raises the counter) is a new revision.
        def revision(expected):
            if self.role.return_value != expected:
                raise ValueError('Multi-Server role changed.')
            return 'revision-%d' % self.generation.return_value
        self.start(patch.object(keys, 'role_revision', side_effect=revision))

    def account(self):
        return Administrator.objects.get(pk=self.administrator.pk)

    def app_code(self):
        """What the authenticator app shows for the key of the set-up, in the next half minute."""
        import pyotp
        self.time.now += 30
        return pyotp.TOTP(self.account().secretKey).generate_otp(self.time.now // 30)

    def send(self, path=ROLE, follow=True, **fields):
        return self.client.post(path, data=fields, follow=follow, secure=True)

    def set_up(self):
        return self.text(self.send(action='setup'))

    def enrol(self, **fields):
        return self.text(self.send(**dict(dict(action='enrol', role='controller', password=PASSWORD,
                                               code=self.app_code()), **fields)))

    def nodes_page(self):
        return self.text(self.client.get(self.NODES, secure=True))

    def test_looking_at_the_page_offers_the_set_up_and_changes_nothing(self):
        before = self.state()
        page = self.text(self.client.get(self.ROLE, secure=True))
        self.assertIn('<input type="hidden" name="action" value="setup">', page)
        self.assertNotIn('<svg', page)
        self.assertNotIn('name="role"', page)
        self.assertNotIn('Get a licence for this server', page)  # this server is licensed
        self.assertEqual(before, self.state())
        self.assertEqual('None', self.account().secretKey)

    def test_one_page_switches_on_two_factor_and_makes_this_server_a_controller(self):
        page = self.set_up()
        account = self.account()
        self.assertEqual(0, account.twoFA)
        key = account.secretKey
        self.assertRegex(key, r'^[A-Z2-7]{32}$')
        self.assertIn('<svg', page)
        self.assertIn(' '.join(key[start:start + 4] for start in range(0, 32, 4)), page)
        self.assertIn('name="role" value="controller" required checked', page)
        from django.conf import settings
        session_before = self.client.cookies[settings.SESSION_COOKIE_NAME].value
        before = self.last_audit_id()
        page = self.enrol()
        self.assertIn('Two-factor login is on for your account.', page)
        self.assertIn('This server is now: Controller.', page)
        self.assertEqual((1, key), (self.account().twoFA, self.account().secretKey))
        self.assertEqual([msctl.ROLE_COMMANDS['controller']], self.commands)
        self.assertEqual([('two_factor', 'ok', '', '', 'admin'), ('role', 'ok', '', '', 'admin')],
                         self.audited(before))
        # The password and a fresh code were checked, as at sign-in: this session is such a sign-in now.
        self.assertNotEqual(session_before, self.client.cookies[settings.SESSION_COOKIE_NAME].value)
        page = self.nodes_page()
        self.assertNotIn('name="action" value="confirm"', page)
        self.assertNotIn('Get a licence for this controller', page)
        self.nowhere(PASSWORD, key)

    def test_the_code_of_the_set_up_works_once(self):
        self.set_up()
        code = self.app_code()
        self.enrol(code=code, role='node')
        self.assertEqual(keys.NODE, self.role.return_value)
        page = self.text(self.send(role='off', password=PASSWORD, code=code))
        self.assertIn(stepup.WRONG, page)
        self.assertEqual(keys.NODE, self.role.return_value)

    def test_wrong_answers_change_nothing_and_five_shut_the_set_up_out(self):
        self.set_up()
        before = self.last_audit_id()
        for name, fields in (('a wrong password', dict(password='not it')), ('no password', dict(password='')),
                             ('a wrong code', dict(code='000000')), ('no code', dict(code='')),
                             ('letters', dict(code='abcdef'))):
            page = self.enrol(**fields)
            self.assertIn(stepup.WRONG, page, name)
            self.assertEqual(0, self.account().twoFA, name)
            self.assertEqual(keys.OFF, self.role.return_value, name)
        self.assertEqual(['password', 'password', 'two_factor', 'two_factor', 'two_factor'],
                         [reason for event, outcome, reason, link, actor in self.audited(before)])
        self.assertIn(stepup.LOCKED, self.enrol())
        self.assertEqual((0, []), (self.account().twoFA, self.commands))
        self.nowhere('not it', PASSWORD)

    def test_the_set_up_is_only_for_an_account_without_two_factor_that_started_it_in_this_session(self):
        # Without a set-up started in this session, no key is taken.
        before = self.state()
        self.assertEqual(404, self.send(follow=False, action='enrol', role='controller', password=PASSWORD,
                                        code='123456').status_code)
        self.assertEqual(before, self.state())
        # A set-up started in another session is not this one's.
        self.set_up()
        other = Client()
        self.sign_in(other)
        response = other.post(self.ROLE, data=dict(action='enrol', role='controller', password=PASSWORD,
                                                   code=self.app_code()), secure=True)
        self.assertEqual(404, response.status_code)
        self.assertEqual(0, self.account().twoFA)
        # An account that has two-factor login sets nothing up here: its key stays.
        Administrator.objects.filter(pk=self.administrator.pk).update(twoFA=1, secretKey=SECRET)
        for action in ('setup', 'enrol'):
            response = self.send(follow=False, action=action, role='controller', password=PASSWORD, code=self.fresh())
            self.assertEqual(404, response.status_code, action)
            self.assertEqual((1, SECRET), (self.account().twoFA, self.account().secretKey), action)
        # A role that is not one of the three is not a request this page knows.
        Administrator.objects.filter(pk=self.administrator.pk).update(twoFA=0, secretKey='None')
        self.set_up()
        for role in ('', 'Controller', 'controller ', 'both'):
            self.assertEqual(404, self.send(follow=False, action='enrol', role=role, password=PASSWORD,
                                            code=self.app_code()).status_code, role)
        self.assertEqual((0, []), (self.account().twoFA, self.commands))

    def test_nobody_else_starts_a_set_up(self):
        for name, client in self.everyone_else():
            if 'without a second factor' in name or 'no secret' in name:
                continue  # the administrator of these tests, who may
            before = self.state()
            response = client.post(self.ROLE, data=dict(action='setup'), secure=True)
            self.assertEqual(404, response.status_code, name)
            self.assertEqual(before, self.state(), name)

    def test_a_controller_confirms_its_sign_in_on_the_list_of_its_servers(self):
        Administrator.objects.filter(pk=self.administrator.pk).update(twoFA=1, secretKey=SECRET)
        self.role.return_value = keys.CONTROLLER
        page = self.nodes_page()
        self.assertIn('<input type="hidden" name="action" value="confirm">', page)
        before = self.last_audit_id()
        page = self.text(self.send(action='confirm', password='not it', code=self.fresh()))
        self.assertIn(stepup.WRONG, page)
        self.assertIn('name="action" value="confirm"', page)  # back on the list, still asked
        # The client follows the redirect without HTTPS, where no controller sign-in counts: look again over HTTPS.
        self.assertIn(SIGNED_IN_TEXT, self.text(self.send(action='confirm', password=PASSWORD, code=self.fresh())))
        self.assertNotIn('name="action" value="confirm"', self.nodes_page())
        self.assertEqual([('sign_in', 'refused', 'password', '', 'admin'), ('sign_in', 'ok', '', '', 'admin')],
                         self.audited(before))
        self.assertEqual([], self.commands)
        # Changing the role here confirms the sign-in too.
        Session.objects.all().delete()
        self.sign_in()
        self.role.return_value = keys.OFF
        self.text(self.send(role='controller', password=PASSWORD, code=self.fresh()))
        self.assertNotIn('name="action" value="confirm"', self.nodes_page())

    def test_without_https_the_sign_in_is_not_marked(self):
        self.set_up()
        import pyotp
        self.time.now += 30
        code = pyotp.TOTP(self.account().secretKey).generate_otp(self.time.now // 30)
        page = self.text(self.client.post(self.ROLE, data=dict(action='enrol', role='controller', password=PASSWORD,
                                                               code=code), follow=True))
        self.assertIn('This server is now: Controller.', page)
        self.assertIn('name="action" value="confirm"', self.text(self.client.get(self.NODES, secure=True)))


@unittest.skipIf(SKIP, SKIP)
class ControllersPageTests(Pages):
    """A managed server: its administrator allows a controller, approves it, and ends its link."""
    CONTROL = '/multiserver/controllers/control'

    def setUp(self):
        super().setUp()
        from plogical import softUpgrade
        self.start(patch.object(pairing, '_certificate_fingerprint', return_value=PIN))
        self.start(patch.object(entitlement, 'server_address', return_value=ADDRESS))
        self.start(patch.object(softUpgrade, 'panel_endpoint', return_value=('0.0.0.0', 8090)))
        # The link of the fixture is active at the time the fixture's clock shows.
        self.start(patch.object(controllers, 'time', self.clock))

    def allow(self, controller_ip=CALLER, **fields):
        return self.post(self.CONTROL, **self.confirmed(action='allow', controller_ip=controller_ip, **fields))

    def code(self, controller_ip=CALLER):
        response = self.allow(controller_ip)
        self.assertEqual(200, response.status_code)
        (code,) = CODE.findall(self.text(response))
        return code

    def asks(self, code, source=CALLER):
        """A controller that has the code asks for a link; (link id, the number its page shows)."""
        endpoint, node_id, seed, commitment = pairing._decode(code)
        key = crypto.generate_private_key()
        fields = dict(link_id=secrets.token_hex(16), pairing_key=crypto.public_key(seed).hex(),
                      controller_key=crypto.public_key(key).hex(), node_id=node_id, tls_fingerprint=endpoint.tls_pin,
                      host=endpoint.authority, timestamp=int(time.time()), nonce=secrets.token_hex(16))
        body = '\n'.join((fields['link_id'], fields['pairing_key'], fields['controller_key'],
                          str(fields['timestamp']), fields['nonce'])).encode('ascii')
        answer = Client().generic('POST', pairing.PATH, data=body, content_type='text/plain',
                                  HTTP_X_CPMS_SIGNATURE=crypto.sign(seed, crypto.pair_request_message(**fields)).hex(),
                                  HTTP_HOST=endpoint.authority, REMOTE_ADDR=source)
        self.assertEqual(200, answer.status_code)
        node_key, value, allowed = answer.content.decode('ascii').split('\n')
        self.assertEqual(commitment, crypto.pair_commitment(value, endpoint.authority, endpoint.tls_pin, allowed))
        return fields['link_id'], pairing.confirmation_number(crypto.pair_confirmation_message(
            fields['link_id'], fields['pairing_key'], fields['controller_key'], node_key, value))

    def status(self, link_id):
        return models.Link.objects.get(pk=link_id).status

    def decide(self, action, link_id, **fields):
        return self.text(self.post(self.CONTROL, follow=True, action=action, link_id=link_id, **fields))

    def test_the_page_lists_the_links_and_looking_at_it_changes_nothing(self):
        link_id, number = self.asks(self.code())
        late = models.Link.objects.create(
            link_id='c3' * 16, controller_key='c1' * 32, pairing_key='c3' * 32, allowed_ips='198.51.100.7',
            admin_id=self.administrator.pk, status=models.PENDING, generation=1, created_at=1, updated_at=1,
            expires_at=2)
        before = self.state()
        response = self.client.get('/multiserver/controllers')
        self.assertEqual(200, response.status_code)
        page = self.text(response)
        self.assertIn('<th scope="row">127.0.0.1</th><td>%s</td><td>Active</td>' % LINK[:8], page)
        self.assertIn('<th scope="row">%s</th><td>%s</td>' % (CALLER, link_id[:8]), page)
        # Not approved in time: no longer offered, and not closed by a look.
        self.assertNotIn('<td>%s</td>' % late.link_id[:8], page)
        self.assertNotIn(number, page)
        self.assertNotIn(number[:4] + ' ' + number[4:], page)
        self.assertEqual(before, self.state())
        self.assertEqual('pending', self.status(late.link_id))
        for method in ('post', 'put', 'delete'):
            self.assertEqual(405, getattr(self.client, method)('/multiserver/controllers').status_code)
        self.assertEqual(405, self.client.get(self.CONTROL).status_code)
        self.assertEqual(405, self.client.get(self.CONTROL + '?action=reject&link_id=' + link_id).status_code)
        self.assertEqual(before, self.state())
        # The next decision anybody makes closes what ran out.
        self.decide('reject', 'ee' * 16)
        self.assertEqual('revoked', self.status(late.link_id))

    def test_a_pairing_code_is_shown_once_to_an_administrator_who_gave_the_password_and_a_new_code(self):
        before = self.last_audit_id()
        response = self.allow()
        (code,) = CODE.findall(self.text(response))
        self.assertEqual((ADDRESS, 8090, NODE, PIN), tuple(pairing.read_code(code)))
        self.assertIn('no-cache', response['Cache-Control'])
        self.assertEqual([(CALLER, self.administrator.pk, 0, 0)], list(models.PairingCode.objects.values_list(
            'controller_ip', 'admin_id', 'failures', 'consumed')))
        self.assertEqual([('pairing_code', 'ok', '', '', 'admin')], self.audited(before))
        seed = pairing._decode(code)[2]
        self.nowhere(code, seed.hex(), PASSWORD)
        self.assertNotIn(code, self.text(self.client.get('/multiserver/controllers')))
        # An IPv6 address passes the panel's request filter and is kept in its one spelling.
        self.assertEqual(1, len(CODE.findall(self.text(self.allow('2A01:04F8:0:0:0:0:0:9')))))
        self.assertEqual(['203.0.113.9', '2a01:4f8::9'],
                         sorted(models.PairingCode.objects.values_list('controller_ip', flat=True)))

    def test_no_code_is_made_without_the_password_and_a_new_code_or_for_what_is_not_one_address(self):
        used = self.fresh()
        self.assertEqual(1, len(CODE.findall(self.text(self.post(
            self.CONTROL, action='allow', controller_ip=CALLER, password=PASSWORD, code=used)))))
        before = self.last_audit_id()
        for fields in (dict(password='wrong', code=self.fresh()), dict(password=PASSWORD, code=used),
                       dict(password=PASSWORD, code='12345'), dict(code=self.fresh()), dict(password=PASSWORD)):
            page = self.text(self.post(self.CONTROL, follow=True, action='allow', controller_ip=CALLER, **fields))
            self.assertIn(stepup.WRONG, page)
            self.assertEqual([], CODE.findall(page))
        self.assertEqual([('pairing_code', 'refused', reason, '', 'admin')
                          for reason in ('password', 'two_factor', 'two_factor', 'password', 'two_factor')],
                         self.audited(before))
        self.assertEqual(1, models.PairingCode.objects.count())
        self.assertIn(stepup.LOCKED, self.text(self.post(self.CONTROL, follow=True, **self.confirmed(
            action='allow', controller_ip=CALLER))))
        Administrator.objects.filter(pk=self.administrator.pk).update(config='{}')
        # What is not one address is said at once; neither the password nor the code is looked at for it.
        kept = Administrator.objects.get(pk=self.administrator.pk).config
        for address in ('controller.example.com', '203.0.113.9/32', '203.0.113.9 203.0.113.10', '', '010.0.0.1',
                        '::ffff:203.0.113.9'):
            page = self.text(self.post(self.CONTROL, follow=True, action='allow', controller_ip=address,
                                       password='wrong', code='000000'))
            self.assertIn('The controller&#x27;s address must be one IPv4 or IPv6 address.', page, address)
        self.assertEqual((1, kept), (models.PairingCode.objects.count(),
                                     Administrator.objects.get(pk=self.administrator.pk).config))

    def test_a_server_whose_own_address_no_controller_can_reach_says_so(self):
        with patch.object(entitlement, 'server_address', return_value='10.0.0.5'):
            page = self.text(self.post(self.CONTROL, follow=True, **self.confirmed(
                action='allow', controller_ip=CALLER)))
        self.assertIn('A controller cannot reach this server at the address the panel has for it. '
                      'A link may not connect to this address (private).', page)

    def test_the_number_from_the_controller_approves_the_link_and_the_next_signed_request_is_answered(self):
        link_id, number = self.asks(self.code())
        self.assertEqual('pending', self.status(link_id))
        before = self.last_audit_id()
        page = self.decide('approve', link_id, number=number[:4] + ' ' + number[4:])
        self.assertIn('Approved. That controller now manages this server.', page)
        self.assertEqual('active', self.status(link_id))
        self.assertEqual([('link_approve', 'ok', '', link_id, 'admin')], self.audited(before))
        self.assertIn('<th scope="row">%s</th><td>%s</td><td>Active</td>' % (CALLER, link_id[:8]), page)
        self.nowhere(number, number[:4] + ' ' + number[4:])

    def test_wrong_digits_are_counted_and_the_fifth_closes_the_request(self):
        link_id, number = self.asks(self.code())
        wrong = '%08d' % ((int(number) + 1) % 10 ** 8)
        for attempt in range(1, 5):
            page = self.decide('approve', link_id, number=wrong)
            self.assertIn('This is not the number the controller shows for this link.', page)
            self.assertEqual(('pending', attempt), (self.status(link_id), models.Link.objects.get(pk=link_id).failures))
        # What is not eight digits is not counted.
        for other in ('', '1234567', '123456789', 'abcdefgh'):
            self.assertIn('The number is the eight digits the controller shows for this link.',
                          self.decide('approve', link_id, number=other))
        self.assertEqual(4, models.Link.objects.get(pk=link_id).failures)
        self.assertIn('A wrong number was typed 5 times. This link is closed; pair the two servers again.',
                      self.decide('approve', link_id, number=wrong))
        self.assertEqual('revoked', self.status(link_id))
        # Not even the right number opens it now.
        self.assertIn('This link is not waiting for a decision.', self.decide('approve', link_id, number=number))
        self.assertEqual('revoked', self.status(link_id))
        self.nowhere(number, wrong)

    def test_a_request_can_be_rejected_and_then_no_number_approves_it(self):
        link_id, number = self.asks(self.code())
        self.assertIn('Rejected. That controller was not let in.', self.decide('reject', link_id))
        self.assertEqual('revoked', self.status(link_id))
        self.assertIn('This link is not waiting for a decision.', self.decide('approve', link_id, number=number))
        self.assertIn('There is no such link.', self.decide('reject', 'ee' * 16))
        for action, link in (('approve', 'not-a-link'), ('remove', LINK), ('', LINK), ('end', 'A1' * 16)):
            self.assertEqual(404, self.post(self.CONTROL, action=action, link_id=link, number=number).status_code)

    def test_ending_an_active_link_is_done_by_root_and_its_next_signed_request_fails(self):
        self.assertEqual(200, self.call()[0].status_code)
        before = self.last_audit_id()
        page = self.text(self.post(self.CONTROL, follow=True, **self.confirmed(
            action='end', link_id=LINK, confirm='end')))
        self.assertIn('The link is ended. That controller can no longer manage this server.', page)
        self.assertEqual([msctl.revoke_command(LINK, self.administrator.pk)], self.commands)
        self.assertEqual('%s %s revoke %s %d' % (msctl.PYTHON, msctl.PROGRAM, LINK, self.administrator.pk),
                         self.commands[0])
        self.assertEqual(('revoked', True, 2), (self.status(LINK), keys.revoked(LINK), self.generation.return_value))
        self.assertEqual([('link_revoke', 'ok', '', LINK, 'admin')], self.audited(before))
        self.assertNotEqual(200, self.call()[0].status_code)
        self.assertIn('<td>Ended</td>', page)
        self.assertNotIn('name="confirm" value="end"', page)
        self.output.assert_not_called()

    def test_a_link_is_not_ended_without_the_tick_the_password_and_a_new_code(self):
        before = self.last_audit_id()
        self.assertIn('Tick the box to confirm', self.text(self.post(self.CONTROL, follow=True, **self.confirmed(
            action='end', link_id=LINK))))
        for fields in (dict(password='wrong', code=self.fresh()), dict(password=PASSWORD, code='000000')):
            self.assertIn(stepup.WRONG, self.text(self.post(self.CONTROL, follow=True, action='end', link_id=LINK,
                                                           confirm='end', **fields)))
        self.assertIn('There is no such link.', self.text(self.post(self.CONTROL, follow=True, **self.confirmed(
            action='end', link_id='ee' * 16, confirm='end'))))
        self.assertEqual([('link_revoke', 'refused', reason, link, 'admin') for reason, link in (
            ('not_allowed', LINK), ('password', LINK), ('two_factor', LINK), ('link', 'ee' * 16))],
            self.audited(before))
        self.assertEqual(([], 'active', 200), (self.commands, self.status(LINK), self.call()[0].status_code))

    def test_a_link_that_root_did_not_end_is_not_reported_as_ended(self):
        self.executioner.side_effect = lambda command, *more, **options: self.commands.append(command) or 0
        before = self.last_audit_id()
        page = self.text(self.post(self.CONTROL, follow=True, **self.confirmed(
            action='end', link_id=LINK, confirm='end')))
        self.assertIn('The link could not be ended.', page)
        self.assertEqual([('link_revoke', 'error', 'internal', LINK, 'admin')], self.audited(before))
        self.assertEqual(('active', 200), (self.status(LINK), self.call()[0].status_code))

    def test_nobody_else_gets_anything_from_these_pages(self):
        link_id, number = self.asks(self.code())
        forms = (dict(action='allow', controller_ip=CALLER), dict(action='approve', link_id=link_id, number=number),
                 dict(action='reject', link_id=link_id), dict(action='end', link_id=LINK, confirm='end'))
        for name, client in self.everyone_else():
            before = self.state()
            self.assertEqual(404, client.get('/multiserver/controllers').status_code, name)
            for form in forms:
                response = self.post(self.CONTROL, client=client, **self.confirmed(**form))
                self.assertEqual((404, []), (response.status_code, CODE.findall(self.text(response))), (name, form))
            self.assertEqual(before, self.state(), name)
        self.assertEqual(([], 'pending', 'active'), (self.commands, self.status(link_id), self.status(LINK)))
        # Without a session the panel sends a visitor to sign in, as for any address.
        self.assertEqual(302, Client().get('/multiserver/controllers').status_code)

    def test_a_form_the_request_filter_refuses_is_not_written_to_the_log(self):
        link_id, number = self.asks(self.code())
        del self.log[:]
        for form in (dict(action='allow', controller_ip='203.0.113.9;id', password='planted-password', code='314159'),
                     dict(action='approve', link_id=link_id, number=number + '$'),
                     dict(action='end', link_id=LINK, confirm='end', password='planted-password', code='314159<')):
            before = self.state()
            response = self.post(self.CONTROL, **form)
            self.assertIn('not accepted', self.text(response))
            self.assertEqual(before, self.state())
        self.assertEqual(['Rejected node control input'] * 3, self.log)
        self.nowhere('planted-password', '314159', number)
        # A password may hold any character; it is not what gets a form refused.
        self.assertEqual(1, len(CODE.findall(self.text(self.allow()))))

    def test_the_forms_are_refused_without_the_token_of_the_page(self):
        link_id, number = self.asks(self.code())
        strict = Client(enforce_csrf_checks=True)
        self.sign_in(strict)
        before = self.state()
        for form in (dict(action='allow', controller_ip=CALLER), dict(action='approve', link_id=link_id, number=number),
                     dict(action='reject', link_id=link_id), dict(action='end', link_id=LINK, confirm='end')):
            self.assertEqual(403, self.post(self.CONTROL, client=strict, **self.confirmed(**form)).status_code)
        self.assertEqual(before[:-1], self.state()[:-1])

    def test_what_a_row_holds_is_shown_as_text(self):
        Administrator.objects.filter(pk=self.administrator.pk).update(userName='<b>{$ 7*7 $}</b>')
        models.Link.objects.filter(pk=LINK).update(allowed_ips='<script>alert(1)</script>')
        page = self.text(self.client.get('/multiserver/controllers'))
        self.assertIn('&lt;b&gt;{$ 7*7 $}&lt;/b&gt;', page)
        self.assertNotIn('<b>{$', page)
        self.assertNotIn('<script>alert(1)</script>', page)
        content = page[page.index('<h1>Controllers</h1>'):]
        container = page.index('<div class="container-fluid" ng-non-bindable>')
        self.assertLess(container, page.index('<h1>Controllers</h1>'))
        self.assertLess(container, page.index('&lt;b&gt;{$'))
        self.assertNotIn('<script', content[:content.index('Role of this server')])


@unittest.skipIf(SKIP, SKIP)
class AddServerTests(Pages):
    """A controller: its administrator pastes a pairing code, sees what it says, and pairs."""
    ADD, NODES, CONTROL = '/multiserver/nodes/add', '/multiserver/nodes', '/multiserver/nodes/control'
    HELLO = b'{"build":10,"capabilities":["hello","ticket"],"role":"node","version":"3.0"}'

    def setUp(self):
        super().setUp()
        self.role.return_value = keys.CONTROLLER
        self.start(patch.object(keys, 'master_key', return_value=test_links.MASTER))
        self.licensed = self.start(patch.object(entitlement, 'allowed', return_value=True))
        self.sent = []
        self.exchange = self.start(patch.object(transport, 'exchange', side_effect=self.node_answers))
        self.seed = crypto.generate_private_key()
        self.pairing_key = crypto.public_key(self.seed).hex()
        self.value = crypto.pair_value(IDENTITY, self.pairing_key)
        self.code = pairing._encode(ADDRESS, 8090, NODE, PIN, self.seed,
                                    crypto.pair_commitment(self.value, ADDRESS + ':8090', PIN, CALLER))

    def node_answers(self, endpoint, path, body, signature):
        """The managed server the code names: it accepts the request as pairing.node_receive does."""
        link, pairing_key, controller, timestamp, nonce = body.decode('ascii').split('\n')
        request = crypto.pair_request_message(link, pairing_key, controller, NODE, PIN, endpoint.authority,
                                              int(timestamp), nonce)
        self.assertTrue(crypto.verify(bytes.fromhex(pairing_key), signature, request))
        value = crypto.pair_value(IDENTITY, pairing_key)
        self.sent.append((link, controller))
        signed = crypto.sign(IDENTITY, crypto.pair_response_message(request, NODE_KEY.hex(), value, CALLER))
        return 200, 'text/plain', '\n'.join((NODE_KEY.hex(), value, CALLER)).encode('ascii'), signed

    def read(self, **fields):
        return self.post(self.ADD, **dict(dict(step='read', label='Frankfurt 1', pairing_code=self.code), **fields))

    def connect(self, follow=True, **fields):
        return self.post(self.ADD, follow=follow, **self.confirmed(
            **dict(dict(step='connect', label='Frankfurt 1', pairing_code=self.code), **fields)))

    def number(self):
        (link_id, controller_key), = self.sent
        return pairing.confirmation_number(crypto.pair_confirmation_message(
            link_id, self.pairing_key, controller_key, NODE_KEY.hex(), self.value))

    def test_what_the_code_says_is_shown_before_anything_is_connected_or_kept(self):
        before = self.state()
        response = self.read()
        self.assertEqual(200, response.status_code)
        page = self.text(response)
        for shown in ('<td>Frankfurt 1</td>', '<td>%s</td>' % ADDRESS, '<td>8090</td>',
                      '<code>%s</code>' % ' '.join(NODE[start:start + 4] for start in range(0, 64, 4)),
                      '<code>%s</code>' % ' '.join(['d4d4'] * 16), 'Nothing has been sent yet.',
                      'name="step" value="connect"', 'name="pairing_code" value="%s"' % self.code):
            self.assertIn(shown, page)
        self.assertNotIn(self.seed.hex(), page)
        self.assertIn('no-cache', response['Cache-Control'])
        self.exchange.assert_not_called()
        self.assertEqual(before, self.state())
        self.assertEqual(0, models.AuditEntry.objects.count())
        self.nowhere(self.code)
        # A code pasted with spaces or line breaks around its groups is the same code.
        self.assertIn('<td>%s</td>' % ADDRESS, self.text(self.read(pairing_code=' ' + self.code + '  ')))

    def test_what_is_not_a_code_or_not_a_name_is_said_and_nothing_is_connected(self):
        for fields, said in ((dict(pairing_code=self.code[:-1]), 'This is not a pairing code, or not all of one.'),
                             (dict(pairing_code='CPMS1-PAIR-AAAA'), 'This is not a pairing code, or not all of one.'),
                             (dict(pairing_code=''), 'This is not a pairing code, or not all of one.'),
                             (dict(label=''), 'A label is 1 to 64 letters'), (dict(label='x' * 65), 'A label is'),
                             (dict(label='-Frankfurt'), 'A label is')):
            for step in ('read', 'connect'):
                page = self.text(self.post(self.ADD, follow=True, **self.confirmed(**dict(
                    dict(step=step, label='Frankfurt 1', pairing_code=self.code), **fields))))
                self.assertIn(said, page, (fields, step))
        private = pairing._encode('10.0.0.5', 8090, NODE, PIN, self.seed, 'e7' * 32)
        self.assertIn('A link may not connect to this address (private).',
                      self.text(self.read(pairing_code=private, follow=True)))
        self.assertEqual(404, self.read(step='pair').status_code)
        self.assertEqual(404, self.read(step='').status_code)
        self.exchange.assert_not_called()
        self.assertEqual(0, models.Node.objects.count())

    def test_with_the_password_and_a_new_code_the_servers_are_paired_and_the_number_is_shown_while_it_waits(self):
        page = self.text(self.connect())
        self.assertEqual(1, self.exchange.call_count)
        (row,) = models.Node.objects.all()
        self.assertEqual(('Frankfurt 1', 'pending', self.sent[0][0]), (row.label, row.status, row.link_id))
        number = self.number()
        shown = number[:4] + ' ' + number[4:]
        self.assertIn('Code accepted. Now, on that server', page)
        self.assertIn('Waiting for approval on that server</strong><br>Number to type there: <strong>%s</strong>' % shown, page)
        self.assertIn('name="action" value="confirm"', page)
        # It is shown again whenever the page is opened, and it is written down nowhere.
        self.assertIn(shown, self.text(self.client.get(self.NODES)))
        self.nowhere(number, shown, self.code, self.seed.hex(), self.value)
        self.assertEqual([('pairing', 'ok', '', row.link_id, 'admin')], self.audited())

    def test_nothing_is_connected_without_the_password_and_a_new_code(self):
        used = self.fresh()
        for fields in (dict(password='wrong', code=used), dict(password=PASSWORD, code='000000'),
                       dict(code=used), dict(password=PASSWORD)):
            page = self.text(self.post(self.ADD, follow=True, step='connect', label='Frankfurt 1',
                                       pairing_code=self.code, **fields))
            self.assertIn(stepup.WRONG, page)
        self.exchange.assert_not_called()
        self.assertEqual(0, models.Node.objects.count())
        self.assertEqual([('pairing', 'refused', reason, '', 'admin')
                          for reason in ('password', 'two_factor', 'password', 'two_factor')], self.audited())
        self.assertIn('Code accepted.', self.text(self.post(self.ADD, follow=True, step='connect', label='Frankfurt 1',
                                                     pairing_code=self.code, password=PASSWORD, code=used)))
        # The code that paired is not good for a second server.
        self.assertIn(stepup.WRONG, self.text(self.post(self.ADD, follow=True, step='connect', label='Second',
                                                        pairing_code=self.code, password=PASSWORD, code=used)))
        self.assertEqual(1, self.exchange.call_count)
        self.nowhere('wrong', PASSWORD, self.code)

    def test_a_refusal_of_the_pairing_is_said_in_its_fixed_words(self):
        self.licensed.return_value = False
        page = self.text(self.connect())
        self.assertIn('This server has no Multi-Server Manager licence.', page)
        self.licensed.return_value = True
        self.exchange.side_effect = transport.CertificateMismatch('other certificate')
        self.assertIn('did not present the certificate the pairing code names', self.text(self.connect()))
        self.exchange.side_effect = self.node_answers
        self.connect()
        self.assertIn('This server is already connected.', self.text(self.connect(label='Again')))
        self.assertEqual(1, models.Node.objects.count())

    def test_the_controller_asks_whether_the_link_was_approved_and_only_a_signed_answer_connects_it(self):
        self.connect()
        (row,) = models.Node.objects.all()
        with patch.object(transport, 'send', side_effect=transport.BadSignature('unsigned')) as send:
            page = self.text(self.post(self.CONTROL, follow=True, action='confirm', link_id=row.link_id))
            self.assertIn('Not connected yet. Approve the link on that server with the number shown here', page)
            self.assertEqual('pending', models.Node.objects.get(pk=row.link_id).status)
            send.side_effect = None
            send.return_value = (200, 'application/json', self.HELLO)
            page = self.text(self.post(self.CONTROL, follow=True, action='confirm', link_id=row.link_id))
            self.assertEqual(2, send.call_count)
        self.assertIn('That server approved the link. It is connected.', page)
        self.assertEqual('active', models.Node.objects.get(pk=row.link_id).status)
        self.assertNotIn('Number to type there', page)
        self.assertIsNotNone(pairing.shown_number(models.Node.objects.get(pk=row.link_id)))

    def test_only_a_post_adds_a_server_and_looking_changes_nothing(self):
        before = self.state()
        for address in (self.ADD, self.ADD + '?step=connect&label=x&pairing_code=' + self.code):
            self.assertEqual(405, self.client.get(address).status_code)
        self.assertEqual(200, self.client.get(self.NODES).status_code)
        self.assertEqual(405, self.client.get(self.CONTROL + '?action=confirm&link_id=' + LINK).status_code)
        self.assertEqual(before, self.state())
        self.exchange.assert_not_called()
        strict = Client(enforce_csrf_checks=True)
        self.sign_in(strict)
        self.assertEqual(403, self.read(client=strict).status_code)
        self.assertEqual(403, self.post(self.ADD, client=strict, **self.confirmed(
            step='connect', label='Frankfurt 1', pairing_code=self.code)).status_code)
        self.exchange.assert_not_called()

    def test_nobody_else_reads_a_code_or_pairs(self):
        for name, client in self.everyone_else():
            before = self.state()
            self.assertEqual(404, self.read(client=client).status_code, name)
            self.assertEqual(404, self.post(self.ADD, client=client, **self.confirmed(
                step='connect', label='Frankfurt 1', pairing_code=self.code)).status_code, name)
            self.assertEqual(404, client.get(self.NODES).status_code, name)
            self.assertEqual(before, self.state(), name)
        self.exchange.assert_not_called()

    def test_a_form_the_request_filter_refuses_is_not_written_to_the_log(self):
        for form in (dict(step='read', label='Frankfurt; 1', pairing_code=self.code),
                     dict(step='connect', label='Frankfurt 1', pairing_code=self.code + '$',
                          password='planted-password', code='314159')):
            self.assertIn('not accepted', self.text(self.post(self.ADD, **form)))
        self.assertEqual(['Rejected node control input'] * 2, self.log)
        self.nowhere(self.code, 'planted-password', '314159')
        self.exchange.assert_not_called()


if __name__ == '__main__':
    unittest.main()
