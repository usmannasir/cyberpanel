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


if __name__ == '__main__':
    unittest.main()
