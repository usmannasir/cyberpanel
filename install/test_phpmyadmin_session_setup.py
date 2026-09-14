"""Extract and execute the actual install/upgrade PMA config/copy statements."""
import ast
from pathlib import Path
import shutil
import tempfile
import zipfile
from types import SimpleNamespace
import unittest

from install.database_consumers import render_phpmyadmin_signon


class PhpMyAdminSessionSetupTests(unittest.TestCase):
    def test_both_setup_paths_configure_hook_and_copy_both_scripts(self):
        root = Path(__file__).resolve().parents[1]
        for relative in ('install/install.py', 'plogical/upgrade.py'):
            with self.subTest(relative=relative):
                tree = ast.parse((root / relative).read_text())
                method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'download_install_phpmyadmin')
                statements = next(n for n in method.body if isinstance(n, ast.Try)).body
                begin = next(i for i, n in enumerate(statements) if isinstance(n, ast.Assign)
                             and any(isinstance(t, ast.Name) and t.id == 'data' for t in n.targets)
                             and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
                             and n.value.func.attr == 'readlines')
                end = next(i + 2 for i, n in enumerate(statements) if isinstance(n, ast.Assign)
                           and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
                           and n.value.value.startswith('cp /usr/local/CyberCP/plogical/phpmyadminsession.php '))
                with tempfile.TemporaryDirectory() as temporary:
                    target = Path(temporary)
                    prefix = '/usr/local/CyberCP/public/phpmyadmin/'
                    with zipfile.ZipFile(root / 'phpmyadmin.zip') as archive:
                        sample = archive.read('phpMyAdmin-5.2.1-all-languages/config.sample.inc.php')
                    (target / 'config.sample.inc.php').write_bytes(sample)
                    def mapped(path):
                        self.assertTrue(path.startswith(prefix))
                        suffix = path[len(prefix):]
                        self.assertNotIn('/', suffix)
                        return target / suffix
                    def fixture_open(path, *args, **kwargs):
                        return open(mapped(path), *args, **kwargs)
                    copied = []
                    def command(command, *args):
                        if command.startswith('chown -R lscpd:lscpd '):
                            self.assertEqual('chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin', command)
                            return
                        fields = command.split()
                        self.assertEqual(3, len(fields))
                        self.assertEqual('cp', fields[0])
                        name = fields[1].rsplit('/', 1)[1]
                        self.assertIn(name, ('phpmyadminsignin.php', 'phpmyadminsession.php'))
                        self.assertEqual('/usr/local/CyberCP/plogical/' + name, fields[1])
                        shutil.copyfile(root / 'plogical' / name, mapped(fields[2]))
                        copied.append(name)
                    scope = dict(open=fixture_open, rString='fixture-secret-only',
                                 os=SimpleNamespace(mkdir=lambda p: mapped(p).mkdir(), EX_OSERR=71),
                                 self=SimpleNamespace(distro='fixture'),
                                 preFlightsChecks=SimpleNamespace(call=command),
                                 Upgrade=SimpleNamespace(executioner=command))
                    exec(compile(ast.fix_missing_locations(ast.Module(body=statements[begin:end], type_ignores=[])),
                                 relative, 'exec'), scope)
                    config = (target / 'config.inc.php').read_text()
                    self.assertIn("['auth_type'] = 'signon'", config)
                    self.assertIn("['SignonScript'] = __DIR__ . '/phpmyadminsession.php'", config)
                    self.assertIn("['SignonURL'] = 'phpmyadminsignin.php'", config)
                    self.assertIn("['LogoutURL'] = 'phpmyadminsignin.php?logout'", config)
                    self.assertEqual(['phpmyadminsignin.php', 'phpmyadminsession.php'], copied)
                    for name in copied:
                        self.assertEqual((root / 'plogical' / name).read_bytes(), (target / name).read_bytes())

    def test_remote_host_port_rendering_preserves_new_session_binding(self):
        source = Path(__file__).resolve().parents[1] / 'plogical/phpmyadminsignin.php'
        rendered = render_phpmyadmin_signon(source.read_text(), 'remote-db.internal', 4406)
        self.assertIn("host'] = 'remote-db.internal'", rendered)
        self.assertIn("port'] = 4406", rendered)
        self.assertIn("$_SESSION['PMA_panel_grant'] = $grant", rendered)
        self.assertIn("$_SESSION['PMA_panel_session'] = $_COOKIE['cyberpanel_sessionid']", rendered)


if __name__ == '__main__':
    unittest.main()
