import ast
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[1]


def load(path, name, namespace, class_name=None):
    tree = ast.parse((ROOT / path).read_text())
    nodes = tree.body
    if class_name:
        nodes = next(n for n in nodes if isinstance(n, ast.ClassDef) and n.name == class_name).body
    function = next(n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == name)
    function.decorator_list = []
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


def response(value):
    return SimpleNamespace(content=value.encode())


class PermissionFeedbackTests(unittest.TestCase):
    def view(self, result=None, error=None, admin=1):
        acl = Mock(); acl.loadedACL.return_value = {'admin':admin}
        manager = Mock(); manager.fixPermissions.return_value = result
        manager.fixPermissions.side_effect = error
        denied = response('{"permissionsChanged":0}')
        acl.loadError.return_value = denied
        function = load('filemanager/views.py','changePermissions',dict(
            json=json, ACLManager=acl, FM=Mock(return_value=manager),
            HttpResponse=response, logging=Mock()))
        request = SimpleNamespace(session={'userID':1},body=b'{"domainName":"fixture.test"}')
        return json.loads(function(request).content), manager

    def test_refused_repair_is_not_reported_as_success(self):
        result, _ = self.view(response('{"status":0,"error_message":"Symlink attack."}'))
        self.assertEqual(0,result['permissionsChanged'])
        self.assertEqual('Symlink attack.',result['error_message'])

    def test_successful_legacy_none_result_still_succeeds(self):
        self.assertEqual(1,self.view()[0]['permissionsChanged'])

    def test_command_failure_is_reported(self):
        result, _ = self.view(error=RuntimeError('Permission repair failed.'))
        self.assertEqual(0,result['permissionsChanged'])

    def test_nonadmin_cannot_repair(self):
        result, manager = self.view(admin=0)
        self.assertEqual(0,result['permissionsChanged'])
        manager.fixPermissions.assert_not_called()

    def worker(self, fail=False):
        process=Mock(centos=0,cent8=1)
        process.decideDistro.return_value=2
        process.outputExecutioner.side_effect=lambda command,**kwargs: ((0 if fail else 1,'fixture command') if kwargs.get('retRequired') else '')
        website=Mock(externalApp='fixtureuser'); website.childdomains_set.all.return_value=[]
        websites=Mock(); websites.objects.get.return_value=website
        function=load('filemanager/filemanager.py','fixPermissions',dict(
            Websites=websites, ProcessUtilities=process, json=json, HttpResponse=response,logging=Mock()),'FileManager')
        manager=SimpleNamespace(returnPathEnclosed=shlex.quote)
        return function,manager,process

    def test_failed_command_stops_repair(self):
        function,manager,process=self.worker(fail=True)
        with self.assertRaisesRegex(RuntimeError,'Permission repair failed'):
            function(manager,'fixture.test')
        commands=[c for c in process.outputExecutioner.call_args_list if c.kwargs.get('retRequired')]
        self.assertEqual(1,len(commands))

    def test_successful_commands_preserve_restricted_document_root(self):
        function,manager,process=self.worker()
        self.assertIsNone(function(manager,'fixture.test'))
        commands=[c.args[0] for c in process.outputExecutioner.call_args_list if c.kwargs.get('retRequired')]
        self.assertTrue(all(c.kwargs.get('shell') is False for c in process.outputExecutioner.call_args_list if c.kwargs.get('retRequired')))
        self.assertIn('chmod 750 /home/fixture.test/public_html',commands)

    def test_find_reports_a_failed_chmod_child(self):
        function,manager,process=self.worker()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'root';root.mkdir();(root/'nested').mkdir()
            binary=Path(directory)/'bin';binary.mkdir()
            chmod=binary/'chmod';chmod.write_text('#!/bin/sh\nexit 1\n');chmod.chmod(0o755)
            def execute(command,**kwargs):
                if not kwargs.get('retRequired'): return ''
                args=shlex.split(command)
                if args[0]!='find': return 1,''
                args[1]=str(root)
                result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    env=dict(os.environ,PATH=str(binary)+os.pathsep+os.environ['PATH']),timeout=10)
                return int(result.returncode==0),result.stderr.decode()
            process.outputExecutioner.side_effect=execute
            with self.assertRaisesRegex(RuntimeError,'Permission repair failed'):
                function(manager,'fixture.test')


if __name__ == '__main__':
    unittest.main()
