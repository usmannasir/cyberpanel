from CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import subprocess



class ProcessUtilities:
    litespeedProcess = "litespeed"

    @staticmethod
    def getLitespeedProcessNumber():
        finalListOfProcesses = []

        try:
            import psutil
            for proc in psutil.process_iter():
                if proc.name() == ProcessUtilities.litespeedProcess:
                    finalListOfProcesses.append(proc.pid)

        except BaseException,msg:
            logging.writeToFile(
                str(msg) + " [getLitespeedProcessNumber]")
            return 0

        if len(finalListOfProcesses) > 0:
         return finalListOfProcesses
        else:
            return 0

    @staticmethod
    def restartLitespeed():
        try:
            cmd = []
            cmd.append("/usr/local/lsws/bin/lswsctrl")
            cmd.append("restart")
            subprocess.call(cmd)
            return 1

        except subprocess.CalledProcessError,msg:

            logging.writeToFile(str(msg) + "[restartLitespeed]")

    @staticmethod
    def stopLitespeed():
        try:
            cmd = []
            cmd.append("/usr/local/lsws/bin/lswsctrl")
            cmd.append("stop")
            subprocess.call(cmd)
            return 1
        except subprocess.CalledProcessError, msg:
            logging.writeToFile(str(msg) + "[stopLitespeed]")


