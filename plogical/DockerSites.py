#!/usr/local/CyberCP/bin/python
import os
import sys
sys.path.append('/usr/local/CyberCP')
import django
from plogical.processUtilities import ProcessUtilities
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import argparse

class DockerSites:

    def __init__(self, data):
        self.data = data
        self.JobID = self.data['JobID'] ##JOBID will be file path where status is being written
        pass

    def InstallDocker(self):

        command = 'apt install docker-compose -y'
        ReturnCode = ProcessUtilities.executioner(command)

        if ReturnCode:
            return 1, None
        else:
            return 0, ReturnCode

    @staticmethod
    def SetupProxy(port):
        ConfPath = '/usr/local/lsws/conf/httpd_config.conf'
        data = open(ConfPath, 'r').read()
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
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

            ProcessUtilities.restartLitespeed()


    # Takes
    # ComposePath, MySQLPath, MySQLRootPass, MySQLDBName, MySQLDBNUser, MySQLPassword, CPUsMySQL, MemoryMySQL,
    # port, SitePath, CPUsSite, MemorySite, ComposePath, SiteName
    # finalURL, blogTitle, adminUser, adminPassword, adminEmail, htaccessPath, externalApp

    def DeployWPContainer(self):

        try:
            logging.statusWriter(self.JobID, 'Checking if Docker is installed..,0')

            command = 'docker --help'
            result = ProcessUtilities.outputExecutioner(command)
            print(f'return code of docker install {result}')
            if result.find("not found") > -1:
                status, message = self.InstallDocker()
                if status == 0:
                    logging.statusWriter(self.JobID, 'Failed to installed docker. [404]')
                    return 0, message

            logging.statusWriter(self.JobID, 'Docker is ready to use..,10')

