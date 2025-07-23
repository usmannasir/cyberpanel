import requests

from plogical import CyberCPLogFileWriter as logging
import os
import shlex
import subprocess
import socket
from plogical.processUtilities import ProcessUtilities
try:
    from websiteFunctions.models import ChildDomains, Websites
except:
    pass
from plogical.acl import ACLManager


class sslUtilities:

    Server_root = "/usr/local/lsws"
    redisConf = '/usr/local/lsws/conf/dvhost_redis.conf'
    
    @staticmethod
    def checkDNSRecords(domain):
        """Check if domain has valid DNS records using external DNS query"""
        try:
            # Use dig command to check DNS records from authoritative servers
            command = f"dig +short {domain} A @8.8.8.8"
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
            except TypeError:
                # Fallback for Python < 3.7
                result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            # If there's any output, the domain has A records
            if result.stdout.strip():
                return True
            
            # Also check AAAA records
            command = f"dig +short {domain} AAAA @8.8.8.8"
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
            except TypeError:
                # Fallback for Python < 3.7
                result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            if result.stdout.strip():
                return True
                
            return False
        except:
            # Fallback to socket method if dig fails
            try:
                socket.gethostbyname(domain)
                return True
            except:
                return False

    DONT_ISSUE = 0
    ISSUE_SELFSIGNED = 1
    ISSUE_SSL = 2

    @staticmethod
    def getDomainsCovered(cert_path):
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            with open(cert_path, 'rb') as cert_file:
                cert_data = cert_file.read()
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())

                # Check for the Subject Alternative Name (SAN) extension
                san_extension = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)

                if san_extension:
                    # Extract and print the domains from SAN
                    san_domains = san_extension.value.get_values_for_type(x509.DNSName)
                    try:
                        logging.CyberCPLogFileWriter.writeToFile(f'Covered domains: {str(san_domains)}')
                    except:
                        pass
                    return 1, san_domains
                else:
                    # If SAN is not present, return the Common Name as a fallback
                    return 0, None
        except BaseException as msg:
            return 0, str(msg)


    @staticmethod
    def CheckIfSSLNeedsToBeIssued(virtualHostName):
        #### if website already have an SSL, better not issue again - need to check for wild-card
        filePath = '/etc/letsencrypt/live/%s/fullchain.pem' % (virtualHostName)
        if os.path.exists(filePath):
            import OpenSSL
            x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open(filePath, 'r').read())
            SSLProvider = x509.get_issuer().get_components()[1][1].decode('utf-8')

            if os.path.exists(ProcessUtilities.debugPath):
                logging.CyberCPLogFileWriter.writeToFile(f'SSL provider for {virtualHostName} is {SSLProvider}.')


            #### totally seprate check to see if both non-www and www are covered

            if SSLProvider == "(STAGING) Let's Encrypt":
                return sslUtilities.ISSUE_SSL

            if SSLProvider == "Let's Encrypt":
                status, domains = sslUtilities.getDomainsCovered(filePath)
                if status:
                    if len(domains) > 1:
                        ### need further checks here to see if ssl is valid for less then 15 days etc
                        logging.CyberCPLogFileWriter.writeToFile(
                            '[CheckIfSSLNeedsToBeIssued] SSL exists for %s and both versions are covered, just need to ensure if SSL is valid for less then 15 days.' % (virtualHostName), 0)
                        pass
                    else:
                        return sslUtilities.ISSUE_SSL

            #####

            expireData = x509.get_notAfter().decode('ascii')
            from datetime import datetime
            finalDate = datetime.strptime(expireData, '%Y%m%d%H%M%SZ')
            now = datetime.now()
            diff = finalDate - now

            if int(diff.days) >= 15 and SSLProvider!='Denial':
                logging.CyberCPLogFileWriter.writeToFile(
                    '[CheckIfSSLNeedsToBeIssued] SSL exists for %s and is not ready to fetch new SSL., skipping..' % (
                        virtualHostName), 0)

                return sslUtilities.DONT_ISSUE
            elif SSLProvider == 'Denial':
                logging.CyberCPLogFileWriter.writeToFile(
                    f'[CheckIfSSLNeedsToBeIssued] Self-signed SSL found, lets issue new SSL for {virtualHostName}', 0)
                return sslUtilities.ISSUE_SSL
            elif SSLProvider != "Let's Encrypt":
                logging.CyberCPLogFileWriter.writeToFile(
                    f'[CheckIfSSLNeedsToBeIssued] Custom SSL found for {virtualHostName}', 0)
                return sslUtilities.DONT_ISSUE
            else:
                logging.CyberCPLogFileWriter.writeToFile(
                    f'[CheckIfSSLNeedsToBeIssued] We will issue SSL for {virtualHostName}', 0)
                return sslUtilities.ISSUE_SSL
        else:
            logging.CyberCPLogFileWriter.writeToFile(
                f'[CheckIfSSLNeedsToBeIssued] We will issue SSL for {virtualHostName}', 0)
            return sslUtilities.ISSUE_SSL

    @staticmethod
    def checkIfSSLMap(virtualHostName):
        try:
            data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()

            sslCheck = 0

            for items in data:
                if items.find("listener") > - 1 and items.find("SSL") > -1:
                    sslCheck = 1
                    continue
                if sslCheck == 1:
                    if items.find("}") > -1:
                        return 0
                if items.find(virtualHostName) > -1 and sslCheck == 1:
                    data = [_f for _f in items.split(" ") if _f]
                    if data[1] == virtualHostName:
                        return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [IO Error with main config file [checkIfSSLMap]]")
            return 0

    @staticmethod
    def checkSSLListener():
        try:
            data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()
            for items in data:
                if items.find("listener SSL") > -1:
                    return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [IO Error with main config file [checkSSLListener]]")
            return str(msg)
        return 0
    
 
    @staticmethod
    def checkSSLIPv6Listener():
        try:
            data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()
            for items in data:
                if items.find("listener SSL IPv6") > -1:
                    return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [IO Error with main config file [checkSSLIPv6Listener]]")
            return str(msg)
        return 0

    @staticmethod
    def getDNSRecords(virtualHostName):
        try:

            withoutWWW = socket.gethostbyname(virtualHostName)
            withWWW = socket.gethostbyname('www.' + virtualHostName)

            return [1, withWWW, withoutWWW]

        except BaseException as msg:
            return [0, "347 " + str(msg) + " [issueSSLForDomain]"]

    @staticmethod
    def PatchVhostConf(virtualHostName):
        """Patch the virtual host configuration to add ACME challenge support
        
        This function adds the necessary configuration to handle ACME challenges
        for both OpenLiteSpeed (OLS) and Apache configurations. It also checks
        for potential configuration conflicts before making changes.
        
        Args:
            virtualHostName (str): The domain name to configure
            
        Returns:
            tuple: (status, message) where status is 1 for success, 0 for failure
        """
        try:
            # Construct paths
            confPath = os.path.join(sslUtilities.Server_root, "conf", "vhosts", virtualHostName)
            completePathToConfigFile = os.path.join(confPath, "vhost.conf")
            
            # Check if file exists
            if not os.path.exists(completePathToConfigFile):
                logging.CyberCPLogFileWriter.writeToFile(f'Configuration file not found: {completePathToConfigFile}')
                return 0, f'Configuration file not found: {completePathToConfigFile}'
            
            # Read current configuration
            try:
                with open(completePathToConfigFile, 'r') as f:
                    DataVhost = f.read()
            except IOError as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Error reading configuration file: {str(e)}')
                return 0, f'Error reading configuration file: {str(e)}'
            
            # Check for potential conflicts
            conflicts = []
            
            # Check if ACME challenge is already configured
            if DataVhost.find('/.well-known/acme-challenge') != -1:
                logging.CyberCPLogFileWriter.writeToFile(f'ACME challenge already configured for {virtualHostName}')
                return 1, 'ACME challenge already configured'
            
            # Check for conflicting rewrite rules
            if DataVhost.find('rewrite') != -1 and DataVhost.find('enable 1') != -1:
                conflicts.append('Active rewrite rules found that might interfere with ACME challenges')
            
            # Check for conflicting location blocks
            if DataVhost.find('location /.well-known') != -1:
                conflicts.append('Existing location block for /.well-known found')
            
            # Check for conflicting aliases
            if DataVhost.find('Alias /.well-known') != -1:
                conflicts.append('Existing alias for /.well-known found')
            
            # Check for conflicting context blocks
            if DataVhost.find('context /.well-known') != -1:
                conflicts.append('Existing context block for /.well-known found')
            
            # Check for conflicting access controls
            if DataVhost.find('deny from all') != -1 and DataVhost.find('location') != -1:
                conflicts.append('Global deny rules found that might block ACME challenges')
            
            # If conflicts found, log them and return
            if conflicts:
                conflict_message = 'Configuration conflicts found: ' + '; '.join(conflicts)
                logging.CyberCPLogFileWriter.writeToFile(f'Configuration conflicts for {virtualHostName}: {conflict_message}')
                return 0, conflict_message
            
            # Create challenge directory if it doesn't exist
            challenge_dir = '/usr/local/lsws/Example/html/.well-known/acme-challenge'
            try:
                os.makedirs(challenge_dir, exist_ok=True)
                # Set proper permissions
                os.chmod(challenge_dir, 0o755)
            except OSError as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Error creating challenge directory: {str(e)}')
                return 0, f'Error creating challenge directory: {str(e)}'
            
            # Handle configuration based on server type
            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                # OpenLiteSpeed configuration
                try:
                    with open(completePathToConfigFile, 'a') as f:
                        content = '''
context /.well-known/acme-challenge {
  location                /usr/local/lsws/Example/html/.well-known/acme-challenge
  allowBrowse             1
  rewrite  {
     enable                  0
  }
  addDefaultCharset       off
  phpIniOverride  {
  }
}
'''
                        f.write(content)
                except IOError as e:
                    logging.CyberCPLogFileWriter.writeToFile(f'Error writing OLS configuration: {str(e)}')
                    return 0, f'Error writing OLS configuration: {str(e)}'
            else:
                # Apache configuration
                try:
                    # Read current configuration
                    with open(completePathToConfigFile, 'r') as f:
                        lines = f.readlines()
                    
                    # Write new configuration
                    with open(completePathToConfigFile, 'w') as f:
                        check = 0
                        for line in lines:
                            f.write(line)
                            if line.find('DocumentRoot /home/') > -1 and check == 0:
                                f.write('    Alias /.well-known/acme-challenge /usr/local/lsws/Example/html/.well-known/acme-challenge\n')
                                check = 1
                except IOError as e:
                    logging.CyberCPLogFileWriter.writeToFile(f'Error writing Apache configuration: {str(e)}')
                    return 0, f'Error writing Apache configuration: {str(e)}'
            
            # Restart LiteSpeed
            try:
                from plogical import installUtilities
                installUtilities.installUtilities.reStartLiteSpeed()
                logging.CyberCPLogFileWriter.writeToFile(f'Successfully configured ACME challenge for {virtualHostName}')
                return 1, 'Successfully configured ACME challenge'
            except Exception as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Error restarting LiteSpeed: {str(e)}')
                return 0, f'Error restarting LiteSpeed: {str(e)}'
                
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Unexpected error in PatchVhostConf: {str(e)}')
            return 0, f'Unexpected error: {str(e)}'

    @staticmethod
    def installSSLForDomain(virtualHostName, adminEmail='example@example.org'):

        try:
            website = Websites.objects.get(domain=virtualHostName)
            adminEmail = website.adminEmail
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile('%s [installSSLForDomain:72]' % (str(msg)))

        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            confPath = sslUtilities.Server_root + "/conf/vhosts/" + virtualHostName
            completePathToConfigFile = confPath + "/vhost.conf"

            try:
                map = "  map                     " + virtualHostName + " " + virtualHostName + "\n"

                if sslUtilities.checkSSLListener() != 1:

                    writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'a')

                    listener = "listener SSL {" + "\n"
                    address = "  address                 *:443" + "\n"
                    secure = "  secure                  1" + "\n"
                    keyFile = "  keyFile                  /etc/letsencrypt/live/" + virtualHostName + "/privkey.pem\n"
                    certFile = "  certFile                 /etc/letsencrypt/live/" + virtualHostName + "/fullchain.pem\n"
                    certChain = "  certChain               1" + "\n"
                    sslProtocol = "  sslProtocol             24" + "\n"
                    enableECDHE = "  enableECDHE             1" + "\n"
                    renegProtection = "  renegProtection         1" + "\n"
                    sslSessionCache = "  sslSessionCache         1" + "\n"
                    enableSpdy = "  enableSpdy              15" + "\n"
                    enableStapling = "  enableStapling           1" + "\n"
                    ocspRespMaxAge = "  ocspRespMaxAge           86400" + "\n"
                    map = "  map                     " + virtualHostName + " " + virtualHostName + "\n"
                    final = "}" + "\n" + "\n"

                    writeDataToFile.writelines("\n")
                    writeDataToFile.writelines(listener)
                    writeDataToFile.writelines(address)
                    writeDataToFile.writelines(secure)
                    writeDataToFile.writelines(keyFile)
                    writeDataToFile.writelines(certFile)
                    writeDataToFile.writelines(certChain)
                    writeDataToFile.writelines(sslProtocol)
                    writeDataToFile.writelines(enableECDHE) 
                    writeDataToFile.writelines(renegProtection)
                    writeDataToFile.writelines(sslSessionCache)
                    writeDataToFile.writelines(enableSpdy)
                    writeDataToFile.writelines(enableStapling)
                    writeDataToFile.writelines(ocspRespMaxAge)
                    writeDataToFile.writelines(map)
                    writeDataToFile.writelines(final)
                    writeDataToFile.writelines("\n")
                    writeDataToFile.close()

                elif sslUtilities.checkSSLIPv6Listener() != 1:

                    writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'a')

                    listener = "listener SSL IPv6 {" + "\n"
                    address = "  address                 [ANY]:443" + "\n"
                    secure = "  secure                  1" + "\n"
                    keyFile = "  keyFile                  /etc/letsencrypt/live/" + virtualHostName + "/privkey.pem\n"
                    certFile = "  certFile                 /etc/letsencrypt/live/" + virtualHostName + "/fullchain.pem\n"
                    certChain = "  certChain               1" + "\n"
                    sslProtocol = "  sslProtocol             24" + "\n"
                    enableECDHE = "  enableECDHE             1" + "\n"
                    renegProtection = "  renegProtection         1" + "\n"
                    sslSessionCache = "  sslSessionCache         1" + "\n"
                    enableSpdy = "  enableSpdy              15" + "\n"
                    enableStapling = "  enableStapling           1" + "\n"
                    ocspRespMaxAge = "  ocspRespMaxAge           86400" + "\n"
                    map = "  map                     " + virtualHostName + " " + virtualHostName + "\n"
                    final = "}" + "\n" + "\n"

                    writeDataToFile.writelines("\n")
                    writeDataToFile.writelines(listener)
                    writeDataToFile.writelines(address)
                    writeDataToFile.writelines(secure)
                    writeDataToFile.writelines(keyFile)
                    writeDataToFile.writelines(certFile)
                    writeDataToFile.writelines(certChain)
                    writeDataToFile.writelines(sslProtocol)
                    writeDataToFile.writelines(enableECDHE) 
                    writeDataToFile.writelines(renegProtection)
                    writeDataToFile.writelines(sslSessionCache)
                    writeDataToFile.writelines(enableSpdy)
                    writeDataToFile.writelines(enableStapling)
                    writeDataToFile.writelines(ocspRespMaxAge)
                    writeDataToFile.writelines(map)
                    writeDataToFile.writelines(final)
                    writeDataToFile.writelines("\n")
                    writeDataToFile.close()

                else:

                    if sslUtilities.checkIfSSLMap(virtualHostName) == 0:

                        data = open("/usr/local/lsws/conf/httpd_config.conf").readlines()
                        writeDataToFile = open("/usr/local/lsws/conf/httpd_config.conf", 'w')
                        sslCheck = 0

                        for items in data:
                            if items.find("listener") > -1 and items.find("SSL") > -1:
                                sslCheck = 1

                            if (sslCheck == 1):
                                writeDataToFile.writelines(items)
                                writeDataToFile.writelines(map)
                                sslCheck = 0
                            else:
                                writeDataToFile.writelines(items)
                        writeDataToFile.close()

                    ###################### Write per host Configs for SSL ###################

                    data = open(completePathToConfigFile, "r").readlines()

                    ## check if vhssl is already in vhconf file

                    vhsslPresense = 0

                    for items in data:
                        if items.find("vhssl") > -1:
                            vhsslPresense = 1

                    if vhsslPresense == 0:
                        writeSSLConfig = open(completePathToConfigFile, "a")

                        vhssl = "vhssl  {" + "\n"
                        keyFile = "  keyFile                 /etc/letsencrypt/live/" + virtualHostName + "/privkey.pem\n"
                        certFile = "  certFile                /etc/letsencrypt/live/" + virtualHostName + "/fullchain.pem\n"
                        certChain = "  certChain               1" + "\n"
                        sslProtocol = "  sslProtocol             24" + "\n"
                        enableECDHE = "  enableECDHE             1" + "\n"
                        renegProtection = "  renegProtection         1" + "\n"
                        sslSessionCache = "  sslSessionCache         1" + "\n"
                        enableSpdy = "  enableSpdy              15" + "\n"
                        enableStapling = "  enableStapling           1" + "\n"
                        ocspRespMaxAge = "  ocspRespMaxAge           86400" + "\n"
                        final = "}"

                        writeSSLConfig.writelines("\n")

                        writeSSLConfig.writelines(vhssl)
                        writeSSLConfig.writelines(keyFile)
                        writeSSLConfig.writelines(certFile)
                        writeSSLConfig.writelines(certChain)
                        writeSSLConfig.writelines(sslProtocol)
                        writeSSLConfig.writelines(enableECDHE)
                        writeSSLConfig.writelines(renegProtection)
                        writeSSLConfig.writelines(sslSessionCache)
                        writeSSLConfig.writelines(enableSpdy)
                        writeSSLConfig.writelines(enableStapling)
                        writeSSLConfig.writelines(ocspRespMaxAge)
                        writeSSLConfig.writelines(final)

                        writeSSLConfig.writelines("\n")

                        writeSSLConfig.close()

                return 1
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installSSLForDomain]]")
                return 0
        else:
            if not os.path.exists(sslUtilities.redisConf):
                confPath = sslUtilities.Server_root + "/conf/vhosts/" + virtualHostName
                completePathToConfigFile = confPath + "/vhost.conf"

                ## Check if SSL VirtualHost already exists

                data = open(completePathToConfigFile, 'r').readlines()

                for items in data:
                    if items.find('*:443') > -1:
                        return 1

                try:

                    try:
                        chilDomain = ChildDomains.objects.get(domain=virtualHostName)
                        externalApp = chilDomain.master.externalApp
                        DocumentRoot = '    DocumentRoot ' + chilDomain.path + '\n'
                    except BaseException as msg:
                        website = Websites.objects.get(domain=virtualHostName)
                        externalApp = website.externalApp
                        docRoot = ACLManager.FindDocRootOfSite(None, virtualHostName)
                        DocumentRoot = f'    DocumentRoot {docRoot}\n'

                    data = open(completePathToConfigFile, 'r').readlines()
                    phpHandler = ''

                    for items in data:
                        if items.find('AddHandler') > -1 and items.find('php') > -1:
                            phpHandler = items
                            break

                    confFile = open(completePathToConfigFile, 'a')

                    cacheRoot = """    <IfModule LiteSpeed>
            CacheRoot lscache
            CacheLookup on
        </IfModule>
    """

                    VirtualHost = '\n<VirtualHost *:443>\n\n'
                    ServerName = '    ServerName ' + virtualHostName + '\n'
                    ServerAlias = '    ServerAlias www.' + virtualHostName + '\n'
                    ServerAdmin = '    ServerAdmin ' + adminEmail + '\n'
                    SeexecUserGroup = '    SuexecUserGroup ' + externalApp + ' ' + externalApp + '\n'
                    CustomLogCombined = '    CustomLog /home/' + virtualHostName + '/logs/' + virtualHostName + '.access_log combined\n'

                    confFile.writelines(VirtualHost)
                    confFile.writelines(ServerName)
                    confFile.writelines(ServerAlias)
                    confFile.writelines(ServerAdmin)
                    confFile.writelines(SeexecUserGroup)
                    confFile.writelines(DocumentRoot)
                    confFile.writelines(CustomLogCombined)
                    confFile.writelines(cacheRoot)

                    SSLEngine = '    SSLEngine on\n'
                    SSLVerifyClient = '    SSLVerifyClient none\n'
                    SSLCertificateFile = '    SSLCertificateFile /etc/letsencrypt/live/' + virtualHostName + '/fullchain.pem\n'
                    SSLCertificateKeyFile = '    SSLCertificateKeyFile /etc/letsencrypt/live/' + virtualHostName + '/privkey.pem\n'

                    confFile.writelines(SSLEngine)
                    confFile.writelines(SSLVerifyClient)
                    confFile.writelines(SSLCertificateFile)
                    confFile.writelines(SSLCertificateKeyFile)
                    confFile.writelines(phpHandler)

                    VirtualHostEnd = '</VirtualHost>\n'
                    confFile.writelines(VirtualHostEnd)
                    confFile.close()
                    return 1
                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [installSSLForDomain]")
                    return 0
            else:
                cert = open('/etc/letsencrypt/live/' + virtualHostName + '/fullchain.pem').read().rstrip('\n')
                key = open('/etc/letsencrypt/live/' + virtualHostName + '/privkey.pem', 'r').read().rstrip('\n')
                command = 'redis-cli hmset "ssl:%s" crt "%s" key "%s"' % (virtualHostName, cert, key)
                logging.CyberCPLogFileWriter.writeToFile('hello world aaa')
                logging.CyberCPLogFileWriter.writeToFile(command)
                ProcessUtilities.executioner(command)
                return 1

    @staticmethod
    def obtainSSLForADomain(virtualHostName, adminEmail, sslpath, aliasDomain=None, isHostname=False):
        from plogical.acl import ACLManager
        from plogical.sslv2 import sslUtilities as sslv2
        from plogical.customACME import CustomACME
        import json
        import socket

        Status = 1

        if sslUtilities.CheckIfSSLNeedsToBeIssued(virtualHostName) == sslUtilities.ISSUE_SSL:
            pass
        else:
            return 1

        sender_email = 'root@%s' % (socket.gethostname())

        sslUtilities.PatchVhostConf(virtualHostName)

        if not os.path.exists('/usr/local/lsws/Example/html/.well-known/acme-challenge'):
            command = f'mkdir -p /usr/local/lsws/Example/html/.well-known/acme-challenge'
            ProcessUtilities.normalExecutioner(command)

        command = f'chmod -R 755 /usr/local/lsws/Example/html'
        ProcessUtilities.executioner(command)

        # Try Let's Encrypt first
        try:
            # Start with just the main domain
            domains = [virtualHostName]
            
            # Check if www subdomain has DNS records before adding it (skip for hostnames)
            if not isHostname and sslUtilities.checkDNSRecords(f'www.{virtualHostName}'):
                domains.append(f'www.{virtualHostName}')
                logging.CyberCPLogFileWriter.writeToFile(f"www.{virtualHostName} has DNS records, including in SSL request")
            elif not isHostname:
                logging.CyberCPLogFileWriter.writeToFile(f"www.{virtualHostName} has no DNS records, excluding from SSL request")
            
            if aliasDomain:
                domains.append(aliasDomain)
                # Check if www.aliasDomain has DNS records
                if sslUtilities.checkDNSRecords(f'www.{aliasDomain}'):
                    domains.append(f'www.{aliasDomain}')
                    logging.CyberCPLogFileWriter.writeToFile(f"www.{aliasDomain} has DNS records, including in SSL request")
                else:
                    logging.CyberCPLogFileWriter.writeToFile(f"www.{aliasDomain} has no DNS records, excluding from SSL request")
            
            # Check if Cloudflare is used
            use_dns = False
            try:
                website = Websites.objects.get(domain=virtualHostName)
                if website.externalApp == 'cloudflare':
                    use_dns = True
            except:
                pass
            
            acme = CustomACME(virtualHostName, adminEmail, staging=False, provider='letsencrypt')
            if acme.issue_certificate(domains, use_dns=use_dns):
                logging.CyberCPLogFileWriter.writeToFile(
                    f"Successfully obtained SSL using Let's Encrypt for: {virtualHostName}")
                return 1
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(
                f"Let's Encrypt failed: {str(e)}. Trying ZeroSSL...")

        # Try ZeroSSL if Let's Encrypt fails
        try:
            # Start with just the main domain
            domains = [virtualHostName]
            
            # Check if www subdomain has DNS records before adding it (skip for hostnames)
            if not isHostname and sslUtilities.checkDNSRecords(f'www.{virtualHostName}'):
                domains.append(f'www.{virtualHostName}')
                logging.CyberCPLogFileWriter.writeToFile(f"www.{virtualHostName} has DNS records, including in SSL request")
            elif not isHostname:
                logging.CyberCPLogFileWriter.writeToFile(f"www.{virtualHostName} has no DNS records, excluding from SSL request")
            
            if aliasDomain:
                domains.append(aliasDomain)
                # Check if www.aliasDomain has DNS records
                if sslUtilities.checkDNSRecords(f'www.{aliasDomain}'):
                    domains.append(f'www.{aliasDomain}')
                    logging.CyberCPLogFileWriter.writeToFile(f"www.{aliasDomain} has DNS records, including in SSL request")
                else:
                    logging.CyberCPLogFileWriter.writeToFile(f"www.{aliasDomain} has no DNS records, excluding from SSL request")
            
            acme = CustomACME(virtualHostName, adminEmail, staging=False, provider='zerossl')
            if acme.issue_certificate(domains, use_dns=use_dns):
                logging.CyberCPLogFileWriter.writeToFile(
                    f"Successfully obtained SSL using ZeroSSL for: {virtualHostName}")
                return 1
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(
                f"ZeroSSL failed: {str(e)}. Falling back to acme.sh")

        # Fallback to acme.sh if both ACME providers fail
        try:
            acmePath = '/root/.acme.sh/acme.sh'
            command = '%s --register-account -m %s' % (acmePath, adminEmail)
            subprocess.call(shlex.split(command))

            command = '%s --set-default-ca --server letsencrypt' % (acmePath)
            subprocess.call(shlex.split(command))

            if aliasDomain is None:
                existingCertPath = '/etc/letsencrypt/live/' + virtualHostName
                if not os.path.exists(existingCertPath):
                    command = 'mkdir -p ' + existingCertPath
                    subprocess.call(shlex.split(command))

                try:
                    # Build domain list for acme.sh
                    domain_list = " -d " + virtualHostName
                    
                    # Check if www subdomain has DNS records (skip for hostnames)
                    if not isHostname and sslUtilities.checkDNSRecords(f'www.{virtualHostName}'):
                        domain_list += " -d www." + virtualHostName
                        logging.CyberCPLogFileWriter.writeToFile(f"www.{virtualHostName} has DNS records, including in acme.sh SSL request")
                    elif not isHostname:
                        logging.CyberCPLogFileWriter.writeToFile(f"www.{virtualHostName} has no DNS records, excluding from acme.sh SSL request")
                    
                    command = acmePath + " --issue" + domain_list \
                              + ' --cert-file ' + existingCertPath + '/cert.pem' + ' --key-file ' + existingCertPath + '/privkey.pem' \
                              + ' --fullchain-file ' + existingCertPath + '/fullchain.pem' + ' -w /usr/local/lsws/Example/html -k ec-256 --force --staging' \
                              + ' --webroot-path /usr/local/lsws/Example/html'
                    
                    try:
                        result = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                    except TypeError:
                        # Fallback for Python < 3.7
                        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

                    if result.returncode == 0:
                        command = acmePath + " --issue" + domain_list \
                                  + ' --cert-file ' + existingCertPath + '/cert.pem' + ' --key-file ' + existingCertPath + '/privkey.pem' \
                                  + ' --fullchain-file ' + existingCertPath + '/fullchain.pem' + ' -w /usr/local/lsws/Example/html -k ec-256 --force --server letsencrypt' \
                                  + ' --webroot-path /usr/local/lsws/Example/html'
                        
                        try:
                            result = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                        except TypeError:
                            # Fallback for Python < 3.7
                            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
                        
                        if result.returncode == 0:
                            logging.CyberCPLogFileWriter.writeToFile(
                                "Successfully obtained SSL for: " + virtualHostName + " and: www." + virtualHostName, 0)
                            logging.CyberCPLogFileWriter.SendEmail(sender_email, adminEmail, result.stdout,
                                                                   'SSL Notification for %s.' % (virtualHostName))
                            return 1
                    return 0
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(str(e))
                    return 0
            else:
                existingCertPath = '/etc/letsencrypt/live/' + virtualHostName
                if not os.path.exists(existingCertPath):
                    command = 'mkdir -p ' + existingCertPath
                    subprocess.call(shlex.split(command))

                try:
                    # Build domain list for acme.sh with alias domains
                    domain_list = " -d " + virtualHostName
                    
                    # Check if www subdomain has DNS records
                    if sslUtilities.checkDNSRecords(f'www.{virtualHostName}'):
                        domain_list += " -d www." + virtualHostName
                    
                    # Add alias domain
                    domain_list += " -d " + aliasDomain
                    
                    # Check if www.aliasDomain has DNS records
                    if sslUtilities.checkDNSRecords(f'www.{aliasDomain}'):
                        domain_list += " -d www." + aliasDomain
                    
                    command = acmePath + " --issue" + domain_list \
                              + ' --cert-file ' + existingCertPath + '/cert.pem' + ' --key-file ' + existingCertPath + '/privkey.pem' \
                              + ' --fullchain-file ' + existingCertPath + '/fullchain.pem' + ' -w /usr/local/lsws/Example/html -k ec-256 --force --server letsencrypt'

                    try:
                        result = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                    except TypeError:
                        # Fallback for Python < 3.7
                        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
                    
                    if result.returncode == 0:
                        return 1
                    return 0
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(str(e))
                    return 0
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(str(e))
            return 0


