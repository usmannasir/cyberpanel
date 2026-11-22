#!/usr/local/CyberCP/bin/python
import json
import os
import re
import sys
import time
from random import randint
import socket
import shutil
import shlex
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


def container_name_matches(application_name, container_name):
    """Match Docker Compose names across underscore and hyphen separators."""
    if not isinstance(application_name, str) or not isinstance(container_name, str):
        return False
    normalized_application = application_name.lower().replace('-', '_')
    normalized_container = container_name.lower().replace('-', '_')
    return (
        normalized_container == normalized_application
        or normalized_container.startswith(normalized_application + '_')
    )


COMPOSE_PROJECT_LABEL = 'com.docker.compose.project'
COMPOSE_SERVICE_LABEL = 'com.docker.compose.service'
COMPOSE_DIRECTORY_LABEL = 'com.docker.compose.project.working_dir'

SITE_NAME_IN_USE = 'The site name "%s" is in use on this server; choose another.'


def compose_project_names(site_name):
    """The Docker Compose project names the containers of one Docker site can carry.

    A site's containers are started with ``-p <site name>`` and Docker Compose
    records that name in a label on each of them: in lower case and, for a name
    from before site names were limited to lower case letters and digits,
    without the characters it does not allow. Hyphens and underscores are
    allowed: only Docker Compose before 1.21 took them out, and that cannot
    read the compose files of a site. A container belongs to the site only
    when the label is exactly one of these names. Part of a container name
    says nothing: "n" is part of the names of every "n8n" container.
    """
    if not isinstance(site_name, str):
        return []
    lowered = site_name.lower()
    names = []
    for name in (site_name, lowered, re.sub('[^-_a-z0-9]', '', lowered)):
        if name and name not in names:
            names.append(name)
    return names


def site_directory(domain):
    """The directory of the Docker site on a website, or None for a domain that cannot name one."""
    if site_directory_name(domain) is None:
        return None
    return '/home/docker/' + domain


def container_of_site(container, site_name, domain):
    """
    Whether a container is one of the Docker site ``site_name`` on the website ``domain``.

    It must carry the label of the site's Docker Compose project. Another
    project on the server can have the same name, so the directory counts as
    well: Docker Compose records the directory of the compose file a container
    was started from, and for a site that is always its own directory under
    /home/docker. A container started from another directory is not the
    site's. A container without that record, from a Docker Compose too old to
    write it, is taken by its project alone.
    """
    labels = getattr(container, 'labels', None) or {}
    project = labels.get(COMPOSE_PROJECT_LABEL)
    directory = site_directory(domain)

    if not project or project not in compose_project_names(site_name) or directory is None:
        return False

    started_from = labels.get(COMPOSE_DIRECTORY_LABEL)

    if not started_from:
        return True

    if not isinstance(started_from, str):
        return False

    started_from = os.path.normpath(started_from).lower()
    return started_from in (directory.lower(), os.path.realpath(directory).lower())


def site_containers(client, site_name, domain, service=None):
    """Every container, running or not, of one Docker site, optionally of one of its services."""
    found = []
    for project in compose_project_names(site_name):
        labels = ['%s=%s' % (COMPOSE_PROJECT_LABEL, project)]
        if service is not None:
            labels.append('%s=%s' % (COMPOSE_SERVICE_LABEL, service))
        for container in client.containers.list(all=True, filters={'label': labels}):
            if container.id not in [known.id for known in found] and container_of_site(container, site_name, domain):
                found.append(container)
    return found


def site_name_in_use(client, site_name):
    """
    Whether containers on this server already run as the Docker Compose
    project a new site of this name would be started as: the project of
    another Docker site, or one that somebody runs beside the panel. Such a
    site would be started into that project and taken down with it.
    """
    for project in compose_project_names(site_name):
        if client.containers.list(all=True, filters={'label': ['%s=%s' % (COMPOSE_PROJECT_LABEL, project)]}):
            return True
    return False


def compose_command():
    """The Docker Compose command of this server, as the deployment uses it."""
    if ProcessUtilities.decideDistro() in (ProcessUtilities.centos, ProcessUtilities.cent8):
        return 'docker compose'
    return 'docker-compose'


def site_directory_name(domain):
    """Return the domain when it can name a directory under /home/docker, else None."""
    if isinstance(domain, str) and re.fullmatch('[A-Za-z0-9_][A-Za-z0-9_.-]*', domain) and '..' not in domain:
        return domain
    return None


FIRST_SITE_PORT = 11000

## The block SetupAppVhost adds to a website's virtual host, from its comment
## line to the closing brace of the context. Earlier releases wrote the same
## block for n8n sites under another comment and with other header lines.
APP_VHOST_BLOCK = re.compile(
    r'(?:^\n){0,2}^# (?:Docker App|N8N) Proxy Configuration\n^context / \{\n'
    r'(?:(?!^\}).*\n)*?^[ \t]*handler[ \t]+docker[0-9]+[ \t]*\n'
    r'(?:(?!^\}).*\n)*?^\}[ \t]*\n?', re.M)

## A context for the whole website that the panel's Docker sites did not write:
## password protection of the website, or a block somebody added by hand.
OTHER_ROOT_CONTEXT = re.compile(r'^[ \t]*context[ \t]+/[ \t]*\{', re.M)


def app_vhost_problem(domain, content):
    """
    Say why a website cannot be pointed at a Docker application, or None.

    ``content`` is the virtual host of the website. A block the panel left
    there for an earlier Docker site is replaced and is no obstacle. Any other
    context for the whole website stays as it is, and the web server would go
    on using it instead of the application.
    """
    if OTHER_ROOT_CONTEXT.search(APP_VHOST_BLOCK.sub('', content)):
        return ('The website %s already has a "context /" block of its own in its virtual host configuration '
                '(password protection of the whole website, or a block added by hand), so it cannot be pointed '
                'at the application. Remove that block and create the Docker site again.' % domain)
    return None


