import sys
import subprocess
import shutil
import argparse
import os
import shlex
import time
import string
import random

def setupVirtualEnv():
    ##


    command = "yum install -y libattr-devel xz-devel gpgme-devel mariadb-devel curl-devel"
    res = subprocess.call(shlex.split(command))

    ##


    command = "pip install virtualenv"
    res = subprocess.call(shlex.split(command))

    ####

    command = "virtualenv /usr/local/CyberCP"
    res = subprocess.call(shlex.split(command))

    ##
    env_path = '/usr/local/CyberCP'
    if not os.path.exists(env_path):
        subprocess.call(['virtualenv', env_path])
        activate_this = os.path.join(env_path, 'bin', 'activate_this.py')
        execfile(activate_this, dict(__file__=activate_this))

    command = "pip install -r /usr/local/CyberCP/requirments.txt"
    res = subprocess.call(shlex.split(command))

    ##

    command = "systemctl restart gunicorn.socket"
    res = subprocess.call(shlex.split(command))


setupVirtualEnv()