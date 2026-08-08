import pathlib
import unittest


class DeveloperInstallerPythonTests(unittest.TestCase):

    def test_ubuntu_dependencies_require_installable_pcre_candidate(self):
        root = pathlib.Path(__file__).parents[1]
        for script_path in (root / 'cyberpanel.sh', root / 'install/venvsetup.sh'):
            script = script_path.read_text(encoding='utf-8')
            self.assertIn(
                "apt-cache policy libpcre3-dev 2>/dev/null | grep -q 'Candidate: [^(]'",
                script,
            )
            self.assertNotIn(
                'apt-cache show libpcre3-dev >/dev/null 2>&1',
                script,
            )
            self.assertIn('libsasl2-dev', script)

    def test_developer_install_uses_system_python_three(self):
        script = pathlib.Path(__file__).with_name('venvsetup.sh').read_text(
            encoding='utf-8'
        )
        self.assertNotIn('python3.6', script)
        self.assertNotIn('pip3.6', script)
        self.assertIn(
            'python3 -m venv --system-site-packages CyberPanel',
            script,
        )
        self.assertIn(
            'python3 -m venv --system-site-packages /usr/local/CyberCP',
            script,
        )
        self.assertGreaterEqual(
            script.count('python -m pip install --ignore-installed'),
            2,
        )


if __name__ == '__main__':
    unittest.main()
