import unittest

from websiteFunctions.website import (
    get_wordpress_flag,
    get_wordpress_json_list,
    get_wordpress_maintenance_mode,
    get_wordpress_version,
)


class WordPressCliOutputTests(unittest.TestCase):

    def test_accepts_a_wordpress_version(self):
        self.assertEqual('6.8.3', get_wordpress_version('6.8.3\n'))

    def test_rejects_non_version_command_output(self):
        self.assertEqual('Unavailable', get_wordpress_version('Error: WordPress is not installed.'))

    def test_invalid_option_output_uses_safe_default(self):
        self.assertEqual(0, get_wordpress_flag('Error: Could not open input file.'))
        self.assertEqual(1, get_wordpress_flag('notice\n1\n'))

    def test_detects_maintenance_mode_without_raising_on_empty_output(self):
        self.assertEqual(0, get_wordpress_maintenance_mode('Maintenance mode is not active.'))
        self.assertEqual(1, get_wordpress_maintenance_mode('Maintenance mode is active.'))
        self.assertEqual(0, get_wordpress_maintenance_mode(''))

    def test_extracts_json_list_after_command_output(self):
        output = 'notice\n[{"name": "sample", "status": "active"}]\n'
        self.assertEqual(
            [{'name': 'sample', 'status': 'active'}],
            get_wordpress_json_list(output),
        )
        self.assertEqual([], get_wordpress_json_list('Error: command failed'))


if __name__ == '__main__':
    unittest.main()
