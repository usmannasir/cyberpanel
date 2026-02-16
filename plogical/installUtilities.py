import subprocess
import sys
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
import shutil
import pexpect
import os
import shlex
from plogical.processUtilities import ProcessUtilities
from datetime import datetime

class installUtilities:

    Server_root_path = "/usr/local/lsws"

    @staticmethod
    def enableEPELRepo():
        try:
            cmd = []
            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("epel-release")
            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("         Could not add EPEL repo              " )
                print("###############################################")
            else:
                print("###############################################")
                print("          EPEL Repo Added                      ")
                print("###############################################")
        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [enableEPELRepo]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [enableEPELRepo]")
            return 0

        return 1


    @staticmethod
    def addLiteSpeedRepo():
        try:
            # Use the official LiteSpeed repository installation script
            # This supports all OS versions including CentOS/AlmaLinux/Rocky 7, 8, and 9
            cmd = "wget -O - https://repo.litespeed.sh | bash"
            
            res = subprocess.call(cmd, shell=True)
            
            if res == 1:
                print("###############################################")
                print("         Could not add Litespeed repo         " )
                print("###############################################")
            else:
                print("###############################################")
                print("          Litespeed Repo Added                 ")
                print("###############################################")

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [addLiteSpeedRepo]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [addLiteSpeedRepo]")
            return 0

        return 1

    @staticmethod
    def installLiteSpeed():

        try:

            cmd = []

            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("openlitespeed")

            res = subprocess.call(cmd)


            if res == 1:
                print("###############################################")
                print("         Could not install Litespeed          " )
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("          Litespeed Installed                  ")
                print("###############################################")

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installLiteSpeed]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installLiteSpeed]")
            return 0

        return 1


    @staticmethod
    def startLiteSpeed():

        try:

            cmd = []

            cmd.append("/usr/local/lsws/bin/lswsctrl")
            cmd.append("start")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("         Could not start Litespeed server      ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("          Litespeed Started                    ")
                print("###############################################")

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startLiteSpeed]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startLiteSpeed]")
            return 0

        return 1


    @staticmethod
    def reStartLiteSpeed():
        try:

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "systemctl restart lsws"
            else:
                command = "/usr/local/lsws/bin/lswsctrl restart"

            ProcessUtilities.normalExecutioner(command)

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        return 1

    @staticmethod
    def reStartLiteSpeedSocket():
        try:

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "sudo systemctl restart lsws"
            else:
                command = "sudo /usr/local/lsws/bin/lswsctrl restart"

            return ProcessUtilities.executioner(command)

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0

    @staticmethod
    def stopLiteSpeedSocket():
        try:

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "sudo systemctl stop lsws"
            else:
                command = "sudo /usr/local/lsws/bin/lswsctrl stop"

            return ProcessUtilities.executioner(command)

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0


    @staticmethod
    def reStartOpenLiteSpeed(restart,orestart):
        try:

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "sudo systemctl restart lsws"
            else:
                command = "sudo /usr/local/lsws/bin/lswsctrl restart"

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("         Could not restart Litespeed serve     ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("          Litespeed Re-Started                 ")
                print("###############################################")

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartOpenLiteSpeed]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [reStartOpenLiteSpeed]")
            return 0
        return 1

    @staticmethod
    def safeModifyHttpdConfig(config_modifier, description="config modification", skip_validation=False):
        """
        Safely modify httpd_config.conf with backup, validation, and rollback on failure.
        Prevents corrupted configs that cause OpenLiteSpeed to fail binding ports 80/443.
        
        Args:
            config_modifier: A function that takes file content (list of lines) and returns modified content
            description: Description of the modification for logging
        
        Returns:
            tuple: (success: bool, error_message: str or None)
        
        Reference: https://github.com/usmannasir/cyberpanel/issues/1609
        """
        config_file = "/usr/local/lsws/conf/httpd_config.conf"
        
        # Check file existence using ProcessUtilities (handles permissions correctly)
        try:
            command = 'test -f {} && echo exists || echo notfound'.format(config_file)
            result = ProcessUtilities.outputExecutioner(command).strip()
            if result == 'notfound':
                error_msg = f"Config file not found: {config_file}"
                CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] {error_msg}")
                return False, error_msg
        except Exception as e:
            # Fallback to os.path.exists if ProcessUtilities fails
            if not os.path.exists(config_file):
                error_msg = f"Config file not found: {config_file} (check failed: {str(e)})"
                CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] {error_msg}")
                return False, error_msg
        
        # Create backup with timestamp
        try:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_file = f"{config_file}.backup-{timestamp}"
            shutil.copy2(config_file, backup_file)
            CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] Created backup: {backup_file} for {description}")
        except Exception as e:
            error_msg = f"Failed to create backup: {str(e)}"
            CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] {error_msg}")
            return False, error_msg
        
        # Read current config
        try:
            with open(config_file, 'r') as f:
                original_content = f.readlines()
        except Exception as e:
            error_msg = f"Failed to read config file: {str(e)}"
            CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] {error_msg}")
            return False, error_msg
        
        # Modify config using callback
        try:
            modified_content = config_modifier(original_content)
            if not isinstance(modified_content, list):
                error_msg = "Config modifier must return a list of lines"
                CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] {error_msg}")
                return False, error_msg
        except Exception as e:
            error_msg = f"Config modifier function failed: {str(e)}"
            CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] {error_msg}")
            return False, error_msg
        
        # Write modified config
        try:
            with open(config_file, 'w') as f:
                f.writelines(modified_content)
        except Exception as e:
            error_msg = f"Failed to write modified config: {str(e)}"
            CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] {error_msg}")
            # Restore backup
            try:
                shutil.copy2(backup_file, config_file)
                CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] Restored backup due to write failure")
            except:
                pass
            return False, error_msg
        
        # Validate config using openlitespeed -t (for OLS)
        # Note: openlitespeed -t may return non-zero due to warnings, so we check for actual errors
        # Skip validation if skip_validation=True (useful when pre-existing config has errors)
        if skip_validation:
            CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] Skipping validation as requested for: {description}")
        else:
            try:
                if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                    openlitespeed_bin = '/usr/local/lsws/bin/openlitespeed'
                    if os.path.exists(openlitespeed_bin):
                        validate_cmd = [openlitespeed_bin, '-t']
                        result = subprocess.run(validate_cmd, capture_output=True, text=True, timeout=30)
                        
                        # Check for actual errors (not just warnings)
                        # openlitespeed -t returns 0 on success, non-zero on errors
                        # But it may also return non-zero for warnings, so check for actual [ERROR] lines
                        if result.returncode != 0:
                            # Check if there are actual ERROR log lines (not just WARN or the word "error" in text)
                            error_output = result.stderr or result.stdout or ''
                            # Look for lines that start with [ERROR] or contain [ERROR] (actual error log entries)
                            error_lines = [line for line in error_output.split('\n') if '[ERROR]' in line.upper()]
                            if error_lines:
                                # Only fail on actual errors, not warnings
                                error_msg = f"Config validation failed with errors: {' '.join(error_lines[:3])}"
                                CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] {error_msg}")
                                # Restore backup
                                try:
                                    shutil.copy2(backup_file, config_file)
                                    CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] Restored backup due to validation failure")
                                except Exception as restore_error:
                                    CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] CRITICAL: Failed to restore backup: {str(restore_error)}")
                                return False, error_msg
                            else:
                                # Only warnings, not errors - proceed
                                CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] Config validation has warnings but no errors, proceeding")
                    else:
                        # openlitespeed binary not found, skip validation
                        CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] Warning: openlitespeed binary not found, skipping config validation")
                else:
                    # For LiteSpeed Enterprise, validation is not available via lswsctrl -t
                    CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] Skipping validation for LiteSpeed Enterprise")
            except Exception as e:
                error_msg = f"Config validation error: {str(e)}"
                CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] {error_msg}")
                # Restore backup
                try:
                    shutil.copy2(backup_file, config_file)
                    CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] Restored backup due to validation error")
                except:
                    pass
                return False, error_msg
        
        CyberCPLogFileWriter.writeToFile(f"[safeModifyHttpdConfig] Successfully modified and validated config: {description}")
        return True, None

    @staticmethod
    def changePortTo80():
        try:
            def modify_config(lines):
                modified = []
                for line in lines:
                    if "*:8088" in line:
                        modified.append(line.replace("*:8088", "*:80"))
                    else:
                        modified.append(line)
                return modified
            
            success, error = installUtilities.safeModifyHttpdConfig(
                modify_config, 
                "Change port from 8088 to 80"
            )
            
            if not success:
                error_msg = error if error else "Unknown error"
                CyberCPLogFileWriter.writeToFile(f"[changePortTo80] Failed: {error_msg}")
                return 0
            
            return installUtilities.reStartLiteSpeed()
            
        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [changePortTo80]")
            return 0


    @staticmethod
    def installAllPHPVersion():

        try:
            cmd = []

            cmd.append("yum")
            cmd.append("groupinstall")
            cmd.append("lsphp-all")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("         Could not install PHP Binaries        ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("          PHP Binaries installed               ")
                print("###############################################")

                writeDataToFile = open(installUtilities.Server_root_path + "/conf/httpd_config.conf", "a")




        except OSError as msg:

            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installAllPHPVersion]")

            return 0

        except ValueError as msg:

            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installAllPHPVersion]")

            return 0

        return 1


    @staticmethod
    def installAllPHPToLitespeed():
        try:
            path = installUtilities.Server_root_path + "/conf/"
            if not os.path.exists(path):
                shutil.copytree("phpconfigs",path+"phpconfigs")

            php53 = "include phpconfigs/php53.conf\n"
            php54 = "include phpconfigs/php54.conf\n"
            php55 = "include phpconfigs/php55.conf\n"
            php56 = "include phpconfigs/php56.conf\n"
            php70 = "include phpconfigs/php70.conf\n"

            writeDataToFile = open(path+"httpd_config.conf", 'a')


            writeDataToFile.writelines(php53)
            writeDataToFile.writelines(php54)
            writeDataToFile.writelines(php55)
            writeDataToFile.writelines(php56)
            writeDataToFile.writelines(php70)

            writeDataToFile.close()

        except IOError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installAllPHPToLitespeed]")
            return 0

        return 1

    @staticmethod
    def installMainWebServer():
        if installUtilities.enableEPELRepo() == 1:
            if installUtilities.addLiteSpeedRepo() == 1:
                if installUtilities.installLiteSpeed() == 1:
                    if installUtilities.startLiteSpeed() == 1:
                        if installUtilities.installAllPHPVersion():
                            if installUtilities.installAllPHPToLitespeed():
                                return 1
                            else:
                                return 0
                        else:
                            return 0
                    else:
                        return 0
                else:
                    return 0
            else:
                return 0
        else:
            return 0

    @staticmethod
    def removeWebServer():

        try:
            cmd = []
            cmd.append("yum")
            cmd.append("-y")
            cmd.append("remove")
            cmd.append("openlitespeed")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("          Could not remove Litespeed           ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("            Litespeed Removed                  ")
                print("###############################################")


        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [removeWebServer]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [removeWebServer]")
            return 0


        try:
            cmd = []
            cmd.append("yum")
            cmd.append("-y")
            cmd.append("remove")
            cmd.append("lsphp*")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("           Could not PHP Binaries              ")
                print("###############################################")
            else:

                print("###############################################")
                print("            PHP Binaries Removed              ")
                print("###############################################")
                sys.exit()

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [removeWebServer]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [removeWebServer]")
            return 0


        try:
            shutil.rmtree(installUtilities.Server_root_path)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [removeWebServer]")
            return 0

        return 1

    @staticmethod
    def startMariaDB():

        ############## Start mariadb ######################

        try:

            cmd = []

            cmd.append("systemctl")
            cmd.append("start")
            cmd.append("mariadb")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("           Could not start MariaDB             ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("              MariaDB Started                  ")
                print("###############################################")


        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startMariaDB]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startMariaDB]")
            return 0

        return 1

    @staticmethod
    def installMySQL(password):

        try:

            ############## Install mariadb ######################

            cmd = []

            cmd.append("yum")
            cmd.append("-y")
            cmd.append("install")
            cmd.append("mariadb-server")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("         Could not install MariaDB             ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("              MariaDB Installed                ")
                print("###############################################")


        except OSError as msg:

            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installMySQL]")

            return 0

        except ValueError as msg:

            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installMySQL]")

            return 0


            ############## Start mariadb ######################

        installUtilities.startMariaDB()

        ############## Enable mariadb at system startup ######################

        try:

            cmd = []

            cmd.append("systemctl")
            cmd.append("enable")
            cmd.append("mariadb")

            res = subprocess.call(cmd)

            if res == 1:
                print("###############################################")
                print("      Could not add mariadb to startup         ")
                print("###############################################")
                sys.exit()
            else:
                print("###############################################")
                print("          MariaDB Addded to startup            ")
                print("###############################################")

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " Could not add mariadb to startup [installMySQL]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " Could not add mariadb to startup [installMySQL]")
            return 0

        if installUtilities.secureMysqlInstallation(password) == 1:
            return 1

        return 0

    @staticmethod
    def secureMysqlInstallation(password):

        try:
            expectation = "(enter for none):"
            securemysql = pexpect.spawn("mysql_secure_installation",maxread=20000)
            securemysql.expect(expectation)
            securemysql.sendcontrol('j')



            expectation = "password? [Y/n]"
            securemysql.expect(expectation)
            securemysql.sendline("Y")

            expectation = "New password:"
            securemysql.expect(expectation)
            securemysql.sendline("1qaz@9xvps")

            expectation = "new password:"
            securemysql.expect(expectation)
            securemysql.sendline(password)

            expectation = "anonymous users? [Y/n]"
            securemysql.expect(expectation)
            securemysql.sendline("Y")

            expectation = "root login remotely? [Y/n]"
            securemysql.expect(expectation)
            securemysql.sendline("Y")


            expectation = "test database and access to it? [Y/n]"
            securemysql.expect(expectation)
            securemysql.sendline("Y")



            expectation = "Reload privilege tables now? [Y/n]"
            securemysql.expect(expectation)
            securemysql.sendline("Y")

            securemysql.wait()


            if (securemysql.before.find("Thanks for using MariaDB!") > -1 or securemysql.after.find("Thanks for using MariaDB!")>-1):
                return 1

        except pexpect.EOF as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " Exception EOF [installMySQL]")
            print("###########################Before########################################")
            print(securemysql.before)
            print("###########################After########################################")
            print(securemysql.after)
            print("########################################################################")
        except BaseException as msg:
            print("#############################Before#####################################")
            print(securemysql.before)
            print("############################After######################################")
            print(securemysql.after)
            print("########################################################################")
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installMySQL]")


        return 0


#installUtilities.installAllPHPToLitespeed()