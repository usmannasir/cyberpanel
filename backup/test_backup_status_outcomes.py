"""A diagnostic filename is not the backup completion protocol."""
import ast
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest


class BackupStatusOutcomeTests(unittest.TestCase):
    def status_result(self, text):
        source = Path(__file__).with_name('backupManager.py')
        tree = ast.parse(source.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BackupManager')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'backupStatus')
        wrapper = ast.ClassDef(name='BackupManager', bases=[], keywords=[], body=[method], decorator_list=[])
        namespace = {
            'os': SimpleNamespace(path=SimpleNamespace(join=os.path.join, exists=lambda path: True)),
            'json': json, 'HttpResponse': lambda text: text,
            'Websites': SimpleNamespace(objects=SimpleNamespace(get=lambda **kwargs: SimpleNamespace(externalApp='fixture'))),
            'Backups': SimpleNamespace(objects=SimpleNamespace(filter=lambda **kwargs: [])),
            'ProcessUtilities': SimpleNamespace(
                outputExecutioner=lambda command, user: 'fixture' if command.endswith('backupFileName') else text,
                executioner=lambda *args: None),
        }
        exec(compile(ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[])), str(source), 'exec'), namespace)
        return json.loads(namespace['BackupManager']().backupStatus(data={'websiteToBeBacked': 'fixture.invalid'}))

    def test_completed_filename_in_error_is_failed(self):
        result = self.status_result('tar: Completed.txt: Disk quota exceeded [5009]')
        self.assertEqual('failed', result['state'])
        self.assertIn('Disk quota exceeded', result['status'])

    def test_completed_status_is_still_accepted(self):
        self.assertEqual('completed', self.status_result('Completed\n')['state'])


if __name__ == '__main__':
    unittest.main()
