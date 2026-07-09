#!/usr/local/CyberCP/bin/python
import json
import os
import sys
import time
from random import randint
import socket
import shutil
import docker

sys.path.append('/usr/local/CyberCP')

try:
    import django
except:
    pass

try:
    from plogical import randomPassword
    from plogical.acl import ACLManager
    from dockerManager.dockerInstall import DockerInstall
except:
    pass

from plogical.processUtilities import ProcessUtilities
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import argparse
import threading as multi

class DockerDeploymentError(Exception):
    def __init__(self, message, error_code=None, recovery_possible=True):
        self.message = message
        self.error_code = error_code
        self.recovery_possible = recovery_possible
        super().__init__(self.message)

class Docker_Sites(multi.Thread):
    Wordpress = 1
    Joomla = 2

    # Error codes
    ERROR_DOCKER_NOT_INSTALLED = 'DOCKER_NOT_INSTALLED'
    ERROR_PORT_IN_USE = 'PORT_IN_USE'
    ERROR_CONTAINER_FAILED = 'CONTAINER_FAILED'
    ERROR_NETWORK_FAILED = 'NETWORK_FAILED'
    ERROR_VOLUME_FAILED = 'VOLUME_FAILED'
    ERROR_DB_FAILED = 'DB_FAILED'

    def __init__(self, function_run, data):
        multi.Thread.__init__(self)
        self.function_run = function_run
        self.data = data
        try:
            self.JobID = self.data['JobID']  ##JOBID will be file path where status is being written
        except:
            pass
        try:
            ### set docker name for listing/deleting etc
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                self.DockerAppName = f"{self.data['name'].replace(' ', '')}-{self.data['name'].replace(' ', '-')}"
            else:
                self.DockerAppName = f"{self.data['name'].replace(' ', '')}_{self.data['name'].replace(' ', '-')}"
        except:
            pass

        command = 'cat /etc/csf/csf.conf'
        result = ProcessUtilities.outputExecutioner(command)

        if result.find('SECTION:Initial Settings') > -1:

            from plogical.csf import CSF
            from plogical.virtualHostUtilities import virtualHostUtilities
            currentSettings = CSF.fetchCSFSettings()

            tcpIN = currentSettings['tcpIN']

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(f'TCPIN docker: {tcpIN}')



            if tcpIN.find('8088') == -1:

                ports = f'{tcpIN},8088'

                portsPath = '/home/cyberpanel/' + str(randint(1000, 9999))

                if os.path.exists(portsPath):
                    os.remove(portsPath)

                writeToFile = open(portsPath, 'w')
                writeToFile.write(ports)
                writeToFile.close()

                execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
                execPath = execPath + f" modifyPorts --protocol TCP_IN --ports " + portsPath
                ProcessUtilities.executioner(execPath)

            tcpOUT = currentSettings['tcpOUT']
            if tcpOUT.find('8088') == -1:

                ports = f'{tcpOUT},8088'

                portsPath = '/home/cyberpanel/' + str(randint(1000, 9999))

                if os.path.exists(portsPath):
                    os.remove(portsPath)

                writeToFile = open(portsPath, 'w')
                writeToFile.write(ports)
                writeToFile.close()

                execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
                execPath = execPath + f" modifyPorts --protocol TCP_OUT --ports " + portsPath
                ProcessUtilities.executioner(execPath)


    def run(self):
        try:
            if self.function_run == 'DeployWPContainer':
                self.DeployWPContainer()
            elif self.function_run == 'SubmitDockersiteCreation':
                self.SubmitDockersiteCreation()
            elif self.function_run == 'DeployN8NContainer':
                self.DeployN8NContainer()


        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [Docker_Sites.run]')

    def InstallDocker(self):

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:

            command = 'dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo'

            ReturnCode = ProcessUtilities.executioner(command)

            if ReturnCode:
                pass
            else:
                return 0, ReturnCode

            command = 'dnf install docker-ce docker-ce-cli containerd.io docker-compose-plugin -y'
            ReturnCode = ProcessUtilities.executioner(command)

            if ReturnCode:
                pass
            else:
                return 0, ReturnCode

            command = 'systemctl enable docker'
            ReturnCode = ProcessUtilities.executioner(command)

            if ReturnCode:
                pass
            else:
                return 0, ReturnCode

            command = 'systemctl start docker'
            ReturnCode = ProcessUtilities.executioner(command)

            if ReturnCode:
                pass
            else:
                return 0, ReturnCode

            command = 'curl -L "https://github.com/docker/compose/releases/download/v2.23.2/docker-compose-linux-x86_64" -o /usr/bin/docker-compose'
            ReturnCode = ProcessUtilities.executioner(command, 'root', True)

            if ReturnCode:
                pass
            else:
                return 0, ReturnCode

            command = 'chmod +x /usr/bin/docker-compose'
            ReturnCode = ProcessUtilities.executioner(command, 'root', True)

            if ReturnCode:
                return 1, None
            else:
                return 0, ReturnCode

        else:
            # Add Docker's official GPG key
            command = 'curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg'
            ReturnCode = ProcessUtilities.executioner(command, 'root', True)
            if not ReturnCode:
                return 0, ReturnCode

            # Add Docker repository
            command = 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null'
            ReturnCode = ProcessUtilities.executioner(command, 'root', True)
            if not ReturnCode:
                return 0, ReturnCode

            # Update package index
            command = 'apt-get update'
            ReturnCode = ProcessUtilities.executioner(command)
            if not ReturnCode:
                return 0, ReturnCode

            # Install Docker packages
            command = 'apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin'
            ReturnCode = ProcessUtilities.executioner(command)
            if not ReturnCode:
                return 0, ReturnCode

            # Enable and start Docker service
            command = 'systemctl enable docker'
            ReturnCode = ProcessUtilities.executioner(command)
            if not ReturnCode:
                return 0, ReturnCode

            command = 'systemctl start docker'
            ReturnCode = ProcessUtilities.executioner(command)
            if not ReturnCode:
                return 0, ReturnCode

            # Install Docker Compose
            command = 'curl -L "https://github.com/docker/compose/releases/download/v2.23.2/docker-compose-linux-$(uname -m)" -o /usr/local/bin/docker-compose'
            ReturnCode = ProcessUtilities.executioner(command, 'root', True)
            if not ReturnCode:
                return 0, ReturnCode

            command = 'chmod +x /usr/local/bin/docker-compose'
            ReturnCode = ProcessUtilities.executioner(command, 'root', True)
            if not ReturnCode:
                return 0, ReturnCode

            return 1, None

    @staticmethod
    def SetupProxy(port):
        import xml.etree.ElementTree as ET

        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            ConfPath = '/usr/local/lsws/conf/httpd_config.conf'
            data = open(ConfPath, 'r').read()
            StringCheck = f"127.0.0.1:{port}"
            if data.find(StringCheck) == -1:
                ProxyContent = f"""
extprocessor docker{port} {{
  type                    proxy
  address                 127.0.0.1:{port}
  maxConns                100
  pcKeepAliveTimeout      3600
  initTimeout             300
  retryTimeout            0
  respBuffer              0
}}    
"""

                WriteToFile = open(ConfPath, 'a')
                WriteToFile.write(ProxyContent)
                WriteToFile.close()

        else:
            ConfPath = '/usr/local/lsws/conf/httpd_config.xml'
            data = open(ConfPath, 'r').read()

            # Parse the XML
            root = ET.fromstring(data)

            # Find the <extProcessorList> node
            ext_processor_list = root.find('extProcessorList')

            # Create the new <extProcessor> node
            new_ext_processor = ET.Element('extProcessor')

            # Add child elements to the new <extProcessor>
            ET.SubElement(new_ext_processor, 'type').text = 'proxy'
            ET.SubElement(new_ext_processor, 'name').text = f'docker{port}'
            ET.SubElement(new_ext_processor, 'address').text = f'127.0.0.1:{port}'
            ET.SubElement(new_ext_processor, 'maxConns').text = '100'
            ET.SubElement(new_ext_processor, 'pcKeepAliveTimeout').text = '3600'
            ET.SubElement(new_ext_processor, 'initTimeout').text = '300'
            ET.SubElement(new_ext_processor, 'retryTimeout').text = '0'
            ET.SubElement(new_ext_processor, 'respBuffer').text = '0'

            # Append the new <extProcessor> to the <extProcessorList>
            ext_processor_list.append(new_ext_processor)

            # Write the updated XML content to a new file or print it out
            tree = ET.ElementTree(root)
            tree.write(ConfPath, encoding='UTF-8', xml_declaration=True)

            # Optionally, print the updated XML
            ET.dump(root)


    @staticmethod
    def SetupN8NVhost(domain, port):
        """Setup n8n vhost with proper proxy configuration for OpenLiteSpeed"""
        try:
            vhost_path = f'/usr/local/lsws/conf/vhosts/{domain}/vhost.conf'

            if not os.path.exists(vhost_path):
                logging.writeToFile(f"Error: Vhost file not found at {vhost_path}")
                return False

            # Read existing vhost configuration
            with open(vhost_path, 'r') as f:
                content = f.read()

            # Check if context already exists
            if 'context / {' in content:
                logging.writeToFile("Context already exists, skipping...")
                return True

            # Add proxy context with proper headers for n8n
            # NOTE: Do NOT include "RequestHeader set Origin" - OpenLiteSpeed cannot override
            # browser Origin headers, which is why NODE_ENV=development is required
            proxy_context = f'''

# N8N Proxy Configuration
context / {{
  type                    proxy
  handler                 docker{port}
  addDefaultCharset       off
  websocket               1

  extraHeaders            <<<END_extraHeaders
  RequestHeader set X-Forwarded-For $ip
  RequestHeader set X-Forwarded-Proto https
  RequestHeader set X-Forwarded-Host "{domain}"
  RequestHeader set Host "{domain}"
  END_extraHeaders
}}
'''
            
            # Append at the end of file
            with open(vhost_path, 'a') as f:
                f.write(proxy_context)
            
            logging.writeToFile(f"Successfully updated vhost for {domain}")
            return True
            
        except Exception as e:
            logging.writeToFile(f'Error setting up n8n vhost: {str(e)}')
            return False
    
    @staticmethod
    def SetupHTAccess(port, htaccess):
        ### Update htaccess

        StringCheck = f'docker{port}'

        try:
            Content = open(htaccess, 'r').read()
        except:
            Content = ''

        print(f'value of content {Content}')

        if Content.find(StringCheck) == -1:
            HTAccessContent = f'''
RewriteEngine On
REWRITERULE ^(.*)$ HTTP://docker{port}/$1 [P]
'''
            WriteToFile = open(htaccess, 'a')
            WriteToFile.write(HTAccessContent)
            WriteToFile.close()

    # Takes
    # ComposePath, MySQLPath, MySQLRootPass, MySQLDBName, MySQLDBNUser, MySQLPassword, CPUsMySQL, MemoryMySQL,
    # port, SitePath, CPUsSite, MemorySite, ComposePath, SiteName
    # finalURL, blogTitle, adminUser, adminPassword, adminEmail, htaccessPath, externalApp

    def DeployWPContainer(self):

        try:
            logging.statusWriter(self.JobID, 'Checking if Docker is installed..,0')

            command = 'docker --help'
            result = ProcessUtilities.outputExecutioner(command)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(f'return code of docker install {result}')

            if result.find("not found") > -1:
                if os.path.exists(ProcessUtilities.debugPath):
                    logging.writeToFile(f'About to run docker install function...')

                execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/dockerManager/dockerInstall.py"
                ProcessUtilities.executioner(execPath)

            logging.statusWriter(self.JobID, 'Docker is ready to use..,10')

            self.data['ServiceName'] = self.data["SiteName"].replace(' ', '-')

            WPSite = f'''
version: '3.8'

services:
  '{self.data['ServiceName']}':
    user: root
    image: cyberpanel/openlitespeed:latest
    ports:
      - "{self.data['port']}:8088"
#      - "443:443"
    environment:
      DB_NAME: "{self.data['MySQLDBName']}"
      DB_USER: "{self.data['MySQLDBNUser']}"
      DB_PASSWORD: "{self.data['MySQLPassword']}"
      WP_ADMIN_EMAIL: "{self.data['adminEmail']}"
      WP_ADMIN_USER: "{self.data['adminUser']}"
      WP_ADMIN_PASSWORD: "{self.data['adminPassword']}"
      WP_URL: {self.data['finalURL']}
      DB_Host: '{self.data['ServiceName']}-db:3306'
      SITE_NAME: '{self.data['SiteName']}'
    volumes:
#      - "/home/docker/{self.data['finalURL']}:/usr/local/lsws/Example/html"
      - "/home/docker/{self.data['finalURL']}/data:/usr/local/lsws/Example/html"
    depends_on:
      - '{self.data['ServiceName']}-db'
    deploy:
      resources:
        limits:
          cpus: '{self.data['CPUsSite']}'  # Use 50% of one CPU core
          memory: {self.data['MemorySite']}M  # Limit memory to 512 megabytes
  '{self.data['ServiceName']}-db':
    image: mariadb
    restart: always
    environment:
#      ALLOW_EMPTY_PASSWORD=no
      MYSQL_DATABASE: '{self.data['MySQLDBName']}'
      MYSQL_USER: '{self.data['MySQLDBNUser']}'
      MYSQL_PASSWORD: '{self.data['MySQLPassword']}'
      MYSQL_ROOT_PASSWORD: '{self.data['MySQLPassword']}'
    volumes:
      - "/home/docker/{self.data['finalURL']}/db:/var/lib/mysql"
    deploy:
      resources:
        limits:
          cpus: '{self.data['CPUsMySQL']}'  # Use 50% of one CPU core
          memory: {self.data['MemoryMySQL']}M  # Limit memory to 512 megabytes            
'''

            ### WriteConfig to compose-file

            command = f"mkdir -p /home/docker/{self.data['finalURL']}"
            result, message = ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            if result == 0:
                logging.statusWriter(self.JobID, f'Error {str(message)} . [404]')
                return 0

            TempCompose = f'/home/cyberpanel/{self.data["finalURL"]}-docker-compose.yml'

            WriteToFile = open(TempCompose, 'w')
            WriteToFile.write(WPSite)
            WriteToFile.close()

            command = f"mv {TempCompose} {self.data['ComposePath']}"
            result, message = ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            if result == 0:
                logging.statusWriter(self.JobID, f'Error {str(message)} . [404]')
                return 0

            command = f"chmod 600 {self.data['ComposePath']} && chown root:root {self.data['ComposePath']}"
            ProcessUtilities.executioner(command, 'root', True)

            ####

            if ProcessUtilities.decideDistro() == ProcessUtilities.cent8 or ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                dockerCommand = 'docker compose'
            else:
                dockerCommand = 'docker-compose'

            command = f"{dockerCommand} -f {self.data['ComposePath']} -p '{self.data['SiteName']}' up -d"
            result, message = ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(message)

            if result == 0:
                logging.statusWriter(self.JobID, f'Error {str(message)} . [404]')
                return 0

            logging.statusWriter(self.JobID, 'Bringing containers online..,50')

            time.sleep(25)

            ### checking if everything ran properly

            passdata = {}
            passdata["JobID"] = None
            passdata['name'] = self.data['ServiceName']
            da = Docker_Sites(None, passdata)
            retdata, containers = da.ListContainers()

            containers = json.loads(containers)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(str(containers))

            ### it means less then two containers which means something went wrong
            if len(containers) < 2:
                logging.writeToFile(f'Unkonwn error, containers not running. [DeployWPContainer]')
                logging.statusWriter(self.JobID, f'Unkonwn error, containers not running. [DeployWPContainer]')
                return 0

            ### Set up Proxy

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py"
            execPath = execPath + f" SetupProxy --port {self.data['port']}"
            ProcessUtilities.executioner(execPath)

            ### Set up ht access

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py"
            execPath = execPath + f" SetupHTAccess --port {self.data['port']} --htaccess {self.data['htaccessPath']}"
            ProcessUtilities.executioner(execPath, self.data['externalApp'])

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                group = 'nobody'
            else:
                group = 'nogroup'

            command = f"chown -R nobody:{group} /home/docker/{self.data['finalURL']}/data"
            ProcessUtilities.executioner(command)

            ### just restart ls for htaccess

            from plogical.installUtilities import installUtilities
            installUtilities.reStartLiteSpeedSocket()

            logging.statusWriter(self.JobID, 'Completed. [200]')

            # command = f"docker-compose -f {self.data['ComposePath']} ps -q wordpress"
            # stdout = ProcessUtilities.outputExecutioner(command)
            #
            # self.ContainerID = stdout.rstrip('\n')

            # command = f'docker-compose -f {self.data["ComposePath"]} exec {self.ContainerID} curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar'
            # result = ProcessUtilities.outputExecutioner(command)
            #
            # if os.path.exists(ProcessUtilities.debugPath):
            #     logging.writeToFile(result)
            #
            # command = f"docker-compose -f {self.data['ComposePath']} exec {self.ContainerID} chmod + wp-cli.phar"
            # result = ProcessUtilities.outputExecutioner(command)
            #
            # if os.path.exists(ProcessUtilities.debugPath):
            #     logging.writeToFile(result)
            #
            # command = f"docker-compose -f {self.data['ComposePath']} exec {self.ContainerID} mv wp-cli.phar /bin/wp"
            # result = ProcessUtilities.outputExecutioner(command)
            #
            # if os.path.exists(ProcessUtilities.debugPath):
            #     logging.writeToFile(result)

            # command = f'docker-compose -f {self.data["ComposePath"]} exec {self.ContainerID} wp core install --url="http://{self.data["finalURL"]}" --title="{self.data["blogTitle"]}" --admin_user="{self.data["adminUser"]}" --admin_password="{self.data["adminPassword"]}" --admin_email="{self.data["adminEmail"]}" --path=. --allow-root'
            # result = ProcessUtilities.outputExecutioner(command)
            #
            # if os.path.exists(ProcessUtilities.debugPath):
            #     logging.writeToFile(result)

        except BaseException as msg:
            logging.writeToFile(f'{str(msg)}. [DeployWPContainer]')
            logging.statusWriter(self.JobID, f'Error {str(msg)} . [404]')
            print(str(msg))
            pass

    def SubmitDockersiteCreation(self):
        try:

            from websiteFunctions.models import DockerSites, Websites
            from websiteFunctions.website import WebsiteManager

            tempStatusPath = self.data['JobID']
            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Creating Website...,10')
            statusFile.close()

            Domain = self.data['Domain']
            WPemal = self.data['WPemal']
            Owner = self.data['Owner']
            userID = self.data['userID']
            MysqlCPU = self.data['MysqlCPU']
            MYsqlRam = self.data['MYsqlRam']
            SiteCPU = self.data['SiteCPU']
            SiteRam = self.data['SiteRam']
            sitename = self.data['sitename']
            WPusername = self.data['WPusername']
            WPpasswd = self.data['WPpasswd']
            externalApp = self.data['externalApp']

            currentTemp = tempStatusPath

            DataToPass = {}
            DataToPass['tempStatusPath'] = tempStatusPath
            DataToPass['domainName'] = Domain
            DataToPass['adminEmail'] = WPemal
            DataToPass['phpSelection'] = "PHP 8.1"
            DataToPass['websiteOwner'] = Owner
            DataToPass['package'] = 'Default'
            DataToPass['ssl'] = 1
            DataToPass['dkimCheck'] = 0
            DataToPass['openBasedir'] = 0
            DataToPass['mailDomain'] = 0
            DataToPass['apacheBackend'] = 0
            UserID = userID

            if Websites.objects.filter(domain=DataToPass['domainName']).count() == 0:
                try:
                    website = Websites.objects.get(domain=DataToPass['domainName'])

                    if website.phpSelection == 'PHP 7.3':
                        website.phpSelection = 'PHP 8.0'
                        website.save()

                    if ACLManager.checkOwnership(website.domain, self.data['adminID'],
                                                 self.data['currentACL']) == 0:
                        statusFile = open(tempStatusPath, 'w')
                        statusFile.writelines('You dont own this site.[404]')
                        statusFile.close()
                except:

                    ab = WebsiteManager()
                    coreResult = ab.submitWebsiteCreation(UserID, DataToPass)
                    coreResult1 = json.loads((coreResult).content)
                    logging.writeToFile("Creating website result....%s" % coreResult1)
                    reutrntempath = coreResult1['tempStatusPath']
                    while (1):
                        lastLine = open(reutrntempath, 'r').read()
                        logging.writeToFile("Error web creating lastline ....... %s" % lastLine)
                        if lastLine.find('[200]') > -1:
                            break
                        elif lastLine.find('[404]') > -1:
                            statusFile = open(currentTemp, 'w')
                            statusFile.writelines('Failed to Create Website: error: %s. [404]' % lastLine)
                            statusFile.close()
                            return 0
                        else:
                            statusFile = open(currentTemp, 'w')
                            statusFile.writelines('Creating Website....,20')
                            statusFile.close()
                            time.sleep(2)

                    statusFile = open(tempStatusPath, 'w')
                    statusFile.writelines('Creating DockerSite....,30')
                    statusFile.close()

            webobj = Websites.objects.get(domain=Domain)

            if webobj.dockersites_set.all().count() > 0:
                logging.statusWriter(self.JobID, f'Docker container already exists on this domain. [404]')
                return 0

            dbname = randomPassword.generate_pass()
            dbpasswd = randomPassword.generate_pass()
            dbusername = randomPassword.generate_pass()
            MySQLRootPass = randomPassword.generate_pass()

            if DockerSites.objects.count() == 0:
                port = '11000'
            else:
                port = str(int(DockerSites.objects.last().port) + 1)

            f_data = {
                "JobID": tempStatusPath,
                "ComposePath": f"/home/docker/{Domain}/docker-compose.yml",
                "MySQLPath": f'/home/{Domain}/public_html/sqldocker',
                "MySQLRootPass": MySQLRootPass,
                "MySQLDBName": dbname,
                "MySQLDBNUser": dbusername,
                "MySQLPassword": dbpasswd,
                "CPUsMySQL": MysqlCPU,
                "MemoryMySQL": MYsqlRam,
                "port": port,
                "SitePath": f'/home/{Domain}/public_html/wpdocker',
                "CPUsSite": SiteCPU,
                "MemorySite": SiteRam,
                "SiteName": sitename,
                "finalURL": Domain,
                "blogTitle": sitename,
                "adminUser": WPusername,
                "adminPassword": WPpasswd,
                "adminEmail": WPemal,
                "htaccessPath": f'/home/{Domain}/public_html/.htaccess',
                "externalApp": webobj.externalApp,
                "docRoot": f"/home/{Domain}"
            }

            dockersiteobj = DockerSites(
                admin=webobj, ComposePath=f"/home/{Domain}/docker-compose.yml",
                SitePath=f'/home/{Domain}/public_html/wpdocker',
                MySQLPath=f'/home/{Domain}/public_html/sqldocker', SiteType=Docker_Sites.Wordpress, MySQLDBName=dbname,
                MySQLDBNUser=dbusername, CPUsMySQL=MysqlCPU, MemoryMySQL=MYsqlRam, port=port, CPUsSite=SiteCPU,
                MemorySite=SiteRam,
                SiteName=sitename, finalURL=Domain, blogTitle=sitename, adminUser=WPusername, adminEmail=WPemal
            )
            dockersiteobj.save()

            if self.data['App'] == 'WordPress':
                background = Docker_Sites('DeployWPContainer', f_data)
                background.start()
            elif self.data['App'] == 'n8n':
                background = Docker_Sites('DeployN8NContainer', f_data)
                background.start()

        except BaseException as msg:
            logging.writeToFile("Error Submit Docker site Creation ....... %s" % str(msg))
            return 0

    def DeleteDockerApp(self):
        try:

            command = f'docker-compose -f /home/docker/{self.data["domain"]}/docker-compose.yml down'
            ProcessUtilities.executioner(command)

            command = f'rm -rf /home/docker/{self.data["domain"]}'
            ProcessUtilities.executioner(command)

            command = f'rm -f /home/{self.data["domain"]}/public_html/.htaccess'
            ProcessUtilities.executioner(command)


            ### forcefully delete containers

            # Create a Docker client
            client = docker.from_env()

            FilerValue = self.DockerAppName

            # Define the label to filter containers
            label_filter = {'name': FilerValue}

            # List containers matching the label filter
            containers = client.containers.list(filters=label_filter)

            logging.writeToFile(f'List of containers {str(containers)}')


            for container in containers:
                command = f'docker stop {container.short_id}'
                ProcessUtilities.executioner(command)

                command = f'docker rm {container.short_id}'
                ProcessUtilities.executioner(command)


            command = f"rm -rf /home/{self.data['domain']}/public_html/.htaccess'"
            ProcessUtilities.executioner(command)

            from plogical.installUtilities import installUtilities
            installUtilities.reStartLiteSpeed()

        except BaseException as msg:
            logging.writeToFile("Error Delete Docker APP ....... %s" % str(msg))
            return 0

    ## This function need site name which was passed while creating the app
    def ListContainers(self):
        try:
            # Create a Docker client
            client = docker.from_env()

            # Debug logging
            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(f'DockerAppName: {self.DockerAppName}')

            # List all containers without filtering first
            all_containers = client.containers.list(all=True)
            
            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(f'Total containers found: {len(all_containers)}')
                for container in all_containers:
                    logging.writeToFile(f'Container name: {container.name}')

            # Now filter containers - handle both CentOS and Ubuntu naming
            containers = []
            
            # Get both possible name formats
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                search_name = self.DockerAppName  # Already in hyphen format for CentOS
            else:
                # For Ubuntu, convert underscore to hyphen as containers use hyphens
                search_name = self.DockerAppName.replace('_', '-')
            
            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(f'Searching for containers with name containing: {search_name}')

            for container in all_containers:
                if os.path.exists(ProcessUtilities.debugPath):
                    logging.writeToFile(f'Checking container: {container.name} against filter: {search_name}')
                if search_name.lower() in container.name.lower():
                    containers.append(container)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(f'Filtered containers count: {len(containers)}')

            json_data = "["
            checker = 0

            for container in containers:
                try:
                    dic = {
                        'id': container.short_id,
                        'name': container.name,
                        'status': container.status,
                        'state': container.attrs.get('State', {}),
                        'health': container.attrs.get('State', {}).get('Health', {}).get('Status', 'unknown'),
                        'volumes': container.attrs['HostConfig']['Binds'] if 'HostConfig' in container.attrs else [],
                        'logs_50': container.logs(tail=50).decode('utf-8'),
                        'ports': container.attrs['HostConfig']['PortBindings'] if 'HostConfig' in container.attrs else {}
                    }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)
                except Exception as e:
                    logging.writeToFile(f"Error processing container {container.name}: {str(e)}")
                    continue

            json_data = json_data + ']'

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(f'Final JSON data: {json_data}')

            return 1, json_data

        except BaseException as msg:
            logging.writeToFile("List Container ....... %s" % str(msg))
            return 0, str(msg)

    ### pass container id and number of lines to fetch from logs
    def ContainerLogs(self):
        try:
            # Create a Docker client
            client = docker.from_env()

            # Get the container by ID
            container = client.containers.get(self.data['containerID'])

            # Fetch last 'tail' logs for the container
            logs = container.logs(tail=self.data['numberOfLines']).decode('utf-8')

            return 1, logs
        except BaseException as msg:
            logging.writeToFile("List Container ....... %s" % str(msg))
            return 0, str(msg)

        ### pass container id and number of lines to fetch from logs

    def ContainerInfo(self):
        try:
            # Create a Docker client
            client = docker.from_env()

            # Get the container by ID
            container = client.containers.get(self.data['containerID'])

            # Fetch container stats
            stats = container.stats(stream=False)

            dic = {
                'id': container.short_id,
                'name': container.name,
                'status': container.status,
                'volumes': container.attrs['HostConfig']['Binds'] if 'HostConfig' in container.attrs else [],
                'logs_50': container.logs(tail=50).decode('utf-8'),
                'ports': container.attrs['HostConfig']['PortBindings'] if 'HostConfig' in container.attrs else {},
                'memory': stats['memory_stats']['usage'],
                'cpu' : stats['cpu_stats']['cpu_usage']['total_usage']
            }

            return 1, dic
        except BaseException as msg:
            logging.writeToFile("List Container ....... %s" % str(msg))
            return 0, str(msg)

    def RebuildApp(self):
        self.DeleteDockerApp()
        self.SubmitDockersiteCreation()

    def RestartContainer(self):
        try:
            # Create a Docker client
            client = docker.from_env()

            # Get the container by ID
            container = client.containers.get(self.data['containerID'])

            container.restart()

            return 1, None
        except BaseException as msg:
            logging.writeToFile("List Container ....... %s" % str(msg))
            return 0, str(msg)

    def StopContainer(self):
        try:
            # Create a Docker client
            client = docker.from_env()

            # Get the container by ID
            container = client.containers.get(self.data['containerID'])

            container.stop()

            return 1, None
        except BaseException as msg:
            logging.writeToFile("List Container ....... %s" % str(msg))
            return 0, str(msg)

    ##### N8N Container

    def check_container_health(self, service_name, max_retries=3, delay=80):
        """
        Check if a container is running, accepting healthy, unhealthy, and starting states
        Total wait time will be 4 minutes (3 retries * 80 seconds)

        Uses fuzzy matching to find containers since Docker Compose naming varies by version:
        - Docker Compose v1: project_service_1 (underscores)
        - Docker Compose v2: project-service-1 (hyphens)
        """
        try:
            logging.writeToFile(f'Checking container health for service: {service_name}')

            for attempt in range(max_retries):
                client = docker.from_env()

                # Find container by searching all containers for a name containing the service name
                # This handles both v1 (underscores) and v2 (hyphens) naming conventions
                all_containers = client.containers.list(all=True)
                container = None

                # Normalize service name for matching (handle both - and _)
                service_pattern = service_name.lower().replace(' ', '').replace('-', '').replace('_', '')

                for c in all_containers:
                    container_pattern = c.name.lower().replace('-', '').replace('_', '')
                    if service_pattern in container_pattern:
                        container = c
                        logging.writeToFile(f'Found matching container: {c.name} for service: {service_name}')
                        break

                if container is None:
                    logging.writeToFile(f'No container found matching service: {service_name}, attempt {attempt + 1}/{max_retries}')
                    time.sleep(delay)
                    continue

                if container.status == 'running':
                    health = container.attrs.get('State', {}).get('Health', {}).get('Status')

                    # Accept healthy, unhealthy, and starting states as long as container is running
                    if health in ['healthy', 'unhealthy', 'starting'] or health is None:
                        logging.writeToFile(f'Container {container.name} is running with health status: {health}')
                        return True
                    else:
                        health_logs = container.attrs.get('State', {}).get('Health', {}).get('Log', [])
                        if health_logs:
                            last_log = health_logs[-1]
                            logging.writeToFile(f'Container health check failed: {last_log.get("Output", "")}')

                logging.writeToFile(f'Container {container.name} status: {container.status}, health: {health}, attempt {attempt + 1}/{max_retries}')
                time.sleep(delay)

            return False

        except Exception as e:
            logging.writeToFile(f'Error checking container health: {str(e)}')
            return False

    def verify_system_resources(self):
        try:
            # Check available disk space using root access
            command = "df -B 1G /home/docker --output=avail | tail -1"
            result, output = ProcessUtilities.outputExecutioner(command, None, None, None, 1)
            if result == 0:
                raise DockerDeploymentError("Failed to check disk space")
            available_gb = int(output.strip())

            if available_gb < 5:  # Require minimum 5GB free space
                raise DockerDeploymentError(
                    f"Insufficient disk space. Need at least 5GB but only {available_gb}GB available.",
                    self.ERROR_VOLUME_FAILED
                )

            # Check if Docker is running and accessible
            command = "systemctl is-active docker"
            result, docker_status = ProcessUtilities.outputExecutioner(command, None, None, None, 1)
            if result == 0:
                raise DockerDeploymentError("Failed to check Docker status")
            if docker_status.strip() != "active":
                raise DockerDeploymentError("Docker service is not running")

            # Check Docker system info for resource limits
            command = "docker info --format '{{.MemTotal}}'"
            result, total_memory = ProcessUtilities.outputExecutioner(command, None, None, None, 1)
            if result == 0:
                raise DockerDeploymentError("Failed to get Docker memory info")
            
            # Convert total_memory from bytes to MB
            total_memory_mb = int(total_memory.strip()) / (1024 * 1024)
            
            # Calculate required memory from site and MySQL requirements
            required_memory = int(self.data['MemoryMySQL']) + int(self.data['MemorySite'])
            
            if total_memory_mb < required_memory:
                raise DockerDeploymentError(
                    f"Insufficient memory. Need {required_memory}MB but only {int(total_memory_mb)}MB available",
                    'INSUFFICIENT_MEMORY'
                )

            # Verify Docker group and permissions
            command = "getent group docker"
            result, docker_group = ProcessUtilities.outputExecutioner(command, None, None, None, 1)
            if result == 0 or not docker_group:
                raise DockerDeploymentError("Docker group does not exist")

            return True

        except DockerDeploymentError as e:
            raise e
        except Exception as e:
            raise DockerDeploymentError(f"Resource verification failed: {str(e)}")

    def setup_docker_environment(self):
        try:
            # Create docker directory with root
            command = f"mkdir -p /home/docker/{self.data['finalURL']}"
            ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            # Set proper permissions
            command = f"chown -R {self.data['externalApp']}:docker /home/docker/{self.data['finalURL']}"
            ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            # Create docker network if doesn't exist
            command = "docker network ls | grep cyberpanel"
            network_exists = ProcessUtilities.outputExecutioner(command, None, None, None, 1)
            if not network_exists:
                command = "docker network create cyberpanel"
                ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            return True

        except Exception as e:
            raise DockerDeploymentError(f"Environment setup failed: {str(e)}")

    def deploy_containers(self):
        try:
            # Write docker-compose file
            command = f"cat > {self.data['ComposePath']} << 'EOF'\n{self.data['ComposeContent']}\nEOF"
            ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            # Set proper permissions on compose file
            command = f"chmod 600 {self.data['ComposePath']} && chown root:root {self.data['ComposePath']}"
            ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            # Deploy with docker-compose
            command = f"cd {os.path.dirname(self.data['ComposePath'])} && docker-compose up -d"
            result = ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            if "error" in result.lower():
                raise DockerDeploymentError(f"Container deployment failed: {result}")

            return True

        except Exception as e:
            raise DockerDeploymentError(f"Deployment failed: {str(e)}")

    def cleanup_failed_deployment(self):
        try:
            # Stop and remove containers
            command = f"cd {os.path.dirname(self.data['ComposePath'])} && docker-compose down -v"
            ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            # Remove docker directory
            command = f"rm -rf /home/docker/{self.data['finalURL']}"
            ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            # Remove compose file
            command = f"rm -f {self.data['ComposePath']}"
            ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            return True

        except Exception as e:
            logging.writeToFile(f"Cleanup failed: {str(e)}")
            return False

    def find_container_by_service(self, service_name):
        """
        Find a container by service name using fuzzy matching.
        Returns the container object or None if not found.
        """
        try:
            client = docker.from_env()
            all_containers = client.containers.list(all=True)

            # Normalize service name for matching
            service_pattern = service_name.lower().replace(' ', '').replace('-', '').replace('_', '')

            for c in all_containers:
                container_pattern = c.name.lower().replace('-', '').replace('_', '')
                if service_pattern in container_pattern:
                    return c
            return None
        except Exception as e:
            logging.writeToFile(f'Error finding container: {str(e)}')
            return None

    def monitor_deployment(self):
        try:
            # Find containers dynamically using fuzzy matching
            n8n_container = self.find_container_by_service(self.data['ServiceName'])
            db_container = self.find_container_by_service(f"{self.data['ServiceName']}-db")

            if not n8n_container or not db_container:
                raise DockerDeploymentError("Could not find n8n or database containers")

            n8n_container_name = n8n_container.name
            db_container_name = db_container.name

            logging.writeToFile(f'Monitoring containers: {n8n_container_name} and {db_container_name}')

            # Check container health
            command = f"docker ps -a --filter name={self.data['ServiceName']} --format '{{{{.Status}}}}'"
            result, status = ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            # Only raise error if container is exited
            if "exited" in status.lower():
                # Get container logs
                command = f"docker logs {n8n_container_name}"
                result, logs = ProcessUtilities.outputExecutioner(command, None, None, None, 1)
                raise DockerDeploymentError(f"Container exited. Logs: {logs}")

            # Wait for database to be ready
            max_retries = 30
            retry_count = 0
            db_ready = False

            while retry_count < max_retries:
                # Check if database container is ready
                command = f"docker exec {db_container_name} pg_isready -U postgres"
                result, output = ProcessUtilities.outputExecutioner(command, None, None, None, 1)

                if "accepting connections" in output:
                    db_ready = True
                    break

                # Refresh container status
                db_container = self.find_container_by_service(f"{self.data['ServiceName']}-db")
                if db_container and db_container.status == 'exited':
                    raise DockerDeploymentError(f"Database container exited")

                retry_count += 1
                time.sleep(2)
                logging.writeToFile(f'Waiting for database to be ready, attempt {retry_count}/{max_retries}')

            if not db_ready:
                raise DockerDeploymentError("Database failed to become ready within timeout period")

            # Check n8n container status
            n8n_container = self.find_container_by_service(self.data['ServiceName'])
            if n8n_container and n8n_container.status == 'exited':
                raise DockerDeploymentError(f"n8n container exited")

            n8n_status = n8n_container.status if n8n_container else 'unknown'
            logging.writeToFile(f'Deployment monitoring completed successfully. n8n status: {n8n_status}, database ready: {db_ready}')
            return True

        except Exception as e:
            logging.writeToFile(f'Error during monitoring: {str(e)}')
            raise DockerDeploymentError(f"Monitoring failed: {str(e)}")

    def handle_deployment_failure(self, error, cleanup=True):
        """
        Handle deployment failures and attempt recovery
        """
        try:
            logging.writeToFile(f'Deployment failed: {str(error)}')
            
            if cleanup:
                self.cleanup_failed_deployment()
            
            if isinstance(error, DockerDeploymentError):
                if error.error_code == self.ERROR_DOCKER_NOT_INSTALLED:
                    # Attempt to install Docker
                    execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/dockerManager/dockerInstall.py"
                    ProcessUtilities.executioner(execPath)
                    return True
                    
                elif error.error_code == self.ERROR_PORT_IN_USE:
                    # Find next available port
                    new_port = int(self.data['port']) + 1
                    while new_port < 65535:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        result = sock.connect_ex(('127.0.0.1', new_port))
                        sock.close()
                        if result != 0:
                            self.data['port'] = str(new_port)
                            return True
                        new_port += 1
                        
                elif error.error_code == self.ERROR_DB_FAILED:
                    # Attempt database recovery
                    return self.recover_database()
                    
            return False
            
        except Exception as e:
            logging.writeToFile(f'Error during failure handling: {str(e)}')
            return False

    def recover_database(self):
        """
        Attempt to recover the database container
        """
        try:
            client = docker.from_env()
            db_container_name = f"{self.data['ServiceName']}-db"
            
            try:
                db_container = client.containers.get(db_container_name)
                
                if db_container.status == 'running':
                    exec_result = db_container.exec_run(
                        'pg_isready -U postgres'
                    )
                    
                    if exec_result.exit_code != 0:
                        db_container.restart()
                        time.sleep(10)
                        
                        if self.check_container_health(db_container_name):
                            return True
                            
            except docker.errors.NotFound:
                pass
                
            return False
            
        except Exception as e:
            logging.writeToFile(f'Database recovery failed: {str(e)}')
            return False

    def log_deployment_metrics(self, metrics):
        """
        Log deployment metrics for analysis
        """
        if metrics:
            try:
                log_file = f"/var/log/cyberpanel/docker/{self.data['ServiceName']}_metrics.json"
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                
                with open(log_file, 'w') as f:
                    json.dump(metrics, f, indent=2)
                    
            except Exception as e:
                logging.writeToFile(f'Error logging metrics: {str(e)}')

    def DeployN8NContainer(self):
        """
        Main deployment method with error handling
        """
        max_retries = 3
        current_try = 0
        
        while current_try < max_retries:
            try:
                logging.statusWriter(self.JobID, 'Starting deployment verification...,0')
                
                # Check Docker installation
                command = 'docker --help'
                result = ProcessUtilities.outputExecutioner(command)
                if result.find("not found") > -1:
                    if os.path.exists(ProcessUtilities.debugPath):
                        logging.writeToFile(f'About to run docker install function...')
                    
                    # Call InstallDocker to install Docker
                    install_result, error = self.InstallDocker()
                    if not install_result:
                        logging.statusWriter(self.JobID, f'Failed to install Docker: {error} [404]')
                        return 0

                logging.statusWriter(self.JobID, 'Docker installation verified...,20')

                # Verify system resources
                self.verify_system_resources()
                logging.statusWriter(self.JobID, 'System resources verified...,10')

                # Create directories
                command = f"mkdir -p /home/docker/{self.data['finalURL']}"
                result, message = ProcessUtilities.outputExecutioner(command, None, None, None, 1)
                if result == 0:
                    raise DockerDeploymentError(f"Failed to create directories: {message}")
                logging.statusWriter(self.JobID, 'Directories created...,30')

                # Generate and write docker-compose file
                self.data['ServiceName'] = self.data["SiteName"].replace(' ', '-')
                compose_config = self.generate_compose_config()
                
                TempCompose = f'/home/cyberpanel/{self.data["finalURL"]}-docker-compose.yml'
                with open(TempCompose, 'w') as f:
                    f.write(compose_config)
                
                command = f"mv {TempCompose} {self.data['ComposePath']}"
                result, message = ProcessUtilities.outputExecutioner(command, None, None, None, 1)
                if result == 0:
                    raise DockerDeploymentError(f"Failed to move compose file: {message}")
                
                command = f"chmod 600 {self.data['ComposePath']} && chown root:root {self.data['ComposePath']}"
                ProcessUtilities.executioner(command, 'root', True)
                logging.statusWriter(self.JobID, 'Docker compose file created...,40')

                # Deploy containers
                if ProcessUtilities.decideDistro() == ProcessUtilities.cent8 or ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                    dockerCommand = 'docker compose'
                else:
                    dockerCommand = 'docker-compose'

                command = f"{dockerCommand} -f {self.data['ComposePath']} -p '{self.data['SiteName']}' up -d"
                result, message = ProcessUtilities.outputExecutioner(command, None, None, None, 1)
                if result == 0:
                    raise DockerDeploymentError(f"Failed to deploy containers: {message}")
                logging.statusWriter(self.JobID, 'Containers deployed...,60')

                # Wait for containers to be healthy
                time.sleep(25)
                if not self.check_container_health(f"{self.data['ServiceName']}-db") or \
                   not self.check_container_health(self.data['ServiceName']):
                    raise DockerDeploymentError("Containers failed to reach healthy state", self.ERROR_CONTAINER_FAILED)
                logging.statusWriter(self.JobID, 'Containers healthy...,70')

                # Setup proxy
                execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py"
                execPath = execPath + f" SetupProxy --port {self.data['port']}"
                ProcessUtilities.executioner(execPath)
                logging.statusWriter(self.JobID, 'Proxy configured...,80')

                # Setup n8n vhost configuration instead of htaccess
                execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py"
                execPath = execPath + f" SetupN8NVhost --domain {self.data['finalURL']} --port {self.data['port']}"
                ProcessUtilities.executioner(execPath)
                logging.statusWriter(self.JobID, 'N8N vhost configured...,90')

                # Restart web server
                from plogical.installUtilities import installUtilities
                installUtilities.reStartLiteSpeedSocket()

                # Monitor deployment
                metrics = self.monitor_deployment()
                self.log_deployment_metrics(metrics)

                logging.statusWriter(self.JobID, 'Deployment completed successfully. [200]')
                return True
                
            except DockerDeploymentError as e:
                logging.writeToFile(f'Deployment error: {str(e)}')
                
                if self.handle_deployment_failure(e):
                    current_try += 1
                    continue
                else:
                    logging.statusWriter(self.JobID, f'Deployment failed: {str(e)} [404]')
                    return False
                    
            except Exception as e:
                logging.writeToFile(f'Unexpected error: {str(e)}')
                self.handle_deployment_failure(e)
                logging.statusWriter(self.JobID, f'Deployment failed: {str(e)} [404]')
                return False
                
        logging.statusWriter(self.JobID, f'Deployment failed after {max_retries} attempts [404]')
        return False

    def generate_compose_config(self):
        """
        Generate the docker-compose configuration with improved security and reliability
        """
        postgres_config = {
            'image': 'postgres:16-alpine',
            'user': 'root',
            'healthcheck': {
                'test': ["CMD-SHELL", "pg_isready -U postgres"],
                'interval': '10s',
                'timeout': '5s',
                'retries': 5,
                'start_period': '30s'
            },
            'environment': {
                'POSTGRES_USER': 'postgres',
                'POSTGRES_PASSWORD': self.data['MySQLPassword'],
                'POSTGRES_DB': self.data['MySQLDBName']
            }
        }

        n8n_config = {
            'image': 'docker.n8n.io/n8nio/n8n',
            'user': 'root',
            'healthcheck': {
                'test': ["CMD", "wget", "--spider", "http://localhost:5678"],
                'interval': '20s',
                'timeout': '10s',
                'retries': 3
            },
            'environment': {
                'DB_TYPE': 'postgresdb',
                'DB_POSTGRESDB_HOST': f"{self.data['ServiceName']}-db",
                'DB_POSTGRESDB_PORT': '5432',
                'DB_POSTGRESDB_DATABASE': self.data['MySQLDBName'],
                'DB_POSTGRESDB_USER': 'postgres',
                'DB_POSTGRESDB_PASSWORD': self.data['MySQLPassword'],
                'N8N_HOST': '0.0.0.0',
                'N8N_PORT': '5678',
                'NODE_ENV': 'development',  # Required for OpenLiteSpeed compatibility - OLS cannot override browser Origin headers which n8n v1.87.0+ validates in production mode
                'N8N_EDITOR_BASE_URL': f"https://{self.data['finalURL']}",
                'WEBHOOK_URL': f"https://{self.data['finalURL']}",
                'WEBHOOK_TUNNEL_URL': f"https://{self.data['finalURL']}",
                'N8N_PUSH_BACKEND': 'sse',
                'GENERIC_TIMEZONE': 'UTC',
                'N8N_ENCRYPTION_KEY': 'auto',
                'N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS': 'true',
                'DB_POSTGRESDB_SCHEMA': 'public',
                'N8N_PROTOCOL': 'https',
                'N8N_SECURE_COOKIE': 'true'
            }
        }

        return f'''version: '3.8'

volumes:
  db_storage:
    driver: local
  n8n_storage:
    driver: local

services:
  '{self.data['ServiceName']}-db':
    image: {postgres_config['image']}
    user: {postgres_config['user']}
    restart: always
    healthcheck:
      test: {postgres_config['healthcheck']['test']}
      interval: {postgres_config['healthcheck']['interval']}
      timeout: {postgres_config['healthcheck']['timeout']}
      retries: {postgres_config['healthcheck']['retries']}
      start_period: {postgres_config['healthcheck']['start_period']}
    environment:
      - POSTGRES_USER={postgres_config['environment']['POSTGRES_USER']}
      - POSTGRES_PASSWORD={postgres_config['environment']['POSTGRES_PASSWORD']}
      - POSTGRES_DB={postgres_config['environment']['POSTGRES_DB']}
    volumes:
      - "/home/docker/{self.data['finalURL']}/db:/var/lib/postgresql/data"
    networks:
      - n8n-network
    deploy:
      resources:
        limits:
          cpus: '{self.data["CPUsMySQL"]}'
          memory: {self.data["MemoryMySQL"]}M

  '{self.data['ServiceName']}':
    image: {n8n_config['image']}
    user: {n8n_config['user']}
    restart: always
    healthcheck:
      test: {n8n_config['healthcheck']['test']}
      interval: {n8n_config['healthcheck']['interval']}
      timeout: {n8n_config['healthcheck']['timeout']}
      retries: {n8n_config['healthcheck']['retries']}
    environment:
      - DB_TYPE={n8n_config['environment']['DB_TYPE']}
      - DB_POSTGRESDB_HOST={n8n_config['environment']['DB_POSTGRESDB_HOST']}
      - DB_POSTGRESDB_PORT={n8n_config['environment']['DB_POSTGRESDB_PORT']}
      - DB_POSTGRESDB_DATABASE={n8n_config['environment']['DB_POSTGRESDB_DATABASE']}
      - DB_POSTGRESDB_USER={n8n_config['environment']['DB_POSTGRESDB_USER']}
      - DB_POSTGRESDB_PASSWORD={n8n_config['environment']['DB_POSTGRESDB_PASSWORD']}
      - DB_POSTGRESDB_SCHEMA={n8n_config['environment']['DB_POSTGRESDB_SCHEMA']}
      - N8N_HOST={n8n_config['environment']['N8N_HOST']}
      - N8N_PORT={n8n_config['environment']['N8N_PORT']}
      - NODE_ENV={n8n_config['environment']['NODE_ENV']}
      - N8N_EDITOR_BASE_URL={n8n_config['environment']['N8N_EDITOR_BASE_URL']}
      - WEBHOOK_URL={n8n_config['environment']['WEBHOOK_URL']}
      - WEBHOOK_TUNNEL_URL={n8n_config['environment']['WEBHOOK_TUNNEL_URL']}
      - N8N_PUSH_BACKEND={n8n_config['environment']['N8N_PUSH_BACKEND']}
      - GENERIC_TIMEZONE={n8n_config['environment']['GENERIC_TIMEZONE']}
      - N8N_ENCRYPTION_KEY={n8n_config['environment']['N8N_ENCRYPTION_KEY']}
      - N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS={n8n_config['environment']['N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS']}
      - N8N_PROTOCOL={n8n_config['environment']['N8N_PROTOCOL']}
      - N8N_SECURE_COOKIE={n8n_config['environment']['N8N_SECURE_COOKIE']}
    ports:
      - "{self.data['port']}:5678"
    depends_on:
      - {self.data['ServiceName']}-db
    volumes:
      - "/home/docker/{self.data['finalURL']}/data:/home/node/.n8n"
    networks:
      - n8n-network
    deploy:
      resources:
        limits:
          cpus: '{self.data["CPUsSite"]}'
          memory: {self.data["MemorySite"]}M

networks:
  n8n-network:
    driver: bridge
    name: {self.data['ServiceName']}_network'''

