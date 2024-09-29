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



            #### totally seprate check to see if both non-www and www are covered

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
        try:
            confPath = sslUtilities.Server_root + "/conf/vhosts/" + virtualHostName
            completePathToConfigFile = confPath + "/vhost.conf"

            DataVhost = open(completePathToConfigFile, 'r').read()

            if DataVhost.find('/.well-known/acme-challenge') == -1:
                if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                    WriteToFile = open(completePathToConfigFile, 'a')

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
                    WriteToFile.write(content)
                    WriteToFile.close()
                else:
                    data = open(completePathToConfigFile, 'r').readlines()
                    WriteToFile = open(completePathToConfigFile, 'w')
                    Check = 0
                    for items in data:
                        if items.find('DocumentRoot /home/')> -1:
                            if Check == 0:
                                WriteToFile.write(items)
                                WriteToFile.write('    Alias /.well-known/acme-challenge /usr/local/lsws/Example/html/.well-known/acme-challenge\n')
                                Check = 1
                            else:
                                WriteToFile.write(items)
                        else:
                            WriteToFile.write(items)

                    WriteToFile.close()

                from plogical import installUtilities

                installUtilities.installUtilities.reStartLiteSpeed()


        except BaseException as msg:
            return 0, str(msg)


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
    def obtainSSLForADomain(virtualHostName, adminEmail, sslpath, aliasDomain=None):

        from plogical.acl import ACLManager
        from plogical.sslv2 import sslUtilities as sslv2
        import json
        #
        # url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
        # data = {
        #     "name": "all",
        #     "IP": ACLManager.GetServerIP()
        # }
        #
        # import requests
        # response = requests.post(url, data=json.dumps(data))
        #Status = response.json()['status']

        Status = 1

        # if (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent:
        #     retStatus, message = sslv2.obtainSSLForADomain(virtualHostName, adminEmail, sslpath, aliasDomain)
        #     if retStatus == 1:
        #         return retStatus

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

        CustomVerificationFile = f'/usr/local/lsws/Example/html/.well-known/acme-challenge/{virtualHostName}'
        command = f'touch {CustomVerificationFile}'
        ProcessUtilities.normalExecutioner(command)


        URLFetchPathWWW = f'http://www.{virtualHostName}/.well-known/acme-challenge/{virtualHostName}'
        URLFetchPathNONWWW = f'http://{virtualHostName}/.well-known/acme-challenge/{virtualHostName}'

        try:
            resp = requests.get(URLFetchPathWWW, timeout=5)

            if resp.status_code == 200:
                logging.CyberCPLogFileWriter.writeToFile(f'Status Code: 200 for: {URLFetchPathWWW}')
                WWWStatus = 1
            else:
                logging.CyberCPLogFileWriter.writeToFile(
                    f'Status Code: {str(resp.status_code)} for: {URLFetchPathWWW}. Error: {resp.text}')
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                f'Status Code: Unknown for: {URLFetchPathWWW}. Error: {str(msg)}')

        try:
            resp = requests.get(URLFetchPathNONWWW, timeout=5)
            if resp.status_code == 200:
                logging.CyberCPLogFileWriter.writeToFile(f'Status Code: 200 for: {URLFetchPathNONWWW}')
                NONWWWStatus = 1
            else:
                logging.CyberCPLogFileWriter.writeToFile(f'Status Code: {str(resp.status_code)} for: {URLFetchPathNONWWW}. Error: {resp.text}')
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                f'Status Code: Unkown for: {URLFetchPathNONWWW}. Error: {str(msg)}')

        WWWStatus = 1
        NONWWWStatus = 1


        try:
            acmePath = '/root/.acme.sh/acme.sh'

            ### register account for zero ssl

            command = '%s --register-account -m %s' % (acmePath, adminEmail)
            subprocess.call(shlex.split(command))

            # if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
            #     acmePath = '/home/cyberpanel/.acme.sh/acme.sh'

            if aliasDomain is None:

                existingCertPath = '/etc/letsencrypt/live/' + virtualHostName
                if not os.path.exists(existingCertPath):
                    command = 'mkdir -p ' + existingCertPath
                    subprocess.call(shlex.split(command))

                try:
                    command = acmePath + " --issue -d " + virtualHostName + " -d www." + virtualHostName \
                              + ' --cert-file ' + existingCertPath + '/cert.pem' + ' --key-file ' + existingCertPath + '/privkey.pem' \
                              + ' --fullchain-file ' + existingCertPath + '/fullchain.pem' + ' -w /usr/local/lsws/Example/html -k ec-256 --force --server letsencrypt'
                    #ResultText = open(logging.CyberCPLogFileWriter.fileName, 'r').read()
                    #CurrentMessage = "Trying to obtain SSL for: " + virtualHostName + " and: www." + virtualHostName
                    if (WWWStatus and NONWWWStatus):

                        #logging.CyberCPLogFileWriter.writeToFile(CurrentMessage, 0)

                        logging.CyberCPLogFileWriter.writeToFile(command, 0)

                        output = subprocess.check_output(shlex.split(command)).decode("utf-8")
                        logging.CyberCPLogFileWriter.writeToFile("Successfully obtained SSL for: " + virtualHostName + " and: www." + virtualHostName, 0)

                        logging.CyberCPLogFileWriter.SendEmail(sender_email, adminEmail, output, 'SSL Notification for %s.' % (virtualHostName))
                    else:
                        logging.CyberCPLogFileWriter.writeToFile(command, 0)
                        raise subprocess.CalledProcessError(0, '', '')

                except subprocess.CalledProcessError:
                    logging.CyberCPLogFileWriter.writeToFile(
                        "Failed to obtain SSL for: " + virtualHostName + " and: www." + virtualHostName, 0)

                    finalText = "Failed to obtain SSL for: " + virtualHostName + " and: www." + virtualHostName

                    try:
                        command = acmePath + " --issue -d " + virtualHostName + ' --cert-file ' + existingCertPath \
                                  + '/cert.pem' + ' --key-file ' + existingCertPath + '/privkey.pem' \
                                  + ' --fullchain-file ' + existingCertPath + '/fullchain.pem' + ' -w /usr/local/lsws/Example/html -k ec-256 --force --server letsencrypt'

                        #ResultText = open(logging.CyberCPLogFileWriter.fileName, 'r').read()
                        CurrentMessage = '%s\nTrying to obtain SSL for: %s' % (finalText, virtualHostName)

                        if NONWWWStatus:
                            finalText = '%s\nTrying to obtain SSL for: %s' % (finalText, virtualHostName)
                            logging.CyberCPLogFileWriter.writeToFile("Trying to obtain SSL for: " + virtualHostName, 0)
                            logging.CyberCPLogFileWriter.writeToFile(command)
                            output = subprocess.check_output(shlex.split(command)).decode("utf-8")
                            logging.CyberCPLogFileWriter.writeToFile(
                                "Successfully obtained SSL for: " + virtualHostName, 0)
                            finalText = '%s\nSuccessfully obtained SSL for: %s.' % (finalText, virtualHostName)
                            logging.CyberCPLogFileWriter.SendEmail(sender_email, adminEmail, finalText,
                                                                   'SSL Notification for %s.' % (virtualHostName))

                        else:
                            logging.CyberCPLogFileWriter.writeToFile(command, 0)
                            raise subprocess.CalledProcessError(0, '', '')

                    except subprocess.CalledProcessError:
                        logging.CyberCPLogFileWriter.writeToFile('Failed to obtain SSL, issuing self-signed SSL for: ' + virtualHostName, 0)
                        logging.CyberCPLogFileWriter.SendEmail(sender_email, adminEmail, 'Failed to obtain SSL, issuing self-signed SSL for: ' + virtualHostName,
                                                               'SSL Notification for %s.' % (virtualHostName))
                        return 0
            else:

                existingCertPath = '/etc/letsencrypt/live/' + virtualHostName
                if not os.path.exists(existingCertPath):
                    command = 'mkdir -p ' + existingCertPath
                    subprocess.call(shlex.split(command))

                try:
                    logging.CyberCPLogFileWriter.writeToFile(
                        "Trying to obtain SSL for: " + virtualHostName + ", www." + virtualHostName + ", " + aliasDomain + " and www." + aliasDomain + ",")

                    command = acmePath + " --issue -d " + virtualHostName + " -d www." + virtualHostName \
                              + ' -d ' + aliasDomain + ' -d www.' + aliasDomain\
                              + ' --cert-file ' + existingCertPath + '/cert.pem' + ' --key-file ' + existingCertPath + '/privkey.pem' \
                              + ' --fullchain-file ' + existingCertPath + '/fullchain.pem' + ' -w /usr/local/lsws/Example/html -k ec-256 --force --server letsencrypt'

                    output = subprocess.check_output(shlex.split(command)).decode("utf-8")
                    logging.CyberCPLogFileWriter.writeToFile(
                        "Successfully obtained SSL for: " + virtualHostName + ", www." + virtualHostName + ", " + aliasDomain + "and www." + aliasDomain + ",")

                except subprocess.CalledProcessError:
                    logging.CyberCPLogFileWriter.writeToFile(
                        "Failed to obtain SSL for: " + virtualHostName + ", www." + virtualHostName + ", " + aliasDomain + "and www." + aliasDomain + ",")
                    return 0

            ##

            if output.find('Cert success') > -1:
                return 1
            else:
                return 0

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Failed to obtain SSL. [obtainSSLForADomain]]")
            return 0


def issueSSLForDomain(domain, adminEmail, sslpath, aliasDomain=None):
    try:
        if sslUtilities.obtainSSLForADomain(domain, adminEmail, sslpath, aliasDomain) == 1:
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
