#!/usr/local/CyberCP/bin/python
import sys
sys.path.append('/usr/local/CyberCP')
import subprocess, shlex
import os


class UpgradeCritical:
    @staticmethod
    def executioner(command):
        try:
            FNULL = open(os.devnull, 'w')

            res = subprocess.call(shlex.split(command), stdout=FNULL)
            if res == 0:
                return 1
            else:
                return 0
        except BaseException as msg:
            return 0

    @staticmethod
    def UpgradeImportantPackages():
        if os.path.exists('/etc/lsb-release'):

            command = "DEBIAN_FRONTEND=noninteractive apt-get install --only-upgrade pdns-server pdns-backend-mysql install dovecot-imapd dovecot-pop3d postfix-mysql pure-ftpd postfix dovecot-mysql  -y"
            UpgradeCritical.executioner(command)
        else:
            command = "yum update"
            UpgradeCritical.executioner(command)

            command = "yum -y upgrade pdns pdns-backend-mysql pure-ftpd postfix dovecot dovecot-mysql"
            UpgradeCritical.executioner(command)



def main():

    UpgradeCritical.UpgradeImportantPackages()


if __name__ == "__main__":
    main()