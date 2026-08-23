import pathlib
import shutil
import subprocess
import unittest


class StaticJavascriptSyntaxTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is required for syntax checks.')
    def test_website_functions_bundles_parse(self):
        repository = pathlib.Path(__file__).parents[1]
        paths = (
            repository / 'websiteFunctions' / 'static' / 'websiteFunctions' / 'websiteFunctions.js',
            repository / 'static' / 'websiteFunctions' / 'websiteFunctions.js',
        )

        for path in paths:
            with self.subTest(path=path):
                result = subprocess.run(
                    ['node', '--check', str(path)],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(0, result.returncode, result.stderr)

    def test_schedule_backup_button_is_spelled_edit(self):
        template = (
            pathlib.Path(__file__).with_name('templates')
            / 'websiteFunctions'
            / 'BackupfileConfig.html'
        ).read_text(encoding='utf-8')

        self.assertIn('>\n                                    Edit\n                                </button>', template)
        self.assertNotIn('>\n                                    Eidt\n                                </button>', template)


if __name__ == '__main__':
    unittest.main()
