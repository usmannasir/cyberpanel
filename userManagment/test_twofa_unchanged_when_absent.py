"""Saving a user changes two-factor only when the request asks for it.

`cyberpanel editUser` and the cloud API call `saveModifications` without `twofa`; such a save leaves
two-factor on or off as it is, with its secret. The view is read from its source and run against
stand-ins: it needs neither the panel's settings nor a database.
"""
import ast
import json
import re
import unittest
import warnings
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SECRET = 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP'
BAD_VALUE = 'twofa is 1 to switch two-factor on or 0 to switch it off.'


def load_view(path, name, namespace):
    """One function of a module that cannot be imported here, bound to the given names."""
    with warnings.catch_warnings():
        # The file writes some patterns without r''; newer interpreters remark on that when parsing.
        warnings.simplefilter('ignore')
        tree = ast.parse((ROOT / path).read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


def stored_user(twofa, secret):
    return SimpleNamespace(pk=2, owner=1, userName='site-owner', twoFA=twofa, secretKey=secret,
                           securityLevel=0, password='hash', save=mock.Mock())


def save(user, request):
    users = mock.Mock()
    users.objects.get.side_effect = [user, SimpleNamespace(pk=1)]
    view = load_view('userManagment/views.py', 'saveModifications', {
        'json': json,
        'Administrator': users,
        'ACLManager': SimpleNamespace(loadedACL=lambda pk: {'admin': 1}),
        'secMiddleware': SimpleNamespace(LOW=1, HIGH=0),
        'hashPassword': mock.Mock(),
        'HttpResponse': lambda content: SimpleNamespace(content=content.encode()),
    })
    return json.loads(view(request).content)


def command_line(**extra):
    """The data `cyberpanel editUser` hands to the view (cli/cyberPanel.py, editUser)."""
    data = {'accountUsername': 'site-owner', 'firstName': 'Site', 'lastName': 'Owner',
            'email': 'owner@example.invalid', 'passwordByPass': 'new-password', 'securityLevel': 'HIGH',
            'userID': 1}
    data.update(extra)
    return data


def over_http(**extra):
    """A request of the Modify User page or the cloud API, with this JSON body."""
    body = {'accountUsername': 'site-owner', 'firstName': 'Site', 'lastName': 'Owner',
            'email': 'owner@example.invalid', 'securityLevel': 'HIGH'}
    body.update(extra)
    return SimpleNamespace(session={'userID': 1}, body=json.dumps(body))


class AbsentTwoFactorTests(unittest.TestCase):
    def test_command_line_edit_leaves_two_factor_and_its_secret(self):
        for twofa, secret in ((1, SECRET), (0, SECRET), (0, 'None')):
            user = stored_user(twofa, secret)
            self.assertEqual(1, save(user, command_line())['saveStatus'])
            user.save.assert_called_once_with()
            self.assertEqual((twofa, secret), (user.twoFA, user.secretKey))

    def test_request_without_twofa_or_with_null_leaves_it(self):
        for request in (over_http(), over_http(twofa=None)):
            user = stored_user(1, SECRET)
            self.assertEqual(1, save(user, request)['saveStatus'])
            self.assertEqual((1, SECRET), (user.twoFA, user.secretKey))

    def test_the_command_line_has_no_two_factor_option(self):
        source = (ROOT / 'cli' / 'cyberPanel.py').read_text()
        block = source[source.index('args.function == "editUser"'):]
        block = block[:block.index('saveModifications(data)')]
        self.assertNotIn('twofa', block.lower())


class ExplicitTwoFactorTests(unittest.TestCase):
    def test_switching_off_discards_the_secret(self):
        for value in (0, False, '0'):
            for request in (over_http(twofa=value), command_line(twofa=value)):
                user = stored_user(1, SECRET)
                self.assertEqual(1, save(user, request)['saveStatus'], value)
                self.assertEqual((0, 'None'), (user.twoFA, user.secretKey), value)

    def test_keeping_it_on_keeps_the_secret(self):
        for value in (1, True, '1'):
            user = stored_user(1, SECRET)
            self.assertEqual(1, save(user, over_http(twofa=value))['saveStatus'], value)
            self.assertEqual((1, SECRET), (user.twoFA, user.secretKey), value)

    def test_value_that_is_not_on_or_off_is_refused_and_nothing_changes(self):
        for value in ('true', 'yes', '', 2, -1, 0.5, [], [1], {}):
            user = stored_user(1, SECRET)
            reply = save(user, over_http(twofa=value))
            self.assertEqual({'status': 0, 'saveStatus': 0, 'error_message': BAD_VALUE}, reply, value)
            user.save.assert_not_called()
            self.assertEqual((1, SECRET), (user.twoFA, user.secretKey), value)


class SourceTests(unittest.TestCase):
    def test_no_other_default_switches_two_factor_off(self):
        tree = ast.parse((ROOT / 'userManagment' / 'views.py').read_text())
        view = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'saveModifications')
        source = ast.get_source_segment((ROOT / 'userManagment' / 'views.py').read_text(), view) \
            if hasattr(ast, 'get_source_segment') else ''
        self.assertFalse(re.search(r'twofa\s*=\s*0\b', source), 'a default of 0 switches two-factor off')


if __name__ == '__main__':
    unittest.main()
