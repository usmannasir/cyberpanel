import CyberCPLogFileWriter as logging
import subprocess
import shlex
import thread
import installUtilities
import argparse
import os
from mailUtilities import mailUtilities
from processUtilities import ProcessUtilities
from random import randint

class CronUtil:

    @staticmethod
    def getWebsiteCron(externalApp):
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                cronPath = "/var/spool/cron/" + externalApp
            else:
                cronPath = "/var/spool/cron/crontabs/" + externalApp

            cmd = 'sudo test -e ' + cronPath + ' && echo Exists'
            output = os.popen(cmd).read()

            if "Exists" not in output:
                print  "0,Not Exists"
                return 1

            try:
                f = subprocess.check_output(["sudo", "crontab", "-u", externalApp, "-l"])
                print f
            except BaseException, msg:
                print "0," + str(msg)
                return 1

        except BaseException, msg:
            print "0," + str(msg)

    @staticmethod
    def saveCronChanges(externalApp, finalCron, line):
        try:

            tempPath = "/home/cyberpanel/" + externalApp + str(randint(10000, 99999)) + ".cron.tmp"

            output = subprocess.check_output(["sudo", "/usr/bin/crontab", "-u", externalApp, "-l"])

            if "no crontab for" in output:
                print "0,crontab file does not exists for user"
                return 1

            with open(tempPath, "w+") as file:
                file.write(output)

            # Confirming that directory is read/writable
            o = subprocess.call(['sudo', 'chown', 'cyberpanel:cyberpanel', tempPath])
            if o is not 0:
                print "0,Error Changing Permissions"
                return 1

            with open(tempPath, 'r') as file:
                data = file.readlines()

            data[line] = finalCron + '\n'

            with open(tempPath, 'w') as file:
                file.writelines(data)

            output = subprocess.call(["sudo", "/usr/bin/crontab", "-u", externalApp, tempPath])

            os.remove(tempPath)
            if output != 0:
                print "0,Incorrect Syntax cannot be accepted."
                return 1

            print "1,None"
        except BaseException, msg:
            print "0," + str(msg)

    @staticmethod
    def remCronbyLine(externalApp, line):
        try:
            line -= 1

            output = subprocess.check_output(["sudo", "/usr/bin/crontab", "-u", externalApp, "-l"])

            if "no crontab for" in output:
                print "0,No Cron exists for this user"
                return 1

            tempPath = "/home/cyberpanel/" + externalApp + str(randint(10000, 99999)) + ".cron.tmp"

            with open(tempPath, "w+") as file:
                file.write(output)

            # Confirming that directory is read/writable
            o = subprocess.call(['sudo', 'chown', 'cyberpanel:cyberpanel', tempPath])
            if o is not 0:
                print "0,Error Changing Permissions"
                return 1

            with open(tempPath, 'r') as file:
                data = file.readlines()

            removedLine = data.pop(line)

            with open(tempPath, 'w') as file:
                file.writelines(data)

            output = subprocess.call(["sudo", "/usr/bin/crontab", "-u", externalApp, tempPath])

            os.remove(tempPath)
            if output != 0:
                print "0,Incorrect Syntax cannot be accepted"
                return 1

            print "1," + removedLine
        except BaseException, msg:
            print "0," + str(msg)

    @staticmethod
    def addNewCron(externalApp, finalCron):
        try:

            try:
                output = subprocess.check_output(["sudo", "/usr/bin/crontab", "-u", externalApp, "-l"])
            except:
                try:
                    subprocess.call(('sudo', 'crontab', '-u', externalApp, '-'))
                except:
                    print "0,Unable to initialise crontab file for user"
                    return 1

            output = subprocess.check_output(["sudo", "/usr/bin/crontab", "-u", externalApp, "-l"])

            if "no crontab for" in output:
                echo = subprocess.Popen((['cat', '/dev/null']), stdout=subprocess.PIPE)
                subprocess.call(('sudo', 'crontab', '-u', externalApp, '-'), stdin=echo.stdout)
                echo.wait()
                echo.stdout.close()
                output = subprocess.check_output(["sudo", "/usr/bin/crontab", "-u", externalApp, "-l"])
                if "no crontab for" in output:
                    print "0,Unable to initialise crontab file for user"
                    return 1

            tempPath = "/home/cyberpanel/" + externalApp + str(randint(10000, 99999)) + ".cron.tmp"

            with open(tempPath, "a") as file:
                file.write(output + finalCron + "\n")

            output = subprocess.call(["sudo", "/usr/bin/crontab", "-u", externalApp, tempPath])

            os.remove(tempPath)
            if output != 0:
                print "0,Incorrect Syntax cannot be accepted"
                return 1

            print "1,None"
        except BaseException, msg:
            print "0," + str(msg)



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




if __name__ == "__main__":
    main()