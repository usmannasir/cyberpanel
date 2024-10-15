#!/usr/local/CyberCP/bin/python
import json
import os
import sys
import time
from random import randint

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


class Docker_Sites(multi.Thread):
    Wordpress = 1
    Joomla = 2

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
            command = 'apt install docker-compose -y'

            ReturnCode = ProcessUtilities.executioner(command)

            if ReturnCode:
                return 1, None
            else:
                return 0, ReturnCode

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
  pcKeepAliveTimeout      60
  initTimeout             60
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
            ET.SubElement(new_ext_processor, 'maxConns').text = '35'
            ET.SubElement(new_ext_processor, 'pcKeepAliveTimeout').text = '60'
            ET.SubElement(new_ext_processor, 'initTimeout').text = '60'
            ET.SubElement(new_ext_processor, 'retryTimeout').text = '60'
            ET.SubElement(new_ext_processor, 'respBuffer').text = '0'

            # Append the new <extProcessor> to the <extProcessorList>
            ext_processor_list.append(new_ext_processor)

            # Write the updated XML content to a new file or print it out
            tree = ET.ElementTree(root)
            tree.write(ConfPath, encoding='UTF-8', xml_declaration=True)

            # Optionally, print the updated XML
            ET.dump(root)


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

            import docker

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

            import docker

            # Create a Docker client
            client = docker.from_env()

            FilerValue = self.DockerAppName

            # Define the label to filter containers
            label_filter = {'name': FilerValue}


            # List containers matching the label filter
            containers = client.containers.list(filters=label_filter)

            json_data = "["
            checker = 0

            for container in containers:

                dic = {
                    'id': container.short_id,
                    'name': container.name,
                    'status': container.status,
                    'volumes': container.attrs['HostConfig']['Binds'] if 'HostConfig' in container.attrs else [],
                    'logs_50': container.logs(tail=50).decode('utf-8'),
                    'ports': container.attrs['HostConfig']['PortBindings'] if 'HostConfig' in container.attrs else {}
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'

            return 1, json_data

        except BaseException as msg:
            logging.writeToFile("List Container ....... %s" % str(msg))
            return 0, str(msg)

    ### pass container id and number of lines to fetch from logs
    def ContainerLogs(self):
        try:
            import docker
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
            import docker
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
            import docker
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
            import docker
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

    def DeployN8NContainer(self):
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

volumes:
  db_storage:
  n8n_storage:

services:
  '{self.data['ServiceName']}-db':
    image: docker.io/bitnami/postgresql:16
    user: root
    restart: always
    environment:
#      - POSTGRES_USER:root
      - POSTGRESQL_USERNAME={self.data['MySQLDBNUser']}
      - POSTGRESQL_DATABASE={self.data['MySQLDBName']}
      - POSTGRESQL_POSTGRES_PASSWORD={self.data['MySQLPassword']}
      - POSTGRESQL_PASSWORD={self.data['MySQLPassword']}
    volumes:
#      - "/home/docker/{self.data['finalURL']}/db:/var/lib/postgresql/data"
      - "/home/docker/{self.data['finalURL']}/db:/bitnami/postgresql"

  '{self.data['ServiceName']}':
    image: docker.n8n.io/n8nio/n8n
    user: root
    restart: always
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST={self.data['ServiceName']}-db
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE={self.data['MySQLDBName']}
      - DB_POSTGRESDB_USER={self.data['MySQLDBNUser']}
      - DB_POSTGRESDB_PASSWORD={self.data['MySQLPassword']}
      - N8N_HOST={self.data['finalURL']}
      - NODE_ENV=production
      - WEBHOOK_URL=https://{self.data['finalURL']}
    ports:
      - "{self.data['port']}:5678"
    links:
      - {self.data['ServiceName']}-db
    volumes:
      - "/home/docker/{self.data['finalURL']}/data:/home/node/.n8n"
    depends_on:
      - '{self.data['ServiceName']}-db'
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
                logging.writeToFile(f'Unkonwn error, containers not running. [DeployN8NContainer]')
                logging.statusWriter(self.JobID, f'Unkonwn error, containers not running. [DeployN8NContainer]')
                return 0

            ### Set up Proxy

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py"
            execPath = execPath + f" SetupProxy --port {self.data['port']}"
            ProcessUtilities.executioner(execPath)

            ### Set up ht access

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py"
            execPath = execPath + f" SetupHTAccess --port {self.data['port']} --htaccess {self.data['htaccessPath']}"
            ProcessUtilities.executioner(execPath, self.data['externalApp'])

            # if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
            #     group = 'nobody'
            # else:
            #     group = 'nogroup'
            #
            # command = f"chown -R nobody:{group} /home/docker/{self.data['finalURL']}/data"
            # ProcessUtilities.executioner(command)

            ### just restart ls for htaccess

            from plogical.installUtilities import installUtilities
            installUtilities.reStartLiteSpeedSocket()

            logging.statusWriter(self.JobID, 'Completed. [200]')

        except BaseException as msg:
            logging.writeToFile(f'{str(msg)}. [DeployN8NContainer]')
            logging.statusWriter(self.JobID, f'Error {str(msg)} . [404]')
            print(str(msg))
            pass


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
