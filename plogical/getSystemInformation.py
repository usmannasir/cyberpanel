import platform
import os
import datetime
import math
import argparse

_METRICS_EMA_CACHE_KEY = 'cp_metrics_ema'
_METRICS_EMA_CACHE_TTL = 3600


def _clamp_step(prev_val, new_val, max_step):
    if prev_val is None:
        return new_val
    delta = new_val - prev_val
    if delta > max_step:
        return prev_val + max_step
    if delta < -max_step:
        return prev_val - max_step
    return new_val


def _smooth_metric(raw_val, prev_val, alpha, max_step):
    if prev_val is None:
        smoothed = raw_val
    else:
        smoothed = (alpha * raw_val) + ((1.0 - alpha) * prev_val)
    smoothed = _clamp_step(prev_val, smoothed, max_step)
    return max(0.0, min(100.0, smoothed))


def _sample_cpu_percent(psutil_mod, samples=3, interval=0.2):
    readings = []
    for _ in range(samples):
        readings.append(psutil_mod.cpu_percent(interval=interval))
    return sum(readings) / float(len(readings))


def _load_metrics_ema():
    try:
        from django.core.cache import cache
        return cache.get(_METRICS_EMA_CACHE_KEY) or {}
    except Exception:
        return {}


def _save_metrics_ema(ema_state):
    try:
        from django.core.cache import cache
        cache.set(_METRICS_EMA_CACHE_KEY, ema_state, _METRICS_EMA_CACHE_TTL)
    except Exception:
        pass


def _smooth_usage_metrics(cpu_raw, ram_raw, disk_raw):
    ema_state = _load_metrics_ema()
    prev_cpu = ema_state.get('cpu')
    prev_ram = ema_state.get('ram')
    prev_disk = ema_state.get('disk')

    cpu_smoothed = _smooth_metric(cpu_raw, prev_cpu, alpha=0.35, max_step=15.0)
    ram_smoothed = _smooth_metric(ram_raw, prev_ram, alpha=0.5, max_step=8.0)
    disk_smoothed = _smooth_metric(disk_raw, prev_disk, alpha=0.5, max_step=8.0)

    _save_metrics_ema({
        'cpu': cpu_smoothed,
        'ram': ram_smoothed,
        'disk': disk_smoothed,
    })

    return (
        int(math.floor(cpu_smoothed)),
        int(math.floor(ram_smoothed)),
        int(math.floor(disk_smoothed)),
    )


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
            
            # Get usage percentages (multi-sample CPU + EMA to avoid burst spikes)
            vm = psutil.virtual_memory()
            ram_raw = float(vm.percent)
            cpu_raw = _sample_cpu_percent(psutil)
            disk = psutil.disk_usage('/')
            disk_raw = float(disk.percent)
            cpu_percent, ram_percent, disk_percent = _smooth_usage_metrics(
                cpu_raw, ram_raw, disk_raw
            )

            # Get total system information
            cpu_cores = psutil.cpu_count() or 1
            ram_total_mb = int(vm.total / (1024 * 1024))
            disk_total_gb = int(disk.total / (1024 * 1024 * 1024))
            disk_free_gb = int(disk.free / (1024 * 1024 * 1024))
            
            # Get uptime
            uptime_seconds = int(psutil.boot_time())
            current_time = int(datetime.datetime.now().timestamp())
            uptime_diff = current_time - uptime_seconds
            
            days = uptime_diff // 86400
            hours = (uptime_diff % 86400) // 3600
            minutes = (uptime_diff % 3600) // 60
            
            if days > 0:
                uptime_str = f"{days}D, {hours}H, {minutes}M"
            else:
                uptime_str = f"{hours}H, {minutes}M"
            
            SystemInfo = {
                'ramUsage': ram_percent, 
                'cpuUsage': cpu_percent, 
                'diskUsage': disk_percent,
                'cpuCores': cpu_cores,
                'ramTotalMB': ram_total_mb,
                'diskTotalGB': disk_total_gb,
                'diskFreeGB': disk_free_gb,
                'uptime': uptime_str
            }
            return SystemInfo
        except:
            SystemInfo = {'ramUsage': 0,
                          'cpuUsage': 0,
                          'diskUsage': 0,
                          'cpuCores': 0,
                          'ramTotalMB': 0,
                          'diskTotalGB': 0,
                          'diskFreeGB': 0,
                          'uptime': 'N/A'}
            return SystemInfo

    @staticmethod
    def cpuRamDisk():
        try:
            import psutil
            vm = psutil.virtual_memory()
            ram_raw = float(vm.percent)
            cpu_raw = _sample_cpu_percent(psutil)
            disk_raw = float(psutil.disk_usage('/').percent)
            cpu_u, ram_u, disk_u = _smooth_usage_metrics(cpu_raw, ram_raw, disk_raw)
            SystemInfo = {'ramUsage': ram_u,
                          'cpuUsage': cpu_u,
                          'diskUsage': disk_u}
        except:
            SystemInfo = {'ramUsage': 0,
                          'cpuUsage': 0,
                          'diskUsage': 0}

        return SystemInfo

    @staticmethod
    def GetRemainingDiskUsageInMBs():
        import psutil

        total_disk = psutil.disk_usage('/').total / (1024 * 1024)  # Total disk space in MB
        used_disk = psutil.disk_usage('/').used / (1024 * 1024)  # Used disk space in MB
        free_disk = psutil.disk_usage('/').free / (1024 * 1024)  # Free disk space in MB
        percent_used = psutil.disk_usage('/').percent  # Percentage of disk used

        return used_disk, free_disk, percent_used

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