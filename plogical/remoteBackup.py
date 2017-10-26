import thread
import CyberCPLogFileWriter as logging
import subprocess
import os
import requests
import json
import time
import backupUtilities as backupUtil

import subprocess
import shlex
import tarfile
from packages.models import Package
from websiteFunctions.models import Websites
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.installUtilities import installUtilities
from plogical.mysqlUtilities import mysqlUtilities
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
            return [0, msg]

    @staticmethod
    def startRestoreTemp(backupName, backupDir, admin, backupLogPath):
        try:
            adminEmail = admin.email

            writeToFile = open(backupLogPath, "a")

            writeToFile.writelines("\n")
            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + " Preparing restore for: " + backupName + "\n")
            writeToFile.writelines("\n")

            backupFileName = backupName.strip(".tar.gz")

            completPath = backupDir + "/" + backupFileName
            originalFile = backupDir + "/" + backupName

            pathToCompressedHome = completPath + "/public_html.tar.gz"

            if not os.path.exists(completPath):
                os.mkdir(completPath)

            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + "Extracting Main Archive\n")

            status = open(completPath + '/status', "w")
            status.write("Extracting Main Archive")
            status.close()

            tar = tarfile.open(originalFile)
            tar.extractall(completPath)
            tar.close()

            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + " UnTar File for backup: " + backupName + "\n")

            status = open(completPath + '/status', "w")
            status.write("Creating Account and databases")
            status.close()

            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + "Creating account and databases\n")

            phpSelection = "PHP 7.0"

            data = open(completPath + "/meta", 'r').readlines()
            domain = data[0].strip('\n')

            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + " Domain for " + backupName + " found: "+domain+"\n")

            try:
                website = Websites.objects.get(domain=domain)

                status = open(completPath + '/status', "w")
                status.write("Website already exists")
                status.close()

                writeToFile.writelines("[" + time.strftime(
                    "%I-%M-%S-%a-%b-%Y") + "]" + " Domain  "+domain+" already exists. Skipping backup file.\n")

                return 0
            except:
                pass

            check = 0
            for items in data:
                if check == 0:
                    if virtualHostUtilities.createDirectoryForVirtualHost(domain, adminEmail, phpSelection) != 1:
                        numberOfWebsites = Websites.objects.count()
                        virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)

                        writeToFile.writelines("[" + time.strftime(
                            "%I-%M-%S-%a-%b-%Y") + "]" + " Unable to create configuration, see CyberCP main login file. Skipping backup file.\n")
                        return 0

                    if virtualHostUtilities.createConfigInMainVirtualHostFile(domain) != 1:
                        numberOfWebsites = Websites.objects.count()
                        virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)
                        writeToFile.writelines("[" + time.strftime(
                            "%I-%M-%S-%a-%b-%Y") + "]" + "Can not create configurations, see CyberCP main log file. Skipping backup file.\n")
                        return 0


                    selectedPackage = Package.objects.get(packageName="Default")

                    website = Websites(admin=admin, package=selectedPackage, domain=domain, adminEmail=adminEmail,
                                       phpSelection=phpSelection, ssl=0)

                    website.save()

                    writeToFile.writelines("[" + time.strftime(
                        "%I-%M-%S-%a-%b-%Y") + "]" + "Saved Configuration for domain\n")

                    check = check + 1
                else:
                    dbData = items.split('-')
                    mysqlUtilities.createDatabase(dbData[0], dbData[1], "cyberpanel")
                    newDB = Databases(website=website, dbName=dbData[0], dbUser=dbData[1])
                    newDB.save()

            status = open(path + '/status', "w")
            status.write("Accounts and DBs Created")
            status.close()

            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + "Accounts and DBs Created\n")

            data = open(completPath + "/meta", 'r').readlines()
            domain = data[0].strip('\n')
            websiteHome = "/home/" + domain + "/public_html"

            check = 0

            status = open(completPath + '/status', "w")
            status.write("Restoring Databases")
            status.close()

            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + "Restoring Databases\n")

            for items in data:
                if check == 0:
                    check = check + 1
                    continue
                else:
                    dbData = items.split('-')
                    mysqlUtilities.mysqlUtilities.restoreDatabaseBackup(dbData[0], completPath, dbData[2].strip('\n'))

            status = open(completPath + '/status', "w")
            status.write("Extracting web home data")
            status.close()

            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + "Extracting Web Home Data\n")


            tar = tarfile.open(pathToCompressedHome)
            tar.extractall(websiteHome)
            tar.close()

            status = open(completPath + '/status', "w")
            status.write("Done")
            status.close()

            writeToFile.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "]" + "Completed Restore for domain: " + domain + "\n")


        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startRestore]")

    @staticmethod
    def startRestore(backupDir,backupLogPath,dir):
        try:
            ext = ".tar.gz"

            for backup in os.listdir(backupDir):

                writeToFile = open(backupLogPath, "a")

                writeToFile.writelines("\n")
                writeToFile.writelines("\n")
                writeToFile.writelines("[" + time.strftime(
                    "%I-%M-%S-%a-%b-%Y") + "]" + " Starting restore for: "+backup+".\n")

                writeToFile.close()

                if backup.endswith(ext):
                    finalData = json.dumps({'backupFile': backup,"dir":dir})
                    r = requests.post("http://localhost:5003/backup/submitRestore", data=finalData)
                    data = json.loads(r.text)

                    logging.CyberCPLogFileWriter.writeToFile(r.text)

                    if data['restoreStatus'] == 1:

                        while (1):
                            finalData = json.dumps({'backupFile': backup, "dir": dir})
                            r = requests.post("http://localhost:5003/backup/restoreStatus", data=finalData)
                            data = json.loads(r.text)

                            logging.CyberCPLogFileWriter.writeToFile(r.text)

                            if data['status'] == "Done":
                                writeToFile = open(backupLogPath, "a")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " Restore Completed.\n")
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " #########################################\n")
                                writeToFile.close()
                                break
                            elif data['status'] == "Website already exists":
                                writeToFile = open(backupLogPath, "a")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " Website associated with this backup already exists.\n")
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " #########################################\n")
                                writeToFile.close()
                                logging.CyberCPLogFileWriter.writeToFile(
                                    "Website associated with this backup already exists")
                                break
                            elif data['status'] == 0:
                                time.sleep(2)

                                writeToFile = open(backupLogPath, "a")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " Waiting for restore to complete.\n")
                                writeToFile.close()

                                pass
                            elif data['status'] == "Not able to create Account and databases, aborting.":
                                writeToFile = open(backupLogPath, "a")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " Not able to create Account and databases, aborting.\n")
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " #########################################\n")
                                writeToFile.close()
                                logging.CyberCPLogFileWriter.writeToFile(
                                    "Not able to create Account and databases, aborting.")
                                break
                            else:
                                time.sleep(3)

                                writeToFile = open(backupLogPath, "a")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("\n")
                                writeToFile.writelines("[" + time.strftime(
                                    "%I-%M-%S-%a-%b-%Y") + "]" + " Waiting for restore to complete.\n")
                                writeToFile.close()

                                pass
                    else:
                        logging.CyberCPLogFileWriter.writeToFile("Could not start restore process for: "+backup)

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
            r = requests.post("http://localhost:5003/backup/submitBackupCreation", data=finalData)
            data = json.loads(r.text)
            backupPath = data['tempStorage']


            while (1):
                r = requests.post("http://localhost:5003/backup/backupStatus", data= finalData)
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

            command = 'rsync -avz -e "ssh  -i /root/.ssh/cyberpanel" ' + completedPathToSend + ' root@' + IPAddress + ':/home/backup/transfer-'+folderNumber
            subprocess.call(shlex.split(command), stdout=writeToFile)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

    @staticmethod
    def backupProcess(ipAddress, dir, backupLogPath,folderNumber):
        try:
            ## dir is without forward slash


            for virtualHost in os.listdir("/home"):

                try:

                    if virtualHost == "vmail" or virtualHost == "backup":
                        pass

                    writeToFile = open(backupLogPath, "a")
                    writeToFile.writelines("[" + time.strftime(
                        "%I-%M-%S-%a-%b-%Y") + "]" + " Currently generating local backups for: " + virtualHost + "\n")
                    writeToFile.close()


                    finalData = json.dumps({'websiteToBeBacked': virtualHost})
                    r = requests.post("http://localhost:5003/backup/submitBackupCreation", data=finalData)

                    data = json.loads(r.text)

                    fileName = data['tempStorage']+".tar.gz"

                    completePathToBackupFile = fileName


                    while (1):
                        r = requests.post("http://localhost:5003/backup/backupStatus", data= finalData)
                        time.sleep(2)
                        data = json.loads(r.text)

                        writeToFile = open(backupLogPath, "a")

                        writeToFile.writelines("[" + time.strftime(
                            "%I-%M-%S-%a-%b-%Y") + "]" + " Waiting for backup to complete.. " + "\n")

                        writeToFile.close()


                        if data['status'] == 0:

                            writeToFile = open(backupLogPath, "a")

                            writeToFile.writelines("[" + time.strftime(
                                "%I-%M-%S-%a-%b-%Y") + "]" + " Local Backup Completed for: " +virtualHost + "\n")


                            ## move the generated backup file to specified destination

                            if os.path.exists(completePathToBackupFile):
                                move(completePathToBackupFile,dir)

                            completedPathToSend = dir +"/" + completePathToBackupFile.split("/")[-1]

                            writeToFile.writelines("[" + time.strftime(
                                "%I-%M-%S-%a-%b-%Y") + "]" + " Sending " + completedPathToSend +" to "+ipAddress +".\n")


                            remoteBackup.sendBackup(completedPathToSend,ipAddress,str(folderNumber),writeToFile)

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
            rmtree(dir)




        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [backupProcess]")

    @staticmethod
    def remoteTransfer(ipAddress, dir):
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

            writeToFile.close()

            ## fix yes/no

            backupUtil.backupUtilities.verifyHostKey(ipAddress)


            if backupUtil.backupUtilities.checkIfHostIsUp(ipAddress) == 1:
                if backupUtil.backupUtilities.checkConnection(ipAddress) != 1:
                    writeToFile.writelines("[" + time.strftime(
                        "%I-%M-%S-%a-%b-%Y") + "]" + " Connection to:" + ipAddress + " Failed, please resetup this destination from CyberPanel, aborting." + "\n")
                    return [0, "Connection check failed"]
                else:
                    pass
            else:
                writeToFile.writelines("[" + time.strftime(
                    "%I-%M-%S-%a-%b-%Y") + "]" + " Host:" + ipAddress + " is down, aborting." + "\n")
                return [0, "Host is down"]


            p = Process(target=remoteBackup.backupProcess, args=(ipAddress, destination, backupLogPath,dir,))
            p.start()

            pid = open(destination + '/pid', "w")
            pid.write(str(p.pid))
            pid.close()

            return [1, None]

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [postRemoteTransfer]")
            return [0, msg]

