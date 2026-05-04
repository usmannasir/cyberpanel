import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import AIScannerSettings, ScanHistory
from .status_models import ScanStatusUpdate
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


@csrf_exempt
@require_http_methods(['POST'])
def receive_status_update(request):
    """
    Receive real-time scan status updates from platform
    
    POST /api/ai-scanner/status-webhook
    
    Expected payload:
    {
        "scan_id": "550e8400-e29b-41d4-a716-446655440000",
        "phase": "scanning_files",
        "progress": 75,
        "current_file": "wp-content/plugins/suspicious/malware.php",
        "files_discovered": 1247,
        "files_scanned": 935,
        "files_remaining": 312,
        "threats_found": 5,
        "critical_threats": 2,
        "high_threats": 3,
        "activity_description": "Scanning file 935/1247: wp-content/plugins/suspicious/malware.php"
    }
    """
    try:
        data = json.loads(request.body)
        
        scan_id = data.get('scan_id')
        if not scan_id:
            logging.writeToFile('[Status API] Missing scan_id in status update')
            return JsonResponse({'error': 'scan_id required'}, status=400)

        provided_key = request.META.get('HTTP_X_API_KEY', '').strip()
        if not provided_key:
            logging.writeToFile('[Status API] Status update rejected: missing X-API-Key header')
            return JsonResponse({'error': 'Authentication required'}, status=401)

        try:
            scan_record = ScanHistory.objects.get(scan_id=scan_id)
            scanner_settings = AIScannerSettings.objects.get(admin=scan_record.admin)
        except (ScanHistory.DoesNotExist, AIScannerSettings.DoesNotExist):
            logging.writeToFile(f'[Status API] Status update rejected: scan not found or missing scanner settings for {scan_id}')
            return JsonResponse({'error': 'Scan not found'}, status=404)

        if provided_key != scanner_settings.api_key:
            logging.writeToFile(f'[Status API] Status update rejected: invalid key for scan {scan_id}')
            return JsonResponse({'error': 'Invalid API key'}, status=403)

        # Update or create status record
        status_update, created = ScanStatusUpdate.objects.update_or_create(
            scan_id=scan_id,
            defaults={
                'phase': data.get('phase', ''),
                'progress': int(data.get('progress', 0)),
                'current_file': data.get('current_file', ''),
                'files_discovered': int(data.get('files_discovered', 0)),
                'files_scanned': int(data.get('files_scanned', 0)),
                'files_remaining': int(data.get('files_remaining', 0)),
                'threats_found': int(data.get('threats_found', 0)),
                'critical_threats': int(data.get('critical_threats', 0)),
                'high_threats': int(data.get('high_threats', 0)),
                'activity_description': data.get('activity_description', ''),
                'last_updated': timezone.now()
            }
        )

        action = "Created" if created else "Updated"
        
        # Extended logging for debugging
        logging.writeToFile(f'[Status API] ✅ {action} status update for scan {scan_id}')
        
        # Track phase transitions
        old_phase = status_update.phase if not created else 'none'
        new_phase = data.get("phase")
        if old_phase != new_phase:
            logging.writeToFile(f'[Status API]    📊 Phase transition: {old_phase} → {new_phase}')
        
        logging.writeToFile(f'[Status API]    Phase: {data.get("phase")} → Progress: {data.get("progress", 0)}%')
        logging.writeToFile(f'[Status API]    Files: {data.get("files_scanned", 0)}/{data.get("files_discovered", 0)} ({data.get("files_remaining", 0)} remaining)')
        logging.writeToFile(f'[Status API]    Threats: {data.get("threats_found", 0)} total (Critical: {data.get("critical_threats", 0)}, High: {data.get("high_threats", 0)})')
        if data.get('current_file'):
            logging.writeToFile(f'[Status API]    Current File: {data.get("current_file")}')
        if data.get('activity_description'):
            logging.writeToFile(f'[Status API]    Activity: {data.get("activity_description")}')
        
        # Log specific phase milestones
        phase = data.get('phase', '')
        if phase == 'discovering_files' and data.get('files_discovered', 0) > 0:
            logging.writeToFile(f'[Status API]    ✅ File discovery complete: {data.get("files_discovered")} files found')
        elif phase == 'scanning_files' and data.get('files_scanned', 0) > 0:
            percentage = (data.get('files_scanned', 0) / data.get('files_discovered', 1)) * 100
            logging.writeToFile(f'[Status API]    📈 Scan progress: {percentage:.1f}% of files scanned')
        elif phase == 'ai_analysis':
            logging.writeToFile(f'[Status API]    🤖 AI Analysis phase - suspicious files being analyzed')
        
        return JsonResponse({'success': True})

    except json.JSONDecodeError:
        logging.writeToFile('[Status API] Invalid JSON in status update')
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValueError as e:
        logging.writeToFile(f'[Status API] Value error in status update: {str(e)}')
        return JsonResponse({'error': 'Invalid data types'}, status=400)
    except Exception as e:
        logging.writeToFile(f'[Status API] Status update error: {str(e)}')
        return JsonResponse({'error': 'Internal server error'}, status=500)


