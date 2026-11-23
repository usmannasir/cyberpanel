"""Two-factor set-up on Modify User: the key for typing is the secret of the QR code beside it.

The secret is sent only while two-factor is being set up: when the box is ticked for an account
that does not have two-factor yet, and only to those who may load that account. It is never sent
for an account that has two-factor. The views are read from their source and run against
stand-ins, and the page's controller is run in Node.js: neither needs the panel's settings or a
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
from urllib.parse import parse_qs, urlparse

import pyotp

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / 'userManagment' / 'views.py'
SCRIPT = ROOT / 'userManagment' / 'static' / 'userManagment' / 'userManagment.js'
SCRIPT_COPY = ROOT / 'static' / 'userManagment' / 'userManagment.js'
TEMPLATE = ROOT / 'userManagment' / 'templates' / 'userManagment' / 'modifyUser.html'
LOADERS = [ROOT / 'baseTemplate' / 'templates' / 'baseTemplate' / 'index.html',
           ROOT / 'userManagment' / 'templates' / 'userManagment' / 'createUser.html',
           ROOT / 'userManagment' / 'templates' / 'userManagment' / 'deleteACL.html']

NOT_SET_UP = ('Two-factor was not set up: tick the box again, add the code that is shown to your '
              'authenticator app, then save.')

# Loads the script with stand-ins for the browser and Angular and uses the Modify User controller the
# way the page does. Each step is one thing a person does, or the server answering the oldest request
# still open; after each step it records what the page holds.
HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const controllers = {}, drawn = [], sent = [], open = [];
const page = {
    app: {controller: function (name, body) { controllers[name] = body; }},
    QRious: function () { this.set = function (options) { drawn.push(options.value); }; },
    document: {getElementById: function () { return {}; }},
    getCookie: function () { return 'token'; },
    alert: function () {}
};
page.window = page;
vm.createContext(page);
vm.runInContext(fs.readFileSync(input.script, 'utf8'), page);
const $scope = {};
const $http = {post: function (url, data) {
    sent.push({url: url, data: JSON.parse(JSON.stringify(data))});
    return {then: function (done, failed) { open.push({done: done, failed: failed}); }};
}};
controllers.modifyUser($scope, $http);
const seen = input.steps.map(function (step) {
    if (step[0] === 'choose') { $scope.accountUsername = step[1]; $scope.fetchUserDetails(); }
    if (step[0] === 'box') { $scope.twofa = step[1]; $scope.decideQRShow(); }
    if (step[0] === 'answer') { open.shift().done({data: step[1]}); }
    if (step[0] === 'unreachable') { open.shift().failed({}); }
    if (step[0] === 'save') { $scope.modifyUser(); }
    return {key: $scope.secretKey, shown: $scope.formattedSecretKey, codeHidden: $scope.qrHidden,
            ticked: $scope.twofa, note: Boolean($scope.twofa && $scope.twofaEnrolled),
            drawn: drawn.length ? drawn[drawn.length - 1] : null, draws: drawn.length,
            error: $scope.canotFetchDetails === false ? $scope.errorMessage : null,
            unreachable: $scope.couldNotConnect === false, sent: sent.length, open: open.length};
});
process.stdout.write(JSON.stringify({seen: seen, sent: sent,
                                     keys: input.addresses.map(page.manualKeyFromOtpauth)}));
"""


def load_view(name, namespace):
    """One view of `userManagment/views.py`, which cannot be imported here, bound to the given names."""
    with warnings.catch_warnings():
        # The file writes some patterns without r''; newer interpreters remark on that when parsing.
        warnings.simplefilter('ignore')
        tree = ast.parse(VIEWS.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(VIEWS), 'exec'), namespace)
    return namespace[name]


def stored_user(name, secret, twofa=0, owner=1, pk=2):
    return SimpleNamespace(id=pk, pk=pk, owner=owner, userName=name, firstName='Site', lastName='Owner',
                           email=name + '+otp@example.invalid', initWebsitesLimit=10, secretKey=secret,
                           acl=SimpleNamespace(name='user'), securityLevel=0, twoFA=twofa, password='hash',
                           save=mock.Mock())


