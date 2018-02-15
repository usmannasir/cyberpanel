import thread
import pexpect
import CyberCPLogFileWriter as logging
import subprocess
import shlex
from shutil import make_archive,rmtree
import os
import mysqlUtilities
import tarfile
from multiprocessing import Process
import json
import requests
import signal
from installUtilities import installUtilities
import argparse
from shutil import move,copy
import sys
from xml.etree import ElementTree


class backupUtilities:

    completeKeyPath  = "/home/cyberpanel/.ssh"
    destinationsPath = "/home/cyberpanel/destinations"


    @staticmethod
    def startBackup(tempStoragePath,backupName,backupPath):
        try:

            ## writing the name of backup file

            ## /home/example.com/backup/backupFileName
            backupFileNamePath = os.path.join(backupPath,"backupFileName")
            status = open(backupFileNamePath, "w")
            status.write(backupName)
            status.close()



            status = open(os.path.join(backupPath,'status'),"w")
            status.write("Making archive of home directory\n")
            status.close()

            ## Parsing XML Meta file!

            ## /home/example.com/backup/backup-example-06-50-03-Thu-Feb-2018/meta.xml -- tempStoragePath
            backupMetaData = ElementTree.parse(os.path.join(tempStoragePath,'meta.xml'))


            ## Making archive of home directory

            domainName = backupMetaData.find('masterDomain').text
            ## /home/example.com/backup/backup-example-06-50-03-Thu-Feb-2018 -- tempStoragePath
            make_archive(os.path.join(tempStoragePath,"public_html"), 'gztar', os.path.join("/home",domainName,"public_html"))

            ## Backing up databases
            databases = backupMetaData.findall('Databases/database')

            for database in databases:
                dbName = database.find('dbName').text

                status = open(os.path.join(backupPath,'status'), "w")
                status.write("Backing up database: " + dbName)
                status.close()
                mysqlUtilities.mysqlUtilities.createDatabaseBackup(dbName, tempStoragePath)


            make_archive(os.path.join(backupPath,backupName), 'gztar', tempStoragePath)
            rmtree(tempStoragePath)

            status = open(os.path.join(backupPath,'status'), "w")
            status.write("completed\n")
            status.close()


        except BaseException,msg:
            try:
                os.remove(os.path.join(backupPath,backupName+".tar.gz"))

            except:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

            try:
                rmtree(tempStoragePath)
            except:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

            status = open(os.path.join(backupPath,'status'), "w")
            status.write(backupName + "\n")
            status.write("Aborted, please check CyberPanel main log file. [5009]")
            status.close()
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")


    @staticmethod
    def initiateBackup(tempStoragePath,backupName,backupPath):
        try:
            p = Process(target=backupUtilities.startBackup, args=(tempStoragePath,backupName,backupPath,))
            p.start()
            pid = open(backupPath + 'pid', "w")
            pid.write(str(p.pid))
            pid.close()
        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateBackup]")

    @staticmethod
    def startRestore(backupName, dir):
        try:

            if dir == "CyberPanelRestore":
                backupFileName = backupName.strip(".tar.gz")
                completPath = os.path.join("/home","backup",backupFileName) ## without extension
                originalFile = os.path.join("/home","backup",backupName) ## with extension
            else:
                backupFileName = backupName.strip(".tar.gz")
                completPath = "/home/backup/transfer-"+str(dir)+"/"+backupFileName ## without extension
                originalFile = "/home/backup/transfer-"+str(dir)+"/"+backupName ## with extension



            pathToCompressedHome = os.path.join(completPath,"public_html.tar.gz")

            if not os.path.exists(completPath):
                os.mkdir(completPath)

            ## writing pid of restore process

            pid = open(os.path.join(completPath,'pid'), "w")
            pid.write(str(os.getpid()))
            pid.close()

            status = open(os.path.join(completPath,'status'), "w")
            status.write("Extracting Main Archive")
            status.close()

            tar = tarfile.open(originalFile)
            tar.extractall(completPath)
            tar.close()

            status = open(os.path.join(completPath,'status'), "w")
            status.write("Creating Account and databases")
            status.close()

            ## creating website and its dabases

            try:
                finalData = json.dumps({'backupFile': backupName,"dir":dir})
                r = requests.post("http://localhost:5003/websites/CreateWebsiteFromBackup", data=finalData,verify=False)
                data = json.loads(r.text)

                if data['createWebSiteStatus'] == 1:
                    pass
                else:
                    status = open(os.path.join(completPath,'status'), "w")
                    status.write("Error Message: " + data['error_message'] +". Not able to create Account and databases, aborting. [5009]")
                    status.close()
                    logging.CyberCPLogFileWriter.writeToFile(r.text)
                    return 0
            except BaseException,msg:
                status = open(os.path.join(completPath,'status'), "w")
                status.write("Error Message: " + str(msg) +". Not able to create Account and databases, aborting. [5009]")
                status.close()
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startRestore]")
                return 0

            ########### creating sub/addon/parked domains

            status = open(os.path.join(completPath,'status'), "w")
            status.write("Creating Child Domains")
            status.close()

            ## reading meta file to create subdomains

            backupMetaData = ElementTree.parse(os.path.join(completPath,"meta.xml"))

            ## extracting master domain for later use
            masterDomain = backupMetaData.find('masterDomain').text
            externalApp = backupMetaData.find('externalApp').text
            websiteHome = os.path.join("/home",masterDomain,"public_html")

            childDomains = backupMetaData.findall('ChildDomains/domain')

            try:
                for childDomain in childDomains:

                    domain = childDomain.find('domain').text
                    phpSelection = childDomain.find('phpSelection').text
                    path = childDomain.find('path').text

                    finalData = json.dumps(
                        {'masterDomain': masterDomain, 'domainName': domain, 'phpSelection': phpSelection,
                         'path': path,
                         'ssl': 0, 'restore': 1})
                    r = requests.post("http://localhost:5003/websites/submitDomainCreation", data=finalData,
                                      verify=False)

                    data = json.loads(r.text)

                    if data['createWebSiteStatus'] == 1:
                        rmtree(websiteHome)
                        continue
                    else:
                        status = open(os.path.join(completPath,'status'), "w")
                        status.write("Error Message: " + data[
                            'error_message'] + ". Not able to create child domains, aborting. [5009]")
                        status.close()
                        logging.CyberCPLogFileWriter.writeToFile(r.text)
                        return 0

            except BaseException, msg:
                status = open(os.path.join(completPath,'status'), "w")
                status.write("Error Message: " + str(msg) +". Not able to create child domains, aborting. [5009]")
                status.close()
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startRestore]")
                return 0

            ## restoring databases

            status = open(os.path.join(completPath,'status'), "w")
            status.write("Restoring Databases")
            status.close()

            databases = backupMetaData.findall('Databases/database')

            for database in databases:
                dbName = database.find('dbName').text
                password = database.find('password').text
                mysqlUtilities.mysqlUtilities.restoreDatabaseBackup(dbName, completPath, password)


            status = open(os.path.join(completPath, 'status'), "w")
            status.write("Extracting web home data")
            status.close()

            tar = tarfile.open(pathToCompressedHome)
            tar.extractall(websiteHome)
            tar.close()

            status = open(os.path.join(completPath,'status'), "w")
            status.write("Done")
            status.close()
            installUtilities.reStartLiteSpeed()

            command = "chown -R " + externalApp + ":" + externalApp + " " + websiteHome

            cmd = shlex.split(command)

            subprocess.call(cmd)

        except BaseException, msg:
            status = open(os.path.join(completPath,'status'), "w")
            status.write(str(msg) + " [5009]")
            status.close()
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startRestore]")

    @staticmethod
    def initiateRestore(backupName,dir):
        try:
            p = Process(target=backupUtilities.startRestore, args=(backupName, dir,))
            p.start()
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateRestore]")

    @staticmethod
    def sendKey(IPAddress, password,port):
        try:

            command = "sudo scp -o StrictHostKeyChecking=no -P "+ port +" /root/.ssh/cyberpanel.pub root@" + IPAddress + ":/root/.ssh/authorized_keys"

            sendKeyProc = pexpect.spawn(command,timeout=3)
            sendKeyProc.expect("password:")

            sendKeyProc.sendline(password)
            sendKeyProc.expect("100%")

            sendKeyProc.wait()

            return [1, "None"]

        except pexpect.TIMEOUT, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [sendKey]")
            return [0, "TIMEOUT [sendKey]"]
        except pexpect.EOF, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [sendKey]")
            return [0,  "EOF [sendKey]"]
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [sendKey]")
            return [0, str(msg) + " [sendKey]"]

    @staticmethod
    def setupSSHKeys(IPAddress, password,port):
        try:
            ## Checking for host verification

            backupUtilities.host_key_verification(IPAddress)

            if backupUtilities.checkIfHostIsUp(IPAddress) == 1:
                pass
            else:
                return [0,"Host is Down."]

            expectation = "password:"


            command = "ssh -o StrictHostKeyChecking=no -p "+ port +" root@"+IPAddress+" mkdir /root/.ssh"

            setupKeys = pexpect.spawn(command,timeout=3)

            setupKeys.expect(expectation)

            ## on first login attempt send password

            setupKeys.sendline(password)

            ## if it again give you password, than provided password is wrong

            expectation = []
            expectation.append("please try again.")
            expectation.append(pexpect.EOF)

            index = setupKeys.expect(expectation)

            if index == 0:
                return [0,"Wrong Password"]
            elif index == 1:
                setupKeys.wait()

                sendKey = backupUtilities.sendKey(IPAddress,password,port)

                if sendKey[0] == 1:
                    return [1, "None"]
                else:
                    return [0,sendKey[1]]


        except pexpect.TIMEOUT, msg:
            logging.CyberCPLogFileWriter.writeToFile(setupKeys.before + " " + str(msg) + " [setupSSHKeys]")
            return [0, str(msg) + " [TIMEOUT setupSSHKeys]"]
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [setupSSHKeys]")
            return [0, str(msg) + " [setupSSHKeys]"]

    @staticmethod
    def checkIfHostIsUp(IPAddress):
        try:
            if subprocess.check_output(['ping', IPAddress, '-c 1']).find("0% packet loss") > -1:
                return 1
            else:
                return 0
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[checkIfHostIsUp]")

    @staticmethod
    def checkConnection(IPAddress):
        try:

            try:
                destinations = backupUtilities.destinationsPath
                data = open(destinations, 'r').readlines()
                port = data[1].strip("\n")
            except:
                port = "22"

            expectation = []
            expectation.append("password:")
            expectation.append("Last login")
            expectation.append(pexpect.EOF)

            checkConn = pexpect.spawn("sudo ssh -i /root/.ssh/cyberpanel -o StrictHostKeyChecking=no -p "+ port+" root@"+IPAddress, timeout=3)
            index = checkConn.expect(expectation)

            if index == 0:
                subprocess.call(['kill', str(checkConn.pid)])
                logging.CyberCPLogFileWriter.writeToFile("Remote Server is not able to authenticate for transfer to initiate, IP Address:" + IPAddress)
                return [0,"Remote Server is not able to authenticate for transfer to initiate."]
            elif index == 1:
                subprocess.call(['kill', str(checkConn.pid)])
                return [1, "None"]
            else:
                subprocess.call(['kill', str(checkConn.pid)])
                logging.CyberCPLogFileWriter.writeToFile(
                    "Remote Server is not able to authenticate for transfer to initiate, IP Address:" + IPAddress)
                return [0, "Remote Server is not able to authenticate for transfer to initiate, IP Address:" + IPAddress]

        except pexpect.TIMEOUT, msg:
            logging.CyberCPLogFileWriter.writeToFile("Timeout "+IPAddress+ " [checkConnection]")
            return [0, "371 Timeout while making connection to this server [checkConnection]"]
        except pexpect.EOF, msg:
            logging.CyberCPLogFileWriter.writeToFile("EOF "+IPAddress+ "[checkConnection]")
            return [0, "374 Remote Server is not able to authenticate for transfer to initiate. [checkConnection]"]
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg)+" " +IPAddress+ " [checkConnection]")
            return [0, "377 Remote Server is not able to authenticate for transfer to initiate. [checkConnection]"]

    @staticmethod
    def verifyHostKey(IPAddress):
        try:
            backupUtilities.host_key_verification(IPAddress)

            password = "hello" ## dumb password, not used anywhere.

            expectation = []

            expectation.append("continue connecting (yes/no)?")
            expectation.append("password:")

            setupSSHKeys = pexpect.spawn("ssh cyberpanel@" + IPAddress, timeout=3)

            index = setupSSHKeys.expect(expectation)

            if index == 0:
                setupSSHKeys.sendline("yes")

                setupSSHKeys.expect("password:")
                setupSSHKeys.sendline(password)

                expectation = []

                expectation.append("password:")
                expectation.append(pexpect.EOF)


                innerIndex = setupSSHKeys.expect(expectation)

                if innerIndex == 0:
                    setupSSHKeys.kill(signal.SIGTERM)
                    return [1, "None"]
                elif innerIndex == 1:
                    setupSSHKeys.kill(signal.SIGTERM)
                    return [1, "None"]

            elif index == 1:

                setupSSHKeys.expect("password:")
                setupSSHKeys.sendline(password)

                expectation = []

                expectation.append("password:")
                expectation.append(pexpect.EOF)

                innerIndex = setupSSHKeys.expect(expectation)

                if innerIndex == 0:
                    setupSSHKeys.kill(signal.SIGTERM)
                    return [1, "None"]
                elif innerIndex == 1:
                    setupSSHKeys.kill(signal.SIGTERM)
                    return [1, "None"]


        except pexpect.TIMEOUT, msg:
            logging.CyberCPLogFileWriter.writeToFile("Timeout [verifyHostKey]")
            return [0,"Timeout [verifyHostKey]"]
        except pexpect.EOF, msg:
            logging.CyberCPLogFileWriter.writeToFile("EOF [verifyHostKey]")
            return [0,"EOF [verifyHostKey]"]
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [verifyHostKey]")
            return [0,str(msg)+" [verifyHostKey]"]


    @staticmethod
    def createBackupDir(IPAddress,port):

        try:
            command = "ssh -o StrictHostKeyChecking=no -p "+ port +" -i /home/cyberpanel/.ssh/cyberpanel cyberpanel@"+IPAddress+" mkdir /home/backup"

            shlex.split(command)

            subprocess.call(shlex.split(command))

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createBackupDir]")
            return 0

    @staticmethod
    def initiateBackupDirCreation(IPAddress,port):
        try:
            thread.start_new_thread(backupUtilities.createBackupDir, (IPAddress,port))
        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateBackupDirCreation]")

    @staticmethod
    def host_key_verification(IPAddress):
        try:
            command = 'sudo ssh-keygen -R '+IPAddress

            shlex.split(command)

            subprocess.call(shlex.split(command))

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [host_key_verification]")
            return 0


