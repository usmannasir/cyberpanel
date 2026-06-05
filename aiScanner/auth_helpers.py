"""
Shared authentication helpers for AI Scanner callbacks and file APIs.
"""

from __future__ import annotations

from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone

from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

from .models import AIScannerSettings, ScanHistory, FileAccessToken

FILE_WRITE_GRACE_HOURS = 72
FILE_WRITE_ALLOWED_STATUSES = frozenset(
    {
        'running',
        'in_progress',
        'queued',
        'completed',
        'scanning',
        'pending',
    }
)


def extract_api_key(request) -> str:
    return (request.META.get('HTTP_X_API_KEY') or '').strip()


def validate_scan_callback_credentials(request, scan_id):
    """
    Validate X-API-Key for scan callback endpoints.

    Returns (scan_history, scanner_settings, None) on success, or
    (None, None, JsonResponse) on failure.
    """
    if not scan_id:
        logging.writeToFile('[AIScannerAuth] Callback rejected: missing scan_id')
        return None, None, JsonResponse(
            {'success': False, 'error': 'Scan ID required'},
            status=400,
        )

    provided_key = extract_api_key(request)
    if not provided_key:
        logging.writeToFile('[AIScannerAuth] Callback rejected: missing X-API-Key header')
        return None, None, JsonResponse(
            {'success': False, 'error': 'Authentication required'},
            status=401,
        )

    try:
        scan_history = ScanHistory.objects.get(scan_id=scan_id)
    except ScanHistory.DoesNotExist:
        logging.writeToFile(f'[AIScannerAuth] Callback rejected: scan not found {scan_id}')
        return None, None, JsonResponse(
            {'success': False, 'error': 'Scan not found'},
            status=404,
        )

    try:
        scanner_settings = AIScannerSettings.objects.get(admin=scan_history.admin)
    except AIScannerSettings.DoesNotExist:
        logging.writeToFile(
            f'[AIScannerAuth] Callback rejected: missing scanner settings for scan {scan_id}'
        )
        return None, None, JsonResponse(
            {'success': False, 'error': 'Scan not found'},
            status=404,
        )

    if provided_key != scanner_settings.api_key:
        logging.writeToFile(f'[AIScannerAuth] Callback rejected: invalid key for scan {scan_id}')
        return None, None, JsonResponse(
            {'success': False, 'error': 'Invalid API key'},
            status=403,
        )

    return scan_history, scanner_settings, None


def api_key_belongs_to_scan_owner(token: str, scan: ScanHistory):
    """
    Ensure the API key belongs to the administrator who owns the scan.
    Returns (scanner_settings, error_message).
    """
    scanner_settings = AIScannerSettings.objects.filter(api_key=token).first()
    if not scanner_settings:
        return None, 'Invalid token'
    if scanner_settings.admin_id != scan.admin_id:
        logging.writeToFile(
            f'[AIScannerAuth] Token admin mismatch for scan {scan.scan_id}'
        )
        return None, 'API key does not match scan owner'
    return scanner_settings, None


def scan_allows_api_key_file_write(scan: ScanHistory, auth_type: str):
    """
    API-key authenticated file writes require an active file token or a recent scan.
    Returns (allowed: bool, error_message or None).
    """
    if auth_type != 'api_key':
        return True, None

    if FileAccessToken.objects.filter(scan_history=scan, is_active=True).exists():
        return True, None

    if not scan.started_at:
        logging.writeToFile(
            f'[AIScannerAuth] File write denied: scan {scan.scan_id} has no started_at'
        )
        return False, 'File write not authorized for this scan'

    cutoff = timezone.now() - timedelta(hours=FILE_WRITE_GRACE_HOURS)
    if scan.started_at < cutoff:
        logging.writeToFile(
            f'[AIScannerAuth] File write denied: scan {scan.scan_id} outside grace window'
        )
        return False, 'File write not authorized for this scan (token expired or scan too old)'

    if scan.status not in FILE_WRITE_ALLOWED_STATUSES:
        logging.writeToFile(
            f'[AIScannerAuth] File write denied: scan {scan.scan_id} status {scan.status}'
        )
        return False, 'File write not authorized for this scan status'

    return True, None
