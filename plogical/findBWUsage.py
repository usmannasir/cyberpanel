import sys
sys.path.append('/usr/local/CyberCP')
import os
import gc
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
    
    @staticmethod
    def parse_last_digits(line):
        """Safely parse log line and extract bandwidth data"""
        try:
            parts = line.split(' ')
            if len(parts) < 10:
                return None
            # Extract the size field (index 9) and clean it
            size_str = parts[9].replace('"', '').strip()
            if size_str == '-':
                return 0
            return int(size_str)
        except (ValueError, IndexError, AttributeError):
            return None

    @staticmethod
    def get_file_size_mb(filepath):
        """Get file size in MB"""
        try:
            return os.path.getsize(filepath) / (1024 * 1024)
        except OSError:
            return 0

    @staticmethod
    def set_memory_limit():
        """Set memory limit to prevent system overload"""
        try:
            # Set memory limit to MAX_MEMORY_MB
            memory_limit = findBWUsage.MAX_MEMORY_MB * 1024 * 1024  # Convert to bytes
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Failed to set memory limit: {str(e)}")

    @staticmethod
    def calculateBandwidth(domainName):
        """Calculate bandwidth usage for a domain with memory protection"""
        start_time = time.time()
        
        try:
            path = "/home/" + domainName + "/logs/" + domainName + ".access_log"
            
            if not os.path.exists(path):
                return 0
                
            # Check file size before processing
            file_size_mb = findBWUsage.get_file_size_mb(path)
            if file_size_mb > findBWUsage.MAX_FILE_SIZE_MB:
                logging.CyberCPLogFileWriter.writeToFile(f"Skipping large file {path} ({file_size_mb:.2f}MB)")
                return 0

            if not os.path.exists("/home/" + domainName + "/logs"):
                return 0

            bwmeta = "/home/cyberpanel/%s.bwmeta" % (domainName)
            
            # Initialize metadata
            currentUsed = 0
            currentLinesRead = 0
            
            # Read existing metadata
            if os.path.exists(bwmeta):
                try:
                    with open(bwmeta, 'r') as f:
                        data = f.readlines()
                    if len(data) >= 2:
                        currentUsed = int(data[0].strip("\n"))
                        currentLinesRead = int(data[1].strip("\n"))
                except (ValueError, IndexError):
                    currentUsed = 0
                    currentLinesRead = 0

            # Process log file in streaming mode to avoid memory issues
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as logfile:
                    # Skip to the last processed line
                    for _ in range(currentLinesRead):
                        try:
                            next(logfile)
                        except StopIteration:
                            break
                    
                    lines_processed = 0
                    batch_size = 0
                    
                    for line in logfile:
                        # Check processing time limit
                        if time.time() - start_time > findBWUsage.MAX_PROCESSING_TIME:
                            logging.CyberCPLogFileWriter.writeToFile(f"Processing timeout for {domainName}")
                            break
                        
                        line = line.strip()
                        if len(line) > 10:
                            bandwidth = findBWUsage.parse_last_digits(line)
                            if bandwidth is not None:
                                currentUsed += bandwidth
                            
                            currentLinesRead += 1
                            lines_processed += 1
                            batch_size += 1
                            
                            # Process in batches to manage memory
                            if batch_size >= findBWUsage.MAX_LOG_LINES_PER_BATCH:
                                # Force garbage collection
                                gc.collect()
                                batch_size = 0
                                
                                # Check memory usage
                                try:
                                    import psutil
                                    process = psutil.Process()
                                    memory_mb = process.memory_info().rss / (1024 * 1024)
                                    if memory_mb > findBWUsage.MAX_MEMORY_MB:
                                        logging.CyberCPLogFileWriter.writeToFile(f"Memory limit reached for {domainName}")
                                        break
                                except ImportError:
                                    pass  # psutil not available, continue processing
                                
            except (IOError, OSError) as e:
                logging.CyberCPLogFileWriter.writeToFile(f"Error reading log file {path}: {str(e)}")
                return 0

            # Write updated metadata
            try:
                with open(bwmeta, 'w') as f:
                    f.write(f"{currentUsed}\n{currentLinesRead}\n")
                os.chmod(bwmeta, 0o600)
            except (IOError, OSError) as e:
                logging.CyberCPLogFileWriter.writeToFile(f"Error writing metadata {bwmeta}: {str(e)}")
                return 0

            # Log processing statistics
            processing_time = time.time() - start_time
            if processing_time > 10:  # Log if processing took more than 10 seconds
                logging.CyberCPLogFileWriter.writeToFile(f"Processed {domainName}: {lines_processed} lines in {processing_time:.2f}s")

        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [calculateBandwidth]")
            return 0

        return 1

    @staticmethod
    def startCalculations():
        """Start bandwidth calculations with resource protection"""
        try:
            # Set memory limit
            findBWUsage.set_memory_limit()
            
            start_time = time.time()
            domains_processed = 0
            
            for directories in os.listdir("/home"):
                # Check overall processing time
                if time.time() - start_time > findBWUsage.MAX_PROCESSING_TIME * 2:
                    logging.CyberCPLogFileWriter.writeToFile("Overall processing timeout reached")
                    break
                
                if validators.domain(directories):
                    try:
                        result = findBWUsage.calculateBandwidth(directories)
                        domains_processed += 1
                        
                        # Force garbage collection after each domain
                        gc.collect()
                        
                        # Small delay to prevent system overload
                        time.sleep(0.1)
                        
                    except Exception as e:
                        logging.CyberCPLogFileWriter.writeToFile(f"Error processing domain {directories}: {str(e)}")
                        continue
            
            total_time = time.time() - start_time
            logging.CyberCPLogFileWriter.writeToFile(f"Bandwidth calculation completed: {domains_processed} domains in {total_time:.2f}s")
            
        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [startCalculations]")
            return 0

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