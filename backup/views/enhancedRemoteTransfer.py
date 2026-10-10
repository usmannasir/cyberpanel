import os
import sys
import subprocess
import json
import psutil
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from plogical import enhancedRemoteTransfer
from plogical.processUtilities import ProcessUtilities
from plogical import CyberCPLogFileWriter as logging

# Add CyberCP path
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
import django
django.setup()

def enhanced_remote_transfer_view(request):
    """Render the enhanced remote transfer page"""
    return render(request, 'backup/enhancedRemoteTransfer.html')

@require_http_methods(["GET"])
def disk_analysis_view(request):
    """Analyze disk space and return recommendations"""
    try:
        # Get disk usage
        disk_info = enhancedRemoteTransfer.enhancedRemoteTransfer.getDiskUsage()

        if not disk_info:
            return JsonResponse({
                'status': 0,
                'error': 'Could not retrieve disk usage information'
            })

        # Convert to GB
        total_gb = disk_info['total'] / (1024**3)
        used_gb = disk_info['used'] / (1024**3)
        free_gb = disk_info['free'] / (1024**3)
        usage_percent = disk_info['percent']

        # Determine recommended mode
        free_percent = (disk_info['free'] / disk_info['total']) * 100
        rsync_available = enhancedRemoteTransfer.enhancedRemoteTransfer.checkRsyncAvailability()

        if rsync_available and free_percent < 30:
            recommended_mode = 'rsync'
        elif free_percent < 50:
            recommended_mode = 'sequential'
        else:
            recommended_mode = 'parallel'

        return JsonResponse({
            'status': 1,
            'disk_usage_percent': usage_percent,
            'total_space_gb': total_gb,
            'used_space_gb': used_gb,
            'free_space_gb': free_gb,
            'recommended_mode': recommended_mode,
            'rsync_available': rsync_available
        })

    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error in disk analysis: {str(e)}")
        return JsonResponse({
            'status': 0,
            'error': str(e)
        })

@require_http_methods(["POST"])
@csrf_exempt
def update_recommendations_view(request):
    """Update transfer recommendations based on selected websites"""
    try:
        data = json.loads(request.body)
        websites = data.get('websites', [])

        if not websites:
            return JsonResponse({
                'status': 0,
                'error': 'No websites provided'
            })

        # Calculate total size
        total_size = enhancedRemoteTransfer.enhancedRemoteTransfer.calculateWebsitesSize(websites)
        estimated_size_gb = total_size / (1024**3)

        # Get disk info
        disk_info = enhancedRemoteTransfer.enhancedRemoteTransfer.getDiskUsage()

        if not disk_info:
            return JsonResponse({
                'status': 0,
                'error': 'Could not get disk information'
            })

        free_gb = disk_info['free'] / (1024**3)
        free_percent = (disk_info['free'] / disk_info['total']) * 100

        # Determine recommendations
        if free_gb < estimated_size_gb * 0.3:
            recommended_mode = 'rsync'
            space_requirement = f"Rsync recommended (minimal space needed). Available: {free_gb:.1f}GB"
        elif free_gb < estimated_size_gb:
            recommended_mode = 'sequential'
            space_requirement = f"Sequential transfer recommended. Estimated: {estimated_size_gb:.1f}GB, Available: {free_gb:.1f}GB"
        else:
            recommended_mode = 'parallel'
            space_requirement = f"Parallel transfer possible. Estimated: {estimated_size_gb:.1f}GB, Available: {free_gb:.1f}GB"

        return JsonResponse({
            'status': 1,
            'estimated_size_gb': estimated_size_gb,
            'space_requirement_text': space_requirement,
            'recommended_mode': recommended_mode
        })

    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error updating recommendations: {str(e)}")
        return JsonResponse({
            'status': 0,
            'error': str(e)
        })

@require_http_methods(["POST"])
@csrf_exempt
def fetch_remote_accounts_view(request):
    """Fetch accounts from remote server (reuse existing logic)"""
    try:
        # This should integrate with existing remote account fetching logic
        # For now, return mock data - integrate with actual remote transfer utilities

        data = json.loads(request.body)
        ip_address = data.get('ipAddress')
        root_password = data.get('rootPassword')
        root_ssh_key = data.get('rootSSHKey')

        # TODO: Integrate with existing account fetching logic
        # This would involve calling the existing remote transfer functions

        # Mock accounts for demonstration
        mock_accounts = [
            'example.com',
            'test-site.org',
            'blog.example.net'
        ]

        return JsonResponse({
            'status': 1,
            'accounts': mock_accounts
        })

    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error fetching remote accounts: {str(e)}")
        return JsonResponse({
            'status': 0,
            'error': str(e)
        })