def call(name, user, body, actor=1, admin=True):
    """What the view answers to this request body about this stored user."""
    users = mock.Mock()
    users.objects.get.side_effect = [user, SimpleNamespace(pk=actor)]
    view = load_view(name, {
        'json': json,
        'Administrator': users,
        'ACLManager': SimpleNamespace(loadedACL=lambda pk: {'admin': int(admin)}),
        'SecurityLevel': lambda level: SimpleNamespace(name='HIGH'),
        'secMiddleware': SimpleNamespace(LOW=1, HIGH=0),
        'hashPassword': mock.Mock(),
        'HttpResponse': lambda content: content,
    })
    request = SimpleNamespace(method='POST', session={'userID': actor}, body=json.dumps(body))
    return json.loads(view(request))


def details(user, set_up=False, actor=1, admin=True):
    body = {'accountUsername': user.userName}
    if set_up:
        body['twofaSetup'] = True
    return call('fetchUserDetails', user, body, actor, admin)


def save(user, twofa, actor=1, admin=True):
    return call('saveModifications', user, {'accountUsername': user.userName, 'firstName': 'Site',
                                            'lastName': 'Owner', 'email': user.email, 'twofa': twofa},
                actor, admin)


def secret_of(reply):
    return parse_qs(urlparse(reply['userDetails']['otpauth']).query)['secret']


class ReplyTests(unittest.TestCase):
    def test_loading_an_account_sends_no_secret_and_makes_none(self):
        # An account that never had a set-up keeps 'None' as its secret: nothing is made for it.
        for user in (stored_user('fresh', 'None'), stored_user('started', pyotp.random_base32()),
                     stored_user('enrolled', pyotp.random_base32(), twofa=1)):
            reply = details(user)
            self.assertEqual(1, reply['fetchStatus'], user.userName)
            self.assertNotIn('otpauth', reply['userDetails'])
            if user.userName == 'fresh':
                self.assertEqual('None', user.secretKey)
            else:
                self.assertNotIn(user.secretKey, json.dumps(reply))
            user.save.assert_not_called()

    def test_set_up_stores_one_secret_and_sends_it_once_inside_the_address_of_the_code(self):
        user = stored_user('fresh', 'None')
        reply = details(user, set_up=True)
        self.assertNotEqual('None', user.secretKey)
        self.assertEqual([user.secretKey], secret_of(reply))
        self.assertEqual(user.secretKey, pyotp.parse_uri(reply['userDetails']['otpauth']).secret)
        address = reply['userDetails'].pop('otpauth')
        self.assertNotIn(user.secretKey, json.dumps(reply))
        self.assertIn('CyberPanel', address)
        user.save.assert_called_once_with()
        # Asked again before saving, it is the same secret: the code already scanned stays right.
        stored = user.secretKey
        user.save.reset_mock()
        self.assertEqual([stored], secret_of(details(user, set_up=True)))
        user.save.assert_not_called()

    def test_account_with_two_factor_never_sends_its_secret(self):
        user = stored_user('enrolled', pyotp.random_base32(), twofa=1)
        for set_up in (False, True):
            reply = details(user, set_up=set_up)
            self.assertEqual(1, reply['fetchStatus'])
            self.assertNotIn('otpauth', reply['userDetails'])
            self.assertNotIn(user.secretKey, json.dumps(reply))
        user.save.assert_not_called()

    def test_set_up_is_asked_for_only_by_name(self):
        for flag in (1, '1', 'true', [True], {'x': 1}, None, False):
            user = stored_user('fresh', 'None')
            reply = call('fetchUserDetails', user, {'accountUsername': 'fresh', 'twofaSetup': flag})
            self.assertNotIn('otpauth', reply['userDetails'], flag)
            user.save.assert_not_called()

    def test_set_up_goes_only_to_the_account_its_owner_and_an_administrator(self):
        for actor, owner, admin in ((1, 99, True), (5, 5, False), (2, 99, False)):
            user = stored_user('fresh', 'None', owner=owner)
            reply = details(user, True, actor, admin)
            self.assertEqual([user.secretKey], secret_of(reply), (actor, owner, admin))
        user = stored_user('fresh', 'None', owner=99)
        reply = details(user, True, actor=5, admin=False)
        self.assertEqual({'fetchStatus': 0, 'error_message': 'Un-authorized access.'}, reply)
        self.assertEqual('None', user.secretKey)
        user.save.assert_not_called()

    def test_the_view_writes_nothing_of_the_secret_to_a_log(self):
        tree = ast.parse(VIEWS.read_text())
        view = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'fetchUserDetails')
        called = {ast.unparse(node.func) if hasattr(ast, 'unparse') else '' for node in ast.walk(view)
                  if isinstance(node, ast.Call)}
        self.assertFalse([name for name in called if re.search(r'log|print|write', name, re.I)], called)


