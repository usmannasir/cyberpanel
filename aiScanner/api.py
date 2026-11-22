import json
import os
import mimetypes
import base64
from datetime import timedelta
from decimal import Decimal
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from websiteFunctions.models import Websites
from loginSystem.models import Administrator
from .models import AIScannerSettings, FileAccessToken, ScanHistory
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.scannerFileAccess import Refused, SiteFiles
from plogical.securityUtils import constant_time_equal


class AuthWrapper:
    """
    Wrapper to provide consistent interface for both FileAccessToken and API Key authentication
    """
    def __init__(self, domain, wp_path, auth_type, external_app=None, source_obj=None):
        self.domain = domain
        self.wp_path = wp_path
        self.auth_type = auth_type  # 'file_token' or 'api_key'
        self.external_app = external_app  # The website's externalApp for command execution
        self.source_obj = source_obj  # Original FileAccessToken or AIScannerSettings object


def extract_auth_token(request):
    """
    Extract authentication token from either Bearer or X-API-Key header

    Returns: (token, auth_type) where auth_type is 'bearer' or 'api_key'
    """
    # Check for X-API-Key header first (preferred for permanent auth)
    api_key_header = request.META.get('HTTP_X_API_KEY', '')
    if api_key_header:
        logging.writeToFile(f'[API] Using X-API-Key authentication')
        return api_key_header, 'api_key'

    # Check for Bearer token (backward compatibility)
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        logging.writeToFile(f'[API] Using Bearer token authentication')
        return auth_header.replace('Bearer ', ''), 'bearer'

    return None, None


# The scanner key of a scan's owner works on that scan's website for this long
# after the scan finished (or was started, when no result ever arrived). The
# platform uses it to apply the fixes a customer chooses from the scan report.
KEY_ACCESS_DAYS = 7


def scan_website(domain):
    """The website a scan was started for: the one whose domain is exactly the scan's domain."""
    try:
        return Websites.objects.get(domain=domain)
    except Websites.DoesNotExist:
        return None


def validate_access_token(token, scan_id):
    """
    Validate authentication - accepts the file access token of a running scan,
    or the scanner API key of the administrator who owns the scan.

    Authentication Flow:
    1. FileAccessToken (temporary token of this scan, while it is valid)
    2. API key of the scan's owner (for file operations after the scan)

    Either way the website is the one named by the scan itself, found by its
    exact domain, and files are reached as that website's own user.

    Returns: (AuthWrapper object or None, error_message or None)
    """
    try:
        if not isinstance(token, str) or not token.startswith('cp_') or not isinstance(scan_id, str) or not scan_id:
            return None, "Invalid token format"

        # OPTION 1: the file access token of this scan (for active scans)
        file_token = FileAccessToken.objects.filter(
            token=token,
            scan_history__scan_id=scan_id,
            is_active=True
        ).first()

        if file_token is not None and not file_token.is_expired():
            website = scan_website(file_token.domain)
            if website is None:
                logging.writeToFile(f'[API] Website not found for scan {scan_id}')
                return None, "Website not found"

            return AuthWrapper(
                domain=file_token.domain,
                wp_path=file_token.wp_path,
                auth_type='file_token',
                external_app=website.externalApp,
                source_obj=file_token
            ), None

        # OPTION 2: the scanner API key of the administrator who owns this scan
        try:
            scan = ScanHistory.objects.get(scan_id=scan_id)
            scanner_settings = AIScannerSettings.objects.get(admin=scan.admin)
        except (ScanHistory.DoesNotExist, AIScannerSettings.DoesNotExist):
            return None, "Invalid token"

        if not scanner_settings.api_key or not constant_time_equal(token, scanner_settings.api_key):
            logging.writeToFile(f'[API] Token not valid for scan {scan_id}')
            return None, "Invalid token"

        finished = scan.completed_at or scan.started_at
        if finished is None or timezone.now() - finished > timedelta(days=KEY_ACCESS_DAYS):
            logging.writeToFile(f'[API] Scan {scan_id} is too old for file operations')
            return None, "Scan is too old for file operations. Run a new scan."

        website = scan_website(scan.domain)
        if website is None:
            logging.writeToFile(f'[API] Website not found for scan {scan_id}')
            return None, "Website not found"

        # The website may have changed hands since the scan.
        from plogical.acl import ACLManager
        if ACLManager.checkOwnership(scan.domain, scan.admin, ACLManager.loadedACL(scan.admin.pk)) != 1:
            logging.writeToFile(f'[API] Scan {scan_id} is for a website its owner no longer has')
            return None, "Website not found"

        return AuthWrapper(
            domain=scan.domain,
            wp_path=site_home(scan.domain) + '/public_html',
            auth_type='api_key',
            external_app=website.externalApp,
            source_obj=scanner_settings
        ), None

    except Exception as e:
        logging.writeToFile(f'[API] Token validation error: {type(e).__name__}')
        return None, "Token validation failed"


