"""A daemon launched during upgrade must not hold the upgrade's output pipe."""
import ast
from pathlib import Path
import os
import shlex
import signal
import subprocess
import sys
import tempfile
import textwrap
import unittest

SOURCE = Path(__file__).with_name('upgrade.py').read_text()

class UpgradeDaemonOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pid_file = self.root/'daemon.pid'
        self.addCleanup(self.stop_daemon)
        tree=ast.parse(SOURCE)
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Upgrade')
        cls.body=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='executioner']
        self.definition=ast.unparse(ast.Module(body=[cls],type_ignores=[]))
    def stop_daemon(self):
        if self.pid_file.exists():
            try: os.kill(int(self.pid_file.read_text()),signal.SIGTERM)
            except ProcessLookupError: pass
    def run_launcher(self, body):
        launcher=self.root/'launcher.py'
        launcher.write_text(body)
        command=shlex.join([sys.executable,str(launcher)])
        harness='import os, sys, shlex, subprocess, tempfile\n'+self.definition+'\n'
        harness+='Upgrade.stdOut = staticmethod(lambda *args: print(*args, flush=True))\n'
        harness+='sys.exit(0 if Upgrade.executioner('+repr(command)+', "service launch", detach_output=True) else 1)\n'
        return subprocess.run([sys.executable,'-c',harness],capture_output=True,text=True,timeout=5)
    def test_running_daemon_cannot_hold_upgrade_logging_pipe_open(self):
        body=textwrap.dedent('''
            import os, subprocess, sys
            from pathlib import Path
            child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],
                                   stdout=sys.stdout,stderr=sys.stderr)
            Path(PID_FILE).write_text(str(child.pid))
            print('service launcher completed',flush=True)
        ''').replace('PID_FILE',repr(str(self.pid_file)))
        result=self.run_launcher(body)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertIn('service launcher completed',result.stdout)
        os.kill(int(self.pid_file.read_text()),0)  # The daemon is still alive.
    def test_failed_launch_keeps_diagnostics_and_failure(self):
        result=self.run_launcher("import sys\nprint('service cannot start',flush=True)\nsys.exit(7)\n")
        self.assertNotEqual(0,result.returncode)
        self.assertEqual(3,result.stdout.count('service cannot start'))
        self.assertIn('service launch failed.',result.stdout)
    def test_ols_start_requests_detached_output(self):
        tree=ast.parse(SOURCE)
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)
               and any(isinstance(a,ast.Constant) and a.value=='Start OpenLiteSpeed' for a in n.args)]
        self.assertEqual(1,len(calls))
        self.assertTrue(any(k.arg=='detach_output' and isinstance(k.value,ast.Constant)
                            and k.value.value is True for k in calls[0].keywords))

if __name__ == '__main__':
    unittest.main()