## The entries SetupProxy adds to the main configuration of the web server for
## a Docker site: an "extprocessor" block on OpenLiteSpeed, a <name> element
## on LiteSpeed Enterprise. Nothing else in that file names a port of a site;
## the names of websites, which are in it too, can hold any text.
SITE_PORT_ENTRIES = (re.compile(r'^extprocessor[ \t]+docker([0-9]{1,5})[ \t]*\{', re.M),
                     re.compile(r'<name>docker([0-9]{1,5})</name>'))


def next_site_port(site_ports, web_server_config=''):
    """
    The loopback port for a new Docker site.

    It is higher than the port of every Docker site there is and of every
    Docker site the web server has ever been told about. A port is therefore
    never handed out twice, and a website that still points at the port of a
    site that was deleted can never reach the container of a new one.
    """
    recorded = []
    for entry in SITE_PORT_ENTRIES:
        recorded.extend(entry.findall(web_server_config or ''))

    highest = FIRST_SITE_PORT - 1
    for port in list(site_ports) + recorded:
        try:
            port = int(port)
        except (TypeError, ValueError):
            continue
        if 0 < port <= 65535:
            highest = max(highest, port)
    if highest >= 65535:
        raise ValueError('No port is left for a new Docker site.')
    return str(highest + 1)


def compose_file(config):
    """
    Render a Docker Compose file from a dictionary.

    JSON is valid Compose YAML. Written this way a value from the creation page
    stays the one value it is, whatever quotes, line breaks or other characters
    it holds, and Docker Compose does not take a dollar sign in it for one of
    its own variables.
    """
    def escape(value):
        if isinstance(value, dict):
            return {key: escape(item) for key, item in value.items()}
        if isinstance(value, list):
            return [escape(item) for item in value]
        return value.replace('$', '$$') if isinstance(value, str) else value

    return json.dumps(escape(config), indent=2)


def environment_list(values):
    """A Compose environment section, one "NAME=value" entry per variable."""
    return ['%s=%s' % (name, value) for name, value in values.items()]


## Registry of the one-click applications offered on the Docker Site creation page.
##
## siteType   -> value stored in DockerSites.SiteType so the panel can tell apps apart
## requiresDB -> the app ships its own database container in the compose file
## deploy     -> Docker_Sites function used to deploy the app
## compose    -> Docker_Sites method that renders the compose file (None when the
##               deployment function writes its own compose content inline)
## minSiteRam -> minimum RAM (MB) the application container needs to run
## firstRun   -> optional Docker_Sites method that completes the application's own
##               first-run setup after its containers are up and before the website
##               is pointed at them
## dataOwner  -> optional "uid:gid" of the user the application's image runs as, for
##               an image that does not run as root: its data directory is created
##               for that user before the containers start

DOCKER_APPS = {
    'WordPress': {
        'siteType': 1,
        'requiresDB': True,
        'deploy': 'DeployWPContainer',
        'compose': 'generate_wordpress_compose_config',
        'minSiteRam': 256,
    },
    'n8n': {
        'siteType': 3,
        'requiresDB': True,
        'deploy': 'DeployN8NContainer',
        'compose': 'generate_compose_config',
        'minSiteRam': 256,
        'firstRun': 'create_n8n_owner',
        'dataOwner': '1000:1000',
    },
    'Hermes': {
        'siteType': 4,
        'requiresDB': False,
        'deploy': 'DeployHermesContainer',
        'compose': 'generate_hermes_compose_config',
        'minSiteRam': 2048,
    },
}


N8N_PASSWORD_RULE = ('n8n needs an administrator password of 8 to 64 characters '
                     'with at least one number and one uppercase letter.')


def n8n_password_problem(password):
    """Say what n8n would refuse about an owner password, or None.

    n8n applies this rule when its owner account is created. The creation page
    applies it first so that the customer hears about it at once and not after
    the containers have been started and removed again.
    """
    if (not isinstance(password, str) or not 8 <= len(password) <= 64
            or not re.search('[0-9]', password) or not re.search('[A-Z]', password)):
        return N8N_PASSWORD_RULE
    return None


def n8n_container_remarks(attrs):
    """
    What an administrator should know about an n8n container that an earlier
    version of the panel started, read from the container's inspection data.
    """
    remarks = []
    config = attrs.get('Config') or {}

    for binding in ((attrs.get('HostConfig') or {}).get('PortBindings') or {}).get('5678/tcp') or []:
        if binding.get('HostIp') not in ('127.0.0.1', '::1'):
            remarks.append('port %s is published on every address of the server and can be reached past the '
                           'website and the firewall' % binding.get('HostPort'))

    if 'N8N_ENCRYPTION_KEY=auto' in (config.get('Env') or []):
        remarks.append('stored credentials are encrypted with the key every older site shares')

    if config.get('User') in ('root', '0', '0:0'):
        remarks.append('runs as root and keeps its settings inside the container, where they are lost when '
                       'the container is created again')

    return remarks


def n8n_owner_missing(port, timeout=10):
    """True when the n8n instance on this loopback port still offers its owner account to the first visitor,
    False when it has an owner, None when it does not answer."""
    import requests

    session = requests.Session()
    session.trust_env = False

    try:
        answer = session.get('http://127.0.0.1:%s/rest/settings' % int(port), timeout=timeout).json()
        return answer['data']['userManagement']['showSetupOnFirstLoad'] is True
    except BaseException:
        return None


