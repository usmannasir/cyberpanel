"""An ACL holds what its form showed: the pages, the controller and the stored configuration name the same permissions."""
import ast
import json
import re
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from plogical.aclPermissions import (
    ABSENT_FROM_OLDER_ACLS, PERMISSIONS, effective_config, granted, stored_config, stored_permission)


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'userManagment' / 'templates' / 'userManagment'
SCRIPT = ROOT / 'userManagment' / 'static' / 'userManagment' / 'userManagment.js'
SCRIPT_COPY = ROOT / 'static' / 'userManagment' / 'userManagment.js'

# What the Create ACL page of 3.0.12 sent when every box it showed was cleared and only
# List Users was ticked: the three permissions it had no box for went along as granted.
HIDDEN_ON_OLD_CREATE_PAGE = ('createBackup', 'googleDriveBackups', 'manageSSL')


def checkboxes(template):
    """The names the checkboxes of a page are bound to, in page order."""
    names = []
    for tag in re.findall(r'<input\b[^>]*>', (TEMPLATES / template).read_text()):
        if 'type="checkbox"' in tag:
            names.append(re.search(r'ng-model="(\w+)"', tag).group(1))
    return names


def controller_defaults():
    """The permissions the controllers know, with the value each has on a new ACL."""
    script = SCRIPT.read_text()
    block = re.search(r'var aclPermissionDefaults = \{(.*?)\n\};', script, re.S).group(1)
    block = re.sub(r'//[^\n]*', '', block)
    entries = [entry.strip() for entry in block.split(',') if entry.strip()]
    pairs = [re.fullmatch(r'(\w+):\s*(true|false)', entry) for entry in entries]
    assert all(pairs), entries
    return [(pair.group(1), pair.group(2) == 'true') for pair in pairs]


def load(path, name, namespace, class_name=None):
    """One function of a module that cannot be imported here, bound to the given names."""
    nodes = ast.parse((ROOT / path).read_text()).body
    if class_name:
        nodes = next(n for n in nodes if isinstance(n, ast.ClassDef) and n.name == class_name).body
    function = next(n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == name)
    function.decorator_list = []
    module = ast.Module(body=[function], type_ignores=[])
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace[name]


def class_strings(path, class_name, names):
    """String constants of a class, read from the source."""
    nodes = ast.parse((ROOT / path).read_text()).body
    body = next(n for n in nodes if isinstance(n, ast.ClassDef) and n.name == class_name).body
    found = {}
    for node in body:
        target = node.targets[0] if isinstance(node, ast.Assign) else None
        if isinstance(target, ast.Name) and target.id in names:
            found[target.id] = ast.literal_eval(node.value)
    return found


class PermissionListTests(unittest.TestCase):
    def test_list_has_no_repeats(self):
        self.assertEqual(len(PERMISSIONS), len(set(PERMISSIONS)))
        self.assertLessEqual(set(ABSENT_FROM_OLDER_ACLS), set(PERMISSIONS))

    def test_each_page_has_one_checkbox_for_every_permission(self):
        for template in ('createACL.html', 'modifyACL.html'):
            names = checkboxes(template)
            self.assertEqual('makeAdmin', names[0], template)
            self.assertEqual(sorted(PERMISSIONS), sorted(names[1:]), template)

    def test_controller_knows_exactly_these_permissions(self):
        names = [name for name, unused in controller_defaults()]
        self.assertEqual(sorted(PERMISSIONS), sorted(names))

    def test_controllers_reach_permissions_only_through_their_list(self):
        script = SCRIPT.read_text()
        start = script.index("app.controller('createACLCTRL'")
        end = script.index("app.controller('changeUserACLCTRL'")
        acl_controllers = script[start:end]
        for name in PERMISSIONS:
            self.assertIsNone(re.search(r'\b%s\b' % name, acl_controllers), name)
        for helper in ('setACLPermissions($scope', 'submittedACLPermissions($scope'):
            self.assertIn(helper, acl_controllers)

    def test_script_copies_are_the_same_and_loaded_from_one_address(self):
        self.assertEqual(SCRIPT.read_bytes(), SCRIPT_COPY.read_bytes())
        addresses = set()
        for template in (ROOT / 'baseTemplate' / 'templates' / 'baseTemplate' / 'index.html',
                         TEMPLATES / 'createUser.html', TEMPLATES / 'deleteACL.html'):
            found = re.findall(r"""\{% static 'userManagment/userManagment\.js' %\}([^"]*)\"""", template.read_text())
            self.assertEqual(1, len(found), template.name)
            addresses.add(found[0])
        # One address on every page that loads the script, and it changes with the release.
        self.assertEqual(1, len(addresses), addresses)
        self.assertTrue(addresses.pop().startswith('?v={{ CP_VERSION }}'))

    def built_in_roles(self, path, class_name):
        roles = class_strings(path, class_name, ('AdminACL', 'ResellerACL', 'UserACL'))
        self.assertEqual(3, len(roles))
        expected = {'adminStatus'} | (set(PERMISSIONS) - set(ABSENT_FROM_OLDER_ACLS))
        for name, text in roles.items():
            self.assertEqual(expected, set(json.loads(text)), '%s in %s' % (name, path))
        return roles

    def test_built_in_roles_name_the_same_permissions(self):
        self.built_in_roles('plogical/acl.py', 'ACLManager')

    def test_built_in_roles_written_by_the_upgrade_name_the_same_permissions(self):
        roles = self.built_in_roles('plogical/upgrade.py', 'Upgrade')
        self.assertEqual(self.built_in_roles('plogical/acl.py', 'ACLManager'), roles)


