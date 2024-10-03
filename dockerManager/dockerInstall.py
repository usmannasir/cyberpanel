#!/usr/local/CyberCP/bin/python
import os
import sys
sys.path.append('/usr/local/CyberCP')
import plogical.CyberCPLogFileWriter as logging
from serverStatus.serverStatusUtil import ServerStatusUtil
from plogical.processUtilities import ProcessUtilities
import time


class DockerInstall:

    @staticmethod
    def submitInstallDocker(CommandCP = 0):
        try:

            statusFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Starting Docker Installation..\n", 1)

            if ProcessUtilities.decideDistro() == ProcessUtilities.cent8:

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile(f'Docker installation started for cent8/9')

                command = 'sudo yum install -y yum-utils'
                ServerStatusUtil.executioner(command, statusFile)

                command = 'yum install yum-utils -y'
                ServerStatusUtil.executioner(command, statusFile)

                command = 'yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo'
                ServerStatusUtil.executioner(command, statusFile)

                command = 'sudo dnf install docker-ce docker-ce-cli containerd.io docker-compose-plugin --allowerasing -y'
            elif ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                command = 'sudo yum install -y docker'
            else:
                command = 'DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose'

            if CommandCP:
                ProcessUtilities.executioner(command, 'root', True)
            else:
                if not ServerStatusUtil.executioner(command, statusFile):
                    logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                              "Failed to install Docker. [404]\n", 1)
                    return 0

            command = 'sudo systemctl enable docker'

            ProcessUtilities.executioner(command, 'root', True)

            command = 'sudo systemctl start docker'
            ProcessUtilities.executioner(command, 'root', True)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Docker successfully installed.[200]\n", 1)

            time.sleep(2)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)
def main():
    DockerInstall.submitInstallDocker()

if __name__ == "__main__":
    main()