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



class backupUtilities:

    @staticmethod
    def startBackup(tempStoragePath,backupName,backupPath):
        try:

            meta = open(tempStoragePath+'/meta',"r").readlines()

            status = open(backupPath+'status',"w")
            status.write(backupName+"\n")
            status.write("Making archive of home directory\n")
            status.close()

            count = 0
            for items in meta:
                if count==0:
                    domainName = items.strip('\n')
                    make_archive(tempStoragePath+"/public_html", 'gztar', "/home/"+domainName+"/public_html")
                    count = count + 1
                else:
                    dbName = items.split('-')[0]
                    status = open(backupPath + 'status', "w")
                    status.write(backupName + "\n")
                    status.write("Backing up database: "+dbName)
                    status.close()
                    mysqlUtilities.mysqlUtilities.createDatabaseBackup(dbName,tempStoragePath)

            make_archive(backupPath+"/"+backupName, 'gztar', tempStoragePath)
            rmtree(tempStoragePath)

            status = open(backupPath + 'status', "w")
            status.write(backupName + "\n")
            status.write("completed\n")
            status.close()



        except BaseException,msg:
            try:
                os.remove(backupPath+"/"+backupName+".tar.gz")

            except:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

            try:
                rmtree(tempStoragePath)
            except:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startBackup]")

            status = open(backupPath + 'status', "w")
            status.write(backupName + "\n")
            status.write("Aborted, please check CyberPanel main log file.")
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
    def startRestore(backupName, backupNames):
        try:
            backupFileName = backupName.strip(".tar.gz")

            completPath = "/home/backup/" + backupFileName
            originalFile = "/home/backup/" + backupName

            pathToCompressedHome = completPath + "/public_html.tar.gz"

            if not os.path.exists(completPath):
                os.mkdir(completPath)

            ## writing pid of restore process

            pid = open(completPath + '/pid', "w")
            pid.write(str(os.getpid()))
            pid.close()

            status = open(completPath + '/status', "w")
            status.write("Extracting Main Archive")
            status.close()

            tar = tarfile.open(originalFile)
            tar.extractall(completPath)
            tar.close()

            status = open(completPath + '/status', "w")
            status.write("Creating Account and databases")
            status.close()

            ## creating website and its dabases

            try:
                finalData = json.dumps({'backupFile': backupName})
                r = requests.post("http://localhost:5003/websites/CreateWebsiteFromBackup", data=finalData)
                data = json.loads(r.text)

                if data['createWebSiteStatus'] == 1:
                    pass
                else:
                    status = open(completPath + '/status', "w")
                    status.write("Not able to create Account and databases, aborting.")
                    status.close()
                    logging.CyberCPLogFileWriter.writeToFile(r.text)
                    return 0
            except BaseException,msg:
                status = open(completPath + '/status', "w")
                status.write("[132] Not able to create Account and databases, aborting.")
                status.close()
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startRestore]")
                return 0




            f = open(completPath + '/status')
            data = f.read()
            status = data.split('\n', 1)[0]

            if (status == "Accounts and DBs Created"):
                pass
            elif (status == "Website already exists"):
                return 0

            ## reading meta file to create databases

            data = open(completPath + "/meta", 'r').readlines()
            domain = data[0].strip('\n')
            websiteHome = "/home/" + domain + "/public_html"

            check = 0

            status = open(completPath + '/status', "w")
            status.write("Restoring Databases")
            status.close()

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

            tar = tarfile.open(pathToCompressedHome)
            tar.extractall(websiteHome)
            tar.close()

            status = open(completPath + '/status', "w")
            status.write("Done")
            status.close()


        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startRestore]")

    @staticmethod
    def initiateRestore(backupName):
        try:
            p = Process(target=backupUtilities.startRestore, args=(backupName, backupName,))
            p.start()
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateRestore]")

    @staticmethod
    def sendKey(IPAddress,password):
        try:

            sendKeyProc = pexpect.spawn("scp /root/.ssh/cyberpanel.pub root@"+IPAddress+":/root/.ssh/authorized_keys")
            sendKeyProc.expect("password:")

            sendKeyProc.sendline(password)
            sendKeyProc.expect("100%")

            sendKeyProc.wait()

            return 1

        except pexpect.TIMEOUT,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [sendKey]")
            return 0
        except pexpect.EOF,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [sendKey]")
            return 0
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [sendKey]")
            return 0

    @staticmethod
    def setupSSHKeys(IPAddress, password):
        try:

            ## Checking for host verification

            backupUtilities.host_key_verification(IPAddress)

            if backupUtilities.checkIfHostIsUp(IPAddress) == 1:
                pass
            else:
                return "Host is Down."

            expectation = []

            expectation.append("continue connecting (yes/no)?")
            expectation.append("password:")

            setupSSHKeys = pexpect.spawn("ssh root@"+IPAddress+" mkdir /root/.ssh")

            index = setupSSHKeys.expect(expectation)

            if index == 0:
                setupSSHKeys.sendline("yes")
                setupSSHKeys.expect("password:")
                setupSSHKeys.sendline(password)

                expectation = []

                expectation.append("File exists")
                expectation.append(pexpect.EOF)
                expectation.append("please try again.")

                innerIndex = setupSSHKeys.expect(expectation)

                if innerIndex == 0:
                    print "Exists"
                    setupSSHKeys.wait()

                    ## setting up keys.

                    if backupUtilities.sendKey(IPAddress,password) == 0:
                        return "Can't setup connection, check CyberCP Main log file."
                    else:
                        return 1

                elif innerIndex == 1:

                    print "Created"
                    setupSSHKeys.wait()

                    ## setting up keys.

                    if backupUtilities.sendKey(IPAddress,password) == 0:
                        return "Can't setup connection, check CyberCP Main log file."
                    else:
                        return 1

                    print "keysInstalled"

                else:
                    return "Wrong Password"

            elif index == 1:
                setupSSHKeys.sendline(password)

                expectation = []

                expectation.append("File exists")
                expectation.append(pexpect.EOF)
                expectation.append("please try again.")

                innerIndex = setupSSHKeys.expect(expectation)

                if innerIndex == 0:
                    print "Exists"
                    setupSSHKeys.wait()

                    ## setting up keys.

                    if backupUtilities.sendKey(IPAddress,password) == 0:
                        return "Can't setup connection, check CyberCP Main log file."
                    else:
                        return 1

                elif innerIndex == 1:
                    print "Created"
                    setupSSHKeys.wait()

                    ## setting up keys.

                    ## setting up keys.

                    if backupUtilities.sendKey(IPAddress,password) == 0:
                        return "Can't setup connection, check CyberCP Main log file."
                    else:
                        return 1

                else:
                    return "Wrong Password"
        except pexpect.TIMEOUT, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [setupSSHKeys]")
            return 0
        except pexpect.EOF, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [setupSSHKeys]")
            return 0
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [setupSSHKeys]")
            return 0

    @staticmethod
    def checkIfHostIsUp(IPAddress):
        try:
            if subprocess.check_output(['ping', IPAddress, '-c 1']).find("0% packet loss") > -1:
                return 1
            else:
                return 0
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[checkIfPostIsUp]")

    @staticmethod
    def checkConnection(IPAddress):

        try:

            expectation = []
            expectation.append("password:")
            expectation.append("Last login")
            expectation.append(pexpect.EOF)

            checkConn = pexpect.spawn("ssh -i /root/.ssh/cyberpanel root@"+IPAddress, timeout=3)
            index = checkConn.expect(expectation)

            if index == 0:
                subprocess.call(['kill', str(checkConn.pid)])
                return 0
            elif index == 1:
                subprocess.call(['kill', str(checkConn.pid)])
                return 1
            else:
                subprocess.call(['kill', str(checkConn.pid)])
                return 0

        except pexpect.TIMEOUT, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [checkConnection]")
            return 0
        except pexpect.EOF, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [checkConnection]")
            return 0
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [checkConnection]")
            return 0

    @staticmethod
    def verifyHostKey(IPAddress):

        try:

            expectation = "continue connecting (yes/no)?"

            verifyHostKey = pexpect.spawn("ssh -i /root/.ssh/cyberpanel root@" + IPAddress, timeout=3)
            verifyHostKey.expect(expectation)
            verifyHostKey.sendline("yes")

        except pexpect.TIMEOUT, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [verifyHostKey]")
            return 0
        except pexpect.EOF, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [verifyHostKey]")
            return 0
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [verifyHostKey]")
            return 0



    @staticmethod
    def createBackupDir(IPAddress,IPAddressA):

        try:
            command = "ssh -i /root/.ssh/cyberpanel root@"+IPAddress+" mkdir /home/backup"

            shlex.split(command)

            subprocess.call(shlex.split(command))

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createBackupDir]")
            return 0

    @staticmethod
    def initiateBackupDirCreation(IPAddress):
        try:
            thread.start_new_thread(backupUtilities.createBackupDir, (IPAddress,IPAddress))
        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [initiateBackupDirCreation]")

    @staticmethod
    def host_key_verification(IPAddress):
        try:
            command = 'ssh-keygen -R '+IPAddress

            shlex.split(command)

            subprocess.call(shlex.split(command))

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [host_key_verification]")
            return 0


