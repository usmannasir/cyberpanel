import os
import sys
sys.path.append('/usr/local/CyberCP')
import argparse
from plogical.processUtilities import ProcessUtilities
from random import randint, seed
import time
try:
    seed(time.perf_counter())
except:
    pass

class CronUtil:

    @staticmethod
    def getWebsiteCron(externalApp):
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                cronPath = "/var/spool/cron/" + externalApp
            else:
                cronPath = "/var/spool/cron/crontabs/" + externalApp

            try:
                f = open(cronPath, 'r').read()
                print(f)
            except BaseException as msg:
                print("0,CyberPanel," + str(msg))
                return 1

        except BaseException as msg:
            print("0,CyberPanel," + str(msg))

    @staticmethod
    def saveCronChanges(externalApp, finalCron, line):
        try:


            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                cronPath = "/var/spool/cron/" + externalApp
            else:
                cronPath = "/var/spool/cron/crontabs/" + externalApp

            with open(cronPath, 'r') as file:
                data = file.readlines()

            data[line] = finalCron + '\n'

            with open(cronPath, 'w') as file:
                file.writelines(data)

            print("1,None")
        except BaseException as msg:
            print("0," + str(msg))

    @staticmethod
    def remCronbyLine(externalApp, line):
        try:
            line -= 1

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                cronPath = "/var/spool/cron/" + externalApp
            else:
                cronPath = "/var/spool/cron/crontabs/" + externalApp

            data = open(cronPath, 'r').readlines()

            counter = 0

            writeToFile = open(cronPath, 'w')

            for items in data:
                if counter == line:
                    removedLine = items
                    counter = counter + 1
                    continue
                else:
                    writeToFile.writelines(items)

                counter = counter + 1

            writeToFile.close()

            print("1," + removedLine)
        except BaseException as msg:
            print("0," + str(msg))

    @staticmethod
    def addNewCron(externalApp, finalCron):
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                cronPath = "/var/spool/cron/" + externalApp
            else:
                cronPath = "/var/spool/cron/crontabs/" + externalApp

            print(cronPath)

            TempFile = '/tmp/' + str(randint(1000, 9999))

            print(TempFile)

            if os.path.exists(cronPath):
                FullCrons = open(cronPath, 'r').read()
                finalCron = '%s%s\n' % (FullCrons, finalCron)
                with open(TempFile, "w") as file:
                    file.write(finalCron)
                print(finalCron)
            else:
                with open(TempFile, "w") as file:
                    file.write(finalCron + '\n')

            command = 'cp %s %s' % (TempFile, cronPath)
            ProcessUtilities.normalExecutioner(command)

            os.remove(TempFile)

            print("1,None")
        except BaseException as msg:
            print("0," + str(msg))

    @staticmethod
    def CronPrem(mode):
        if mode:
            cronParent = '/var/spool/cron'
            commandT = 'chmod 755 %s' % (cronParent)
            ProcessUtilities.executioner(commandT, 'root')

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                command = 'chmod 755 /var/spool/cron/crontabs'
                ProcessUtilities.outputExecutioner(command)

        else:
            cronParent = '/var/spool/cron'
            commandT = 'chmod 700 %s' % (cronParent)
            ProcessUtilities.executioner(commandT, 'root')

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                command = 'chmod 1730 /var/spool/cron/crontabs'
                ProcessUtilities.outputExecutioner(command)

    @staticmethod
    def suspendWebsiteCrons(externalApp):
        """
        Suspend all cron jobs for a website by backing up and clearing the cron file.
        This prevents cron jobs from running when a website is suspended.
        """
        try:
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                cronPath = "/var/spool/cron/" + externalApp
                backupPath = "/var/spool/cron/" + externalApp + ".suspended"
            else:
                cronPath = "/var/spool/cron/crontabs/" + externalApp
                backupPath = "/var/spool/cron/crontabs/" + externalApp + ".suspended"

            # Check if cron file exists
            if not os.path.exists(cronPath):
                print("1,None")  # No cron file to suspend
                return

            # Create backup of current cron jobs
            try:
                command = f'cp {cronPath} {backupPath}'
                ProcessUtilities.executioner(command, 'root')
            except Exception as e:
                print(f"0,Warning: Could not backup cron file: {str(e)}")

            # Clear the cron file to suspend all jobs
            try:
                CronUtil.CronPrem(1)  # Enable permissions
                
                # Create empty cron file or clear existing one
                with open(cronPath, 'w') as f:
                    f.write('')  # Empty file to disable all cron jobs
                
                # Set proper ownership
                command = f'chown {externalApp}:{externalApp} {cronPath}'
                ProcessUtilities.executioner(command, 'root')
                
                CronUtil.CronPrem(0)  # Restore permissions
                
                print("1,Cron jobs suspended successfully")
                
            except Exception as e:
                CronUtil.CronPrem(0)  # Ensure permissions are restored
                print(f"0,Failed to suspend cron jobs: {str(e)}")

        except Exception as e:
            print(f"0,Error suspending cron jobs: {str(e)}")

    @staticmethod
    def restoreWebsiteCrons(externalApp):
        """
        Restore cron jobs for a website by restoring from backup file.
        This restores cron jobs when a website is unsuspended.
        """
        try:
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                cronPath = "/var/spool/cron/" + externalApp
                backupPath = "/var/spool/cron/" + externalApp + ".suspended"
            else:
                cronPath = "/var/spool/cron/crontabs/" + externalApp
                backupPath = "/var/spool/cron/crontabs/" + externalApp + ".suspended"

            # Check if backup file exists
            if not os.path.exists(backupPath):
                print("1,No suspended cron jobs to restore")
                return

            try:
                CronUtil.CronPrem(1)  # Enable permissions
                
                # Restore cron jobs from backup
                command = f'cp {backupPath} {cronPath}'
                ProcessUtilities.executioner(command, 'root')
                
                # Set proper ownership
                command = f'chown {externalApp}:{externalApp} {cronPath}'
                ProcessUtilities.executioner(command, 'root')
                
                # Remove backup file
                os.remove(backupPath)
                
                CronUtil.CronPrem(0)  # Restore permissions
                
                print("1,Cron jobs restored successfully")
                
            except Exception as e:
                CronUtil.CronPrem(0)  # Ensure permissions are restored
                print(f"0,Failed to restore cron jobs: {str(e)}")

        except Exception as e:
            print(f"0,Error restoring cron jobs: {str(e)}")

    @staticmethod
    def getCronSuspensionStatus(externalApp):
        """
        Check if cron jobs are currently suspended for a website.
        Returns 1 if suspended, 0 if active, -1 if error.
        """
        try:
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                cronPath = "/var/spool/cron/" + externalApp
                backupPath = "/var/spool/cron/" + externalApp + ".suspended"
            else:
                cronPath = "/var/spool/cron/crontabs/" + externalApp
                backupPath = "/var/spool/cron/crontabs/" + externalApp + ".suspended"

            # Check if backup file exists (indicates suspension)
            if os.path.exists(backupPath):
                print("1,Cron jobs are suspended")
                return
            elif os.path.exists(cronPath):
                # Check if cron file is empty (also indicates suspension)
                try:
                    with open(cronPath, 'r') as f:
                        content = f.read().strip()
                    if not content:
                        print("1,Cron jobs are suspended (empty file)")
                    else:
                        print("0,Cron jobs are active")
                except Exception as e:
                    print(f"-1,Error reading cron file: {str(e)}")
            else:
                print("0,No cron jobs configured")
                
        except Exception as e:
            print(f"-1,Error checking cron status: {str(e)}")

    @staticmethod
    def restartCronService():
        """
        Restart the cron service to apply changes immediately.
        Works across all distributions (Ubuntu/Debian/CentOS/AlmaLinux).
        
        Returns:
            tuple: (success_bool, error_message)
        """
        try:
            # Determine which cron service command to use based on distribution
            distro = ProcessUtilities.decideDistro()
            
            if distro == ProcessUtilities.centos or distro == ProcessUtilities.cent8:
                # CentOS/AlmaLinux uses 'crond'
                command = 'systemctl restart crond'
            else:
                # Ubuntu/Debian uses 'cron'
                command = 'systemctl restart cron'
            
            # Execute the restart command with root privileges
            ProcessUtilities.executioner(command, 'root')
            
            # Return success
            return (True, None)
            
        except BaseException as msg:
            error_msg = f"Failed to restart cron service: {str(msg)}"
            print(f"0,{error_msg}")
            return (False, error_msg)



def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')

    parser.add_argument("--externalApp", help="externalApp")
    parser.add_argument("--line", help="")
    parser.add_argument("--finalCron", help="")
    parser.add_argument("--tempPath", help="Temporary path to file where PHP is storing data!")


    args = parser.parse_args()

    if args.function == "getWebsiteCron":
        CronUtil.getWebsiteCron(args.externalApp)
    elif args.function == "saveCronChanges":
        CronUtil.saveCronChanges(args.externalApp, args.finalCron, int(args.line))
    elif args.function == "remCronbyLine":
        CronUtil.remCronbyLine(args.externalApp, int(args.line))
    elif args.function == "addNewCron":
        CronUtil.addNewCron(args.externalApp, args.finalCron)
    elif args.function == "suspendWebsiteCrons":
        CronUtil.suspendWebsiteCrons(args.externalApp)
    elif args.function == "restoreWebsiteCrons":
        CronUtil.restoreWebsiteCrons(args.externalApp)
    elif args.function == "getCronSuspensionStatus":
        CronUtil.getCronSuspensionStatus(args.externalApp)




if __name__ == "__main__":
    main()