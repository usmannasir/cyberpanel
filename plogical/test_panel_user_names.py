"""The name of a new panel user follows one written rule; earlier names stay usable where they can be carried."""
import unittest

from plogical.panelUserNames import NAME_RULE, new_name_refusal, stored_name_is_usable


class NewNameTests(unittest.TestCase):
    def test_names_people_choose_are_accepted(self):
        for name in ('admin', 'john', 'John.Doe', 'john-doe', 'john_doe', 'john@example.com', 'a', '7up',
                     'site-owner', 'example_com', 'x' * 50):
            self.assertIsNone(new_name_refusal(name), name)

    def test_names_with_other_characters_are_refused(self):
        for name in ('', ' john', 'john ', 'john smith', 'john;id', 'john&id', "john'", 'john"', 'john/..', '../x',
                     '-rf', '.hidden', '_x', '@x', 'john\n', 'john\tx', 'jöhn', 'john$', 'john`id`', 'john|x',
                     'john>x', 'john<x', 'john\\', 'john%', 'john*', 'john+x', 'john(x)', 'john=x', 'john,x',
                     'john:x', 'john#x', 'john!', 'x' * 51):
            self.assertEqual(NAME_RULE, new_name_refusal(name), repr(name))

    def test_values_that_are_not_text_are_refused(self):
        for name in (None, 7, 7.5, True, ['john'], {'a': 1}, b'john'):
            self.assertEqual(NAME_RULE, new_name_refusal(name), repr(name))

    def test_names_of_the_server_are_refused_in_any_case(self):
        for name in ('root', 'Root', 'ROOT', 'mysql', 'MySQL', 'mariadb.sys', 'mysql.sys', 'mysql.session',
                     'mysql.infoschema', 'debian-sys-maint', 'cyberpanel', 'CyberPanel', 'public', 'PUBLIC',
                     'rdsadmin', 'cp-pma-5', 'CP-PMA-5', 'cp-pma-', 'cp-pma-x'):
            refusal = new_name_refusal(name)
            self.assertIsNotNone(refusal, name)
            self.assertIn('reserved', refusal, name)

    def test_first_user_of_every_server_is_not_reserved(self):
        self.assertIsNone(new_name_refusal('admin'))


class StoredNameTests(unittest.TestCase):
    def test_names_earlier_releases_accepted_stay_usable(self):
        for name in ('admin', 'john', 'John.Doe', 'john-doe', 'john_doe', '_john', 'john@example.com',
                     'john+tag@example.com', 'John Smith', 'jürgen', 'محمد',
                     'root', 'cyberpanel', 'x' * 50):
            self.assertTrue(stored_name_is_usable(name), name)

    def test_names_that_cannot_be_carried_are_not_usable(self):
        for name in ('', ' john', 'john ', "jo'hn", 'jo"hn', 'a/b', 'a\\b', 'a;b', 'a&b', 'a|b', 'a$b', 'a`b',
                     'a\nb', 'john\n', 'a\tb', 'a\x00b', '-x', '.x', '@x', '+x', 'a<b', 'a>b', 'a(b', 'a)b',
                     'a*b', 'a%b', 'a=b', 'a,b', 'a:b', 'a#b', 'a!b', 'a?b', 'a{b', 'a[b', 'a~b', 'x' * 51,
                     None, 7, ['john'], b'john'):
            self.assertFalse(stored_name_is_usable(name), repr(name))


if __name__ == '__main__':
    unittest.main()
