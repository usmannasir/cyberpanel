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
    def _ssl_live_cert_paths(domain):
        live_dir = '/etc/letsencrypt/live/' + domain
        return live_dir + '/privkey.pem', live_dir + '/fullchain.pem'

    @staticmethod
    def _ssl_cert_files_exist(domain):
        priv_path, full_path = sslUtilities._ssl_live_cert_paths(domain)
        return os.path.exists(full_path) and os.path.exists(priv_path)

    @staticmethod
    def _ssl_issue_self_signed(domain):
        """Create self-signed cert under /etc/letsencrypt/live/ via privileged executioner."""
        priv_path, full_path = sslUtilities._ssl_live_cert_paths(domain)
        if os.path.exists(full_path) and os.path.exists(priv_path):
            return True

        live_dir = os.path.dirname(full_path)
        ProcessUtilities.ensureCommandToken()
        mkdir_cmd = 'mkdir -p %s && chmod 755 %s' % (shlex.quote(live_dir), shlex.quote(live_dir))
        if ProcessUtilities.executioner(mkdir_cmd, None, True) != 1:
            logging.CyberCPLogFileWriter.writeToFile(
                'Failed to create live cert directory for %s' % (domain))
            return False

        subj = '/C=US/ST=Denial/L=Springfield/O=Dis/CN=%s' % domain
        openssl_cmd = (
            'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 '
            '-subj %s -keyout %s -out %s && chmod 600 %s && chmod 644 %s'
        ) % (
            shlex.quote(subj),
            shlex.quote(priv_path),
            shlex.quote(full_path),
            shlex.quote(priv_path),
            shlex.quote(full_path),
        )
        if ProcessUtilities.executioner(openssl_cmd, None, True) != 1:
            logging.CyberCPLogFileWriter.writeToFile(
                'Failed to issue self-signed SSL for %s via openssl' % (domain))
            return False

        if os.path.exists(full_path) and os.path.exists(priv_path):
            return True

        verify_cmd = 'test -f %s && test -f %s && echo ok' % (
            shlex.quote(full_path), shlex.quote(priv_path))
        out = (ProcessUtilities.outputExecutioner(verify_cmd, None, True) or '').strip()
        return out == 'ok'

    @staticmethod
    def _ssl_ensure_cert_files_for_vhost(virtualHostName):
        if sslUtilities._ssl_cert_files_exist(virtualHostName):
            return True
        return sslUtilities._ssl_issue_self_signed(virtualHostName)

    @staticmethod
    def parseACMEError(error_output):
        """Parse ACME error output to extract meaningful error messages"""
        if not error_output:
            return "Unknown error occurred"

        error_output = str(error_output)

        # Common ACME/Let's Encrypt errors
        error_patterns = {
            r"rateLimited": "Rate limit exceeded. Too many certificates issued for this domain. Please wait before retrying.",
            r"urn:ietf:params:acme:error:rateLimited": "Rate limit exceeded. Please wait before retrying.",
            r"too many certificates": "Rate limit: Too many certificates issued recently.",
            r"DNS problem: NXDOMAIN": "DNS Error: Domain does not exist or DNS not propagated.",
            r"DNS problem": "DNS validation failed. Ensure domain points to this server.",
            r"Connection refused": "Cannot connect to ACME server. Check firewall/network settings.",
            r"Connection timeout": "Connection to ACME server timed out. Check network connectivity.",
            r"Timeout during connect": "Connection timeout. The ACME server may be unreachable.",
            r"unauthorized": "Authorization failed. Domain validation unsuccessful.",
            r"urn:ietf:params:acme:error:unauthorized": "Domain authorization failed. Verify domain ownership.",
            r"Invalid response from": "Invalid response from domain during validation.",
            r"404": "Challenge file not found. Check web server configuration.",
            r"403": "Access forbidden. Check file permissions and .htaccess rules.",
            r"CAA record": "CAA record prevents certificate issuance. Update DNS CAA records.",
            r"urn:ietf:params:acme:error:caa": "CAA record forbids issuance. Check DNS CAA settings.",
            r"Challenge failed": "ACME challenge failed. Ensure port 80 is accessible.",
            r"No valid IP addresses": "No valid IP addresses found for domain.",
            r"Could not connect to": "Cannot connect to domain for validation.",
            r"conflictingRequest": "A conflicting request exists. Previous request may still be processing.",
            r"urn:ietf:params:acme:error:malformed": "Malformed request. Check domain format.",
            r"urn:ietf:params:acme:error:serverInternal": "ACME server internal error. Try again later.",
            r"urn:ietf:params:acme:error:orderNotReady": "Order not ready. Domain validation incomplete.",
            r"badNonce": "Bad nonce error. This is usually temporary, please retry.",
            r"JWS has an invalid anti-replay nonce": "Invalid nonce. Please retry the request.",
            r"Account registration error": "Account registration failed. Check email address.",
            r"Error creating new account": "Cannot create ACME account. Check email validity.",
            r"Verify error": "Certificate verification failed.",
            r"Fetching http://": "HTTP validation failed. Ensure port 80 is open.",
            r"Fetching https://": "HTTPS validation issue detected.",
            r"Invalid email address": "Invalid email address provided for registration.",
            r"blacklisted": "Domain is blacklisted by the certificate authority.",
            r"PolicyForbids": "Certificate authority policy forbids issuance for this domain."
        }

        # Check each pattern
        import re
        for pattern, message in error_patterns.items():
            if re.search(pattern, error_output, re.IGNORECASE):
                # Try to extract additional context
                lines = error_output.split('\n')
                for line in lines:
                    if 'Detail:' in line:
                        message += f" Detail: {line.split('Detail:')[1].strip()}"
                        break
                return message

        # Try to extract specific error details from acme.sh output
        if "[" in error_output and "]" in error_output:
            # Extract content between brackets which often contains the error
            import re
            bracket_content = re.findall(r'\[([^\]]+)\]', error_output)
            if bracket_content:
                # Get the last bracketed content as it's usually the error
                potential_error = bracket_content[-1]
                if len(potential_error) > 10:  # Make sure it's meaningful
                    return f"SSL issuance failed: {potential_error}"

        # Look for lines starting with "Error:" or containing "error:"
        lines = error_output.split('\n')
        for line in lines:
            if line.strip().startswith('Error:') or 'error:' in line.lower():
                return line.strip()

        # If we can't parse a specific error, return a portion of the output
        if len(error_output) > 200:
            # Get the last 200 characters which likely contain the error
            return f"SSL issuance failed: ...{error_output[-200:]}"

        return f"SSL issuance failed: {error_output}"

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
                result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        universal_newlines=True)

            # If there's any output, the domain has A records
            if result.stdout.strip():
                return True

            # Also check AAAA records
            command = f"dig +short {domain} AAAA @8.8.8.8"
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
            except TypeError:
                # Fallback for Python < 3.7
                result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        universal_newlines=True)

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
                            '[CheckIfSSLNeedsToBeIssued] SSL exists for %s and both versions are covered, just need to ensure if SSL is valid for less then 15 days.' % (
                                virtualHostName), 0)
                        pass
                    else:
                        return sslUtilities.ISSUE_SSL

            #####

            expireData = x509.get_notAfter().decode('ascii')
            from datetime import datetime
            finalDate = datetime.strptime(expireData, '%Y%m%d%H%M%SZ')
            now = datetime.now()
            diff = finalDate - now

            if int(diff.days) >= 15 and SSLProvider != 'Denial':
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
            from plogical import installUtilities
            data = installUtilities.installUtilities._readProtectedConfigLines(
                "/usr/local/lsws/conf/httpd_config.conf")

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
            from plogical import installUtilities
            data = installUtilities.installUtilities._readProtectedConfigLines(
                "/usr/local/lsws/conf/httpd_config.conf")
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
            from plogical import installUtilities
            data = installUtilities.installUtilities._readProtectedConfigLines(
                "/usr/local/lsws/conf/httpd_config.conf")
            for items in data:
                if items.find("listener SSL IPv6") > -1:
                    return 1

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(
                str(msg) + " [IO Error with main config file [checkSSLIPv6Listener]]")
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
                logging.CyberCPLogFileWriter.writeToFile(
                    f'Configuration conflicts for {virtualHostName}: {conflict_message}')
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
                                f.write(
                                    '    Alias /.well-known/acme-challenge /usr/local/lsws/Example/html/.well-known/acme-challenge\n')
                                check = 1
                except IOError as e:
                    logging.CyberCPLogFileWriter.writeToFile(f'Error writing Apache configuration: {str(e)}')
                    return 0, f'Error writing Apache configuration: {str(e)}'

            # Restart LiteSpeed
            try:
                from plogical import installUtilities
                installUtilities.installUtilities.reStartLiteSpeed()
                logging.CyberCPLogFileWriter.writeToFile(
                    f'Successfully configured ACME challenge for {virtualHostName}')
                return 1, 'Successfully configured ACME challenge'
            except Exception as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Error restarting LiteSpeed: {str(e)}')
                return 0, f'Error restarting LiteSpeed: {str(e)}'

        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Unexpected error in PatchVhostConf: {str(e)}')
            return 0, f'Unexpected error: {str(e)}'

    @staticmethod
    def installSSLForDomain(virtualHostName, adminEmail='domain@cyberpanel.net'):

        try:
            website = Websites.objects.get(domain=virtualHostName)
            adminEmail = website.adminEmail
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile('%s [installSSLForDomain:72]' % (str(msg)))

        if not sslUtilities._ssl_ensure_cert_files_for_vhost(virtualHostName):
            logging.CyberCPLogFileWriter.writeToFile(
                'Cannot install SSL for %s: certificate files are missing' % (virtualHostName))
            return 0

        priv_path, full_path = sslUtilities._ssl_live_cert_paths(virtualHostName)

        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            confPath = sslUtilities.Server_root + "/conf/vhosts/" + virtualHostName
            completePathToConfigFile = confPath + "/vhost.conf"

            try:
                map = "  map                     " + virtualHostName + " " + virtualHostName + "\n"

                if sslUtilities.checkSSLListener() != 1:
                    from plogical import installUtilities
                    listener_block = (
                        "\nlistener SSL {\n"
                        "  address                 *:443\n"
                        "  secure                  1\n"
                        "  keyFile                  " + priv_path + "\n"
                        "  certFile                 " + full_path + "\n"
                        "  certChain               1\n"
                        "  sslProtocol             24\n"
                        "  enableECDHE             1\n"
                        "  renegProtection         1\n"
                        "  sslSessionCache         1\n"
                        "  enableSpdy              15\n"
                        "  enableStapling           1\n"
                        "  ocspRespMaxAge           86400\n"
                        "  map                     " + virtualHostName + " " + virtualHostName + "\n"
                        "}\n\n"
                    )
                    ok, err = installUtilities.installUtilities.appendProtectedHttpdConfigBlock(
                        listener_block, 'Add SSL listener for %s' % virtualHostName)
                    if not ok:
                        raise BaseException(err or 'Failed to add SSL listener block')

                elif sslUtilities.checkSSLIPv6Listener() != 1:
                    from plogical import installUtilities
                    listener_block = (
                        "\nlistener SSL IPv6 {\n"
                        "  address                 [ANY]:443\n"
                        "  secure                  1\n"
                        "  keyFile                  " + priv_path + "\n"
                        "  certFile                 " + full_path + "\n"
                        "  certChain               1\n"
                        "  sslProtocol             24\n"
                        "  enableECDHE             1\n"
                        "  renegProtection         1\n"
                        "  sslSessionCache         1\n"
                        "  enableSpdy              15\n"
                        "  enableStapling           1\n"
                        "  ocspRespMaxAge           86400\n"
                        "  map                     " + virtualHostName + " " + virtualHostName + "\n"
                        "}\n\n"
                    )
                    ok, err = installUtilities.installUtilities.appendProtectedHttpdConfigBlock(
                        listener_block, 'Add SSL IPv6 listener for %s' % virtualHostName)
                    if not ok:
                        raise BaseException(err or 'Failed to add SSL IPv6 listener block')

                else:

                    if sslUtilities.checkIfSSLMap(virtualHostName) == 0:
                        from plogical import installUtilities
                        
                        def modify_config(lines):
                            """Add SSL map entry to existing SSL listener"""
                            modified = []
                            sslCheck = 0
                            
                            for line in lines:
                                if line.find("listener") > -1 and line.find("SSL") > -1:
                                    sslCheck = 1
                                
                                if (sslCheck == 1):
                                    modified.append(line)
                                    modified.append(map)
                                    sslCheck = 0
                                else:
                                    modified.append(line)
                            
                            return modified
                        
                        # Use safe modification with backup and validation
                        success, error = installUtilities.installUtilities.safeModifyHttpdConfig(
                            modify_config,
                            f"Add SSL map entry for {virtualHostName}"
                        )
                        
                        if not success:
                            error_msg = error if error else "Unknown error"
                            logging.writeToFile(f"[sslUtilities] Failed to add SSL map entry: {error_msg}")
                            raise BaseException(f"Failed to add SSL map entry: {error_msg}")

                    ###################### Write per host Configs for SSL ###################

                    from plogical import installUtilities
                    data = installUtilities.installUtilities._readProtectedConfigLines(completePathToConfigFile)

                    ## check if vhssl is already in vhconf file

                    vhsslPresense = 0

                    for items in data:
                        if items.find("vhssl") > -1:
                            vhsslPresense = 1

                    if vhsslPresense == 0:
                        ssl_block = (
                            "\nvhssl  {\n"
                            "  keyFile                 " + priv_path + "\n"
                            "  certFile                " + full_path + "\n"
                            "  certChain               1\n"
                            "  sslProtocol             24\n"
                            "  enableECDHE             1\n"
                            "  renegProtection         1\n"
                            "  sslSessionCache         1\n"
                            "  enableSpdy              15\n"
                            "  enableStapling           1\n"
                            "  ocspRespMaxAge           86400\n"
                            "}\n\n"
                        )
                        ok, err = installUtilities.installUtilities._writeProtectedConfigLines(
                            completePathToConfigFile, data + [ssl_block])
                        if not ok:
                            raise BaseException(err or 'Failed to write vhssl block to vhost.conf')

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

        # Replace example.org emails with domain-specific email
        if adminEmail and ('example.org' in adminEmail or 'example.com' in adminEmail):
            import re
            # Remove special characters and create domain-based email
            clean_domain = re.sub(r'[^a-zA-Z0-9]', '', virtualHostName)
            adminEmail = f'{clean_domain}@cyberpanel.net'
            logging.CyberCPLogFileWriter.writeToFile(f'Replacing invalid email with {adminEmail}')

        Status = 1

        if sslUtilities.CheckIfSSLNeedsToBeIssued(virtualHostName) == sslUtilities.ISSUE_SSL:
            pass
        else:
            return 1

        sender_email = 'root@%s' % (socket.gethostname())

        sslUtilities.PatchVhostConf(virtualHostName)

        try:
            from plogical.ssl_cloudflare_dns import find_domain_in_cloudflare, issue_le_via_cloudflare_dns
            cf_ok, _cf_msg = find_domain_in_cloudflare(virtualHostName)
            if cf_ok and issue_le_via_cloudflare_dns(virtualHostName, adminEmail, isHostname):
                logging.CyberCPLogFileWriter.writeToFile(
                    'obtainSSLForADomain: issued via Cloudflare DNS for %s' % virtualHostName, 0)
                return 1
        except BaseException as cf_exc:
            logging.CyberCPLogFileWriter.writeToFile(
                'Cloudflare DNS SSL path skipped for %s: %s' % (virtualHostName, str(cf_exc)))

        default_webroot = '/usr/local/lsws/Example/html'
        # Child domains: use their docroot so HTTP-01 challenge is served from the correct vhost
        if sslpath and str(sslpath).strip():
            webroot = str(sslpath).strip().rstrip('/')
            if webroot != default_webroot and os.path.isdir(webroot):
                challenge_path = webroot + '/.well-known/acme-challenge'
                if not os.path.exists(challenge_path):
                    ProcessUtilities.executioner('mkdir -p %s' % shlex.quote(challenge_path), None, True)
                    ProcessUtilities.executioner(
                        'chmod -R 755 %s' % shlex.quote(webroot + '/.well-known'), None, True)
                logging.CyberCPLogFileWriter.writeToFile(
                    f"Using domain webroot for ACME challenge: {webroot}")
            else:
                webroot = default_webroot
                challenge_path = None
        else:
            webroot = default_webroot
            challenge_path = None

        if not os.path.exists(default_webroot + '/.well-known/acme-challenge'):
            command = 'mkdir -p %s' % shlex.quote(default_webroot + '/.well-known/acme-challenge')
            ProcessUtilities.executioner(command, None, True)

        command = f'chmod -R 755 {default_webroot}'
        ProcessUtilities.executioner(command)

        # Try Let's Encrypt first
        try:
            # Start with just the main domain
            domains = [virtualHostName]

            # Check if www subdomain has DNS records before adding it (skip for hostnames)
            if not isHostname and sslUtilities.checkDNSRecords(f'www.{virtualHostName}'):
                domains.append(f'www.{virtualHostName}')
                logging.CyberCPLogFileWriter.writeToFile(
                    f"www.{virtualHostName} has DNS records, including in SSL request")
            elif not isHostname:
                logging.CyberCPLogFileWriter.writeToFile(
                    f"www.{virtualHostName} has no DNS records, excluding from SSL request")

            if aliasDomain:
                domains.append(aliasDomain)
                # Check if www.aliasDomain has DNS records
                if sslUtilities.checkDNSRecords(f'www.{aliasDomain}'):
                    domains.append(f'www.{aliasDomain}')
                    logging.CyberCPLogFileWriter.writeToFile(
                        f"www.{aliasDomain} has DNS records, including in SSL request")
                else:
                    logging.CyberCPLogFileWriter.writeToFile(
                        f"www.{aliasDomain} has no DNS records, excluding from SSL request")

            # DNS-01 when zone is in Cloudflare (not only externalApp flag)
            use_dns = False
            try:
                from plogical.ssl_cloudflare_dns import find_domain_in_cloudflare
                cf_ok, _ = find_domain_in_cloudflare(virtualHostName)
                use_dns = bool(cf_ok)
            except BaseException:
                try:
                    website = Websites.objects.get(domain=virtualHostName)
                    if website.externalApp == 'cloudflare':
                        use_dns = True
                except BaseException:
                    pass

            acme = CustomACME(virtualHostName, adminEmail, staging=False, provider='letsencrypt', challenge_path=challenge_path)
            if acme.issue_certificate(domains, use_dns=use_dns):
                logging.CyberCPLogFileWriter.writeToFile(
                    f"Successfully obtained SSL using Let's Encrypt for: {virtualHostName}")
                return 1
        except Exception as e:
            error_msg = str(e)
            # Try to extract more detailed error information
            if hasattr(e, '__dict__'):
                error_details = str(e.__dict__)
            else:
                error_details = error_msg

            logging.CyberCPLogFileWriter.writeToFile(
                f"Let's Encrypt failed for {virtualHostName}: {error_msg}"
            )
            logging.CyberCPLogFileWriter.writeToFile(
                f"Detailed error: {error_details}. Trying ZeroSSL..."
            )

        # Try ZeroSSL if Let's Encrypt fails
        try:
            # Start with just the main domain
            domains = [virtualHostName]

            # Check if www subdomain has DNS records before adding it (skip for hostnames)
            if not isHostname and sslUtilities.checkDNSRecords(f'www.{virtualHostName}'):
                domains.append(f'www.{virtualHostName}')
                logging.CyberCPLogFileWriter.writeToFile(
                    f"www.{virtualHostName} has DNS records, including in SSL request")
            elif not isHostname:
                logging.CyberCPLogFileWriter.writeToFile(
                    f"www.{virtualHostName} has no DNS records, excluding from SSL request")

            if aliasDomain:
                domains.append(aliasDomain)
                # Check if www.aliasDomain has DNS records
                if sslUtilities.checkDNSRecords(f'www.{aliasDomain}'):
                    domains.append(f'www.{aliasDomain}')
                    logging.CyberCPLogFileWriter.writeToFile(
                        f"www.{aliasDomain} has DNS records, including in SSL request")
                else:
                    logging.CyberCPLogFileWriter.writeToFile(
                        f"www.{aliasDomain} has no DNS records, excluding from SSL request")

            acme = CustomACME(virtualHostName, adminEmail, staging=False, provider='zerossl', challenge_path=challenge_path)
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
                        logging.CyberCPLogFileWriter.writeToFile(
                            f"www.{virtualHostName} has DNS records, including in acme.sh SSL request")
                    elif not isHostname:
                        logging.CyberCPLogFileWriter.writeToFile(
                            f"www.{virtualHostName} has no DNS records, excluding from acme.sh SSL request")

                    # Step 1: Issue the certificate (staging) - this stores config in /root/.acme.sh/
                    command = acmePath + " --issue" + domain_list \
                              + ' --cert-file ' + existingCertPath + '/cert.pem' + ' --key-file ' + existingCertPath + '/privkey.pem' \
                              + ' --fullchain-file ' + existingCertPath + '/fullchain.pem' + ' -w ' + webroot + ' -k ec-256 --force --staging' \
                              + ' --webroot-path ' + webroot

                    try:
                        result = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                    except TypeError:
                        # Fallback for Python < 3.7
                        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                universal_newlines=True, shell=True)

                    if result.returncode == 0:
                        # Step 2: Issue the certificate (production) - this stores config in /root/.acme.sh/
                        command = acmePath + " --issue" + domain_list \
                                  + ' --cert-file ' + existingCertPath + '/cert.pem' + ' --key-file ' + existingCertPath + '/privkey.pem' \
                                  + ' --fullchain-file ' + existingCertPath + '/fullchain.pem' + ' -w ' + webroot + ' -k ec-256 --force --server letsencrypt' \
                                  + ' --webroot-path ' + webroot

                        try:
                            result = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                        except TypeError:
                            # Fallback for Python < 3.7
                            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                    universal_newlines=True, shell=True)

                        if result.returncode == 0:
                            # Step 3: Install the certificate to the desired location
                            install_command = acmePath + " --install-cert -d " + virtualHostName \
                                            + ' --ecc' \
                                            + ' --cert-file ' + existingCertPath + '/cert.pem' \
                                            + ' --key-file ' + existingCertPath + '/privkey.pem' \
                                            + ' --fullchain-file ' + existingCertPath + '/fullchain.pem'

                            try:
                                install_result = subprocess.run(install_command, capture_output=True, universal_newlines=True, shell=True)
                            except TypeError:
                                # Fallback for Python < 3.7
                                install_result = subprocess.run(install_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                                universal_newlines=True, shell=True)

                            if install_result.returncode == 0:
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

                    # Step 1: Issue the certificate - this stores config in /root/.acme.sh/
                    command = acmePath + " --issue" + domain_list \
                              + ' --cert-file ' + existingCertPath + '/cert.pem' + ' --key-file ' + existingCertPath + '/privkey.pem' \
                              + ' --fullchain-file ' + existingCertPath + '/fullchain.pem' + ' -w ' + webroot + ' -k ec-256 --force --server letsencrypt'

                    try:
                        result = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                    except TypeError:
                        # Fallback for Python < 3.7
                        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                universal_newlines=True, shell=True)

                    if result.returncode == 0:
                        # Step 2: Install the certificate to the desired location
                        install_command = acmePath + " --install-cert -d " + virtualHostName \
                                        + ' --ecc' \
                                        + ' --cert-file ' + existingCertPath + '/cert.pem' \
                                        + ' --key-file ' + existingCertPath + '/privkey.pem' \
                                        + ' --fullchain-file ' + existingCertPath + '/fullchain.pem'

                        try:
                            install_result = subprocess.run(install_command, capture_output=True, universal_newlines=True, shell=True)
                        except TypeError:
                            # Fallback for Python < 3.7
                            install_result = subprocess.run(install_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                            universal_newlines=True, shell=True)

                        if install_result.returncode == 0:
                            return 1
                    return 0
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(str(e))
                    return 0
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(str(e))
            return 0


