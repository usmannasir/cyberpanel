import os
import pathlib
import unittest

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')
django.setup()

from websiteFunctions.website import WebsiteManager


class GitManagementTests(unittest.TestCase):

    def test_custom_ssh_port_uses_ssh_url(self):
        self.assertEqual(
            'ssh://git@git.example.com:9008/team/project.git',
            WebsiteManager.gitCloneURL(
                'git.example.com:9008',
                'team',
                'project',
            ),
        )

    def test_standard_git_host_keeps_scp_style_url(self):
        self.assertEqual(
            'git@git.example.com:team/project.git',
            WebsiteManager.gitCloneURL(
                'git.example.com',
                'team',
                'project',
            ),
        )

    def test_custom_ssh_port_must_be_in_range(self):
        with self.assertRaises(ValueError):
            WebsiteManager.gitCloneURL(
                'git.example.com:70000',
                'team',
                'project',
            )

    def test_site_workspace_opens_full_git_manager(self):
        root = pathlib.Path(__file__).parents[1]
        workspace = (
            root / 'baseTemplate/templates/baseTemplate/siteWorkspace.html'
        ).read_text(encoding='utf-8')
        self.assertIn("{% url 'manageGIT' domain %}", workspace)
        self.assertNotIn("{% url 'setupGit' domain %}", workspace)


if __name__ == '__main__':
    unittest.main()
