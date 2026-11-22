"""The name of a new panel user follows one written rule; earlier names stay usable where they can be carried."""
import unittest

from plogical.panelUserNames import NAME_RULE, name_from, new_name_refusal, stored_name_is_usable


class NewNameTests(unittest.TestCase):
    def test_names_people_choose_are_accepted(self):
        for name in ('admin', 'john', 'John.Doe', 'john-doe', 'john_doe', 'john@example.com', 'a', '7up',
                     'site-owner', 'example_com', 'x' * 50):
            self.assertIsNone(new_name_refusal(name), name)

    def test_letters_and_numbers_of_every_alphabet_are_accepted(self):
        for name in ('jöhn', 'JoséGarcía', 'jürgen', 'Łukasz', 'ЮрийГагарин', 'Ελένη', '李雷', '山田太郎', 'محمد',
                     'דוד', '김철수', '٣ali', 'renée.dupont@example.com', 'ö' * 50,
                     # Letters written with marks that follow them.
                     'हिंदी', 'สมชาย', 'Jose\u0301'):
            self.assertIsNone(new_name_refusal(name), name)

    def test_names_with_other_characters_are_refused(self):
        for name in ('', ' john', 'john ', 'john smith', 'john;id', 'john&id', "john'", 'john"', 'john/..', '../x',
                     '-rf', '.hidden', '_x', '@x', 'john\n', 'john\tx', 'john$', 'john`id`', 'john|x',
                     'john>x', 'john<x', 'john\\', 'john%', 'john*', 'john+x', 'john(x)', 'john=x', 'john,x',
                     'john:x', 'john#x', 'john!', 'x' * 51, 'ö' * 51,
                     # Spaces, quotes and separators of other alphabets, and characters that are not shown.
                     'josé garcía', 'josé\u00a0garcía', 'josé\u3000garcía', 'josé\u2019s', 'josé\u201cx\u201d',
                     'josé\u2215x', 'josé\uff0fx', 'josé\u200bx', 'josé\u202ex', 'josé\u0000', 'josé\x7f',
                     'josé\u2028x', '\u0301jose', '\ud800'):
            self.assertEqual(NAME_RULE, new_name_refusal(name), repr(name))

    def test_name_made_from_what_somebody_wrote_keeps_what_the_rule_allows(self):
        for written, name in (("O'Brien", 'OBrien'), ('JoséGarcía', 'JoséGarcía'), ('John Smith', 'JohnSmith'),
                              ('Anne-Marie (Jr.)', 'Anne-MarieJr.'), ('.-_@x', 'x'), ('\u0301é', 'é'),
                              ('a/b;c|d`e$f', 'abcdef'), ("'!!'", ''), ('...', ''), ('', ''), (None, ''), (7, '')):
            self.assertEqual(name, name_from(written), repr(written))
            if name:
                self.assertIsNone(new_name_refusal(name), name)

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


class ImportTests(unittest.TestCase):
    def test_rule_is_read_without_django_settings_or_the_database_driver(self):
        # Saving a user reads the rule; the installer does that before the panel is configured.
        import os
        import subprocess
        import sys
        code = ("import sys\n"
                "sys.modules['MySQLdb'] = None\n"
                "sys.modules['django'] = None\n"
                "from plogical.panelUserNames import new_name_refusal, restored_name_refusal\n"
                "assert new_name_refusal('admin') is None\n"
                "assert new_name_refusal('root') is not None\n"
                "assert restored_name_refusal('John Smith') is None\n"
                "print('read')\n")
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        environment = dict((key, value) for key, value in os.environ.items() if key != 'DJANGO_SETTINGS_MODULE')
        output = subprocess.check_output([sys.executable, '-c', code], cwd=root, env=environment)
        self.assertEqual(b'read', output.strip())


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
