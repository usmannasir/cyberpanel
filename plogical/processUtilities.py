from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import subprocess
import shlex
import os
import socket
import threading as multi
import time
import getpass
import codecs

class ProcessUtilities(multi.Thread):
    debugPath = '/usr/local/CyberCP/debug'
    litespeedProcess = "litespeed"
    ent = 1
    OLS = 0
    centos = 1
    cent8 = 2
    cent9 = 3
    ubuntu = 0
    ubuntu20 = 3
    ubuntu22Check = 0
    alma9check = 0
    ubuntu24Check = 0  # New flag for Ubuntu 24.04 specific handling
    server_address = '/usr/local/lscpd/admin/comm.sock'
    token = "unset"
    portPath = '/usr/local/lscp/conf/bind.conf'

    def __init__(self, function, extraArgs):
        multi.Thread.__init__(self)
        self.function = function
        self.extraArgs = extraArgs

    def run(self):
        try:
            if self.function == 'popen':
                self.customPoen()
        except BaseException as msg:
            logging.writeToFile( str(msg) + ' [ApplicationInstaller.run]')

    @staticmethod
    def fetchCurrentPort():
        command = 'cat %s' % (ProcessUtilities.portPath)
        port = ProcessUtilities.outputExecutioner(command)

        if port.find('*') > -1:
            return port.split(':')[1].rstrip('\n')
        else:
            return '8090'

    @staticmethod
    def getLitespeedProcessNumber():
        finalListOfProcesses = []

        try:
            import psutil
            for proc in psutil.process_iter():
                if proc.name().find(ProcessUtilities.litespeedProcess) > -1:
                    finalListOfProcesses.append(proc.pid)

        except BaseException as msg:
            logging.writeToFile(
                str(msg) + " [getLitespeedProcessNumber]")
            return 0

        if len(finalListOfProcesses) > 0:
         return finalListOfProcesses
        else:
            return 0

    @staticmethod
    def restartLitespeed():
        try:
            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "systemctl restart lsws"
            else:
                command = "/usr/local/lsws/bin/lswsctrl restart"

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 0:
                return 1
            else:
                return 0

        except subprocess.CalledProcessError as msg:
            logging.writeToFile(str(msg) + "[restartLitespeed]")

    @staticmethod
    def stopLitespeed():
        try:
            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "systemctl stop lsws"
            else:
                command = "/usr/local/lsws/bin/lswsctrl stop"

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 0:
                return 1
            else:
                return 0

        except subprocess.CalledProcessError as msg:
            logging.writeToFile(str(msg) + "[stopLitespeed]")

    @staticmethod
    def normalExecutioner(command, shell=False, User=None):
        try:

            f = open(os.devnull, 'w')

            if User == None:
                if shell == False:
                    res = subprocess.call(shlex.split(command), stdout=f, stderr=f)
                else:
                    res = subprocess.call(command, shell=shell, stdout=f, stderr=f)
            else:
                if command.find('export') > -1:
                    pass
                elif command.find('sudo') == -1:
                    command = 'sudo -u %s %s' % (User, command)

                if shell == False:
                    res = subprocess.call(shlex.split(command), stdout=f, stderr=f)
                else:
                    res = subprocess.call(command, shell=shell, stdout=f, stderr=f)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(f"{command} [Exit Code: {res}]")

            if res == 0:
                return 1
            else:
                return 0
        except subprocess.CalledProcessError as msg:
            logging.writeToFile('%s. [ProcessUtilities.normalExecutioner]' % (str(msg)))
            return 0
        except BaseException as msg:
            logging.writeToFile('%s. [ProcessUtilities.normalExecutioner.Base]' % (str(msg)))
            return 0

    @staticmethod
    def killLiteSpeed():
        try:
            command = 'systemctl stop lsws'
            ProcessUtilities.normalExecutioner(command)
        except:
            pass

        pids = ProcessUtilities.getLitespeedProcessNumber()
        if pids !=0:
            for items in pids:
                try:
                    command = 'sudo kill -9 ' + str(items)
                    ProcessUtilities.normalExecutioner(command)
                except:
                    pass

    @staticmethod
    def decideServer():
        if os.path.exists('/usr/local/lsws/bin/openlitespeed'):
            return ProcessUtilities.OLS
        else:
            return ProcessUtilities.ent

    @staticmethod
    def decideDistro():
        distroPath = '/etc/lsb-release'
        distroPathAlma = '/etc/redhat-release'

        # First check if we're on Ubuntu
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                content = f.read()
                if 'Ubuntu' in content:
                    if '24.04' in content:
                        ProcessUtilities.ubuntu22Check = 1
                        ProcessUtilities.ubuntu24Check = 1  # Specific flag for Ubuntu 24.04
                        # Ubuntu 24.04 uses newer package versions, set flag for compatibility
                        ProcessUtilities.alma9check = 1  # Reuse flag to indicate Ubuntu 24.04
                        return ProcessUtilities.ubuntu20
                    elif '22.04' in content:
                        ProcessUtilities.ubuntu22Check = 1
                        return ProcessUtilities.ubuntu20
                    elif '20.04' in content:
                        return ProcessUtilities.ubuntu20
                    return ProcessUtilities.ubuntu

        # Check for RedHat-based distributions
        if os.path.exists(distroPathAlma):
            with open(distroPathAlma, 'r') as f:
                content = f.read()
                if any(x in content for x in ['CentOS Linux release 8', 'AlmaLinux release 8', 'Rocky Linux release 8', 
                                            'Rocky Linux release 9', 'AlmaLinux release 9', 'CloudLinux release 9', 
                                            'CloudLinux release 8', 'AlmaLinux release 10']):
                    if any(x in content for x in ['AlmaLinux release 9', 'Rocky Linux release 9', 'AlmaLinux release 10']):
                        ProcessUtilities.alma9check = 1
                    return ProcessUtilities.cent8

        # Default to Ubuntu if no other distribution is detected
        return ProcessUtilities.ubuntu

    @staticmethod
    def containerCheck():
        try:
            command = 'cat /etc/cgrules.conf'
            output = ProcessUtilities.outputExecutioner(command)
            if output.find('No such') > -1:
                return 0
            else:
                return 1
        except BaseException:
            return 0

    @staticmethod
    def setupUDSConnection():
        count = 0
        while 1:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(ProcessUtilities.server_address)
                return [sock, "None"]
            except BaseException as msg:
                if count == 3:
                    logging.writeToFile("Failed to connect to LSCPD socket, run 'systemctl restart lscpd' on command line to fix this issue.")
                    return [-1, str(msg)]
                else:
                    count = count + 1

                logging.writeToFile("Failed to connect to LSCPD UDS, error message:" + str(msg) + ". Attempt " + str(count) + ", we will attempt again in 2 seconds. [setupUDSConnection:138]")
                time.sleep(2)

    @staticmethod
    def sendCommand(command, user=None, dir=None, retries=3):
        """
        Send command to lscpd with retry mechanism
        
        :param command: Command to execute
        :param user: User to run command as
        :param dir: Directory to run command in
        :param retries: Number of retry attempts if connection fails
        """
        attempt = 0
        last_error = None
        ret = None
        
        while attempt < retries:
            try:
                ret = ProcessUtilities.setupUDSConnection()

                if ret[0] == -1:
                    attempt += 1
                    last_error = ret[1]
                    if attempt < retries:
                        logging.writeToFile(f"[sendCommand] Connection failed, attempt {attempt}/{retries}. Retrying in 2 seconds...")
                        time.sleep(2)
                        # Try to restart lscpd if this is the second attempt
                        if attempt == 2:
                            logging.writeToFile("[sendCommand] Attempting to restart lscpd service...")
                            try:
                                subprocess.run(['systemctl', 'restart', 'lscpd'], capture_output=True, text=True)
                                time.sleep(3)  # Give lscpd time to start
                            except Exception as e:
                                logging.writeToFile(f"[sendCommand] Failed to restart lscpd: {str(e)}")
                        continue
                    else:
                        logging.writeToFile(f"[sendCommand] All connection attempts failed. Last error: {last_error}")
                        return f"-1Connection failed after {retries} attempts: {last_error}"
                
                # If we get here, connection succeeded
                break
                
            except Exception as e:
                attempt += 1
                last_error = str(e)
                if attempt < retries:
                    logging.writeToFile(f"[sendCommand] Unexpected error, attempt {attempt}/{retries}: {last_error}")
                    time.sleep(2)
                    continue
                else:
                    return f"-1Error after {retries} attempts: {last_error}"
        
        try:
            # At this point, we have a successful connection
            if ret is None:
                return "-1Internal error: connection result is None"
            sock = ret[0]
            
            if ProcessUtilities.token == "unset":
                ProcessUtilities.token = os.environ.get('TOKEN')
                del os.environ['TOKEN']

            if user == None:
                if command.find('export') > -1:
                    pass
                elif command.find('sudo') == -1:
                    command = 'sudo %s' % (command)

                if os.path.exists(ProcessUtilities.debugPath):
                    # Log all commands for debugging
                    logging.writeToFile(command)

                if dir == None:
                    sock.sendall((ProcessUtilities.token + command).encode('utf-8'))
                else:
                    command = '%s-d %s %s' % (ProcessUtilities.token, dir, command)
                    sock.sendall(command.encode('utf-8'))
            else:
                if command.startswith('sudo'):
                    command = command.replace('sudo', '', 1)  # Replace 'sudo' with an empty string, only once

                if dir == None:
                    command = '%s-u %s %s' % (ProcessUtilities.token, user, command)
                else:
                    command = '%s-u %s -d %s %s' % (ProcessUtilities.token, user, dir, command)



                if os.path.exists(ProcessUtilities.debugPath):
                    # Log all commands for debugging
                    logging.writeToFile(command)

                sock.sendall(command.encode('utf-8'))

            # Collect all raw bytes first, then decode as a complete unit
            raw_data = b""

            while (1):
                currentData = sock.recv(32)
                if len(currentData) == 0 or currentData == None:
                    break
                raw_data += currentData

            # Decode all data at once to prevent UTF-8 character boundary issues
            try:
                data = raw_data.decode('utf-8', errors='replace')
            except BaseException as msg:
                logging.writeToFile('Some data could not be decoded to str, error message: %s' % str(msg))
                data = ""

            sock.close()
            
            # Log exit code if debug is enabled
            if os.path.exists(ProcessUtilities.debugPath):
                if len(data) == 0:
                    logging.writeToFile(f"    └─ Empty response from lscpd")
                else:
                    try:
                        exit_char = data[-1]
                        # Log raw data for debugging
                        logging.writeToFile(f"    └─ Response length: {len(data)}, last char: {repr(exit_char)}")
                        
                        if isinstance(exit_char, str):
                            exit_code = ord(exit_char)
                        else:
                            exit_code = "unknown"
                        # Log the actual command that was executed (without token)
                        clean_command = command.replace(ProcessUtilities.token, '').replace('-u %s ' % user if user else '', '').replace('-d %s ' % dir if dir else '', '').strip()
                        logging.writeToFile(f"    └─ {clean_command} [Exit Code: {exit_code}]")
                    except Exception as e:
                        logging.writeToFile(f"    └─ Failed to log exit code: {str(e)}")
            
            #logging.writeToFile('Final data: %s.' % (str(data)))

            return data
        except BaseException as msg:
            logging.writeToFile(str(msg) + " [hey:sendCommand]")
            return "0" + str(msg)

    @staticmethod
    def executioner(command, user=None, shell=False):
        try:
            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(f"[executioner] Called with command: {command}, user: {user}, shell: {shell}")
            
            if getpass.getuser() == 'root':
                if os.path.exists(ProcessUtilities.debugPath):
                    logging.writeToFile(f"[executioner] Running as root, using normalExecutioner")
                ProcessUtilities.normalExecutioner(command, shell, user)
                return 1

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(f"[executioner] Not root, using sendCommand via lscpd")
            
            ret = ProcessUtilities.sendCommand(command, user)

            # Check if we got any response
            if not ret or len(ret) == 0:
                logging.writeToFile("Empty response from lscpd for command: %s" % command)
                return 0
            
            # Extract exit code from last character
            try:
                exitCode = ret[-1]
                # Convert the last character to its ASCII value
                if isinstance(exitCode, str):
                    exitCode = ord(exitCode)
                elif isinstance(exitCode, bytes):
                    exitCode = exitCode[0] if len(exitCode) > 0 else 1
                else:
                    # Try the original hex encoding method as fallback
                    exitCode = int(codecs.encode(exitCode.encode(), 'hex'))
                
                if os.path.exists(ProcessUtilities.debugPath):
                    logging.writeToFile(f'Exit code from lscpd: {exitCode} for command: {command}')
                
                if exitCode == 0:
                    return 1
                else:
                    return 0
            except Exception as e:
                logging.writeToFile(f"Failed to parse exit code: {str(e)} for command: {command}")
                return 0

        except BaseException as msg:
            logging.writeToFile(str(msg) + " [executioner]")
            return 0

    @staticmethod
    def outputExecutioner(command, user=None, shell = None, dir = None, retRequired = None):
        try:
            if getpass.getuser() == 'root':
                if os.path.exists(ProcessUtilities.debugPath):
                    logging.writeToFile(command)

                if user!=None:
                    if not command.startswith('sudo'):
                        command = f'sudo -u {user} {command}'
                # Ensure UTF-8 environment for proper character handling
                env = os.environ.copy()
                env['LC_ALL'] = 'C.UTF-8'
                env['LANG'] = 'C.UTF-8'
                env['PYTHONIOENCODING'] = 'utf-8'
                
                if shell == None or shell == True:
                    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, encoding='utf-8', errors='replace')
                else:
                    p = subprocess.Popen(shlex.split(command),  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, encoding='utf-8', errors='replace')

                if retRequired:
                    output, _ = p.communicate()
                    exit_code = p.returncode
                    if os.path.exists(ProcessUtilities.debugPath):
                        logging.writeToFile(f"    └─ [Exit Code: {exit_code}]")
                    if exit_code == 0:
                        return 1, output
                    else:
                        return 0, output
                else:
                    output = p.communicate()[0]
                    exit_code = p.returncode
                    if os.path.exists(ProcessUtilities.debugPath):
                        logging.writeToFile(f"    └─ [Exit Code: {exit_code}]")
                    return output

            if type(command) == list:
                command = " ".join(command)

            if retRequired:
                ret = ProcessUtilities.sendCommand(command, user)

                # Check if we got any response
                if not ret or len(ret) == 0:
                    logging.writeToFile("Empty response from lscpd in outputExecutioner for command: %s" % command)
                    return 0, ""
                
                # Extract exit code from last character
                try:
                    exitCode = ret[-1]
                    
                    if os.path.exists(ProcessUtilities.debugPath):
                        logging.writeToFile(f'Raw exit code character in outputExecutioner: {repr(exitCode)}')
                    
                    # Convert the last character to its ASCII value
                    if isinstance(exitCode, str):
                        exitCode = ord(exitCode)
                    elif isinstance(exitCode, bytes):
                        exitCode = exitCode[0] if len(exitCode) > 0 else 1
                    else:
                        # Try the original hex encoding method as fallback
                        exitCode = int(codecs.encode(exitCode.encode(), 'hex'))
                    
                    if os.path.exists(ProcessUtilities.debugPath):
                        logging.writeToFile(f'Parsed exit code in outputExecutioner: {exitCode} for command: {command}')
                    
                    if exitCode == 0:
                        return 1, ret[:-1]
                    else:
                        return 0, ret[:-1]
                except Exception as e:
                    logging.writeToFile(f"Failed to parse exit code in outputExecutioner: {str(e)} for command: {command}")
                    return 0, ret[:-1] if len(ret) > 1 else ""
            else:
                return ProcessUtilities.sendCommand(command, user, dir)[:-1]
        except BaseException as msg:
            logging.writeToFile(str(msg) + "[outputExecutioner:188]")

    def customPoen(self):
        try:

            if type(self.extraArgs['command']) == str or type(self.extraArgs['command']) == bytes:
                command = self.extraArgs['command']
            else:
                command = " ".join(self.extraArgs['command'])

            if getpass.getuser() == 'root':
                subprocess.call(command, shell=True)
            else:
                ProcessUtilities.sendCommand(command, self.extraArgs['user'])

            return 1
        except BaseException as msg:
            logging.writeToFile(str(msg) + " [customPoen]")

    @staticmethod
    def popenExecutioner(command, user=None):
        try:
            extraArgs = {}
            extraArgs['command'] = command
            extraArgs['user'] = user
            pu = ProcessUtilities("popen", extraArgs)
            pu.start()
        except BaseException as msg:
            logging.writeToFile(str(msg) + " [popenExecutioner]")

    @staticmethod
    def BuildCommand(path, functionName, parameters):

        execPath = "/usr/local/CyberCP/bin/python %s %s " % (path, functionName)
        for key, value in parameters.items():
            execPath = execPath + ' --%s %s' % (key, value)

        return execPath


    @staticmethod
    def fetch_latest_lts_version_for_node():
        import requests
        url = "https://api.github.com/repos/nodejs/node/releases"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                releases = response.json()
                for release in releases:
                    if release.get('prerelease') == False and 'LTS' in release.get('name'):
                        lts_version = release.get('tag_name')
                        return lts_version
            else:
                print("Failed to fetch releases. Status code:", response.status_code)
        except Exception as e:
            print("An error occurred:", e)
        return None

    @staticmethod
    def getNumberOfCores():
        """Get the number of CPU cores available on the system"""
        try:
            import multiprocessing
            return multiprocessing.cpu_count()
        except:
            try:
                # Fallback method using /proc/cpuinfo
                with open('/proc/cpuinfo', 'r') as f:
                    return len([line for line in f if line.startswith('processor')])
            except:
                # Default to 2 if we can't determine
                return 2

    @staticmethod
    def fetch_latest_prestashop_version():
        import requests
        url = "https://api.github.com/repos/PrestaShop/PrestaShop/releases"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                releases = response.json()
                return releases[0].get('tag_name')
            else:
                logging.writeToFile(f"Failed to fetch releases. Status code: {response.status_code}"  )
                print("[fetch_latest_prestashop_version] Failed to fetch releases. Status code:", response.status_code)
        except Exception as e:
            print("An error occurred:", e)
            logging.writeToFile(f"[fetch_latest_prestashop_version] An error occurred: {str(e)}")
        return None
    