def issueSSLForDomain(domain, adminEmail, sslpath, aliasDomain=None, isHostname=False):
    try:
        # Check if certificate already exists and try to renew it first
        existingCertPath = '/etc/letsencrypt/live/' + domain + '/fullchain.pem'
        if os.path.exists(existingCertPath):
            logging.CyberCPLogFileWriter.writeToFile(f"Certificate exists for {domain}, attempting renewal...")
            
            # Try to renew using acme.sh
            acmePath = '/root/.acme.sh/acme.sh'
            if os.path.exists(acmePath):
                # First set the webroot path for the domain
                command = f'{acmePath} --update-account --accountemail {adminEmail}'
                subprocess.call(command, shell=True)
                
                # Build domain list for renewal
                renewal_domains = f'-d {domain}'
                if not isHostname and sslUtilities.checkDNSRecords(f'www.{domain}'):
                    renewal_domains += f' -d www.{domain}'
                
                # Try to renew with explicit webroot
                command = f'{acmePath} --renew {renewal_domains} --webroot /usr/local/lsws/Example/html --force'
                try:
                    result = subprocess.run(command, capture_output=True, text=True, shell=True)
                except TypeError:
                    # Fallback for Python < 3.7
                    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
                
                if result.returncode == 0:
                    logging.CyberCPLogFileWriter.writeToFile(f"Successfully renewed SSL for {domain}")
                    if sslUtilities.installSSLForDomain(domain, adminEmail) == 1:
                        return [1, "None"]
                else:
                    logging.CyberCPLogFileWriter.writeToFile(f"Renewal failed for {domain}, falling back to new issuance")
        
        if sslUtilities.obtainSSLForADomain(domain, adminEmail, sslpath, aliasDomain, isHostname) == 1:
            if sslUtilities.installSSLForDomain(domain, adminEmail) == 1:
                return [1, "None"]
            else:
                return [0, "210 Failed to install SSL for domain. [issueSSLForDomain]"]
        else:

            pathToStoreSSLPrivKey = "/etc/letsencrypt/live/%s/privkey.pem" % (domain)
            pathToStoreSSLFullChain = "/etc/letsencrypt/live/%s/fullchain.pem" % (domain)

            #### if in any case ssl failed to obtain and CyberPanel try to issue self-signed ssl, first check if ssl already present.
            ### if so, dont issue self-signed ssl, as it may override some existing ssl

            if os.path.exists(pathToStoreSSLFullChain):
                import OpenSSL
                x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open(pathToStoreSSLFullChain, 'r').read())
                SSLProvider = x509.get_issuer().get_components()[1][1].decode('utf-8')

                if SSLProvider != 'Denial':
                    if sslUtilities.installSSLForDomain(domain) == 1:
                        logging.CyberCPLogFileWriter.writeToFile("We are not able to get new SSL for " + domain + ". But there is an existing SSL, it might only be for the main domain (excluding www).")
                        return [1, "We are not able to get new SSL for " + domain + ". But there is an existing SSL, it might only be for the main domain (excluding www)." + " [issueSSLForDomain]"]

            command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=' + domain + '" -keyout ' + pathToStoreSSLPrivKey + ' -out ' + pathToStoreSSLFullChain
            cmd = shlex.split(command)
            subprocess.call(cmd)

            if sslUtilities.installSSLForDomain(domain) == 1:
                logging.CyberCPLogFileWriter.writeToFile("Self signed SSL issued for " + domain + ".")
                return [1, "Self signed certificate was issued. [issueSSLForDomain]"]
            else:
                return [0, "210 Failed to install SSL for domain. [issueSSLForDomain]"]

    except BaseException as msg:
        return [0, "347 " + str(msg) + " [issueSSLForDomain]"]