#             WPSite = f"""
# version: "3.8"
#
# services:
#   db:
#     image: mysql:5.7
#     restart: always
#     volumes:
#       - "{self.data['MySQLPath']}:/var/lib/mysql"
#     environment:
#       MYSQL_ROOT_PASSWORD: {self.data['MySQLRootPass']}
#       MYSQL_DATABASE: {self.data['MySQLDBName']}
#       MYSQL_USER: {self.data['MySQLDBNUser']}
#       MYSQL_PASSWORD: {self.data['MySQLPassword']}
#     deploy:
#       resources:
#         limits:
#           cpus: '{self.data['CPUsMySQL']}'  # Use 50% of one CPU core
#           memory: {self.data['MemoryMySQL']}M  # Limit memory to 512 megabytes
#   wordpress:
#     depends_on:
#       - db
#     image: wordpress:latest
#     restart: always
#     ports:
#       - "{self.data['port']}:80"
#     environment:
#       WORDPRESS_DB_HOST: db:3306
#       WORDPRESS_DB_USER: {self.data['MySQLDBNUser']}
#       WORDPRESS_DB_PASSWORD: {self.data['MySQLPassword']}
#       WORDPRESS_DB_NAME: {self.data['MySQLDBName']}
#     volumes:
#       - "{self.data['SitePath']}:/var/www/html"
#     deploy:
#       resources:
#         limits:
#           cpus: '{self.data['CPUsSite']}'  # Use 50% of one CPU core
#           memory: {self.data['MemorySite']}M  # Limit memory to 512 megabytes
#
# volumes:
#   mysql: {{}}
# """
#
#             WPSite = f"""
# # Copyright VMware, Inc.
# # SPDX-License-Identifier: APACHE-2.0
#
# version: '2'
# services:
#   mariadb:
#     image: mariadb:10.5.9
#     user: root
#     command: --max_allowed_packet=256M
#     volumes:
#       - "{self.data['MySQLPath']}:/var/lib/mysql:delegated"
#     environment:
#       - ALLOW_EMPTY_PASSWORD=no
#       - MYSQL_USER={self.data['MySQLDBNUser']}
#       - MYSQL_PASSWORD={self.data['MySQLPassword']}
#       - MYSQL_DATABASE={self.data['MySQLDBName']}
#       - MYSQL_ROOT_PASSWORD={self.data['MySQLPassword']}
#     deploy:
#       resources:
#         limits:
#           cpus: '{self.data['CPUsMySQL']}'  # Use 50% of one CPU core
#           memory: {self.data['MemoryMySQL']}M  # Limit memory to 512 megabytes
#   wordpress:
#     image: litespeedtech/openlitespeed:latest
#     user: root
#     ports:
#       - "{self.data['port']}:80"
#       # - '443:8443'
#     volumes:
#       - {self.data['docRoot']}/lsws/conf:/usr/local/lsws/conf
#       - {self.data['docRoot']}/lsws/admin-conf:/usr/local/lsws/admin/conf
#       - {self.data['docRoot']}/bin:/usr/local/bin
#       - {self.data['SitePath']}:/var/www/vhosts/
#       - {self.data['docRoot']}/acme:/root/.acme.sh/
#       - {self.data['docRoot']}/logs:/usr/local/lsws/logs/
#     depends_on:
#       - mariadb
#     environment:
#       - TZ=America/New_York
#       - PHP_VERSION=lsphp82
#       - MYSQL_ROOT_PASSWORD={self.data['MySQLPassword']}
#       - DOMAIN={self.data['finalURL']}
#       - MYSQL_USER={self.data['MySQLDBNUser']}
#       - MYSQL_DATABASE={self.data['MySQLDBName']}
#       - MYSQL_PASSWORD={self.data['MySQLPassword']}
#     #   - ALLOW_EMPTY_PASSWORD=no
#     #   - WORDPRESS_DATABASE_HOST=mariadb
#     #   - WORDPRESS_DATABASE_PORT_NUMBER=3306
#     #   - WORDPRESS_USERNAME={self.data['adminUser']}
#     #   - WORDPRESS_PASSWORD={self.data["adminPassword"]}
#     #   - WORDPRESS_EMAIL={self.data["adminEmail"]}
#     #   - WORDPRESS_BLOG_NAME={self.data["blogTitle"]}
#     #   - WORDPRESS_ENABLE_REVERSE_PROXY=yes
#     deploy:
#       resources:
#         limits:
#           cpus: '{self.data['CPUsSite']}'  # Use 50% of one CPU core
#           memory: {self.data['MemorySite']}M  # Limit memory to 512 megabytes
# #   phpmyadmin:
# #     image: bitnami/phpmyadmin:latest
# #     ports:
# # #      - 8080:8080
# # #      - 8443:8443
# #     environment:
# #         DATABASE_HOST: mysql
# #     restart: always
# #     networks:
# #       - default
#
# volumes:
#   mariadb_data:
#     driver: local
#   wordpress_data:
#     driver: local
# """

            WPSite = f'''
version: '3.8'

services:
  wordpress:
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
      DB_Host: mariadb:3306
      SITE_NAME: '{self.data['SiteName']}'
    volumes:
#      - "/home/docker/{self.data['finalURL']}:/usr/local/lsws/Example/html"
      - "/home/docker/{self.data['finalURL']}/data:/usr/local/lsws/Example/html"
    depends_on:
      - mariadb
    deploy:
      resources:
        limits:
          cpus: '{self.data['CPUsSite']}'  # Use 50% of one CPU core
          memory: {self.data['MemorySite']}M  # Limit memory to 512 megabytes
  mariadb:
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


            WriteToFile = open(self.data['ComposePath'], 'w')
            WriteToFile.write(WPSite)
            WriteToFile.close()

            ####

            command = f"docker-compose -f {self.data['ComposePath']} -p '{self.data['SiteName']}' up -d"
            result = ProcessUtilities.outputExecutioner(command)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(result)


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
            print(str(msg))
            pass



def Main():
    try:


        parser = argparse.ArgumentParser(description='CyberPanel Docker Sites')
        parser.add_argument('function', help='Specify a function to call!')
        parser.add_argument('--port', help='')
        parser.add_argument('--htaccess', help='')
        parser.add_argument('--externalApp', help='')

        args = parser.parse_args()

        if args.function == "SetupProxy":
            DockerSites.SetupProxy(args.port)
        elif args.function == 'SetupHTAccess':
            DockerSites.SetupHTAccess(args.port, args.htaccess)
        elif args.function == 'DeployWPDocker':
            # Takes
            # ComposePath, MySQLPath, MySQLRootPass, MySQLDBName, MySQLDBNUser, MySQLPassword, CPUsMySQL, MemoryMySQL,
            # port, SitePath, CPUsSite, MemorySite, SiteName
            # finalURL, blogTitle, adminUser, adminPassword, adminEmail, htaccessPath, externalApp
            data = {
                "JobID": '/home/cyberpanel/error-logs.txt',
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
            ds = DockerSites(data)
            ds.DeployWPContainer()


    except BaseException as msg:
        print(str(msg))
        pass

if __name__ == "__main__":
    Main()