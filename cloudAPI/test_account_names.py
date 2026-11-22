"""An account the platform asks for is named by what the rule for user names allows of the customer's name."""
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from cloudAPI.test_wordpress_cloud_entitlements import load_cloud, Response
from plogical.panelUserNames import NAME_RULE, name_from, new_name_refusal


class AccountNameTests(unittest.TestCase):
    def setUp(self):
        self.ns, self.services, self.admin, unused = load_cloud()
        self.ns['hashPassword'] = mock.Mock()
        self.ns['ACL'] = mock.Mock()
        self.ns.update(name_from=name_from, new_name_refusal=new_name_refusal)
        self.users = self.services['Administrator']
        self.existing = {}
        self.users.objects.filter.side_effect = lambda userName: SimpleNamespace(
            exists=lambda: userName in self.existing)
        self.users.objects.get.side_effect = lambda userName: self.existing[userName]
        self.manager = self.services['WebsiteManager'].return_value
        self.manager.submitWebsiteCreation.return_value = Response('{"status":1,"createWebSiteStatus":1}')

    def create(self, sent, owner=None):
        self.data = {'UserAccountName': sent, 'websiteOwner': sent if owner is None else owner,
                     'UserPassword': 'inert', 'FullName': 'Full Name', 'adminEmail': 'owner@example.test',
                     'domainName': 'owned.example', 'apacheBackend': 0}
        return json.loads(self.ns['CloudManager'](self.data, self.admin).submitWebsiteCreation().content)

    def created_name(self):
        return self.users.call_args[1]['userName']

    def test_name_in_another_alphabet_is_used_as_it_is(self):
        for name in ('JoséGarcía', 'ЮрийГагарин', '李雷', 'JohnSmith', 'john.smith@example.com'):
            self.assertEqual(1, self.create(name)['status'], name)
            self.assertEqual(name, self.created_name())
            self.assertEqual(name, self.data['websiteOwner'])
            self.manager.submitWebsiteCreation.assert_called_with(7, self.data)

    def test_other_characters_are_dropped_for_the_account_and_for_the_owner(self):
        for sent, expected in (("O'Brien", 'OBrien'), ('Anne-Marie(Jr.)', 'Anne-MarieJr.'), ('"Mc&Sons"', 'McSons'),
                               ('.-_@Smith', 'Smith'), ('D`Arcy;x', 'DArcyx')):
            self.assertEqual(1, self.create(sent)['status'], sent)
            self.assertEqual(expected, self.created_name())
            self.assertEqual(expected, self.data['websiteOwner'])
            self.assertEqual(expected, self.manager.submitWebsiteCreation.call_args[0][1]['websiteOwner'])

    def test_owner_that_is_another_user_is_left_as_sent(self):
        self.assertEqual(1, self.create("O'Brien", owner='admin')['status'])
        self.assertEqual('OBrien', self.created_name())
        self.assertEqual('admin', self.data['websiteOwner'])

    def test_existing_user_with_exactly_the_sent_name_is_used_as_before(self):
        user = SimpleNamespace(save=mock.Mock())
        self.existing["O'Brien"] = user
        # As on a server: a second user of that name cannot be saved, the existing one gets the new password.
        self.users.return_value.save.side_effect = ValueError('duplicate entry')
        self.assertEqual(1, self.create("O'Brien")['status'])
        self.assertEqual("O'Brien", self.created_name())
        self.assertEqual("O'Brien", self.data['websiteOwner'])
        user.save.assert_called_once_with()
        self.assertEqual(self.ns['hashPassword'].hash_password.return_value, user.password)

    def test_name_without_a_letter_or_number_is_answered_with_the_rule(self):
        for sent in ("'!!'", '...', '_-@', '', ' ', '!"#$%&/()=?', None, 7):
            answer = self.create(sent)
            self.assertEqual(0, answer['status'], repr(sent))
            self.assertEqual(NAME_RULE, answer['error_message'])
        self.users.assert_not_called()
        self.services['WebsiteManager'].assert_not_called()

    def test_name_that_is_left_too_long_or_reserved_is_refused(self):
        self.assertEqual(NAME_RULE, self.create('x' * 51)['error_message'])
        for sent in ('root', "r'oot", 'Cyber Panel', 'cp-pma-5'):
            answer = self.create(sent)
            self.assertEqual(0, answer['status'], sent)
            self.assertIn('reserved', answer['error_message'])
        self.users.assert_not_called()
        self.services['WebsiteManager'].assert_not_called()


if __name__ == '__main__':
    unittest.main()
