"""Reseller Center saves a website limit when the owner of the user is kept.

A request that names no new owner is treated as one that names the current owner. The view and the
ownership and allowance checks it calls are read from their source and run against users held in
memory, and the page's controller is run in Node.js: none of it needs the panel's settings or a
database.
"""
import ast
import json
import re
import shutil
import subprocess
import unittest
import warnings
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'userManagment' / 'static' / 'userManagment' / 'userManagment.js'
TEMPLATE = ROOT / 'userManagment' / 'templates' / 'userManagment' / 'resellerCenter.html'

NOT_AUTHORIZED = 'You are not authorized to access this resource.'
NO_SUCH_OWNER = 'The new owner does not exist.'
NOTHING_TO_CHANGE = 'Nothing to change: no new owner and no website limit were given.'
NOT_A_LIMIT = 'The website limit is a whole number of 0 or more.'
NOT_ITSELF = 'Your own owner and website limit can only be changed by an administrator.'
OWN_OWNER = 'A user cannot be its own owner.'
NO_UNLIMITED = 'Unlimited websites can only be given under an owner that has unlimited websites.'
OVER_ALLOWANCE = "You've reached maximum websites limit as a reseller."

# Uses the Reseller Center controller the way the page does and prints the body of each request.
HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const controllers = {}, sent = [];
const page = {
    app: {controller: function (name, body) { controllers[name] = body; }},
    getCookie: function () { return 'token'; }
};
page.window = page;
vm.createContext(page);
vm.runInContext(fs.readFileSync(input.script, 'utf8'), page);
const $http = {post: function (url, data) { sent.push(JSON.stringify(data)); return {then: function () {}}; }};
input.forms.forEach(function (form) {
    const $scope = {};
    controllers.resellerCenterCTRL($scope, $http);
    Object.keys(form).forEach(function (name) { $scope[name] = form[name]; });
    $scope.saveResellerChanges();
});
process.stdout.write(JSON.stringify(sent));
"""


def load(path, name, namespace, class_name=None):
    """One function of a module that cannot be imported here, bound to the given names."""
    with warnings.catch_warnings():
        # Some files write patterns without r''; newer interpreters remark on that when parsing.
        warnings.simplefilter('ignore')
        nodes = ast.parse((ROOT / path).read_text()).body
    if class_name:
        nodes = next(n for n in nodes if isinstance(n, ast.ClassDef) and n.name == class_name).body
    function = next(n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == name)
    function.decorator_list = []
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


class Panel:
    """The users of a panel, held in memory, with the view that saves Reseller Center changes."""

    class DoesNotExist(Exception):
        pass

    def __init__(self):
        roles = {'admin': SimpleNamespace(adminStatus=1, resellerCenter=1),
                 'reseller': SimpleNamespace(adminStatus=0, resellerCenter=1),
                 'user': SimpleNamespace(adminStatus=0, resellerCenter=0)}
        self.users = {}
        # name, key, key of the owner, role, website limit, websites of its own
        for name, pk, owner, role, limit, sites in (('admin', 1, 1, 'admin', 0, 3),
                                                    ('reseller1', 4, 1, 'reseller', 20, 2),
                                                    ('reseller2', 5, 1, 'reseller', 20, 0),
                                                    ('tenant', 6, 1, 'user', 6, 1),
                                                    ('customer', 7, 4, 'user', 6, 1),
                                                    ('other', 8, 5, 'user', 6, 0),
                                                    ('orphan', 9, 99, 'user', 6, 0),
                                                    ('reseller3', 10, 1, 'reseller', 0, 0),
                                                    ('client3', 11, 10, 'user', 6, 0)):
            websites = SimpleNamespace(all=lambda sites=sites: SimpleNamespace(count=lambda: sites))
            self.users[name] = SimpleNamespace(pk=pk, userName=name, owner=owner, acl=roles[role],
                                               initWebsitesLimit=limit, websites_set=websites, save=mock.Mock())
        self.retire = mock.Mock()
        names = {'json': json, 'HttpResponse': lambda content: content,
                 'phpmyadminAccess': SimpleNamespace(retire=self.retire),
                 'Administrator': SimpleNamespace(DoesNotExist=self.DoesNotExist,
                                                  objects=SimpleNamespace(get=self.get, filter=self.filter))}
        names['ACLManager'] = SimpleNamespace(
            loadedACL=lambda pk: {'admin': self.get(pk=pk).acl.adminStatus,
                                  'resellerCenter': self.get(pk=pk).acl.resellerCenter},
            **{name: load('plogical/acl.py', name, names, 'ACLManager')
               for name in ('checkUserOwnerShip', 'websitesLimitCheck', 'isAdminACL', 'loadErrorJson')})
        self.view = load('userManagment/views.py', 'saveResellerChanges', names)

    def filter(self, **wanted):
        (field, value), = wanted.items()
        return [user for user in self.users.values() if getattr(user, field) == value]

    def get(self, **wanted):
        found = self.filter(**wanted)
        if len(found) != 1:
            raise self.DoesNotExist('Administrator matching query does not exist.')
        return found[0]

    def stored(self, name):
        user = self.users[name]
        return user.owner, user.initWebsitesLimit

    def save(self, actor, body):
        """The reply to this request body, and whether the user it names was saved."""
        if not isinstance(body, str):
            body = json.dumps(body)
        target = self.users[json.loads(body)['userToBeModified']]
        before = self.stored(target.userName)
        reply = json.loads(self.view(SimpleNamespace(session={'userID': self.users[actor].pk}, body=body)))
        saved = target.save.call_count
        target.save.reset_mock()
        if not saved:
            assert before == self.stored(target.userName), 'changed without being saved'
        assert saved == reply['status'], 'answered %r after %d saves' % (reply, saved)
        return reply


class KeptOwnerTests(unittest.TestCase):
    def setUp(self):
        self.panel = Panel()

    def assert_refused(self, message, actor, body):
        reply = self.panel.save(actor, body)
        self.assertEqual({'status': 0, 'errorMessage': message, 'error_message': message}, reply, body)

    def test_limit_is_saved_when_the_owner_is_kept(self):
        for limit, kept in ((10, {}), (11, {'newOwner': None}), (12, {'newOwner': ''}), (0, {})):
            body = dict(kept, userToBeModified='tenant', websitesLimit=limit)
            self.assertEqual({'status': 1}, self.panel.save('admin', body), body)
            self.assertEqual((1, limit), self.panel.stored('tenant'))
        self.panel.retire.assert_not_called()

    def test_digits_from_the_shortcuts_of_the_page_are_a_limit(self):
        self.assertEqual({'status': 1}, self.panel.save('admin', {'userToBeModified': 'tenant', 'websitesLimit': '50'}))
        self.assertEqual((1, 50), self.panel.stored('tenant'))

    def test_owner_chosen_by_name_works_as_before(self):
        body = {'userToBeModified': 'customer', 'newOwner': 'reseller2', 'websitesLimit': 8}
        self.assertEqual({'status': 1}, self.panel.save('admin', body))
        self.assertEqual((5, 8), self.panel.stored('customer'))
        self.panel.retire.assert_called_once_with([self.panel.users['reseller1']])
        self.panel.retire.reset_mock()
        self.assertEqual({'status': 1}, self.panel.save('admin', body))
        self.panel.retire.assert_not_called()

    def test_owner_alone_is_moved_and_the_limit_stays(self):
        for limit in ({}, {'websitesLimit': None}):
            body = dict(limit, userToBeModified='customer', newOwner='reseller2')
            self.assertEqual({'status': 1}, self.panel.save('admin', body))
            self.assertEqual((5, 6), self.panel.stored('customer'))

    def test_keeping_the_owner_is_naming_the_current_owner(self):
        for kept in ({}, {'newOwner': 'reseller1'}):
            body = dict(kept, userToBeModified='customer', websitesLimit=9)
            self.assertEqual({'status': 1}, self.panel.save('admin', body), body)
            self.assertEqual((4, 9), self.panel.stored('customer'))
            self.panel.users['customer'].initWebsitesLimit = 6
        self.panel.retire.assert_not_called()

    def test_unknown_owner_is_refused(self):
        for owner in ('ghost', ' ', 7, 0, False, ['admin'], {'userName': 'admin'}):
            for limit in ({}, {'websitesLimit': 10}):
                self.assert_refused(NO_SUCH_OWNER, 'admin', dict(limit, userToBeModified='tenant', newOwner=owner))
        self.panel.retire.assert_not_called()

    def test_kept_owner_that_is_gone_is_refused(self):
        self.assert_refused('The current owner of this user no longer exists. Choose a new owner.',
                            'admin', {'userToBeModified': 'orphan', 'websitesLimit': 10})
        self.assertEqual({'status': 1}, self.panel.save('admin', {'userToBeModified': 'orphan', 'newOwner': 'admin'}))
        self.assertEqual((1, 6), self.panel.stored('orphan'))

    def test_request_that_changes_nothing_is_refused(self):
        for body in ({}, {'newOwner': ''}, {'newOwner': None, 'websitesLimit': None}):
            self.assert_refused(NOTHING_TO_CHANGE, 'admin', dict(body, userToBeModified='tenant'))

    def test_limit_that_is_no_whole_number_is_refused_and_the_owner_stays(self):
        for limit in ('ten', '', ' 5', '-1', '1e3', '2.5', '\u0661\u0660', '\u00b2', -1, 2.5, 10.0, True, False,
                      [], [10], {}):
            self.assert_refused(NOT_A_LIMIT, 'admin', {'userToBeModified': 'tenant', 'websitesLimit': limit})
            self.assert_refused(NOT_A_LIMIT, 'admin',
                                {'userToBeModified': 'customer', 'newOwner': 'reseller2', 'websitesLimit': limit})
        self.panel.retire.assert_not_called()

    def test_super_user_is_not_modified(self):
        self.assert_refused('Super user can not be modified.', 'reseller1',
                            {'userToBeModified': 'admin', 'websitesLimit': 10})


class AuthorisationTests(unittest.TestCase):
    """Keeping the owner opens nothing that naming the current owner did not open."""

    def setUp(self):
        self.panel = Panel()

    def assert_refused(self, message, actor, body):
        reply = self.panel.save(actor, body)
        self.assertEqual({'status': 0, 'errorMessage': message, 'error_message': message}, reply, body)

    def test_user_without_reseller_center_is_refused(self):
        for body in ({'websitesLimit': 10}, {'newOwner': 'tenant', 'websitesLimit': 10}):
            self.assert_refused(NOT_AUTHORIZED, 'tenant', dict(body, userToBeModified='tenant'))

    def test_reseller_changes_own_user_within_the_allowance(self):
        # reseller1 may hand out 20: two websites of its own leave 18 for its one user.
        for kept in ({}, {'newOwner': 'reseller1'}):
            self.panel.users['customer'].initWebsitesLimit = 6
            self.assertEqual({'status': 1}, self.panel.save(
                'reseller1', dict(kept, userToBeModified='customer', websitesLimit=18)), kept)
            self.assertEqual((4, 18), self.panel.stored('customer'))
            for limit in (19, '19', 500):
                self.assert_refused(OVER_ALLOWANCE, 'reseller1',
                                    dict(kept, userToBeModified='customer', websitesLimit=limit))
            self.assertEqual((4, 18), self.panel.stored('customer'))

    def test_reseller_does_not_reach_the_user_of_another_reseller(self):
        for body in ({'websitesLimit': 1}, {'newOwner': 'reseller1', 'websitesLimit': 1},
                     {'newOwner': 'reseller1'}, {'newOwner': 'ghost'}, {}):
            self.assert_refused(NOT_AUTHORIZED, 'reseller1', dict(body, userToBeModified='other'))
        self.assert_refused(NOT_AUTHORIZED, 'reseller1', {'userToBeModified': 'orphan', 'websitesLimit': 1})

    def test_reseller_does_not_move_a_user_to_an_owner_it_does_not_control(self):
        for owner in ('reseller2', 'admin', 'other'):
            self.assert_refused(NOT_AUTHORIZED, 'reseller1',
                                {'userToBeModified': 'customer', 'newOwner': owner, 'websitesLimit': 1})
        self.assertEqual((4, 6), self.panel.stored('customer'))

    def test_reseller_does_not_change_its_own_limit_or_owner(self):
        # Kept owner, itself named as the owner, another owner; a higher limit and unlimited.
        for owner in ({}, {'newOwner': 'reseller1'}, {'newOwner': 'admin'}, {'newOwner': 'customer'}):
            for limit in ({'websitesLimit': 32}, {'websitesLimit': 0}, {'websitesLimit': 10}, {}):
                body = dict(owner, userToBeModified='reseller1', **limit)
                self.assert_refused(NOT_ITSELF, 'reseller1', body)
        self.assertEqual((1, 20), self.panel.stored('reseller1'))

    def test_reseller_does_not_make_a_user_its_own_owner(self):
        for limit in ({'websitesLimit': 6}, {}):
            self.assert_refused(OWN_OWNER, 'reseller1', dict(limit, userToBeModified='customer', newOwner='customer'))
        self.assertEqual((4, 6), self.panel.stored('customer'))

    def test_limited_reseller_does_not_give_out_unlimited(self):
        for owner in ({}, {'newOwner': 'reseller1'}, {'newOwner': ''}):
            for limit in (0, '0'):
                self.assert_refused(NO_UNLIMITED, 'reseller1',
                                    dict(owner, userToBeModified='customer', websitesLimit=limit))
        self.assertEqual((4, 6), self.panel.stored('customer'))
        # An administrator is held to the same allowance of the owner the user stays with or goes to.
        self.assert_refused(NO_UNLIMITED, 'admin', {'userToBeModified': 'customer', 'websitesLimit': 0})
        self.assert_refused(NO_UNLIMITED, 'admin', {'userToBeModified': 'tenant', 'newOwner': 'reseller2',
                                                    'websitesLimit': 0})
        self.assertEqual([(4, 6), (1, 6)], [self.panel.stored('customer'), self.panel.stored('tenant')])

    def test_unlimited_reseller_gives_out_unlimited(self):
        self.assertEqual({'status': 1}, self.panel.save('reseller3', {'userToBeModified': 'client3', 'websitesLimit': 0}))
        self.assertEqual((10, 0), self.panel.stored('client3'))

    def test_new_owner_is_held_to_what_it_really_has_given_out(self):
        # reseller2 may hand out 20 and has given 6 to its user: a user moved to it may bring 14, not 20.
        self.assert_refused(OVER_ALLOWANCE, 'admin', {'userToBeModified': 'customer', 'newOwner': 'reseller2',
                                                      'websitesLimit': 15})
        self.assertEqual((4, 6), self.panel.stored('customer'))
        self.assertEqual({'status': 1}, self.panel.save('admin', {'userToBeModified': 'customer',
                                                                  'newOwner': 'reseller2', 'websitesLimit': 14}))
        self.assertEqual((5, 14), self.panel.stored('customer'))

    def test_an_owner_that_owns_itself_does_not_count_its_own_limit_as_given_out(self):
        reseller = self.panel.users['reseller1']
        reseller.owner = reseller.pk
        # Its own limit is not one it gave out: its two websites leave 18 of its 20 for its one user.
        self.assertEqual({'status': 1}, self.panel.save('admin', {'userToBeModified': 'customer', 'websitesLimit': 18}))
        self.assert_refused(OVER_ALLOWANCE, 'admin', {'userToBeModified': 'customer', 'websitesLimit': 19})

    def test_administrator_is_held_to_the_allowance_of_the_owner_that_is_kept(self):
        self.assert_refused(OVER_ALLOWANCE, 'admin', {'userToBeModified': 'customer', 'websitesLimit': 19})
        self.assertEqual({'status': 1}, self.panel.save('admin', {'userToBeModified': 'customer', 'websitesLimit': 18}))


class PageTests(unittest.TestCase):
    def test_keeping_the_owner_is_the_empty_choice_of_the_owner_list(self):
        template = TEMPLATE.read_text()
        owners = re.search(r'<select ng-model="newOwner"[^>]*>(.*?)</select>', template, re.S).group(1)
        self.assertEqual(['<option value="">-- {% trans "Keep current owner" %} --</option>'],
                         re.findall(r'<option value=.*', owners))

    def test_shortcuts_put_numbers_into_the_number_field(self):
        # Angular leaves a number field empty, with an error in the console, when it is handed text.
        self.assertEqual(['0', '10', '50'], re.findall(r'ng-click="websitesLimit=([^"]*)"', TEMPLATE.read_text()))

    @unittest.skipUnless(shutil.which('node'), 'Node.js runs the page controller')
    def test_what_the_page_sends_for_a_kept_owner_is_saved(self):
        # Untouched, the owner list leaves nothing in the form; set back to its empty choice it leaves null.
        forms = [{'userToBeModified': 'tenant', 'websitesLimit': 10},
                 {'userToBeModified': 'tenant', 'websitesLimit': 11, 'newOwner': None},
                 {'userToBeModified': 'tenant', 'websitesLimit': '50'}]
        finished = subprocess.run(['node', '-e', HARNESS], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  universal_newlines=True, input=json.dumps({'script': str(SCRIPT), 'forms': forms}))
        self.assertEqual(0, finished.returncode, finished.stderr)
        bodies = json.loads(finished.stdout)
        self.assertEqual([['userToBeModified', 'websitesLimit'], ['newOwner', 'userToBeModified', 'websitesLimit'],
                          ['userToBeModified', 'websitesLimit']], [sorted(json.loads(body)) for body in bodies])
        panel = Panel()
        for body, limit in zip(bodies, (10, 11, 50)):
            self.assertEqual({'status': 1}, panel.save('admin', body), body)
            self.assertEqual((1, limit), panel.stored('tenant'))


if __name__ == '__main__':
    unittest.main()
