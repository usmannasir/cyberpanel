import platform
import os
import datetime
import math
import argparse

class SystemInformation:
    now = datetime.datetime.now()
    olsReport = ""

    @staticmethod
    def cpuLoad():
        return os.getloadavg()

    @staticmethod
    def getOSName():

        OSName = platform.platform()
        data =  OSName.split("-")

        checker = 0
        finalOSName = ""

        for items in data:

            if checker == 1:
                finalOSName = items
                break

            if items == "with":
                checker = 1

        return finalOSName

    @staticmethod
    def getCurrentSystemTime():
        return SystemInformation.now.strftime("%I:%M")

    @staticmethod
    def currentWeekDay():
        return SystemInformation.now.strftime("%a")

    @staticmethod
    def currentMonth():
        return SystemInformation.now.strftime("%B")

    @staticmethod
    def currentYear():
        return SystemInformation.now.strftime("%Y")

    @staticmethod
    def currentDay():
        return SystemInformation.now.strftime("%d")

    @staticmethod
    def getAllInfo():
        OSName = SystemInformation.getOSName()
        loadAverage = SystemInformation.cpuLoad()
        currentTime = SystemInformation.getCurrentSystemTime()
        weekDayNameInString = SystemInformation.currentWeekDay()
        currentMonthName = SystemInformation.currentMonth()
        currentDayInDecimal = SystemInformation.currentDay()
        currentYear = SystemInformation.currentYear()
        loadAverage = list(loadAverage)
        one = loadAverage[0]
        two = loadAverage[1]
        three = loadAverage[2]

        data = {"weekDayNameInString": weekDayNameInString, "currentMonthName": currentMonthName,
         "currentDayInDecimal": currentDayInDecimal, "currentYear": currentYear, "OSName": OSName,
         "loadAVG": loadAverage, "currentTime": currentTime, "one":one,"two":two,"three":three}

        return data


    @staticmethod
    def getSystemInformation():
        try:
            import psutil
            SystemInfo = {'ramUsage': int(math.floor(psutil.virtual_memory()[2])), 'cpuUsage': int(math.floor(psutil.cpu_percent())), 'diskUsage': int(math.floor(psutil.disk_usage('/')[3]))}
            return SystemInfo
        except:
            SystemInfo = {'ramUsage': 0,
                          'cpuUsage': 0,
                          'diskUsage': 0}
            return SystemInfo

    @staticmethod
    def cpuRamDisk():
        try:
            import psutil
            SystemInfo = {'ramUsage': int(math.floor(psutil.virtual_memory()[2])),
                          'cpuUsage': int(math.floor(psutil.cpu_percent())),
                          'diskUsage': int(math.floor(psutil.disk_usage('/')[3]))}
        except:
            SystemInfo = {'ramUsage': 0,
                          'cpuUsage': 0,
                          'diskUsage': 0}

        return SystemInfo

    @staticmethod
    def populateOLSReport():
        SystemInformation.olsReport = open("/tmp/lshttpd/.rtreport", "r").readlines()



def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')

    args = parser.parse_args()

    if args.function == "populateOLSReport":
        SystemInformation.populateOLSReport()


if __name__ == "__main__":
    main()