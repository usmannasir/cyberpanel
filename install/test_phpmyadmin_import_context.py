"""Exercise fresh PMA imports with Python's actual standalone/package machinery."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

PROBE = r'''
import ast, pathlib, sys
root = pathlib.Path(sys.argv[1])
mode = sys.argv[2]
sys.path.insert(0, str(root / 'install'))
if mode == 'standalone':
    # Load the actual script module used by installCyberPanel, not a mock of it.
    import install as actual
    assert not hasattr(actual, '__path__')
else:
    sys.path.insert(0, str(root))
    import install.install as actual
assert pathlib.Path(actual.__file__).resolve() == (root / 'install/install.py').resolve()
tree = ast.parse(pathlib.Path(actual.__file__).read_text())
method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
              and n.name == 'download_install_phpmyadmin')
body = next(n for n in method.body if isinstance(n, ast.Try)).body
imports = [n for n in body if any(isinstance(i, ast.ImportFrom)
           and i.module and i.module.endswith('proxy_identity') for i in ast.walk(n))]
assert len(imports) == 1
namespace = actual.__dict__
exec(compile(ast.fix_missing_locations(ast.Module(body=imports, type_ignores=[])),
             'real-pma-import', 'exec'), namespace)
function = namespace['ensure_pma_peer_key']
assert callable(function)
assert pathlib.Path(sys.modules[function.__module__].__file__).resolve() == (root / 'install/proxy_identity.py').resolve()
print('resolved matching release helper')
'''


class PhpMyAdminImportContextTests(unittest.TestCase):
    def test_real_standalone_module_collision_resolves_adjacent_helper(self):
        result = subprocess.run([sys.executable, '-c', PROBE, str(ROOT), 'standalone'],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('resolved matching release helper', result.stdout)

    def test_real_packaged_context_resolves_package_helper(self):
        result = subprocess.run([sys.executable, '-c', PROBE, str(ROOT), 'package'],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