class DockerDeploymentError(Exception):
    def __init__(self, message, error_code=None, recovery_possible=True):
        self.message = message
        self.error_code = error_code
        self.recovery_possible = recovery_possible
        super().__init__(self.message)

class Docker_Sites(multi.Thread):
    Wordpress = 1
    Joomla = 2
    N8N = 3
    Hermes = 4

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
            elif self.function_run == 'DeployHermesContainer':
                self.DeployHermesContainer()


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
        """Backwards compatible name, kept because it is also called over the CLI."""
        return Docker_Sites.SetupAppVhost(domain, port)

    @staticmethod
    def SetupAppVhost(domain, port):
        """Point the domain vhost at the app container through the OpenLiteSpeed proxy.

        Used by every proxied Docker app (n8n, Hermes), all of which need the same
        websocket enabled proxy context and forwarded headers.
        """
        try:
            problem = Docker_Sites.AppVhostProblem(domain)

            if problem is not None:
                # The deployment reads this line and shows it to the customer.
                print(problem)
                return False

            vhost_path = f'/usr/local/lsws/conf/vhosts/{domain}/vhost.conf'

            # Read existing vhost configuration
            with open(vhost_path, 'r') as f:
                content = f.read()

            # A block the panel left behind for a Docker site that is gone would
            # keep pointing the domain at that site's port.
            remaining = APP_VHOST_BLOCK.sub('', content)
            if remaining != content:
                content = remaining
                with open(vhost_path, 'w') as f:
                    f.write(content)

            # Add proxy context with proper headers for the app container
            # NOTE: Do NOT include "RequestHeader set Origin" - OpenLiteSpeed cannot override
            # browser Origin headers, which is why n8n needs NODE_ENV=development
            proxy_context = f'''

# Docker App Proxy Configuration
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
            logging.writeToFile(f'Error setting up app vhost: {str(e)}')
            return False

    @staticmethod
    def AppVhostProblem(domain):
        """Say why the virtual host of a website cannot be pointed at a Docker application, or None."""
        vhost_path = f'/usr/local/lsws/conf/vhosts/{domain}/vhost.conf'

        try:
            if site_directory_name(domain) is None or not os.path.exists(vhost_path):
                logging.writeToFile(f"Error: Vhost file not found at {vhost_path}")
                return 'The website %s has no virtual host configuration to point at the application.' % domain

            with open(vhost_path, 'r') as f:
                problem = app_vhost_problem(domain, f.read())

        except Exception as e:
            logging.writeToFile(f'Error reading the app vhost: {str(e)}')
            return 'The virtual host configuration of %s could not be read.' % domain

        if problem is not None:
            logging.writeToFile(problem)

        return problem

    @staticmethod
    def RemoveAppVhost(domain):
        """Take the proxy context the panel added for a Docker site out of the domain's virtual host."""
        try:
            if site_directory_name(domain) is None:
                return False

            vhost_path = f'/usr/local/lsws/conf/vhosts/{domain}/vhost.conf'

            if not os.path.exists(vhost_path):
                return False

            with open(vhost_path, 'r') as f:
                content = f.read()

            remaining = APP_VHOST_BLOCK.sub('', content)

            if remaining == content:
                return False

            with open(vhost_path, 'w') as f:
                f.write(remaining)

            logging.writeToFile(f"Removed the Docker app proxy context of {domain}")
            return True

        except Exception as e:
            logging.writeToFile(f'Error removing app vhost: {str(e)}')
            return False

    @staticmethod
    def htaccess_rules(port, domain=None):
        """The lines the panel adds to a website's .htaccess for a Docker site."""
        rules = f'''