def submitBackupCreation(tempStoragePath,backupName,backupPath,metaPath):
    try:

        if not os.path.exists(backupPath):
            os.mkdir(backupPath)

        if not os.path.exists(tempStoragePath):
            os.mkdir(tempStoragePath)


        move(metaPath,tempStoragePath+"/meta.xml")

        p = Process(target=backupUtilities.startBackup, args=(tempStoragePath, backupName, backupPath,))
        p.start()
        pid = open(backupPath + 'pid', "w")
        pid.write(str(p.pid))
        pid.close()

        print "1,None"

    except BaseException,msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [submitBackupCreation]")
        print "0,"+str(msg)

def cancelBackupCreation(backupCancellationDomain,fileName):
    try:

        path = "/home/" + backupCancellationDomain + "/backup/pid"

        pid = open(path, "r").readlines()[0]

        try:
            os.kill(int(pid), signal.SIGKILL)
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [cancelBackupCreation]")

        backupPath = "/home/" + backupCancellationDomain + "/backup/"

        tempStoragePath = backupPath + fileName

        try:
            os.remove(tempStoragePath + ".tar.gz")
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [cancelBackupCreation]")

        try:
            rmtree(tempStoragePath)
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [cancelBackupCreation]")

        status = open(backupPath + 'status', "w")
        status.write("Aborted manually. [5009]")
        status.close()
    except BaseException,msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [cancelBackupCreation]")
        print "0,"+str(msg)

def submitRestore(backupFile,dir):
    try:

        p = Process(target=backupUtilities.startRestore, args=(backupFile, dir,))
        p.start()

        print "1,None"

    except BaseException,msg:
        logging.CyberCPLogFileWriter.writeToFile(
            str(msg) + "  [cancelBackupCreation]")
        print "0,"+str(msg)

def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--tempStoragePath', help='')
    parser.add_argument('--backupName', help='!')
    parser.add_argument('--backupPath', help='')
    parser.add_argument('--metaPath', help='')

    ## backup cancellation arguments

    parser.add_argument('--backupCancellationDomain', help='')
    parser.add_argument('--fileName', help='')

    ## backup restore arguments

    parser.add_argument('--backupFile', help='')
    parser.add_argument('--dir', help='')




    args = parser.parse_args()

    if args.function == "submitBackupCreation":
        submitBackupCreation(args.tempStoragePath,args.backupName,args.backupPath,args.metaPath)
    elif args.function == "cancelBackupCreation":
        cancelBackupCreation(args.backupCancellationDomain,args.fileName)
    elif args.function == "submitRestore":
        submitRestore(args.backupFile,args.dir)

if __name__ == "__main__":
    main()


