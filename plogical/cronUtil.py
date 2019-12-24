import sys
sys.path.append('/usr/local/CyberCP')
import argparse
from plogical.processUtilities import ProcessUtilities

class CronUtil:

    @staticmethod
    def getWebsiteCron(externalApp):
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
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


            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
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

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                cronPath = "/var/spool/cron/" + externalApp
            else:
                cronPath = "/var/spool/cron/crontabs/" + externalApp

            data = open(cronPath, 'r').readlines()

            counter = 0

            writeToFile = open(cronPath, 'w')
            for items in data:
                if counter == line:
                    removedLine = items
                    continue
                else:
                    writeToFile.writelines(items)

                counter = counter + 1

            print("1," + removedLine)
        except BaseException as msg:
            print("0," + str(msg))

    @staticmethod
    def addNewCron(externalApp, finalCron):
        try:
            CronPath = '/var/spool/cron/%s' % (externalApp)

            with open(CronPath, "a") as file:
                file.write(finalCron + "\n")

            print("1,None")
        except BaseException as msg:
            print("0," + str(msg))

    @staticmethod
    def CronPrem(mode):
        if mode:
            cronParent = '/var/spool/cron'
            commandT = 'chmod 755 %s' % (cronParent)
            ProcessUtilities.executioner(commandT, 'root')
        else:
            cronParent = '/var/spool/cron'
            commandT = 'chmod 700 %s' % (cronParent)
            ProcessUtilities.executioner(commandT, 'root')



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