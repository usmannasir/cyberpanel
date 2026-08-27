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
from shutil import move, rmtree
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.processUtilities import ProcessUtilities
from plogical.backupSchedule import backupSchedule
from plogical.backupArchive import archive_path_without_suffix

class remoteTransferUtilities:

    RESTORE_STATUS_TIMEOUT = 120
    RESTORE_POLL_INTERVAL = 1

    @staticmethod
    def _appendRestoreLog(backupLogPath, message):
        with open(backupLogPath, "a") as writeToFile:
            writeToFile.writelines("[" + time.strftime(
                "%m.%d.%Y_%H-%M-%S") + "] " + message + "\n")

    @staticmethod
    def _restoreStatusPath(backupDir, backup):
        backupName = archive_path_without_suffix(backup)
        path = os.path.join(backupDir, backupName)
        backupRoot = os.path.realpath(backupDir)
        if os.path.commonpath((backupRoot, os.path.realpath(path))) != backupRoot:
            raise ValueError('Invalid backup archive path')
        return path, os.path.join(path, 'status')

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
    def remoteTransfer(ipAddress, dir, accountsToTransfer, sshPort='22'):
        try:

            destination = "/home/backup/transfer-" + dir
            backupLogPath = destination + "/backup_log"

            data = open(accountsToTransfer, 'r').readlines()

            accountsToTransfer = []

            for items in data:
                accountsToTransfer.append(items.strip('\n'))

            if not os.path.exists(destination):
                os.makedirs(destination)

            command = 'chmod 600 %s' % (destination)
            ProcessUtilities.executioner(command)

            writeToFile = open(backupLogPath, "w+")

            writeToFile.writelines("############################\n")
            writeToFile.writelines("      Starting remote Backup\n")
            writeToFile.writelines("      Start date: " + time.strftime("%m.%d.%Y_%H-%M-%S") + "\n")
            writeToFile.writelines("############################\n")
            writeToFile.writelines("\n")
            writeToFile.writelines("\n")

            if backupUtil.backupUtilities.checkIfHostIsUp(ipAddress) == 1:
                checkConn = backupUtil.backupUtilities.checkConnection(
                    ipAddress, str(sshPort)
                )
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
                        args=(ipAddress, destination, backupLogPath, dir,
                              accountsToTransfer, str(sshPort)))
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
    def backupProcess(ipAddress, dir, backupLogPath, folderNumber,
                      accountsToTransfer, sshPort='22'):
            try:
                ## dir is without forward slash

                allBackupsSent = True
                backupsAttempted = 0

                for virtualHost in accountsToTransfer:
                    try:

                        writeToFile = open(backupLogPath, "a")
                        writeToFile.writelines("[" + time.strftime(
                            "%m.%d.%Y_%H-%M-%S") + "]" + " Currently generating local backups for: " + virtualHost + "\n")
                        writeToFile.close()

                        retValue = backupSchedule.createLocalBackup(virtualHost, backupLogPath)

                        if retValue[0] == 1:
                            backupsAttempted += 1
                            writeToFile = open(backupLogPath, 'a')
                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + " Local Backup Completed for: " + virtualHost + "\n")

                            completePathToBackupFile = retValue[1] + '.tar.gz'

                            ### change permissions of backup file

                            command = 'chmod 600 %s' % (completePathToBackupFile)
                            ProcessUtilities.executioner(command)

                            ## move the generated backup file to specified destination

                            if os.path.exists(completePathToBackupFile):
                                move(completePathToBackupFile, dir)

                            completedPathToSend = dir + "/" + completePathToBackupFile.split("/")[-1]

                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + " Sending " + completedPathToSend + " to " + ipAddress + ".\n")

                            sent = remoteTransferUtilities.sendBackup(
                                completedPathToSend,
                                ipAddress,
                                str(folderNumber),
                                writeToFile,
                                str(sshPort),
                            )
                            if sent:
                                writeToFile.writelines("[" + time.strftime(
                                    "%m.%d.%Y_%H-%M-%S") + "]" + " Sent " + completedPathToSend + " to " + ipAddress + ".\n")
                            else:
                                allBackupsSent = False

                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + " #############################################" + "\n")

                            writeToFile.close()
                        else:
                            allBackupsSent = False
                            writeToFile = open(backupLogPath, "a")
                            writeToFile.writelines("[" + time.strftime(
                                "%m.%d.%Y_%H-%M-%S") + "]" + "Failed to generate local backup for: " + virtualHost + ". Error message: %s\n" % (retValue[1]))
                            writeToFile.close()

                    except BaseException as msg:
                        allBackupsSent = False
                        logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [remoteTransferUtilities.backupProcess:173]")
                        remoteTransferUtilities._appendRestoreLog(
                            backupLogPath,
                            "Backup or transfer failed for: " + virtualHost +
                            ". Error message: " + str(msg) + " [5010]",
                        )

                writeToFile = open(backupLogPath, "a")
                if (allBackupsSent and backupsAttempted > 0 and
                        backupsAttempted == len(accountsToTransfer)):
                    writeToFile.writelines("[" + time.strftime(
                        "%m.%d.%Y_%H-%M-%S") + "]" + " Backups are successfully generated and received on: " + ipAddress + "\n")
                else:
                    writeToFile.writelines("[" + time.strftime(
                        "%m.%d.%Y_%H-%M-%S") + "]" +
                        " Backup transfer finished with errors. [5010]\n")
                writeToFile.close()

                ## removing local directory where backups were generated
                #time.sleep(5)
                # rmtree(dir)

            except BaseException as msg:
                writeToFile = open(backupLogPath, "a")
                writeToFile.writelines("[" + time.strftime(
                    "%m.%d.%Y_%H-%M-%S") + "]" + " Backups are not generated "  "\n")
                writeToFile.close()
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [backupProcess]")

    @staticmethod
    def sendBackup(completedPathToSend, IPAddress, folderNumber, writeToFile,
                   sshPort='22'):
        try:
            ## complete path is a path to the file need to send
            command = "sudo scp -o StrictHostKeyChecking=no -i /root/.ssh/cyberpanel -P "+ sshPort + " " + completedPathToSend + " root@" + IPAddress + ":/home/backup/transfer-" + folderNumber + "/"
            return_Code = subprocess.call(shlex.split(command), stdout=writeToFile)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(command)

            if return_Code == 0:
                logging.CyberCPLogFileWriter.writeToFile("Remote backup file sent: %s" % completedPathToSend)
                writeToFile.writelines("[" + time.strftime(
                    "%m.%d.%Y_%H-%M-%S") + "]" + " Transfer of " + completedPathToSend + " completed successfully.\n")
                ## Only remove the local copy once the transfer is confirmed.
                os.remove(completedPathToSend)
                return True
            else:
                logging.CyberCPLogFileWriter.writeToFile(
                    "Remote backup transfer FAILED (scp exit %s): %s" % (return_Code, completedPathToSend))
                writeToFile.writelines("[" + time.strftime(
                    "%m.%d.%Y_%H-%M-%S") + "]" + " Transfer of " + completedPathToSend + " FAILED (scp exit code " + str(return_Code) + "). Local copy kept. [5010]\n")
                return False

        except BaseException as msg:
            try:
                writeToFile.writelines("[" + time.strftime(
                    "%m.%d.%Y_%H-%M-%S") + "]" + " Error while sending backup: " + str(msg) + " [5010]\n")
            except:
                pass
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [sendBackup]")
            return False

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

            backups = sorted(
                backup for backup in os.listdir(backupDir)
                if backup.endswith(ext)
                and os.path.isfile(os.path.join(backupDir, backup))
                and not os.path.islink(os.path.join(backupDir, backup))
            )
            if not backups:
                raise RuntimeError('No backup archives were found in the transfer directory')

            restoreFailed = False

            for backup in backups:
                remoteTransferUtilities._appendRestoreLog(
                    backupLogPath, "Starting restore for: " + backup + "."
                )

                path, statusPath = remoteTransferUtilities._restoreStatusPath(
                    backupDir, backup
                )
                if os.path.exists(path):
                    rmtree(path)

                execArgs = [
                    'sudo', 'nice', '-n', '10',
                    '/usr/local/CyberCP/bin/python',
                    virtualHostUtilities.cyberPanel + '/plogical/backupUtilities.py',
                    'submitRestore', '--backupFile', backup, '--dir', str(dir),
                ]
                restoreLauncher = subprocess.Popen(execArgs)
                statusDeadline = time.monotonic() + remoteTransferUtilities.RESTORE_STATUS_TIMEOUT

                while not os.path.exists(statusPath):
                    if time.monotonic() >= statusDeadline:
                        exitCode = restoreLauncher.poll()
                        raise RuntimeError(
                            'Restore status was not created for %s within %s seconds '
                            '(launcher exit code: %s)' % (
                                backup,
                                remoteTransferUtilities.RESTORE_STATUS_TIMEOUT,
                                str(exitCode),
                            )
                        )
                    time.sleep(remoteTransferUtilities.RESTORE_POLL_INTERVAL)

                while True:
                    with open(statusPath, 'r') as statusFile:
                        status = statusFile.read()

                    if status.find("Done") > -1:
                        rmtree(path)
                        remoteTransferUtilities._appendRestoreLog(
                            backupLogPath, "Restore completed for: " + backup + "."
                        )
                        break
                    elif status.find("[5009]") > -1:
                        restoreFailed = True
                        remoteTransferUtilities._appendRestoreLog(
                            backupLogPath,
                            "Restore aborted for: " + backup + ". Error message: " + status,
                        )
                        break
                    else:
                        remoteTransferUtilities._appendRestoreLog(
                            backupLogPath, "Waiting for restore to complete: " + backup + "."
                        )
                        time.sleep(4)

            if restoreFailed:
                remoteTransferUtilities._appendRestoreLog(
                    backupLogPath, "Backup restore finished with errors."
                )
                with open(backupLogPath, "a") as writeToFile:
                    writeToFile.writelines("completed[failed]")
            else:
                remoteTransferUtilities._appendRestoreLog(
                    backupLogPath, "Backup restore complete."
                )
                with open(backupLogPath, "a") as writeToFile:
                    writeToFile.writelines("completed[success]")

        except BaseException as msg:
            remoteTransferUtilities._appendRestoreLog(
                backupLogPath, "Backup restore failed: " + str(msg)
            )
            with open(backupLogPath, "a") as writeToFile:
                writeToFile.writelines("completed[failed]")
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [remoteTransferUtilities.startRestore]")


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific function to call!')
    parser.add_argument('--pathToKey', help='')


    ## remote transfer arguments

    parser.add_argument('--ipAddress', help='')
    parser.add_argument('--dir', help='')
    parser.add_argument('--accountsToTransfer', help='')
    parser.add_argument('--port', default='22', help='')

    ## remote backup restore arguments

    parser.add_argument('--backupDirComplete', help='')
    parser.add_argument('--backupDir', help='')


    args = parser.parse_args()

    if args.function == "writeAuthKey":
        remoteTransferUtilities.writeAuthKey(args.pathToKey)
    elif args.function == "remoteTransfer":
        remoteTransferUtilities.remoteTransfer(
            args.ipAddress, args.dir, args.accountsToTransfer, args.port
        )
    elif args.function == "remoteBackupRestore":
        remoteTransferUtilities.remoteBackupRestore(args.backupDirComplete,args.backupDir)

if __name__ == "__main__":
    main()