def site_home(domain):
    """The home directory of a website; its backups are kept there, outside every served folder."""
    return '/home/' + domain


def site_files(auth):
    """File access for the website a request was authenticated for, as that website's own user."""
    return SiteFiles(auth.external_app, site_home(auth.domain), auth.wp_path)


# What a refused file request is answered with: HTTP status, message, error code.
REFUSALS = {
    'path_not_allowed': (403, 'Path not allowed', 'PATH_NOT_ALLOWED'),
    'path_too_long': (400, 'Path too long', 'PATH_TOO_LONG'),
    'other_directory': (403, 'A file can only be renamed inside its own folder', 'RENAME_OTHER_FOLDER'),
    'changed': (409, 'File changed while it was being backed up', 'FILE_CHANGED'),
    'not_found': (404, 'File not found', 'FILE_NOT_FOUND'),
    'not_a_file': (404, 'File not found', 'FILE_NOT_FOUND'),
    'type_not_allowed': (403, 'File type not allowed', 'FILE_TYPE_NOT_ALLOWED'),
    'too_large': (400, 'File too large (max 10MB)', 'FILE_TOO_LARGE'),
    'protected_file': (403, 'This file is protected and cannot be changed by the scanner', 'PROTECTED_FILE'),
    'no_site_user': (500, 'Website has no system user', 'NO_USER'),
    'hash_mismatch': (400, 'Hash verification failed - file was modified during scan', 'HASH_MISMATCH'),
    'exists': (409, 'Destination file already exists', 'FILE_EXISTS'),
    'backup_dir_failed': (500, 'Failed to create backup directory', 'BACKUP_DIR_FAILED'),
    'backup_failed': (500, 'Failed to backup file', 'BACKUP_FAILED'),
    'write_failed': (500, 'Failed to write file', 'WRITE_FAILED'),
    'replace_failed': (500, 'Failed to replace file', 'REPLACE_FAILED'),
    'rename_failed': (500, 'Failed to rename file', 'RENAME_FAILED'),
    'delete_failed': (500, 'Failed to delete file', 'DELETE_FAILED'),
}


def refusal_reply(refusal):
    return REFUSALS.get(refusal.code, (500, 'File operation failed', 'FILE_OPERATION_FAILED'))


def text_field(data, name):
    """A text field of a JSON request; anything else is an empty path, which every operation refuses."""
    value = data.get(name, '') if isinstance(data, dict) else ''
    return value if isinstance(value, str) else ''


def iso_time(timestamp):
    import datetime
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M:%SZ')


def now_iso():
    import datetime
    return datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')


def guess_mime_type(path):
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type:
        return mime_type
    extension = os.path.splitext(path)[1].lower()
    if extension == '.php':
        return 'text/x-php'
    if extension == '.js':
        return 'application/javascript'
    return 'text/plain'


