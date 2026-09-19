import sys
sys.path.append('/usr/local/CyberCP')
import os
import gc
import hashlib
import json
import re
import tempfile
import time
from plogical import CyberCPLogFileWriter as logging
import shlex
import subprocess
import validators
import resource

class findBWUsage:
    # Configuration constants
    MAX_MEMORY_MB = 512  # Maximum memory usage in MB
    MAX_PROCESSING_TIME = 300  # Maximum processing time in seconds (5 minutes)
    MAX_LOG_LINES_PER_BATCH = 10000  # Process logs in batches
    MAX_FILE_SIZE_MB = 100  # Skip files larger than 100MB
    
    HOME_DIRECTORY = "/home"
    # Match the configured common/combined format, including empty or escaped requests.
    LOG_RECORD = re.compile(
        r'^\S+\s+\S+\s+\S+\s+\[[^\]]+\]\s+"(?:[^"\\]|\\.)*"'
        r'\s+[0-9]{3}\s+([0-9]+|-)(?:\s|$)'
    )

    @staticmethod
    def parse_last_digits(line):
        """Return response bytes from a common/combined access-log record."""
        if not isinstance(line, str):
            return None
        match = findBWUsage.LOG_RECORD.match(line)
        if match is None:
            return None
        try:
            return 0 if match[1] == '-' else int(match[1])
        except ValueError:
            return None

    @staticmethod
    def get_file_size_mb(filepath):
        return os.path.getsize(filepath) / (1024 * 1024)

    @staticmethod
    def set_memory_limit():
        """Cap the standalone worker without raising an existing process limit."""
        try:
            soft, hard = resource.getrlimit(resource.RLIMIT_AS)
            limit = findBWUsage.MAX_MEMORY_MB * 1024 * 1024
            for existing in (soft, hard):
                if existing != resource.RLIM_INFINITY:
                    limit = min(limit, existing)
            resource.setrlimit(resource.RLIMIT_AS, (limit, hard))
        except (OSError, ValueError, AttributeError) as exc:
            logging.CyberCPLogFileWriter.writeToFile(f"Failed to set memory limit: {exc}")

    @staticmethod
    def _checkpoint(logfile, offset):
        """Recognize copy-truncated logs even if they have already grown again."""
        logfile.seek(max(0, offset - 256))
        digest = hashlib.sha256(logfile.read(min(offset, 256))).hexdigest()
        logfile.seek(offset)
        return digest

    @staticmethod
    def calculateBandwidth(domainName):
        """Stream new complete records, preserving monthly totals across rotation."""
        start_time = time.monotonic()
        temporary = None
        try:
            path = os.path.join(findBWUsage.HOME_DIRECTORY, domainName, "logs",
                                domainName + ".access_log")
            bwmeta = os.path.join(findBWUsage.HOME_DIRECTORY, "cyberpanel", domainName + ".bwmeta")
            if not os.path.exists(path):
                return 0
            if findBWUsage.get_file_size_mb(path) > findBWUsage.MAX_FILE_SIZE_MB:
                logging.CyberCPLogFileWriter.writeToFile(f"Skipping large file {path}")
                return 0

            currentUsed, currentLinesRead, cursor = 0, 0, None
            try:
                with open(bwmeta) as metadata:
                    currentUsed = int(metadata.readline())
                    currentLinesRead = int(metadata.readline())
                    extra = metadata.readline()
                    cursor = json.loads(extra) if extra.strip() else None
                if currentUsed < 0 or currentLinesRead < 0:
                    raise ValueError("Negative bandwidth metadata")
            except FileNotFoundError:
                pass

            with open(path, 'rb') as logfile:
                info = os.fstat(logfile.fileno())
                # Only read the snapshot available at open; growing logs cannot extend a run.
                size = info.st_size
                if size > findBWUsage.MAX_FILE_SIZE_MB * 1024 * 1024:
                    return 0
                if cursor is not None:
                    offset = cursor['offset']
                    if not isinstance(offset, int) or offset < 0:
                        raise ValueError("Invalid bandwidth cursor")
                    same_log = (cursor['device'] == info.st_dev and cursor['inode'] == info.st_ino
                                and offset <= size
                                and cursor['tail'] == findBWUsage._checkpoint(logfile, offset))
                    if same_log:
                        logfile.seek(offset)
                    else:
                        currentLinesRead = 0
                        logfile.seek(0)
                else:
                    # Upgrade legacy two-line metadata without recounting existing traffic.
                    for _ in range(currentLinesRead):
                        if time.monotonic() - start_time >= findBWUsage.MAX_PROCESSING_TIME:
                            return 0  # Keep the old cursor until migration can finish.
                        remaining = size - logfile.tell()
                        line = logfile.readline(remaining) if remaining > 0 else b''
                        if not line or not line.endswith(b'\n'):
                            currentLinesRead = 0
                            logfile.seek(0)
                            break

                lines_processed = 0
                while logfile.tell() < size:
                    if time.monotonic() - start_time >= findBWUsage.MAX_PROCESSING_TIME:
                        logging.CyberCPLogFileWriter.writeToFile(f"Processing timeout for {domainName}")
                        break
                    offset = logfile.tell()
                    line = logfile.readline(size - offset)
                    if not line or not line.endswith(b'\n'):
                        # Retry a partially written record on the next run.
                        logfile.seek(offset)
                        break
                    bandwidth = findBWUsage.parse_last_digits(line.decode('utf-8', errors='replace'))
                    if bandwidth is not None:
                        currentUsed += bandwidth
                    currentLinesRead += 1  # Blank/invalid records still advance the cursor.
                    lines_processed += 1
                    if lines_processed % findBWUsage.MAX_LOG_LINES_PER_BATCH == 0:
                        gc.collect()
                        try:
                            import psutil
                            if psutil.Process().memory_info().rss > findBWUsage.MAX_MEMORY_MB * 1024 * 1024:
                                logging.CyberCPLogFileWriter.writeToFile(f"Memory limit reached for {domainName}")
                                break
                        except ImportError:
                            pass
                offset = logfile.tell()
                cursor = {'device': info.st_dev, 'inode': info.st_ino, 'offset': offset,
                          'tail': findBWUsage._checkpoint(logfile, offset)}

            # Existing readers consume the first two lines. The optional third line
            # adds rotation detection and avoids rescanning on subsequent runs.
            with tempfile.NamedTemporaryFile(mode='w', dir=os.path.dirname(bwmeta),
                                             prefix='.' + domainName + '.bwmeta.', delete=False) as metadata:
                temporary = metadata.name
                metadata.write(f"{currentUsed}\n{currentLinesRead}\n{json.dumps(cursor)}\n")
                metadata.flush()
                os.fsync(metadata.fileno())
            os.replace(temporary, bwmeta)
            temporary = None
            return 1
        except Exception as exc:
            logging.CyberCPLogFileWriter.writeToFile(f"{exc} [calculateBandwidth]")
            return 0
        finally:
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError as exc:
                    logging.CyberCPLogFileWriter.writeToFile(f"{exc} [bandwidth metadata cleanup]")

    @staticmethod
    def startCalculations():
        """Start the standalone bandwidth worker with resource protection."""
        try:
            findBWUsage.set_memory_limit()
            for directory in os.listdir(findBWUsage.HOME_DIRECTORY):
                if validators.domain(directory):
                    try:
                        findBWUsage.calculateBandwidth(directory)
                    except Exception as exc:
                        logging.CyberCPLogFileWriter.writeToFile(f"{exc} [bandwidth: {directory}]")
        except Exception as exc:
            logging.CyberCPLogFileWriter.writeToFile(f"{exc} [startCalculations]")
            return 0
        return 1

    @staticmethod
    def findDomainBW(domainName, totalAllowed):
        """Find domain bandwidth usage with improved error handling"""
        try:
            path = "/home/" + domainName + "/logs/" + domainName + ".access_log"

            if not os.path.exists("/home/" + domainName + "/logs"):
                return [0, 0]

            bwmeta = "/home/cyberpanel/%s.bwmeta" % (domainName)

            if not os.path.exists(path):
                return [0, 0]

            if os.path.exists(bwmeta):
                try:
                    with open(bwmeta, 'r') as f:
                        data = f.readlines()
                    
                    if len(data) < 1:
                        return [0, 0]
                        
                    currentUsed = int(data[0].strip("\n"))
                    inMB = int(float(currentUsed) / (1024.0 * 1024.0))

                    if totalAllowed <= 0:
                        totalAllowed = 999999

                    percentage = float(100) / float(totalAllowed)
                    percentage = float(percentage) * float(inMB)

                    if percentage > 100.0:
                        percentage = 100

                    return [inMB, percentage]
                except (ValueError, IndexError, IOError):
                    return [0, 0]
            else:
                return [0, 0]


        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [findDomainBW]")
            return [0, 0]
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [findDomainBW]")
            return [0, 0]

    @staticmethod
    def changeSystemLanguage():
        """Change system language with improved error handling"""
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


if __name__ == "__main__":
    findBWUsage.startCalculations()