def _ssl_resolve_acme_webroot(sslpath):
    """Match obtainSSLForADomain webroot selection for HTTP-01 (child domains / custom docroot)."""
    default_webroot = '/usr/local/lsws/Example/html'
    if sslpath and str(sslpath).strip():
        webroot = str(sslpath).strip().rstrip('/')
        if webroot != default_webroot and os.path.isdir(webroot):
            return webroot
    return default_webroot


def _ssl_privkey_is_ecdsa(privkey_path):
    """True if privkey is ECDSA (CyberPanel acme.sh -k ec-256); False for legacy RSA."""
    if not os.path.exists(privkey_path):
        return True
    try:
        try:
            proc = subprocess.run(
                ['openssl', 'ec', '-in', privkey_path, '-noout'],
                capture_output=True, text=True, timeout=15,
            )
        except TypeError:
            proc = subprocess.run(
                ['openssl', 'ec', '-in', privkey_path, '-noout'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True, timeout=15,
            )
        return proc.returncode == 0
    except BaseException as exc:
        try:
            logging.CyberCPLogFileWriter.writeToFile(
                '_ssl_privkey_is_ecdsa: %s, assuming ECDSA' % (str(exc),))
        except BaseException:
            pass
        return True


def _ssl_acme_deploy_to_live(acmePath, domain, use_ecc):
    """Run acme.sh --install-cert so renewed certs are copied to /etc/letsencrypt/live/."""
    live_dir = '/etc/letsencrypt/live/' + domain
    if not os.path.exists(live_dir):
        subprocess.call(shlex.split('mkdir -p ' + live_dir))
    install_command = acmePath + ' --install-cert -d ' + shlex.quote(domain)
    if use_ecc:
        install_command += ' --ecc'
    install_command += (
        ' --cert-file ' + live_dir + '/cert.pem'
        ' --key-file ' + live_dir + '/privkey.pem'
        ' --fullchain-file ' + live_dir + '/fullchain.pem'
    )
    try:
        install_result = subprocess.run(
            install_command, capture_output=True, text=True, shell=True)
    except TypeError:
        install_result = subprocess.run(
            install_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, shell=True)
    if install_result.returncode != 0:
        err = ''
        try:
            err = (install_result.stderr or install_result.stdout or '').strip()
        except BaseException:
            err = ''
        logging.CyberCPLogFileWriter.writeToFile(
            'acme.sh install-cert failed for %s (exit %s): %s' % (
                domain, install_result.returncode, err[:2000]))
        return False
    logging.CyberCPLogFileWriter.writeToFile(
        'Deployed renewed certificate to %s via acme.sh install-cert' % (live_dir,), 0)
    return True


def issueSSLForDomain(domain, adminEmail, sslpath, aliasDomain=None, isHostname=False):
    try:
        # Check if certificate already exists and try to renew it first
        existingCertPath = '/etc/letsencrypt/live/' + domain + '/fullchain.pem'
        if os.path.exists(existingCertPath):
            # Check if certificate is expired
            is_expired = False
            try:
                import OpenSSL
                from datetime import datetime
                with open(existingCertPath, 'r') as cert_file:
                    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_file.read())
                expire_data = x509.get_notAfter().decode('ascii')
                final_date = datetime.strptime(expire_data, '%Y%m%d%H%M%SZ')
                now = datetime.now()
                diff = final_date - now
                is_expired = diff.days < 0
                logging.CyberCPLogFileWriter.writeToFile(f"Certificate for {domain} expires in {diff.days} days")
            except Exception as e:
                logging.CyberCPLogFileWriter.writeToFile(f"Could not check certificate expiry: {str(e)}")

            logging.CyberCPLogFileWriter.writeToFile(f"Certificate exists for {domain}, attempting renewal...")

            if is_expired:
                try:
                    from plogical.ssl_cloudflare_dns import issue_le_via_cloudflare_dns
                    if issue_le_via_cloudflare_dns(domain, adminEmail, isHostname):
                        if sslUtilities.installSSLForDomain(domain, adminEmail) == 1:
                            return [1, "SSL successfully renewed via Cloudflare DNS"]
                except BaseException as cf_renew_exc:
                    logging.CyberCPLogFileWriter.writeToFile(
                        'Cloudflare DNS renewal attempt failed for %s: %s' % (domain, str(cf_renew_exc)))

            # Try to renew using acme.sh
            acmePath = '/root/.acme.sh/acme.sh'
            if os.path.exists(acmePath):
                # First set the webroot path for the domain
                command = f'{acmePath} --update-account --accountemail {adminEmail}'
                subprocess.call(command, shell=True)

                webroot = _ssl_resolve_acme_webroot(sslpath)
                logging.CyberCPLogFileWriter.writeToFile(
                    f'ACME renew webroot for {domain}: {webroot}', 0)

                privkey_path = '/etc/letsencrypt/live/' + domain + '/privkey.pem'
                use_ecc = _ssl_privkey_is_ecdsa(privkey_path)

                # Build domain list for renewal
                renewal_domains = f'-d {domain}'
                if not isHostname and sslUtilities.checkDNSRecords(f'www.{domain}'):
                    renewal_domains += f' -d www.{domain}'

                # For expired certificates, use --issue --force instead of --renew
                if is_expired:
                    logging.CyberCPLogFileWriter.writeToFile(
                        f"Certificate is expired, using --issue --force for {domain}")
                    key_opt = ' -k ec-256' if use_ecc else ''
                    command = (
                        f'{acmePath} --issue {renewal_domains} -w {shlex.quote(webroot)}'
                        f'{key_opt} --force'
                    )
                else:
                    ecc_opt = ' --ecc' if use_ecc else ''
                    command = (
                        f'{acmePath} --renew {renewal_domains} -w {shlex.quote(webroot)}'
                        f'{ecc_opt} --force'
                    )

                try:
                    result = subprocess.run(command, capture_output=True, text=True, shell=True)
                except TypeError:
                    # Fallback for Python < 3.7
                    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                            universal_newlines=True, shell=True)

                if result.returncode == 0:
                    logging.CyberCPLogFileWriter.writeToFile(f"Successfully renewed SSL for {domain}")
                    if not _ssl_acme_deploy_to_live(acmePath, domain, use_ecc):
                        logging.CyberCPLogFileWriter.writeToFile(
                            f'install-cert after renew failed for {domain}; will try full obtain path', 1)
                    elif sslUtilities.installSSLForDomain(domain, adminEmail) == 1:
                        return [1, "SSL successfully renewed"]
                else:
                    # Parse ACME error details
                    error_output = result.stderr if hasattr(result, 'stderr') and result.stderr else result.stdout
                    error_details = sslUtilities.parseACMEError(error_output)
                    logging.CyberCPLogFileWriter.writeToFile(f"Renewal failed for {domain}. Error: {error_details}")
                    logging.CyberCPLogFileWriter.writeToFile(f"Full error output: {error_output}")

        if sslUtilities.obtainSSLForADomain(domain, adminEmail, sslpath, aliasDomain, isHostname) == 1:
            if sslUtilities.installSSLForDomain(domain, adminEmail) == 1:
                return [1, "None"]
            else:
                return [0, "210 Failed to install SSL for domain. [issueSSLForDomain]"]
        else:

            pathToStoreSSLPrivKey, pathToStoreSSLFullChain = sslUtilities._ssl_live_cert_paths(domain)

            #### if in any case ssl failed to obtain and CyberPanel try to issue self-signed ssl, first check if ssl already present.
            ### if so, dont issue self-signed ssl, as it may override some existing ssl

            if os.path.exists(pathToStoreSSLFullChain):
                import OpenSSL
                from datetime import datetime
                with open(pathToStoreSSLFullChain, 'r') as _cf:
                    _pem = _cf.read()
                x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, _pem)
                SSLProvider = x509.get_issuer().get_components()[1][1].decode('utf-8')

                if SSLProvider != 'Denial':
                    expireData = x509.get_notAfter().decode('ascii')
                    finalDate = datetime.strptime(expireData, '%Y%m%d%H%M%SZ')
                    if (finalDate - datetime.now()).days < 0:
                        msg = (
                            "Renewal failed and the certificate on the server is expired. "
                            "HTTP validation often fails when the domain is behind Cloudflare proxy "
                            "(orange cloud): use DNS-only mode temporarily, or issue SSL via DNS challenge. "
                            "Check /home/cyberpanel/error-logs.txt for ACME details. [issueSSLForDomain]"
                        )
                        logging.CyberCPLogFileWriter.writeToFile(msg)
                        return [0, msg]
                    if sslUtilities.installSSLForDomain(domain) == 1:
                        logging.CyberCPLogFileWriter.writeToFile(
                            "We are not able to get new SSL for " + domain + ". But there is an existing SSL, it might only be for the main domain (excluding www).")
                        return [0,
                                "Could not renew SSL. An older certificate is still installed. "
                                "If you use Cloudflare, turn off proxy (grey cloud) for the site during issuance, "
                                "or use DNS validation. See error logs. [issueSSLForDomain]"]

            if not sslUtilities._ssl_issue_self_signed(domain):
                return [0, "210 Failed to install SSL for domain. [issueSSLForDomain]"]

            if sslUtilities.installSSLForDomain(domain) == 1:
                logging.CyberCPLogFileWriter.writeToFile("Self signed SSL issued for " + domain + ".")
                return [1, "Self signed certificate was issued. [issueSSLForDomain]"]
            else:
                return [0, "210 Failed to install SSL for domain. [issueSSLForDomain]"]

    except BaseException as msg:
        return [0, "347 " + str(msg) + " [issueSSLForDomain]"]

    @staticmethod
    def reconcile_ssl_all():
        """Reconcile SSL configuration for all domains using the new reconciliation module"""
        try:
            from plogical.sslReconcile import SSLReconcile
            return SSLReconcile.reconcile_all()
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error in reconcile_ssl_all: {str(e)}")
            return False

    @staticmethod
    def reconcile_ssl_domain(domain):
        """Reconcile SSL configuration for a specific domain using the new reconciliation module"""
        try:
            from plogical.sslReconcile import SSLReconcile
            return SSLReconcile.reconcile_domain(domain)
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error in reconcile_ssl_domain for {domain}: {str(e)}")
            return False

    @staticmethod
    def fix_acme_challenge_context(virtualHostName):
        """Fix ACME challenge context for a specific domain"""
        try:
            from plogical.sslReconcile import SSLReconcile
            
            vconf_path = f"{sslUtilities.Server_root}/conf/vhosts/{virtualHostName}/vhost.conf"
            
            if not os.path.exists(vconf_path):
                logging.CyberCPLogFileWriter.writeToFile(f"VHost configuration not found: {vconf_path}")
                return False
            
            # Read docRoot from vhost configuration
            docroot = ""
            with open(vconf_path, 'r') as f:
                for line in f:
                    if line.strip().startswith('docRoot'):
                        docroot = line.split()[1]
                        break
            
            if not docroot:
                logging.CyberCPLogFileWriter.writeToFile(f"No docRoot found for {virtualHostName}")
                return False
            
            # Resolve $VH_ROOT variable
            if docroot.startswith('$VH_ROOT/'):
                docroot = docroot.replace('$VH_ROOT', f"/home/{virtualHostName}")
            
            return SSLReconcile.fix_context_location(vconf_path, docroot)
            
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error fixing ACME challenge context for {virtualHostName}: {str(e)}")
            return False