class SaveTests(unittest.TestCase):
    def test_two_factor_is_not_switched_on_without_a_set_up(self):
        user = stored_user('fresh', 'None')
        self.assertEqual({'status': 0, 'saveStatus': 0, 'error_message': NOT_SET_UP}, save(user, 1))
        self.assertEqual((0, 'None'), (user.twoFA, user.secretKey))
        user.save.assert_not_called()

    def test_two_factor_is_switched_on_with_the_secret_of_the_set_up(self):
        user = stored_user('fresh', 'None')
        details(user, set_up=True)
        secret = user.secretKey
        self.assertEqual(1, save(user, 1)['saveStatus'])
        self.assertEqual((1, secret), (user.twoFA, user.secretKey))

    def test_switching_off_discards_the_secret_and_kept_two_factor_is_saved(self):
        user = stored_user('enrolled', pyotp.random_base32(), twofa=1)
        secret = user.secretKey
        self.assertEqual(1, save(user, 1)['saveStatus'])
        self.assertEqual((1, secret), (user.twoFA, user.secretKey))
        self.assertEqual(1, save(user, 0)['saveStatus'])
        self.assertEqual((0, 'None'), (user.twoFA, user.secretKey))


class PageTests(unittest.TestCase):
    def test_both_copies_of_the_script_are_the_same(self):
        self.assertEqual(SCRIPT.read_bytes(), SCRIPT_COPY.read_bytes())

    def test_every_page_loads_the_script_under_the_same_new_address(self):
        found = [re.findall(r"userManagment/userManagment\.js' %\}\?v=\{\{ CP_VERSION \}\}([^\"]*)\"",
                            path.read_text()) for path in LOADERS]
        self.assertEqual(1, len({suffix for each in found for suffix in each}), found)
        self.assertTrue(all(len(each) == 1 for each in found), found)
        self.assertNotIn('-acl-permissions', found[0])

    def test_key_field_sits_with_the_code_behind_the_two_factor_box(self):
        template = TEMPLATE.read_text()
        box = re.search(r'<input\b[^>]*ng-model="twofa"[^>]*>', template).group(0)
        self.assertIn('ng-change="decideQRShow()"', box)
        hidden = template[template.index('<div ng-hide="qrHidden"'):]
        hidden = hidden[:hidden.index('ng-click="modifyUser()"')]
        self.assertIn('<canvas id="qr">', hidden)
        self.assertIn('ng-model="formattedSecretKey"', hidden)
        self.assertEqual(1, template.count('formattedSecretKey'))
        self.assertIn('ng-show="twofa && twofaEnrolled"', template)


