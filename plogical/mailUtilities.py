import json
import os,sys

from django.http import HttpResponse

sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass
import os.path
import shutil
from plogical import CyberCPLogFileWriter as logging
import subprocess
import argparse
import shlex
from plogical.processUtilities import ProcessUtilities
import os
import bcrypt
import getpass
import smtplib
import threading as multi

try:
    from mailServer.models import Domains, EUsers
    from emailPremium.models import DomainLimits, EmailLimits
    from websiteFunctions.models import Websites, ChildDomains
except:
    pass

class mailUtilities:

    installLogPath = "/home/cyberpanel/openDKIMInstallLog"
    spamassassinInstallLogPath = "/home/cyberpanel/spamassassinInstallLogPath"
    cyberPanelHome = "/home/cyberpanel"
    mailScannerInstallLogPath = "/home/cyberpanel/mailScannerInstallLogPath"

    @staticmethod
    def SendEmail(sender, receivers, message):
        try:
            smtpObj = smtplib.SMTP('localhost')
            smtpObj.sendmail(sender, receivers, message)
            print("Successfully sent email")
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
    @staticmethod
    def AfterEffects(domain):
        path = "/usr/local/CyberCP/install/rainloop/cyberpanel.net.ini"

        if not os.path.exists("/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/domains/"):
            os.makedirs("/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/domains/")

        finalPath = "/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/domains/" + domain + ".ini"

        if not os.path.exists(finalPath):
            shutil.copy(path, finalPath)

        command = 'chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/rainloop/data/'
        ProcessUtilities.normalExecutioner(command)

    @staticmethod
    def createEmailAccount(domain, userName, password, restore = None):
        try:

            ## Check if already exists

            finalEmailUsername = userName + "@" + domain

            if EUsers.objects.filter(email=finalEmailUsername).exists():
                raise BaseException("This account already exists!")

            ## Check for email limits.

            ChildCheck = 0
            try:
                website = Websites.objects.get(domain=domain)
            except:
                website = ChildDomains.objects.get(domain=domain)
                ChildCheck = 1

            try:

                if not Domains.objects.filter(domain=domain).exists():
                    if ChildCheck == 0:
                        newEmailDomain = Domains(domainOwner=website, domain=domain)
                    else:
                        newEmailDomain = Domains(childOwner=website, domain=domain)

                    newEmailDomain.save()

                if not DomainLimits.objects.filter(domain=newEmailDomain).exists():
                    domainLimits = DomainLimits(domain=newEmailDomain)
                    domainLimits.save()

                if ChildCheck == 0:
                    if website.package.emailAccounts == 0 or (
                                newEmailDomain.eusers_set.all().count() < website.package.emailAccounts):
                        pass
                    else:
                        raise BaseException("Exceeded maximum amount of email accounts allowed for the package.")
                else:
                    if website.master.package.emailAccounts == 0 or (
                                newEmailDomain.eusers_set.all().count() < website.master.package.emailAccounts):
                        pass
                    else:
                        raise BaseException("Exceeded maximum amount of email accounts allowed for the package.")

            except:

                emailDomain = Domains.objects.get(domain=domain)
                if ChildCheck == 0:
                    if website.package.emailAccounts == 0 or (
                                emailDomain.eusers_set.all().count() < website.package.emailAccounts):
                        pass
                    else:
                        raise BaseException("Exceeded maximum amount of email accounts allowed for the package.")
                else:
                    if website.master.package.emailAccounts == 0 or (
                                emailDomain.eusers_set.all().count() < website.master.package.emailAccounts):
                        pass
                    else:
                        raise BaseException("Exceeded maximum amount of email accounts allowed for the package.")


            ## After effects

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/mailUtilities.py"
            execPath = execPath + " AfterEffects --domain " + domain

            if getpass.getuser() == 'root':
                ## This is the case when cPanel Importer is running and token is not present in enviroment.
                ProcessUtilities.normalExecutioner(execPath)
            else:
                ProcessUtilities.executioner(execPath, 'lscpd')

            ## After effects ends

            emailDomain = Domains.objects.get(domain=domain)

            #emailAcct = EUsers(emailOwner=emailDomain, email=finalEmailUsername, password=hash.hexdigest())

            CentOSPath = '/etc/redhat-release'

            if os.path.exists(CentOSPath):
                if restore == None:
                    password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    password = '{CRYPT}%s' % (password.decode())
                emailAcct = EUsers(emailOwner=emailDomain, email=finalEmailUsername, password=password)
                emailAcct.mail = 'maildir:/home/vmail/%s/%s/Maildir' % (domain, userName)
                emailAcct.save()
            else:
                if restore == None:
                    password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    password = '{CRYPT}%s' % (password.decode())
                emailAcct = EUsers(emailOwner=emailDomain, email=finalEmailUsername, password=password)
                emailAcct.mail = 'maildir:/home/vmail/%s/%s/Maildir' % (domain, userName)
                emailAcct.save()

            emailLimits = EmailLimits(email=emailAcct)
            emailLimits.save()

            print("1,None")
            return 1,"None"

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [createEmailAccount]")
            print("0," + str(msg))
            return 0, str(msg)

    @staticmethod
    def deleteEmailAccount(email):
        try:

            email = EUsers(email=email)
            email.delete()

            return 1, 'None'

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [deleteEmailAccount]")
            return 0, str(msg)

    @staticmethod
    def getEmailAccounts(virtualHostName):
        try:
            emailDomain = Domains.objects.get(domain=virtualHostName)
            return emailDomain.eusers_set.all()
        except:
            return 0

    @staticmethod
    def changeEmailPassword(email, newPassword, encrypt = None):
        try:
            if encrypt == None:
                CentOSPath = '/etc/redhat-release'
                changePass = EUsers.objects.get(email=email)
                if os.path.exists(CentOSPath):
                    password = bcrypt.hashpw(newPassword.encode('utf-8'), bcrypt.gensalt())
                    password = '{CRYPT}%s' % (password.decode())
                    changePass.password = password
                else:
                    changePass.password = newPassword
                changePass.save()
            else:
                changePass = EUsers.objects.get(email=email)
                changePass.password = newPassword
                changePass.save()
            return 0,'None'
        except BaseException as msg:
            return 0, str(msg)

    @staticmethod
    def setupDKIM(virtualHostName):
        try:
            ## Generate DKIM Keys

            command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.6/site-packages/tldextract/.suffix_cache'
            ProcessUtilities.executioner(command)

            command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.8/site-packages/tldextract/.suffix_cache'
            ProcessUtilities.executioner(command)

            import tldextract

            actualDomain = virtualHostName
            extractDomain = tldextract.extract(virtualHostName)
            virtualHostName = extractDomain.domain + '.' + extractDomain.suffix

            if not os.path.exists("/etc/opendkim/keys/" + virtualHostName + "/default.txt"):

                path = '/etc/opendkim/keys/%s' % (virtualHostName)
                command = 'mkdir %s' % (path)
                ProcessUtilities.normalExecutioner(command)

                ## Generate keys

                if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                    command = "/usr/sbin/opendkim-genkey -D /etc/opendkim/keys/%s -d %s -s default" % (virtualHostName, virtualHostName)
                else:
                    command = "opendkim-genkey -D /etc/opendkim/keys/%s -d %s -s default" % (
                    virtualHostName, virtualHostName)

                ProcessUtilities.normalExecutioner(command)


                ## Fix permissions

                command = "chown -R root:opendkim /etc/opendkim/keys/" + virtualHostName
                ProcessUtilities.normalExecutioner(command)

                command = "chmod 640 /etc/opendkim/keys/" + virtualHostName + "/default.private"
                ProcessUtilities.normalExecutioner(command)

                command = "chmod 644 /etc/opendkim/keys/" + virtualHostName + "/default.txt"
                ProcessUtilities.normalExecutioner(command)

            ## Edit key file

            keyTable = "/etc/opendkim/KeyTable"
            configToWrite = "default._domainkey." + actualDomain + " " + actualDomain + ":default:/etc/opendkim/keys/" + virtualHostName + "/default.private\n"

            writeToFile = open(keyTable, 'a')
            writeToFile.write(configToWrite)
            writeToFile.close()

            ## Edit signing table

            signingTable = "/etc/opendkim/SigningTable"
            configToWrite = "*@" + actualDomain + " default._domainkey." + actualDomain + "\n"

            writeToFile = open(signingTable, 'a')
            writeToFile.write(configToWrite)
            writeToFile.close()

            ## Trusted hosts

            trustedHosts = "/etc/opendkim/TrustedHosts"
            configToWrite = actualDomain + "\n"

            writeToFile = open(trustedHosts, 'a')
            writeToFile.write(configToWrite)
            writeToFile.close()

            ## Restart Postfix and OpenDKIM

            command = "systemctl restart opendkim"
            subprocess.call(shlex.split(command))

            command = "systemctl restart postfix"
            subprocess.call(shlex.split(command))

            return 1, "None"

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [setupDKIM:275]")
            return 0, str(msg)

    @staticmethod
    def checkIfDKIMInstalled():
        try:

            path = "/etc/opendkim.conf"

            command = "sudo cat " + path
            return ProcessUtilities.executioner(command)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [checkIfDKIMInstalled]")
            return 0

    @staticmethod
    def generateKeys(domain):
        try:
            result = mailUtilities.setupDKIM(domain)
            if result[0] == 0:
                raise BaseException(result[1])
            else:
                print("1,None")

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [generateKeys]")
            print("0," + str(msg))

    @staticmethod
    def configureOpenDKIM():
            try:

                ## Configure OpenDKIM specific settings

                openDKIMConfigurePath = "/etc/opendkim.conf"

                configData = """
Mode	sv
Canonicalization	relaxed/simple
KeyTable	refile:/etc/opendkim/KeyTable
SigningTable	refile:/etc/opendkim/SigningTable
ExternalIgnoreList	refile:/etc/opendkim/TrustedHosts
InternalHosts	refile:/etc/opendkim/TrustedHosts
"""

                writeToFile = open(openDKIMConfigurePath, 'a')
                writeToFile.write(configData)
                writeToFile.close()

                ## Configure postfix specific settings

                postfixFilePath = "/etc/postfix/main.cf"

                configData = """
smtpd_milters = inet:127.0.0.1:8891
non_smtpd_milters = $smtpd_milters
milter_default_action = accept
"""

                writeToFile = open(postfixFilePath, 'a')
                writeToFile.write(configData)
                writeToFile.close()

                #### Restarting Postfix and OpenDKIM

                command = "systemctl start opendkim"
                subprocess.call(shlex.split(command))

                command = "systemctl enable opendkim"
                subprocess.call(shlex.split(command))

                ##

                command = "systemctl start postfix"
                subprocess.call(shlex.split(command))

                print("1,None")
                return



            except OSError as msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [configureOpenDKIM]")
                print("0," + str(msg))
                return
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [configureOpenDKIM]")
                print("0," + str(msg))
            return

    @staticmethod
    def checkHome():
        try:
            try:
                FNULL = open(os.devnull, 'w')

                if getpass.getuser() == 'root':
                    if not os.path.exists(mailUtilities.cyberPanelHome):
                        command = "mkdir " + mailUtilities.cyberPanelHome
                        subprocess.call(shlex.split(command), stdout=FNULL)

                    command = "sudo chown -R cyberpanel:cyberpanel " + mailUtilities.cyberPanelHome
                    subprocess.call(shlex.split(command), stdout=FNULL)
                else:
                    if not os.path.exists(mailUtilities.cyberPanelHome):
                        command = "mkdir " + mailUtilities.cyberPanelHome
                        ProcessUtilities.executioner(command)

                    command = "chown -R cyberpanel:cyberpanel " + mailUtilities.cyberPanelHome
                    ProcessUtilities.executioner(command)
            except:
                FNULL = open(os.devnull, 'w')
                command = "chown -R cyberpanel:cyberpanel " + mailUtilities.cyberPanelHome
                subprocess.call(shlex.split(command), stdout=FNULL)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [checkHome]")

    @staticmethod
    def installOpenDKIM(install, openDKIMINstall):
        try:

            mailUtilities.checkHome()

            command = 'sudo yum install opendkim -y'

            cmd = shlex.split(command)

            with open(mailUtilities.installLogPath, 'w') as f:
                res = subprocess.call(cmd, stdout=f)

            if res == 1:
                writeToFile = open(mailUtilities.installLogPath, 'a')
                writeToFile.writelines("Can not be installed.[404]\n")
                writeToFile.close()
                logging.CyberCPLogFileWriter.writeToFile("[Could not Install OpenDKIM.]")
                return 0
            else:
                writeToFile = open(mailUtilities.installLogPath, 'a')
                writeToFile.writelines("OpenDKIM Installed.[200]\n")
                writeToFile.close()

            return 1
        except BaseException as msg:
            writeToFile = open(mailUtilities.installLogPath, 'a')
            writeToFile.writelines("Can not be installed.[404]\n")
            writeToFile.close()
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installOpenDKIM]")

    @staticmethod
    def restartServices():
        try:
            command = 'systemctl restart postfix'
            subprocess.call(shlex.split(command))

            command = 'systemctl restart dovecot'
            subprocess.call(shlex.split(command))
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [restartServices]")

    @staticmethod
    def installSpamAssassin(install, SpamAssassin):
        try:

            if os.path.exists(mailUtilities.spamassassinInstallLogPath):
                os.remove(mailUtilities.spamassassinInstallLogPath)

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'sudo yum install spamassassin -y'
            else:
                command = 'sudo apt-get install spamassassin spamc -y'

            cmd = shlex.split(command)

            with open(mailUtilities.spamassassinInstallLogPath, 'w') as f:
                res = subprocess.call(cmd, stdout=f)

            if res == 1:
                writeToFile = open(mailUtilities.spamassassinInstallLogPath, 'a')
                writeToFile.writelines("Can not be installed.[404]\n")
                writeToFile.close()
                logging.CyberCPLogFileWriter.writeToFile("[Could not Install SpamAssassin.]")
                return 0
            else:
                writeToFile = open(mailUtilities.spamassassinInstallLogPath, 'a')
                writeToFile.writelines("SpamAssassin Installed.[200]\n")
                writeToFile.close()

            return 1
        except BaseException as msg:
            writeToFile = open(mailUtilities.spamassassinInstallLogPath, 'a')
            writeToFile.writelines("Can not be installed.[404]\n")
            writeToFile.close()
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installSpamAssassin]")

    @staticmethod
    def installMailScanner(install, SpamAssassin):
        try:

            if os.path.exists(mailUtilities.mailScannerInstallLogPath):
                os.remove(mailUtilities.mailScannerInstallLogPath)

            if mailUtilities.checkIfSpamAssassinInstalled():

                command = 'chmod +x /usr/local/CyberCP/CPScripts/mailscannerinstaller.sh'
                ProcessUtilities.executioner(command)


                command = '/usr/local/CyberCP/CPScripts/mailscannerinstaller.sh'

                cmd = shlex.split(command)

                with open(mailUtilities.mailScannerInstallLogPath, 'w') as f:
                    res = subprocess.call(cmd, stdout=f, shell=True)

                if res == 1:
                    writeToFile = open(mailUtilities.mailScannerInstallLogPath, 'a')
                    writeToFile.writelines("Can not be installed.[404]\n")
                    writeToFile.close()
                    logging.CyberCPLogFileWriter.writeToFile("[Could not Install MailScanner.]")
                    return 0
                else:
                    writeToFile = open(mailUtilities.mailScannerInstallLogPath, 'a')
                    writeToFile.writelines("MailScanner Installed.[200]\n")
                    writeToFile.close()

                return 1
            else:
                writeToFile = open(mailUtilities.mailScannerInstallLogPath, 'a')
                writeToFile.writelines("Please install SpamAssassin from CyberPanel before installing MailScanner.[404]\n")
                writeToFile.close()



        except BaseException as msg:
            writeToFile = open(mailUtilities.mailScannerInstallLogPath, 'a')
            writeToFile.writelines("Can not be installed.[404]\n")
            writeToFile.close()
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installSpamAssassin]")

    @staticmethod
    def checkIfSpamAssassinInstalled():
        try:

            path = "/etc/postfix/master.cf"

            command = "cat " + path
            output = ProcessUtilities.outputExecutioner(command)

            if output.find('content_filter=spamassassin') > -1:
                return 1
            else:
                return 0

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [checkIfSpamAssassinInstalled]")
            return 0

    @staticmethod
    def configureSpamAssassin():
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                confFile = "/etc/mail/spamassassin/local.cf"
                confData = open(confFile).readlines()

                conf = open(confFile, 'w')

                for items in confData:
                    if items.find('report_safe') > -1 or items.find('rewrite_header') > -1 or items.find('required_score') > -1 or items.find('required_hits') > -1:
                        conf.write(items.strip('#').strip(' '))
                    else:
                        conf.write(items)

                conf.close()


            command = "groupadd spamd"
            ProcessUtilities.normalExecutioner(command)

            command = "useradd -g spamd -s /bin/false -d /var/log/spamassassin spamd"
            ProcessUtilities.normalExecutioner(command)

            ##

            command = "chown spamd:spamd /var/log/spamassassin"
            ProcessUtilities.normalExecutioner(command)

            command = "systemctl enable spamassassin"
            ProcessUtilities.normalExecutioner(command)

            command = "systemctl start spamassassin"
            ProcessUtilities.normalExecutioner(command)

            ## Configuration to postfix

            postfixConf = '/etc/postfix/master.cf'
            data = open(postfixConf, 'r').readlines()

            writeToFile = open(postfixConf, 'w')
            checker = 1

            for items in data:
                if items.find('smtp') > - 1 and items.find('inet') > - 1 and items.find('smtpd') > - 1 and checker == 1:
                    writeToFile.writelines(items.strip('\n') + ' -o content_filter=spamassassin\n')
                    checker = 0
                else:
                    writeToFile.writelines(items)

            writeToFile.writelines('spamassassin unix - n n - - pipe flags=R user=spamd argv=/usr/bin/spamc -e /usr/sbin/sendmail -oi -f ${sender} ${recipient}')
            writeToFile.close()

            command = 'systemctl restart postfix'
            ProcessUtilities.normalExecutioner(command)


            print("1,None")
            return


        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [configureSpamAssassin]")
            print("0," + str(msg))
            return
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [configureSpamAssassin]")
            print("0," + str(msg))
        return

    @staticmethod
    def saveSpamAssassinConfigs(tempConfigPath):
        try:

            data = open(tempConfigPath).readlines()
            os.remove(tempConfigPath)

            confFile = "/etc/mail/spamassassin/local.cf"
            confData = open(confFile).readlines()

            conf = open(confFile, 'w')

            rsCheck = 0

            for items in confData:

                if items.find('report_safe ') > -1:
                    conf.writelines(data[0])
                    continue
                elif items.find('required_hits ') > -1:
                    conf.writelines(data[1])
                    continue
                elif items.find('rewrite_header ') > -1:
                    conf.writelines(data[2])
                    continue
                elif items.find('required_score ') > -1:
                    conf.writelines(data[3])
                    rsCheck = 1
                    continue

            if rsCheck == 0:
                conf.writelines(data[3])


            conf.close()

            command = 'systemctl restart spamassassin'
            subprocess.call(shlex.split(command))

            print("1,None")
            return

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [saveSpamAssassinConfigs]")
            print("0," + str(msg))

    @staticmethod
    def savePolicyServerStatus(install):
        try:

            postfixPath = '/etc/postfix/main.cf'

            if install == '1':
                if not os.path.exists('/etc/systemd/system/cpecs.service'):
                    shutil.copy("/usr/local/CyberCP/postfixSenderPolicy/cpecs.service", "/etc/systemd/system/cpecs.service")

                command = 'systemctl enable cpecs'
                subprocess.call(shlex.split(command))

                command = 'systemctl start cpecs'
                subprocess.call(shlex.split(command))

                writeToFile = open(postfixPath, 'a')
                writeToFile.writelines('smtpd_data_restrictions = check_policy_service unix:/var/log/policyServerSocket\n')
                writeToFile.writelines('smtpd_policy_service_default_action = DUNNO\n')
                writeToFile.close()

                command = 'systemctl restart postfix'
                subprocess.call(shlex.split(command))
            else:

                data = open(postfixPath, 'r').readlines()
                writeToFile = open(postfixPath, 'w')

                for items in data:
                    if items.find('check_policy_service unix:/var/log/policyServerSocket') > -1:
                        continue
                    elif items.find('smtpd_policy_service_default_action = DUNNO') > -1:
                        continue
                    else:
                        writeToFile.writelines(items)

                writeToFile.close()

                command = 'systemctl stop cpecs'
                subprocess.call(shlex.split(command))

                command = 'systemctl restart postfix'
                subprocess.call(shlex.split(command))

            print("1,None")
            return

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [savePolicyServerStatus]")
            print("0," + str(msg))

    @staticmethod
    def checkIfMailScannerInstalled():
        try:

            path = "/usr/local/CyberCP/public/mailwatch"

            if os .path.exists(path):
                return 1
            else:
                return 0

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [checkIfMailScannerInstalled]")
            return 0

    ####### Imported below functions from mailserver/mailservermanager, need to refactor later

