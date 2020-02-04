#!/usr/local/CyberCP/bin/python
import os, sys

sys.path.append('/usr/local/CyberCP')
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import threading as multi
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import subprocess
from plogical.vhost import vhost
from websiteFunctions.models import ChildDomains, Websites
from plogical import randomPassword
from plogical.mysqlUtilities import mysqlUtilities
from databases.models import Databases
from plogical.installUtilities import installUtilities
import shutil
from plogical.mailUtilities import mailUtilities
from plogical.processUtilities import ProcessUtilities



class ApplicationInstaller(multi.Thread):

    def __init__(self, installApp, extraArgs):
        multi.Thread.__init__(self)
        self.installApp = installApp
        self.extraArgs = extraArgs
        if extraArgs != None:
            self.tempStatusPath = self.extraArgs['tempStatusPath']

    def run(self):
        try:
            if self.installApp == 'wordpress':
                self.installWordPress()
            elif self.installApp == 'joomla':
                self.installJoomla()
            elif self.installApp == 'git':
                self.setupGit()
            elif self.installApp == 'pull':
                self.gitPull()
            elif self.installApp == 'detach':
                self.detachRepo()
            elif self.installApp == 'changeBranch':
                self.changeBranch()
            elif self.installApp == 'prestashop':
                self.installPrestaShop()
            elif self.installApp == 'magento':
                self.installMagento()
            elif self.installApp == 'convertDomainToSite':
                self.convertDomainToSite()

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [ApplicationInstaller.run]')

    def convertDomainToSite(self):
        try:

            from websiteFunctions.website import WebsiteManager
            import json, time

            request = self.extraArgs['request']

            ##

            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines('Deleting domain as child..,20')
            statusFile.close()

            data = json.loads(request.body)

            domainName = data['domainName']

            childDomain = ChildDomains.objects.get(domain=domainName)
            path = childDomain.path

            wm = WebsiteManager()

            wm.submitDomainDeletion(request.session['userID'], {'websiteName': domainName})
            time.sleep(5)

            ##

            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines('Creating domain as website..,40')
            statusFile.close()

            resp = wm.submitWebsiteCreation(request.session['userID'], data)
            respData = json.loads(resp.content.decode('utf-8'))

            ##

            while True:
                respDataStatus = ProcessUtilities.outputExecutioner("cat " + respData['tempStatusPath'])

                if respDataStatus.find('[200]') > -1:
                    break
                elif respDataStatus.find('[404]') > -1:
                    statusFile = open(self.tempStatusPath, 'w')
                    statusFile.writelines(respDataStatus['currentStatus'] + '  [404]')
                    statusFile.close()
                    return 0
                else:
                    statusFile = open(self.tempStatusPath, 'w')
                    statusFile.writelines(respDataStatus)
                    statusFile.close()
                    time.sleep(1)

            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines('Moving data..,80')
            statusFile.close()


            command = 'rm -rf  /home/%s/public_html' % (domainName)
            ProcessUtilities.executioner(command)

            command = 'mv %s /home/%s/public_html' % (path, domainName)
            ProcessUtilities.executioner(command)

            website = Websites.objects.get(domain=domainName)

            command = 'chown %s:%s /home/%s/public_html' % (website.externalApp, website.externalApp, domainName)
            ProcessUtilities.executioner(command)

            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines('Successfully converted. [200]')
            statusFile.close()

        except BaseException as msg:
            statusFile = open(self.tempStatusPath, 'w')
            statusFile.writelines(str(msg) + " [404]")
            statusFile.close()
            return 0

    def installWPCLI(self):
        try:
            command = 'sudo wget https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar'
            ProcessUtilities.executioner(command)

            command = 'sudo chmod +x wp-cli.phar'
            ProcessUtilities.executioner(command)

            command = 'sudo mv wp-cli.phar /usr/bin/wp'
            ProcessUtilities.executioner(command)

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [ApplicationInstaller.installWPCLI]')

    def dataLossCheck(self, finalPath, tempStatusPath):

        dirFiles = os.listdir(finalPath)

        if len(dirFiles) <= 3:
            return 1
        else:
            return 0

    def installGit(self):
        try:
            if os.path.exists("/etc/lsb-release"):
                command = 'apt -y install git'
                ProcessUtilities.executioner(command)
            else:
                command = 'sudo yum -y install http://repo.iotti.biz/CentOS/7/noarch/lux-release-7-1.noarch.rpm'
                ProcessUtilities.executioner(command)

                command = 'sudo yum install git -y'
                ProcessUtilities.executioner(command)

        except BaseException as msg:
            logging.writeToFile(str(msg) + ' [ApplicationInstaller.installGit]')

    def dbCreation(self, tempStatusPath, website):
        try:
            dbName = randomPassword.generate_pass()
            dbUser = dbName
            dbPassword = randomPassword.generate_pass()

            ## DB Creation

            if Databases.objects.filter(dbName=dbName).exists() or Databases.objects.filter(
                    dbUser=dbUser).exists():
                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines(
                    "This database or user is already taken." + " [404]")
                statusFile.close()
                return 0

            result = mysqlUtilities.createDatabase(dbName, dbUser, dbPassword)

            if result == 1:
                pass
            else:
                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines(
                    "Not able to create database." + " [404]")
                statusFile.close()
                return 0

            db = Databases(website=website, dbName=dbName, dbUser=dbUser)
            db.save()

            return dbName, dbUser, dbPassword

        except BaseException as msg:
            logging.writeToFile(str(msg) + '[ApplicationInstallerdbCreation]')

    def installWordPress(self):
        try:

            admin = self.extraArgs['admin']
            domainName = self.extraArgs['domainName']
            home = self.extraArgs['home']
            tempStatusPath = self.extraArgs['tempStatusPath']
            blogTitle = self.extraArgs['blogTitle']
            adminUser = self.extraArgs['adminUser']
            adminPassword = self.extraArgs['adminPassword']
            adminEmail = self.extraArgs['adminEmail']

            FNULL = open(os.devnull, 'w')

            ### Check WP CLI

            try:
                command = 'sudo wp --info'
                outout = ProcessUtilities.outputExecutioner(command)

                if not outout.find('WP-CLI root dir:') > -1:
                    self.installWPCLI()
            except subprocess.CalledProcessError:
                self.installWPCLI()

            ## Open Status File

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Setting up paths,0')
            statusFile.close()

            finalPath = ''

            try:
                website = ChildDomains.objects.get(domain=domainName)
                externalApp = website.master.externalApp

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = website.path.rstrip('/') + "/" + path + "/"
                else:
                    finalPath = website.path

                if website.master.package.dataBases > website.master.databases_set.all().count():
                    pass
                else:
                    statusFile = open(tempStatusPath, 'w')
                    statusFile.writelines(
                        "Maximum database limit reached for this website." + " [404]")
                    statusFile.close()
                    return 0

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website.master)

            except:
                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = "/home/" + domainName + "/public_html/" + path + "/"
                else:
                    finalPath = "/home/" + domainName + "/public_html/"

                if website.package.dataBases > website.databases_set.all().count():
                    pass
                else:
                    statusFile = open(tempStatusPath, 'w')
                    statusFile.writelines(
                        "Maximum database limit reached for this website." + " [404]")
                    statusFile.close()
                    return 0

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website)

            ## Security Check

            if finalPath.find("..") > -1:
                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines("Specified path must be inside virtual host home." + " [404]")
                statusFile.close()
                return 0

            if not os.path.exists(finalPath):
                command = 'mkdir -p ' + finalPath
                ProcessUtilities.executioner(command, externalApp)

            ## checking for directories/files

            if self.dataLossCheck(finalPath, tempStatusPath) == 0:
                return 0

            ####

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Downloading WordPress Core,30')
            statusFile.close()

            command = "wp core download --allow-root --path=" + finalPath
            ProcessUtilities.executioner(command, externalApp)

            ##

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Configuring the installation,40')
            statusFile.close()

            command = "wp core config --dbname=" + dbName + " --dbuser=" + dbUser + " --dbpass=" + dbPassword + " --dbhost=localhost --dbprefix=wp_ --allow-root --path=" + finalPath
            ProcessUtilities.executioner(command, externalApp)

            if home == '0':
                path = self.extraArgs['path']
                finalURL = domainName + '/' + path
            else:
                finalURL = domainName

            command = 'wp core install --url="http://' + finalURL + '" --title="' + blogTitle + '" --admin_user="' + adminUser + '" --admin_password="' + adminPassword + '" --admin_email="' + adminEmail + '" --allow-root --path=' + finalPath
            ProcessUtilities.executioner(command, externalApp)

            ##

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Installing LSCache Plugin,80')
            statusFile.close()

            command = "wp plugin install litespeed-cache --allow-root --path=" + finalPath
            ProcessUtilities.executioner(command, externalApp)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Activating LSCache Plugin,90')
            statusFile.close()

            command = "wp plugin activate litespeed-cache --allow-root --path=" + finalPath
            ProcessUtilities.executioner(command, externalApp)

            ##

            command = "chown -R " + externalApp + ":" + externalApp + " " + finalPath
            ProcessUtilities.executioner(command, externalApp)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines("Successfully Installed. [200]")
            statusFile.close()
            return 0


        except BaseException as msg:
            # remove the downloaded files
            FNULL = open(os.devnull, 'w')

            homeDir = "/home/" + domainName + "/public_html"

            if not os.path.exists(homeDir):
                command = "chown -R " + externalApp + ":" + externalApp + " " + homeDir
                ProcessUtilities.executioner(command, externalApp)

            try:
                mysqlUtilities.deleteDatabase(dbName, dbUser)
                db = Databases.objects.get(dbName=dbName)
                db.delete()
            except:
                pass

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines(str(msg) + " [404]")
            statusFile.close()
            return 0

    def installPrestaShop(self):
        try:

            admin = self.extraArgs['admin']
            domainName = self.extraArgs['domainName']
            home = self.extraArgs['home']
            shopName = self.extraArgs['shopName']
            firstName = self.extraArgs['firstName']
            lastName = self.extraArgs['lastName']
            databasePrefix = self.extraArgs['databasePrefix']
            email = self.extraArgs['email']
            password = self.extraArgs['password']
            tempStatusPath = self.extraArgs['tempStatusPath']

            FNULL = open(os.devnull, 'w')

            ## Open Status File

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Setting up paths,0')
            statusFile.close()

            finalPath = ''

            try:
                website = ChildDomains.objects.get(domain=domainName)
                externalApp = website.master.externalApp

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = website.path.rstrip('/') + "/" + path + "/"
                else:
                    finalPath = website.path + "/"

                if website.master.package.dataBases > website.master.databases_set.all().count():
                    pass
                else:
                    statusFile = open(tempStatusPath, 'w')
                    statusFile.writelines(
                        "Maximum database limit reached for this website." + " [404]")
                    statusFile.close()
                    return 0

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website.master)

            except:
                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = "/home/" + domainName + "/public_html/" + path + "/"
                else:
                    finalPath = "/home/" + domainName + "/public_html/"

                if website.package.dataBases > website.databases_set.all().count():
                    pass
                else:
                    statusFile = open(tempStatusPath, 'w')
                    statusFile.writelines(
                        "Maximum database limit reached for this website." + " [404]")
                    statusFile.close()
                    return 0

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website)

            ## Security Check

            if finalPath.find("..") > -1:
                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines("Specified path must be inside virtual host home." + " [404]")
                statusFile.close()
                return 0

            if not os.path.exists(finalPath):
                command = 'sudo mkdir -p ' + finalPath
                ProcessUtilities.executioner(command, externalApp)

            ## checking for directories/files

            if self.dataLossCheck(finalPath, tempStatusPath) == 0:
                return 0

            ####

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Downloading and extracting PrestaShop Core..,30')
            statusFile.close()

            command = "sudo wget https://download.prestashop.com/download/releases/prestashop_1.7.4.2.zip -P %s" % (
                finalPath)
            ProcessUtilities.executioner(command, externalApp)

            command = "sudo unzip -o %sprestashop_1.7.4.2.zip -d " % (finalPath) + finalPath
            ProcessUtilities.executioner(command, externalApp)

            command = "sudo unzip -o %sprestashop.zip -d " % (finalPath) + finalPath
            ProcessUtilities.executioner(command, externalApp)

            ##

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Configuring the installation,40')
            statusFile.close()

            if home == '0':
                path = self.extraArgs['path']
                # finalURL = domainName + '/' + path
                finalURL = domainName
            else:
                finalURL = domainName

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Installing and configuring PrestaShop..,60')
            statusFile.close()

            command = "sudo php " + finalPath + "install/index_cli.php --domain=" + finalURL + \
                      " --db_server=localhost --db_name=" + dbName + " --db_user=" + dbUser + " --db_password=" + dbPassword \
                      + " --name='" + shopName + "' --firstname=" + firstName + " --lastname=" + lastName + \
                      " --email=" + email + " --password=" + password
            ProcessUtilities.executioner(command, externalApp)

            ##

            command = "sudo rm -rf " + finalPath + "install"
            ProcessUtilities.executioner(command, externalApp)

            ##

            command = "sudo chown -R " + externalApp + ":" + externalApp + " " + finalPath
            ProcessUtilities.executioner(command, externalApp)

            command = "sudo rm -f prestashop_1.7.4.2.zip"
            ProcessUtilities.executioner(command, externalApp)

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines("Successfully Installed. [200]")
            statusFile.close()
            return 0


        except BaseException as msg:
            # remove the downloaded files

            homeDir = "/home/" + domainName + "/public_html"

            if not os.path.exists(homeDir):
                command = "sudo chown -R " + externalApp + ":" + externalApp + " " + homeDir
                ProcessUtilities.executioner(command, externalApp)

            try:
                mysqlUtilities.deleteDatabase(dbName, dbUser)
                db = Databases.objects.get(dbName=dbName)
                db.delete()
            except:
                pass

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines(str(msg) + " [404]")
            statusFile.close()
            return 0

    def setupGit(self):
        try:
            admin = self.extraArgs['admin']
            domainName = self.extraArgs['domainName']
            username = self.extraArgs['username']
            reponame = self.extraArgs['reponame']
            branch = self.extraArgs['branch']
            tempStatusPath = self.extraArgs['tempStatusPath']
            defaultProvider = self.extraArgs['defaultProvider']

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Checking if GIT installed..,0')
            statusFile.close()

            ### Check git

            try:
                command = 'sudo git --help'
                output = ProcessUtilities.outputExecutioner(command)

                if output.find('command not found') > -1:
                    statusFile = open(tempStatusPath, 'w')
                    statusFile.writelines('Installing GIT..,0')
                    statusFile.close()
                    self.installGit()
                    statusFile = open(tempStatusPath, 'w')
                    statusFile.writelines('GIT successfully installed,20')
                    statusFile.close()
            except subprocess.CalledProcessError:
                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Installing GIT..,0')
                statusFile.close()
                self.installGit()
                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('GIT successfully installed.,20')
                statusFile.close()

            ## Open Status File

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Setting up directories..,20')
            statusFile.close()

            try:
                website = ChildDomains.objects.get(domain=domainName)
                externalApp = website.master.externalApp
                finalPath = website.path

            except:
                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp
                finalPath = "/home/" + domainName + "/public_html/"

            ## Security Check

            if finalPath.find("..") > -1:
                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines("Specified path must be inside virtual host home." + " [404]")
                statusFile.close()
                return 0

            command = 'sudo mkdir -p ' + finalPath
            ProcessUtilities.executioner(command, externalApp)

            ## checking for directories/files

            if self.dataLossCheck(finalPath, tempStatusPath) == 0:
                return 0

            ####

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Cloning the repo..,40')
            statusFile.close()

            try:
                command = 'git clone --depth 1 --no-single-branch git@' + defaultProvider + '.com:' + username + '/' + reponame + '.git -b ' + branch + ' ' + finalPath
                ProcessUtilities.executioner(command, externalApp)
            except subprocess.CalledProcessError as msg:
                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines(
                    'Failed to clone repository, make sure you deployed your key to repository. [404]')
                statusFile.close()
                return 0

            ##

            command = "sudo chown -R " + externalApp + ":" + externalApp + " " + finalPath
            ProcessUtilities.executioner(command, externalApp)

            vhost.addRewriteRules(domainName)
            installUtilities.reStartLiteSpeed()

            mailUtilities.checkHome()

            gitPath = '/home/cyberpanel/' + domainName + '.git'
            writeToFile = open(gitPath, 'w')
            writeToFile.write(username + ':' + reponame)
            writeToFile.close()

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines("GIT Repository successfully attached. [200]")
            statusFile.close()
            return 0


        except BaseException as msg:
            os.remove('/home/cyberpanel/' + domainName + '.git')
            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines(str(msg) + " [404]")
            statusFile.close()
            return 0

    def gitPull(self):
        try:
            domain = self.extraArgs['domain']

            try:
                website = Websites.objects.get(domain=domain)
                finalPath = "/home/" + domain + "/public_html/"
                externalApp = website.externalApp
            except:
                childDomain = ChildDomains.objects.get(domain=domain)
                finalPath = childDomain.path
                externalApp = website.externalApp

            path = '/home/cyberpanel/' + domain + '.git'

            if not os.path.exists(path):
                logging.writeToFile('Git is not setup for this website.')
                return 0

            command = 'sudo git --git-dir=' + finalPath + '.git --work-tree=' + finalPath + '  pull'
            ProcessUtilities.executioner(command, externalApp)

            ##

            website = Websites.objects.get(domain=domain)
            externalApp = website.externalApp

            command = "sudo chown -R " + externalApp + ":" + externalApp + " " + finalPath
            ProcessUtilities.executioner(command, externalApp)

            return 0


        except BaseException as msg:
            logging.writeToFile(str(msg) + " [ApplicationInstaller.gitPull]")
            return 0

    def detachRepo(self):
        try:
            domain = self.extraArgs['domainName']
            admin = self.extraArgs['admin']

            try:
                website = ChildDomains.objects.get(domain=domain)
                externalApp = website.master.externalApp


            except:
                website = Websites.objects.get(domain=domain)
                externalApp = website.externalApp

            try:
                website = Websites.objects.get(domain=domain)
                finalPath = "/home/" + domain + "/public_html/"
            except:
                childDomain = ChildDomains.objects.get(domain=domain)
                finalPath = childDomain.path

            command = 'sudo rm -rf ' + finalPath
            ProcessUtilities.executioner(command, website.externalApp)

            command = 'sudo mkdir ' + finalPath
            ProcessUtilities.executioner(command, website.externalApp)

            ##

            command = "sudo chown -R " + externalApp + ":" + externalApp + " " + finalPath
            ProcessUtilities.executioner(command, website.externalApp)

            gitPath = '/home/cyberpanel/' + domain + '.git'

            os.remove(gitPath)

            return 0


        except BaseException as msg:
            logging.writeToFile(str(msg) + " [ApplicationInstaller.gitPull]")
            return 0

    def installJoomla(self):

        try:

            domainName = self.extraArgs['domainName']
            finalPath = self.extraArgs['finalPath']
            virtualHostUser = self.extraArgs['virtualHostUser']
            dbName = self.extraArgs['dbName']
            dbUser = self.extraArgs['dbUser']
            dbPassword = self.extraArgs['dbPassword']
            username = self.extraArgs['username']
            password = self.extraArgs['password']
            prefix = self.extraArgs['prefix']
            sitename = self.extraArgs['sitename']
            tempStatusPath = self.extraArgs['tempStatusPath']

            FNULL = open(os.devnull, 'w')

            if not os.path.exists(finalPath):
                os.makedirs(finalPath)

            ## checking for directories/files

            if self.dataLossCheck(finalPath, tempStatusPath) == 0:
                return 0

            ## Get Joomla

            os.chdir(finalPath)

            if not os.path.exists("staging.zip"):
                command = 'wget --no-check-certificate https://github.com/joomla/joomla-cms/archive/staging.zip -P ' + finalPath
                ProcessUtilities.executioner(command, virtualHostUser)
            else:
                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines("File already exists." + " [404]")
                statusFile.close()
                return 0

            command = 'unzip ' + finalPath + 'staging.zip -d ' + finalPath
            ProcessUtilities.executioner(command, virtualHostUser)

            command = 'rm -f %s' % (finalPath + 'staging.zip')
            ProcessUtilities.executioner(command, virtualHostUser)

            command = 'cp -r ' + finalPath + 'joomla-cms-staging/. ' + finalPath
            ProcessUtilities.executioner(command, virtualHostUser)

            command = 'chown -R cyberpanel:cyberpanel %s' % (finalPath)
            ProcessUtilities.executioner(command)

            shutil.rmtree(finalPath + "joomla-cms-staging")
            os.rename(finalPath + "installation/configuration.php-dist", finalPath + "configuration.php")
            os.rename(finalPath + "robots.txt.dist", finalPath + "robots.txt")
            os.rename(finalPath + "htaccess.txt", finalPath + ".htaccess")

            ## edit config file

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Creating configuration files.,40')
            statusFile.close()

            configfile = finalPath + "configuration.php"

            data = open(configfile, "r").readlines()

            writeDataToFile = open(configfile, "w")

            secret = randomPassword.generate_pass()

            defDBName = "   public $user = '" + dbName + "';" + "\n"
            defDBUser = "   public $db = '" + dbUser + "';" + "\n"
            defDBPassword = "   public $password = '" + dbPassword + "';" + "\n"
            secretKey = "   public $secret = '" + secret + "';" + "\n"
            logPath = "   public $log_path = '" + finalPath + "administrator/logs';" + "\n"
            tmpPath = "   public $tmp_path = '" + finalPath + "administrator/tmp';" + "\n"
            dbprefix = "   public $dbprefix = '" + prefix + "';" + "\n"
            sitename = "   public $sitename = '" + sitename + "';" + "\n"

            for items in data:
                if items.find("public $user ") > -1:
                    writeDataToFile.writelines(defDBUser)
                elif items.find("public $password ") > -1:
                    writeDataToFile.writelines(defDBPassword)
                elif items.find("public $db ") > -1:
                    writeDataToFile.writelines(defDBName)
                elif items.find("public $log_path ") > -1:
                    writeDataToFile.writelines(logPath)
                elif items.find("public $tmp_path ") > -1:
                    writeDataToFile.writelines(tmpPath)
                elif items.find("public $secret ") > -1:
                    writeDataToFile.writelines(secretKey)
                elif items.find("public $dbprefix ") > -1:
                    writeDataToFile.writelines(dbprefix)
                elif items.find("public $sitename ") > -1:
                    writeDataToFile.writelines(sitename)
                elif items.find("/*") > -1:
                    pass
                elif items.find(" *") > -1:
                    pass
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Creating default user..,70')
            statusFile.close()

            # Rename SQL db prefix

            f1 = open(finalPath + 'installation/sql/mysql/joomla.sql', 'r')
            f2 = open(finalPath + 'installation/sql/mysql/joomlaInstall.sql', 'w')
            for line in f1:
                f2.write(line.replace('#__', prefix))
            f1.close()
            f2.close()

            # Restore SQL
            proc = subprocess.Popen(["mysql", "--user=%s" % dbUser, "--password=%s" % dbPassword, dbName],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE)

            usercreation = """INSERT INTO `%susers`
            (`name`, `username`, `password`, `params`)
            VALUES ('Administrator', '%s',
            '%s', '');
            INSERT INTO `%suser_usergroup_map` (`user_id`,`group_id`)
            VALUES (LAST_INSERT_ID(),'8');""" % (prefix, username, password, prefix)

            out, err = proc.communicate(
                open(finalPath + 'installation/sql/mysql/joomlaInstall.sql', 'rb').read() + ("\n" + usercreation).encode('utf-8'))

            shutil.rmtree(finalPath + "installation")

            command = "chown -R " + virtualHostUser + ":" + virtualHostUser + " " + finalPath
            ProcessUtilities.executioner(command)

            vhost.addRewriteRules(domainName)

            installUtilities.reStartLiteSpeedSocket()

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines("Successfully Installed. [200]")
            statusFile.close()
            return 0

        except BaseException as msg:
            # remove the downloaded files

            homeDir = "/home/" + domainName + "/public_html"

            if not os.path.exists(homeDir):
                command = "chown -R " + virtualHostUser + ":" + virtualHostUser + " " + homeDir
                ProcessUtilities.executioner(command)

            try:
                mysqlUtilities.deleteDatabase(dbName, dbUser)
                db = Databases.objects.get(dbName=dbName)
                db.delete()
            except:
                pass

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines(str(msg) + " [404]")
            statusFile.close()
            logging.writeToFile(str(msg))
            return 0

    def changeBranch(self):
        try:
            domainName = self.extraArgs['domainName']
            githubBranch = self.extraArgs['githubBranch']
            admin = self.extraArgs['admin']

            try:
                website = Websites.objects.get(domain=domainName)
                finalPath = "/home/" + domainName + "/public_html/"
                externalApp = website.externalApp
            except:
                childDomain = ChildDomains.objects.get(domain=domainName)
                finalPath = childDomain.path
                externalApp = childDomain.master.externalApp

            try:
                command = 'sudo git --git-dir=' + finalPath + '/.git  checkout -b ' + githubBranch
                ProcessUtilities.executioner(command, externalApp)
            except:
                try:
                    command = 'sudo git --git-dir=' + finalPath + '/.git  checkout ' + githubBranch
                    ProcessUtilities.executioner(command, externalApp)
                except subprocess.CalledProcessError as msg:
                    logging.writeToFile('Failed to change branch: ' + str(msg))
                    return 0
            return 0
        except BaseException as msg:
            logging.writeToFile('Failed to change branch: ' + str(msg))
            return 0

    def installMagento(self):
        try:

            username = self.extraArgs['username']
            domainName = self.extraArgs['domainName']
            home = self.extraArgs['home']
            firstName = self.extraArgs['firstName']
            lastName = self.extraArgs['lastName']
            email = self.extraArgs['email']
            password = self.extraArgs['password']
            tempStatusPath = self.extraArgs['tempStatusPath']
            sampleData = self.extraArgs['sampleData']

            FNULL = open(os.devnull, 'w')

            ## Open Status File

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Setting up paths,0')
            statusFile.close()

            finalPath = ''

            try:
                website = ChildDomains.objects.get(domain=domainName)
                externalApp = website.master.externalApp

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = website.path.rstrip('/') + "/" + path + "/"
                else:
                    finalPath = website.path + "/"

                if website.master.package.dataBases > website.master.databases_set.all().count():
                    pass
                else:
                    statusFile = open(tempStatusPath, 'w')
                    statusFile.writelines(
                        "Maximum database limit reached for this website." + " [404]")
                    statusFile.close()
                    return 0

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website.master)

            except:
                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp

                if home == '0':
                    path = self.extraArgs['path']
                    finalPath = "/home/" + domainName + "/public_html/" + path + "/"
                else:
                    finalPath = "/home/" + domainName + "/public_html/"

                if website.package.dataBases > website.databases_set.all().count():
                    pass
                else:
                    statusFile = open(tempStatusPath, 'w')
                    statusFile.writelines(
                        "Maximum database limit reached for this website." + " [404]")
                    statusFile.close()
                    return 0

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Setting up Database,20')
                statusFile.close()

                dbName, dbUser, dbPassword = self.dbCreation(tempStatusPath, website)

            ## Security Check

            if finalPath.find("..") > -1:
                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines("Specified path must be inside virtual host home." + " [404]")
                statusFile.close()
                return 0

            if not os.path.exists(finalPath):
                command = 'sudo mkdir -p ' + finalPath
                ProcessUtilities.executioner(command, externalApp)

            ## checking for directories/files

            if self.dataLossCheck(finalPath, tempStatusPath) == 0:
                return 0

            ####

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Downloading and extracting Magento Core..,30')
            statusFile.close()

            if sampleData:
                command = "sudo wget http://cyberpanelsh.b-cdn.net/latest-sample.tar.gz -P %s" % (finalPath)
            else:
                command = "sudo wget http://cyberpanelsh.b-cdn.net/latest.tar.gz -P %s" % (finalPath)

            ProcessUtilities.executioner(command, externalApp)

            if sampleData:
                command = 'tar -xf %slatest-sample.tar.gz --directory %s' % (finalPath, finalPath)
            else:
                command = 'tar -xf %slatest.tar.gz --directory %s' % (finalPath, finalPath)

            ProcessUtilities.executioner(command, externalApp)

            ##

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Configuring the installation,40')
            statusFile.close()

            if home == '0':
                path = self.extraArgs['path']
                # finalURL = domainName + '/' + path
                finalURL = domainName
            else:
                finalURL = domainName

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Installing and configuring Magento..,60')
            statusFile.close()

            command = '/usr/local/lsws/lsphp72/bin/php -d memory_limit=512M %sbin/magento setup:install --backend-frontname="admin" ' \
                      '--db-host="localhost" --db-name="%s" --db-user="%s" --db-password="%s" ' \
                      '--base-url="http://%s" --base-url-secure="https://%s/" --admin-user="%s" ' \
                      '--admin-password="%s" --admin-email="%s" --admin-firstname="%s" --admin-lastname="%s"' \
                      % (finalPath, dbName, dbUser, dbPassword, finalURL, finalURL, username, password, email, firstName, lastName)
            result = ProcessUtilities.outputExecutioner(command, externalApp)
            logging.writeToFile(result)

            ##

            if sampleData:
                command = 'rm -rf %slatest-sample.tar.gz' % (finalPath)
            else:
                command = 'rm -rf %slatest.tar.gz' % (finalPath)

            ProcessUtilities.executioner(command, externalApp)

            ##

            command = "sudo chown -R " + externalApp + ":" + externalApp + " " + finalPath
            ProcessUtilities.executioner(command, externalApp)

            installUtilities.reStartLiteSpeed()

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines("Successfully Installed. [200]")
            statusFile.close()
            return 0


        except BaseException as msg:
            # remove the downloaded files

            homeDir = "/home/" + domainName + "/public_html"

            if not os.path.exists(homeDir):
                command = "sudo chown -R " + externalApp + ":" + externalApp + " " + homeDir
                ProcessUtilities.executioner(command, externalApp)

            try:
                mysqlUtilities.deleteDatabase(dbName, dbUser)
                db = Databases.objects.get(dbName=dbName)
                db.delete()
            except:
                pass

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines(str(msg) + " [404]")
            statusFile.close()
            return 0
