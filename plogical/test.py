import subprocess, shlex
command = 'yum list | grep lsphp | xargs -n3 | column -t'
result = subprocess.check_output(command, shell=True).splitlines()
for item in result:
    print(item.split(b' '))
