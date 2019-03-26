import CyberCPLogFileWriter as logging
import os
import requests
import json
import time
import backupUtilities as backupUtil
import subprocess
import shlex
from multiprocessing import Process
from shutil import move,rmtree

class remoteBackup:


    @staticmethod
    def getKey(ipAddress, password):
        try:
            finalData = json.dumps({'username': "admin", "password": password})
            url = "https://" + ipAddress + ":8090/api/fetchSSHkey"
            r = requests.post(url, data=finalData, verify=False)
            data = json.loads(r.text)

            if data['pubKeyStatus'] == 1:
                return [1, data["pubKey"]]
            else:
                return [0, data['error_message']]

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [getKey]")
            return [0,"Not able to fetch key from remote server, Error Message:" + str(msg)]

    @staticmethod
    def startRestore(backupDir,backupLogPath,dir):
        try:
            ext = ".tar.gz"

            for backup in os.listdir(backupDir):

                if backup.endswith(ext):

                    writeToFile = open(backupLogPath, "a")

                    writeToFile.writelines("\n")
                    writeToFile.writelines("\n")
                    writeToFile.writelines("[" + time.strftime(
                        "%I-%M-%S-%a-%b-%Y") + "]" + " Starting restore for: "+backup+".\n")
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
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " Restore aborted for: " + backup + ". Error message: "+data['status']+"\n")
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
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateRestore]")

    @staticmethod
    def remoteRestore(backupDir, dir):
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
                return [0, 'No such directory found']


            p = Process(target=remoteBackup.startRestore, args=(backupDir, backupLogPath,dir,))
            p.start()

            return [1, 'Started']

            pid = open(destination + '/pid', "w")
            pid.write(str(p.pid))
            pid.close()

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [remoteRestore]")
            return [0, msg]

    @staticmethod
    def postRemoteTransfer(ipAddress, ownIP ,password, sshkey):
        try:
            finalData = json.dumps({'username': "admin", "ipAddress": ownIP, "password": password})
            url = "https://" + ipAddress + ":8090/api/remoteTransfer"
            r = requests.post(url, data=finalData, verify=False)
            data = json.loads(r.text)

            if data['transferStatus'] == 1:
                path = "/home/backup/transfer-"+data['dir']
                if not os.path.exists(path):
                    os.makedirs(path)
                return [1, data['dir']]
            else:
                return [0, data['error_message']]

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [postRemoteTransfer]")
            return [0, msg]

    @staticmethod
    def createBackup(virtualHost, ipAddress,writeToFile, dir):
        try:
            writeToFile.writelines("Location: "+dir + "\n")
            writeToFile.writelines("["+time.strftime("%I-%M-%S-%a-%b-%Y")+"]"+" Preparing to create backup for: "+virtualHost+"\n")
            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + " Backup started for: " + virtualHost + "\n")

            finalData = json.dumps({'websiteToBeBacked': virtualHost})
            r = requests.post("http://localhost:5003/backup/submitBackupCreation", data=finalData,verify=False)
            data = json.loads(r.text)
            backupPath = data['tempStorage']


            while (1):
                r = requests.post("http://localhost:5003/backup/backupStatus", data= finalData,verify=False)
                time.sleep(2)
                data = json.loads(r.text)

                if data['status'] == 0:
                    break

            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + " Backup created for:" + virtualHost + "\n")

            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + " Preparing to send backup for: " + virtualHost +" to "+ipAddress+ "\n")
            writeToFile.flush()

            remoteBackup.sendBackup(backupPath+".tar.gz", ipAddress,writeToFile, dir)

            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + "  Backup for: " + virtualHost + " is sent to " + ipAddress + "\n")

            writeToFile.writelines("\n")
            writeToFile.writelines("\n")

            writeToFile.writelines("#####################################")

            writeToFile.writelines("\n")
            writeToFile.writelines("\n")

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")


    @staticmethod
    def sendBackup(completedPathToSend, IPAddress, folderNumber,writeToFile):
        try:
            ## complete path is a path to the file need to send

            command = 'sudo rsync -avz -e "ssh  -i /root/.ssh/cyberpanel -o StrictHostKeyChecking=no" ' + completedPathToSend + ' root@' + IPAddress + ':/home/backup/transfer-'+folderNumber
            subprocess.call(shlex.split(command), stdout=writeToFile)
            os.remove(completedPathToSend)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

    @staticmethod
    def backupProcess(ipAddress, dir, backupLogPath,folderNumber,accountsToTransfer):
        try:
            ## dir is without forward slash

            for virtualHost in accountsToTransfer:

                try:

                    if virtualHost == "vmail" or virtualHost == "backup":
                        continue

                    writeToFile = open(backupLogPath, "a")
                    writeToFile.writelines("[" + time.strftime(
                        "%I-%M-%S-%a-%b-%Y") + "]" + " Currently generating local backups for: " + virtualHost + "\n")
                    writeToFile.close()


                    finalData = json.dumps({'websiteToBeBacked': virtualHost})
                    r = requests.post("http://localhost:5003/backup/submitBackupCreation", data=finalData,verify=False)

                    data = json.loads(r.text)

                    fileName = data['tempStorage']+".tar.gz"

                    completePathToBackupFile = fileName


                    while (1):
                        time.sleep(2)
                        r = requests.post("http://localhost:5003/backup/backupStatus", data= finalData,verify=False)
                        data = json.loads(r.text)

                        writeToFile = open(backupLogPath, "a")

                        writeToFile.writelines("[" + time.strftime(
                            "%I-%M-%S-%a-%b-%Y") + "]" + " Waiting for backup to complete.. " + "\n")

                        writeToFile.close()


                        if data['abort'] == 1:

                            writeToFile = open(backupLogPath, "a")

                            writeToFile.writelines("[" + time.strftime(
                                "%I-%M-%S-%a-%b-%Y") + "]" + " Local Backup Completed for: " +virtualHost + " with status: "+ data['status'] +"\n")


                            ## move the generated backup file to specified destination

                            if os.path.exists(completePathToBackupFile):
                                move(completePathToBackupFile,dir)

                            completedPathToSend = dir +"/" + completePathToBackupFile.split("/")[-1]

                            writeToFile.writelines("[" + time.strftime(
                                "%I-%M-%S-%a-%b-%Y") + "]" + " Sending " + completedPathToSend +" to "+ipAddress +".\n")


                            remoteBackup.sendBackup(completedPathToSend,ipAddress,str(folderNumber),writeToFile)

                            writeToFile.writelines("[" + time.strftime(
                                "%I-%M-%S-%a-%b-%Y") + "]" + " Sent " + completedPathToSend + " to " + ipAddress + ".\n")

                            writeToFile.writelines("[" + time.strftime(
                                "%I-%M-%S-%a-%b-%Y") + "]" + " #############################################" + "\n")

                            writeToFile.close()
                            break
                except:
                    pass

            writeToFile = open(backupLogPath, "a")
            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + " Backups are successfully generated and received on: " + ipAddress + "\n")
            writeToFile.close()

            ## removing local directory where backups were generated
            time.sleep(5)
            #rmtree(dir)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [backupProcess]")

    @staticmethod
    def remoteTransfer(ipAddress, dir,accountsToTransfer):
        try:

            destination = "/home/backup/transfer-" + dir
            backupLogPath = destination + "/backup_log"

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
                        "%I-%M-%S-%a-%b-%Y") + "]" + " Connection to:" + ipAddress + " Failed, please resetup this destination from CyberPanel, aborting." + "\n")
                    writeToFile.close()
                    return [0, checkConn[1]]
                else:
                    pass
            else:
                writeToFile.writelines("[" + time.strftime(
                    "%I-%M-%S-%a-%b-%Y") + "]" + " Host:" + ipAddress + " is down, aborting." + "\n")
                writeToFile.close()
                return [0, "Remote server is not able to communicate with this server."]

            writeToFile.close()


            p = Process(target=remoteBackup.backupProcess, args=(ipAddress, destination, backupLogPath,dir,accountsToTransfer))
            p.start()

            pid = open(destination + '/pid', "w")
            pid.write(str(p.pid))
            pid.close()

            return [1, None]

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [remoteTransfer]")
            return [0, msg]