class StoredConfigurationTests(unittest.TestCase):
    def test_only_true_or_one_grants(self):
        for value in (True, 1):
            self.assertTrue(granted(value), repr(value))
        for value in (None, False, 0, 2, -1, 1.0, '1', 'true', 'on', 'false', [1], {'a': 1}):
            self.assertFalse(granted(value), repr(value))

    def test_absent_permission_is_stored_as_not_granted(self):
        config = stored_config({'listUsers': True}, False)
        self.assertEqual(['adminStatus'] + list(PERMISSIONS), list(config))
        self.assertEqual(['listUsers'], [name for name in PERMISSIONS if config[name]])
        self.assertEqual(0, config['adminStatus'])
        self.assertEqual({'adminStatus': 0}, {k: v for k, v in stored_config({}, None).items() if k == 'adminStatus' or v})

    def test_other_values_and_other_keys_are_not_stored(self):
        submitted = {name: 'true' for name in PERMISSIONS}
        submitted.update(listDatabases=1, createEmail=True, admin=1, aclName='support', anything=True)
        config = stored_config(submitted, 1)
        self.assertEqual({'adminStatus', 'listDatabases', 'createEmail'}, {k for k, v in config.items() if v})
        self.assertEqual({'adminStatus'} | set(PERMISSIONS), set(config))
        self.assertTrue(all(type(value) is int for value in config.values()))

    def test_older_acl_keeps_the_scanner_and_nothing_else_it_does_not_carry(self):
        older = {'adminStatus': 0, 'listUsers': True, 'manageSSL': 1}
        self.assertEqual(1, stored_permission(older, 'aiScannerAccess'))
        self.assertEqual(0, stored_permission({'aiScannerAccess': 0}, 'aiScannerAccess'))
        self.assertIs(False, stored_permission({'aiScannerAccess': False}, 'aiScannerAccess'))
        self.assertEqual(0, stored_permission(older, 'createBackup'))
        effective = effective_config(older)
        self.assertEqual({'adminStatus'} | set(PERMISSIONS), set(effective))
        self.assertEqual({'listUsers', 'manageSSL', 'aiScannerAccess'}, {k for k, v in effective.items() if v})
        self.assertNotIn('aiScannerAccess', older)

    def test_new_acl_carries_the_scanner_switch_either_way(self):
        self.assertEqual(1, stored_config({'aiScannerAccess': True}, False)['aiScannerAccess'])
        self.assertEqual(0, stored_config({'aiScannerAccess': False}, False)['aiScannerAccess'])
        self.assertEqual(0, stored_config({}, False)['aiScannerAccess'])


class Answer(object):
    def __init__(self, content):
        self.content = json.loads(content)


