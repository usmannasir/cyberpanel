import argparse
import os
import CyberCPLogFileWriter as logging
import remoteBackup as rBackup
import backupUtilities as backupUtil
import time
from multiprocessing import Process
import json
import requests
import subprocess
import shlex
from shutil import move

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
                        print "1,None"
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
                print "1,None"
                return

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile("For remote transfer, I am not able to write key to auth file, Error Message: "+str(msg))
            print "0,"+"For remote transfer, I am not able to write key to auth file, Error Message: " + str(msg)

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
            writeToFile.writelines("      Start date: " + time.strftime("%I-%M-%S-%a-%b-%Y") + "\n")
            writeToFile.writelines("############################\n")
            writeToFile.writelines("\n")
            writeToFile.writelines("\n")

            if backupUtil.backupUtilities.checkIfHostIsUp(ipAddress) == 1:
                checkConn = backupUtil.backupUtilities.checkConnection(ipAddress)
                if checkConn[0] == 0:
                    writeToFile.writelines("[" + time.strftime(
                        "%I-%M-%S-%a-%b-%Y") + "]" + " Connection to:" + ipAddress + " Failed, please resetup this destination from CyberPanel, aborting. [5010]" + "\n")
                    writeToFile.close()
                    return
                else:
                    pass
            else:
                writeToFile.writelines("[" + time.strftime(
                    "%I-%M-%S-%a-%b-%Y") + "]" + " Host:" + ipAddress + " is down, aborting. [5010]" + "\n")
                writeToFile.close()
                return

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

        except BaseException, msg:
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
                            "%I-%M-%S-%a-%b-%Y") + "]" + " Currently generating local backups for: " + virtualHost + "\n")
                        writeToFile.close()

                        finalData = json.dumps({'websiteToBeBacked': virtualHost})
                        r = requests.post("http://localhost:5003/backup/submitBackupCreation", data=finalData,
                                          verify=False)

                        data = json.loads(r.text)

                        fileName = data['tempStorage'] + ".tar.gz"

                        completePathToBackupFile = fileName

                        while (1):
                            time.sleep(2)
                            r = requests.post("http://localhost:5003/backup/backupStatus", data=finalData, verify=False)
                            data = json.loads(r.text)

                            writeToFile = open(backupLogPath, "a")

                            writeToFile.writelines("[" + time.strftime(
                                "%I-%M-%S-%a-%b-%Y") + "]" + " Waiting for backup to complete.. " + "\n")

                            writeToFile.close()

                            if data['backupStatus'] == 0:
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + "Failed to generate local backup for: " + virtualHost + ". Error message: " +
                                                       data['error_message'] + "\n")
                                break

                            elif data['abort'] == 1:

                                writeToFile = open(backupLogPath, "a")

                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " Local Backup Completed for: " + virtualHost + " with status: " +
                                                       data['status'] + "\n")

                                ## move the generated backup file to specified destination

                                if os.path.exists(completePathToBackupFile):
                                    move(completePathToBackupFile, dir)

                                completedPathToSend = dir + "/" + completePathToBackupFile.split("/")[-1]

                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " Sending " + completedPathToSend + " to " + ipAddress + ".\n")

                                remoteTransferUtilities.sendBackup(completedPathToSend, ipAddress, str(folderNumber), writeToFile)

                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " Sent " + completedPathToSend + " to " + ipAddress + ".\n")

                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " #############################################" + "\n")

                                writeToFile.close()
                                break
                    except BaseException, msg:
                        logging.CyberCPLogFileWriter.writeToFile(str(msg))
                        pass

                writeToFile = open(backupLogPath, "a")
                writeToFile.writelines("[" + time.strftime(
                    "%I-%M-%S-%a-%b-%Y") + "]" + " Backups are successfully generated and received on: " + ipAddress + "\n")
                writeToFile.close()

                ## removing local directory where backups were generated
                #time.sleep(5)
                # rmtree(dir)

            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [backupProcess]")

    @staticmethod
    def sendBackup(completedPathToSend, IPAddress, folderNumber,writeToFile):
        try:
            ## complete path is a path to the file need to send

            command = "sudo scp -o StrictHostKeyChecking=no -i /root/.ssh/cyberpanel " + completedPathToSend + " root@" + IPAddress + ":/home/backup/transfer-" + folderNumber + "/"
            subprocess.call(shlex.split(command), stdout=writeToFile)

        except BaseException, msg:
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
            writeToFile.writelines("      Start date: " + time.strftime("%I-%M-%S-%a-%b-%Y") + "\n")
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

        except BaseException, msg:
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
                        "%I-%M-%S-%a-%b-%Y") + "]" + " Starting restore for: " + backup + ".\n")
                    writeToFile.close()

                    finalData = json.dumps({'backupFile': backup, "dir": dir})
                    r = requests.post("http://localhost:5003/backup/submitRestore", data=finalData, verify=False)
                    data = json.loads(r.text)

                    if data['restoreStatus'] == 1:
                        while (1):
                            time.sleep(1)
                            finalData = json.dumps({'backupFile': backup, "dir": dir})
                            r = requests.post("http://localhost:5003/backup/restoreStatus", data=finalData,
                                              verify=False)
                            data = json.loads(r.text)

                            if data['abort'] == 1 and data['running'] == "Error":
                                writeToFile = open(backupLogPath, "a")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " Restore aborted for: " + backup + ". Error message: " +
                                                       data['status'] + "\n")
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " #########################################\n")
                                writeToFile.close()
                                break
                            elif data['abort'] == 1 and data['running'] == "Completed":
                                writeToFile = open(backupLogPath, "a")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " Restore Completed for: " + backup + ".\n")
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " #########################################\n")
                                writeToFile.close()
                                break
                            else:
                                writeToFile = open(backupLogPath, "a")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " Waiting for restore to complete.\n")
                                writeToFile.close()
                                time.sleep(3)
                                pass
                    else:
                        logging.CyberCPLogFileWriter.writeToFile("Could not start restore process for: " + backup)
                        writeToFile = open(backupLogPath, "a")
                        writeToFile.writelines("\n")
                        writeToFile.writelines("\n")
                        writeToFile.writelines("[" + time.strftime(
                            "%I-%M-%S-%a-%b-%Y") + "]" + "Could not start restore process for: " + backup + "\n")
                        writeToFile.close()

            writeToFile = open(backupLogPath, "a")

            writeToFile.writelines("\n")
            writeToFile.writelines("\n")
            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + " Backup Restore complete\n")
            writeToFile.writelines("completed[success]")


        except BaseException, msg:
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