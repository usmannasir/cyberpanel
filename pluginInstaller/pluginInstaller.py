import sys
sys.path.append('/usr/local/CyberCP')
import subprocess
import shlex
import argparse
import os
import shutil
import time
from plogical.processUtilities import ProcessUtilities

class pluginInstaller:
    installLogPath = "/home/cyberpanel/modSecInstallLog"
    tempRulesFile = "/home/cyberpanel/tempModSecRules"
    mirrorPath = "cyberpanel.net"

    @staticmethod
    def stdOut(message):
        print("\n\n")
        print(("[" + time.strftime(
            "%m.%d.%Y_%H-%M-%S") + "] #########################################################################\n"))
        print(("[" + time.strftime("%m.%d.%Y_%H-%M-%S") + "] " + message + "\n"))
        print(("[" + time.strftime(
            "%m.%d.%Y_%H-%M-%S") + "] #########################################################################\n"))

    @staticmethod
    def migrationsEnabled(pluginName: str) -> bool:
        pluginHome = '/usr/local/CyberCP/' + pluginName
        return os.path.exists(pluginHome + '/enable_migrations')

    ### Functions Related to plugin installation.

    @staticmethod
    def extractPlugin(pluginName):
        pathToPlugin = pluginName + '.zip'
        command = 'unzip ' + pathToPlugin + ' -d /usr/local/CyberCP'
        subprocess.call(shlex.split(command))

    @staticmethod
    def upgradingSettingsFile(pluginName):
        data = open("/usr/local/CyberCP/CyberCP/settings.py", 'r').readlines()
        writeToFile = open("/usr/local/CyberCP/CyberCP/settings.py", 'w')

        for items in data:
            if items.find("'emailPremium',") > -1:
                writeToFile.writelines(items)
                writeToFile.writelines("    '" + pluginName + "',\n")
            else:
                writeToFile.writelines(items)

        writeToFile.close()

    @staticmethod
    def upgradingURLs(pluginName):
        data = open("/usr/local/CyberCP/CyberCP/urls.py", 'r').readlines()
        writeToFile = open("/usr/local/CyberCP/CyberCP/urls.py", 'w')

        for items in data:
            if items.find("manageservices") > -1:
                writeToFile.writelines(items)
                writeToFile.writelines("    url(r'^" + pluginName + "/',include('" + pluginName + ".urls')),\n")
            else:
                writeToFile.writelines(items)

        writeToFile.close()

    @staticmethod
    def informCyberPanel(pluginName):
        pluginPath = '/home/cyberpanel/plugins'

        if not os.path.exists(pluginPath):
            os.mkdir(pluginPath)

        pluginFile = pluginPath + '/' + pluginName
        command = 'touch ' + pluginFile
        subprocess.call(shlex.split(command))

    @staticmethod
    def addInterfaceLink(pluginName):
        data = open("/usr/local/CyberCP/baseTemplate/templates/baseTemplate/index.html", 'r').readlines()
        writeToFile = open("/usr/local/CyberCP/baseTemplate/templates/baseTemplate/index.html", 'w')

        for items in data:
            if items.find("{# pluginsList #}") > -1:
                writeToFile.writelines(items)
                writeToFile.writelines("                                ")
                writeToFile.writelines(
                    '<li><a href="{% url \'' + pluginName + '\' %}" title="{% trans \'' + pluginName + '\' %}"><span>{% trans "' + pluginName + '" %}</span></a></li>\n')
            else:
                writeToFile.writelines(items)

        writeToFile.close()

    @staticmethod
    def staticContent():
        currentDir = os.getcwd()

        command = "rm -rf /usr/local/lscp/cyberpanel/static"
        subprocess.call(shlex.split(command))

        os.chdir('/usr/local/CyberCP')

        command = "/usr/local/CyberCP/bin/python manage.py collectstatic --noinput"
        subprocess.call(shlex.split(command))

        command = "mv /usr/local/CyberCP/static /usr/local/lscp/cyberpanel"
        subprocess.call(shlex.split(command))


        os.chdir(currentDir)

    @staticmethod
    def installMigrations(pluginName):
        currentDir = os.getcwd()
        os.chdir('/usr/local/CyberCP')
        command = "/usr/local/CyberCP/bin/python manage.py makemigrations %s" % pluginName
        subprocess.call(shlex.split(command))
        command = "/usr/local/CyberCP/bin/python manage.py migrate %s" % pluginName
        subprocess.call(shlex.split(command))
        os.chdir(currentDir)


    @staticmethod
    def preInstallScript(pluginName):
        pluginHome = '/usr/local/CyberCP/' + pluginName

        if os.path.exists(pluginHome + '/pre_install'):
            command = 'chmod +x ' + pluginHome + '/pre_install'
            subprocess.call(shlex.split(command))

            command = pluginHome + '/pre_install'
            subprocess.call(shlex.split(command))

    @staticmethod
    def postInstallScript(pluginName):
        pluginHome = '/usr/local/CyberCP/' + pluginName

        if os.path.exists(pluginHome + '/post_install'):
            command = 'chmod +x ' + pluginHome + '/post_install'
            subprocess.call(shlex.split(command))

            command = pluginHome + '/post_install'
            subprocess.call(shlex.split(command))

    @staticmethod
    def preRemoveScript(pluginName):
        pluginHome = '/usr/local/CyberCP/' + pluginName

        if os.path.exists(pluginHome + '/pre_remove'):
            command = 'chmod +x ' + pluginHome + '/pre_remove'
            subprocess.call(shlex.split(command))

            command = pluginHome + '/pre_remove'
            subprocess.call(shlex.split(command))


    @staticmethod
    def installPlugin(pluginName):
        try:
            ##

            pluginInstaller.stdOut('Extracting plugin..')
            pluginInstaller.extractPlugin(pluginName)
            pluginInstaller.stdOut('Plugin extracted.')

            ##

            pluginInstaller.stdOut('Executing pre_install script..')
            pluginInstaller.preInstallScript(pluginName)
            pluginInstaller.stdOut('pre_install executed.')

            ##

            pluginInstaller.stdOut('Restoring settings file.')
            pluginInstaller.upgradingSettingsFile(pluginName)
            pluginInstaller.stdOut('Settings file restored.')

            ##

            pluginInstaller.stdOut('Upgrading URLs')
            pluginInstaller.upgradingURLs(pluginName)
            pluginInstaller.stdOut('URLs upgraded.')

            ##

            pluginInstaller.stdOut('Informing CyberPanel about plugin.')
            pluginInstaller.informCyberPanel(pluginName)
            pluginInstaller.stdOut('CyberPanel core informed about the plugin.')

            ##

            pluginInstaller.stdOut('Adding interface link..')
            pluginInstaller.addInterfaceLink(pluginName)
            pluginInstaller.stdOut('Interface link added.')

            ##

            pluginInstaller.stdOut('Upgrading static content..')
            pluginInstaller.staticContent()
            pluginInstaller.stdOut('Static content upgraded.')

            ##

            if pluginInstaller.migrationsEnabled(pluginName):
                pluginInstaller.stdOut('Running Migrations..')
                pluginInstaller.installMigrations(pluginName)
                pluginInstaller.stdOut('Migrations Completed..')
            else:
                pluginInstaller.stdOut('Migrations not enabled, add file \'enable_migrations\' to plugin to enable')

            ##

            pluginInstaller.restartGunicorn()

            ##

            pluginInstaller.stdOut('Executing post_install script..')
            pluginInstaller.postInstallScript(pluginName)
            pluginInstaller.stdOut('post_install executed.')

            ##

            pluginInstaller.stdOut('Plugin successfully installed.')

        except BaseException as msg:
            pluginInstaller.stdOut(str(msg))

    ### Functions Related to plugin installation.

    @staticmethod
    def removeFiles(pluginName):
        pluginPath = '/usr/local/CyberCP/' + pluginName
        if os.path.exists(pluginPath):
            shutil.rmtree(pluginPath)

    @staticmethod
    def removeFromSettings(pluginName):
        data = open("/usr/local/CyberCP/CyberCP/settings.py", 'r').readlines()
        writeToFile = open("/usr/local/CyberCP/CyberCP/settings.py", 'w')

        for items in data:
            if items.find(pluginName) > -1:
                continue
            else:
                writeToFile.writelines(items)
        writeToFile.close()

    @staticmethod
    def removeFromURLs(pluginName):
        data = open("/usr/local/CyberCP/CyberCP/urls.py", 'r').readlines()
        writeToFile = open("/usr/local/CyberCP/CyberCP/urls.py", 'w')

        for items in data:
            if items.find(pluginName) > -1:
                continue
            else:
                writeToFile.writelines(items)

        writeToFile.close()

    @staticmethod
    def informCyberPanelRemoval(pluginName):
        pluginPath = '/home/cyberpanel/plugins'
        pluginFile = pluginPath + '/' + pluginName
        if os.path.exists(pluginFile):
            os.remove(pluginFile)

    @staticmethod
    def removeInterfaceLink(pluginName):
        data = open("/usr/local/CyberCP/baseTemplate/templates/baseTemplate/index.html", 'r').readlines()
        writeToFile = open("/usr/local/CyberCP/baseTemplate/templates/baseTemplate/index.html", 'w')

        for items in data:
            if items.find(pluginName) > -1 and items.find('<li>') > -1:
                continue
            else:
                writeToFile.writelines(items)
        writeToFile.close()

    @staticmethod
    def removeMigrations(pluginName):
        currentDir = os.getcwd()
        os.chdir('/usr/local/CyberCP')
        command = "/usr/local/CyberCP/bin/python manage.py migrate %s zero" % pluginName
        subprocess.call(shlex.split(command))
        os.chdir(currentDir)

    @staticmethod
    def removePlugin(pluginName):
        try:
            ##

            pluginInstaller.stdOut('Executing pre_remove script..')
            pluginInstaller.preRemoveScript(pluginName)
            pluginInstaller.stdOut('pre_remove executed.')

            ##

            if pluginInstaller.migrationsEnabled(pluginName):
                pluginInstaller.stdOut('Removing migrations..')
                pluginInstaller.removeMigrations(pluginName)
                pluginInstaller.stdOut('Migrations removed..')
            else:
                pluginInstaller.stdOut('Migrations not enabled, add file \'enable_migrations\' to plugin to enable')

            ##

            pluginInstaller.stdOut('Removing files..')
            pluginInstaller.removeFiles(pluginName)
            pluginInstaller.stdOut('Files removed..')

            ##

            pluginInstaller.stdOut('Restoring settings file.')
            pluginInstaller.removeFromSettings(pluginName)
            pluginInstaller.stdOut('Settings file restored.')

            ###

            pluginInstaller.stdOut('Upgrading URLs')
            pluginInstaller.removeFromURLs(pluginName)
            pluginInstaller.stdOut('URLs upgraded.')

            ##

            pluginInstaller.stdOut('Informing CyberPanel about plugin removal.')
            pluginInstaller.informCyberPanelRemoval(pluginName)
            pluginInstaller.stdOut('CyberPanel core informed about the plugin removal.')

            ##

            pluginInstaller.stdOut('Remove interface link..')
            pluginInstaller.removeInterfaceLink(pluginName)
            pluginInstaller.stdOut('Interface link removed.')

            ##

            pluginInstaller.restartGunicorn()

            pluginInstaller.stdOut('Plugin successfully removed.')

        except BaseException as msg:
            pluginInstaller.stdOut(str(msg))

    ####

    @staticmethod
    def restartGunicorn():
        command = 'systemctl restart lscpd'
        ProcessUtilities.normalExecutioner(command)




def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specify a function to call!')

    parser.add_argument('--pluginName', help='Temporary path to configurations data!')


    args = parser.parse_args()
    if args.function == 'install':
        pluginInstaller.installPlugin(args.pluginName)
    else:
        pluginInstaller.removePlugin(args.pluginName)

if __name__ == "__main__":
    main()