class ACLViewTests(unittest.TestCase):
    """The views of userManagment/views.py, run on stand-ins for the model and the session."""

    def setUp(self):
        self.saved = []
        self.stored = SimpleNamespace(name='support', adminStatus=0, config='{}',
                                      save=lambda: self.saved.append(self.stored),
                                      administrator_set=SimpleNamespace(all=lambda: []))
        test = self

        class ACL(object):
            objects = SimpleNamespace(get=lambda name: test.stored)

            def __init__(self, **fields):
                self.__dict__.update(fields)

            def save(self):
                test.saved.append(self)

        self.manager = mock.Mock()
        self.manager.loadedACL.return_value = {'admin': 1}
        self.manager.loadErrorJson.return_value = Answer('{"status": 0}')
        self.names = dict(json=json, ACL=ACL, ACLManager=self.manager, HttpResponse=Answer,
                          phpmyadminAccess=mock.Mock(), stored_config=stored_config,
                          effective_config=effective_config)

    def call(self, view, payload):
        request = SimpleNamespace(session={'userID': 1}, body=json.dumps(payload))
        return load('userManagment/views.py', view, self.names)(request).content

    def old_page_request(self, **more):
        request = {name: False for name in PERMISSIONS if name != 'aiScannerAccess'}
        request.update({name: True for name in HIDDEN_ON_OLD_CREATE_PAGE})
        request.update(listUsers=True, **more)
        return request

    def test_created_acl_holds_only_what_was_ticked(self):
        request = {name: False for name in PERMISSIONS}
        request.update(aclName='listOnly', makeAdmin=False, listUsers=True)
        self.assertEqual({'status': 1}, self.call('createACLFunc', request))
        acl, = self.saved
        config = json.loads(acl.config)
        self.assertEqual(('listOnly', 0), (acl.name, acl.adminStatus))
        self.assertEqual(['adminStatus'] + list(PERMISSIONS), list(config))
        self.assertEqual(['listUsers'], [name for name, value in config.items() if value])

    def test_request_that_leaves_permissions_out_grants_none_of_them(self):
        self.assertEqual({'status': 1}, self.call('createACLFunc', {'aclName': 'bare', 'makeAdmin': False}))
        self.assertEqual({'status': 1}, self.call('submitACLModifications', {'aclToModify': 'support',
                                                                              'adminStatus': False}))
        for acl in self.saved:
            self.assertEqual({0}, set(json.loads(acl.config).values()))
            self.assertEqual(0, acl.adminStatus)

    def test_admin_acl_is_stored_as_admin(self):
        request = {name: True for name in PERMISSIONS}
        self.assertEqual({'status': 1}, self.call('createACLFunc', dict(request, aclName='ops', makeAdmin=True)))
        self.assertEqual({'status': 1}, self.call('submitACLModifications',
                                                  dict(request, aclToModify='support', adminStatus=True)))
        for acl in self.saved:
            self.assertEqual(1, acl.adminStatus)
            self.assertEqual({1}, set(json.loads(acl.config).values()))

    def test_only_an_administrator_creates_or_changes_an_acl(self):
        self.manager.loadedACL.return_value = {'admin': 0}
        request = dict({name: True for name in PERMISSIONS}, aclName='ops', makeAdmin=True,
                       aclToModify='support', adminStatus=True)
        for view in ('createACLFunc', 'submitACLModifications', 'fetchACLDetails'):
            self.assertEqual({'status': 0}, self.call(view, request), view)
        self.assertEqual([], self.saved)
        self.assertEqual('{}', self.stored.config)

    def test_acl_made_on_the_old_page_shows_its_three_unseen_permissions_and_they_can_be_cleared(self):
        # Stored by 3.0.12: everything the page sent, as it was sent.
        self.stored.config = json.dumps(self.old_page_request(aclName='qaListOnly', makeAdmin=False, adminStatus=0))
        shown = self.call('fetchACLDetails', {'aclToModify': 'qaListOnly'})
        self.assertEqual(1, shown['status'])
        self.assertEqual(sorted(HIDDEN_ON_OLD_CREATE_PAGE + ('listUsers', 'aiScannerAccess')),
                         sorted(name for name in PERMISSIONS if shown[name]))
        self.assertEqual(self.old_page_request(aclName='qaListOnly', makeAdmin=False, adminStatus=0),
                         json.loads(self.stored.config))

        cleared = {name: bool(shown[name]) and name not in HIDDEN_ON_OLD_CREATE_PAGE for name in PERMISSIONS}
        self.assertEqual({'status': 1}, self.call('submitACLModifications',
                                                  dict(cleared, aclToModify='qaListOnly', adminStatus=False)))
        config = json.loads(self.stored.config)
        self.assertEqual(['listUsers', 'aiScannerAccess'], [name for name in PERMISSIONS if config[name]])

    def test_signed_in_user_gets_what_the_acl_stores(self):
        names = dict(json=json, stored_permission=stored_permission, PERMISSIONS=PERMISSIONS,
                     open=mock.Mock(side_effect=IOError('no file in a test')))
        admin = SimpleNamespace(firstName='Site', lastName='Owner', acl=SimpleNamespace(config='{}'))
        names['Administrator'] = SimpleNamespace(objects=SimpleNamespace(get=lambda pk: admin))
        loadedACL = load('plogical/acl.py', 'loadedACL', names, 'ACLManager')

        admin.acl.config = json.dumps(self.old_page_request(adminStatus=0))
        acl = loadedACL(7)
        self.assertEqual(0, acl['admin'])
        self.assertEqual(sorted(HIDDEN_ON_OLD_CREATE_PAGE + ('listUsers', 'aiScannerAccess')),
                         sorted(name for name in PERMISSIONS if acl[name] == 1))

        admin.acl.config = json.dumps(stored_config({'listUsers': True}, False))
        acl = loadedACL(7)
        self.assertEqual(['listUsers'], [name for name in PERMISSIONS if acl[name] == 1])
        self.assertEqual(set(PERMISSIONS), set(acl) - {'admin', 'firstName', 'lastName', 'serverIPAddress', 'adminName'})

        admin.acl.config = json.dumps(stored_config({}, True))
        self.assertEqual(1, loadedACL(7)['admin'])


if __name__ == '__main__':
    unittest.main()