@require_http_methods(['GET'])
def get_live_scan_progress(request, scan_id):
    """
    Get current scan progress for real-time UI updates
    
    GET /api/ai-scanner/scan/{scan_id}/live-progress
    
    Response:
    {
        "success": true,
        "scan_id": "550e8400-e29b-41d4-a716-446655440000",
        "phase": "scanning_files",
        "progress": 75,
        "current_file": "wp-content/plugins/suspicious/malware.php",
        "files_discovered": 1247,
        "files_scanned": 935,
        "files_remaining": 312,
        "threats_found": 5,
        "critical_threats": 2,
        "high_threats": 3,
        "activity_description": "Scanning file 935/1247: wp-content/plugins/suspicious/malware.php",
        "last_updated": "2024-12-25T10:34:30Z",
        "is_active": true
    }
    """
    try:
        # Log the request
        logging.writeToFile(f'[Status API] Live progress request for scan: {scan_id}')
        
        # Get latest status update
        try:
            status_update = ScanStatusUpdate.objects.get(scan_id=scan_id)
        except ScanStatusUpdate.DoesNotExist:
            logging.writeToFile(f'[Status API] Status not found for scan {scan_id} - checking if scan exists in history')
            
            # Check if scan exists in ScanHistory
            from .models import ScanHistory
            try:
                scan_history = ScanHistory.objects.get(scan_id=scan_id)
                logging.writeToFile(f'[Status API] Scan {scan_id} exists in history with status: {scan_history.status}')
                
                # If scan exists but no status update, it might not have started yet
                return JsonResponse({
                    'success': False,
                    'error': 'No live status available yet',
                    'scan_exists': True,
                    'scan_status': scan_history.status
                }, status=404)
            except ScanHistory.DoesNotExist:
                logging.writeToFile(f'[Status API] Scan {scan_id} not found in history either')
                
            return JsonResponse({'success': False, 'error': 'Scan not found'}, status=404)

        response_data = {
            'success': True,
            'scan_id': scan_id,
            'phase': status_update.phase,
            'progress': status_update.progress,
            'current_file': status_update.current_file,
            'files_discovered': status_update.files_discovered,
            'files_scanned': status_update.files_scanned,
            'files_remaining': status_update.files_remaining,
            'threats_found': status_update.threats_found,
            'critical_threats': status_update.critical_threats,
            'high_threats': status_update.high_threats,
            'activity_description': status_update.activity_description,
            'last_updated': status_update.last_updated.isoformat(),
            'is_active': status_update.is_active
        }

        # Extended logging for frontend polling
        logging.writeToFile(f'[Status API] 📊 Frontend polling scan {scan_id}')
        logging.writeToFile(f'[Status API]    Status: {status_update.phase} ({status_update.progress}%) - Active: {status_update.is_active}')
        logging.writeToFile(f'[Status API]    Progress: {status_update.files_scanned}/{status_update.files_discovered} files, {status_update.threats_found} threats')
        if status_update.current_file:
            logging.writeToFile(f'[Status API]    Currently scanning: {status_update.current_file}')
        
        return JsonResponse(response_data)

    except Exception as e:
        logging.writeToFile(f'[Status API] Get progress error: {str(e)}')
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)