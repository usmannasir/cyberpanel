import subprocess
subprocess.run(self.command, capture_output=self.capture_output, text=True, shell=self.shell)
if subprocess.run('uname -a', check=True, shell=True).find('arch64') ==-1:
    pass
else:
    print('arch64')