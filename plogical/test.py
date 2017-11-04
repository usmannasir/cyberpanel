import requests
import json
import pexpect
from CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import time
from backupUtilities import backupUtilities
import signal
import shlex
import subprocess

def verifyHostKey(directory):
    command = "sudo chmod -R 775 " + directory

    print command

    cmd = shlex.shlex(command)

    res = subprocess.call(cmd)



print verifyHostKey("/home/ssl.cyberpanel.net")