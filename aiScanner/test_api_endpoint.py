#!/usr/bin/env python3
"""
Test endpoint to debug API key validation for AI Scanner
Add this to your aiScanner/urls.py:
    path('api/test-auth/', test_api_endpoint.test_auth, name='test_auth'),
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .api import validate_access_token, extract_auth_token
from .models import AIScannerSettings, ScanHistory
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


@csrf_exempt
@require_http_methods(['POST'])
def test_auth(request):
    """
    Test endpoint to validate API authentication

    Usage:
    curl -X POST http://localhost:8001/api/ai-scanner/test-auth/ \
         -H "X-API-Key: cp_your_api_key_here" \
         -H "X-Scan-ID: your-scan-id" \
         -H "Content-Type: application/json" \
         -d '{"scan_id": "your-scan-id"}'
    """
    try:
        # Parse request
        data = json.loads(request.body) if request.body else {}
        scan_id = data.get('scan_id', '') or request.META.get('HTTP_X_SCAN_ID', '')

        # Extract authentication token
        access_token, auth_type = extract_auth_token(request)

        response = {
            'auth_type_detected': auth_type,
            'token_prefix': access_token[:20] + '...' if access_token else None,
            'scan_id': scan_id,
            'validation_steps': []
        }

        if not access_token:
            response['error'] = 'No authentication token found'
            response['validation_steps'].append('FAILED: No Bearer token or X-API-Key header found')
            return JsonResponse(response, status=401)

        if not scan_id:
            response['error'] = 'No scan_id provided'
            response['validation_steps'].append('FAILED: No scan_id in body or X-Scan-ID header')
            return JsonResponse(response, status=400)

        # Check if API key exists in database
        response['validation_steps'].append(f'Checking if token {access_token[:20]}... exists in database')

        api_key_exists = AIScannerSettings.objects.filter(api_key=access_token).exists()
        response['api_key_exists'] = api_key_exists

        if api_key_exists:
            response['validation_steps'].append('SUCCESS: API key found in AIScannerSettings')

            # Get the admin who owns this API key
            settings = AIScannerSettings.objects.get(api_key=access_token)
            response['api_key_owner'] = settings.admin.userName
            response['validation_steps'].append(f'API key belongs to admin: {settings.admin.userName}')
        else:
            response['validation_steps'].append('WARNING: API key not found in AIScannerSettings')

        # Check if scan exists
        response['validation_steps'].append(f'Checking if scan {scan_id} exists')

        try:
            scan = ScanHistory.objects.get(scan_id=scan_id)
            response['scan_exists'] = True
            response['scan_domain'] = scan.domain
            response['scan_admin'] = scan.admin.userName
            response['scan_status'] = scan.status
            response['validation_steps'].append(f'SUCCESS: Scan found for domain {scan.domain}, admin {scan.admin.userName}')
        except ScanHistory.DoesNotExist:
            response['scan_exists'] = False
            response['validation_steps'].append('WARNING: Scan not found in database')

        # Now validate using the actual validation function
        response['validation_steps'].append('Running validate_access_token() function...')

        auth_wrapper, error = validate_access_token(access_token, scan_id)

        if error:
            response['validation_error'] = error
            response['validation_success'] = False
            response['validation_steps'].append(f'FAILED: {error}')
            return JsonResponse(response, status=401)
        else:
            response['validation_success'] = True
            response['auth_wrapper'] = {
                'domain': auth_wrapper.domain,
                'wp_path': auth_wrapper.wp_path,
                'auth_type': auth_wrapper.auth_type,
                'external_app': auth_wrapper.external_app
            }
            response['validation_steps'].append(f'SUCCESS: Token validated as {auth_wrapper.auth_type}')
            return JsonResponse(response)

    except Exception as e:
        logging.writeToFile(f'[API TEST] Error: {str(e)}')
        return JsonResponse({
            'error': str(e),
            'validation_steps': ['EXCEPTION: ' + str(e)]
        }, status=500)


@csrf_exempt
@require_http_methods(['GET'])
def list_api_keys(request):
    """
    Debug endpoint to list all API keys in the system

    Usage:
    curl http://localhost:8001/api/ai-scanner/list-api-keys/
    """
    try:
        api_keys = []
        for settings in AIScannerSettings.objects.all():
            api_keys.append({
                'admin': settings.admin.userName,
                'api_key_prefix': settings.api_key[:20] + '...' if settings.api_key else 'None',
                'balance': float(settings.balance),
                'is_payment_configured': settings.is_payment_configured
            })

        recent_scans = []
        for scan in ScanHistory.objects.all()[:5]:
            recent_scans.append({
                'scan_id': scan.scan_id,
                'domain': scan.domain,
                'admin': scan.admin.userName,
                'status': scan.status,
                'started_at': scan.started_at.isoformat() if scan.started_at else None
            })

        return JsonResponse({
            'api_keys': api_keys,
            'recent_scans': recent_scans
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)