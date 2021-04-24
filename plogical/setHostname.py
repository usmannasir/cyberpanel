import os
import re
import shlex
import subprocess


def setHostname(hostname):
    # First, make sure it's legal
    hostname = re.sub(' ', '-', hostname.strip())
    hostname = re.sub('[^a-zA-Z0-9\-]', '', hostname).strip()
    if hostname is '' or len(hostname) > 63:
        return False

    # Next, let's edit the relevant files....
    with open('/etc/hostname', 'w') as f:
        f.write(f'{hostname}\n')

    # Mailname file create if not exists and open for writing
    with open('/etc/mailname', 'w+') as f:
        f.write(f'{hostname}\n')

    lines = []
    with open('/etc/hosts', 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('127.0.1.1'):
                line = '127.0.1.1\t%s' % hostname
            lines.append(line)
    with open('/etc/hosts.new', 'w') as f:
        for line in lines:
            f.write('%s\n' % line)

    try:
        os.rename('/etc/hosts', '/etc/hosts.old')
        os.rename('/etc/hosts.new', '/etc/hosts')
        # Keep the first version of the config.txt just-in-case
        os.unlink('/etc/hosts.old')

        # also, run hostname with the new name
        command = f'hostnamectl set-hostname {hostname}'
        subprocess.call(shlex.split(command))

        # run postconf with the new hostname
        command = f"postconf -e 'myhostname = {hostname}'"
        subprocess.call(shlex.split(command))

        # here we should renew the hostname/mailserver SSL with hostname
        # Todo

        # also, restart postfix dovecot
        services_to_restart = ['postfix', 'dovecot', 'opendkim', 'lscpd', 'lsws']

        for service in services_to_restart:
            command = f"systemctl restart {service}"
            subprocess.call(shlex.split(command))

        return True
    except:
        return False
