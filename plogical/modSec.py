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

    # Compatible ModSecurity binaries (built against custom OLS headers)
    # These prevent ABI incompatibility crashes (Signal 11/SIGSEGV)
    MODSEC_COMPATIBLE = {
        'rhel8': {
            'url': 'https://cyberpanel.net/mod_security-compatible-rhel8.so',
            'sha256': 'bbbf003bdc7979b98f09b640dffe2cbbe5f855427f41319e4c121403c05837b2'
        },
        'rhel9': {
            'url': 'https://cyberpanel.net/mod_security-compatible-rhel.so',
            'sha256': '19deb2ffbaf1334cf4ce4d46d53f747a75b29e835bf5a01f91ebcc0c78e98629'
        },
        'ubuntu': {
            'url': 'https://cyberpanel.net/mod_security-compatible-ubuntu.so',
            'sha256': 'ed02c813136720bd4b9de5925f6e41bdc8392e494d7740d035479aaca6d1e0cd'
        }
    }

    @staticmethod
    def detectPlatform():
        """Detect OS platform for compatible binary selection"""
        try:
            # Check for Ubuntu/Debian
            if os.path.exists('/etc/lsb-release'):
                with open('/etc/lsb-release', 'r') as f:
                    content = f.read()
                    if 'Ubuntu' in content or 'ubuntu' in content:
                        return 'ubuntu'

            # Check for Debian
            if os.path.exists('/etc/debian_version'):
                return 'ubuntu'  # Use Ubuntu binary for Debian

            # Check for RHEL-based distributions
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    content = f.read().lower()

                    # Check for version 8.x
                    if 'version="8.' in content or 'version_id="8' in content:
                        return 'rhel8'

                    # Check for version 9.x
                    if 'version="9.' in content or 'version_id="9' in content:
                        return 'rhel9'

            return 'rhel9'  # Default to rhel9
        except:
            return 'rhel9'

    @staticmethod
    def downloadCompatibleModSec(platform):
        """Download and install compatible ModSecurity binary"""
        try:
            config = modSec.MODSEC_COMPATIBLE.get(platform)
            if not config:
                logging.CyberCPLogFileWriter.writeToFile(f"No compatible ModSecurity for platform {platform}")
                return False

            modsec_path = "/usr/local/lsws/modules/mod_security.so"
            tmp_path = "/tmp/mod_security-compatible.so"

            # Download compatible binary
            command = f"wget -q {config['url']} -O {tmp_path}"
            result = subprocess.call(shlex.split(command))
            if result != 0:
                logging.CyberCPLogFileWriter.writeToFile("Failed to download compatible ModSecurity")
                return False

            # Verify checksum
            import hashlib
            sha256_hash = hashlib.sha256()
            with open(tmp_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            actual_sha256 = sha256_hash.hexdigest()

            if actual_sha256 != config['sha256']:
                logging.CyberCPLogFileWriter.writeToFile(f"ModSecurity checksum mismatch: expected {config['sha256']}, got {actual_sha256}")
                os.remove(tmp_path)
                return False

            # Backup original if exists
            if os.path.exists(modsec_path):
                shutil.copy2(modsec_path, f"{modsec_path}.stock")

            # Install compatible version
            shutil.move(tmp_path, modsec_path)
            os.chmod(modsec_path, 0o644)

            logging.CyberCPLogFileWriter.writeToFile("Installed compatible ModSecurity binary")
            return True

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [downloadCompatibleModSec]")
            return False

    @staticmethod
    def installModSec():
        try:

            mailUtilities.checkHome()

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
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

            # Check if custom OLS binary is installed - if so, replace with compatible ModSecurity
            custom_ols_marker = "/usr/local/lsws/modules/cyberpanel_ols.so"
            if os.path.exists(custom_ols_marker):
                writeToFile = open(modSec.installLogPath, 'a')
                writeToFile.writelines("Custom OLS detected, installing compatible ModSecurity...\n")
                writeToFile.close()

                platform = modSec.detectPlatform()
                if modSec.downloadCompatibleModSec(platform):
                    writeToFile = open(modSec.installLogPath, 'a')
                    writeToFile.writelines("Compatible ModSecurity installed successfully.\n")
                    writeToFile.close()
                else:
                    writeToFile = open(modSec.installLogPath, 'a')
                    writeToFile.writelines("WARNING: Could not install compatible ModSecurity. May experience crashes.\n")
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
                
                def modify_config(lines):
                    """Update ModSecurity configuration parameters"""
                    modified = []
                    
                    for line in lines:
                        if line.find('modsecurity ') > -1:
                            modified.append(data[0])
                            continue
                        elif line.find('SecAuditEngine ') > -1:
                            modified.append(data[1])
                            continue
                        elif line.find('SecRuleEngine ') > -1:
                            modified.append(data[2])
                            continue
                        elif line.find('SecDebugLogLevel') > -1:
                            modified.append(data[3])
                            continue
                        elif line.find('SecAuditLogRelevantStatus ') > -1:
                            modified.append(data[5])
                            continue
                        elif line.find('SecAuditLogParts ') > -1:
                            modified.append(data[4])
                            continue
                        elif line.find('SecAuditLogType ') > -1:
                            modified.append(data[6])
                            continue
                        else:
                            modified.append(line)
                    
                    return modified
                
                # Use safe modification with backup and validation
                success, error = installUtilities.installUtilities.safeModifyHttpdConfig(
                    modify_config,
                    "Update ModSecurity configuration parameters"
                )
                
                if not success:
                    error_msg = error if error else "Unknown error"
                    logging.writeToFile(f"[saveModSecConfigs] Failed: {error_msg}")
                    print(f"0,{error_msg}")
                    return

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
                        conf.write(owaspRulesConf)
                        conf.writelines(items)
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

                command = "wget --no-check-certificate https://waf.comodo.com/api/cpanel_litespeed_vendor"
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
            pathToOWASFolderNew = '%s/modsec/owasp-modsecurity-crs-4.18.0' % (virtualHostUtilities.vhostConfPath)

            command = 'mkdir -p /usr/local/lsws/conf/modsec'
            result = subprocess.call(shlex.split(command))
            if result != 0:
                logging.CyberCPLogFileWriter.writeToFile("Failed to create modsec directory: " + str(result) + " [setupOWASPRules]")
                return 0

            if os.path.exists(pathToOWASFolderNew):
                shutil.rmtree(pathToOWASFolderNew)

            if os.path.exists(pathTOOWASPFolder):
                shutil.rmtree(pathTOOWASPFolder)

            if os.path.exists('owasp.tar.gz'):
                os.remove('owasp.tar.gz')

            # Clean up any existing zip file
            if os.path.exists('/usr/local/lsws/conf/modsec/owasp.zip'):
                os.remove('/usr/local/lsws/conf/modsec/owasp.zip')

            command = "wget https://github.com/coreruleset/coreruleset/archive/refs/tags/v4.18.0.zip -O /usr/local/lsws/conf/modsec/owasp.zip"
            logging.CyberCPLogFileWriter.writeToFile("Downloading OWASP rules: " + command + " [setupOWASPRules]")
            result = subprocess.call(shlex.split(command))

            if result != 0:
                logging.CyberCPLogFileWriter.writeToFile("Failed to download OWASP rules: " + str(result) + " [setupOWASPRules]")
                return 0

            command = "unzip -o /usr/local/lsws/conf/modsec/owasp.zip -d /usr/local/lsws/conf/modsec/"
            logging.CyberCPLogFileWriter.writeToFile("Extracting OWASP rules: " + command + " [setupOWASPRules]")
            result = subprocess.call(shlex.split(command))

            if result != 0:
                logging.CyberCPLogFileWriter.writeToFile("Failed to extract OWASP rules: " + str(result) + " [setupOWASPRules]")
                return 0

            command = 'mv /usr/local/lsws/conf/modsec/coreruleset-4.18.0 /usr/local/lsws/conf/modsec/owasp-modsecurity-crs-4.18.0'
            logging.CyberCPLogFileWriter.writeToFile("Moving OWASP rules: " + command + " [setupOWASPRules]")
            result = subprocess.call(shlex.split(command))

            if result != 0:
                logging.CyberCPLogFileWriter.writeToFile("Failed to move OWASP rules: " + str(result) + " [setupOWASPRules]")
                return 0

            command = 'mv %s/crs-setup.conf.example %s/crs-setup.conf' % (pathToOWASFolderNew, pathToOWASFolderNew)
            result = subprocess.call(shlex.split(command))

            if result != 0:
                return 0

            command = 'mv %s/rules/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf.example %s/rules/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf' % (pathToOWASFolderNew, pathToOWASFolderNew)
            result = subprocess.call(shlex.split(command))

            if result != 0:
                return 0

            command = 'mv %s/rules/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf.example %s/rules/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf' % (
            pathToOWASFolderNew, pathToOWASFolderNew)
            result = subprocess.call(shlex.split(command))

            if result != 0:
                return 0

            # CRS v4.0.0 uses a different structure - it has a main crs.conf file
            content = """include {pathToOWASFolderNew}/crs.conf
"""
            writeToFile = open('%s/owasp-master.conf' % (pathToOWASFolderNew), 'w')
            writeToFile.write(content.replace('{pathToOWASFolderNew}', pathToOWASFolderNew))
            writeToFile.close()

            return 1

        except BaseException as msg:
            print(str(msg))
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [setupOWASPRules]")
            return 0

    @staticmethod
    def installOWASP():
        try:
            if modSec.setupOWASPRules() == 0:
                print('0, Unable to download OWASP Rules.')
                return

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                owaspRulesConf = """
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp-modsecurity-crs-4.18.0/owasp-master.conf
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
                
                # Verify the installation
                owaspPath = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/owasp-modsecurity-crs-4.18.0")
                if not os.path.exists(owaspPath) or not os.path.exists(os.path.join(owaspPath, "owasp-master.conf")):
                    logging.CyberCPLogFileWriter.writeToFile("OWASP installation verification failed - files not found [installOWASP]")
                    print("0, OWASP installation verification failed")
                    return
                    
            else:
                confFile = os.path.join('/usr/local/lsws/conf/modsec.conf')
                confData = open(confFile).readlines()

                conf = open(confFile, 'w')

                for items in confData:
                    if items.find('/conf/comodo_litespeed/') > -1:
                        conf.writelines(items)
                        conf.write('Include /usr/local/lsws/conf/modsec/owasp-modsecurity-crs-4.18.0/*.conf\n')
                        continue
                    else:
                        conf.writelines(items)

                conf.close()

            installUtilities.reStartLiteSpeed()
            
            logging.CyberCPLogFileWriter.writeToFile("OWASP ModSecurity rules installed successfully [installOWASP]")
            print("1,None")

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [installOWASP]")
            print("0," + str(msg))

    @staticmethod
    def disableOWASP():
        try:
            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
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
            else:
                confFile = os.path.join("/usr/local/lsws/conf/modsec.conf")
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

            confFile = os.path.join('/usr/local/lsws/conf/modsec/owasp-modsecurity-crs-3.0-master/owasp-master.conf')
            confData = open(confFile).readlines()
            conf = open(confFile, 'w')

            for items in confData:
                if items.find('modsec/' + packName) > -1 and items.find(fileName) > -1:
                    conf.write("#" + items)
                else:
                    conf.writelines(items)

            conf.close()

            installUtilities.reStartLiteSpeed()

            print("1,None")

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "  [disableRuleFile]")
            print("0," + str(msg))

    @staticmethod
    def enableRuleFile(fileName, packName):
        try:

            confFile = os.path.join('/usr/local/lsws/conf/modsec/owasp-modsecurity-crs-3.0-master/owasp-master.conf')
            confData = open(confFile).readlines()
            conf = open(confFile, 'w')

            for items in confData:
                if items.find('modsec/' + packName) > -1 and items.find(fileName) > -1:
                    conf.write(items.lstrip('#'))
                else:
                    conf.writelines(items)

            conf.close()

            # if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            #     confFile = os.path.join('/usr/local/lsws/conf/modsec/owasp-modsecurity-crs-3.0-master/owasp-master.conf')
            #     confData = open(confFile).readlines()
            #     conf = open(confFile, 'w')
            #
            #     for items in confData:
            #         if items.find('modsec/' + packName) > -1 and items.find(fileName) > -1:
            #             conf.write(items.lstrip('#'))
            #         else:
            #             conf.writelines(items)
            #
            #     conf.close()
            # else:
            #     path = '/usr/local/lsws/conf/comodo_litespeed/'
            #     completePath = path + fileName
            #     completePathBak = path + fileName + '.bak'
            #
            #     command = 'mv ' + completePathBak + ' ' + completePath
            #     ProcessUtilities.executioner(command)

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