@csrf_exempt
@require_http_methods(['POST'])
def authenticate_worker(request):
    """
    POST /api/ai-scanner/authenticate
    
    Request Body:
    {
        "access_token": "cp_access_abc123...",
        "scan_id": "550e8400-e29b-41d4-a716-446655440000",
        "worker_id": "scanner-1.domain.com"
    }
    
    Response:
    {
        "success": true,
        "site_info": {
            "domain": "client-domain.com",
            "wp_path": "/home/client/public_html",
            "php_version": "8.1",
            "wp_version": "6.3.1"
        },
        "permissions": ["read_files", "list_directories"],
        "expires_at": "2024-12-25T11:00:00Z"
    }
    """
    try:
        data = json.loads(request.body)
        access_token = data.get('access_token')
        scan_id = data.get('scan_id')
        
        logging.writeToFile(f'[API] Authentication request for scan {scan_id}')
        
        if not access_token or not scan_id:
            return JsonResponse({'error': 'Missing access_token or scan_id'}, status=400)

        # Validate access token
        file_token, error = validate_access_token(access_token, scan_id)
        if error:
            return JsonResponse({'error': error}, status=401)
        
        wp_version = 'Unknown'
        php_version = 'Unknown'

        # Read the WordPress version from wp-includes/version.php as the website user
        try:
            import re
            version_file = site_files(file_token).read_file('wp-includes/version.php')
            match = re.search(r'\$wp_version\s*=\s*[\'"]([^\'"]+)[\'"]',
                              version_file['data'].decode('utf-8', errors='replace'))
            if match:
                wp_version = match.group(1)
        except Refused:
            logging.writeToFile('[API] Could not read WP version file')

        # Try to detect PHP version (basic detection)
        try:
            import re
            import subprocess
            result = subprocess.run(['php', '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5)
            if result.returncode == 0:
                match = re.search(r'PHP (\d+\.\d+)', result.stdout)
                if match:
                    php_version = match.group(1)
        except Exception:
            pass

        response_data = {
            'success': True,
            'site_info': {
                'domain': file_token.domain,
                'wp_path': file_token.wp_path,
                'php_version': php_version,
                'wp_version': wp_version,
                'scan_id': scan_id
            },
            'permissions': ['read_files', 'list_directories'],
        }
        expires_at = getattr(file_token.source_obj, 'expires_at', None)
        if expires_at:
            response_data['expires_at'] = expires_at.strftime('%Y-%m-%dT%H:%M:%SZ')

        logging.writeToFile(f'[API] Authentication successful for {file_token.domain}')
        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logging.writeToFile(f'[API] Authentication error: {type(e).__name__}')
        return JsonResponse({'error': 'Authentication failed'}, status=500)


@csrf_exempt  
@require_http_methods(['GET'])
def list_files(request):
    """
    GET /api/ai-scanner/files/list?path=wp-content/plugins
    
    Headers:
    Authorization: Bearer cp_access_abc123...
    X-Scan-ID: 550e8400-e29b-41d4-a716-446655440000
    
    Response:
    {
        "path": "wp-content/plugins",
        "items": [
            {
                "name": "akismet",
                "type": "directory",
                "size": 0,
                "permissions": "rwx"
            },
            {
                "name": "suspicious-plugin.php",
                "type": "file",
                "size": 15420,
                "permissions": "rw-"
            }
        ]
    }
    """
    try:
        # Validate authorization (supports both Bearer token and X-API-Key)
        access_token, auth_type = extract_auth_token(request)
        if not access_token:
            return JsonResponse({'error': 'Missing or invalid Authorization header. Use Bearer token or X-API-Key header'}, status=401)

        scan_id = request.META.get('HTTP_X_SCAN_ID', '')

        if not scan_id:
            return JsonResponse({'error': 'X-Scan-ID header required'}, status=400)

        # Validate access token
        file_token, error = validate_access_token(access_token, scan_id)
        if error:
            return JsonResponse({'error': error}, status=401)

        # Get parameters
        path = request.GET.get('path', '').strip('/')

        # The folder is listed as the website user and only inside the site
        try:
            files = site_files(file_token)
            items = files.list_directory(path)
        except Refused as refusal:
            if refusal.code == 'path_not_allowed':
                logging.writeToFile(f'[API] Path not allowed for scan {scan_id}')
                return JsonResponse({'error': 'Path not allowed'}, status=403)
            if refusal.code == 'no_site_user':
                return JsonResponse({'error': 'Website not found'}, status=404)
            return JsonResponse({'error': 'Directory access failed'}, status=403)

        if files.left_out:
            logging.writeToFile(
                f'[API] Listing for scan {scan_id} left out {files.left_out} entries: '
                'their names hold control characters or are not text')

        return JsonResponse({
            'path': path,
            'items': sorted(items, key=lambda x: (x['type'] == 'file', x['name'].lower()))
        })

    except Exception as e:
        logging.writeToFile(f'[API] List files error: {type(e).__name__}')
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(['GET']) 
def get_file_content(request):
    """
    GET /api/ai-scanner/files/content?path=wp-content/plugins/plugin.php
    
    Headers:
    Authorization: Bearer cp_access_abc123...
    X-Scan-ID: 550e8400-e29b-41d4-a716-446655440000
    
    Response:
    {
        "path": "wp-content/plugins/plugin.php",
        "content": "<base64 of the file's bytes>",
        "size": 15420,
        "encoding": "utf-8",
        "mime_type": "text/x-php"
    }
    """
    try:
        # Validate authorization (supports both Bearer token and X-API-Key)
        access_token, auth_type = extract_auth_token(request)
        if not access_token:
            return JsonResponse({'error': 'Missing or invalid Authorization header. Use Bearer token or X-API-Key header'}, status=401)

        scan_id = request.META.get('HTTP_X_SCAN_ID', '')

        if not scan_id:
            return JsonResponse({'error': 'X-Scan-ID header required'}, status=400)

        # Get file path
        path = request.GET.get('path', '').strip('/')
        if not path:
            return JsonResponse({'error': 'File path required'}, status=400)

        # Validate access token
        file_token, error = validate_access_token(access_token, scan_id)
        if error:
            return JsonResponse({'error': error}, status=401)

        # The file is read as the website user and only inside the site
        try:
            found = site_files(file_token).read_file(path)
        except Refused as refusal:
            if refusal.code == 'path_not_allowed':
                logging.writeToFile(f'[API] Path not allowed for scan {scan_id}')
                return JsonResponse({'error': 'Path not allowed'}, status=403)
            if refusal.code == 'type_not_allowed':
                return JsonResponse({'error': 'File type not allowed'}, status=403)
            if refusal.code == 'too_large':
                return JsonResponse({'error': 'File too large (max 10MB)'}, status=400)
            if refusal.code == 'no_site_user':
                return JsonResponse({'error': 'Website not found'}, status=404)
            if refusal.code in ('not_found', 'not_a_file'):
                return JsonResponse({'error': 'File not found or inaccessible'}, status=404)
            return JsonResponse({'error': 'Unable to read file'}, status=400)

        return JsonResponse({
            'path': path,
            'content': base64.b64encode(found['data']).decode('ascii'),
            'size': found['size'],
            'encoding': 'utf-8',
            'mime_type': guess_mime_type(path)
        })

    except Exception as e:
        logging.writeToFile(f'[API] Get file content error: {type(e).__name__}')
        return JsonResponse({'error': 'Internal server error'}, status=500)


def whole_number(value):
    """A count from a callback: a whole number that is never negative."""
    try:
        if isinstance(value, bool):
            return 0
        number = int(Decimal(str(value).strip()))
    except (ArithmeticError, ValueError):
        return 0
    return min(max(number, 0), 2147483647)


def money(value):
    """An amount of money from a callback, as a decimal that is never negative."""
    try:
        amount = Decimal(str(value).replace('$', '').replace(',', '').strip())
        if not amount.is_finite() or amount <= 0 or amount >= 10000:
            return Decimal('0')
        return amount.quantize(Decimal('0.000001'))
    except (ArithmeticError, ValueError):
        return Decimal('0')


# What a scan can become when the platform reports its end.
FINAL_SCAN_STATES = ('completed', 'failed', 'cancelled')


@csrf_exempt
@require_http_methods(['POST'])
def scan_callback(request):
    """
    Receive scan completion callbacks from AI Scanner platform

    POST /api/ai-scanner/callback
    Content-Type: application/json
    X-API-Key: the scanner key of the scan's owner

    A scan ends once: the first callback that reports its end is stored, and
    a repeated one changes nothing.

    Expected payload:
    {
        "scan_id": "uuid",
        "status": "completed",
        "summary": {
            "threat_level": "HIGH|MEDIUM|LOW",
            "total_findings": 3,
            "files_scanned": 25,
            "cost": "$0.0456"
        },
        "findings": [
            {
                "file_path": "wp-content/plugins/file.php",
                "severity": "CRITICAL|HIGH|MEDIUM|LOW",
                "title": "Issue title",
                "description": "Detailed description",
                "ai_confidence": 95
            }
        ],
        "ai_analysis": "AI summary text",
        "completed_at": "2025-06-23T11:40:12Z"
    }
    """
    try:
        # Parse JSON payload
        data = json.loads(request.body)
        if not isinstance(data, dict):
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON payload'}, status=400)

        scan_id = data.get('scan_id')
        if not scan_id or not isinstance(scan_id, str):
            logging.writeToFile("[API] Callback rejected: missing scan_id")
            return JsonResponse({'error': 'scan_id required'}, status=400)

        provided_key = request.META.get('HTTP_X_API_KEY', '').strip()
        if not provided_key:
            logging.writeToFile('[API] Callback rejected: missing X-API-Key header')
            return JsonResponse({'error': 'Authentication required'}, status=401)

        try:
            scan_record = ScanHistory.objects.get(scan_id=scan_id)
            scanner_settings = AIScannerSettings.objects.get(admin=scan_record.admin)
        except (ScanHistory.DoesNotExist, AIScannerSettings.DoesNotExist):
            logging.writeToFile(f"[API] Callback rejected: scan not found or missing scanner settings for {scan_id}")
            return JsonResponse({'error': 'Scan not found'}, status=404)

        if not scanner_settings.api_key or not constant_time_equal(provided_key, scanner_settings.api_key):
            logging.writeToFile(f'[API] Callback rejected: invalid key for scan {scan_id}')
            return JsonResponse({'error': 'Invalid API key'}, status=403)

        status = data.get('status')
        if status not in FINAL_SCAN_STATES:
            logging.writeToFile(f'[API] Callback rejected: scan {scan_id} reported an unknown state')
            return JsonResponse({'status': 'error', 'message': 'Invalid status', 'scan_id': scan_id}, status=400)

        summary = data.get('summary') if isinstance(data.get('summary'), dict) else {}
        findings = data.get('findings') if isinstance(data.get('findings'), list) else []
        findings = [finding for finding in findings if isinstance(finding, dict)]
        ai_analysis = data.get('ai_analysis', '')
        completed_at = data.get('completed_at')
        total_findings = whole_number(summary.get('total_findings', 0))
        files_scanned = whole_number(summary.get('files_scanned', 0))
        cost = money(summary.get('cost', 0)) if status == 'completed' else Decimal('0')

        # Only a scan that is still under way can end, and only the first
        # callback gets to end it.
        if ScanHistory.objects.filter(pk=scan_record.pk, status__in=('pending', 'running')).update(status=status) != 1:
            logging.writeToFile(f"[API] Callback for scan {scan_id} ignored: the scan has already ended")
            return JsonResponse({
                'status': 'success',
                'message': 'Callback already processed',
                'scan_id': scan_id
            })

        logging.writeToFile(f"[API] Received callback for scan {scan_id}: {status}")

        try:
            # Update scan record
            scan_record.status = status
            scan_record.issues_found = total_findings
            scan_record.files_scanned = files_scanned
            scan_record.cost_usd = cost

            # Store findings and AI analysis
            scan_record.set_findings(findings)
            scan_record.set_summary({
                'threat_level': str(summary.get('threat_level', 'UNKNOWN'))[:20],
                'total_findings': total_findings,
                'files_scanned': files_scanned,
                'ai_analysis': ai_analysis if isinstance(ai_analysis, str) else ''
            })

            # Set completion time
            scan_record.completed_at = timezone.now()
            if isinstance(completed_at, str):
                try:
                    from plogical.isoTime import parse_iso_datetime
                    scan_record.completed_at = parse_iso_datetime(completed_at.replace('Z', '+00:00'))
                except (TypeError, ValueError):
                    pass

            scan_record.save()

            # Also update the ScanStatusUpdate record with final statistics
            try:
                from .status_models import ScanStatusUpdate
                status_update, _ = ScanStatusUpdate.objects.get_or_create(scan_id=scan_id)
                status_update.phase = status
                status_update.progress = 100
                status_update.files_discovered = files_scanned  # Use files_scanned as approximation
                status_update.files_scanned = files_scanned
                status_update.files_remaining = 0
                status_update.threats_found = total_findings
                # Extract critical and high threats from findings if available
                severities = [str(finding.get('severity', '')).lower() for finding in findings]
                status_update.critical_threats = severities.count('critical')
                status_update.high_threats = severities.count('high')
                status_update.activity_description = f"Scan {status} - {total_findings} threats found"
                status_update.save()
            except Exception as e:
                logging.writeToFile(f"[API] Error updating ScanStatusUpdate: {type(e).__name__}")

            # Take the cost off the balance once, and only when the balance covers it
            if cost > 0:
                try:
                    charged = AIScannerSettings.objects.filter(
                        pk=scanner_settings.pk, balance__gte=cost).update(balance=F('balance') - cost)
                    if charged != 1:
                        logging.writeToFile(f"[API] Balance does not cover the cost of scan {scan_id}")
                except Exception as e:
                    logging.writeToFile(f"[API] Error updating balance: {type(e).__name__}")

            # Deactivate file access tokens for this scan
            try:
                FileAccessToken.objects.filter(scan_history=scan_record).update(is_active=False)
            except Exception as e:
                logging.writeToFile(f"[API] Error deactivating tokens: {type(e).__name__}")

            logging.writeToFile(
                f"[API] Scan {scan_id} {status}: {total_findings} findings, {files_scanned} files scanned")

        except Exception as e:
            logging.writeToFile(f"[API] Failed to update scan record: {type(e).__name__}")
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to update scan record',
                'scan_id': scan_id
            }, status=500)

        # Return success response
        return JsonResponse({
            'status': 'success',
            'message': 'Callback received successfully',
            'scan_id': scan_id
        })

    except json.JSONDecodeError:
        logging.writeToFile("[API] Invalid JSON in callback request")
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON payload'
        }, status=400)

    except Exception as e:
        logging.writeToFile(f"[API] Callback processing error: {type(e).__name__}")
        return JsonResponse({
            'status': 'error',
            'message': 'Internal server error'
        }, status=500)


