import subprocess

command = 'git -C /home/usman/Backup/CyberCP commit -m "Auto commit by CyberPanel Daily cron on"'
print(subprocess.check_output(command, shell=True).decode("utf-8"))