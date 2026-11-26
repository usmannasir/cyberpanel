import argparse
import os
import sys
import shutil
sys.path.append('/usr/local/CyberCP')
from plogical import CyberCPLogFileWriter as logging
from plogical import backupUtilities as backupUtil
from plogical.remoteTransferUtilities import remoteTransferUtilities
import time
from multiprocessing import Process
import subprocess
import shlex
from shutil import move
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.processUtilities import ProcessUtilities
from plogical.backupSchedule import backupSchedule
import json
import psutil

class enhancedRemoteTransfer:

    TRANSFER_MODES = {
        'SEQUENTIAL': 'sequential',      # One by one with cleanup
        'RSYNC': 'rsync',               # Direct sync with rsync
        'PARALLEL': 'parallel'          # Current method (all at once)
    }

    @staticmethod
    def getDiskUsage(path='/'):
        """Get disk usage statistics"""
        try:
            usage = psutil.disk_usage(path)
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': (usage.used / usage.total) * 100
            }
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error getting disk usage: {str(e)}")
            return None

    @staticmethod
    def calculateWebsitesSize(websites):
        """Calculate total size of selected websites"""
        total_size = 0
        for website in websites:
            website_path = f"/home/{website}"
            if os.path.exists(website_path):
                try:
                    for dirpath, dirnames, filenames in os.walk(website_path):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            if os.path.exists(filepath):
                                total_size += os.path.getsize(filepath)
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Error calculating size for {website}: {str(e)}")
        return total_size

    @staticmethod
    def recommendTransferMode(websites):
        """Recommend transfer mode based on disk space and website sizes"""
        disk_info = enhancedRemoteTransfer.getDiskUsage()
        if not disk_info:
            return enhancedRemoteTransfer.TRANSFER_MODES['SEQUENTIAL']  # Safe fallback

        total_websites_size = enhancedRemoteTransfer.calculateWebsitesSize(websites)
        estimated_compressed_size = total_websites_size * 0.7  # Assuming 30% compression

        free_space_gb = disk_info['free'] / (1024**3)
        required_space_gb = estimated_compressed_size / (1024**3)

        free_percent = (disk_info['free'] / disk_info['total']) * 100

        logging.CyberCPLogFileWriter.writeToFile(f"Disk analysis: {free_percent:.1f}% free ({free_space_gb:.1f}GB), "
                                                f"Websites: {required_space_gb:.1f}GB estimated")

        # Check if rsync is available
        rsync_available = enhancedRemoteTransfer.checkRsyncAvailability()

        # Decision logic
        if rsync_available and free_percent < 30:
            return enhancedRemoteTransfer.TRANSFER_MODES['RSYNC']
        elif free_percent < 50:
            return enhancedRemoteTransfer.TRANSFER_MODES['SEQUENTIAL']
        else:
            return enhancedRemoteTransfer.TRANSFER_MODES['PARALLEL']

    @staticmethod
    def checkRsyncAvailability():
        """Check if rsync is available on the system"""
        try:
            result = subprocess.run(['which', 'rsync'], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    @staticmethod
    def enhancedRemoteTransfer(ipAddress, dir, accountsToTransfer, transferMode=None):
        """Enhanced remote transfer with multiple transfer modes"""
        try:

            # Parse accounts list
            with open(accountsToTransfer, 'r') as f:
                accounts_list = [line.strip() for line in f.readlines() if line.strip()]

            # Determine transfer mode if not specified
            if not transferMode:
                transferMode = enhancedRemoteTransfer.recommendTransferMode(accounts_list)

            destination = "/home/backup/transfer-" + dir
            backupLogPath = destination + "/backup_log"

            if not os.path.exists(destination):
                os.makedirs(destination)

            command = 'chmod 600 %s' % (destination)
            ProcessUtilities.executioner(command)

            writeToFile = open(backupLogPath, "w+")
            writeToFile.writelines("############################\n")
            writeToFile.writelines("   Enhanced Remote Backup\n")
            writeToFile.writelines(f"   Transfer Mode: {transferMode}\n")
            writeToFile.writelines("   Start date: " + time.strftime("%m.%d.%Y_%H-%M-%S") + "\n")
            writeToFile.writelines("############################\n\n")

            # Add disk usage information to log
            disk_info = enhancedRemoteTransfer.getDiskUsage()
            if disk_info:
                writeToFile.writelines(f"Disk Usage: {disk_info['percent']:.1f}% used, "
                                     f"{disk_info['free']/(1024**3):.1f}GB free\n\n")

            writeToFile.close()

            # Verify connectivity
            if backupUtil.backupUtilities.checkIfHostIsUp(ipAddress) == 1:
                checkConn = backupUtil.backupUtilities.checkConnection(ipAddress)
                if checkConn[0] == 0:
                    writeToFile = open(backupLogPath, "a")
                    writeToFile.writelines("[" + time.strftime(
                        "%m.%d.%Y_%H-%M-%S") + "] Connection to:" + ipAddress +
                                        " Failed, please resetup this destination from CyberPanel, aborting. [5010]\n")
                    writeToFile.close()
                    return
            else:
                writeToFile = open(backupLogPath, "a")
                writeToFile.writelines("[" + time.strftime(
                    "%m.%d.%Y_%H-%M-%S") + "] Host:" + ipAddress + " could be down, we are continuing...\n")
                writeToFile.close()

            # Start transfer process based on mode
            if transferMode == enhancedRemoteTransfer.TRANSFER_MODES['RSYNC']:
                p = Process(target=enhancedRemoteTransfer.rsyncTransferProcess,
                           args=(ipAddress, destination, backupLogPath, dir, accounts_list))
            elif transferMode == enhancedRemoteTransfer.TRANSFER_MODES['SEQUENTIAL']:
                p = Process(target=enhancedRemoteTransfer.sequentialTransferProcess,
                           args=(ipAddress, destination, backupLogPath, dir, accounts_list))
            else:  # PARALLEL (current method)
                p = Process(target=remoteTransferUtilities.backupProcess,
                           args=(ipAddress, destination, backupLogPath, dir, accounts_list))

            p.start()

            pid = open(destination + '/pid', "w")
            pid.write(str(p.pid))
            pid.close()

            return

        except BaseException as msg:
            writeToFile = open(backupLogPath, "w+")
            writeToFile.writelines(str(msg) + " [5010]" + "\n")
            writeToFile.close()
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [enhancedRemoteTransfer]")
            return [0, str(msg)]

    @staticmethod
    def sequentialTransferProcess(ipAddress, dir, backupLogPath, folderNumber, accountsToTransfer):
        """Process websites one by one with cleanup after each transfer"""
        try:
            writeToFile = open(backupLogPath, "a")
            writeToFile.writelines("[" + time.strftime("%m.%d.%Y_%H-%M-%S") + "] Starting sequential transfer mode\n")
            writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Processing {len(accountsToTransfer)} websites one by one\n")
            writeToFile.close()

            for i, virtualHost in enumerate(accountsToTransfer, 1):
                try:
                    writeToFile = open(backupLogPath, "a")
                    writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Processing website {i}/{len(accountsToTransfer)}: {virtualHost}\n")
                    writeToFile.close()

                    # Create backup for this single website
                    retValue = backupSchedule.createLocalBackup(virtualHost, backupLogPath)

                    if retValue[0] == 1:
                        writeToFile = open(backupLogPath, 'a')
                        writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Local backup completed for: {virtualHost}\n")

                        completePathToBackupFile = retValue[1] + '.tar.gz'

                        # Change permissions
                        command = 'chmod 600 %s' % (completePathToBackupFile)
                        ProcessUtilities.executioner(command)

                        if os.path.exists(completePathToBackupFile):
                            # Move to transfer directory
                            move(completePathToBackupFile, dir)
                            completedPathToSend = dir + "/" + completePathToBackupFile.split("/")[-1]

                            writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Sending {completedPathToSend} to {ipAddress}\n")

                            # Send backup
                            remoteTransferUtilities.sendBackup(completedPathToSend, ipAddress, str(folderNumber), writeToFile)

                            writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Successfully sent and cleaned up: {virtualHost}\n")

                            # Log disk usage after each cleanup
                            disk_info = enhancedRemoteTransfer.getDiskUsage()
                            if disk_info:
                                writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Disk usage after cleanup: {disk_info['percent']:.1f}% used, "
                                                     f"{disk_info['free']/(1024**3):.1f}GB free\n")

                    else:
                        writeToFile = open(backupLogPath, "a")
                        writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Failed to generate backup for: {virtualHost}. "
                                             f"Error: {retValue[1]}\n")
                        writeToFile.close()

                except BaseException as msg:
                    writeToFile = open(backupLogPath, "a")
                    writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Error processing {virtualHost}: {str(msg)}\n")
                    writeToFile.close()
                    logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [sequentialTransferProcess]")

            # Cleanup
            portpath = "/home/cyberpanel/remote_port"
            if os.path.exists(portpath):
                os.remove(portpath)

            writeToFile = open(backupLogPath, "a")
            writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Sequential transfer completed successfully\n")
            writeToFile.close()

        except BaseException as msg:
            writeToFile = open(backupLogPath, "a")
            writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Sequential transfer failed: {str(msg)}\n")
            writeToFile.close()
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [sequentialTransferProcess]")

    @staticmethod
    def rsyncTransferProcess(ipAddress, dir, backupLogPath, folderNumber, accountsToTransfer):
        """Transfer websites directly using rsync without compression"""
        try:
            writeToFile = open(backupLogPath, "a")
            writeToFile.writelines("[" + time.strftime("%m.%d.%Y_%H-%M-%S") + "] Starting rsync transfer mode\n")
            writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Processing {len(accountsToTransfer)} websites with rsync\n")
            writeToFile.close()

            # Get SSH port
            portpath = "/home/cyberpanel/remote_port"
            with open(portpath, 'r') as file:
                sshPort = file.readline().strip()

            for i, virtualHost in enumerate(accountsToTransfer, 1):
                try:
                    writeToFile = open(backupLogPath, "a")
                    writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Rsyncing website {i}/{len(accountsToTransfer)}: {virtualHost}\n")

                    # Source path on local server
                    source_path = f"/home/{virtualHost}/"
                    # Destination path on remote server
                    dest_path = f"root@{ipAddress}:/home/backup/transfer-{folderNumber}/{virtualHost}/"

                    # Build rsync command with options for efficiency and safety
                    rsync_cmd = [
                        'rsync',
                        '-avz',                    # archive, verbose, compress
                        '-e', f'ssh -o StrictHostKeyChecking=no -i /root/.ssh/cyberpanel -p {sshPort}',
                        '--progress',              # Show progress
                        '--delete',                # Delete files on destination that don't exist on source
                        '--exclude', 'backup',     # Exclude backup directories
                        '--exclude', 'logs',       # Exclude log directories
                        source_path,
                        dest_path
                    ]

                    writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Executing: {' '.join(rsync_cmd)}\n")

                    # Execute rsync
                    process = subprocess.Popen(rsync_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            universal_newlines=True)

                    # Log rsync output in real-time
                    for line in iter(process.stdout.readline, ''):
                        writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] rsync: {line.strip()}\n")
                        writeToFile.flush()

                    process.wait()

                    if process.returncode == 0:
                        writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Successfully rsynced: {virtualHost}\n")
                    else:
                        writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Rsync failed for: {virtualHost}. Return code: {process.returncode}\n")

                    writeToFile.close()

                except BaseException as msg:
                    writeToFile = open(backupLogPath, "a")
                    writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Error rsyncing {virtualHost}: {str(msg)}\n")
                    writeToFile.close()
                    logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [rsyncTransferProcess]")

            # Cleanup
            if os.path.exists(portpath):
                os.remove(portpath)

            writeToFile = open(backupLogPath, "a")
            writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Rsync transfer completed successfully\n")
            writeToFile.close()

        except BaseException as msg:
            writeToFile = open(backupLogPath, "a")
            writeToFile.writelines(f"[{time.strftime('%m.%d.%Y_%H-%M-%S')}] Rsync transfer failed: {str(msg)}\n")
            writeToFile.close()
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [rsyncTransferProcess]")


def main():
    parser = argparse.ArgumentParser(description='Enhanced CyberPanel Remote Transfer')
    parser.add_argument('function', help='Function to execute')
    parser.add_argument('--ipAddress', help='Remote IP address')
    parser.add_argument('--dir', help='Transfer directory')
    parser.add_argument('--accountsToTransfer', help='File containing accounts to transfer')
    parser.add_argument('--transferMode', help='Transfer mode: sequential, rsync, or parallel')

    args = parser.parse_args()

    if args.function == "enhancedRemoteTransfer":
        enhancedRemoteTransfer.enhancedRemoteTransfer(
            args.ipAddress,
            args.dir,
            args.accountsToTransfer,
            args.transferMode
        )

if __name__ == "__main__":
    main()