# =============================================================================
# File Operation Helper Functions
# =============================================================================

def log_file_operation(scan_id, operation, file_path, success, error_message=None, backup_path=None, request=None):
    """
    Log file operations to the audit log
    """
    try:
        from .models import ScannerFileOperation

        ip_address = None
        user_agent = None

        if request:
            ip_address = request.META.get('REMOTE_ADDR', '')[:45]
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]

        ScannerFileOperation.objects.create(
            scan_id=scan_id,
            operation=operation,
            file_path=file_path,
            backup_path=backup_path,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent
        )

        logging.writeToFile(f'[API] Logged {operation} operation for {file_path}: {"success" if success else "failed"}')
    except Exception as e:
        logging.writeToFile(f'[API] Failed to log operation: {str(e)}')


# Requests to one endpoint for one scan are counted over this long.
RATE_LIMIT_WINDOW = timedelta(hours=1)


def check_rate_limit(scan_id, endpoint, max_requests):
    """
    Count one request to an endpoint for a scan, unless the limit of the
    current time window is reached.
    Returns (is_allowed, current_count); a failure to count is not allowed.
    """
    try:
        from .models import ScannerAPIRateLimit

        now = timezone.now()
        rate_limit, created = ScannerAPIRateLimit.objects.get_or_create(
            scan_id=scan_id,
            endpoint=endpoint,
            defaults={'request_count': 0}
        )
        counters = ScannerAPIRateLimit.objects.filter(pk=rate_limit.pk)

        # last_request_at holds the start of the window: a window that is over starts again.
        counters.filter(last_request_at__lt=now - RATE_LIMIT_WINDOW).update(request_count=0, last_request_at=now)

        # Counted in the database, so requests that arrive together cannot pass the limit.
        if counters.filter(request_count__lt=max_requests).update(request_count=F('request_count') + 1) != 1:
            logging.writeToFile(f'[API] Rate limit exceeded for scan {scan_id} on endpoint {endpoint}')
            return False, max_requests

        return True, 0
    except Exception as e:
        logging.writeToFile(f'[API] Rate limit check error: {type(e).__name__}')
        return False, 0


