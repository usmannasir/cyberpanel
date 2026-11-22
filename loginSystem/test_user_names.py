"""A new panel user is saved only under a name that follows the rule, on whichever path it is created."""
import os
import unittest
from unittest import mock

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
django.setup()

from django.db import models
from loginSystem.models import Administrator


class NewUserTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(models.Model, 'save')
        self.stored = patcher.start()
        self.addCleanup(patcher.stop)

    def test_new_user_with_a_plain_name_is_saved(self):
        for name in ('admin', 'john', 'John.Doe', 'john-doe', 'john_doe', 'john@example.com', 'example_com'):
            Administrator(userName=name, password='x', email='a@example.com', type=3).save()
        self.assertEqual(7, self.stored.call_count)

    def test_new_user_with_any_other_name_is_not_saved(self):
        for name in ('x /etc/shadow', 'x & id', "x' OR '1", 'a/../../b', 'x\nid', ' x', 'x;id', '$(id)', '`id`',
                     'John Smith', '-rf', '', None, 7, 'x' * 51,
                     'root', 'ROOT', 'mysql', 'mariadb.sys', 'cyberpanel', 'debian-sys-maint', 'cp-pma-5'):
            with self.assertRaises(ValueError):
                Administrator(userName=name, password='x', email='a@example.com', type=3).save()
        self.stored.assert_not_called()

    def test_user_saved_by_an_earlier_release_keeps_working(self):
        for name in ('John Smith', 'root', 'cyberpanel', "o'brien"):
            user = Administrator(userName=name, password='x', email='a@example.com', type=3)
            user._state.adding = False
            user.state = 'SUSPENDED'
            user.save()
        self.assertEqual(4, self.stored.call_count)


class RestoredOwnerTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(models.Model, 'save')
        self.stored = patcher.start()
        self.addCleanup(patcher.stop)

    def user(self, name):
        return Administrator(userName=name, password='x', email='a@example.com', type=3)

    def test_owner_from_a_backup_is_saved_under_a_name_earlier_releases_accepted(self):
        for name in ('john', 'John Smith', 'jürgen', 'john+tag@example.com', '_john'):
            self.user(name).save(name_from_backup=True)
        self.assertEqual(5, self.stored.call_count)
        # The model's own save never sees the argument.
        for call in self.stored.call_args_list:
            self.assertEqual({}, call[1])

    def test_owner_from_a_backup_never_gets_a_name_of_the_server_or_one_that_cannot_be_carried(self):
        for name in ('root', 'ROOT', 'cyberpanel', 'mysql', 'cp-pma-5', "o'brien", 'a/../b', 'x;y', ' x', 'x\ny',
                     '', None, 'x' * 51):
            with self.assertRaises(ValueError):
                self.user(name).save(name_from_backup=True)
        self.stored.assert_not_called()

    def test_only_the_argument_of_the_restore_selects_that_rule(self):
        # It is not a value of the user, so it cannot arrive with the values of a new user.
        with self.assertRaises(TypeError):
            Administrator(userName='John Smith', password='x', email='a@example.com', type=3, name_from_backup=True)
        for value in (1, 'true', 'yes', [True], None, False):
            with self.assertRaises(ValueError):
                self.user('John Smith').save(name_from_backup=value)
        user = self.user('John Smith')
        user.name_from_backup = True
        with self.assertRaises(ValueError):
            user.save()
        self.stored.assert_not_called()

    def test_no_other_place_in_the_panel_passes_the_argument(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        places = [str(path.relative_to(root)) for path in sorted(root.rglob('*.py'))
                  if not path.name.startswith('test_') and 'name_from_backup=' in path.read_text(errors='replace')]
        self.assertEqual(['plogical/backupUtilities.py'], places)


if __name__ == '__main__':
    unittest.main()
