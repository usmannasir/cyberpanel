import sys
sys.path.append('/usr/local/CyberCP')
import os
from plogical import CyberCPLogFileWriter as logging
import shlex
import subprocess
class findBWUsage:
    @staticmethod
    def parse_last_digits(line):
        return line.split(' ')

    @staticmethod
    def calculateBandwidth(domainName):
        try:
            path = "/home/"+domainName+"/logs/"+domainName+".access_log"

            if not os.path.exists("/home/"+domainName+"/logs"):
                return 0

            bwmeta = "/home/" + domainName + "/logs/bwmeta"

            if not os.path.exists(path):
                writeMeta = open(bwmeta, 'w')
                writeMeta.writelines(str(0) + "\n")
                writeMeta.writelines(str(0) + "\n")
                writeMeta.close()
                return 1



            if os.path.exists(bwmeta):
                data = open(bwmeta).readlines()
                currentUsed = int(data[0].strip("\n"))
                seekPoint = int(data[1].strip("\n"))
                if seekPoint > os.path.getsize(path):
                    seekPoint = 0
            else:
                currentUsed = 0
                seekPoint = 0

            newSeekPoint = seekPoint

            logFile = open(path,'r')
            logFile.seek(seekPoint)


            for line in logFile:
                line = line.strip('"\n')
                newSeekPoint = newSeekPoint + len(line)
                if len(line)>10:
                    currentUsed = int(findBWUsage.parse_last_digits(line)[9].replace('"', '')) + currentUsed


            writeMeta = open(bwmeta,'w')
            writeMeta.writelines(str(currentUsed)+"\n")
            writeMeta.writelines(str(newSeekPoint) + "\n")
            writeMeta.close()

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [calculateBandwidth]")
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [calculateBandwidth]")
            return 0

        return 1



    @staticmethod
    def startCalculations():
        try:
            for directories in os.listdir("/home"):
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