# =============================================================================
# File Operation API Endpoints
# =============================================================================

def file_request(request, operation, scan_id, file_path):
    """Authenticate one file operation request.

    Reading is open to a scan's file access token and to the scanner key of
    the scan's owner; backing up, replacing, renaming and deleting need the key.

    Returns (authentication, None) or (None, the reply to send).
    """
    access_token, auth_type = extract_auth_token(request)
    if not access_token:
        return None, JsonResponse({'success': False, 'error': 'Missing or invalid Authorization header. Use Bearer token or X-API-Key header'}, status=401)

    if not scan_id:
        return None, JsonResponse({'success': False, 'error': 'X-Scan-ID header required'}, status=400)

    file_token, error = validate_access_token(access_token, scan_id)
    if error:
        log_file_operation(scan_id, operation, file_path, False, error, request=request)
        return None, JsonResponse({'success': False, 'error': error}, status=401)

    # The token a scan hands to its workers reads files and nothing more.
    if operation != 'read' and file_token.auth_type != 'api_key':
        error = 'The file access token of a scan can only read files'
        log_file_operation(scan_id, operation, file_path, False, error, request=request)
        return None, JsonResponse({'success': False, 'error': error, 'error_code': 'READ_ONLY_TOKEN'}, status=403)

    return file_token, None


