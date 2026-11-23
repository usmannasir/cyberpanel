"""The key shown for typing into an authenticator app is the secret of the QR code beside it.

The page takes the key from the `otpauth` address the QR code is drawn from, so the reply for a
user carries the secret once and the two cannot differ. The view is read from its source and run
against stand-ins, and the page's controller is run in Node.js: neither needs the panel's settings
or a database.
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
SCRIPT = ROOT / 'userManagment' / 'static' / 'userManagment' / 'userManagment.js'
SCRIPT_COPY = ROOT / 'static' / 'userManagment' / 'userManagment.js'
TEMPLATE = ROOT / 'userManagment' / 'templates' / 'userManagment' / 'modifyUser.html'

# Loads the script with stand-ins for the browser and Angular, then uses the Modify User controller
# the way the page does: load an account, look at what is shown, tick the two-factor box.
HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const controllers = {}, drawn = [];
const page = {
    app: {controller: function (name, body) { controllers[name] = body; }},
    QRious: function () { this.set = function (options) { drawn.push(options.value); }; },
    document: {getElementById: function () { return {}; }},
    getCookie: function () { return 'token'; }
};
page.window = page;
vm.createContext(page);
vm.runInContext(fs.readFileSync(input.script, 'utf8'), page);
const replies = input.replies.slice(), $scope = {};
const $http = {post: function () { return {then: function (done) { done({data: replies.shift()}); }}; }};
controllers.modifyUser($scope, $http);
const before = {hidden: $scope.qrHidden, key: $scope.secretKey, shown: $scope.formattedSecretKey};
const loads = input.replies.map(function () {
    $scope.fetchUserDetails();
    const loaded = {key: $scope.secretKey, shown: $scope.formattedSecretKey, hidden: $scope.qrHidden,
                    ticked: $scope.twofa, drawn: drawn[drawn.length - 1], form: !$scope.acctDetailsFetched};
    $scope.twofa = true;
    $scope.decideQRShow();
    loaded.hiddenOnceTicked = $scope.qrHidden;
    return loaded;
});
process.stdout.write(JSON.stringify({before: before, loads: loads,
                                     keys: input.addresses.map(page.manualKeyFromOtpauth)}));
"""