@unittest.skipUnless(shutil.which('node'), 'Node.js runs the page controller')
class ControllerTests(unittest.TestCase):
    def run_page(self, steps, addresses=()):
        finished = subprocess.run(
            ['node', '-e', HARNESS], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
            input=json.dumps({'script': str(SCRIPT), 'steps': steps, 'addresses': list(addresses)}))
        if finished.returncode != 0:
            raise AssertionError(finished.stderr)
        return json.loads(finished.stdout)

    def test_first_set_up_shows_the_key_of_the_code(self):
        user = stored_user('fresh', 'None')
        loaded = details(user)
        set_up = details(user, set_up=True)
        page = self.run_page([['choose', 'fresh'], ['answer', loaded], ['box', True], ['answer', set_up],
                              ['box', False], ['box', True]])
        self.assertEqual([{'url': '/users/fetchUserDetails', 'data': {'accountUsername': 'fresh'}},
                          {'url': '/users/fetchUserDetails', 'data': {'accountUsername': 'fresh', 'twofaSetup': True}}],
                         page['sent'])
        chosen, answered, ticked, shown, unticked, again = page['seen']
        # Loading the account draws no code and holds no key.
        self.assertEqual(('', True, 0), (answered['key'], answered['codeHidden'], answered['draws']))
        self.assertEqual((True, 2), (ticked['codeHidden'], ticked['sent']))
        self.assertEqual(user.secretKey, shown['key'])
        self.assertEqual(set_up['userDetails']['otpauth'], shown['drawn'])
        self.assertEqual(user.secretKey, shown['shown'].replace(' ', ''))
        self.assertTrue(all(len(group) == 4 for group in shown['shown'].split(' ')), shown['shown'])
        self.assertTrue(pyotp.TOTP(shown['shown'].replace(' ', '')).verify(pyotp.TOTP(user.secretKey).now()))
        self.assertFalse(shown['codeHidden'])
        self.assertTrue(unticked['codeHidden'])
        # Ticked again, the same code and key are shown without asking again.
        self.assertEqual((False, user.secretKey, 2), (again['codeHidden'], again['key'], again['sent']))

    def test_account_with_two_factor_shows_a_note_and_no_code(self):
        user = stored_user('enrolled', pyotp.random_base32(), twofa=1)
        page = self.run_page([['choose', 'enrolled'], ['answer', details(user)], ['box', False], ['box', True]])
        self.assertEqual(1, len(page['sent']))
        for seen in page['seen'][1:]:
            self.assertEqual(('', True, 0), (seen['key'], seen['codeHidden'], seen['draws']))
        self.assertEqual([True, False, True], [seen['note'] for seen in page['seen'][1:]])

    def test_re_enrolment_after_switching_off_shows_the_new_key(self):
        user = stored_user('enrolled', pyotp.random_base32(), twofa=1)
        old = user.secretKey
        loaded = details(user)
        save(user, 0)
        reloaded = details(user)
        set_up = details(user, set_up=True)
        self.assertNotEqual(old, user.secretKey)
        page = self.run_page([['choose', 'enrolled'], ['answer', loaded], ['box', False], ['save'],
                              ['answer', {'status': 1, 'saveStatus': 1}], ['choose', 'enrolled'],
                              ['answer', reloaded], ['box', True], ['answer', set_up]])
        last = page['seen'][-1]
        self.assertEqual((user.secretKey, False, set_up['userDetails']['otpauth']),
                         (last['key'], last['codeHidden'], last['drawn']))
        self.assertEqual({'accountUsername': 'enrolled', 'twofaSetup': True}, page['sent'][-1]['data'])

    def test_answer_for_an_account_no_longer_chosen_is_dropped(self):
        first, second = stored_user('first', 'None'), stored_user('second', 'None', pk=3)
        page = self.run_page([['choose', 'first'], ['answer', details(first)], ['box', True],
                              ['choose', 'second'], ['answer', details(first, set_up=True)],
                              ['answer', details(second)]])
        for seen in page['seen'][3:]:
            self.assertEqual(('', True, 0), (seen['key'], seen['codeHidden'], seen['draws']))
        self.assertFalse(page['seen'][-1]['ticked'])

    def test_refused_or_failed_set_up_unticks_the_box_and_says_why(self):
        user = stored_user('fresh', 'None')
        refused = {'fetchStatus': 0, 'error_message': 'Un-authorized access.'}
        page = self.run_page([['choose', 'fresh'], ['answer', details(user)], ['box', True], ['answer', refused],
                              ['box', True], ['unreachable'], ['box', True], ['answer', details(user, True)]])
        refusal, unreachable, last = page['seen'][3], page['seen'][5], page['seen'][7]
        self.assertEqual((False, 'Un-authorized access.', True, ''),
                         (refusal['ticked'], refusal['error'], refusal['codeHidden'], refusal['key']))
        self.assertEqual((False, True, True), (unreachable['ticked'], unreachable['unreachable'], unreachable['codeHidden']))
        # Asking again after a failure works.
        self.assertEqual((user.secretKey, False, None), (last['key'], last['codeHidden'], last['error']))

    def test_saving_takes_the_key_off_the_page(self):
        user = stored_user('fresh', 'None')
        page = self.run_page([['choose', 'fresh'], ['answer', details(user)], ['box', True],
                              ['answer', details(user, True)], ['save'], ['answer', {'status': 1, 'saveStatus': 1}]])
        self.assertEqual({'accountUsername': 'fresh', 'firstName': 'Site', 'lastName': 'Owner',
                          'email': user.email, 'securityLevel': 'HIGH', 'twofa': True},
                         page['sent'][-1]['data'])
        self.assertEqual(('', True), (page['seen'][-1]['key'], page['seen'][-1]['codeHidden']))

    def test_key_is_read_from_the_secret_of_an_address_only(self):
        secret = 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP'
        named = pyotp.TOTP(secret).provisioning_uri(name='a?secret=AAAA&b@example.invalid', issuer_name='CyberPanel')
        addresses = [named, 'otpauth://totp/CyberPanel:x?issuer=CyberPanel&secret=' + secret + '&digits=6',
                     'otpauth://totp/x?secret=ABCD%3D%3D', 'otpauth://totp/x?issuer=CyberPanel', '', None, 7]
        self.assertEqual([secret, secret, 'ABCD==', '', '', '', ''], self.run_page([], addresses)['keys'])


if __name__ == '__main__':
    unittest.main()
