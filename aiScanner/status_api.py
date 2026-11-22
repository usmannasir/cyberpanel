import json
import math
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import AIScannerSettings, ScanHistory
from .status_models import ScanStatusUpdate
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.securityUtils import constant_time_equal


# A counter as text: digits only, and no more of them than a counter needs.
DIGITS = re.compile(r'[0-9]{1,10}\Z')


def count(data, name, highest=2147483647):
    """A counter from a status update: a whole number between nothing and the highest the field holds.

    Taken from a number, or from text that is nothing but a few digits.
    """
    value = data.get(name, 0)
    if isinstance(value, str):
        value = value.strip()
        if DIGITS.match(value) is None:
            raise ValueError(name)
        value = int(value)
    elif isinstance(value, float) and math.isfinite(value):
        value = int(value)
    elif isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(name)
    return min(max(value, 0), highest)


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
        if not isinstance(data, dict):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        scan_id = data.get('scan_id')
        if not scan_id or not isinstance(scan_id, str):
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

        if not scanner_settings.api_key or not constant_time_equal(provided_key, scanner_settings.api_key):
            logging.writeToFile(f'[Status API] Status update rejected: invalid key for scan {scan_id}')
            return JsonResponse({'error': 'Invalid API key'}, status=403)

        # Update or create status record
        status_update, created = ScanStatusUpdate.objects.update_or_create(
            scan_id=scan_id,
            defaults={
                'phase': str(data.get('phase', ''))[:50],
                'progress': count(data, 'progress', 100),
                'current_file': str(data.get('current_file', ''))[:1000],
                'files_discovered': count(data, 'files_discovered'),
                'files_scanned': count(data, 'files_scanned'),
                'files_remaining': count(data, 'files_remaining'),
                'threats_found': count(data, 'threats_found'),
                'critical_threats': count(data, 'critical_threats'),
                'high_threats': count(data, 'high_threats'),
                'activity_description': str(data.get('activity_description', ''))[:1000],
                'last_updated': timezone.now()
            }
        )

        logging.writeToFile(
            f'[Status API] Status of scan {scan_id}: {status_update.phase} {status_update.progress}%, '
            f'{status_update.files_scanned}/{status_update.files_discovered} files, '
            f'{status_update.threats_found} threats')

        return JsonResponse({'success': True})

    except json.JSONDecodeError:
        logging.writeToFile('[Status API] Invalid JSON in status update')
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except (TypeError, ValueError):
        logging.writeToFile('[Status API] Invalid values in status update')
        return JsonResponse({'error': 'Invalid data types'}, status=400)
    except Exception as e:
        logging.writeToFile(f'[Status API] Status update error: {type(e).__name__}')
        return JsonResponse({'error': 'Internal server error'}, status=500)


@require_http_methods(['GET'])
def get_live_scan_progress(request, scan_id):
    """
    Get current scan progress for real-time UI updates

    GET /api/ai-scanner/scan/{scan_id}/live-progress

    Asked by the AI Scanner page of a signed-in user, who must be allowed to
    use the scanner and to see this scan.

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
        from .access import may_see_scan, scanner_allowed
        from plogical.acl import ACLManager

        try:
            userID = request.session['userID']
        except KeyError:
            return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)
        if not scanner_allowed(ACLManager.loadedACL(userID)):
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)

        # A scan that is not the user's to see is answered like one that does not exist.
        try:
            scan_history = ScanHistory.objects.get(scan_id=scan_id)
        except ScanHistory.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Scan not found'}, status=404)
        if not may_see_scan(userID, scan_history):
            return JsonResponse({'success': False, 'error': 'Scan not found'}, status=404)

        # Get latest status update
        try:
            status_update = ScanStatusUpdate.objects.get(scan_id=scan_id)
        except ScanStatusUpdate.DoesNotExist:
            # The scan exists but has sent no status yet: it might not have started
            return JsonResponse({
                'success': False,
                'error': 'No live status available yet',
                'scan_exists': True,
                'scan_status': scan_history.status
            }, status=404)

        return JsonResponse({
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
        })

    except Exception as e:
        logging.writeToFile(f'[Status API] Get progress error: {type(e).__name__}')
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)