def Main():
    try:

        parser = argparse.ArgumentParser(description='CyberPanel Docker Sites')
        parser.add_argument('function', help='Specify a function to call!')
        parser.add_argument('--port', help='')
        parser.add_argument('--htaccess', help='')
        parser.add_argument('--externalApp', help='')
        parser.add_argument('--domain', help='')

        args = parser.parse_args()

        if args.function == "SetupProxy":
            Docker_Sites.SetupProxy(args.port)
        elif args.function == 'SetupHTAccess':
            Docker_Sites.SetupHTAccess(args.port, args.htaccess)
        elif args.function == 'SetupN8NVhost':
            Docker_Sites.SetupN8NVhost(args.domain, args.port)
        elif args.function == 'DeployWPDocker':
            # Takes
            # ComposePath, MySQLPath, MySQLRootPass, MySQLDBName, MySQLDBNUser, MySQLPassword, CPUsMySQL, MemoryMySQL,
            # port, SitePath, CPUsSite, MemorySite, SiteName
            # finalURL, blogTitle, adminUser, adminPassword, adminEmail, htaccessPath, externalApp
            data = {
                "JobID": '/home/cyberpanel/hey.txt',
                "ComposePath": "/home/docker.cyberpanel.net/docker-compose.yml",
                "MySQLPath": '/home/docker.cyberpanel.net/public_html/sqldocker',
                "MySQLRootPass": 'testdbwp12345',
                "MySQLDBName": 'testdbwp',
                "MySQLDBNUser": 'testdbwp',
                "MySQLPassword": 'testdbwp12345',
                "CPUsMySQL": '2',
                "MemoryMySQL": '512',
                "port": '8000',
                "SitePath": '/home/docker.cyberpanel.net/public_html/wpdocker',
                "CPUsSite": '2',
                "MemorySite": '512',
                "SiteName": 'wp docker test',
                "finalURL": 'docker.cyberpanel.net',
                "blogTitle": 'docker site',
                "adminUser": 'testdbwp',
                "adminPassword": 'testdbwp',
                "adminEmail": 'usman@cyberpersons.com',
                "htaccessPath": '/home/docker.cyberpanel.net/public_html/.htaccess',
                "externalApp": 'docke8463',
                "docRoot": "/home/docker.cyberpanel.net"
            }
            ds = Docker_Sites('', data)
            ds.DeployN8NContainer()

        elif args.function == 'DeleteDockerApp':
            data = {
                "domain": args.domain}
            ds = Docker_Sites('', data)
            ds.DeleteDockerApp()


    except BaseException as msg:
        print(str(msg))
        pass


if __name__ == "__main__":
    Main()