def refused_file_reply(refusal, scan_id, operation, file_path, request, extra=None):
    """Record a refused file operation and build its reply."""
    status, error, error_code = refusal_reply(refusal)
    backup_path = refusal.details.get('backup_path')
    log_file_operation(scan_id, operation, file_path, False, error, backup_path=backup_path, request=request)
    reply = {'success': False, 'error': error, 'error_code': error_code}
    if extra:
        reply.update(extra)
    return JsonResponse(reply, status=status)


def rate_limited(file_token, scan_id, endpoint, token_limit, key_limit, what):
    """Higher limits for API key authenticated requests (platform operations)."""
    limit = key_limit if file_token.auth_type == 'api_key' else token_limit
    is_allowed, count = check_rate_limit(scan_id, endpoint, limit)
    if is_allowed:
        return None
    return JsonResponse({'success': False, 'error': f'Rate limit exceeded (max {limit} {what} per scan and hour)'}, status=429)


@csrf_exempt
@require_http_methods(['POST'])
def scanner_backup_file(request):
    """
    POST /api/scanner/backup-file

    Create a backup copy of a file before modification. The copy is kept in
    the website's home, outside every folder the web server serves.

    Headers:
        X-API-Key: {scanner api key}
        X-Scan-ID: {scan_job_id}

    Request Body:
        {
            "file_path": "wp-content/plugins/example/plugin.php",
            "scan_id": "550e8400-e29b-41d4-a716-446655440000"
        }

    Response:
        {
            "success": true,
            "backup_path": "/home/example.com/.ai-scanner-backups/2025-10-25/plugin.php.1730000000.1a2b3c4d5e6f.bak",
            "original_path": "wp-content/plugins/example/plugin.php",
            "backup_size": 15420,
            "timestamp": "2025-10-25T20:30:00Z"
        }
    """
    scan_id = 'unknown'
    file_path = 'unknown'
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            data = {}
        file_path = text_field(data, 'file_path').strip('/')
        scan_id = text_field(data, 'scan_id')
        header_scan_id = request.META.get('HTTP_X_SCAN_ID', '')

        if not scan_id or not header_scan_id or scan_id != header_scan_id:
            return JsonResponse({'success': False, 'error': 'Scan ID mismatch'}, status=400)

        file_token, reply = file_request(request, 'backup', scan_id, file_path)
        if reply:
            return reply

        reply = rate_limited(file_token, scan_id, 'backup-file', 100, 1000, 'backups')
        if reply:
            return reply

        try:
            backup = site_files(file_token).backup_file(file_path)
        except Refused as refusal:
            return refused_file_reply(refusal, scan_id, 'backup', file_path, request)

        log_file_operation(scan_id, 'backup', file_path, True, backup_path=backup['backup_path'], request=request)

        return JsonResponse({
            'success': True,
            'backup_path': backup['backup_path'],
            'original_path': file_path,
            'backup_size': backup['size'],
            'timestamp': now_iso()
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logging.writeToFile(f'[API] Backup file error: {type(e).__name__}')
        log_file_operation(scan_id, 'backup', file_path, False, 'Internal server error', request=request)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(['GET'])
def scanner_get_file(request):
    """
    GET /api/scanner/get-file?file_path=wp-content/plugins/plugin.php

    Read the contents of a file for analysis or verification

    Headers:
        Authorization: Bearer {file_access_token}  or  X-API-Key: {scanner api key}
        X-Scan-ID: {scan_job_id}

    Response:
        {
            "success": true,
            "file_path": "wp-content/plugins/example/plugin.php",
            "content": "<?php\n/*\nPlugin Name: Example Plugin\n*/\n...",
            "size": 15420,
            "encoding": "utf-8",
            "mime_type": "text/x-php",
            "last_modified": "2025-10-25T20:30:00Z",
            "hash": {
                "md5": "5d41402abc4b2a76b9719d911017c592",
                "sha256": "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
            }
        }
    """
    scan_id = 'unknown'
    file_path = 'unknown'
    try:
        scan_id = request.META.get('HTTP_X_SCAN_ID', '')
        file_path = request.GET.get('file_path', '').strip('/')

        access_token, auth_type = extract_auth_token(request)
        if not access_token:
            return JsonResponse({'success': False, 'error': 'Missing or invalid Authorization header. Use Bearer token or X-API-Key header'}, status=401)
        if not scan_id:
            return JsonResponse({'success': False, 'error': 'X-Scan-ID header required'}, status=400)
        if not file_path:
            return JsonResponse({'success': False, 'error': 'File path required'}, status=400)

        file_token, reply = file_request(request, 'read', scan_id, file_path)
        if reply:
            return reply

        reply = rate_limited(file_token, scan_id, 'get-file', 500, 5000, 'file reads')
        if reply:
            return reply

        try:
            found = site_files(file_token).read_file(file_path)
        except Refused as refusal:
            return refused_file_reply(refusal, scan_id, 'read', file_path, request)

        log_file_operation(scan_id, 'read', file_path, True, request=request)

        return JsonResponse({
            'success': True,
            'file_path': file_path,
            'content': found['data'].decode('utf-8', errors='replace'),
            'size': found['size'],
            'encoding': 'utf-8',
            'mime_type': guess_mime_type(file_path),
            'last_modified': iso_time(found['modified']),
            'hash': {
                'md5': found['md5'],
                'sha256': found['sha256']
            }
        })

    except Exception as e:
        logging.writeToFile(f'[API] Get file error: {type(e).__name__}')
        log_file_operation(scan_id, 'read', file_path, False, 'Internal server error', request=request)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def scanner_replace_file(request):
    """
    POST /api/scanner/replace-file

    Overwrite an existing file with new content (after backup)

    Headers:
        X-API-Key: {scanner api key}
        X-Scan-ID: {scan_job_id}

    Request Body:
        {
            "file_path": "wp-content/plugins/example/plugin.php",
            "content": "<?php\n/*\nPlugin Name: Example Plugin (Clean Version)\n*/\n...",
            "backup_before_replace": true,
            "verify_hash": "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
        }

    Response:
        {
            "success": true,
            "file_path": "wp-content/plugins/example/plugin.php",
            "backup_path": "/home/example.com/.ai-scanner-backups/2025-10-25/plugin.php.1730000000.1a2b3c4d5e6f.bak",
            "bytes_written": 14850,
            "new_hash": {
                "md5": "abc123...",
                "sha256": "def456..."
            },
            "timestamp": "2025-10-25T20:35:00Z"
        }
    """
    scan_id = 'unknown'
    file_path = 'unknown'
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            data = {}
        scan_id = request.META.get('HTTP_X_SCAN_ID', '')
        file_path = text_field(data, 'file_path').strip('/')
        content = text_field(data, 'content')
        backup_before_replace = data.get('backup_before_replace', True) is not False
        verify_hash = text_field(data, 'verify_hash')

        file_token, reply = file_request(request, 'replace', scan_id, file_path)
        if reply:
            return reply

        reply = rate_limited(file_token, scan_id, 'replace-file', 100, 1000, 'replacements')
        if reply:
            return reply

        try:
            replaced = site_files(file_token).replace_file(
                file_path, content.encode('utf-8'), backup=backup_before_replace,
                verify_sha256=verify_hash or None)
        except Refused as refusal:
            extra = None
            if refusal.code == 'hash_mismatch':
                extra = {'expected_hash': verify_hash, 'actual_hash': refusal.details.get('actual', '')}
            return refused_file_reply(refusal, scan_id, 'replace', file_path, request, extra)

        log_file_operation(scan_id, 'replace', file_path, True, backup_path=replaced['backup_path'], request=request)

        return JsonResponse({
            'success': True,
            'file_path': file_path,
            'backup_path': replaced['backup_path'],
            'bytes_written': replaced['bytes_written'],
            'new_hash': {
                'md5': replaced['md5'],
                'sha256': replaced['sha256']
            },
            'timestamp': now_iso()
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logging.writeToFile(f'[API] Replace file error: {type(e).__name__}')
        log_file_operation(scan_id, 'replace', file_path, False, 'Internal server error', request=request)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def scanner_rename_file(request):
    """
    POST /api/scanner/rename-file

    Rename a file (used for quarantining malicious files)

    Headers:
        X-API-Key: {scanner api key}
        X-Scan-ID: {scan_job_id}

    Request Body:
        {
            "old_path": "wp-content/uploads/malicious.php",
            "new_path": "wp-content/uploads/malicious.php.quarantined.1730000000",
            "backup_before_rename": true
        }

    The new name must be in the folder the file is in.

    Response:
        {
            "success": true,
            "old_path": "wp-content/uploads/malicious.php",
            "new_path": "wp-content/uploads/malicious.php.quarantined.1730000000",
            "backup_path": "/home/example.com/.ai-scanner-backups/2025-10-25/malicious.php.1730000000.1a2b3c4d5e6f.bak",
            "timestamp": "2025-10-25T20:40:00Z"
        }
    """
    scan_id = 'unknown'
    old_path = 'unknown'
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            data = {}
        scan_id = request.META.get('HTTP_X_SCAN_ID', '')
        old_path = text_field(data, 'old_path').strip('/')
        new_path = text_field(data, 'new_path').strip('/')
        backup_before_rename = data.get('backup_before_rename', True) is not False

        file_token, reply = file_request(request, 'rename', scan_id, old_path)
        if reply:
            return reply

        reply = rate_limited(file_token, scan_id, 'rename-file', 50, 500, 'renames')
        if reply:
            return reply

        try:
            renamed = site_files(file_token).rename_file(old_path, new_path, backup=backup_before_rename)
        except Refused as refusal:
            return refused_file_reply(refusal, scan_id, 'rename', old_path, request)

        log_file_operation(scan_id, 'rename', old_path, True, backup_path=renamed['backup_path'], request=request)

        return JsonResponse({
            'success': True,
            'old_path': old_path,
            'new_path': new_path,
            'backup_path': renamed['backup_path'],
            'timestamp': now_iso()
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logging.writeToFile(f'[API] Rename file error: {type(e).__name__}')
        log_file_operation(scan_id, 'rename', old_path, False, 'Internal server error', request=request)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def scanner_delete_file(request):
    """
    POST /api/scanner/delete-file

    Permanently delete a malicious file (after backup)

    Headers:
        X-API-Key: {scanner api key}
        X-Scan-ID: {scan_job_id}

    Request Body:
        {
            "file_path": "wp-content/uploads/shell.php",
            "confirm_deletion": true
        }

    Response:
        {
            "success": true,
            "file_path": "wp-content/uploads/shell.php",
            "backup_path": "/home/example.com/.ai-scanner-backups/2025-10-25/shell.php.1730000000.1a2b3c4d5e6f.bak",
            "deleted_at": "2025-10-25T20:45:00Z",
            "file_info": {
                "size": 2048,
                "last_modified": "2025-10-20T14:30:00Z",
                "hash": "abc123..."
            }
        }
    """
    scan_id = 'unknown'
    file_path = 'unknown'
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            data = {}
        scan_id = request.META.get('HTTP_X_SCAN_ID', '')
        file_path = text_field(data, 'file_path').strip('/')

        # Require explicit confirmation
        if data.get('confirm_deletion') is not True:
            return JsonResponse({
                'success': False,
                'error': 'Deletion not confirmed',
                'error_code': 'CONFIRMATION_REQUIRED',
                'message': 'Set confirm_deletion: true to proceed'
            }, status=400)

        file_token, reply = file_request(request, 'delete', scan_id, file_path)
        if reply:
            return reply

        reply = rate_limited(file_token, scan_id, 'delete-file', 50, 500, 'deletions')
        if reply:
            return reply

        # A copy is always kept before a file is deleted
        try:
            deleted = site_files(file_token).delete_file(file_path)
        except Refused as refusal:
            return refused_file_reply(refusal, scan_id, 'delete', file_path, request)

        log_file_operation(scan_id, 'delete', file_path, True, backup_path=deleted['backup_path'], request=request)

        return JsonResponse({
            'success': True,
            'file_path': file_path,
            'backup_path': deleted['backup_path'],
            'deleted_at': now_iso(),
            'file_info': {
                'size': deleted['size'],
                'last_modified': iso_time(deleted['modified']),
                'hash': deleted['sha256']
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logging.writeToFile(f'[API] Delete file error: {type(e).__name__}')
        log_file_operation(scan_id, 'delete', file_path, False, 'Internal server error', request=request)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)
