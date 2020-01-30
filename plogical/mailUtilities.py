import os,sys
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

            import tldextract

            #extractDomain = tldextract.extract(virtualHostName)
            #virtualHostName = extractDomain.domain + '.' + extractDomain.suffix

            if os.path.exists("/etc/opendkim/keys/" + virtualHostName + "/default.txt"):
                return 1, "None"


            path = '/etc/opendkim/keys/%s' % (virtualHostName)
            command = 'mkdir %s' % (path)
            ProcessUtilities.normalExecutioner(command)

            ## Generate keys

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
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
            configToWrite = "default._domainkey." + virtualHostName + " " + virtualHostName + ":default:/etc/opendkim/keys/" + virtualHostName + "/default.private\n"

            writeToFile = open(keyTable, 'a')
            writeToFile.write(configToWrite)
            writeToFile.close()

            ## Edit signing table

            signingTable = "/etc/opendkim/SigningTable"
            configToWrite = "*@" + virtualHostName + " default._domainkey." + virtualHostName + "\n"

            writeToFile = open(signingTable, 'a')
            writeToFile.write(configToWrite)
            writeToFile.close()

            ## Trusted hosts

            trustedHosts = "/etc/opendkim/TrustedHosts"
            configToWrite = virtualHostName + "\n"

            writeToFile = open(trustedHosts, 'a')
            writeToFile.write(configToWrite)
            writeToFile.close()

            ## Restart postfix and OpenDKIM

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

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
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
    def checkIfSpamAssassinInstalled():
        try:

            path = "/etc/mail/spamassassin/local.cf"

            command = "sudo cat " + path
            output = ProcessUtilities.outputExecutioner(command)

            if output.find('No such') > -1:
                return 0
            else:
                return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [checkIfSpamAssassinInstalled]")
            return 0

    @staticmethod
    def configureSpamAssassin():
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
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


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--domain', help='Domain name!')
    parser.add_argument('--userName', help='Email Username!')
    parser.add_argument('--password', help='Email password!')
    parser.add_argument('--tempConfigPath', help='Temporary Configuration Path!')
    parser.add_argument('--install', help='Enable/Disable Policy Server!')



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
    elif args.function == 'AfterEffects':
        mailUtilities.AfterEffects(args.domain)

if __name__ == "__main__":
    main()