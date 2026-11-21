"""The names of a new database and its user start with a prefix the server takes from the website."""
import json
import unittest
from pathlib import Path
from unittest import mock

from databases import databaseManager as module
from databases.databaseManager import DatabaseManager, website_database_prefix

ROOT = Path(__file__).resolve().parents[1]


class PrefixTests(unittest.TestCase):
    def test_prefix_is_what_the_page_shows_for_the_website(self):
        for domain, prefix in (('example.com', 'exam'), ('abcde.com', 'abcde'), ('abcdef.com', 'abcd'),
                               ('ab-cd-ef.com', 'abcd'), ('a.com', 'a'), ('my-site.example.org', 'mysi'),
                               ('x1.io', 'x1'), ('12345.com', '12345'), ('123456.com', '1234'),
                               ('shop.example.co.uk', 'shop'), ('a-b.com', 'ab')):
            self.assertEqual(prefix, website_database_prefix(domain), domain)

    def test_page_script_still_uses_the_same_rule(self):
        for path in ('databases/static/databases/databases.js', 'static/databases/databases.js'):
            script = (ROOT / path).read_text()
            rule = script[script.index('$scope.getTruncatedWebName = function(domain)'):]
            rule = rule[:rule.index('return webName;')]
            self.assertIn("var webName = domain.replace(/-/g, '').split('.')[0];", rule, path)
            self.assertIn('if (webName.length > 5) {', rule, path)
            self.assertIn('webName = webName.substring(0, 4);', rule, path)


class CreationTests(unittest.TestCase):
    def create(self, data, api=None, owner=1, created=(1, 'None')):
        with mock.patch.object(module.ACLManager, 'loadedACL', return_value={'admin': 0}), \
                mock.patch.object(module.ACLManager, 'currentContextPermission', return_value=1), \
                mock.patch.object(module.ACLManager, 'checkOwnership', return_value=owner) as ownership, \
                mock.patch.object(module.ACLManager, 'loadErrorJson', return_value='refused'), \
                mock.patch.object(module.Administrator.objects, 'get', return_value='admin-row'), \
                mock.patch.object(module.mysqlUtilities, 'submitDBCreation', return_value=created) as submit:
            response = DatabaseManager().submitDBCreation(5, data, api)
        self.ownership, self.submit = ownership, submit
        return response if response == 'refused' else json.loads(response.content.decode())

    def request(self, **changes):
        data = {'databaseWebsite': 'example.com', 'dbName': 'shop', 'dbUsername': 'user', 'dbPassword': 'secret',
                'webUserName': 'exam'}
        data.update(changes)
        return data

    def test_names_start_with_the_prefix_of_the_website(self):
        answer = self.create(self.request())
        self.submit.assert_called_once_with('exam_shop', 'exam_user', 'secret', 'example.com')
        self.assertEqual({'status': 1, 'createDBStatus': 1, 'error_message': 'None',
                          'dbName': 'exam_shop', 'dbUsername': 'exam_user'}, answer)

    def test_prefix_sent_by_the_browser_is_not_used(self):
        for sent in ('', '_', '____', 'other', 'cyberpanel', 'mysql', '%', 7, None, ['x']):
            self.create(self.request(webUserName=sent, dbName='_____', dbUsername='u'))
            self.submit.assert_called_once_with('exam______', 'exam_u', 'secret', 'example.com')

    def test_request_without_a_prefix_is_served(self):
        data = self.request()
        del data['webUserName']
        self.create(data)
        self.submit.assert_called_once_with('exam_shop', 'exam_user', 'secret', 'example.com')

    def test_website_is_checked_before_its_name_is_used(self):
        self.assertEqual('refused', self.create(self.request(), owner=0))
        self.ownership.assert_called_once_with('example.com', 'admin-row', {'admin': 0})
        self.submit.assert_not_called()

    def test_website_name_that_gives_no_usable_prefix_is_refused(self):
        for domain in ('-.com', '_x.com', '.com', 'a b.com', 'x;y.com'):
            answer = self.create(self.request(databaseWebsite=domain))
            self.assertEqual(0, answer['createDBStatus'], domain)
            self.assertEqual('A database name cannot be derived from this website name.', answer['error_message'])
            self.submit.assert_not_called()

    def test_names_with_other_characters_are_still_refused(self):
        for name in ('shop-1', 'shop db', 'shop`', "shop'", 'shop%', 'x' * 60):
            answer = self.create(self.request(dbName=name))
            self.assertEqual(0, answer['createDBStatus'], name)
            self.submit.assert_not_called()

    def test_api_names_are_used_as_given(self):
        self.create(self.request(dbName='wp_live', dbUsername='wp_user', webUserName='bogus'), api=1)
        self.submit.assert_called_once_with('wp_live', 'wp_user', 'secret', 'example.com')

    def test_api_request_without_a_prefix_is_served(self):
        data = self.request(dbName='wp_live', dbUsername='wp_user')
        del data['webUserName']
        self.create(data, api=1)
        self.submit.assert_called_once_with('wp_live', 'wp_user', 'secret', 'example.com')

    def test_failed_creation_is_reported(self):
        answer = self.create(self.request(), created=(0, 'This database or user is already taken.'))
        self.assertEqual({'status': 0, 'createDBStatus': 0,
                          'error_message': 'This database or user is already taken.'}, answer)


if __name__ == '__main__':
    unittest.main()