class MailServerManagerUtils(multi.Thread):

    def __init__(self, request=None, function=None, extraArgs=None):
        multi.Thread.__init__(self)
        self.request = request
        self.function = function
        self.extraArgs = extraArgs
        self.MailSSL = 0

    def checkIfMailServerSSLIssued(self):

        postfixPath = '/etc/postfix/main.cf'

        postFixData = ProcessUtilities.outputExecutioner('cat %s' % (postfixPath))

        if postFixData.find('myhostname = server.example.com') > -1:
            self.MailSSL = 0
            return 0
        else:
            try:

                postFixLines = ProcessUtilities.outputExecutioner('cat %s' % (postfixPath)).splitlines()

                for items in postFixLines:
                    if items.find('myhostname') > -1 and items[0] != '#':
                        self.mailHostName = items.split('=')[1].strip(' ')
                        self.MailSSL = 1
            except BaseException as msg:
                self.MailSSL = 0
                logging.CyberCPLogFileWriter.writeToFile('%s. [checkIfMailServerSSLIssued:864]' % (str(msg)))

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]

            command = 'openssl s_client -connect %s:465' % (ipAddress)
            result = ProcessUtilities.outputExecutioner(command)

            if result.find('18 (self signed certificate)') > -1:
                return 0
            else:
                return 1

    def RunServerLevelEmailChecks(self):
        try:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      'Checking if MailServer SSL issued..,10')

            reportFile = self.extraArgs['reportFile']

            report = {}
            report['MailSSL'] = self.checkIfMailServerSSLIssued()

            writeToFile = open(reportFile, 'w')
            writeToFile.write(json.dumps(report))
            writeToFile.close()

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Completed [200].')

        except BaseException as msg:
            final_dic = {'installOpenDKIM': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def install_postfix_dovecot(self):
        try:
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'yum remove postfix -y'
                ProcessUtilities.executioner(command)
            elif ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                command = 'apt-get -y remove postfix'
                ProcessUtilities.executioner(command)

            ### On Ubuntu 18 find if old dovecot and remove

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                try:

                    command = 'apt-get purge dovecot* -y'
                    os.system(command)

                    command = 'apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 18A348AEED409DA1'
                    ProcessUtilities.executioner(command)

                    writeToFile = open('/etc/apt/sources.list.d/dovecot.list', 'a')
                    writeToFile.writelines('deb [arch=amd64] https://repo.dovecot.org/ce-2.3-latest/ubuntu/bionic bionic main\n')
                    writeToFile.close()

                    command = 'apt update'
                    ProcessUtilities.executioner(command)

                except:
                    pass

            ##

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Re-installing postfix..,10')

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:

                command = 'yum --nogpg install https://mirror.ghettoforge.org/distributions/gf/gf-release-latest.gf.el7.noarch.rpm -y'
                ProcessUtilities.executioner(command)

                command = 'yum install --enablerepo=gf-plus -y postfix3 postfix3-ldap postfix3-mysql postfix3-pcre'
            elif ProcessUtilities.decideDistro() == ProcessUtilities.cent8:

                command = 'dnf --nogpg install -y https://mirror.ghettoforge.org/distributions/gf/el/8/gf/x86_64/gf-release-8-11.gf.el8.noarch.rpm'
                ProcessUtilities.executioner(command)

                command = 'dnf install --enablerepo=gf-plus postfix3 postfix3-mysql -y'
                ProcessUtilities.executioner(command)
            else:


                import socket
                command = 'apt-get install -y debconf-utils'
                ProcessUtilities.executioner(command)
                file_name = 'pf.unattend.text'
                pf = open(file_name, 'w')
                pf.write('postfix postfix/mailname string ' + str(socket.getfqdn() + '\n'))
                pf.write('postfix postfix/main_mailer_type string "Internet Site"\n')
                pf.close()
                command = 'debconf-set-selections ' + file_name
                ProcessUtilities.executioner(command)

                command = 'apt-get -y install postfix postfix-mysql'
                # os.remove(file_name)

            ProcessUtilities.executioner(command)

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Re-installing Dovecot..,15')

            ##

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                command = 'yum --enablerepo=gf-plus -y install dovecot23 dovecot23-mysql'
                ProcessUtilities.executioner(command)
            elif ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'dnf install --enablerepo=gf-plus dovecot23 dovecot23-mysql -y'
                ProcessUtilities.executioner(command)
            else:
                command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install dovecot-mysql dovecot-imapd dovecot-pop3d'
                os.system(command)

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      'Postfix/dovecot reinstalled.,40')

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      '%s [install_postfix_dovecot][404]' % (str(msg)), 10)
            return 0

        return 1

    def setup_email_Passwords(self, mysqlPassword):
        try:

            mysql_virtual_domains = "/usr/local/CyberCP/install/email-configs-one/mysql-virtual_domains.cf"
            mysql_virtual_forwardings = "/usr/local/CyberCP/install/email-configs-one/mysql-virtual_forwardings.cf"
            mysql_virtual_mailboxes = "/usr/local/CyberCP/install/email-configs-one/mysql-virtual_mailboxes.cf"
            mysql_virtual_email2email = "/usr/local/CyberCP/install/email-configs-one/mysql-virtual_email2email.cf"
            dovecotmysql = "/usr/local/CyberCP/install/email-configs-one/dovecot-sql.conf.ext"

            ### update password:

            data = open(dovecotmysql, "r").readlines()

            writeDataToFile = open(dovecotmysql, "w")

            dataWritten = "connect = host=localhost dbname=cyberpanel user=cyberpanel password=" + mysqlPassword + " port=3306\n"

            for items in data:
                if items.find("connect") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            ### update password:

            data = open(mysql_virtual_domains, "r").readlines()

            writeDataToFile = open(mysql_virtual_domains, "w")

            dataWritten = "password = " + mysqlPassword + "\n"

            for items in data:
                if items.find("password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            ### update password:

            data = open(mysql_virtual_forwardings, "r").readlines()

            writeDataToFile = open(mysql_virtual_forwardings, "w")

            dataWritten = "password = " + mysqlPassword + "\n"

            for items in data:
                if items.find("password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            ### update password:

            data = open(mysql_virtual_mailboxes, "r").readlines()

            writeDataToFile = open(mysql_virtual_mailboxes, "w")

            dataWritten = "password = " + mysqlPassword + "\n"

            for items in data:
                if items.find("password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            ### update password:

            data = open(mysql_virtual_email2email, "r").readlines()

            writeDataToFile = open(mysql_virtual_email2email, "w")

            dataWritten = "password = " + mysqlPassword + "\n"

            for items in data:
                if items.find("password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            if self.remotemysql == 'ON':
                command = "sed -i 's|host=localhost|host=%s|g' %s" % (self.mysqlhost, dovecotmysql)
                ProcessUtilities.executioner(command)

                command = "sed -i 's|port=3306|port=%s|g' %s" % (self.mysqlport, dovecotmysql)
                ProcessUtilities.executioner(command)

                ##

                command = "sed -i 's|localhost|%s:%s|g' %s" % (self.mysqlhost, self.mysqlport, mysql_virtual_domains)
                ProcessUtilities.executioner(command)

                command = "sed -i 's|localhost|%s:%s|g' %s" % (
                    self.mysqlhost, self.mysqlport, mysql_virtual_forwardings)
                ProcessUtilities.executioner(command)

                command = "sed -i 's|localhost|%s:%s|g' %s" % (
                    self.mysqlhost, self.mysqlport, mysql_virtual_mailboxes)
                ProcessUtilities.executioner(command)

                command = "sed -i 's|localhost|%s:%s|g' %s" % (
                    self.mysqlhost, self.mysqlport, mysql_virtual_email2email)
                ProcessUtilities.executioner(command)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      '%s [setup_email_Passwords][404]' % (str(msg)), 10)
            return 0

        return 1

    def centos_lib_dir_to_ubuntu(self, filename, old, new):
        try:
            fd = open(filename, 'r')
            lines = fd.readlines()
            fd.close()
            fd = open(filename, 'w')
            centos_prefix = old
            ubuntu_prefix = new
            for line in lines:
                index = line.find(centos_prefix)
                if index != -1:
                    line = line[:index] + ubuntu_prefix + line[index + len(centos_prefix):]
                fd.write(line)
            fd.close()
        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      '%s [centos_lib_dir_to_ubuntu][404]' % (str(msg)), 10)

    def setup_postfix_dovecot_config(self):
        try:

            mysql_virtual_domains = "/etc/postfix/mysql-virtual_domains.cf"
            mysql_virtual_forwardings = "/etc/postfix/mysql-virtual_forwardings.cf"
            mysql_virtual_mailboxes = "/etc/postfix/mysql-virtual_mailboxes.cf"
            mysql_virtual_email2email = "/etc/postfix/mysql-virtual_email2email.cf"
            main = "/etc/postfix/main.cf"
            master = "/etc/postfix/master.cf"
            dovecot = "/etc/dovecot/dovecot.conf"
            dovecotmysql = "/etc/dovecot/dovecot-sql.conf.ext"

            if os.path.exists(mysql_virtual_domains):
                os.remove(mysql_virtual_domains)

            if os.path.exists(mysql_virtual_forwardings):
                os.remove(mysql_virtual_forwardings)

            if os.path.exists(mysql_virtual_mailboxes):
                os.remove(mysql_virtual_mailboxes)

            if os.path.exists(mysql_virtual_email2email):
                os.remove(mysql_virtual_email2email)

            if os.path.exists(main):
                os.remove(main)

            if os.path.exists(master):
                os.remove(master)

            if os.path.exists(dovecot):
                os.remove(dovecot)

            if os.path.exists(dovecotmysql):
                os.remove(dovecotmysql)

            ###############Getting SSL

            command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/postfix/key.pem -out /etc/postfix/cert.pem'
            ProcessUtilities.executioner(command)

            ##

            command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/dovecot/key.pem -out /etc/dovecot/cert.pem'
            ProcessUtilities.executioner(command)

            # Cleanup config files for ubuntu
            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                self.centos_lib_dir_to_ubuntu("/usr/local/CyberCP/install/email-configs-one/master.cf", "/usr/libexec/",
                                              "/usr/lib/")
                self.centos_lib_dir_to_ubuntu("/usr/local/CyberCP/install/email-configs-one/main.cf",
                                              "/usr/libexec/postfix",
                                              "/usr/lib/postfix/sbin")

            ########### Copy config files
            import shutil

            shutil.copy("/usr/local/CyberCP/install/email-configs-one/mysql-virtual_domains.cf",
                        "/etc/postfix/mysql-virtual_domains.cf")
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/mysql-virtual_forwardings.cf",
                        "/etc/postfix/mysql-virtual_forwardings.cf")
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/mysql-virtual_mailboxes.cf",
                        "/etc/postfix/mysql-virtual_mailboxes.cf")
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/mysql-virtual_email2email.cf",
                        "/etc/postfix/mysql-virtual_email2email.cf")
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/main.cf", main)
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/master.cf", master)
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/dovecot.conf", dovecot)
            shutil.copy("/usr/local/CyberCP/install/email-configs-one/dovecot-sql.conf.ext", dovecotmysql)

            ######################################## Permissions

            command = 'chmod o= /etc/postfix/mysql-virtual_domains.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chmod o= /etc/postfix/mysql-virtual_forwardings.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chmod o= /etc/postfix/mysql-virtual_mailboxes.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chmod o= /etc/postfix/mysql-virtual_email2email.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chmod o= ' + main
            ProcessUtilities.executioner(command)

            ##

            command = 'chmod o= ' + master
            ProcessUtilities.executioner(command)

            #######################################

            command = 'chgrp postfix /etc/postfix/mysql-virtual_domains.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chgrp postfix /etc/postfix/mysql-virtual_forwardings.cf'
            ProcessUtilities.executioner(command)
            ##

            command = 'chgrp postfix /etc/postfix/mysql-virtual_mailboxes.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chgrp postfix /etc/postfix/mysql-virtual_email2email.cf'
            ProcessUtilities.executioner(command)

            ##

            command = 'chgrp postfix ' + main
            ProcessUtilities.executioner(command)

            ##

            command = 'chgrp postfix ' + master
            ProcessUtilities.executioner(command)

            ######################################## users and groups

            command = 'groupadd -g 5000 vmail'
            ProcessUtilities.executioner(command)

            ##

            command = 'useradd -g vmail -u 5000 vmail -d /home/vmail -m'
            ProcessUtilities.executioner(command)

            ######################################## Further configurations

            # hostname = socket.gethostname()

            ################################### Restart postix

            command = 'systemctl enable postfix.service'
            ProcessUtilities.executioner(command)

            ##

            command = 'systemctl start postfix.service'
            ProcessUtilities.executioner(command)

            ######################################## Permissions

            command = 'chgrp dovecot /etc/dovecot/dovecot-sql.conf.ext'
            ProcessUtilities.executioner(command)

            ##

            command = 'chmod o= /etc/dovecot/dovecot-sql.conf.ext'
            ProcessUtilities.executioner(command)

            ################################### Restart dovecot

            command = 'systemctl enable dovecot.service'
            ProcessUtilities.executioner(command)

            ##

            command = 'systemctl start dovecot.service'
            ProcessUtilities.executioner(command)

            ##

            command = 'systemctl restart  postfix.service'
            ProcessUtilities.executioner(command)

            ## changing permissions for main.cf

            command = "chmod 755 " + main
            ProcessUtilities.executioner(command)

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                command = "mkdir -p /etc/pki/dovecot/private/"
                ProcessUtilities.executioner(command)

                command = "mkdir -p /etc/pki/dovecot/certs/"
                ProcessUtilities.executioner(command)

                command = "mkdir -p /etc/opendkim/keys/"
                ProcessUtilities.executioner(command)

                command = "sed -i 's/auth_mechanisms = plain/#auth_mechanisms = plain/g' /etc/dovecot/conf.d/10-auth.conf"
                ProcessUtilities.executioner(command)

                ## Ubuntu 18.10 ssl_dh for dovecot 2.3.2.1

                if ProcessUtilities.ubuntu:
                    dovecotConf = '/etc/dovecot/dovecot.conf'

                    data = open(dovecotConf, 'r').readlines()
                    writeToFile = open(dovecotConf, 'w')
                    for items in data:
                        if items.find('ssl_key = <key.pem') > -1:
                            writeToFile.writelines(items)
                            writeToFile.writelines('ssl_dh = </usr/share/dovecot/dh.pem\n')
                        else:
                            writeToFile.writelines(items)
                    writeToFile.close()

                command = "systemctl restart dovecot"
                ProcessUtilities.executioner(command)

            ## For ubuntu 20

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:

                command = "sed -i 's|daemon_directory = /usr/libexec/postfix|daemon_directory = /usr/lib/postfix/sbin|g' /etc/postfix/main.cf"
                ProcessUtilities.executioner(command)


        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      '%s [setup_postfix_dovecot_config][404]' % (
                                                          str(msg)), 10)
            return 0

        return 1

    def fixCyberPanelPermissions(self):

        ###### fix Core CyberPanel permissions
        command = "find /usr/local/CyberCP -type d -exec chmod 0755 {} \;"
        ProcessUtilities.executioner(command)

        command = "find /usr/local/CyberCP -type f -exec chmod 0644 {} \;"
        ProcessUtilities.executioner(command)

        command = "chmod -R 755 /usr/local/CyberCP/bin"
        ProcessUtilities.executioner(command)

        ## change owner

        command = "chown -R root:root /usr/local/CyberCP"
        ProcessUtilities.executioner(command)

        ########### Fix LSCPD

        command = "find /usr/local/lscp -type d -exec chmod 0755 {} \;"
        ProcessUtilities.executioner(command)

        command = "find /usr/local/lscp -type f -exec chmod 0644 {} \;"
        ProcessUtilities.executioner(command)

        command = "chmod -R 755 /usr/local/lscp/bin"
        ProcessUtilities.executioner(command)

        command = "chmod -R 755 /usr/local/lscp/fcgi-bin"
        ProcessUtilities.executioner(command)

        command = "chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin/tmp"
        ProcessUtilities.executioner(command)

        ## change owner

        command = "chown -R root:root /usr/local/lscp"
        ProcessUtilities.executioner(command)

        command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/rainloop/data"
        ProcessUtilities.executioner(command)

        command = "chmod 700 /usr/local/CyberCP/cli/cyberPanel.py"
        ProcessUtilities.executioner(command)

        command = "chmod 700 /usr/local/CyberCP/plogical/upgradeCritical.py"
        ProcessUtilities.executioner(command)

        command = "chmod 755 /usr/local/CyberCP/postfixSenderPolicy/client.py"
        ProcessUtilities.executioner(command)

        command = "chmod 640 /usr/local/CyberCP/CyberCP/settings.py"
        ProcessUtilities.executioner(command)

        command = "chown root:cyberpanel /usr/local/CyberCP/CyberCP/settings.py"
        ProcessUtilities.executioner(command)

        files = ['/etc/yum.repos.d/MariaDB.repo', '/etc/pdns/pdns.conf', '/etc/systemd/system/lscpd.service',
                 '/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
                 '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
                 '/etc/dovecot/dovecot.conf', '/usr/local/lsws/conf/httpd_config.xml',
                 '/usr/local/lsws/conf/modsec.conf', '/usr/local/lsws/conf/httpd.conf']

        for items in files:
            command = 'chmod 644 %s' % (items)
            ProcessUtilities.executioner(command)

        impFile = ['/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
                   '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
                   '/etc/dovecot/dovecot.conf', '/etc/pdns/pdns.conf', '/etc/pure-ftpd/db/mysql.conf',
                   '/etc/powerdns/pdns.conf']

        for items in impFile:
            command = 'chmod 600 %s' % (items)
            ProcessUtilities.executioner(command)

        command = 'chmod 640 /etc/postfix/*.cf'
        subprocess.call(command, shell=True)

        command = 'chmod 644 /etc/postfix/main.cf'
        subprocess.call(command, shell=True)

        command = 'chmod 640 /etc/dovecot/*.conf'
        subprocess.call(command, shell=True)

        command = 'chmod 644 /etc/dovecot/dovecot.conf'
        subprocess.call(command, shell=True)

        command = 'chmod 640 /etc/dovecot/dovecot-sql.conf.ext'
        subprocess.call(command, shell=True)

        command = 'chmod 644 /etc/postfix/dynamicmaps.cf'
        subprocess.call(command, shell=True)

        fileM = ['/usr/local/lsws/FileManager/', '/usr/local/CyberCP/install/FileManager',
                 '/usr/local/CyberCP/serverStatus/litespeed/FileManager', '/usr/local/lsws/Example/html/FileManager']

        for items in fileM:
            try:
                import shutil
                shutil.rmtree(items)
            except:
                pass

        command = 'chmod 755 /etc/pure-ftpd/'
        subprocess.call(command, shell=True)

        command = 'chmod +x /usr/local/CyberCP/plogical/renew.py'
        ProcessUtilities.executioner(command)

        command = 'chmod +x /usr/local/CyberCP/CLManager/CLPackages.py'
        ProcessUtilities.executioner(command)

        clScripts = ['/usr/local/CyberCP/CLScript/panel_info.py', '/usr/local/CyberCP/CLScript/CloudLinuxPackages.py',
                     '/usr/local/CyberCP/CLScript/CloudLinuxUsers.py',
                     '/usr/local/CyberCP/CLScript/CloudLinuxDomains.py'
            , '/usr/local/CyberCP/CLScript/CloudLinuxResellers.py', '/usr/local/CyberCP/CLScript/CloudLinuxAdmins.py',
                     '/usr/local/CyberCP/CLScript/CloudLinuxDB.py', '/usr/local/CyberCP/CLScript/UserInfo.py']

        for items in clScripts:
            command = 'chmod +x %s' % (items)
            ProcessUtilities.executioner(command)

        command = 'chmod 600 /usr/local/CyberCP/plogical/adminPass.py'
        ProcessUtilities.executioner(command)

        command = 'chmod 600 /etc/cagefs/exclude/cyberpanelexclude'
        ProcessUtilities.executioner(command)

        command = "find /usr/local/CyberCP/ -name '*.pyc' -delete"
        ProcessUtilities.executioner(command)

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.cent8:
            command = 'chown root:pdns /etc/pdns/pdns.conf'
            ProcessUtilities.executioner(command)

            command = 'chmod 640 /etc/pdns/pdns.conf'
            ProcessUtilities.executioner(command)

        command = 'chmod 640 /usr/local/lscp/cyberpanel/logs/access.log'
        ProcessUtilities.executioner(command)

        ###

    def ResetEmailConfigurations(self):
        try:
            ### Check if remote or local mysql

            passFile = "/etc/cyberpanel/mysqlPassword"

            try:
                jsonData = json.loads(ProcessUtilities.outputExecutioner('cat %s' % (passFile)))

                self.mysqluser = jsonData['mysqluser']
                self.mysqlpassword = jsonData['mysqlpassword']
                self.mysqlport = jsonData['mysqlport']
                self.mysqlhost = jsonData['mysqlhost']
                self.remotemysql = 'ON'

                if self.mysqlhost.find('rds.amazon') > -1:
                    self.RDS = 1

                ## Also set localhost to this server

                ipFile = "/etc/cyberpanel/machineIP"
                f = open(ipFile)
                ipData = f.read()
                ipAddressLocal = ipData.split('\n', 1)[0]

                self.LOCALHOST = ipAddressLocal
            except BaseException as msg:
                self.remotemysql = 'OFF'

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile('%s. [setupConnection:75]' % (str(msg)))

            ###

            self.checkIfMailServerSSLIssued()

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      'Removing and re-installing postfix/dovecot..,5')

            if self.install_postfix_dovecot() == 0:
                return 0

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Resetting configurations..,40')

            import sys
            sys.path.append('/usr/local/CyberCP')
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
            from CyberCP import settings

            if self.setup_email_Passwords(settings.DATABASES['default']['PASSWORD']) == 0:
                return 0

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Configurations reset..,70')

            if self.setup_postfix_dovecot_config() == 0:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                          'setup_postfix_dovecot_config failed. [404].')
                return 0

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      'Restoring OpenDKIM configurations..,70')

            if self.configureOpenDKIM() == 0:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                          'configureOpenDKIM failed. [404].')
                return 0

            if self.MailSSL:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                          'Setting up Mail Server SSL if any..,75')
                from plogical.virtualHostUtilities import virtualHostUtilities
                virtualHostUtilities.issueSSLForMailServer(self.mailHostName,
                                                           '/home/%s/public_html' % (self.mailHostName))

            from websiteFunctions.models import ChildDomains
            from plogical.virtualHostUtilities import virtualHostUtilities
            for websites in Websites.objects.all():
                try:
                    child = ChildDomains.objects.get(domain='mail.%s' % (websites.domain))
                    logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                              'Creating mail domain for %s..,80' % (websites.domain))
                    virtualHostUtilities.setupAutoDiscover(1, '/dev/null', websites.domain, websites.admin)
                except:
                    pass

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Fixing permissions..,90')

            self.fixCyberPanelPermissions()

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Completed [200].')

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      'Failed. Error %s [404].' % str(msg))

    def configureOpenDKIM(self):
        try:

            ## Configure OpenDKIM specific settings

            openDKIMConfigurePath = "/etc/opendkim.conf"

            configData = """
Mode	sv
Canonicalization	relaxed/simple
KeyTable	refile:/etc/opendkim/KeyTable
SigningTable	refile:/etc/opendkim/SigningTable
ExternalIgnoreList	refile:/etc/opendkim/TrustedHosts
InternalHosts	refile:/etc/opendkim/TrustedHosts
"""

            writeToFile = open(openDKIMConfigurePath, 'a')
            writeToFile.write(configData)
            writeToFile.close()

            ## Configure postfix specific settings

            postfixFilePath = "/etc/postfix/main.cf"

            configData = """
smtpd_milters = inet:127.0.0.1:8891
non_smtpd_milters = $smtpd_milters
milter_default_action = accept
"""

            writeToFile = open(postfixFilePath, 'a')
            writeToFile.write(configData)
            writeToFile.close()

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                data = open(openDKIMConfigurePath, 'r').readlines()
                writeToFile = open(openDKIMConfigurePath, 'w')
                for items in data:
                    if items.find('Socket') > -1 and items.find('local:') and items[0] != '#':
                        writeToFile.writelines('Socket  inet:8891@localhost\n')
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()

            #### Restarting Postfix and OpenDKIM

            command = "systemctl start opendkim"
            ProcessUtilities.executioner(command)

            command = "systemctl enable opendkim"
            ProcessUtilities.executioner(command)

            ##

            command = "systemctl restart postfix"
            ProcessUtilities.executioner(command)

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                      'configureOpenDKIM failed. Error %s [404].' % str(msg))
            return 0

    def debugEmailForSite(self, websiteName):

        ipFile = "/etc/cyberpanel/machineIP"
        f = open(ipFile)
        ipData = f.read()
        ipAddress = ipData.split('\n', 1)[0]

        try:
            import socket
            siteIPAddr = socket.gethostbyname('mail.%s' % (websiteName))

            if siteIPAddr != ipAddress:
                return 0, 'mail.%s does not point to %s.' % (websiteName, ipAddress)
        except:
            return 0, 'mail.%s does not point to %s.' % (websiteName, ipAddress)

        command = 'openssl s_client -connect mail.%s:993' % (websiteName)
        result = ProcessUtilities.outputExecutioner(command)

        if result.find('18 (self signed certificate)') > -1:
            return 0, 'No valid SSL on port 993.'
        else:
            return 1, 'All checks are OK.'


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--domain', help='Domain name!')
    parser.add_argument('--userName', help='Email Username!')
    parser.add_argument('--password', help='Email password!')
    parser.add_argument('--tempConfigPath', help='Temporary Configuration Path!')
    parser.add_argument('--install', help='Enable/Disable Policy Server!')
    parser.add_argument('--tempStatusPath', help='Path of temporary status file.')



    args = parser.parse_args()

    if args.function == "createEmailAccount":
        mailUtilities.createEmailAccount(args.domain, args.userName, args.password)
    elif args.function == "generateKeys":
        mailUtilities.generateKeys(args.domain)
    elif args.function == "configureOpenDKIM":
        mailUtilities.configureOpenDKIM()
    elif args.function == "configureSpamAssassin":
        mailUtilities.configureSpamAssassin()
    elif args.function == "saveSpamAssassinConfigs":
        mailUtilities.saveSpamAssassinConfigs(args.tempConfigPath)
    elif args.function == 'savePolicyServerStatus':
        mailUtilities.savePolicyServerStatus(args.install)
    elif args.function == 'installSpamAssassin':
        mailUtilities.installSpamAssassin("install", "SpamAssassin")
    elif args.function == 'installMailScanner':
        mailUtilities.installMailScanner("install", "installMailScanner")
    elif args.function == 'AfterEffects':
        mailUtilities.AfterEffects(args.domain)
    elif args.function == "ResetEmailConfigurations":
        extraArgs = {'tempStatusPath': args.tempStatusPath}
        background = MailServerManagerUtils(None, 'ResetEmailConfigurations', extraArgs)
        background.ResetEmailConfigurations()

if __name__ == "__main__":
    main()
