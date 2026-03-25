import json
import os
import time
import mimetypes
import base64
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from websiteFunctions.models import Websites
from loginSystem.models import Administrator
from .models import FileAccessToken, ScanHistory
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


class SecurityError(Exception):
    """Custom exception for security violations"""
    pass


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


def validate_access_token(token, scan_id):
    """
    Validate authentication token - accepts BOTH file access tokens and API keys

    Authentication Flow:
    1. Try FileAccessToken (temporary token for active scans)
    2. If not found, try API Key (for post-scan file operations)

    Returns: (AuthWrapper object or None, error_message or None)
    """
    try:
        if not token or not token.startswith('cp_'):
            logging.writeToFile(f'[API] Invalid token format: {token[:20] if token else "None"}...')
            return None, "Invalid token format"

        # OPTION 1: Try FileAccessToken first (for active scans)
        try:
            file_token = FileAccessToken.objects.get(
                token=token,
                scan_history__scan_id=scan_id,
                is_active=True
            )

            if file_token.is_expired():
                logging.writeToFile(f'[API] File token expired for scan {scan_id}, trying API key fallback...')
                # Don't return here - fall through to try API key
            else:
                # Get externalApp from the website object
                from websiteFunctions.models import Websites
                try:
                    website = Websites.objects.get(domain=file_token.domain)
                    external_app = website.externalApp
                except Websites.DoesNotExist:
                    logging.writeToFile(f'[API] Website not found for domain: {file_token.domain}')
                    return None, "Website not found"

                logging.writeToFile(f'[API] File token validated successfully for scan {scan_id}, user {external_app}')
                return AuthWrapper(
                    domain=file_token.domain,
                    wp_path=file_token.wp_path,
                    auth_type='file_token',
                    external_app=external_app,
                    source_obj=file_token
                ), None

        except FileAccessToken.DoesNotExist:
            logging.writeToFile(f'[API] File token not found for scan {scan_id}, trying API key fallback...')
            # Fall through to try API key

        # OPTION 2: Try CyberPanel's own API Key (for post-scan file operations from platform)
        # The platform sends back the same API key that CyberPanel used to submit the scan
        try:
            from .models import AIScannerSettings, ScanHistory

            # Debug: log the token being checked
            logging.writeToFile(f'[API] Checking API key: {token[:20]}... for scan {scan_id}')

            # First, check if this is a valid CyberPanel API key (any admin's key)
            scanner_settings = AIScannerSettings.objects.filter(
                api_key=token
            ).first()

            if not scanner_settings:
                logging.writeToFile(f'[API] API key not found in settings')
                return None, "Invalid token"

            logging.writeToFile(f'[API] Found API key for admin: {scanner_settings.admin.userName}')

            # Get the scan - don't require it to belong to the same admin
            # (platform may be using any valid CyberPanel API key for file operations)
            try:
                scan = ScanHistory.objects.get(
                    scan_id=scan_id
                )

                # Get wp_path from WPSites (WordPress installations)
                try:
                    from websiteFunctions.models import WPSites

                    # Try to find WordPress site by domain
                    # FinalURL contains the full URL, so we use icontains to match domain
                    wp_site = WPSites.objects.filter(
                        FinalURL__icontains=scan.domain
                    ).first()

                    if not wp_site:
                        logging.writeToFile(f'[API] WordPress site not found for domain: {scan.domain}')
                        return None, "WordPress site not found"

                    wp_path = wp_site.path
                    external_app = wp_site.owner.externalApp  # Get externalApp from the website owner

                    # If no external app, try to get it from the website directly
                    if not external_app:
                        try:
                            from websiteFunctions.models import Websites
                            website = Websites.objects.get(domain=scan.domain)
                            external_app = website.externalApp
                        except Websites.DoesNotExist:
                            pass

                    # If still no external app, use the admin username as fallback
                    if not external_app:
                        external_app = scanner_settings.admin.userName
                        logging.writeToFile(f'[API] Warning: No externalApp for {scan.domain}, using admin username: {external_app}')

                    logging.writeToFile(f'[API] API key validated successfully for scan {scan_id}, domain {scan.domain}, path {wp_path}, user {external_app}')

                    return AuthWrapper(
                        domain=scan.domain,
                        wp_path=wp_path,
                        auth_type='api_key',
                        external_app=external_app,
                        source_obj=scanner_settings
                    ), None

                except Exception as e:
                    logging.writeToFile(f'[API] Error getting WordPress path for domain {scan.domain}: {str(e)}')
                    return None, "WordPress site not found"

            except ScanHistory.DoesNotExist:
                logging.writeToFile(f'[API] Scan {scan_id} not found')
                return None, "Scan not found"

        except Exception as e:
            logging.writeToFile(f'[API] API key validation error: {str(e)}')
            pass  # Fall through to OPTION 3

        # OPTION 3: Simple validation for platform callbacks
        # If we have a valid CyberPanel API key and a valid scan, allow access
        # This handles cases where the platform is using the API key to fix files
        try:
            from .models import AIScannerSettings, ScanHistory

            # Check if ANY admin has this API key (less restrictive for platform callbacks)
            has_valid_key = AIScannerSettings.objects.filter(api_key=token).exists()

            if has_valid_key:
                # Check if the scan exists (any admin's scan)
                try:
                    scan = ScanHistory.objects.get(scan_id=scan_id)

                    # Get WordPress site info
                    from websiteFunctions.models import WPSites, Websites
                    wp_site = WPSites.objects.filter(
                        FinalURL__icontains=scan.domain
                    ).first()

                    if wp_site:
                        # Get the external app (user) for this website
                        external_app = wp_site.owner.externalApp

                        # If no external app, try to get it from the website directly
                        if not external_app:
                            try:
                                website = Websites.objects.get(domain=scan.domain)
                                external_app = website.externalApp
                            except Websites.DoesNotExist:
                                pass

                        # If still no external app, use the admin username as fallback
                        if not external_app:
                            external_app = wp_site.owner.admin.userName
                            logging.writeToFile(f'[API] Warning: No externalApp for {scan.domain}, using admin username: {external_app}')

                        logging.writeToFile(f'[API] Platform callback validated: API key exists, scan {scan_id} found, user {external_app}')
                        return AuthWrapper(
                            domain=scan.domain,
                            wp_path=wp_site.path,
                            auth_type='api_key',
                            external_app=external_app,
                            source_obj=None
                        ), None
                    else:
                        logging.writeToFile(f'[API] WordPress site not found for scan {scan_id}')
                        return None, "WordPress site not found"

                except ScanHistory.DoesNotExist:
                    logging.writeToFile(f'[API] Scan {scan_id} not found in OPTION 3')
                    return None, "Scan not found"
            else:
                logging.writeToFile(f'[API] No valid API key found matching: {token[:20]}...')

        except Exception as e:
            logging.writeToFile(f'[API] OPTION 3 validation error: {str(e)}')
            pass  # Fall through to final error

    except Exception as e:
        logging.writeToFile(f'[API] Token validation error: {str(e)}')
        import traceback
        logging.writeToFile(f'[API] Traceback: {traceback.format_exc()}')
        return None, "Token validation failed"


