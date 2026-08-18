"""Regression tests for issue #1716, git repositories with a dot in the name.

Attaching a repo such as repo.ltd failed the input security check because the default
validateInput pattern allows no dots. Run standalone:

    /usr/local/CyberCP/bin/python -m unittest websiteFunctions.test_git_repo_names -v
"""

import os
import sys
import unittest

sys.path.append('/usr/local/CyberCP')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plogical.acl import ACLManager


class TestRepoNameValidation(unittest.TestCase):

    def accepts(self, name):
        return ACLManager.validateInput(name, ACLManager.RepoNameRegex) == 1

    def test_accepts_a_dotted_repository_name(self):
        self.assertTrue(self.accepts('repo.ltd'))
        self.assertTrue(self.accepts('my.repo.name'))

    def test_still_accepts_ordinary_names(self):
        for name in ('cyberpanel', 'my-repo', 'my_repo', 'repo123'):
            self.assertTrue(self.accepts(name), name)

    def test_rejects_path_traversal_and_injection(self):
        for name in ('..', '../etc', 'repo/../other', '.hidden', 'repo.', 'repo;rm -rf /',
                     'repo name', 'repo$(id)', 'repo|cat', ''):
            self.assertFalse(self.accepts(name), name)

    def test_default_pattern_is_unchanged(self):
        ## Everything that does not pass a repo name keeps the original rules.
        self.assertEqual(ACLManager.validateInput('plain-name'), 1)
        self.assertEqual(ACLManager.validateInput('has.dot'), 0)


if __name__ == '__main__':
    unittest.main()
