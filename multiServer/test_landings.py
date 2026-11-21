"""What a managed session may open or call on a managed server, checked against the panel's URL tables.

A link ends when it is paused, revoked or expired, and a login made through it
lasts five minutes. So nothing reachable through such a login may leave another
way in behind: a panel user, an ACL, a reseller setting, API access, an SSH
key, or a second login that hands out a password of the server itself.
"""
import ast
from pathlib import Path
import types
import unittest

from multiServer import landings, testing

ROOT = Path(__file__).resolve().parent.parent
LISTED = ('websiteFunctions', 'databases', 'dockerManager')

# Every route of the users application except the three that only show users.
USERS_REFUSED = frozenset('''
viewProfile createUser submitUserCreation modifyUsers fetchUserDetails saveModifications deleteUser
submitUserDeletion createNewACL createACLFunc deleteACL deleteACLFunc modifyACL fetchACLDetails
submitACLModifications changeUserACL changeACLFunc resellerCenter saveResellerChanges apiAccess
saveChangesAPIAccess controlUserState
'''.split())
# A second login, a credential of the server, a key, a shell.
SECOND_LOGINS = frozenset(
    [('databases', name) for name in ('phpMyAdmin', 'generateAccess', 'fetchDetailsPHPMYAdmin',
                                      'consumePHPMYAdminHandoff', 'validatePHPMYAdminSession')]
    + [('websiteFunctions', name) for name in ('AutoLogin', 'sshAccess', 'saveSSHAccessChanges', 'getSSHConfigs',
                                               'deleteSSHKey', 'addSSHKey', 'get_terminal_jwt')]
    + [('dockerManager', 'executeContainerCommand')])
# Called by a git host, which has no session of any kind.
NOT_FOR_A_SESSION = frozenset([('websiteFunctions', 'webhook'), ('websiteFunctions', 'gitNotify')])


def text(node):
    return node.value if hasattr(node, 'value') else node.s  # ast.Str before Python 3.8


def routes(app):
    """(application of the view, route name) of every route in one application's URL table, from its source."""
    tree = ast.parse((ROOT / app / 'urls.py').read_text())
    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for alias in node.names:
                imported[alias.asname or alias.name] = node.module.split('.')[0]
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, 'id', None) in ('path', 're_path', 'url'):
            names = [keyword.value for keyword in node.keywords if keyword.arg == 'name']
            if len(node.args) < 2 or len(names) != 1:
                raise AssertionError('%s/urls.py has a route this test cannot read (line %d)' % (app, node.lineno))
            view = node.args[1]
            module = view.value.id if isinstance(view, ast.Attribute) else view.id
            found.append((imported.get(module, app), text(names[0])))
    return found


def match(app, name, module='views'):
    return types.SimpleNamespace(func=types.SimpleNamespace(__module__='%s.%s' % (app, module)), url_name=name)


def allowed(app, name):
    return landings.native_allowed(match(app, name))


class UsersTests(unittest.TestCase):
    def test_the_users_application_is_read_only(self):
        found = routes('userManagment')
        self.assertEqual({'userManagment'}, set(app for app, _ in found))
        names = set(name for _, name in found)
        # A route that is added must be put on one side or the other here, by somebody who read it.
        self.assertEqual(names, set(landings.USERS) | USERS_REFUSED)
        self.assertEqual({'loadUsersHome', 'listUsers', 'fetchTableUsers'}, set(landings.USERS))
        for name in sorted(names):
            self.assertEqual(name in landings.USERS, allowed('userManagment', name), name)

    def test_no_user_acl_reseller_or_api_access_route_is_a_landing_page(self):
        for name in sorted(USERS_REFUSED):
            self.assertNotIn(name, landings.PAGES, name)
            self.assertNotIn(name, landings.CREATE_PAGES, name)
            self.assertNotIn(name, landings.PICKERS.values(), name)
            self.assertEqual('index', landings.destination(name), name)
            self.assertRaises(ValueError, landings.path, name)

    def test_the_forms_that_make_users_and_acls_do_not_offer_another_server(self):
        for template in ('createUser.html', 'createACL.html', 'modifyUser.html', 'modifyACL.html',
                         'apiAccess.html', 'resellerCenter.html'):
            source = ROOT / 'userManagment' / 'templates' / 'userManagment' / template
            if source.exists():
                self.assertNotIn('multiServer/selector.html', source.read_text(), template)
        self.assertTrue((ROOT / 'userManagment/templates/userManagment/createUser.html').exists())
        self.assertTrue((ROOT / 'userManagment/templates/userManagment/createACL.html').exists())


