import argparse
import os
import sys
sys.path.append('/usr/local/CyberCP')
from plogical import CyberCPLogFileWriter as logging
from plogical import backupUtilities as backupUtil
import time
from multiprocessing import Process
import subprocess
import shlex
from shutil import move
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.processUtilities import ProcessUtilities
from plogical.backupSchedule import backupSchedule

class remoteTransferUtilities:

    @staticmethod
    def writeAuthKey(pathToKey):
        try:
            authorized_keys = os.path.join("/root",".ssh","authorized_keys")
            presenseCheck = 0

            try:
                data = open(authorized_keys, "r").readlines()
                for items in data:
                    if items.find(open(pathToKey,"r").read()) > -1:
                        try:
                            os.remove(pathToKey)
                        except:
                            pass
                        print("1,None")
                        return
            except:
                pass

            if presenseCheck == 0:
                writeToFile = open(authorized_keys, 'a')
                writeToFile.writelines("#Added by CyberPanel\n")
                writeToFile.writelines(open(pathToKey,"r").read())
                writeToFile.writelines("\n")
                writeToFile.close()
                try:
                    os.remove(pathToKey)
                except:
                    pass
                print("1,None")
                return

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile("For remote transfer, I am not able to write key to auth file, Error Message: "+str(msg))
            print("0,"+"For remote transfer, I am not able to write key to auth file, Error Message: " + str(msg))

    ## House keeping function to run remote backups
    @staticmethod
    def remoteTransfer(ipAddress, dir, accountsToTransfer):
        try:

            destination = "/home/backup/transfer-" + dir
            backupLogPath = destination + "/backup_log"

            data = open(accountsToTransfer, 'r').readlines()

            accountsToTransfer = []

            for items in data:
                accountsToTransfer.append(items.strip('\n'))

            if not os.path.exists(destination):
                os.makedirs(destination)

            writeToFile = open(backupLogPath, "w+")

            writeToFile.writelines("############################\n")
            writeToFile.writelines("      Starting remote Backup\n")
            writeToFile.writelines("      Start date: " + time.strftime("%m.%d.%Y_%H-%M-%S") + "\n")
            writeToFile.writelines("############################\n")
            writeToFile.writelines("\n")
            writeToFile.writelines("\n")

            if backupUtil.backupUtilities.checkIfHostIsUp(ipAddress) == 1:
                checkConn = backupUtil.backupUtilities.checkConnection(ipAddress)
                if checkConn[0] == 0:
                    writeToFile.writelines("[" + time.strftime(
                        "%m.%d.%Y_%H-%M-%S") + "]" + " Connection to:" + ipAddress + " Failed, please resetup this destination from CyberPanel, aborting. [5010]" + "\n")
                    writeToFile.close()
                    return
                else:
                    pass
            else:
                writeToFile.writelines("[" + time.strftime(
                    "%m.%d.%Y_%H-%M-%S") + "]" + " Host:" + ipAddress + " could be  down, we are continuing..." + "\n")
                writeToFile.close()

            writeToFile.close()

            ## destination = /home/backup/transfer-2558
            ## backupLogPath = /home/backup/transfer-2558/backup_log
            ## dir = 2558
            ## Array of domains to be transferred

            p = Process(target=remoteTransferUtilities.backupProcess,
                        args=(ipAddress, destination, backupLogPath, dir, accountsToTransfer))
            p.start()

            pid = open(destination + '/pid', "w")
            pid.write(str(p.pid))
            pid.close()

            return

        except BaseException as msg:
            writeToFile = open(backupLogPath, "w+")
            writeToFile.writelines(str(msg) + " [5010]" + "\n")
            writeToFile.close()
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [remoteTransfer]")
            return [0, str(msg)]


    ## destination = /home/backup/transfer-2558
    ## backupLogPath = /home/backup/transfer-2558/backup_log
    ## dir = 2558
    ## Array of domains to be transferred

    @staticmethod
    def backupProcess(ipAddress, dir, backupLogPath, folderNumber, accountsToTransfer):
            try:
                ## dir is without forward slash

                for virtualHost in accountsToTransfer:
                    try:

                        writeToFile = open(backupLogPath, "a")
                        writeToFile.writelines("[" + time.strftime(
                            "%m.%d.%Y_%H-%M-%S") + "]" + " Currently generating local backups for: " + virtualHost + "\n")
                        writeToFile.close()

                        retValue = backupSchedule.createLocalBackup(virtualHost, backupLogPath)

                        if retValue[0] == 1:
                            writeToFile = open(backupLogPath, 'a')
                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + " Local Backup Completed for: " + virtualHost + "\n")

                            completePathToBackupFile = retValue[1] + '.tar.gz'

                            ## move the generated backup file to specified destination

                            if os.path.exists(completePathToBackupFile):
                                move(completePathToBackupFile, dir)

                            completedPathToSend = dir + "/" + completePathToBackupFile.split("/")[-1]

                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + " Sending " + completedPathToSend + " to " + ipAddress + ".\n")

                            remoteTransferUtilities.sendBackup(completedPathToSend, ipAddress, str(folderNumber),
                                                               writeToFile)
                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + " Sent " + completedPathToSend + " to " + ipAddress + ".\n")

                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + " #############################################" + "\n")

                            writeToFile.close()
                        else:
                            writeToFile = open(backupLogPath, "a")
                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + "Failed to generate local backup for: " + virtualHost + ". Error message: %s\n" % (retValue[1]))
                            writeToFile.close()

                    except BaseException as msg:
                        logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [remoteTransferUtilities.backupProcess:173]")
                        pass

                writeToFile = open(backupLogPath, "a")
                writeToFile.writelines("[" + time.strftime(
                    "%m.%d.%Y_%H-%M-%S") + "]" + " Backups are successfully generated and received on: " + ipAddress + "\n")
                writeToFile.close()

                ## removing local directory where backups were generated
                #time.sleep(5)
                # rmtree(dir)

            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [backupProcess]")

    @staticmethod
    def sendBackup(completedPathToSend, IPAddress, folderNumber,writeToFile):
        try:
            ## complete path is a path to the file need to send

            command = "sudo scp -o StrictHostKeyChecking=no -i /root/.ssh/cyberpanel " + completedPathToSend + " root@" + IPAddress + ":/home/backup/transfer-" + folderNumber + "/"
            subprocess.call(shlex.split(command), stdout=writeToFile)

            os.remove(completedPathToSend)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

    @staticmethod
    def remoteBackupRestore(backupDir, dir):
        try:

            ## dir is transfer-###
            # backupDir is /home/backup/transfer-###

            backupLogPath = backupDir + "/backup_log"

            writeToFile = open(backupLogPath, "a+")

            writeToFile.writelines("\n")
            writeToFile.writelines("\n")
            writeToFile.writelines("############################\n")
            writeToFile.writelines("      Starting Backup Restore\n")
            writeToFile.writelines("      Start date: " + time.strftime("%m.%d.%Y_%H-%M-%S") + "\n")
            writeToFile.writelines("############################\n")
            writeToFile.writelines("\n")
            writeToFile.writelines("\n")
            writeToFile.close()

            if os.path.exists(backupDir):
                pass
            else:
                writeToFile = open(backupLogPath, "w+")
                writeToFile.writelines(
                    "No such directory found (Local directory where backups are placed does not exists)' [5010]" + "\n")
                writeToFile.close()
                return

            p = Process(target=remoteTransferUtilities.startRestore, args=(backupDir, backupLogPath, dir,))
            p.start()

            pid = open(backupDir + '/pid', "w")
            pid.write(str(p.pid))
            pid.close()

            return

        except BaseException as msg:
            backupLogPath = backupDir + "/backup_log"
            writeToFile = open(backupLogPath, "w+")
            writeToFile.writelines(str(msg) + " [5010]" + "\n")
            writeToFile.close()
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [remoteRestore]")
            return [0, msg]

    @staticmethod
    def startRestore(backupDir, backupLogPath, dir):
        try:
            ext = ".tar.gz"

            for backup in os.listdir(backupDir):

                if backup.endswith(ext):

                    writeToFile = open(backupLogPath, "a")

                    writeToFile.writelines("\n")
                    writeToFile.writelines("\n")
                    writeToFile.writelines("[" + time.strftime(
                        "%m.%d.%Y_%H-%M-%S") + "]" + " Starting restore for: " + backup + ".\n")
                    writeToFile.close()

                    backupFile = backup
                    execPath = "sudo nice -n 10 /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
                    execPath = execPath + " submitRestore --backupFile " + backupFile + " --dir " + dir
                    subprocess.Popen(shlex.split(execPath))
                    time.sleep(4)

                    while (1):
                        time.sleep(1)

                        backupFile = backup.strip(".tar.gz")
                        path = "/home/backup/transfer-" + str(dir) + "/" + backupFile
                        status = open(path + "/status", 'r').read()

                        if status.find("Done") > -1:
                            command = "sudo rm -rf " + path
                            ProcessUtilities.normalExecutioner(command)

                            writeToFile = open(backupLogPath, "a")
                            writeToFile.writelines("\n")
                            writeToFile.writelines("\n")
                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + " Restore Completed for: " + backup + ".\n")
                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + " #########################################\n")
                            writeToFile.close()
                            break
                        elif status.find("[5009]") > -1:
                            ## removing temporarily generated files while restoring
                            command = "sudo rm -rf " + path
                            ProcessUtilities.normalExecutioner(command)

                            writeToFile = open(backupLogPath, "a")
                            writeToFile.writelines("\n")
                            writeToFile.writelines("\n")
                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + " Restore aborted for: " + backup + ". Error message: " +
                                                   status + "\n")
                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + " #########################################\n")
                            writeToFile.close()
                            break
                        else:
                            writeToFile = open(backupLogPath, "a")
                            writeToFile.writelines("\n")
                            writeToFile.writelines("\n")
                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + " Waiting for restore to complete.\n")
                            writeToFile.close()
                            time.sleep(3)
                            pass

            writeToFile = open(backupLogPath, "a")

            writeToFile.writelines("\n")
            writeToFile.writelines("\n")
            writeToFile.writelines("[" + time.strftime(
                "%m.%d.%Y_%H-%M-%S") + "]" + " Backup Restore complete\n")
            writeToFile.writelines("completed[success]")

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [remoteTransferUtilities.startRestore]")


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific function to call!')
    parser.add_argument('--pathToKey', help='')


    ## remote transfer arguments

    parser.add_argument('--ipAddress', help='')
    parser.add_argument('--dir', help='')
    parser.add_argument('--accountsToTransfer', help='')

    ## remote backup restore arguments

    parser.add_argument('--backupDirComplete', help='')
    parser.add_argument('--backupDir', help='')


    args = parser.parse_args()

    if args.function == "writeAuthKey":
        remoteTransferUtilities.writeAuthKey(args.pathToKey)
    elif args.function == "remoteTransfer":
        remoteTransferUtilities.remoteTransfer(args.ipAddress,args.dir,args.accountsToTransfer)
    elif args.function == "remoteBackupRestore":
        remoteTransferUtilities.remoteBackupRestore(args.backupDirComplete,args.backupDir)

if __name__ == "__main__":
    main()