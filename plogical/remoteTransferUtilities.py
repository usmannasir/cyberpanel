import argparse
import os
import CyberCPLogFileWriter as logging
import remoteBackup as rBackup
import backupUtilities as backupUtil
import time
from multiprocessing import Process

class remoteTransferUtilities:

    @staticmethod
    def writeAuthKey(pathToKey):
        try:
            authorized_keys = "/root/.ssh/authorized_keys"
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
            print "0,"+"For remote transfer, I am not able to write key to auth file, Error Message: "+str(msg)

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
                writeToFile.writelines("No such directory found (Local directory where backups are placed does not exists)' [5010]" + "\n")
                writeToFile.close()
                return


            p = Process(target=rBackup.remoteBackup.startRestore, args=(backupDir, backupLogPath,dir,))
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
    def remoteTransfer(ipAddress,dir,accountsToTransfer):
        try:

            destination = "/home/backup/transfer-" + dir
            backupLogPath = destination + "/backup_log"

            accountsToTransfer = accountsToTransfer.split(",")

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

            p = Process(target=rBackup.remoteBackup.backupProcess,
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
            return [0, msg]


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
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