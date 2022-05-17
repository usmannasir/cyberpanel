import sys
sys.path.append('/usr/local/CyberCP')
import os
from plogical import CyberCPLogFileWriter as logging
import shlex
import subprocess
import validators

class findBWUsage:
    @staticmethod
    def parse_last_digits(line):
        return line.split(' ')

    @staticmethod
    def calculateBandwidth(domainName):
        try:
            path = "/home/"+domainName+"/logs/"+domainName+".access_log"

            if not os.path.exists(path):
                return 0
            from processUtilities import ProcessUtilities
            logData = ProcessUtilities.outputExecutioner('cat %s' % (path), 'nobody').splitlines()
            logDataLines = len(logData)

            if not os.path.exists("/home/"+domainName+"/logs"):
                return 0

            bwmeta = "/home/cyberpanel/%s.bwmeta" % (domainName)

            if not os.path.exists(path):
                writeMeta = open(bwmeta, 'w')
                writeMeta.writelines('0\n0\n')
                writeMeta.close()
                os.chmod(bwmeta, 0o600)
                return 1

            if os.path.exists(bwmeta):
                data = open(bwmeta).readlines()
                currentUsed = int(data[0].strip("\n"))
                currentLinesRead = int(data[1].strip("\n"))
                if currentLinesRead > logDataLines:
                    currentLinesRead = 0
            else:
                currentUsed = 0
                currentLinesRead = 0

            startLine = currentLinesRead

            for line in logData[startLine:]:
                line = line.strip('"\n')
                currentLinesRead = currentLinesRead + 1
                if len(line)>10:
                    currentUsed = int(findBWUsage.parse_last_digits(line)[9].replace('"', '')) + currentUsed

            writeMeta = open(bwmeta,'w')
            writeMeta.writelines(str(currentUsed)+"\n")
            writeMeta.writelines(str(currentLinesRead) + "\n")
            writeMeta.close()

            os.chmod(bwmeta, 0o600)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [calculateBandwidth]")
            return 0

        return 1

    @staticmethod
    def startCalculations():
        try:
            for directories in os.listdir("/home"):
                if validators.domain(directories):
                    findBWUsage.calculateBandwidth(directories)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startCalculations]")
            return 0

    @staticmethod
    def findDomainBW(domainName,totalAllowed):
        try:
            path = "/home/"+domainName+"/logs/"+domainName+".access_log"

            if not os.path.exists("/home/"+domainName+"/logs"):
                return [0,0]

            bwmeta = "/home/" + domainName + "/logs/bwmeta"

            if not os.path.exists(path):
                return [0,0]



            if os.path.exists(bwmeta):
                try:
                    data = open(bwmeta).readlines()
                    currentUsed = int(data[0].strip("\n"))

                    inMB = int(float(currentUsed)/(1024.0*1024.0))

                    percentage = float(100) / float(totalAllowed)

                    percentage = float(percentage) * float(inMB)
                except:
                    return [0,0]

                if percentage > 100.0:
                    percentage = 100

                return [inMB,percentage]
            else:
                return [0, 0]


        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [findDomainBW]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [findDomainBW]")
            return 0

        return 1

    @staticmethod
    def changeSystemLanguage():
        try:

            command = 'localectl set-locale LANG=en_US.UTF-8'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 1:
                logging.CyberCPLogFileWriter.writeToFile("1440 [setup_cron]")
            else:
                pass


            print("###############################################")
            print("        Language Changed to English                ")
            print("###############################################")


        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [changeSystemLanguage]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [changeSystemLanguage]")
            return 0

        return 1


findBWUsage.startCalculations()