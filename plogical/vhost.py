#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django

from plogical.acl import ACLManager
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass
import shutil
from plogical import installUtilities

import subprocess
import shlex
from plogical import CyberCPLogFileWriter as logging
from plogical.mysqlUtilities import mysqlUtilities
from plogical.dnsUtilities import DNS
from random import randint
from plogical.processUtilities import ProcessUtilities
from managePHP.phpManager import PHPManager
from plogical.vhostConfs import vhostConfs
from ApachController.ApacheVhosts import ApacheVhost
try:
    from websiteFunctions.models import Websites, ChildDomains, aliasDomains, DockerSites, WPSites, WPStaging
    from databases.models import Databases
except:
    pass
import pwd
import grp

## If you want justice, you have come to the wrong place.


class vhost:

    Server_root = "/usr/local/lsws"
    cyberPanel = "/usr/local/CyberCP"
    redisConf = '/usr/local/lsws/conf/dvhost_redis.conf'

    @staticmethod
    def addUser(virtualHostUser, path):
        try:

            FNULL = open(os.devnull, 'w')
            if os.path.exists("/etc/lsb-release"):
                command = f'/usr/sbin/adduser --no-create-home --home {path} --disabled-login --gecos "" {virtualHostUser}'
            else:
                command = f"/usr/sbin/adduser {virtualHostUser} -M -d {path}"

            ProcessUtilities.executioner(command)

            command = f"/usr/sbin/groupadd {virtualHostUser}"
            ProcessUtilities.executioner(command)

            command = f"/usr/sbin/usermod -a -G {virtualHostUser} {virtualHostUser}"
            ProcessUtilities.executioner(command)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(f"{str(msg)} [addingUsers]")

    @staticmethod
    def createDirectories(path, virtualHostUser, pathHTML, pathLogs, confPath, completePathToConfigFile):
        try:
            FNULL = open(os.devnull, 'w')

            try:
                command = 'chmod 711 /home'
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)
            except:
                pass

            try:
                os.makedirs(path)

                command = f"chown {virtualHostUser}:{virtualHostUser} {path}"
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

                command = f"chmod 711 {path}"
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            except OSError as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [27 Not able create to directories for virtual host [createDirectories]]")
                #return [0, "[27 Not able to directories for virtual host [createDirectories]]"]

            try:
                os.makedirs(pathHTML)

                if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                    groupName = 'nobody'
                else:
                    groupName = 'nogroup'

                command = f"chown {virtualHostUser}:{groupName} {pathHTML}"
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

                command = f"chmod 750 {pathHTML}"
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            except OSError as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [33 Not able to directories for virtual host [createDirectories]]")
                #return [0, "[33 Not able to directories for virtual host [createDirectories]]"]

            try:
                os.makedirs(pathLogs)

                if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                    groupName = 'nobody'
                else:
                    groupName = 'nogroup'

                command = "chown %s:%s %s" % ('root', groupName, pathLogs)
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)


                if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                    command = f"chmod -R 750 {pathLogs}"
                else:
                    command = f"chmod -R 750 {pathLogs}"

                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            except OSError as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [39 Not able to directories for virtual host [createDirectories]]")
                #return [0, "[39 Not able to directories for virtual host [createDirectories]]"]

            try:
                ## For configuration files permissions will be changed later globally.
                if not os.path.exists(confPath):
                    os.makedirs(confPath)
            except OSError as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [45 Not able to directories for virtual host [createDirectories]]")
                #return [0, "[45 Not able to directories for virtual host [createDirectories]]"]

            try:
                ## For configuration files permissions will be changed later globally.
                file = open(completePathToConfigFile, "w+")

                command = "chown " + "lsadm" + ":" + "lsadm" + " " + completePathToConfigFile
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

                command = f'chmod 600 {completePathToConfigFile}'
                cmd = shlex.split(command)
                subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            except IOError as msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDirectories]]")
                #return [0, "[45 Not able to directories for virtual host [createDirectories]]"]

            return [1, 'None']

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createDirectories]")
            return [1, str(msg)]

    @staticmethod
    def finalizeVhostCreation(virtualHostName, virtualHostUser):
        try:

            FNULL = open(os.devnull, 'w')

            shutil.copy("/usr/local/CyberCP/index.html", f"/home/{virtualHostName}/public_html/index.html")

            command = f"chown {virtualHostUser}:{virtualHostUser} /home/{virtualHostName}/public_html/index.html"
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            vhostPath = f"{vhost.Server_root}/conf/vhosts"

            command = f"chown -R lsadm:lsadm {vhostPath}"
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [finalizeVhostCreation]")

    @staticmethod
    def createDirectoryForVirtualHost(virtualHostName,administratorEmail,virtualHostUser, phpVersion, openBasedir,
                                      memSoftLimit=2047, memHardLimit=2047, maxConnections=10,
                                      procSoftLimit=400, procHardLimit=500):

        if not os.path.exists('/usr/local/lsws/Example/html/.well-known/acme-challenge'):
            command = 'mkdir -p /usr/local/lsws/Example/html/.well-known/acme-challenge'
            ProcessUtilities.normalExecutioner(command)

        # Get user's home directory dynamically
        from userManagment.homeDirectoryUtils import HomeDirectoryUtils
        home_path = HomeDirectoryUtils.getUserHomeDirectory(virtualHostUser)
        if not home_path:
            home_path = "/home"  # Fallback to default
        
        path = os.path.join(home_path, virtualHostName)
        pathHTML = os.path.join(home_path, virtualHostName, "public_html")
        pathLogs = os.path.join(home_path, virtualHostName, "logs")
        confPath = vhost.Server_root + "/conf/vhosts/"+virtualHostName
        completePathToConfigFile = confPath +"/vhost.conf"


        ## adding user

        vhost.addUser(virtualHostUser, path)

        ## Creating Directories

        result = vhost.createDirectories(path, virtualHostUser, pathHTML, pathLogs, confPath, completePathToConfigFile)

        if result[0] == 0:
            return [0, result[1]]


        ## Creating Per vhost Configuration File


        if vhost.perHostVirtualConf(completePathToConfigFile,administratorEmail,virtualHostUser,phpVersion, virtualHostName, openBasedir,
                                    memSoftLimit, memHardLimit, maxConnections, procSoftLimit, procHardLimit) == 1:
            return [1,"None"]
        else:
            return [0,"[61 Not able to create per host virtual configurations [perHostVirtualConf]"]

    @staticmethod
    def perHostVirtualConf(vhFile, administratorEmail,virtualHostUser, phpVersion, virtualHostName, openBasedir,
                          memSoftLimit=2047, memHardLimit=2047, maxConnections=10,
                          procSoftLimit=400, procHardLimit=500):
        # General Configurations tab
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:

                confFile = open(vhFile, "w+")

                php = PHPManager.getPHPString(phpVersion)

                currentConf = vhostConfs.olsMasterConf
                currentConf = currentConf.replace('{adminEmails}', administratorEmail)
                currentConf = currentConf.replace('{virtualHostUser}', virtualHostUser)
                currentConf = currentConf.replace('{php}', php)
                currentConf = currentConf.replace('{adminEmails}', administratorEmail)
                currentConf = currentConf.replace('{php}', php)

                # Replace resource limits
                currentConf = currentConf.replace('{memSoftLimit}', str(memSoftLimit))
                currentConf = currentConf.replace('{memHardLimit}', str(memHardLimit))
                currentConf = currentConf.replace('{maxConnections}', str(maxConnections))
                currentConf = currentConf.replace('{procSoftLimit}', str(procSoftLimit))
                currentConf = currentConf.replace('{procHardLimit}', str(procHardLimit))

                if openBasedir == 1:
                    currentConf = currentConf.replace('{open_basedir}', 'php_admin_value open_basedir "/tmp:$VH_ROOT"')
                else:
                    currentConf = currentConf.replace('{open_basedir}', '')



                confFile.write(currentConf)
                confFile.close()

                return 1

            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [perHostVirtualConf]]")
                return 0
        else:
            try:

                if not os.path.exists(vhost.redisConf):
                    confFile = open(vhFile, "w+")
                    php = PHPManager.getPHPString(phpVersion)

                    currentConf = vhostConfs.lswsMasterConf

                    currentConf = currentConf.replace('{virtualHostName}', virtualHostName)
                    currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
                    currentConf = currentConf.replace('{externalApp}', virtualHostUser)
                    currentConf = currentConf.replace('{php}', php)

                    confFile.write(currentConf)

                    confFile.close()

                else:

                    ## Non-www

                    currentConf = vhostConfs.lswsRediConfMaster

                    currentConf = currentConf.replace('{virtualHostName}', virtualHostName)
                    currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
                    currentConf = currentConf.replace('{externalApp}', virtualHostUser)
                    currentConf = currentConf.replace('{php}', phpVersion.lstrip('PHP '))
                    currentConf = currentConf.replace('{uid}', str(pwd.getpwnam(virtualHostUser).pw_uid))
                    currentConf = currentConf.replace('{gid}', str(grp.getgrnam(virtualHostUser).gr_gid))

                    command = 'redis-cli set %s' % (currentConf)
                    ProcessUtilities.executioner(command)

                    ## WWW

                    currentConf = vhostConfs.lswsRediConfMasterWWW

                    currentConf = currentConf.replace('{virtualHostName}', 'www.%s' % (virtualHostName))
                    currentConf = currentConf.replace('{master}', virtualHostName)
                    currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
                    currentConf = currentConf.replace('{externalApp}', virtualHostUser)
                    currentConf = currentConf.replace('{php}', phpVersion.lstrip('PHP '))
                    currentConf = currentConf.replace('{uid}', str(pwd.getpwnam(virtualHostUser).pw_uid))
                    currentConf = currentConf.replace('{gid}', str(grp.getgrnam(virtualHostUser).gr_gid))

                    command = 'redis-cli set %s' % (currentConf)
                    ProcessUtilities.executioner(command)

                return 1

            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [perHostVirtualConf]]")
                return 0


    @staticmethod
    def createNONSSLMapEntry(virtualHostName):
        """Add NON-SSL map entry for virtualHostName in OLS httpd_config.conf.
        Returns (1, None) on success, (0, error_message) on failure.
        """
        try:
            def modify_config(lines):
                map_entry = "  map                     " + virtualHostName + " " + virtualHostName + "\n"
                modified = []
                mapchecker = 1
                line_lower = None
                for line in lines:
                    line_lower = line.lower()
                    # Match listener block: "listener Default" or "listener default" (case-insensitive)
                    if (mapchecker == 1 and "listener" in line_lower and "default" in line_lower):
                        modified.append(line)
                        modified.append(map_entry)
                        mapchecker = 0
                    else:
                        modified.append(line)
                if mapchecker != 0:
                    raise ValueError(
                        "Could not find Default listener block in /usr/local/lsws/conf/httpd_config.conf. "
                        "Ensure the file contains a line like 'listener Default {'."
                    )
                return modified

            success, error = installUtilities.installUtilities.safeModifyHttpdConfig(
                modify_config,
                f"Add NON-SSL map entry for {virtualHostName}"
            )

            if not success:
                error_msg = error if error else "Unknown error"
                logging.CyberCPLogFileWriter.writeToFile(f"[createNONSSLMapEntry] Failed: {error_msg}")
                return 0, error_msg

            return 1, None
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [createNONSSLMapEntry]")
            return 0, str(msg)

    @staticmethod
    def createConfigInMainVirtualHostFile(virtualHostName):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:
                success, error_msg = vhost.createNONSSLMapEntry(virtualHostName)
                if success != 1:
                    display_msg = error_msg or "Failed to create NON SSL Map Entry [createConfigInMainVirtualHostFile]"
                    return [0, display_msg]

                currentConf = vhostConfs.olsMasterMainConf
                currentConf = currentConf.replace('{virtualHostName}', virtualHostName)
                ok, err = installUtilities.installUtilities.appendProtectedHttpdConfigBlock(
                    currentConf, 'Append master vhost block for %s' % virtualHostName)
                if not ok:
                    return [0, err or 'Failed to append master vhost block to httpd_config.conf']

                return [1,"None"]
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + "223 [IO Error with main config file [createConfigInMainVirtualHostFile]]")
                return [0,"223 [IO Error with main config file [createConfigInMainVirtualHostFile]]"]
        else:
            try:
                writeDataToFile = open("/usr/local/lsws/conf/httpd.conf", 'a')
                configFile = 'Include /usr/local/lsws/conf/vhosts/' + virtualHostName + '/vhost.conf\n'
                writeDataToFile.writelines(configFile)
                writeDataToFile.close()

                writeDataToFile.close()
                return [1, "None"]
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + "223 [IO Error with main config file [createConfigInMainVirtualHostFile]]")
                return [0, "223 [IO Error with main config file [createConfigInMainVirtualHostFile]]"]

    @staticmethod
    def deleteVirtualHostConfigurations(virtualHostName):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:

                ## Deleting master conf
                numberOfSites = str(Websites.objects.count() + ChildDomains.objects.count())
                vhost.deleteCoreConf(virtualHostName, numberOfSites)

                delWebsite = Websites.objects.get(domain=virtualHostName)
                externalApp = delWebsite.externalApp

                # Get admin user name for CloudFlare cleanup
                adminUserName = None
                try:
                    adminUserName = delWebsite.admin.userName
                except:
                    pass

                ##

                databases = Databases.objects.filter(website=delWebsite)

                childDomains = delWebsite.childdomains_set.all()

                ## Deleting child domains

                for items in childDomains:
                    numberOfSites = Websites.objects.count() + ChildDomains.objects.count()
                    vhost.deleteCoreConf(items.domain, numberOfSites)

                    # Delete CloudFlare and local DNS records for child domain
                    try:
                        DNS.cleanupHostDNSRecords(items.domain, adminUserName)
                    except Exception as cfError:
                        # Log error but don't fail deletion if CloudFlare deletion fails
                        logging.CyberCPLogFileWriter.writeToFile(
                            f'CloudFlare DNS deletion failed for child domain {items.domain}: {str(cfError)}')

                    ### Delete ACME Folder

                    if os.path.exists('/root/.acme.sh/%s' % (items.domain)):
                        shutil.rmtree('/root/.acme.sh/%s' % (items.domain))

                ## Child check, to make sure no database entires are being deleted from child node

                if ACLManager.FindIfChild() == 0:

                    ### Delete WordPress Sites and Staging Sites first
                    try:
                        wpSites = WPSites.objects.filter(owner=delWebsite)
                        for wpSite in wpSites:
                            # Delete any staging sites associated with this WP site
                            stagingSites = WPStaging.objects.filter(wpsite=wpSite)
                            for staging in stagingSites:
                                staging.delete()
                                logging.CyberCPLogFileWriter.writeToFile(f"Deleted staging site record: {staging.id}")
                            # Delete the WP site itself
                            wpSite.delete()
                            logging.CyberCPLogFileWriter.writeToFile(f"Deleted WP site: {wpSite.id}")
                    except Exception as msg:
                        logging.CyberCPLogFileWriter.writeToFile(f"Error cleaning up WP/Staging sites: {str(msg)}")

                    ### Delete Docker Sites first before website deletion

                    if os.path.exists('/home/docker/%s' % (virtualHostName)):
                        try:
                            dockerSite = DockerSites.objects.get(admin__domain=virtualHostName)
                            passdata = {
                                "domain": virtualHostName,
                                "name": dockerSite.SiteName
                            }
                            from plogical.DockerSites import Docker_Sites
                            da = Docker_Sites(None, passdata)
                            da.DeleteDockerApp()
                            dockerSite.delete()
                        except:
                            # If anything fails in Docker cleanup, at least remove the directory
                            shutil.rmtree('/home/docker/%s' % (virtualHostName))

                    for items in databases:
                        mysqlUtilities.deleteDatabase(items.dbName, items.dbUser)

                    # Delete CloudFlare and local DNS records for main domain before deletion
                    try:
                        DNS.cleanupHostDNSRecords(virtualHostName, adminUserName)
                    except Exception as cfError:
                        # Log error but don't fail deletion if CloudFlare deletion fails
                        logging.CyberCPLogFileWriter.writeToFile(
                            f'CloudFlare DNS deletion failed for {virtualHostName}: {str(cfError)}')

                    delWebsite.delete()

                    ## Deleting DNS Zone if there is any.

                    DNS.deleteDNSZone(virtualHostName)

                if not os.path.exists(vhost.redisConf):
                    installUtilities.installUtilities.reStartLiteSpeed()

                ## Delete mail accounts

                command = "rm -rf /home/vmail/" + virtualHostName
                subprocess.call(shlex.split(command))

                ##

                if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                    command = 'userdel -r -f %s' % (externalApp)
                else:
                    command = 'deluser %s' % (externalApp)

                ProcessUtilities.executioner(command)

                #

                command = 'groupdel %s' % (externalApp)
                ProcessUtilities.executioner(command)

                ## Remove git conf folder if present

                gitPath = '/home/cyberpanel/git/%s' % (virtualHostName)

                if os.path.exists(gitPath):
                    shutil.rmtree(gitPath)

                ## Remove resource limits for this user (OLS cgroups)
                try:
                    from plogical.resourceLimits import resource_manager
                    resource_manager.remove_user_limits(externalApp)
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Warning: Failed to remove resource limits for user {externalApp}: {str(e)}")

                ### Delete Acme folder

                if os.path.exists('/root/.acme.sh/%s' % (virtualHostName)):
                    shutil.rmtree('/root/.acme.sh/%s' % (virtualHostName))

            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Not able to remove virtual host configuration from main configuration file.]")
                return 0
            return 1
        else:
            try:
                ## Deleting master conf
                numberOfSites = str(Websites.objects.count() + ChildDomains.objects.count())
                vhost.deleteCoreConf(virtualHostName, numberOfSites)

                delWebsite = Websites.objects.get(domain=virtualHostName)
                externalApp = delWebsite.externalApp

                ## Cagefs

                command = '/usr/sbin/cagefsctl --disable %s' % (delWebsite.externalApp)
                ProcessUtilities.normalExecutioner(command)

                databases = Databases.objects.filter(website=delWebsite)

                childDomains = delWebsite.childdomains_set.all()

                ## Deleting child domains

                for items in childDomains:
                    numberOfSites = Websites.objects.count() + ChildDomains.objects.count()
                    vhost.deleteCoreConf(items.domain, numberOfSites)


                ## child check to make sure no database entires are being deleted from child server

                if ACLManager.FindIfChild() == 0:
                    ### Delete WordPress Sites and Staging Sites first
                    try:
                        wpSites = WPSites.objects.filter(owner=delWebsite)
                        for wpSite in wpSites:
                            # Delete any staging sites associated with this WP site
                            stagingSites = WPStaging.objects.filter(wpsite=wpSite)
                            for staging in stagingSites:
                                staging.delete()
                                logging.CyberCPLogFileWriter.writeToFile(f"Deleted staging site record: {staging.id}")
                            # Delete the WP site itself
                            wpSite.delete()
                            logging.CyberCPLogFileWriter.writeToFile(f"Deleted WP site: {wpSite.id}")
                    except Exception as msg:
                        logging.CyberCPLogFileWriter.writeToFile(f"Error cleaning up WP/Staging sites: {str(msg)}")

                    for items in databases:
                        mysqlUtilities.deleteDatabase(items.dbName, items.dbUser)

                    delWebsite.delete()

                    ## Deleting DNS Zone if there is any.

                    DNS.deleteDNSZone(virtualHostName)

                installUtilities.installUtilities.reStartLiteSpeed()

                ## Delete mail accounts

                command = "rm -rf /home/vmail/" + virtualHostName
                subprocess.call(shlex.split(command))

                ##

                if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                    command = 'userdel -r -f %s' % (externalApp)
                else:
                    command = 'deluser %s' % (externalApp)

                ProcessUtilities.executioner(command)

                #

                command = 'groupdel %s' % (externalApp)
                ProcessUtilities.executioner(command)
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [Not able to remove virtual host configuration from main configuration file.]")
                return 0
            return 1

    @staticmethod
    def deleteCoreConf(virtualHostName, numberOfSites):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:

                virtualHostPath = "/home/" + virtualHostName
                if os.path.exists(virtualHostPath):
                    shutil.rmtree(virtualHostPath)

                confPath = vhost.Server_root + "/conf/vhosts/" + virtualHostName
                if os.path.exists(confPath):
                    shutil.rmtree(confPath)

                def modify_config(lines):
                    """Remove virtual host entries from config"""
                    modified = []
                    check = 1
                    sslCheck = 1

                    for line in lines:
                        if numberOfSites == 1:
                            if (line.find(' ' + virtualHostName) > -1 and line.find("  map                     " + virtualHostName) > -1):
                                continue
                            if (line.find(' ' + virtualHostName) > -1 and (line.find("virtualHost") > -1 or line.find("virtualhost") > -1)):
                                check = 0
                            if line.find("listener") > -1 and line.find("SSL") > -1:
                                sslCheck = 0
                            if (check == 1 and sslCheck == 1):
                                modified.append(line)
                            if (line.find("}") > -1 and (check == 0 or sslCheck == 0)):
                                check = 1
                                sslCheck = 1
                        else:
                            if (line.find(' ' + virtualHostName) > -1 and line.find("  map                     " + virtualHostName) > -1):
                                continue
                            if (line.find(' ' + virtualHostName) > -1 and (line.find("virtualHost") > -1 or line.find("virtualhost") > -1)):
                                check = 0
                            if (check == 1):
                                modified.append(line)
                            if (line.find("}") > -1 and check == 0):
                                check = 1
                    
                    return modified
                
                # Use safe modification with backup and validation
                success, error = installUtilities.installUtilities.safeModifyHttpdConfig(
                    modify_config,
                    f"Remove virtual host {virtualHostName} from config"
                )
                
                if not success:
                    error_msg = error if error else "Unknown error"
                    logging.writeToFile(f"[deleteCoreConf] Failed to remove vhost config: {error_msg}")
                    raise BaseException(f"Failed to remove vhost config: {error_msg}")

                ## Delete Apache Conf

                ApacheVhost.DeleteApacheVhost(virtualHostName)

            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [Not able to remove virtual host configuration from main configuration file.]")
                return 0
            return 1
        else:
            virtualHostPath = "/home/" + virtualHostName
            try:
                shutil.rmtree(virtualHostPath)
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [Not able to remove virtual host directory from /home continuing..]")

            if not os.path.exists(vhost.redisConf):
                try:
                    confPath = vhost.Server_root + "/conf/vhosts/" + virtualHostName
                    shutil.rmtree(confPath)
                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile(
                        str(msg) + " [Not able to remove virtual host configuration directory from /conf ]")

                try:
                    data = open("/usr/local/lsws/conf/httpd.conf").readlines()

                    writeDataToFile = open("/usr/local/lsws/conf/httpd.conf", 'w')

                    for items in data:
                        if items.find('/' + virtualHostName + '/') > -1:
                            pass
                        else:
                            writeDataToFile.writelines(items)

                    writeDataToFile.close()

                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile(
                        str(msg) + " [Not able to remove virtual host configuration from main configuration file.]")
                    return 0
                return 1
            else:
                command = 'redis-cli delete "vhost:%s"' % (virtualHostName)
                ProcessUtilities.executioner(command)

                command = 'redis-cli delete "vhost:www.%s"' % (virtualHostName)
                ProcessUtilities.executioner(command)

    @staticmethod
    def checkIfVirtualHostExists(virtualHostName):
        if os.path.exists("/home/" + virtualHostName):
            return 1
        return 0

    @staticmethod
    def changePHP(vhFile, phpVersion):

        from pathlib import Path
        domain = vhFile.split('/')[6]
        print(domain)
        try:
            website = Websites.objects.get(domain=domain)
            externalApp = website.externalApp
        except:
            child = ChildDomains.objects.get(domain=domain)
            externalApp = child.master.externalApp
        #HomePath = website.externalApp
        virtualHostUser = externalApp

        logging.CyberCPLogFileWriter.writeToFile(f"PHP version before making sure its available or not: {phpVersion} and vhFile: {vhFile}")

        from plogical.phpUtilities import phpUtilities

        phpVersion = phpUtilities.FindIfSaidPHPIsAvaiableOtherwiseMaketheNextOneAvailableToUse(None, phpVersion)

        phpDetachUpdatePath = '/home/%s/.lsphp_restart.txt' % (vhFile.split('/')[-2])
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:
                if ApacheVhost.changePHP(phpVersion, vhFile) == 0:
                    data = open(vhFile, "r").readlines()

                    php = PHPManager.getPHPString(phpVersion)

                    if not os.path.exists("/usr/local/lsws/lsphp" + str(php) + "/bin/lsphp"):
                        print(0, 'This PHP version is not available on your CyberPanel.')
                        return [0, "[This PHP version is not available on your CyberPanel. [changePHP]"]

                    writeDataToFile = open(vhFile, "w")

                    path = "  path                    /usr/local/lsws/lsphp" + str(php) + "/bin/lsphp\n"

                    logging.CyberCPLogFileWriter.writeToFile(f"PHP String to be written {path}")

                    for items in data:
                        if items.find("/usr/local/lsws/lsphp") > -1 and items.find("path") > -1:
                            writeDataToFile.writelines(path)
                        else:
                            writeDataToFile.writelines(items)

                    writeDataToFile.close()

                    command = 'sudo -u %s touch %s' % (virtualHostUser, phpDetachUpdatePath)
                    ProcessUtilities.normalExecutioner(command)

                    installUtilities.installUtilities.reStartLiteSpeed()
                    try:
                        command = 'sudo -u %s rm -f %s' % (virtualHostUser, phpDetachUpdatePath)
                        ProcessUtilities.normalExecutioner(command)
                    except:
                        pass
                else:
                    logging.CyberCPLogFileWriter.writeToFile('apache vhost 1')

                    php = PHPManager.getPHPString(phpVersion)

                    phpService = ApacheVhost.DecideFPMServiceName(phpVersion)

                    command = f"systemctl restart {phpService}"
                    ProcessUtilities.normalExecutioner(command)

                print("1,None")
                return 1,'None'
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [changePHP]")
                print(0,str(msg))
                return [0, str(msg) + " [IO Error with per host config file [changePHP]"]
        else:
            try:
                if not os.path.exists(vhost.redisConf):
                    data = open(vhFile, "r").readlines()

                    php = PHPManager.getPHPString(phpVersion)

                    if not os.path.exists("/usr/local/lsws/lsphp" + str(php) + "/bin/lsphp"):
                        print(0, 'This PHP version is not available on your CyberPanel.')
                        return [0, "[This PHP version is not available on your CyberPanel. [changePHP]"]

                    writeDataToFile = open(vhFile, "w")

                    finalString = '    AddHandler application/x-httpd-php' + str(php) + ' .php\n'

                    for items in data:
                        if items.find("AddHandler application/x-httpd") > -1:
                            writeDataToFile.writelines(finalString)
                        else:
                            writeDataToFile.writelines(items)

                    writeDataToFile.close()

                    writeToFile = open(phpDetachUpdatePath, 'w')
                    writeToFile.close()

                    installUtilities.installUtilities.reStartLiteSpeed()
                    try:
                        os.remove(phpDetachUpdatePath)
                    except:
                        pass
                else:
                    command = 'redis-cli get "vhost:%s"' % (vhFile.split('/')[-2])
                    configData = ProcessUtilities.outputExecutioner(command)

                    import re
                    configData = re.sub(r'"phpVersion": .*,', '"phpVersion": %s,' % (phpVersion.lstrip('PHP ')), configData)

                    command = "redis-cli set vhost:%s '%s'" % (vhFile.split('/')[-2], configData)
                    ProcessUtilities.executioner(command)


                print("1,None")
                return 1, 'None'
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [changePHP]]")
                print(0, str(msg))
                return [0, str(msg) + " [IO Error with per host config file [changePHP]]"]

    @staticmethod
    def addRewriteRules(virtualHostName, fileName=None):
        try:
            pass
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [IO Error with per host config file [changePHP]]")
            return 0

        return 1

    @staticmethod
    def checkIfRewriteEnabled(data):
        try:
            for items in data:
                if items.find(".htaccess") > -1:
                    return 1
            return 0

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [IO Error with per host config file [checkIfRewriteEnabled]]")
            return 0

    @staticmethod
    def findDomainBW(domainName, totalAllowed):
        try:
            path = "/home/" + domainName + "/logs/" + domainName + ".access_log"

            if not os.path.exists("/home/" + domainName + "/logs"):
                print("0,0")
                return 0,0

            bwmeta = "/home/cyberpanel/%s.bwmeta" % (domainName)

            if not os.path.exists(path):
                print("0,0")
                return 0, 0

            if os.path.exists(bwmeta):
                try:
                    data = open(bwmeta).readlines()
                    currentUsed = int(data[0].strip("\n"))

                    inMB = int(float(currentUsed) / (1024.0 * 1024.0))

                    if totalAllowed == 0:
                        totalAllowed = 999999

                    percentage = float(100) / float(totalAllowed)
                    percentage = float(percentage) * float(inMB)
                except:
                    print("0,0")
                    return 0, 0

                if percentage > 100.0:
                    percentage = 100

                print(str(inMB) + "," + str(percentage))
                return str(inMB), str(percentage)
            else:
                print("0,0")
                return 0, 0
        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [findDomainBW]")
            print("0,0")
            return 0, 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [findDomainBW]")
            print("0,0")
            return 0, 0

    @staticmethod
    def permissionControl(path):
        try:
            command = 'sudo chown -R  cyberpanel:cyberpanel ' + path
            cmd = shlex.split(command)
            res = subprocess.call(cmd)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def leaveControl(path):
        try:
            command = 'sudo chown -R  root:root ' + path

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))

    @staticmethod
    def checkIfAliasExists(aliasDomain):
        try:
            alias = aliasDomains.objects.get(aliasDomain=aliasDomain)
            return 1
        except BaseException as msg:
            return 0

    @staticmethod
    def checkIfSSLAliasExists(data, aliasDomain):
        try:
            for items in data:
                if items.strip(',').strip('\n') == aliasDomain:
                    return 1
            return 0

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [checkIfSSLAliasExists]")
            return 1

    @staticmethod
    def createAliasSSLMap(confPath, masterDomain, aliasDomain):
        try:

            data = open(confPath, 'r').readlines()
            writeToFile = open(confPath, 'w')
            sslCheck = 0


            for items in data:
                if (items.find("listener SSL") > -1):
                    sslCheck = 1
                if items.find(masterDomain) > -1 and items.find('map') > -1 and sslCheck == 1:
                    data = [_f for _f in items.split(" ") if _f]
                    if data[1] == masterDomain:
                        if vhost.checkIfSSLAliasExists(data, aliasDomain) == 0:
                            writeToFile.writelines(items.rstrip('\n') + ", " + aliasDomain + "\n")
                            sslCheck = 0
                        else:
                            writeToFile.writelines(items)
                else:
                    writeToFile.writelines(items)

            writeToFile.close()
            installUtilities.installUtilities.reStartLiteSpeed()

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "  [createAliasSSLMap]")

    ## Child Domain Functions

    @staticmethod
    def finalizeDomainCreation(virtualHostUser, path):
        try:

            ACLManager.CreateSecureDir()

            RanddomFileName = str(randint(1000, 9999))

            FullPath = '%s/%s' % ('/usr/local/CyberCP/tmp', RanddomFileName)

            FNULL = open(os.devnull, 'w')

            #shutil.copy("/usr/local/CyberCP/index.html", path + "/index.html")

            shutil.copy("/usr/local/CyberCP/index.html", FullPath)

            command = "chown " + virtualHostUser + ":" + virtualHostUser + " " + FullPath
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

            command = 'sudo -u %s cp %s %s/index.html' % (virtualHostUser, FullPath, path)
            ProcessUtilities.normalExecutioner(command)

            os.remove(FullPath)

            vhostPath = vhost.Server_root + "/conf/vhosts"
            command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + vhostPath
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [finalizeDomainCreation]")

    @staticmethod
    def createDirectoryForDomain(masterDomain, domain, phpVersion, path, administratorEmail, virtualHostUser,
                                 openBasedir, memSoftLimit=2047, memHardLimit=2047, maxConnections=10,
                                 procSoftLimit=400, procHardLimit=500):

        FNULL = open(os.devnull, 'w')

        confPath = vhost.Server_root + "/conf/vhosts/" + domain
        completePathToConfigFile = confPath + "/vhost.conf"

        try:

            command = 'mkdir -p %s' % shlex.quote(path)
            ProcessUtilities.executioner(command, None, True)

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                groupName = 'nobody'
            else:
                groupName = 'nogroup'

            command = 'chown %s:%s %s' % (virtualHostUser, groupName, shlex.quote(path))
            ProcessUtilities.executioner(command, None, True)

            command = "chmod 750 %s" % shlex.quote(path)
            ProcessUtilities.executioner(command, None, True)

            # Create .well-known/acme-challenge so LiteSpeed config validation does not fail (path must exist)
            acme_path = path.rstrip('/') + '/.well-known/acme-challenge'
            try:
                command = 'mkdir -p %s' % shlex.quote(acme_path)
                ProcessUtilities.executioner(command, None, True)
                command = "chmod 755 %s" % shlex.quote(acme_path)
                ProcessUtilities.executioner(command, None, True)
            except Exception as acme_err:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(acme_err) + " [createDirectoryForDomain acme-challenge]")

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + "329 [Not able to create directories for virtual host [createDirectoryForDomain]]")
            return [0, str(msg)]

        command = 'mkdir -p %s' % shlex.quote(confPath)
        if ProcessUtilities.executioner(command, None, True) != 1:
            err_msg = 'Could not create vhost config directory: %s' % confPath
            logging.CyberCPLogFileWriter.writeToFile(err_msg + ' [createDirectoryForDomain]')
            return [0, err_msg]

        if vhost.perHostDomainConf(path, masterDomain, domain, completePathToConfigFile,
                                   administratorEmail, phpVersion, virtualHostUser, openBasedir,
                                   memSoftLimit, memHardLimit, maxConnections, procSoftLimit, procHardLimit) == 1:
            return [1, "None"]

        return [0, 'Could not create per-host virtual host configuration [createDirectoryForDomain]']

    @staticmethod
    def perHostDomainConf(path, masterDomain, domain, vhFile, administratorEmail, phpVersion, virtualHostUser, openBasedir,
                         memSoftLimit=2047, memHardLimit=2047, maxConnections=10,
                         procSoftLimit=400, procHardLimit=500):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:
                php = PHPManager.getPHPString(phpVersion)
                externalApp = virtualHostUser + str(randint(1000, 9999))

                currentConf = vhostConfs.olsChildConf
                currentConf = currentConf.replace('{path}', path)
                currentConf = currentConf.replace('{masterDomain}', masterDomain)
                currentConf = currentConf.replace('{virtualHostName}', domain)
                currentConf = currentConf.replace('{adminEmails}', administratorEmail)
                currentConf = currentConf.replace('{externalApp}', externalApp)
                currentConf = currentConf.replace('{externalAppMaster}', virtualHostUser)
                currentConf = currentConf.replace('{php}', php)
                currentConf = currentConf.replace('{adminEmails}', administratorEmail)
                currentConf = currentConf.replace('{php}', php)

                # Replace resource limits (child domains share parent's limits)
                currentConf = currentConf.replace('{memSoftLimit}', str(memSoftLimit))
                currentConf = currentConf.replace('{memHardLimit}', str(memHardLimit))
                currentConf = currentConf.replace('{maxConnections}', str(maxConnections))
                currentConf = currentConf.replace('{procSoftLimit}', str(procSoftLimit))
                currentConf = currentConf.replace('{procHardLimit}', str(procHardLimit))

                if openBasedir == 1:
                    currentConf = currentConf.replace('{open_basedir}', 'php_admin_value open_basedir "/tmp:$VH_ROOT"')
                else:
                    currentConf = currentConf.replace('{open_basedir}', '')
                
                # Ensure log directory exists in master domain's home directory
                masterLogDir = f"/home/{masterDomain}/logs"
                try:
                    if not os.path.exists(masterLogDir):
                        ProcessUtilities.executioner('mkdir -p %s' % shlex.quote(masterLogDir), None, True)
                        command = f"chown -R {virtualHostUser}:{virtualHostUser} {shlex.quote(masterLogDir)}"
                        ProcessUtilities.executioner(command, None, True)
                    
                    # Create empty log files for the child domain
                    error_log_path = f"{masterLogDir}/{domain}.error_log"
                    access_log_path = f"{masterLogDir}/{domain}.access_log"
                    
                    for log_path in [error_log_path, access_log_path]:
                        if not os.path.exists(log_path):
                            ProcessUtilities.executioner('touch %s' % shlex.quote(log_path), None, True)
                            command = f"chown {virtualHostUser}:{virtualHostUser} {shlex.quote(log_path)}"
                            ProcessUtilities.executioner(command, None, True)
                            command = f"chmod 644 {shlex.quote(log_path)}"
                            ProcessUtilities.executioner(command, None, True)
                except Exception as logErr:
                    logging.CyberCPLogFileWriter.writeToFile(
                        f'Error creating log files for child domain {domain}: {str(logErr)}')

                conf_lines = [currentConf if currentConf.endswith('\n') else currentConf + '\n']
                ok, err = installUtilities.installUtilities._writeProtectedConfigLines(vhFile, conf_lines)
                if not ok:
                    logging.CyberCPLogFileWriter.writeToFile(
                        '%s [IO Error with per host config file [perHostDomainConf]]' % (err or 'write failed'))
                    return 0

            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [perHostDomainConf]]")
                return 0
            return 1
        else:
            try:

                if not os.path.exists(vhost.redisConf):
                    confFile = open(vhFile, "w+")
                    php = PHPManager.getPHPString(phpVersion)

                    currentConf = vhostConfs.lswsChildConf

                    currentConf = currentConf.replace('{virtualHostName}', domain)
                    currentConf = currentConf.replace('{masterDomain}', masterDomain)
                    currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
                    currentConf = currentConf.replace('{externalApp}', virtualHostUser)
                    currentConf = currentConf.replace('{path}', path)
                    currentConf = currentConf.replace('{php}', php)

                    confFile.write(currentConf)

                    confFile.close()
                    
                    # Ensure log directory exists in master domain's home directory and create log files
                    masterLogDir = f"/home/{masterDomain}/logs"
                    try:
                        if not os.path.exists(masterLogDir):
                            os.makedirs(masterLogDir, exist_ok=True)
                            command = f"chown -R {virtualHostUser}:{virtualHostUser} {masterLogDir}"
                            ProcessUtilities.executioner(command)
                        
                        # Create empty log files for the child domain
                        error_log_path = f"{masterLogDir}/{domain}.error_log"
                        access_log_path = f"{masterLogDir}/{domain}.access_log"
                        
                        for log_path in [error_log_path, access_log_path]:
                            if not os.path.exists(log_path):
                                with open(log_path, 'w') as f:
                                    f.write('')
                                command = f"chown {virtualHostUser}:{virtualHostUser} {log_path}"
                                ProcessUtilities.executioner(command)
                                command = f"chmod 644 {log_path}"
                                ProcessUtilities.executioner(command)
                    except Exception as logErr:
                        logging.CyberCPLogFileWriter.writeToFile(
                            f'Error creating log files for child domain {domain}: {str(logErr)}')

                else:

                    ## Non www

                    currentConf = vhostConfs.lswsRediConfChild

                    currentConf = currentConf.replace('{virtualHostName}', domain)
                    currentConf = currentConf.replace('{masterDomain}', masterDomain)
                    currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
                    currentConf = currentConf.replace('{path}', path)
                    currentConf = currentConf.replace('{externalApp}', virtualHostUser)
                    currentConf = currentConf.replace('{php}', phpVersion.lstrip('PHP '))
                    currentConf = currentConf.replace('{uid}', str(pwd.getpwnam(virtualHostUser).pw_uid))
                    currentConf = currentConf.replace('{gid}', str(grp.getgrnam(virtualHostUser).gr_gid))

                    command = 'redis-cli set %s' % (currentConf)
                    ProcessUtilities.executioner(command)
                    
                    # Ensure log directory exists in master domain's home directory and create log files
                    masterLogDir = f"/home/{masterDomain}/logs"
                    try:
                        if not os.path.exists(masterLogDir):
                            os.makedirs(masterLogDir, exist_ok=True)
                            command = f"chown -R {virtualHostUser}:{virtualHostUser} {masterLogDir}"
                            ProcessUtilities.executioner(command)
                        
                        # Create empty log files for the child domain (non-www)
                        access_log_path = f"{masterLogDir}/{domain}.access_log"
                        
                        if not os.path.exists(access_log_path):
                            with open(access_log_path, 'w') as f:
                                f.write('')
                            command = f"chown {virtualHostUser}:{virtualHostUser} {access_log_path}"
                            ProcessUtilities.executioner(command)
                            command = f"chmod 644 {access_log_path}"
                            ProcessUtilities.executioner(command)
                    except Exception as logErr:
                        logging.CyberCPLogFileWriter.writeToFile(
                            f'Error creating log files for child domain {domain} (redis non-www): {str(logErr)}')

                    ## www

                    currentConf = vhostConfs.lswsRediConfChildWWW

                    currentConf = currentConf.replace('{virtualHostName}', 'www.%s' % (domain))
                    currentConf = currentConf.replace('{masterDomain}', masterDomain)
                    currentConf = currentConf.replace('{administratorEmail}', administratorEmail)
                    currentConf = currentConf.replace('{path}', path)
                    currentConf = currentConf.replace('{externalApp}', virtualHostUser)
                    currentConf = currentConf.replace('{php}', phpVersion.lstrip('PHP '))
                    currentConf = currentConf.replace('{uid}', str(pwd.getpwnam(virtualHostUser).pw_uid))
                    currentConf = currentConf.replace('{gid}', str(grp.getgrnam(virtualHostUser).gr_gid))

                    command = 'redis-cli set %s' % (currentConf)
                    ProcessUtilities.executioner(command)
                    
                    # Note: Log files already created for non-www version above
                    # The www version shares the same log files

            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + " [IO Error with per host config file [perHostDomainConf]]")
                return 0
            return 1


    @staticmethod
    def createConfigInMainDomainHostFile(domain, masterDomain):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            try:
                success, error_msg = vhost.createNONSSLMapEntry(domain)
                if success != 1:
                    display_msg = error_msg or "Failed to create NON SSL Map Entry [createConfigInMainVirtualHostFile]"
                    return [0, display_msg]

                currentConf = vhostConfs.olsChildMainConf
                currentConf = currentConf.replace('{virtualHostName}', domain)
                currentConf = currentConf.replace('{masterDomain}', masterDomain)
                ok, err = installUtilities.installUtilities.appendProtectedHttpdConfigBlock(
                    currentConf, 'Append child vhost block for %s' % domain)
                if not ok:
                    return [0, err or 'Failed to append child vhost block to httpd_config.conf']

                return [1, "None"]

            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + "223 [IO Error with main config file [createConfigInMainDomainHostFile]]")
                return [0, "223 [IO Error with main config file [createConfigInMainDomainHostFile]]"]
        else:
            try:
                writeDataToFile = open("/usr/local/lsws/conf/httpd.conf", 'a')
                configFile = 'Include /usr/local/lsws/conf/vhosts/' + domain + '/vhost.conf\n'
                writeDataToFile.writelines(configFile)
                writeDataToFile.close()
                return [1, "None"]
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(
                    str(msg) + "223 [IO Error with main config file [createConfigInMainDomainHostFile]]")
                return [0, "223 [IO Error with main config file [createConfigInMainDomainHostFile]]"]
