import sys
sys.path.append('/usr/local/CyberCP')
from plogical import CyberCPLogFileWriter as logging
import subprocess
import shlex
import argparse
from plogical.virtualHostUtilities import virtualHostUtilities
import os
import tarfile
import shutil
from plogical.mailUtilities import mailUtilities
from plogical.processUtilities import ProcessUtilities
from plogical.installUtilities import installUtilities

class modSec:

    installLogPath = "/home/cyberpanel/modSecInstallLog"
    tempRulesFile = "/home/cyberpanel/tempModSecRules"
    mirrorPath = "cyberpanel.net"

    @staticmethod
    def installModSec():
        try:

            mailUtilities.checkHome()

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                command = 'sudo yum install ols-modsecurity -y'
            else:
                command = 'sudo DEBIAN_FRONTEND=noninteractive apt-get install ols-modsecurity -y'

            cmd = shlex.split(command)

            with open(modSec.installLogPath, 'w') as f:
                res = subprocess.call(cmd, stdout=f)

            if res == 1:
                writeToFile = open(modSec.installLogPath, 'a')
                writeToFile.writelines("Can not be installed.[404]\n")
                writeToFile.close()
                logging.CyberCPLogFileWriter.writeToFile("[Could not Install]")
                return 0
            else:
                writeToFile = open(modSec.installLogPath, 'a')
                writeToFile.writelines("ModSecurity Installed.[200]\n")
                writeToFile.close()

            return 1
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installModSec]")

    @staticmethod
    def installModSecConfigs():
        try:
            ## Try making a dir that will store ModSec configurations
            path = os.path.join(virtualHostUtilities.Server_root,"conf/modsec")
            try:
                os.mkdir(path)
            except:
                logging.CyberCPLogFileWriter.writeToFile(
                    "ModSecurity rules directory already exists." + "  [installModSecConfigs]")

            initialConfigs = """
module mod_security {
modsecurity  on
modsecurity_rules `
SecDebugLogLevel 0
SecDebugLog /usr/local/lsws/logs/modsec.log
SecAuditEngine on
SecAuditLogRelevantStatus "^(?:5|4(?!04))"
SecAuditLogParts AFH
SecAuditLogType Serial
SecAuditLog /usr/local/lsws/logs/auditmodsec.log
SecRuleEngine On
`
modsecurity_rules_file /usr/local/lsws/conf/modsec/rules.conf
}
"""

            confFile = os.path.join(virtualHostUtilities.Server_root,"conf/httpd_config.conf")

            confData = open(confFile).readlines()
            confData.reverse()

            modSecConfigFlag = False

            for items in confData:
                if items.find('module mod_security') > -1:
                    modSecConfigFlag = True
                    break

            if modSecConfigFlag == False:
                conf = open(confFile,'a+')
                conf.write(initialConfigs)
                conf.close()

            rulesFilePath = os.path.join(virtualHostUtilities.Server_root,"conf/modsec/rules.conf")

            if not os.path.exists(rulesFilePath):
                initialRules = """SecRule ARGS "\.\./" "t:normalisePathWin,id:99999,severity:4,msg:'Drive Access' ,log,auditlog,deny"
"""
                rule = open(rulesFilePath,'a+')
                rule.write(initialRules)
                rule.close()

            print("1,None")
            return

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [installModSecConfigs]")
            print("0," + str(msg))

    @staticmethod
    def saveModSecConfigs(tempConfigPath):
        try:

            data = open(tempConfigPath).readlines()
            os.remove(tempConfigPath)

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:

                confFile = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")
                confData = open(confFile).readlines()
                conf = open(confFile, 'w')

                for items in confData:

                    if items.find('modsecurity ') > -1:
                        conf.writelines(data[0])
                        continue
                    elif items.find('SecAuditEngine ') > -1:
                        conf.writelines(data[1])
                        continue
                    elif items.find('SecRuleEngine ') > -1:
                        conf.writelines(data[2])
                        continue
                    elif items.find('SecDebugLogLevel') > -1:
                        conf.writelines(data[3])
                        continue
                    elif items.find('SecAuditLogRelevantStatus ') > -1:
                        conf.writelines(data[5])
                        continue
                    elif items.find('SecAuditLogParts ') > -1:
                        conf.writelines(data[4])
                        continue
                    elif items.find('SecAuditLogType ') > -1:
                        conf.writelines(data[6])
                        continue
                    else:
                        conf.writelines(items)

                conf.close()

                installUtilities.reStartLiteSpeed()

                print("1,None")
                return
            else:
                confFile = os.path.join(virtualHostUtilities.Server_root, "conf/modsec.conf")
                confData = open(confFile).readlines()
                conf = open(confFile, 'w')

                for items in confData:

                    if items.find('SecAuditEngine ') > -1:
                        conf.writelines(data[0])
                        continue
                    elif items.find('SecRuleEngine ') > -1:
                        conf.writelines(data[1])
                        continue
                    elif items.find('SecDebugLogLevel') > -1:
                        conf.writelines(data[2])
                        continue
                    elif items.find('SecAuditLogRelevantStatus ') > -1:
                        conf.writelines(data[4])
                        continue
                    elif items.find('SecAuditLogParts ') > -1:
                        conf.writelines(data[3])
                        continue
                    elif items.find('SecAuditLogType ') > -1:
                        conf.writelines(data[5])
                        continue
                    else:
                        conf.writelines(items)

                conf.close()

                installUtilities.reStartLiteSpeed()

                print("1,None")
                return

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [saveModSecConfigs]")
            print("0," + str(msg))

    @staticmethod
    def saveModSecRules():
        try:
            rulesFile = open(modSec.tempRulesFile,'r')
            data = rulesFile.read()
            rulesFile.close()

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                rulesFilePath = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/rules.conf")
            else:
                rulesFilePath = os.path.join(virtualHostUtilities.Server_root, "conf/rules.conf")

            rulesFile = open(rulesFilePath,'w')
            rulesFile.write(data)
            rulesFile.close()

            installUtilities.reStartLiteSpeed()

            print("1,None")
            return

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [saveModSecRules]")
            print("0," + str(msg))

    @staticmethod
    def setupComodoRules():
        try:
            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                pathTOOWASPFolder = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/comodo")
                extractLocation = os.path.join(virtualHostUtilities.Server_root, "conf/modsec")

                if os.path.exists(pathTOOWASPFolder):
                    shutil.rmtree(pathTOOWASPFolder)

                if os.path.exists('comodo.tar.gz'):
                    os.remove('comodo.tar.gz')

                command = "wget https://" + modSec.mirrorPath + "/modsec/comodo.tar.gz"
                result = subprocess.call(shlex.split(command))

                if result == 1:
                    return 0

                tar = tarfile.open('comodo.tar.gz')
                tar.extractall(extractLocation)
                tar.close()

                return 1
            else:
                if os.path.exists('/usr/local/lsws/conf/comodo_litespeed'):
                    shutil.rmtree('/usr/local/lsws/conf/comodo_litespeed')

                extractLocation = os.path.join(virtualHostUtilities.Server_root, "conf")

                if os.path.exists('cpanel_litespeed_vendor'):
                    os.remove('cpanel_litespeed_vendor')

                command = "wget https://waf.comodo.com/api/cpanel_litespeed_vendor"
                result = subprocess.call(shlex.split(command))

                if result == 1:
                    return 0

                command = "unzip cpanel_litespeed_vendor -d " + extractLocation
                subprocess.call(shlex.split(command))

                return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [setupComodoRules]")
            return 0

    @staticmethod
    def installComodo():
        try:

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                if modSec.setupComodoRules() == 0:
                    print('0, Unable to download Comodo Rules.')
                    return

                owaspRulesConf = """modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/modsecurity.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/00_Init_Initialization.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/01_Init_AppsInitialization.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/02_Global_Generic.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/03_Global_Agents.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/04_Global_Domains.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/05_Global_Backdoor.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/06_XSS_XSS.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/07_Global_Other.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/08_Bruteforce_Bruteforce.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/09_HTTP_HTTP.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/10_HTTP_HTTPDoS.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/11_HTTP_Protocol.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/12_HTTP_Request.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/13_Outgoing_FilterGen.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/14_Outgoing_FilterASP.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/15_Outgoing_FilterPHP.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/16_Outgoing_FilterSQL.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/17_Outgoing_FilterOther.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/18_Outgoing_FilterInFrame.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/19_Outgoing_FiltersEnd.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/20_PHP_PHPGen.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/21_SQL_SQLi.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/22_Apps_Joomla.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/23_Apps_JComponent.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/24_Apps_WordPress.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/25_Apps_WPPlugin.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/26_Apps_WHMCS.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/27_Apps_Drupal.conf
    modsecurity_rules_file /usr/local/lsws/conf/modsec/comodo/28_Apps_OtherApps.conf
    """

                confFile = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

                confData = open(confFile).readlines()

                conf = open(confFile, 'w')

                for items in confData:
                    if items.find('/usr/local/lsws/conf/modsec/rules.conf') > -1:
                        conf.writelines(items)
                        conf.write(owaspRulesConf)
                        continue
                    else:
                        conf.writelines(items)

                conf.close()

                installUtilities.reStartLiteSpeed()
                print("1,None")
                return
            else:
                if os.path.exists('/usr/local/lsws/conf/comodo_litespeed'):
                    shutil.rmtree('/usr/local/lsws/conf/comodo_litespeed')

                extractLocation = os.path.join(virtualHostUtilities.Server_root, "conf")

                if os.path.exists('cpanel_litespeed_vendor'):
                    os.remove('cpanel_litespeed_vendor')

                command = "wget https://waf.comodo.com/api/cpanel_litespeed_vendor"
                result = subprocess.call(shlex.split(command))

                if result == 1:
                    return 0

                command = "unzip cpanel_litespeed_vendor -d " + extractLocation
                result = subprocess.call(shlex.split(command))

                command = 'sudo chown -R lsadm:lsadm /usr/local/lsws/conf'
                subprocess.call(shlex.split(command))

                installUtilities.reStartLiteSpeed()
                print("1,None")
                return

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [installComodo]")
            print("0," + str(msg))

    @staticmethod
    def disableComodo():
        try:

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                confFile = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")
                confData = open(confFile).readlines()
                conf = open(confFile, 'w')

                for items in confData:
                    if items.find('modsec/comodo') > -1:
                        continue
                    else:
                        conf.writelines(items)

                conf.close()
                installUtilities.reStartLiteSpeed()

                print("1,None")

            else:
                try:
                    shutil.rmtree('/usr/local/lsws/conf/comodo_litespeed')
                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [disableComodo]')

                installUtilities.reStartLiteSpeed()
                print("1,None")


        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [disableComodo]")
            print("0," + str(msg))

    @staticmethod
    def setupOWASPRules():
        try:
            pathTOOWASPFolder = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/owasp")
            extractLocation = os.path.join(virtualHostUtilities.Server_root, "conf/modsec")

            if os.path.exists(pathTOOWASPFolder):
                shutil.rmtree(pathTOOWASPFolder)

            if os.path.exists('owasp.tar.gz'):
                os.remove('owasp.tar.gz')

            command = "wget https://" + modSec.mirrorPath + "/modsec/owasp.tar.gz"
            result = subprocess.call(shlex.split(command))

            if result == 1:
                return 0

            tar = tarfile.open('owasp.tar.gz')
            tar.extractall(extractLocation)
            tar.close()

            return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [setupOWASPRules]")
            return 0

    @staticmethod
    def installOWASP():
        try:
            if modSec.setupOWASPRules() == 0:
                print('0, Unable to download OWASP Rules.')
                return

            owaspRulesConf = """modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/modsecurity.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/crs-setup.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-901-INITIALIZATION.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-905-COMMON-EXCEPTIONS.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-910-IP-REPUTATION.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-911-METHOD-ENFORCEMENT.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-912-DOS-PROTECTION.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-913-SCANNER-DETECTION.conf
#modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-920-PROTOCOL-ENFORCEMENT.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-921-PROTOCOL-ATTACK.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-930-APPLICATION-ATTACK-LFI.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-931-APPLICATION-ATTACK-RFI.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-932-APPLICATION-ATTACK-RCE.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-933-APPLICATION-ATTACK-PHP.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-941-APPLICATION-ATTACK-XSS.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-942-APPLICATION-ATTACK-SQLI.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-943-APPLICATION-ATTACK-SESSION-FIXATION.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/REQUEST-949-BLOCKING-EVALUATION.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/RESPONSE-950-DATA-LEAKAGES.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/RESPONSE-951-DATA-LEAKAGES-SQL.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/RESPONSE-952-DATA-LEAKAGES-JAVA.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/RESPONSE-953-DATA-LEAKAGES-PHP.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/RESPONSE-954-DATA-LEAKAGES-IIS.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/RESPONSE-959-BLOCKING-EVALUATION.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/RESPONSE-980-CORRELATION.conf
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp/rules/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf
"""

            confFile = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

            confData = open(confFile).readlines()

            conf = open(confFile, 'w')

            for items in confData:
                if items.find('/usr/local/lsws/conf/modsec/rules.conf') > -1:
                    conf.writelines(items)
                    conf.write(owaspRulesConf)
                    continue
                else:
                    conf.writelines(items)

            conf.close()
            installUtilities.reStartLiteSpeed()

            print("1,None")

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [installOWASP]")
            print("0," + str(msg))

    @staticmethod
    def disableOWASP():
        try:

            confFile = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")
            confData = open(confFile).readlines()
            conf = open(confFile, 'w')

            for items in confData:
                if items.find('modsec/owasp') > -1:
                    continue
                else:
                    conf.writelines(items)

            conf.close()
            installUtilities.reStartLiteSpeed()

            print("1,None")

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [disableOWASP]")
            print("0," + str(msg))

    @staticmethod
    def disableRuleFile(fileName, packName):
        try:

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                confFile = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")
                confData = open(confFile).readlines()
                conf = open(confFile, 'w')

                for items in confData:
                    if items.find('modsec/'+packName) > -1 and items.find(fileName) > -1:
                        conf.write("#" + items)
                    else:
                        conf.writelines(items)

                conf.close()

            else:
                path = '/usr/local/lsws/conf/comodo_litespeed/'
                completePath = path + fileName
                completePathBak = path + fileName + '.bak'

                command = 'mv ' + completePath + ' ' + completePathBak
                ProcessUtilities.executioner(command)

            installUtilities.reStartLiteSpeed()

            print("1,None")

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [disableRuleFile]")
            print("0," + str(msg))

    @staticmethod
    def enableRuleFile(fileName, packName):
        try:

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                confFile = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")
                confData = open(confFile).readlines()
                conf = open(confFile, 'w')

                for items in confData:
                    if items.find('modsec/' + packName) > -1 and items.find(fileName) > -1:
                        conf.write(items.lstrip('#'))
                    else:
                        conf.writelines(items)

                conf.close()
            else:
                path = '/usr/local/lsws/conf/comodo_litespeed/'
                completePath = path + fileName
                completePathBak = path + fileName + '.bak'

                command = 'mv ' + completePathBak + ' ' + completePath
                ProcessUtilities.executioner(command)

            installUtilities.reStartLiteSpeed()

            print("1,None")

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [enableRuleFile]")
            print("0," + str(msg))


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')

    parser.add_argument('--tempConfigPath', help='Temporary path to configurations data!')
    parser.add_argument('--packName', help='ModSecurity supplier name!')
    parser.add_argument('--fileName', help='Filename to enable or disable!')

    args = parser.parse_args()

    if args.function == "installModSecConfigs":
        modSec.installModSecConfigs()
    elif args.function == "installModSec":
        modSec.installModSec()
    elif args.function == "saveModSecConfigs":
        modSec.saveModSecConfigs(args.tempConfigPath)
    elif args.function == "saveModSecRules":
        modSec.saveModSecRules()
    elif args.function == "setupOWASPRules":
        modSec.setupOWASPRules()
    elif args.function == "installOWASP":
        modSec.installOWASP()
    elif args.function == "disableOWASP":
        modSec.disableOWASP()
    elif args.function == "setupComodoRules":
        modSec.setupComodoRules()
    elif args.function == "installComodo":
        modSec.installComodo()
    elif args.function == "disableComodo":
        modSec.disableComodo()
    elif args.function == "disableRuleFile":
        modSec.disableRuleFile(args.fileName, args.packName)
    elif args.function == "enableRuleFile":
        modSec.enableRuleFile(args.fileName, args.packName)

if __name__ == "__main__":
    main()