def load_view(name, namespace):
    """One view of `userManagment/views.py`, which cannot be imported here, bound to the given names."""
    path = ROOT / 'userManagment' / 'views.py'
    with warnings.catch_warnings():
        # The file writes some patterns without r''; newer interpreters remark on that when parsing.
        warnings.simplefilter('ignore')
        tree = ast.parse(path.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


def user_details_reply(user, actor=1, admin=True):
    """What `fetchUserDetails` answers for this stored user."""
    users = mock.Mock()
    users.objects.get.side_effect = [user, SimpleNamespace(pk=actor)]
    view = load_view('fetchUserDetails', {
        'json': json,
        'Administrator': users,
        'ACLManager': SimpleNamespace(loadedACL=lambda pk: {'admin': int(admin)}),
        'SecurityLevel': lambda level: SimpleNamespace(name='HIGH'),
        'HttpResponse': lambda content: content,
    })
    request = SimpleNamespace(method='POST', session={'userID': actor},
                              body=json.dumps({'accountUsername': user.userName}))
    return json.loads(view(request))


def stored_user(name, secret, twofa=0, owner=1, pk=2):
    return SimpleNamespace(id=pk, pk=pk, owner=owner, userName=name, firstName='Site', lastName='Owner',
                           email=name + '+otp@example.invalid', initWebsitesLimit=10, secretKey=secret,
                           acl=SimpleNamespace(name='user'), securityLevel=0, twoFA=twofa, save=mock.Mock())


def on_the_page(replies, addresses=()):
    """What the Modify User page holds after each of these replies, and the key it reads from each address."""
    finished = subprocess.run(
        ['node', '-e', HARNESS], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
        input=json.dumps({'script': str(SCRIPT), 'replies': replies, 'addresses': list(addresses)}))
    if finished.returncode != 0:
        raise AssertionError(finished.stderr)
    return json.loads(finished.stdout)


class ReplyTests(unittest.TestCase):
    def test_secret_goes_out_once_inside_the_address_of_the_code(self):
        user = stored_user('first', pyotp.random_base32())
        reply = user_details_reply(user)
        self.assertEqual(1, reply['fetchStatus'])
        address = reply['userDetails'].pop('otpauth')
        self.assertEqual([user.secretKey], parse_qs(urlparse(address).query)['secret'])
        self.assertNotIn(user.secretKey, json.dumps(reply))
        user.save.assert_not_called()

    def test_first_set_up_stores_the_secret_it_sends(self):
        user = stored_user('first', 'None')
        address = user_details_reply(user)['userDetails']['otpauth']
        self.assertNotEqual('None', user.secretKey)
        self.assertEqual([user.secretKey], parse_qs(urlparse(address).query)['secret'])
        user.save.assert_called_once_with()

    def test_only_the_user_the_owner_and_an_administrator_are_answered(self):
        secret = pyotp.random_base32()
        for actor, owner, admin in ((1, 99, True), (5, 5, False), (2, 99, False)):
            reply = user_details_reply(stored_user('first', secret, owner=owner), actor=actor, admin=admin)
            self.assertIn(secret, reply['userDetails']['otpauth'], (actor, owner, admin))
        user = stored_user('first', 'None', owner=99)
        reply = user_details_reply(user, actor=5, admin=False)
        self.assertEqual({'fetchStatus': 0, 'error_message': 'Un-authorized access.'}, reply)
        self.assertEqual('None', user.secretKey)
        user.save.assert_not_called()


class PageTests(unittest.TestCase):
    def test_both_copies_of_the_script_are_the_same(self):
        self.assertEqual(SCRIPT.read_bytes(), SCRIPT_COPY.read_bytes())

    def test_key_field_sits_with_the_code_behind_the_two_factor_box(self):
        template = TEMPLATE.read_text()
        box = re.search(r'<input\b[^>]*ng-model="twofa"[^>]*>', template).group(0)
        self.assertIn('ng-change="decideQRShow()"', box)
        hidden = template[template.index('<div ng-hide="qrHidden"'):]
        hidden = hidden[:hidden.index('ng-click="modifyUser()"')]
        self.assertIn('<canvas id="qr">', hidden)
        self.assertIn('ng-model="formattedSecretKey"', hidden)
        self.assertEqual(1, template.count('formattedSecretKey'))
        self.assertNotIn('secretKey', template.replace('formattedSecretKey', '').replace('copySecretKey', ''))


@unittest.skipUnless(shutil.which('node'), 'Node.js runs the page controller')
class ControllerTests(unittest.TestCase):
    def test_key_is_the_secret_of_the_code_for_every_account_loaded(self):
        first, second = stored_user('first', 'None'), stored_user('second', pyotp.random_base32(), twofa=1)
        replies = [user_details_reply(first), user_details_reply(second)]
        page = on_the_page(replies)
        self.assertEqual({'hidden': True}, page['before'])
        self.assertNotEqual(first.secretKey, second.secretKey)
        for user, reply, load in zip((first, second), replies, page['loads']):
            address = reply['userDetails']['otpauth']
            self.assertEqual(address, load['drawn'], user.userName)
            self.assertEqual(pyotp.parse_uri(address).secret, load['key'], user.userName)
            self.assertEqual(user.secretKey, load['key'], user.userName)
            self.assertEqual(user.secretKey, load['shown'].replace(' ', ''), user.userName)
            self.assertTrue(all(len(group) == 4 for group in load['shown'].split(' ')), load['shown'])
            self.assertTrue(pyotp.TOTP(load['shown'].replace(' ', '')).verify(pyotp.TOTP(user.secretKey).now()))
            # Nothing of it is on show until the box is ticked for this account, enrolled or not.
            self.assertEqual((True, True, False), (load['form'], load['hidden'], load['hiddenOnceTicked']))
        self.assertEqual([False, True], [load['ticked'] for load in page['loads']])

    def test_refused_account_shows_no_form_and_draws_no_code(self):
        refused = user_details_reply(stored_user('other', 'None', owner=99), actor=5, admin=False)
        load = on_the_page([refused])['loads'][0]
        self.assertEqual((False, None, None, None),
                         (load['form'], load.get('key'), load.get('shown'), load.get('drawn')))

    def test_key_is_read_from_the_secret_of_an_address_only(self):
        secret = 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP'
        named = pyotp.TOTP(secret).provisioning_uri(name='a?secret=AAAA&b@example.invalid', issuer_name='CyberPanel')
        addresses = [named, 'otpauth://totp/CyberPanel:x?issuer=CyberPanel&secret=' + secret + '&digits=6',
                     'otpauth://totp/x?secret=ABCD%3D%3D', 'otpauth://totp/x?issuer=CyberPanel', '', None, 7]
        self.assertEqual([secret, secret, 'ABCD==', '', '', '', ''], on_the_page([], addresses)['keys'])


if __name__ == '__main__':
    unittest.main()
