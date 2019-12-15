import subprocess
import shlex

print (subprocess.check_output(shlex.split('ls -la')).decode("utf-8"))