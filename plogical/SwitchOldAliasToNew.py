import os,sys
import shutil

sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass
import subprocess
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging



class SwitchOldAliasToNew:

    def __init__(self):
        pass

    def Rebuild(self):
        try:
            message = 'We will convert old Domain Aliases to new Domain Aliases'
            logging.writeToFile(message)

            origConf = "/usr/local/lsws/conf/httpd_config.conf"
            origConfBack = "/usr/local/lsws/conf/httpd_config.conf"

            if not os.path.exists(origConf):
                shutil.copy(origConf, origConfBack)

            from websiteFunctions.models import aliasDomains
            from plogical.virtualHostUtilities import virtualHostUtilities
            from plogical.processUtilities import ProcessUtilities

            for alias in aliasDomains.objects.all():
                message = f"{alias.aliasDomain} was alias of {alias.master.domain}. Conversions started.."
                logging.writeToFile(message)

                path = f'/home/{alias.master.domain}/public_html'

                result = virtualHostUtilities.createDomain(alias.master.domain, alias.aliasDomain, alias.master.phpSelection, path, 1, 0,
                                                           0, 'admin', 0,'/home/cyberpanel/fakePath', 1, 1)

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.writeToFile(str(result))

                data = open(origConf, 'r').readlines()
                writeToFile = open(origConf, 'w')
                for line in data:
                    if line.find(alias.master.domain) > -1:
                        line = line.replace(f',{alias.aliasDomain},', '')
                        line = line.replace(f', {alias.aliasDomain}', '')
                        writeToFile.write(line)
                    else:
                        writeToFile.write(line)
                writeToFile.close()

                message = f"{alias.aliasDomain} is converted to new Domain Aliase."
                logging.writeToFile(message)

            message = f"Conversion successfully completed."
            logging.writeToFile(message)

        except:
            pass

def main():

    rbQ = SwitchOldAliasToNew()
    rbQ.Rebuild()



if __name__ == "__main__":
    main()