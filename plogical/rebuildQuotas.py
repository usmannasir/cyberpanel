import os,sys

sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass
import subprocess



class rebuildQuotas:

    def __init__(self):
        pass

    def Rebuild(self):
        try:
            print("Fixing and rebuilding Quotas...")

            fstab_path = '/etc/fstab'

            rData = open(fstab_path, 'r').read()

            if rData.find('xfs') > -1:
                command  = "mount | grep ' / '"

                qResult = subprocess.run(command, capture_output=True, text=True, shell=True)

                if qResult.stdout.find('usrquota') > -1:
                    print("Looks like Quotas are enabled in filesystem, moving on..")
                else:
                    print("Looks like Quotas are not enabled in filesystem, exiting.")
                    print("Please follow this guide to enable Quotas on XFS file system: ")
                    exit(1)
            else:
                command  = "mount | grep quota"
                qResult = subprocess.run(command, capture_output=True, text=True, shell=True)
                if qResult.stdout.find('usrquota') > -1:
                    print("Looks like Quotas are enabled in filesystem, moving on..")
                else:
                    print("Looks like Quotas are not enabled in filesystem, exiting.")
                    exit(1)


            from websiteFunctions.models import Websites
            for website in Websites.objects.all():
                print(f"Rebuilding quotas for {website.domain}...")
                command = 'chattr -R -i /home/%s/' % (website.domain)
                subprocess.run(command, capture_output=True, text=True, shell=True)

                if website.package.enforceDiskLimits:
                    spaceString = f'{website.package.diskSpace}M {website.package.diskSpace}M'
                    command = f'setquota -u {website.externalApp} {spaceString} 0 0 /'
                    print(command)
                    qResult = subprocess.run(command, capture_output=True, text=True, shell=True)
                else:
                    print(f"Ignored {website.domain} because the selected package does not enforce disk limits.")
        except:
            pass

def main():

    rbQ = rebuildQuotas()
    rbQ.Rebuild()



if __name__ == "__main__":
    main()