def secure_path_check(base_path, requested_path):
    """
    Ensure requested path is within allowed directory
    Prevent directory traversal attacks
    """
    try:
        if requested_path:
            full_path = os.path.join(base_path, requested_path.strip('/'))
        else:
            full_path = base_path
            
        full_path = os.path.abspath(full_path)
        base_path = os.path.abspath(base_path)

        if not full_path.startswith(base_path):
            raise SecurityError("Path outside allowed directory")

        return full_path
    except Exception as e:
        raise SecurityError(f"Path security check failed: {str(e)}")


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
        worker_id = data.get('worker_id', 'unknown')
        
        logging.writeToFile(f'[API] Authentication request from worker {worker_id} for scan {scan_id}')
        
        if not access_token or not scan_id:
            return JsonResponse({'error': 'Missing access_token or scan_id'}, status=400)

        # Validate access token
        file_token, error = validate_access_token(access_token, scan_id)
        if error:
            return JsonResponse({'error': error}, status=401)
        
        # Get website info
        try:
            website = Websites.objects.get(domain=file_token.domain)
            
            # Get WordPress info
            wp_path = file_token.wp_path
            wp_version = 'Unknown'
            php_version = 'Unknown'
            
            # Try to get WP version from wp-includes/version.php using ProcessUtilities
            version_file = os.path.join(wp_path, 'wp-includes', 'version.php')
            try:
                from plogical.processUtilities import ProcessUtilities
                
                # Use ProcessUtilities to read file as the website user
                command = f'cat "{version_file}"'
                result = ProcessUtilities.outputExecutioner(command, user=website.externalApp, retRequired=True)
                
                if result[1]:  # Check if there's content (ignore return code)
                    content = result[1]
                    import re
                    match = re.search(r'\$wp_version\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                    if match:
                        wp_version = match.group(1)
                        logging.writeToFile(f'[API] Detected WordPress version: {wp_version}')
                else:
                    logging.writeToFile(f'[API] Could not read WP version file: {result[1] if len(result) > 1 else "No content returned"}')
                    
            except Exception as e:
                logging.writeToFile(f'[API] Error reading WP version: {str(e)}')
            
            # Try to detect PHP version (basic detection)
            try:
                import subprocess
                result = subprocess.run(['php', '-v'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    import re
                    match = re.search(r'PHP (\d+\.\d+)', result.stdout)
                    if match:
                        php_version = match.group(1)
            except Exception:
                pass
            
            response_data = {
                'success': True,
                'site_info': {
                    'domain': file_token.domain,
                    'wp_path': wp_path,
                    'php_version': php_version,
                    'wp_version': wp_version,
                    'scan_id': scan_id
                },
                'permissions': ['read_files', 'list_directories'],
                'expires_at': file_token.expires_at.strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            
            logging.writeToFile(f'[API] Authentication successful for {file_token.domain}')
            return JsonResponse(response_data)
            
        except Websites.DoesNotExist:
            logging.writeToFile(f'[API] Website not found: {file_token.domain}')
            return JsonResponse({'error': 'Website not found'}, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logging.writeToFile(f'[API] Authentication error: {str(e)}')
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
                "modified": "2024-12-20T10:30:00Z"
            },
            {
                "name": "suspicious-plugin.php",
                "type": "file",
                "size": 15420,
                "modified": "2024-12-24T15:20:00Z",
                "permissions": "644"
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
        
        try:
            # Security check and get full path
            full_path = secure_path_check(file_token.wp_path, path)
            
            # Path existence and type checking will be done by ProcessUtilities

            # List directory contents using ProcessUtilities
            items = []
            try:
                from plogical.processUtilities import ProcessUtilities
                from websiteFunctions.models import Websites
                
                # Get website object for user context
                try:
                    website = Websites.objects.get(domain=file_token.domain)
                    user = website.externalApp
                except Websites.DoesNotExist:
                    return JsonResponse({'error': 'Website not found'}, status=404)
                
                # Use ls command with ProcessUtilities to list directory as website user
                ls_command = f'ls -la "{full_path}"'
                result = ProcessUtilities.outputExecutioner(ls_command, user=user, retRequired=True)
                
                if result[1]:  # Check if there's content (ignore return code)
                    lines = result[1].strip().split('\n')
                    for line in lines[1:]:  # Skip the 'total' line
                        if not line.strip():
                            continue
                            
                        parts = line.split()
                        if len(parts) < 9:
                            continue
                            
                        permissions = parts[0]
                        size = parts[4] if parts[4].isdigit() else 0
                        name = ' '.join(parts[8:])  # Handle filenames with spaces
                        
                        # Skip hidden files, current/parent directory entries
                        if name.startswith('.') or name in ['.', '..'] or name in ['__pycache__', 'node_modules']:
                            continue
                        
                        item_data = {
                            'name': name,
                            'type': 'directory' if permissions.startswith('d') else 'file',
                            'permissions': permissions[1:4] if len(permissions) >= 4 else '644'
                        }
                        
                        if permissions.startswith('-'):  # Regular file
                            try:
                                item_data['size'] = int(size)
                            except ValueError:
                                item_data['size'] = 0
                                
                            # Only include certain file types
                            if name.endswith(('.php', '.js', '.html', '.htm', '.css', '.txt', '.md', '.json', '.xml', '.sql', '.log', '.conf', '.ini', '.yml', '.yaml')):
                                items.append(item_data)
                        elif permissions.startswith('d'):  # Directory
                            # Directories don't have a size in the same way
                            item_data['size'] = 0
                            items.append(item_data)
                        else:
                            # Other file types (links, etc.) - include with size 0
                            item_data['size'] = 0
                            items.append(item_data)
                else:
                    logging.writeToFile(f'[API] Directory listing failed: {result[1] if len(result) > 1 else "No content returned"}')
                    return JsonResponse({'error': 'Directory access failed'}, status=403)

            except Exception as e:
                logging.writeToFile(f'[API] Directory listing error: {str(e)}')
                return JsonResponse({'error': 'Directory access failed'}, status=403)

            logging.writeToFile(f'[API] Listed {len(items)} items in {path or "root"} for scan {scan_id}')
            
            return JsonResponse({
                'path': path,
                'items': sorted(items, key=lambda x: (x['type'] == 'file', x['name'].lower()))
            })
            
        except SecurityError as e:
            logging.writeToFile(f'[API] Security violation: {str(e)}')
            return JsonResponse({'error': 'Path not allowed'}, status=403)

    except Exception as e:
        logging.writeToFile(f'[API] List files error: {str(e)}')
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
        "content": "<?php\n// Plugin code here...",
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

        try:
            # Security check and get full path
            full_path = secure_path_check(file_token.wp_path, path)

            # File existence, type, and size checking will be done by ProcessUtilities

            # Only allow specific file types for security
            allowed_extensions = {
                '.php', '.js', '.html', '.htm', '.css', '.txt', '.md',
                '.json', '.xml', '.sql', '.log', '.conf', '.ini', '.yml', '.yaml'
            }

            file_ext = os.path.splitext(full_path)[1].lower()
            if file_ext not in allowed_extensions:
                return JsonResponse({'error': f'File type not allowed: {file_ext}'}, status=403)

            # Read file content using ProcessUtilities
            try:
                from plogical.processUtilities import ProcessUtilities
                from websiteFunctions.models import Websites
                
                # Get website object for user context
                try:
                    website = Websites.objects.get(domain=file_token.domain)
                    user = website.externalApp
                except Websites.DoesNotExist:
                    return JsonResponse({'error': 'Website not found'}, status=404)
                
                # Check file size first using stat command
                stat_command = f'stat -c %s "{full_path}"'
                stat_result = ProcessUtilities.outputExecutioner(stat_command, user=user, retRequired=True)
                
                if stat_result[1]:  # Check if there's content (ignore return code)
                    try:
                        file_size = int(stat_result[1].strip())
                        if file_size > 10 * 1024 * 1024:  # 10MB limit
                            return JsonResponse({'error': 'File too large (max 10MB)'}, status=400)
                    except ValueError:
                        logging.writeToFile(f'[API] Could not parse file size: {stat_result[1]}')
                        file_size = 0
                else:
                    logging.writeToFile(f'[API] Could not get file size: {stat_result[1] if len(stat_result) > 1 else "No content returned"}')
                    return JsonResponse({'error': 'File not found or inaccessible'}, status=404)
                
                # Use cat command with ProcessUtilities to read file as website user
                cat_command = f'cat "{full_path}"'
                result = ProcessUtilities.outputExecutioner(cat_command, user=user, retRequired=True)
                
                # Check if content was returned (file might be empty, which is valid)
                if len(result) > 1:  # We got a tuple back
                    content = result[1] if result[1] is not None else ''
                    encoding = 'utf-8'
                else:
                    logging.writeToFile(f'[API] File read failed: No result returned')
                    return JsonResponse({'error': 'Unable to read file'}, status=400)

            except Exception as e:
                logging.writeToFile(f'[API] File read error: {str(e)}')
                return JsonResponse({'error': 'Unable to read file'}, status=400)

            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(full_path)
            if not mime_type:
                if file_ext == '.php':
                    mime_type = 'text/x-php'
                elif file_ext == '.js':
                    mime_type = 'application/javascript'
                else:
                    mime_type = 'text/plain'

            # Base64 encode the content for safe transport
            try:
                content_base64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            except UnicodeEncodeError:
                # Handle binary files or encoding issues
                try:
                    content_base64 = base64.b64encode(content.encode('latin-1')).decode('utf-8')
                    encoding = 'latin-1'
                except:
                    logging.writeToFile(f'[API] Failed to encode file content for {path}')
                    return JsonResponse({'error': 'File encoding not supported'}, status=400)

            logging.writeToFile(f'[API] File content retrieved: {path} ({file_size} bytes) for scan {scan_id}')

            return JsonResponse({
                'path': path,
                'content': content_base64,
                'size': file_size,
                'encoding': encoding,
                'mime_type': mime_type
            })
            
        except SecurityError as e:
            logging.writeToFile(f'[API] Security violation: {str(e)}')
            return JsonResponse({'error': 'Path not allowed'}, status=403)

    except Exception as e:
        logging.writeToFile(f'[API] Get file content error: {str(e)}')
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def scan_callback(request):
    """
    Receive scan completion callbacks from AI Scanner platform

    POST /api/ai-scanner/callback
    Content-Type: application/json

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

        scan_id = data.get('scan_id')
        status = data.get('status')
        summary = data.get('summary', {})
        findings = data.get('findings', [])
        ai_analysis = data.get('ai_analysis', '')
        completed_at = data.get('completed_at')

        logging.writeToFile(f"[API] Received callback for scan {scan_id}: {status}")

        # Update scan status in CyberPanel database
        try:
            from .models import ScanHistory
            from django.utils import timezone
            import datetime

            # Find the scan record
            scan_record = ScanHistory.objects.get(scan_id=scan_id)

            # Update scan record
            scan_record.status = status
            scan_record.issues_found = summary.get('total_findings', 0)
            scan_record.files_scanned = summary.get('files_scanned', 0)

            # Parse and store cost
            cost_str = summary.get('cost', '$0.00')
            try:
                # Remove '$' and convert to float
                cost_value = float(cost_str.replace('$', '').replace(',', ''))
                scan_record.cost_usd = cost_value
            except (ValueError, AttributeError):
                scan_record.cost_usd = 0.0

            # Store findings and AI analysis
            scan_record.set_findings(findings)

            # Build summary dict
            summary_dict = {
                'threat_level': summary.get('threat_level', 'UNKNOWN'),
                'total_findings': summary.get('total_findings', 0),
                'files_scanned': summary.get('files_scanned', 0),
                'ai_analysis': ai_analysis
            }
            scan_record.set_summary(summary_dict)

            # Set completion time
            if completed_at:
                try:
                    # Parse ISO format datetime
                    completed_datetime = datetime.datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                    scan_record.completed_at = completed_datetime
                except ValueError:
                    scan_record.completed_at = timezone.now()
            else:
                scan_record.completed_at = timezone.now()

            scan_record.save()

            # Also update the ScanStatusUpdate record with final statistics
            try:
                from .status_models import ScanStatusUpdate
                status_update, _ = ScanStatusUpdate.objects.get_or_create(scan_id=scan_id)
                status_update.phase = 'completed'
                status_update.progress = 100
                status_update.files_discovered = summary.get('files_scanned', 0)  # Use files_scanned as approximation
                status_update.files_scanned = summary.get('files_scanned', 0)
                status_update.files_remaining = 0
                status_update.threats_found = summary.get('total_findings', 0)
                # Extract critical and high threats from findings if available
                critical_count = 0
                high_count = 0
                for finding in findings:
                    severity = finding.get('severity', '').lower()
                    if severity == 'critical':
                        critical_count += 1
                    elif severity == 'high':
                        high_count += 1
                status_update.critical_threats = critical_count
                status_update.high_threats = high_count
                status_update.activity_description = f"Scan completed - {summary.get('total_findings', 0)} threats found"
                status_update.save()
                logging.writeToFile(f"[API] Updated ScanStatusUpdate for completed scan {scan_id}")
            except Exception as e:
                logging.writeToFile(f"[API] Error updating ScanStatusUpdate: {str(e)}")

            # Update user balance if scan cost money
            if scan_record.cost_usd > 0:
                try:
                    scanner_settings = scan_record.admin.ai_scanner_settings
                    if scanner_settings.balance >= scan_record.cost_usd:
                        # Convert to same type to avoid Decimal/float issues
                        scanner_settings.balance = float(scanner_settings.balance) - float(scan_record.cost_usd)
                        scanner_settings.save()
                        logging.writeToFile(f"[API] Deducted ${scan_record.cost_usd} from {scan_record.admin.userName} balance")
                    else:
                        logging.writeToFile(f"[API] Insufficient balance for scan cost: ${scan_record.cost_usd}")
                except Exception as e:
                    logging.writeToFile(f"[API] Error updating balance: {str(e)}")

            # Deactivate file access tokens for this scan
            try:
                from .models import FileAccessToken
                FileAccessToken.objects.filter(scan_history=scan_record).update(is_active=False)
                logging.writeToFile(f"[API] Deactivated file access tokens for scan {scan_id}")
            except Exception as e:
                logging.writeToFile(f"[API] Error deactivating tokens: {str(e)}")

            logging.writeToFile(f"[API] Scan {scan_id} completed successfully:")
            logging.writeToFile(f"[API]   Status: {status}")
            logging.writeToFile(f"[API]   Threat Level: {summary.get('threat_level')}")
            logging.writeToFile(f"[API]   Findings: {summary.get('total_findings')}")
            logging.writeToFile(f"[API]   Files Scanned: {summary.get('files_scanned')}")
            logging.writeToFile(f"[API]   Cost: {summary.get('cost')}")

        except ScanHistory.DoesNotExist:
            logging.writeToFile(f"[API] Scan record not found: {scan_id}")
            return JsonResponse({
                'status': 'error',
                'message': 'Scan record not found',
                'scan_id': scan_id
            }, status=404)

        except Exception as e:
            logging.writeToFile(f"[API] Failed to update scan record: {str(e)}")
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
        logging.writeToFile(f"[API] Callback processing error: {str(e)}")
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


def check_rate_limit(scan_id, endpoint, max_requests):
    """
    Check if rate limit is exceeded for a scan/endpoint combination
    Returns (is_allowed, current_count)
    """
    try:
        from .models import ScannerAPIRateLimit

        rate_limit, created = ScannerAPIRateLimit.objects.get_or_create(
            scan_id=scan_id,
            endpoint=endpoint,
            defaults={'request_count': 0}
        )

        if rate_limit.request_count >= max_requests:
            logging.writeToFile(f'[API] Rate limit exceeded for scan {scan_id} on endpoint {endpoint}: {rate_limit.request_count}/{max_requests}')
            return False, rate_limit.request_count

        rate_limit.request_count += 1
        rate_limit.save()

        return True, rate_limit.request_count
    except Exception as e:
        logging.writeToFile(f'[API] Rate limit check error: {str(e)}')
        # On error, allow the request
        return True, 0


def get_website_user(domain):
    """
    Get the system user for a website domain
    """
    try:
        website = Websites.objects.get(domain=domain)
        return website.externalApp
    except Websites.DoesNotExist:
        raise SecurityError(f"Website not found: {domain}")


# =============================================================================
# File Operation API Endpoints
# =============================================================================

@csrf_exempt
@require_http_methods(['POST'])
def scanner_backup_file(request):
    """
    POST /api/scanner/backup-file

    Create a backup copy of a file before modification

    Headers:
        Authorization: Bearer {file_access_token}
        X-Scan-ID: {scan_job_id}

    Request Body:
        {
            "file_path": "wp-content/plugins/example/plugin.php",
            "scan_id": "550e8400-e29b-41d4-a716-446655440000"
        }

    Response:
        {
            "success": true,
            "backup_path": "/home/username/public_html/.ai-scanner-backups/2025-10-25/plugin.php.1730000000.bak",
            "original_path": "wp-content/plugins/example/plugin.php",
            "backup_size": 15420,
            "timestamp": "2025-10-25T20:30:00Z"
        }
    """
    try:
        # Parse request
        data = json.loads(request.body)
        file_path = data.get('file_path', '').strip('/')
        scan_id = data.get('scan_id', '')

        # Validate authorization (supports both Bearer token and X-API-Key)
        access_token, auth_type = extract_auth_token(request)
        if not access_token:
            return JsonResponse({'success': False, 'error': 'Missing or invalid Authorization header. Use Bearer token or X-API-Key header'}, status=401)

        header_scan_id = request.META.get('HTTP_X_SCAN_ID', '')

        if not scan_id or not header_scan_id or scan_id != header_scan_id:
            return JsonResponse({'success': False, 'error': 'Scan ID mismatch'}, status=400)

        # Validate access token
        file_token, error = validate_access_token(access_token, scan_id)
        if error:
            log_file_operation(scan_id, 'backup', file_path, False, error, request=request)
            return JsonResponse({'success': False, 'error': error}, status=401)

        # Rate limiting - higher limits for API key authenticated requests (platform operations)
        max_backups = 1000 if file_token.auth_type == 'api_key' else 100
        is_allowed, count = check_rate_limit(scan_id, 'backup-file', max_backups)
        if not is_allowed:
            return JsonResponse({'success': False, 'error': f'Rate limit exceeded (max {max_backups} backups per scan)'}, status=429)

        # Security check and get full path
        try:
            full_path = secure_path_check(file_token.wp_path, file_path)
        except SecurityError as e:
            log_file_operation(scan_id, 'backup', file_path, False, str(e), request=request)
            return JsonResponse({'success': False, 'error': 'Path not allowed'}, status=403)

        # Get website user from auth wrapper (already validated during authentication)
        user = file_token.external_app
        if not user:
            error_msg = f'External app (user) not available in auth context for domain {file_token.domain}'
            logging.writeToFile(f'[API] Backup error: {error_msg}, auth_type={file_token.auth_type}')
            log_file_operation(scan_id, 'backup', file_path, False, error_msg, request=request)
            return JsonResponse({'success': False, 'error': error_msg, 'error_code': 'NO_USER'}, status=500)

        # Check file exists
        from plogical.processUtilities import ProcessUtilities

        check_cmd = f'test -f "{full_path}" && echo "exists"'
        result = ProcessUtilities.outputExecutioner(check_cmd, user=user, retRequired=True)

        if not result[1] or 'exists' not in result[1]:
            log_file_operation(scan_id, 'backup', file_path, False, 'File not found', request=request)
            return JsonResponse({'success': False, 'error': 'File not found', 'error_code': 'FILE_NOT_FOUND'}, status=404)

        # Create backup directory
        import datetime
        # Remove trailing slash from wp_path to avoid double slashes
        wp_path_clean = file_token.wp_path.rstrip('/')
        backup_dir_name = f'{wp_path_clean}/.ai-scanner-backups/{datetime.datetime.now().strftime("%Y-%m-%d")}'

        logging.writeToFile(f'[API] Creating backup directory: {backup_dir_name}')
        mkdir_cmd = f'mkdir -p "{backup_dir_name}"'
        mkdir_result = ProcessUtilities.executioner(mkdir_cmd, user=user)

        # executioner returns 1 for success, 0 for failure
        if mkdir_result != 1:
            error_msg = f'Failed to create backup directory: {backup_dir_name}'
            logging.writeToFile(f'[API] {error_msg}, mkdir_result={mkdir_result}')
            log_file_operation(scan_id, 'backup', file_path, False, error_msg, request=request)
            return JsonResponse({'success': False, 'error': error_msg, 'error_code': 'BACKUP_DIR_FAILED'}, status=500)

        # Create backup filename with timestamp
        timestamp = int(time.time())
        basename = os.path.basename(full_path)
        backup_filename = f'{basename}.{timestamp}.bak'
        backup_path = os.path.join(backup_dir_name, backup_filename)

        logging.writeToFile(f'[API] Backing up {full_path} to {backup_path}')

        # Copy file to backup
        cp_cmd = f'cp "{full_path}" "{backup_path}"'
        cp_result = ProcessUtilities.outputExecutioner(cp_cmd, user=user, retRequired=True)

        # outputExecutioner returns (1, output) for success, (0, output) for failure
        # Also check output for error messages as additional safety
        if cp_result[0] != 1 or (cp_result[1] and 'error' in cp_result[1].lower()):
            error_output = cp_result[1] if len(cp_result) > 1 else 'Unknown error'
            error_msg = f'Failed to create backup: {error_output}'
            logging.writeToFile(f'[API] Backup failed: cp returned {cp_result[0]}, output: {error_output}')
            log_file_operation(scan_id, 'backup', file_path, False, error_msg, request=request)
            return JsonResponse({'success': False, 'error': error_msg, 'error_code': 'BACKUP_FAILED'}, status=500)

        # Get file size
        stat_cmd = f'stat -c %s "{backup_path}"'
        stat_result = ProcessUtilities.outputExecutioner(stat_cmd, user=user, retRequired=True)

        backup_size = 0
        if stat_result[1]:
            try:
                backup_size = int(stat_result[1].strip())
            except ValueError:
                pass

        # Log success
        log_file_operation(scan_id, 'backup', file_path, True, backup_path=backup_path, request=request)

        logging.writeToFile(f'[API] Backup created for {file_path}: {backup_path}')

        return JsonResponse({
            'success': True,
            'backup_path': backup_path,
            'original_path': file_path,
            'backup_size': backup_size,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logging.writeToFile(f'[API] Backup file error: {str(e)}')
        log_file_operation(scan_id if 'scan_id' in locals() else 'unknown', 'backup',
                          file_path if 'file_path' in locals() else 'unknown', False, str(e), request=request)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)@csrf_exempt
@require_http_methods(['GET'])
def scanner_get_file(request):
    """
    GET /api/scanner/get-file?file_path=wp-content/plugins/plugin.php

    Read the contents of a file for analysis or verification

    Headers:
        Authorization: Bearer {file_access_token}
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
    try:
        # Validate authorization (supports both Bearer token and X-API-Key)
        access_token, auth_type = extract_auth_token(request)
        if not access_token:
            return JsonResponse({'success': False, 'error': 'Missing or invalid Authorization header. Use Bearer token or X-API-Key header'}, status=401)

        scan_id = request.META.get('HTTP_X_SCAN_ID', '')

        if not scan_id:
            return JsonResponse({'success': False, 'error': 'X-Scan-ID header required'}, status=400)

        # Get file path
        file_path = request.GET.get('file_path', '').strip('/')
        if not file_path:
            return JsonResponse({'success': False, 'error': 'File path required'}, status=400)

        # Validate access token
        file_token, error = validate_access_token(access_token, scan_id)
        if error:
            log_file_operation(scan_id, 'read', file_path, False, error, request=request)
            return JsonResponse({'success': False, 'error': error}, status=401)

        # Rate limiting - higher limits for API key authenticated requests (platform operations)
        max_reads = 5000 if file_token.auth_type == 'api_key' else 500
        is_allowed, count = check_rate_limit(scan_id, 'get-file', max_reads)
        if not is_allowed:
            return JsonResponse({'success': False, 'error': f'Rate limit exceeded (max {max_reads} file reads per scan)'}, status=429)

        # Security check and get full path
        try:
            full_path = secure_path_check(file_token.wp_path, file_path)
        except SecurityError as e:
            log_file_operation(scan_id, 'read', file_path, False, str(e), request=request)
            return JsonResponse({'success': False, 'error': 'Path not allowed'}, status=403)

        # Only allow specific file types for security
        allowed_extensions = {
            '.php', '.js', '.html', '.htm', '.css', '.txt', '.md',
            '.json', '.xml', '.sql', '.log', '.conf', '.ini', '.yml', '.yaml'
        }

        file_ext = os.path.splitext(full_path)[1].lower()
        if file_ext not in allowed_extensions:
            log_file_operation(scan_id, 'read', file_path, False, f'File type not allowed: {file_ext}', request=request)
            return JsonResponse({'success': False, 'error': f'File type not allowed: {file_ext}'}, status=403)

        # Get website user from auth wrapper (already validated during authentication)
        user = file_token.external_app
        if not user:
            error_msg = 'External app not available in auth context'
            log_file_operation(scan_id, 'read', file_path, False, error_msg, request=request)
            return JsonResponse({'success': False, 'error': error_msg}, status=500)

        # Check file size
        from plogical.processUtilities import ProcessUtilities
        import hashlib

        stat_cmd = f'stat -c "%s %Y" "{full_path}"'
        stat_result = ProcessUtilities.outputExecutioner(stat_cmd, user=user, retRequired=True)

        if not stat_result[1]:
            log_file_operation(scan_id, 'read', file_path, False, 'File not found', request=request)
            return JsonResponse({'success': False, 'error': 'File not found', 'error_code': 'FILE_NOT_FOUND'}, status=404)

        try:
            parts = stat_result[1].strip().split()
            file_size = int(parts[0])
            last_modified_timestamp = int(parts[1])

            if file_size > 10 * 1024 * 1024:  # 10MB limit
                log_file_operation(scan_id, 'read', file_path, False, 'File too large (max 10MB)', request=request)
                return JsonResponse({'success': False, 'error': 'File too large (max 10MB)'}, status=400)
        except (ValueError, IndexError):
            log_file_operation(scan_id, 'read', file_path, False, 'Could not get file size', request=request)
            return JsonResponse({'success': False, 'error': 'Could not get file size'}, status=500)

        # Read file content
        cat_cmd = f'cat "{full_path}"'
        result = ProcessUtilities.outputExecutioner(cat_cmd, user=user, retRequired=True)

        if len(result) < 2:
            log_file_operation(scan_id, 'read', file_path, False, 'Unable to read file', request=request)
            return JsonResponse({'success': False, 'error': 'Unable to read file'}, status=400)

        content = result[1] if result[1] is not None else ''

        # Calculate hashes
        try:
            content_bytes = content.encode('utf-8')
            md5_hash = hashlib.md5(content_bytes).hexdigest()
            sha256_hash = hashlib.sha256(content_bytes).hexdigest()
        except UnicodeEncodeError:
            try:
                content_bytes = content.encode('latin-1')
                md5_hash = hashlib.md5(content_bytes).hexdigest()
                sha256_hash = hashlib.sha256(content_bytes).hexdigest()
            except:
                md5_hash = ''
                sha256_hash = ''

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(full_path)
        if not mime_type:
            if file_ext == '.php':
                mime_type = 'text/x-php'
            elif file_ext == '.js':
                mime_type = 'application/javascript'
            else:
                mime_type = 'text/plain'

        # Format last modified time
        import datetime
        last_modified = datetime.datetime.fromtimestamp(last_modified_timestamp).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Log success
        log_file_operation(scan_id, 'read', file_path, True, request=request)

        logging.writeToFile(f'[API] File content retrieved: {file_path} ({file_size} bytes)')

        return JsonResponse({
            'success': True,
            'file_path': file_path,
            'content': content,
            'size': file_size,
            'encoding': 'utf-8',
            'mime_type': mime_type,
            'last_modified': last_modified,
            'hash': {
                'md5': md5_hash,
                'sha256': sha256_hash
            }
        })

    except Exception as e:
        logging.writeToFile(f'[API] Get file error: {str(e)}')
        log_file_operation(scan_id if 'scan_id' in locals() else 'unknown', 'read',
                          file_path if 'file_path' in locals() else 'unknown', False, str(e), request=request)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def scanner_replace_file(request):
    """
    POST /api/scanner/replace-file

    Overwrite a file with new content (after backup)

    Headers:
        Authorization: Bearer {file_access_token}
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
            "backup_path": "/home/username/public_html/.ai-scanner-backups/2025-10-25/plugin.php.1730000000.bak",
            "bytes_written": 14850,
            "new_hash": {
                "md5": "abc123...",
                "sha256": "def456..."
            },
            "timestamp": "2025-10-25T20:35:00Z"
        }
    """
    try:
        # Parse request
        data = json.loads(request.body)
        file_path = data.get('file_path', '').strip('/')
        content = data.get('content', '')
        backup_before_replace = data.get('backup_before_replace', True)
        verify_hash = data.get('verify_hash', '')

        # Validate authorization (supports both Bearer token and X-API-Key)
        access_token, auth_type = extract_auth_token(request)
        if not access_token:
            return JsonResponse({'success': False, 'error': 'Missing or invalid Authorization header. Use Bearer token or X-API-Key header'}, status=401)

        scan_id = request.META.get('HTTP_X_SCAN_ID', '')

        if not scan_id:
            return JsonResponse({'success': False, 'error': 'X-Scan-ID header required'}, status=400)

        # Validate access token
        file_token, error = validate_access_token(access_token, scan_id)
        if error:
            log_file_operation(scan_id, 'replace', file_path, False, error, request=request)
            return JsonResponse({'success': False, 'error': error}, status=401)

        # Rate limiting - higher limits for API key authenticated requests (platform operations)
        max_replacements = 1000 if file_token.auth_type == 'api_key' else 100
        is_allowed, count = check_rate_limit(scan_id, 'replace-file', max_replacements)
        if not is_allowed:
            return JsonResponse({'success': False, 'error': f'Rate limit exceeded (max {max_replacements} replacements per scan)'}, status=429)

        # Security check and get full path
        try:
            full_path = secure_path_check(file_token.wp_path, file_path)
        except SecurityError as e:
            log_file_operation(scan_id, 'replace', file_path, False, str(e), request=request)
            return JsonResponse({'success': False, 'error': 'Path not allowed'}, status=403)

        # Get website user from auth wrapper (already validated during authentication)
        user = file_token.external_app
        if not user:
            error_msg = f'External app (user) not available in auth context for domain {file_token.domain}'
            logging.writeToFile(f'[API] Replace error: {error_msg}, auth_type={file_token.auth_type}')
            log_file_operation(scan_id, 'replace', file_path, False, error_msg, request=request)
            return JsonResponse({'success': False, 'error': error_msg, 'error_code': 'NO_USER'}, status=500)

        # Verify hash if provided
        from plogical.processUtilities import ProcessUtilities
        import hashlib
        import datetime

        if verify_hash:
            cat_cmd = f'cat "{full_path}"'
            result = ProcessUtilities.outputExecutioner(cat_cmd, user=user, retRequired=True)

            if result[1]:
                current_hash = hashlib.sha256(result[1].encode('utf-8')).hexdigest()
                if current_hash != verify_hash:
                    log_file_operation(scan_id, 'replace', file_path, False, 'Hash verification failed - file was modified', request=request)
                    return JsonResponse({
                        'success': False,
                        'error': 'Hash verification failed - file was modified during scan',
                        'error_code': 'HASH_MISMATCH',
                        'expected_hash': verify_hash,
                        'actual_hash': current_hash
                    }, status=400)

        backup_path = None

        # Create backup if requested
        if backup_before_replace:
            wp_path_clean = file_token.wp_path.rstrip('/')
            backup_dir_name = f'{wp_path_clean}/.ai-scanner-backups/{datetime.datetime.now().strftime("%Y-%m-%d")}'
            mkdir_cmd = f'mkdir -p "{backup_dir_name}"'

            logging.writeToFile(f'[API] Creating backup dir with user {user}: {backup_dir_name}')
            mkdir_result = ProcessUtilities.executioner(mkdir_cmd, user=user)

            # Check if directory creation failed
            if mkdir_result != 1:
                error_msg = f'Failed to create backup directory: {backup_dir_name} for user {user}'
                logging.writeToFile(f'[API] {error_msg}, mkdir_result={mkdir_result}')
                log_file_operation(scan_id, 'replace', file_path, False, error_msg, request=request)
                return JsonResponse({'success': False, 'error': 'Failed to create backup directory', 'error_code': 'BACKUP_DIR_FAILED', 'details': error_msg}, status=500)

            timestamp = int(time.time())
            basename = os.path.basename(full_path)
            backup_filename = f'{basename}.{timestamp}.bak'
            backup_path = os.path.join(backup_dir_name, backup_filename)

            cp_cmd = f'cp "{full_path}" "{backup_path}"'
            cp_result = ProcessUtilities.executioner(cp_cmd, user=user)

            # executioner returns 1 for success, 0 for failure
            if cp_result != 1:
                error_msg = f'Failed to create backup: cp command failed for user {user}'
                logging.writeToFile(f'[API] {error_msg}, cp_result={cp_result}, backup_path={backup_path}')
                log_file_operation(scan_id, 'replace', file_path, False, error_msg, backup_path=backup_path, request=request)
                return JsonResponse({'success': False, 'error': 'Failed to backup file before replacement', 'error_code': 'BACKUP_FAILED', 'details': error_msg}, status=500)

        # Write new content to temp file first (atomic write)
        # Write to /tmp (accessible by all users, no permission issues)
        tmp_file = f'/tmp/scanner_temp_{scan_id}_{int(time.time())}.tmp'

        try:
            # Write content directly to /tmp directory
            with open(tmp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logging.writeToFile(f'[API] Wrote {len(content)} bytes to {tmp_file}')
        except Exception as e:
            error_msg = f'Failed to write temp file: {str(e)}'
            logging.writeToFile(f'[API] {error_msg}')
            log_file_operation(scan_id, 'replace', file_path, False, error_msg, backup_path=backup_path, request=request)
            return JsonResponse({'success': False, 'error': 'Failed to write file', 'error_code': 'WRITE_FAILED'}, status=500)

        # Get original file permissions
        stat_cmd = f'stat -c %a "{full_path}"'
        stat_result = ProcessUtilities.outputExecutioner(stat_cmd, user=user, retRequired=True)
        permissions = '644'  # Default
        if stat_result[1]:
            permissions = stat_result[1].strip()

        # Set permissions on temp file
        chmod_cmd = f'chmod {permissions} "{tmp_file}"'
        ProcessUtilities.executioner(chmod_cmd)

        # Verify temp file has content before replacing
        check_cmd = f'wc -c "{tmp_file}"'
        check_result = ProcessUtilities.outputExecutioner(check_cmd, retRequired=True)
        logging.writeToFile(f'[API] Temp file size check: {check_result}')

        # Replace file using cat redirection (more reliable than cp for overwriting)
        # This ensures the file contents are actually replaced
        replace_cmd = f'cat "{tmp_file}" > "{full_path}"'
        logging.writeToFile(f'[API] Executing replace command: {replace_cmd}')
        replace_result = ProcessUtilities.executioner(replace_cmd, user=user, shell=True)
        logging.writeToFile(f'[API] Replace command result: {replace_result}')

        # Clean up temp file
        try:
            os.remove(tmp_file)
        except:
            pass

        # executioner returns 1 for success, 0 for failure
        if replace_result != 1:
            error_msg = 'Failed to replace file contents'
            logging.writeToFile(f'[API] {error_msg}, replace_result={replace_result}')
            log_file_operation(scan_id, 'replace', file_path, False, error_msg, backup_path=backup_path, request=request)
            return JsonResponse({'success': False, 'error': 'Failed to replace file', 'error_code': 'REPLACE_FAILED'}, status=500)

        logging.writeToFile(f'[API] Successfully replaced {full_path} with new content')

        # Calculate new hash
        cat_cmd = f'cat "{full_path}"'
        result = ProcessUtilities.outputExecutioner(cat_cmd, user=user, retRequired=True)

        new_md5 = ''
        new_sha256 = ''
        if result[1]:
            try:
                content_bytes = result[1].encode('utf-8')
                new_md5 = hashlib.md5(content_bytes).hexdigest()
                new_sha256 = hashlib.sha256(content_bytes).hexdigest()
            except:
                pass

        bytes_written = len(content.encode('utf-8'))

        # Log success
        log_file_operation(scan_id, 'replace', file_path, True, backup_path=backup_path, request=request)

        logging.writeToFile(f'[API] File replaced: {file_path} ({bytes_written} bytes)')

        return JsonResponse({
            'success': True,
            'file_path': file_path,
            'backup_path': backup_path,
            'bytes_written': bytes_written,
            'new_hash': {
                'md5': new_md5,
                'sha256': new_sha256
            },
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logging.writeToFile(f'[API] Replace file error: {str(e)}')
        log_file_operation(scan_id if 'scan_id' in locals() else 'unknown', 'replace',
                          file_path if 'file_path' in locals() else 'unknown', False, str(e), request=request)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def scanner_rename_file(request):
    """
    POST /api/scanner/rename-file

    Rename a file (used for quarantining malicious files)

    Headers:
        Authorization: Bearer {file_access_token}
        X-Scan-ID: {scan_job_id}

    Request Body:
        {
            "old_path": "wp-content/uploads/malicious.php",
            "new_path": "wp-content/uploads/malicious.php.quarantined.1730000000",
            "backup_before_rename": true
        }

    Response:
        {
            "success": true,
            "old_path": "wp-content/uploads/malicious.php",
            "new_path": "wp-content/uploads/malicious.php.quarantined.1730000000",
            "backup_path": "/home/username/public_html/.ai-scanner-backups/2025-10-25/malicious.php.1730000000.bak",
            "timestamp": "2025-10-25T20:40:00Z"
        }
    """
    try:
        # Parse request
        data = json.loads(request.body)
        old_path = data.get('old_path', '').strip('/')
        new_path = data.get('new_path', '').strip('/')
        backup_before_rename = data.get('backup_before_rename', True)

        # Validate authorization (supports both Bearer token and X-API-Key)
        access_token, auth_type = extract_auth_token(request)
        if not access_token:
            return JsonResponse({'success': False, 'error': 'Missing or invalid Authorization header. Use Bearer token or X-API-Key header'}, status=401)

        scan_id = request.META.get('HTTP_X_SCAN_ID', '')

        if not scan_id:
            return JsonResponse({'success': False, 'error': 'X-Scan-ID header required'}, status=400)

        # Validate access token
        file_token, error = validate_access_token(access_token, scan_id)
        if error:
            log_file_operation(scan_id, 'rename', old_path, False, error, request=request)
            return JsonResponse({'success': False, 'error': error}, status=401)

        # Rate limiting - higher limits for API key authenticated requests (platform operations)
        max_renames = 500 if file_token.auth_type == 'api_key' else 50
        is_allowed, count = check_rate_limit(scan_id, 'rename-file', max_renames)
        if not is_allowed:
            return JsonResponse({'success': False, 'error': f'Rate limit exceeded (max {max_renames} renames per scan)'}, status=429)

        # Security check for both paths
        try:
            full_old_path = secure_path_check(file_token.wp_path, old_path)
            full_new_path = secure_path_check(file_token.wp_path, new_path)
        except SecurityError as e:
            log_file_operation(scan_id, 'rename', old_path, False, str(e), request=request)
            return JsonResponse({'success': False, 'error': 'Path not allowed'}, status=403)

        # Get website user from auth wrapper (already validated during authentication)
        user = file_token.external_app
        if not user:
            error_msg = 'External app not available in auth context'
            log_file_operation(scan_id, 'rename', old_path, False, error_msg, request=request)
            return JsonResponse({'success': False, 'error': error_msg}, status=500)

        # Check source file exists
        from plogical.processUtilities import ProcessUtilities
        import datetime

        check_cmd = f'test -f "{full_old_path}" && echo "exists"'
        result = ProcessUtilities.outputExecutioner(check_cmd, user=user, retRequired=True)

        if not result[1] or 'exists' not in result[1]:
            log_file_operation(scan_id, 'rename', old_path, False, 'Source file not found', request=request)
            return JsonResponse({'success': False, 'error': 'Source file not found', 'error_code': 'FILE_NOT_FOUND'}, status=404)

        # Check destination doesn't exist
        check_cmd = f'test -f "{full_new_path}" && echo "exists"'
        result = ProcessUtilities.outputExecutioner(check_cmd, user=user, retRequired=True)

        if result[1] and 'exists' in result[1]:
            log_file_operation(scan_id, 'rename', old_path, False, 'Destination file already exists', request=request)
            return JsonResponse({'success': False, 'error': 'Destination file already exists', 'error_code': 'FILE_EXISTS'}, status=409)

        backup_path = None

        # Create backup if requested
        if backup_before_rename:
            wp_path_clean = file_token.wp_path.rstrip('/')
            backup_dir_name = f'{wp_path_clean}/.ai-scanner-backups/{datetime.datetime.now().strftime("%Y-%m-%d")}'
            mkdir_cmd = f'mkdir -p "{backup_dir_name}"'
            mkdir_result = ProcessUtilities.executioner(mkdir_cmd, user=user)

            # executioner returns 1 for success, 0 for failure
            if mkdir_result != 1:
                error_msg = f'Failed to create backup directory: {backup_dir_name}'
                logging.writeToFile(f'[API] {error_msg}')
                log_file_operation(scan_id, 'rename', old_path, False, error_msg, request=request)
                return JsonResponse({'success': False, 'error': 'Failed to create backup directory', 'error_code': 'BACKUP_DIR_FAILED'}, status=500)

            timestamp = int(time.time())
            basename = os.path.basename(full_old_path)
            backup_filename = f'{basename}.{timestamp}.bak'
            backup_path = os.path.join(backup_dir_name, backup_filename)

            cp_cmd = f'cp "{full_old_path}" "{backup_path}"'
            cp_result = ProcessUtilities.executioner(cp_cmd, user=user)

            # executioner returns 1 for success, 0 for failure
            if cp_result != 1:
                error_msg = f'Failed to backup file before rename'
                logging.writeToFile(f'[API] {error_msg}, cp_result={cp_result}')
                log_file_operation(scan_id, 'rename', old_path, False, error_msg, request=request)
                return JsonResponse({'success': False, 'error': 'Failed to backup file before quarantine', 'error_code': 'BACKUP_FAILED'}, status=500)

        # Perform rename
        mv_cmd = f'mv "{full_old_path}" "{full_new_path}"'
        mv_result = ProcessUtilities.executioner(mv_cmd, user=user)

        # executioner returns 1 for success, 0 for failure
        if mv_result != 1:
            log_file_operation(scan_id, 'rename', old_path, False, 'Failed to rename file', backup_path=backup_path, request=request)
            return JsonResponse({'success': False, 'error': 'Failed to rename file', 'error_code': 'RENAME_FAILED'}, status=500)

        # Verify rename
        check_cmd = f'test -f "{full_new_path}" && echo "exists"'
        result = ProcessUtilities.outputExecutioner(check_cmd, user=user, retRequired=True)

        if not result[1] or 'exists' not in result[1]:
            log_file_operation(scan_id, 'rename', old_path, False, 'Rename verification failed', backup_path=backup_path, request=request)
            return JsonResponse({'success': False, 'error': 'Rename verification failed'}, status=500)

        # Log success
        log_file_operation(scan_id, 'rename', old_path, True, backup_path=backup_path, request=request)

        logging.writeToFile(f'[API] File renamed: {old_path} -> {new_path}')

        return JsonResponse({
            'success': True,
            'old_path': old_path,
            'new_path': new_path,
            'backup_path': backup_path,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logging.writeToFile(f'[API] Rename file error: {str(e)}')
        log_file_operation(scan_id if 'scan_id' in locals() else 'unknown', 'rename',
                          old_path if 'old_path' in locals() else 'unknown', False, str(e), request=request)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def scanner_delete_file(request):
    """
    POST /api/scanner/delete-file

    Permanently delete a malicious file (after backup)

    Headers:
        Authorization: Bearer {file_access_token}
        X-Scan-ID: {scan_job_id}

    Request Body:
        {
            "file_path": "wp-content/uploads/shell.php",
            "backup_before_delete": true,
            "confirm_deletion": true
        }

    Response:
        {
            "success": true,
            "file_path": "wp-content/uploads/shell.php",
            "backup_path": "/home/username/public_html/.ai-scanner-backups/2025-10-25/shell.php.1730000000.bak",
            "deleted_at": "2025-10-25T20:45:00Z",
            "file_info": {
                "size": 2048,
                "last_modified": "2025-10-20T14:30:00Z",
                "hash": "abc123..."
            }
        }
    """
    try:
        # Parse request
        data = json.loads(request.body)
        file_path = data.get('file_path', '').strip('/')
        backup_before_delete = data.get('backup_before_delete', True)
        confirm_deletion = data.get('confirm_deletion', False)

        # Require explicit confirmation
        if not confirm_deletion:
            return JsonResponse({
                'success': False,
                'error': 'Deletion not confirmed',
                'error_code': 'CONFIRMATION_REQUIRED',
                'message': 'Set confirm_deletion: true to proceed'
            }, status=400)

        # Validate authorization (supports both Bearer token and X-API-Key)
        access_token, auth_type = extract_auth_token(request)
        if not access_token:
            return JsonResponse({'success': False, 'error': 'Missing or invalid Authorization header. Use Bearer token or X-API-Key header'}, status=401)

        scan_id = request.META.get('HTTP_X_SCAN_ID', '')

        if not scan_id:
            return JsonResponse({'success': False, 'error': 'X-Scan-ID header required'}, status=400)

        # Validate access token
        file_token, error = validate_access_token(access_token, scan_id)
        if error:
            log_file_operation(scan_id, 'delete', file_path, False, error, request=request)
            return JsonResponse({'success': False, 'error': error}, status=401)

        # Rate limiting - higher limits for API key authenticated requests (platform operations)
        max_deletions = 500 if file_token.auth_type == 'api_key' else 50
        is_allowed, count = check_rate_limit(scan_id, 'delete-file', max_deletions)
        if not is_allowed:
            return JsonResponse({'success': False, 'error': f'Rate limit exceeded (max {max_deletions} deletions per scan)'}, status=429)

        # Security check and get full path
        try:
            full_path = secure_path_check(file_token.wp_path, file_path)
        except SecurityError as e:
            log_file_operation(scan_id, 'delete', file_path, False, str(e), request=request)
            return JsonResponse({'success': False, 'error': 'Path not allowed'}, status=403)

        # Check for protected files
        protected_files = ['wp-config.php', '.htaccess', 'index.php']
        if os.path.basename(full_path) in protected_files:
            log_file_operation(scan_id, 'delete', file_path, False, 'Cannot delete protected system file', request=request)
            return JsonResponse({'success': False, 'error': 'Cannot delete protected system file', 'error_code': 'PROTECTED_FILE'}, status=403)

        # Get website user from auth wrapper (already validated during authentication)
        user = file_token.external_app
        if not user:
            error_msg = 'External app not available in auth context'
            log_file_operation(scan_id, 'delete', file_path, False, error_msg, request=request)
            return JsonResponse({'success': False, 'error': error_msg}, status=500)

        # Get file info before deletion
        from plogical.processUtilities import ProcessUtilities
        import hashlib
        import datetime

        stat_cmd = f'stat -c "%s %Y" "{full_path}"'
        stat_result = ProcessUtilities.outputExecutioner(stat_cmd, user=user, retRequired=True)

        if not stat_result[1]:
            log_file_operation(scan_id, 'delete', file_path, False, 'File not found', request=request)
            return JsonResponse({'success': False, 'error': 'File not found', 'error_code': 'FILE_NOT_FOUND'}, status=404)

        file_size = 0
        last_modified = ''
        try:
            parts = stat_result[1].strip().split()
            file_size = int(parts[0])
            last_modified_timestamp = int(parts[1])
            last_modified = datetime.datetime.fromtimestamp(last_modified_timestamp).strftime('%Y-%m-%dT%H:%M:%SZ')
        except (ValueError, IndexError):
            pass

        # Get file hash
        cat_cmd = f'cat "{full_path}"'
        result = ProcessUtilities.outputExecutioner(cat_cmd, user=user, retRequired=True)

        file_hash = ''
        if result[1]:
            try:
                file_hash = hashlib.sha256(result[1].encode('utf-8')).hexdigest()
            except:
                pass

        backup_path = None

        # ALWAYS create backup before deletion
        wp_path_clean = file_token.wp_path.rstrip('/')
        backup_dir_name = f'{wp_path_clean}/.ai-scanner-backups/{datetime.datetime.now().strftime("%Y-%m-%d")}'
        mkdir_cmd = f'mkdir -p "{backup_dir_name}"'
        mkdir_result = ProcessUtilities.executioner(mkdir_cmd, user=user)

        # executioner returns 1 for success, 0 for failure
        if mkdir_result != 1:
            error_msg = f'Failed to create backup directory: {backup_dir_name}'
            logging.writeToFile(f'[API] {error_msg}')
            log_file_operation(scan_id, 'delete', file_path, False, error_msg, request=request)
            return JsonResponse({'success': False, 'error': 'Failed to create backup directory', 'error_code': 'BACKUP_DIR_FAILED'}, status=500)

        timestamp = int(time.time())
        basename = os.path.basename(full_path)
        backup_filename = f'{basename}.{timestamp}.bak'
        backup_path = os.path.join(backup_dir_name, backup_filename)

        cp_cmd = f'cp "{full_path}" "{backup_path}"'
        cp_result = ProcessUtilities.executioner(cp_cmd, user=user)

        # executioner returns 1 for success, 0 for failure
        if cp_result != 1:
            error_msg = f'Failed to backup file before deletion'
            logging.writeToFile(f'[API] {error_msg}, cp_result={cp_result}')
            log_file_operation(scan_id, 'delete', file_path, False, error_msg, backup_path=backup_path, request=request)
            return JsonResponse({'success': False, 'error': 'Backup creation failed - deletion blocked', 'error_code': 'BACKUP_FAILED'}, status=500)

        # Delete file
        rm_cmd = f'rm -f "{full_path}"'
        rm_result = ProcessUtilities.executioner(rm_cmd, user=user)

        # executioner returns 1 for success, 0 for failure
        if rm_result != 1:
            log_file_operation(scan_id, 'delete', file_path, False, 'Failed to delete file', backup_path=backup_path, request=request)
            return JsonResponse({'success': False, 'error': 'Failed to delete file', 'error_code': 'DELETE_FAILED'}, status=500)

        # Verify deletion
        check_cmd = f'test -f "{full_path}" && echo "exists"'
        result = ProcessUtilities.outputExecutioner(check_cmd, user=user, retRequired=True)

        if result[1] and 'exists' in result[1]:
            log_file_operation(scan_id, 'delete', file_path, False, 'Deletion verification failed', backup_path=backup_path, request=request)
            return JsonResponse({'success': False, 'error': 'Deletion verification failed'}, status=500)

        # Log success
        log_file_operation(scan_id, 'delete', file_path, True, backup_path=backup_path, request=request)

        logging.writeToFile(f'[API] File deleted: {file_path} (backup: {backup_path})')

        return JsonResponse({
            'success': True,
            'file_path': file_path,
            'backup_path': backup_path,
            'deleted_at': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'file_info': {
                'size': file_size,
                'last_modified': last_modified,
                'hash': file_hash
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logging.writeToFile(f'[API] Delete file error: {str(e)}')
        log_file_operation(scan_id if 'scan_id' in locals() else 'unknown', 'delete',
                          file_path if 'file_path' in locals() else 'unknown', False, str(e), request=request)
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)
