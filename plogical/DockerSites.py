from plogical.processUtilities import ProcessUtilities
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


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

    # Takes
    # ComposePath, MySQLPath, MySQLRootPass, MySQLDBName, MySQLDBNUser, MySQLPassword, CPUsMySQL, MemoryMySQL,
    # port, SitePath, CPUsSite, MemorySite, ComposePath, SiteName
    # finalURL, blogTitle, adminUser, adminPassword, adminEmail

    def DeployWPContainer(self):
        try:
            logging.statusWriter(self.JobID, 'Checking if Docker is installed..,0')


            command = 'docker --help'
            ReturnCode = ProcessUtilities.executioner(command)
            if ReturnCode == 0:
                status, message = self.InstallDocker()
                if status == 0:
                    logging.statusWriter(self.JobID, 'Failed to installed docker. [404]')
                    return 0, message

            logging.statusWriter(self.JobID, 'Docker is ready to use..,10')

            WPSite = f"""
version: "3.8"

services:
  db:
    image: mysql:5.7
    restart: always
    volumes:
      - "{self.data['MySQLPath']}:/var/lib/mysql"
    environment:
      MYSQL_ROOT_PASSWORD: {self.data['MySQLRootPass']}
      MYSQL_DATABASE: {self.data['MySQLDBName']}
      MYSQL_USER: {self.data['MySQLDBNUser']}
      MYSQL_PASSWORD: {self.data['MySQLPassword']}
    deploy:
      resources:
        limits:
          cpus: '{self.data['CPUsMySQL']}'  # Use 50% of one CPU core
          memory: {self.data['MemoryMySQL']}M  # Limit memory to 512 megabytes
  wordpress:
    depends_on:
      - db
    image: wordpress:latest
    restart: always
    ports:
      - "{self.data['port']}:80"
    environment:
      WORDPRESS_DB_HOST: db:3306
      WORDPRESS_DB_USER: {self.data['MySQLDBNUser']}
      WORDPRESS_DB_PASSWORD: {self.data['MySQLPassword']}
      WORDPRESS_DB_NAME: {self.data['MySQLDBName']}
    volumes:
      - "{self.data['SitePath']}:/var/www/html"
    deploy:
      resources:
        limits:
          cpus: '{self.data['CPUsSite']}'  # Use 50% of one CPU core
          memory: {self.data['MemorySite']}M  # Limit memory to 512 megabytes

volumes:
  mysql: {{}}
"""

            ### WriteConfig to compose-file

            WriteToFile = open(self.data['ComposePath'], 'w')
            WriteToFile.write(WPSite)
            WriteToFile.close()

            ####

            command = f"docker-compose -f {self.data['ComposePath']} -p '{self.data['SiteName']}' up -d"
            ReturnCode = ProcessUtilities.executioner(command)

            command = f"docker-compose -f {self.data['ComposePath']} ps -q wordpress"
            stdout = ProcessUtilities.outputExecutioner(command)

            self.ContainerID = stdout.rstrip('\n')



            command = f'docker-compose -f {self.data["ComposePath"]} exec {self.ContainerID} curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar'
            ReturnCode = ProcessUtilities.executioner(command)

            command = f"docker-compose -f {self.data['ComposePath']} exec {self.ContainerID} chmod + wp-cli.phar"
            ReturnCode = ProcessUtilities.executioner(command)

            command = f"docker-compose -f {self.data['ComposePath']} exec {self.ContainerID} mv wp-cli.phar /bin/wp"
            ReturnCode = ProcessUtilities.executioner(command)

            command = f'docker-compose -f {self.data["ComposePath"]} exec {self.ContainerID} wp core install --url="http://{self.data["finalURL"]}" --title="{self.data["blogTitle"]}" --admin_user="{self.data["adminUser"]}" --admin_password="{self.data["adminPassword"]}" --admin_email="{self.data["adminEmail"]}" --path=. --allow-root'
            ReturnCode = ProcessUtilities.executioner(command)

        except BaseException as msg:
            print(str(msg))
            pass


def Main():
    try:
        # Takes
        # ComposePath, MySQLPath, MySQLRootPass, MySQLDBName, MySQLDBNUser, MySQLPassword, CPUsMySQL, MemoryMySQL,
        # port, SitePath, CPUsSite, MemorySite, SiteName
        # finalURL, blogTitle, adminUser, adminPassword, adminEmail
        data = {
            "JobID": 1122344566667778888,
            "ComposePath": "/home/dockercloudpagescloud/docker-compose.yml",
            "MySQLPath": '/home/dockercloudpagescloud/public_html/sqldocker',
            "MySQLRootPass": 'testdbwp12345',
            "MySQLDBName": 'testdbwp',
            "MySQLDBNUser": 'testdbwp',
            "MySQLPassword": 'testdbwp12345',
            "CPUsMySQL": '2',
            "MemoryMySQL": '512',
            "port": '8000',
            "SitePath": '/home/dockercloudpagescloud/public_html/wpdocker',
            "CPUsSite": '2',
            "MemorySite": '512',
            "SiteName": 'wp docker test',
            "finalURL": '95.217.125.218:8001',
            "blogTitle": 'testdbwp',
            "adminUser": 'testdbwp',
            "adminPassword": 'testdbwp',
            "adminEmail": 'testdbwp',
        }
        ds = DockerSites(data)

        ds.DeployWPContainer()
    except BaseException as msg:
        print(str(msg))
        pass

if __name__ == "__main__":
    Main()