RewriteEngine On
REWRITERULE ^(.*)$ HTTP://docker{port}/$1 [P]
'''
        if domain:
            rules = ('RewriteEngine On\nRewriteCond %{HTTPS} !=on\n'
                'RewriteRule ^ https://' + domain + '%{REQUEST_URI} [R=301,L]\n'
                + rules)
        return rules

    @staticmethod
    def SetupHTAccess(port, htaccess, domain=None):
        ### Update htaccess

        StringCheck = f'docker{port}'

        try:
            Content = open(htaccess, 'r').read()
        except:
            Content = ''

        print(f'value of content {Content}')

        if Content.find(StringCheck) == -1:
            WriteToFile = open(htaccess, 'a')
            WriteToFile.write(Docker_Sites.htaccess_rules(port, domain))
            WriteToFile.close()

    @staticmethod
    def RemoveHTAccess(htaccess, domain=None):
        """
        Take the panel's Docker site rules out of a website's .htaccess.

        Runs as the website's own account. Everything the customer has in the
        file stays; the file itself is removed only when the panel's rules were
        all it held. The file is read and written as bytes: it is the
        customer's, in whatever encoding and with whatever line ends it has,
        and nothing but the panel's lines is changed in it.
        """
        try:
            with open(htaccess, 'rb') as handle:
                Content = handle.read()
        except (IOError, OSError):
            return 0

        ports = set(re.findall(br'HTTP://docker(\d+)/\$1 \[P\]', Content))
        Remaining = Content

        for port in ports:
            number = port.decode('ascii')
            if domain:
                Remaining = Remaining.replace(Docker_Sites.htaccess_rules(number, domain).encode('utf-8'), b'')
            Remaining = Remaining.replace(Docker_Sites.htaccess_rules(number).encode('utf-8'), b'')
            # The rule alone, where the lines around it were changed by hand.
            Remaining = re.sub(br'(?m)^[ \t]*REWRITERULE \^\(\.\*\)\$ HTTP://docker%s/\$1 \[P\][ \t]*\r?\n?' % port,
                               b'', Remaining)

        if Remaining == Content:
            return 0

        if Remaining.strip() == b'':
            os.remove(htaccess)
        else:
            with open(htaccess, 'wb') as handle:
                handle.write(Remaining)

        return 1

    # Takes
    # ComposePath, MySQLPath, MySQLRootPass, MySQLDBName, MySQLDBNUser, MySQLPassword, CPUsMySQL, MemoryMySQL,
    # port, SitePath, CPUsSite, MemorySite, ComposePath, SiteName
    # finalURL, blogTitle, adminUser, adminPassword, adminEmail, htaccessPath, externalApp

    def generate_wordpress_compose_config(self):
        name = self.data['ServiceName']
        directory = '/home/docker/' + self.data['finalURL']
        probe = ('$context=stream_context_create(["http"=>["header"=>'
                 + json.dumps('Host: ' + self.data['finalURL'])
                 + ',"follow_location"=>0,"timeout"=>5]]); '
                 '$page=@file_get_contents("http://127.0.0.1:8088/wp-login.php", false, $context); '
                 'exit(is_string($page) && strpos($page, "id=\\\"loginform\\\"") !== false ? 0 : 1);')
        config = {'services': {
            name: {
                'image': 'cyberpanel/openlitespeed:latest',
                'user': 'root',
                'entrypoint': ['/bin/bash', '/usr/local/bin/entrypoint.sh'],
                'ports': ['127.0.0.1:%s:8088' % self.data['port']],
                'environment': {
                    'DB_NAME': self.data['MySQLDBName'], 'DB_USER': self.data['MySQLDBNUser'],
                    'DB_PASSWORD': self.data['MySQLPassword'],
                    'WP_ADMIN_EMAIL': self.data['adminEmail'], 'WP_ADMIN_USER': self.data['adminUser'],
                    'WP_ADMIN_PASSWORD': self.data['adminPassword'],
                    'WP_URL': 'https://' + self.data['finalURL'],
                    'DB_Host': name + '-db:3306', 'SITE_NAME': self.data['SiteName'],
                },
                'volumes': [directory + '/data:/usr/local/lsws/Example/html',
                            '/usr/local/CyberCP/dockerManager/entrypoint.sh:/usr/local/bin/entrypoint.sh:ro'],
                'depends_on': [name + '-db'],
                'healthcheck': {
                    'test': ['CMD-SHELL', 'test -f /tmp/cyberpanel-wordpress-ready && '
                             '/usr/local/lsws/lsphp82/bin/php -r ' + shlex.quote(probe)],
                    'interval': '5s', 'timeout': '10s', 'retries': 60, 'start_period': '20s',
                },
                'deploy': {'resources': {'limits': {
                    'cpus': str(self.data['CPUsSite']), 'memory': str(self.data['MemorySite']) + 'M'}}},
            },
            name + '-db': {
                'image': 'mariadb', 'restart': 'always',
                'environment': {
                    'MYSQL_DATABASE': self.data['MySQLDBName'], 'MYSQL_USER': self.data['MySQLDBNUser'],
                    'MYSQL_PASSWORD': self.data['MySQLPassword'], 'MYSQL_ROOT_PASSWORD': self.data['MySQLRootPass'],
                },
                'volumes': [directory + '/db:/var/lib/mysql'],
                'deploy': {'resources': {'limits': {
                    'cpus': str(self.data['CPUsMySQL']), 'memory': str(self.data['MemoryMySQL']) + 'M'}}},
            },
        }}

        return compose_file(config)

    def create_site_directory(self, data_owner=None):
        """
        Create /home/docker/<domain> for root alone, and return (1, None) or (0, the error).

        The containers of a site write into this directory as whatever user they
        run as inside, root included. No other account of the server can enter
        it, so nothing a container leaves there can be opened or run from the
        host. An application whose image runs as its own user gets its data
        directory created for that user; Docker would create it for root.
        """
        directory = '/home/docker/' + self.data['finalURL']
        commands = [f"install -d -m 700 -o root -g root {shlex.quote(directory)}"]

        if data_owner:
            owner, group = data_owner.split(':')
            commands.append(f"install -d -m 700 -o {int(owner)} -g {int(group)} {shlex.quote(directory + '/data')}")

        for command in commands:
            result, message = ProcessUtilities.outputExecutioner(command, None, None, None, 1)
            if result == 0:
                return 0, message

        return 1, None

    def install_compose_file(self, content):
        """
        Put the compose file of the site in place, and return (1, None) or (0, the error).

        The file holds the passwords of the site. It is written where only the
        panel can read it and handed to root in one step that also sets its
        owner and mode, so there is no moment at which another account of the
        server could read it.
        """
        temporary = f'/home/cyberpanel/{self.data["finalURL"]}-docker-compose.yml'

        try:
            os.remove(temporary)
        except OSError:
            pass

        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w') as handle:
            handle.write(content)

        command = f"install -m 600 -o root -g root {shlex.quote(temporary)} {shlex.quote(self.data['ComposePath'])}"
        result, message = ProcessUtilities.outputExecutioner(command, None, None, None, 1)

        try:
            os.remove(temporary)
        except OSError:
            pass

        return (1, None) if result else (0, message)

    def wait_for_wordpress(self, attempts=60, delay=5):
        client = docker.from_env()
        for _ in range(attempts):
            containers = client.containers.list(all=True, filters={'label': [
                'com.docker.compose.project=' + self.data['SiteName'],
                'com.docker.compose.service=' + self.data['ServiceName'],
            ]})
            if len(containers) == 1:
                container = containers[0]
                if container.status in ('exited', 'dead', 'restarting'):
                    raise DockerDeploymentError('WordPress initialization failed; inspect the application container logs.')
                health = container.attrs.get('State', {}).get('Health', {}).get('Status')
                if container.status == 'running' and health == 'healthy':
                    return True
            time.sleep(delay)
        raise DockerDeploymentError('WordPress installation did not become ready within five minutes.')

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

            WPSite = self.generate_wordpress_compose_config()

            ### WriteConfig to compose-file

            result, message = self.create_site_directory()

            if result == 0:
                logging.statusWriter(self.JobID, f'Error {str(message)} . [404]')
                return 0

            result, message = self.install_compose_file(WPSite)

            if result == 0:
                logging.statusWriter(self.JobID, f'Error {str(message)} . [404]')
                return 0

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

            self.wait_for_wordpress()

            ### Set up Proxy

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py"
            execPath = execPath + f" SetupProxy --port {self.data['port']}"
            ProcessUtilities.executioner(execPath)

            ### Set up ht access

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py"
            execPath = execPath + f" SetupHTAccess --port {self.data['port']} --htaccess {self.data['htaccessPath']} --domain {self.data['finalURL']}"
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
            App = self.data.get('App')

            if App not in DOCKER_APPS:
                logging.statusWriter(self.JobID, f'Unknown application: {App}. [404]')
                return 0

            AppMeta = DOCKER_APPS[App]

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

            else:

                ## The website was there before this request. The page that started
                ## this job has already refused callers who do not own it; the job
                ## runs later, so it asks again before it touches the website.

                from loginSystem.models import Administrator
                if ACLManager.checkOwnership(Domain, Administrator.objects.get(pk=userID),
                                             ACLManager.loadedACL(userID)) != 1:
                    logging.statusWriter(tempStatusPath, 'You do not own this website. [404]')
                    return 0

            ## Every path and command below is built from the stored domain, not
            ## from the text of the request, which the database matches loosely.

            webobj = Websites.objects.get(domain=Domain)
            Domain = webobj.domain

            if webobj.dockersites_set.all().count() > 0:
                logging.statusWriter(self.JobID, f'Docker container already exists on this domain. [404]')
                return 0

            ## The page that started this job has asked already; the job asks
            ## again just before it gives the name to the site.

            problem = self.site_name_problem(sitename)

            if problem is not None:
                logging.statusWriter(tempStatusPath, problem + ' [404]')
                return 0

            dbname = randomPassword.generate_pass()
            dbpasswd = randomPassword.generate_pass()
            dbusername = randomPassword.generate_pass()
            MySQLRootPass = randomPassword.generate_pass()

            ## Without the web server's record of the ports it was given, the port
            ## of a site that was deleted could be chosen again.

            web_server_config = Docker_Sites.web_server_config()

            if web_server_config is None:
                logging.statusWriter(tempStatusPath, 'The configuration of the web server could not be read, so no '
                                                     'port could be chosen. The Docker site was not created. [404]')
                return 0

            port = next_site_port(DockerSites.objects.values_list('port', flat=True), web_server_config)

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
                "docRoot": f"/home/{Domain}",
                "dashboardSecret": randomPassword.generate_pass(32),
                "App": App
            }

            dockersiteobj = DockerSites(
                admin=webobj, ComposePath=f"/home/{Domain}/docker-compose.yml",
                SitePath=f'/home/{Domain}/public_html/wpdocker',
                MySQLPath=f'/home/{Domain}/public_html/sqldocker', SiteType=AppMeta['siteType'], MySQLDBName=dbname,
                MySQLDBNUser=dbusername, CPUsMySQL=MysqlCPU, MemoryMySQL=MYsqlRam, port=port, CPUsSite=SiteCPU,
                MemorySite=SiteRam,
                SiteName=sitename, finalURL=Domain, blogTitle=sitename, adminUser=WPusername, adminEmail=WPemal
            )
            dockersiteobj.save()

            background = Docker_Sites(AppMeta['deploy'], f_data)
            background.start()

        except BaseException as msg:
            logging.writeToFile("Error Submit Docker site Creation ....... %s" % str(msg))

            ## The creation page waits for this file to say how the job ended.
            try:
                logging.statusWriter(self.data.get('JobID'),
                                     'The Docker site could not be created: %s [404]' % ' '.join(str(msg).split()))
            except BaseException:
                pass

            return 0

    @staticmethod
    def site_name_problem(site_name):
        """
        Say why a new Docker site cannot have this name, or None: another
        Docker site has it, or containers on the server already run as its
        Docker Compose project. A server whose Docker does not answer has no
        such containers running, and nothing can be started on it either.
        """
        from websiteFunctions.models import DockerSites

        if DockerSites.objects.filter(SiteName=site_name).count() > 0:
            return SITE_NAME_IN_USE % site_name

        try:
            in_use = site_name_in_use(docker.from_env(), site_name)
        except BaseException as msg:
            logging.writeToFile('Docker did not answer when the site name %s was checked: %s' % (site_name, str(msg)))
            in_use = False

        return SITE_NAME_IN_USE % site_name if in_use else None

    def DeleteDockerApp(self):
        try:

            domain = site_directory_name(self.data.get('domain'))
            name = self.data.get('name')

            if domain is None:
                logging.writeToFile("Error Delete Docker APP ....... no usable domain was given.")
                return 0

            ## The containers were started as the Compose project named after the
            ## site, so that is the project to take down, with the volumes its
            ## compose file declares. Whatever is left of the project afterwards
            ## is removed by its label. Containers of other sites are never
            ## selected, whatever their names contain.

            compose = f'/home/docker/{domain}/docker-compose.yml'

            for project in compose_project_names(name):
                command = f'{compose_command()} -f {shlex.quote(compose)} -p {shlex.quote(project)} down -v'
                ProcessUtilities.executioner(command)

            client = docker.from_env()
            containers = site_containers(client, name, domain)

            logging.writeToFile(f'List of containers {str(containers)}')

            for container in containers:
                command = f'docker rm -f {shlex.quote(container.id)}'
                ProcessUtilities.executioner(command)

            command = f'rm -rf {shlex.quote("/home/docker/" + domain)}'
            ProcessUtilities.executioner(command)

            ## The website's .htaccess belongs to the customer. Only the rules the
            ## panel added for the Docker site are taken out of it, and by the
            ## website's own account, which reaches nothing but its own files.

            account = self.website_account(domain)

            if account is not None:
                execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py"
                execPath = execPath + f" RemoveHTAccess --htaccess /home/{domain}/public_html/.htaccess --domain {domain}"
                ProcessUtilities.executioner(execPath, account)

            ## The virtual host must not go on pointing at the port of a site that is gone.

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py"
            execPath = execPath + f" RemoveAppVhost --domain {domain}"
            ProcessUtilities.executioner(execPath)

            from plogical.installUtilities import installUtilities
            installUtilities.reStartLiteSpeed()

        except BaseException as msg:
            logging.writeToFile("Error Delete Docker APP ....... %s" % str(msg))
            return 0

    @staticmethod
    def web_server_config():
        """
        The main configuration of the web server, where SetupProxy records every
        Docker site port, or None when it cannot be read.
        """
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            path = '/usr/local/lsws/conf/httpd_config.conf'
        else:
            path = '/usr/local/lsws/conf/httpd_config.xml'
        try:
            answer = ProcessUtilities.outputExecutioner('cat ' + path, None, None, None, 1)
            result, content = answer if isinstance(answer, tuple) and len(answer) == 2 else (0, None)
            if result and isinstance(content, str) and content.strip():
                return content
            logging.writeToFile('Error reading the web server configuration %s' % path)
        except BaseException as msg:
            logging.writeToFile('Error reading the web server configuration: %s' % str(msg))
        return None

    def website_account(self, domain):
        """The system account of the website a Docker site is installed on, or None."""
        try:
            from websiteFunctions.models import Websites
            account = Websites.objects.get(domain=domain).externalApp
        except BaseException as msg:
            logging.writeToFile("Error Delete Docker APP ....... no account for %s: %s" % (domain, str(msg)))
            return None

        if isinstance(account, str) and re.fullmatch('[A-Za-z0-9_][A-Za-z0-9_-]*', account):
            return account
        return None

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

            # Compose v1 and v2 use different separators. Normalize both instead
            # of assuming a separator from the operating system.
            containers = []
            search_name = self.DockerAppName
            
            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(f'Searching for containers with name containing: {search_name}')

            for container in all_containers:
                if os.path.exists(ProcessUtilities.debugPath):
                    logging.writeToFile(f'Checking container: {container.name} against filter: {search_name}')
                if container_name_matches(search_name, container.name):
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

        The container is the one Docker Compose labelled with this site's project
        and the given service. Names are not compared: they vary with the Docker
        Compose version, and part of another site's name can equal this one.
        """
        try:
            logging.writeToFile(f'Checking container health for service: {service_name}')

            for attempt in range(max_retries):
                container = self.find_container_by_service(service_name)

                if container is None:
                    logging.writeToFile(f'No container found matching service: {service_name}, attempt {attempt + 1}/{max_retries}')
                    time.sleep(delay)
                    continue

                health = container.attrs.get('State', {}).get('Health', {}).get('Status')

                if container.status == 'running':

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

    def cleanup_failed_deployment(self):
        try:
            # Stop and remove the containers of this site's project, and nothing else
            for project in compose_project_names(self.data['SiteName']):
                command = (f"{compose_command()} -f {shlex.quote(self.data['ComposePath'])} "
                           f"-p {shlex.quote(project)} down -v")
                ProcessUtilities.outputExecutioner(command, None, None, None, 1)

            for container in site_containers(docker.from_env(), self.data['SiteName'], self.data['finalURL']):
                command = f'docker rm -f {shlex.quote(container.id)}'
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
        Find the container of one service of this site's Docker Compose project.
        Returns the container object or None if not found.
        """
        try:
            containers = site_containers(docker.from_env(), self.data['SiteName'], self.data['finalURL'],
                                         service_name)
            return containers[0] if containers else None
        except Exception as e:
            logging.writeToFile(f'Error finding container: {str(e)}')
            return None

    def monitor_deployment(self, requiresDB=True):
        try:
            # Find containers dynamically using fuzzy matching
            n8n_container = self.find_container_by_service(self.data['ServiceName'])
            db_container = self.find_container_by_service(f"{self.data['ServiceName']}-db") if requiresDB else None

            if not n8n_container or (requiresDB and not db_container):
                raise DockerDeploymentError("Could not find app or database containers")

            n8n_container_name = n8n_container.name
            db_container_name = db_container.name if db_container else ''

            logging.writeToFile(f'Monitoring containers: {n8n_container_name} and {db_container_name}')

            # Only raise error if container is exited
            if n8n_container.status == 'exited':
                # Get container logs
                command = f"docker logs {n8n_container_name}"
                result, logs = ProcessUtilities.outputExecutioner(command, None, None, None, 1)
                raise DockerDeploymentError(f"Container exited. Logs: {logs}")

            # Wait for database to be ready
            max_retries = 30
            retry_count = 0
            db_ready = not requiresDB

            while requiresDB and retry_count < max_retries:
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

    def app_vhost_step(self, arguments):
        """
        Run one virtual host helper of this file as root. When the helper says
        the website cannot be pointed at the application, the deployment fails
        with what the helper printed instead of ending as completed.
        """
        command = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py " + arguments
        answer = ProcessUtilities.outputExecutioner(command, None, None, None, 1)
        result, output = answer if isinstance(answer, tuple) and len(answer) == 2 else (0, '')

        if result:
            return True

        lines = [line.strip() for line in str(output or '').splitlines() if line.strip()]
        raise DockerDeploymentError(lines[-1] if lines else
                                    'The website could not be pointed at the application.')

    def DeployN8NContainer(self):
        return self.DeployComposeApp('n8n')

    def DeployHermesContainer(self):
        return self.DeployComposeApp('Hermes')

    def DeployComposeApp(self, app='n8n'):
        """
        Main deployment method with error handling, shared by every compose based app
        """
        meta = DOCKER_APPS[app]
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

                # A website that cannot be pointed at the application is refused
                # now, not after its containers have been started.
                self.app_vhost_step(f"CheckAppVhost --domain {self.data['finalURL']}")

                # Create directories
                result, message = self.create_site_directory(meta.get('dataOwner'))
                if result == 0:
                    raise DockerDeploymentError(f"Failed to create directories: {message}")
                logging.statusWriter(self.JobID, 'Directories created...,30')

                # Generate and write docker-compose file
                self.data['ServiceName'] = self.data["SiteName"].replace(' ', '-')
                compose_config = getattr(self, meta['compose'])()
                
                result, message = self.install_compose_file(compose_config)
                if result == 0:
                    raise DockerDeploymentError(f"Failed to move compose file: {message}")
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
                if meta['requiresDB'] and not self.check_container_health(f"{self.data['ServiceName']}-db"):
                    raise DockerDeploymentError("Containers failed to reach healthy state", self.ERROR_CONTAINER_FAILED)
                if not self.check_container_health(self.data['ServiceName']):
                    raise DockerDeploymentError("Containers failed to reach healthy state", self.ERROR_CONTAINER_FAILED)
                logging.statusWriter(self.JobID, 'Containers healthy...,70')

                # The website is pointed at the containers only after the
                # application has been given its administrator.
                if meta.get('firstRun'):
                    getattr(self, meta['firstRun'])()
                    logging.statusWriter(self.JobID, f'{app} administrator created...,75')

                # Setup proxy
                execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/DockerSites.py"
                execPath = execPath + f" SetupProxy --port {self.data['port']}"
                ProcessUtilities.executioner(execPath)
                logging.statusWriter(self.JobID, 'Proxy configured...,80')

                # Setup the app vhost configuration instead of htaccess
                self.app_vhost_step(f"SetupAppVhost --domain {self.data['finalURL']} --port {self.data['port']}")
                logging.statusWriter(self.JobID, f'{app} vhost configured...,90')

                # Restart web server
                from plogical.installUtilities import installUtilities
                installUtilities.reStartLiteSpeedSocket()

                # Monitor deployment
                metrics = self.monitor_deployment(meta['requiresDB'])
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

    def create_n8n_owner(self, attempts=150, delay=2):
        """
        Create the n8n owner account with the credentials from the creation page.

        A new n8n instance gives its owner account to the first caller of its
        setup address. The container is published on 127.0.0.1 only and the
        website does not proxy to it yet, so that caller is the panel. Anything
        but a created owner fails the deployment, and a failed deployment is
        removed: an instance that somebody else has claimed is never published.
        """
        import requests

        # n8n takes a name of up to 32 characters and refuses one that looks like
        # markup or an address, which a user name with a dot in it does.
        name = re.sub(r'[^\w -]', '', str(self.data.get('adminUser') or '')).strip()[:32]

        owner = {
            'email': self.data['adminEmail'],
            'firstName': name or 'Administrator',
            'lastName': 'Admin',
            'password': self.data['adminPassword'],
        }
        url = 'http://127.0.0.1:%s/rest/owner/setup' % int(self.data['port'])

        session = requests.Session()
        session.trust_env = False

        for _ in range(attempts):
            try:
                response = session.post(url, json=owner, timeout=30)
                answer = response.json()
            except (requests.RequestException, ValueError):
                # Not listening yet, or still answering every address with its
                # "n8n is starting up" page.
                time.sleep(delay)
                continue

            if response.status_code == 200 and isinstance(answer, dict) and isinstance(answer.get('data'), dict):
                logging.writeToFile('n8n owner account created for %s' % self.data['finalURL'])
                return True

            reason = answer.get('message') if isinstance(answer, dict) else None
            raise DockerDeploymentError('n8n did not accept the administrator account: %s' % (
                reason or 'HTTP %s' % response.status_code))

        raise DockerDeploymentError('n8n did not become ready to create its administrator account.')

    @staticmethod
    def CheckN8NSites():
        """
        Report the n8n sites that were deployed the way earlier versions did it.

        Nothing is changed. A site is listed with what is open about it: an
        instance without an owner account, a port published on every address,
        the shared encryption key, a container that runs as root.
        """
        from websiteFunctions.models import DockerSites

        report = []
        client = docker.from_env()

        for site in DockerSites.objects.filter(SiteType=Docker_Sites.N8N):
            remarks = []

            if n8n_owner_missing(site.port) is True:
                remarks.append('HAS NO OWNER ACCOUNT: whoever opens it first becomes its owner')

            # The application container only: the database container beside it is not n8n.
            for container in site_containers(client, site.SiteName, site.admin.domain,
                                             site.SiteName.replace(' ', '-')):
                for remark in n8n_container_remarks(container.attrs):
                    if remark not in remarks:
                        remarks.append(remark)

            for remark in remarks:
                report.append('%s (%s): %s' % (site.admin.domain, site.SiteName, remark))

        return report

    def n8n_encryption_key(self):
        """
        The key a new n8n site encrypts its stored credentials with.

        Every site gets a random key of its own. It is made once for a
        deployment and then lives in the site's compose file, which only root
        can read, and from there in the settings n8n keeps in its data
        directory. A site that is already running is never given another key:
        its compose file is not written again, and with another key n8n could
        no longer read what it has stored.
        """
        if not self.data.get('n8nEncryptionKey'):
            self.data['n8nEncryptionKey'] = randomPassword.generate_pass(32)
        return self.data['n8nEncryptionKey']

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
                'N8N_ENCRYPTION_KEY': self.n8n_encryption_key(),
                'N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS': 'true',
                'DB_POSTGRESDB_SCHEMA': 'public',
                'N8N_PROTOCOL': 'https',
                'N8N_SECURE_COOKIE': 'true'
            }
        }

        name = self.data['ServiceName']
        directory = '/home/docker/' + self.data['finalURL']

        return compose_file({
            'version': '3.8',
            'volumes': {'db_storage': {'driver': 'local'}, 'n8n_storage': {'driver': 'local'}},
            'services': {
                name + '-db': {
                    'image': postgres_config['image'],
                    'user': postgres_config['user'],
                    'restart': 'always',
                    'healthcheck': postgres_config['healthcheck'],
                    'environment': environment_list(postgres_config['environment']),
                    'volumes': [directory + '/db:/var/lib/postgresql/data'],
                    'networks': ['n8n-network'],
                    'deploy': {'resources': {'limits': {
                        'cpus': str(self.data['CPUsMySQL']), 'memory': str(self.data['MemoryMySQL']) + 'M'}}},
                },
                name: {
                    'image': n8n_config['image'],
                    'restart': 'always',
                    'healthcheck': n8n_config['healthcheck'],
                    'environment': environment_list(n8n_config['environment']),
                    'ports': ['127.0.0.1:%s:5678' % self.data['port']],
                    'depends_on': [name + '-db'],
                    'volumes': [directory + '/data:/home/node/.n8n'],
                    'networks': ['n8n-network'],
                    'deploy': {'resources': {'limits': {
                        'cpus': str(self.data['CPUsSite']), 'memory': str(self.data['MemorySite']) + 'M'}}},
                },
            },
            'networks': {'n8n-network': {'driver': 'bridge', 'name': name + '_network'}},
        })

    def generate_hermes_compose_config(self):
        """
        Generate the docker-compose configuration for Hermes Agent.

        Hermes keeps all of its state in /opt/data and needs no database container.
        The dashboard is the only surface we expose, and it is published on loopback
        only because OpenLiteSpeed reaches the container over 127.0.0.1 (see SetupProxy).
        A non loopback bind inside the container engages the Hermes auth gate, so the
        basic auth credentials below are mandatory, without them Hermes refuses to start.
        """

        hermes_config = {
            'image': 'nousresearch/hermes-agent:latest',
            'healthcheck': {
                'test': ["CMD-SHELL",
                         "python3 -c \"import socket; socket.create_connection(('127.0.0.1', 9119), 5).close()\""],
                'interval': '20s',
                'timeout': '10s',
                'retries': 3,
                'start_period': '60s'
            },
            'environment': {
                'HERMES_DASHBOARD': '1',
                'HERMES_DASHBOARD_HOST': '0.0.0.0',
                'HERMES_DASHBOARD_PORT': '9119',
                'HERMES_DASHBOARD_PUBLIC_URL': f"https://{self.data['finalURL']}",
                'HERMES_DASHBOARD_BASIC_AUTH_USERNAME': self.data['adminUser'],
                'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD': self.data['adminPassword'],
                'HERMES_DASHBOARD_BASIC_AUTH_SECRET': self.data['dashboardSecret'],
            }
        }

        name = self.data['ServiceName']

        return compose_file({
            'version': '3.8',
            'services': {
                name: {
                    'image': hermes_config['image'],
                    'restart': 'always',
                    'command': 'gateway run',
                    'healthcheck': hermes_config['healthcheck'],
                    'environment': environment_list(hermes_config['environment']),
                    'ports': ['127.0.0.1:%s:9119' % self.data['port']],
                    'volumes': ['/home/docker/' + self.data['finalURL'] + '/data:/opt/data'],
                    'networks': ['hermes-network'],
                    'deploy': {'resources': {'limits': {
                        'cpus': str(self.data['CPUsSite']), 'memory': str(self.data['MemorySite']) + 'M'}}},
                },
            },
            'networks': {'hermes-network': {'driver': 'bridge', 'name': name + '_network'}},
        })

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
            Docker_Sites.SetupHTAccess(args.port, args.htaccess, args.domain)
        elif args.function == 'RemoveHTAccess':
            Docker_Sites.RemoveHTAccess(args.htaccess, args.domain)
        elif args.function == 'SetupN8NVhost' or args.function == 'SetupAppVhost':
            if not Docker_Sites.SetupAppVhost(args.domain, args.port):
                return 1
        elif args.function == 'CheckAppVhost':
            problem = Docker_Sites.AppVhostProblem(args.domain)
            if problem is not None:
                print(problem)
                return 1
        elif args.function == 'RemoveAppVhost':
            Docker_Sites.RemoveAppVhost(args.domain)
        elif args.function == 'CheckN8NSites':
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
            django.setup()
            report = Docker_Sites.CheckN8NSites()
            print('\n'.join(report) if report else 'No n8n site needs attention.')
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
    sys.exit(Main())
