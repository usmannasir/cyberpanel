import pathlib
import unittest


class DockerEnvironmentFieldTests(unittest.TestCase):
    def test_simple_environment_rows_use_the_next_array_index(self):
        script = (
            pathlib.Path(__file__).parent
            / 'static'
            / 'dockerManager'
            / 'dockerManager.js'
        ).read_text(encoding='utf-8')

        self.assertEqual(script.count("envList[countEnv] = {'name': '', 'value': ''}"), 2)
        self.assertNotIn('envList[countEnv + 1]', script)


if __name__ == '__main__':
    unittest.main()