@require_http_methods(["POST"])
@csrf_exempt
def start_enhanced_transfer_view(request):
    """Start the enhanced remote transfer process"""
    try:
        data = json.loads(request.body)
        ip_address = data.get('ipAddress')
        websites = data.get('websites', [])
        transfer_mode = data.get('transferMode')

        if not ip_address or not websites or not transfer_mode:
            return JsonResponse({
                'status': 0,
                'error': 'Missing required parameters'
            })

        # Create temporary file with websites list
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            for website in websites:
                f.write(f"{website}\n")
            accounts_file = f.name

        # Generate unique directory ID
        import time
        dir_id = str(int(time.time()))

        try:
            # Start the enhanced transfer process
            enhancedRemoteTransfer.enhancedRemoteTransfer.enhancedRemoteTransfer(
                ip_address,
                dir_id,
                accounts_file,
                transfer_mode
            )

            # Store transfer info for monitoring
            transfer_info = {
                'ip_address': ip_address,
                'websites': websites,
                'transfer_mode': transfer_mode,
                'start_time': time.time(),
                'status': 'running'
            }

            # Save transfer info to file for monitoring
            info_file = f"/home/cyberpanel/transfer_{dir_id}_info.json"
            with open(info_file, 'w') as f:
                json.dump(transfer_info, f)

            return JsonResponse({
                'status': 1,
                'dir': dir_id,
                'message': 'Transfer started successfully'
            })

        finally:
            # Clean up temp file
            try:
                os.unlink(accounts_file)
            except:
                pass

    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error starting enhanced transfer: {str(e)}")
        return JsonResponse({
            'status': 0,
            'error': str(e)
        })

@require_http_methods(["GET"])
def transfer_progress_view(request):
    """Get transfer progress information"""
    try:
        # Find the most recent transfer
        import glob
        transfer_files = glob.glob("/home/cyberpanel/transfer_*_info.json")

        if not transfer_files:
            return JsonResponse({
                'status': 1,
                'progress_percentage': 0,
                'current_website': '',
                'transferred_count': 0,
                'total_count': 0,
                'completed': True
            })

        # Get the most recent transfer
        latest_file = max(transfer_files, key=os.path.getctime)

        with open(latest_file, 'r') as f:
            transfer_info = json.load(f)

        # Parse backup log for progress
        dir_id = latest_file.split('_')[1]
        backup_log = f"/home/backup/transfer-{dir_id}/backup_log"

        if not os.path.exists(backup_log):
            return JsonResponse({
                'status': 1,
                'progress_percentage': 0,
                'current_website': '',
                'transferred_count': 0,
                'total_count': len(transfer_info.get('websites', [])),
                'completed': False
            })

        # Parse log for progress
        with open(backup_log, 'r') as f:
            log_content = f.read()

        # Count completed transfers
        completed_count = log_content.count("Successfully sent and cleaned up")
        total_count = len(transfer_info.get('websites', []))

        # Find current website being processed
        current_website = ''
        lines = log_content.split('\n')
        for line in reversed(lines):
            if 'Processing website' in line and ':' in line:
                try:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        website_part = parts[-1].strip()
                        if website_part and website_part != current_website:
                            current_website = website_part
                            break
                except:
                    continue

        # Check if completed
        completed = "transfer completed successfully" in log_content.lower()
        failed = "transfer failed" in log_content.lower() or "aborted" in log_content.lower()

        progress_percentage = (completed_count / total_count) * 100 if total_count > 0 else 0

        return JsonResponse({
            'status': 1,
            'progress_percentage': progress_percentage,
            'current_website': current_website,
            'transferred_count': completed_count,
            'total_count': total_count,
            'completed': completed,
            'failed': failed,
            'transfer_mode': transfer_info.get('transfer_mode', '')
        })

    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error getting transfer progress: {str(e)}")
        return JsonResponse({
            'status': 0,
            'error': str(e)
        })

@require_http_methods(["POST"])
@csrf_exempt
def cancel_transfer_view(request):
    """Cancel the ongoing transfer"""
    try:
        # Find the most recent transfer
        import glob
        transfer_files = glob.glob("/home/cyberpanel/transfer_*_info.json")

        if not transfer_files:
            return JsonResponse({
                'status': 0,
                'error': 'No active transfer found'
            })

        latest_file = max(transfer_files, key=os.path.getctime)

        with open(latest_file, 'r') as f:
            transfer_info = json.load(f)

        # Update status
        transfer_info['status'] = 'cancelled'
        transfer_info['end_time'] = time.time()

        with open(latest_file, 'w') as f:
            json.dump(transfer_info, f)

        # Find and kill the transfer process
        dir_id = latest_file.split('_')[1]
        pid_file = f"/home/backup/transfer-{dir_id}/pid"

        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())

                # Kill the process
                os.kill(pid, 15)  # SIGTERM
                logging.CyberCPLogFileWriter.writeToFile(f"Cancelled transfer process {pid}")

            except (FileNotFoundError, ValueError, ProcessLookupError):
                pass
            except PermissionError:
                try:
                    subprocess.run(['sudo', 'kill', '-15', str(pid)], check=False)
                except:
                    pass

        return JsonResponse({
            'status': 1,
            'message': 'Transfer cancelled successfully'
        })

    except Exception as e:
        logging.CyberCPLogFileWriter.writeToFile(f"Error cancelling transfer: {str(e)}")
        return JsonResponse({
            'status': 0,
            'error': str(e)
        })