class SecondLoginTests(unittest.TestCase):
    def test_every_such_route_exists_and_is_refused(self):
        found = set(route for app in LISTED for route in routes(app))
        for app, name in sorted(SECOND_LOGINS | NOT_FOR_A_SESSION):
            self.assertIn((app, name), found, 'the URL table no longer has this route: correct the list')
            for owner in LISTED:
                self.assertFalse(allowed(owner, name), (owner, name))
            self.assertNotIn(name, landings.PAGES, name)
            self.assertNotIn(name, landings.CREATE_PAGES, name)
            self.assertNotIn(name, landings.PICKERS.values(), name)

    def test_the_view_that_shows_the_database_root_password_is_among_them(self):
        source = (ROOT / 'databases' / 'views.py').read_text()
        view = source[source.index('def fetchDetailsPHPMYAdmin('):]
        self.assertIn('/etc/cyberpanel/mysqlPassword', view[:view.index('\ndef ', 1)])
        self.assertIn(('databases', 'fetchDetailsPHPMYAdmin'), SECOND_LOGINS)
        self.assertFalse(allowed('databases', 'fetchDetailsPHPMYAdmin'))


class AllowListTests(unittest.TestCase):
    def test_every_route_of_the_three_applications_is_listed_or_refused_on_purpose(self):
        found = set(route for app in LISTED for route in routes(app))
        refused = SECOND_LOGINS | NOT_FOR_A_SESSION
        for app in LISTED:
            mine = set(name for owner, name in found if owner == app)
            self.assertEqual(mine - set(name for owner, name in refused if owner == app), set(landings.NATIVE[app]),
                             'a route of %s was added, removed or renamed: list it or refuse it' % app)
        self.assertEqual(set(LISTED), set(landings.NATIVE))
        self.assertEqual(set(LISTED), set(app for app, _ in found))

    def test_a_route_that_is_not_listed_is_refused(self):
        for app in LISTED:
            for name in ('somethingAddedLater', '', None, 'phpMyAdmin2', 'AUTOLOGIN'):
                self.assertFalse(allowed(app, name), (app, name))
        # A name is allowed for the application it is listed under, not for another.
        self.assertTrue(allowed('databases', 'listDBs'))
        self.assertFalse(allowed('websiteFunctions', 'listDBs'))
        self.assertFalse(allowed('dockerManager', 'listWebsites'))

    def test_applications_that_are_never_reached_through_a_link(self):
        for app, name in (('firewall', 'firewallHome'), ('api', 'verifyConn'), ('cloudAPI', 'router'),
                          ('multiServer', 'multiServerNodes'), ('filemanager', 'controller'),
                          ('serverStatus', 'serverStatusHome'), ('managePHP', 'installExtensions'),
                          ('WebTerminal', 'terminal'), ('loginSystem', 'verifyLogin'), ('loginSystem', 'loadLoginPage'),
                          ('serverLogs', 'logsHome'), ('pluginHolder', 'installed'), ('tuning', 'loadTuningHome')):
            self.assertFalse(allowed(app, name), (app, name))
        self.assertTrue(allowed('loginSystem', 'logout'))


SKIP = testing.unavailable()
if SKIP is None:
    testing.start_django()


@unittest.skipIf(SKIP, SKIP)
class RoutedTests(unittest.TestCase):
    """The same, asked of the URL table Django itself built."""

    def walk(self, patterns=None):
        from django.urls import get_resolver
        for entry in (get_resolver().url_patterns if patterns is None else patterns):
            if hasattr(entry, 'url_patterns'):
                for found in self.walk(entry.url_patterns):
                    yield found
            elif getattr(entry, 'callback', None) is not None:
                yield types.SimpleNamespace(func=entry.callback, url_name=entry.name)

    def test_no_route_into_the_users_application_but_the_three_that_show_users(self):
        reached = set()
        for route in self.walk():
            app = route.func.__module__.split('.')[0]
            if app == 'userManagment' and landings.native_allowed(route):
                reached.add(route.url_name)
        self.assertEqual({'loadUsersHome', 'listUsers', 'fetchTableUsers'}, reached)

    def test_the_source_reading_of_the_url_tables_agrees_with_django(self):
        tables = LISTED + ('userManagment',)
        for app in tables:
            read = set(route for table in tables for route in routes(table) if route[0] == app)
            built = set((app, route.url_name) for route in self.walk()
                        if route.func.__module__.split('.')[0] == app)
            self.assertEqual(built, read, app)

    def test_every_landing_page_can_be_opened_by_a_managed_session(self):
        from django.urls import resolve
        for page in sorted(landings.PAGES):
            self.assertTrue(landings.native_allowed(resolve(landings.path(page))), page)

    def test_no_route_that_is_allowed_names_a_second_login(self):
        for route in self.walk():
            if landings.native_allowed(route):
                self.assertNotIn(route.url_name, set(name for _, name in SECOND_LOGINS), route.func.__module__)


if __name__ == '__main__':
    unittest.main()
