import CyberCPLogFileWriter as logging
import subprocess
import shlex
import argparse
from virtualHostUtilities import virtualHostUtilities
import os

class modSec:
    installLogPath = "/home/cyberpanel/modSecInstallLog"
    tempRulesFile = "/home/cyberpanel/tempModSecRules"

    @staticmethod
    def installModSec(install, modSecInstall):
        try:

            command = 'sudo yum install ols-modsecurity -y'

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
        except BaseException, msg:
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
SecDebugLogLevel 9
SecDebugLog /usr/local/lsws/logs/modsec.log
SecAuditEngine on
SecAuditLogRelevantStatus "^(?:5|4(?!04))"
SecAuditLogParts ABIJDEFHZ
SecAuditLogType Serial
SecAuditLog /usr/local/lsws/logs/auditmodsec.log
SecRuleEngine On
`
modsecurity_rules_file /usr/local/lsws/conf/modsec/rules.conf
}
"""


            confFile = os.path.join(virtualHostUtilities.Server_root,"conf/httpd_config.conf")

            conf = open(confFile,'a+')
            conf.write(initialConfigs)
            conf.close()

            rulesFilePath = os.path.join(virtualHostUtilities.Server_root,"conf/modsec/rules.conf")

            if not os.path.exists(rulesFilePath):
                initialRules = """
SecRule ARGS "\.\./" "t:normalisePathWin,id:99999,severity:4,msg:'Drive Access' ,log,auditlog,deny"
"""
                rule = open(rulesFilePath,'a+')
                rule.write(initialRules)
                rule.close()

            print "1,None"
            return

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [installModSecConfigs]")
            print "0," + str(msg)

    @staticmethod
    def saveModSecConfigs(tempConfigPath):
        try:

            data = open(tempConfigPath).readlines()
            os.remove(tempConfigPath)

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

            print "1,None"
            return

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [saveModSecConfigs]")
            print "0," + str(msg)

    @staticmethod
    def saveModSecRules():
        try:

            rulesFile = open(modSec.tempRulesFile,'r')
            data = rulesFile.read()
            rulesFile.close()

            rulesFilePath = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/rules.conf")

            rulesFile = open(rulesFilePath,'w')
            rulesFile.write(data)
            rulesFile.close()

            print data

            print "1,None"
            return

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [saveModSecRules]")
            print "0," + str(msg)



def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')

    parser.add_argument('--tempConfigPath', help='Temporary path to configurations data!')

    args = parser.parse_args()

    if args.function == "installModSecConfigs":
        modSec.installModSecConfigs()
    elif args.function == "saveModSecConfigs":
        modSec.saveModSecConfigs(args.tempConfigPath)
    elif args.function == "saveModSecRules":
        modSec.saveModSecRules()

if __name__ == "__main__":
    main()