import os
import subprocess
rootdir = '/home/repo.cyberpanel.net/public_html/epel/Packages'

for subdir, dirs, files in os.walk(rootdir):
    for file in files:
        if file.endswith('.rpm'):
            command = 'rpm --resign %s/%s' % (subdir, file)
            subprocess.call(command, shell=True)