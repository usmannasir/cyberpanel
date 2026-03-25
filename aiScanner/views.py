from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from loginSystem.views import loadLoginPage
from .aiScannerManager import AIScannerManager
import json
import os


def aiScannerHome(request):
    """Main AI Scanner page"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.scannerHome(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def setupPayment(request):
    """Setup payment method for AI scanner"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.setupPayment(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def setupComplete(request):
    """Handle return from payment setup"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.setupComplete(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def startScan(request):
    """Start a new AI security scan"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.startScan(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def refreshBalance(request):
    """Refresh account balance from API"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.refreshBalance(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def addPaymentMethod(request):
    """Add a new payment method"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.addPaymentMethod(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def paymentMethodComplete(request):
    """Handle return from adding payment method"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.paymentMethodComplete(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


@csrf_exempt
def scanCallback(request):
    """Handle scan results callback from AI Scanner API"""
    sm = AIScannerManager()
    return sm.scanCallback(request)


def getScanHistory(request):
    """Get scan history for user"""
    try:
        userID = request.session['userID']
        from loginSystem.models import Administrator
        from .models import ScanHistory
        from plogical.acl import ACLManager
        
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)
        
        # Get scan history with ACL respect
        if currentACL['admin'] == 1:
            # Admin can see all scans
            scans = ScanHistory.objects.all().order_by('-started_at')[:20]
        else:
            # Users can only see their own scans and their sub-users' scans
            user_admins = ACLManager.loadUserObjects(userID)
            scans = ScanHistory.objects.filter(admin__in=user_admins).order_by('-started_at')[:20]
        
        scan_data = []
        for scan in scans:
            scan_data.append({
                'scan_id': scan.scan_id,
                'domain': scan.domain,
                'status': scan.status,
                'scan_type': scan.scan_type,
                'started_at': scan.started_at.strftime('%Y-%m-%d %H:%M:%S'),
                'completed_at': scan.completed_at.strftime('%Y-%m-%d %H:%M:%S') if scan.completed_at else None,
                'cost_usd': float(scan.cost_usd) if scan.cost_usd else 0,
                'files_scanned': scan.files_scanned,
                'issues_found': scan.issues_found,
                'findings': scan.findings[:5] if scan.findings else [],  # First 5 findings
                'summary': scan.summary
            })
        
        return JsonResponse({'success': True, 'scans': scan_data})
        
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(['GET'])
def getScanDetails(request, scan_id):
    """Get detailed scan results"""
    try:
        userID = request.session['userID']
        from loginSystem.models import Administrator
        from .models import ScanHistory
        from .status_models import ScanStatusUpdate
        from plogical.acl import ACLManager
        
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)
        
        # Get scan with ACL respect
        try:
            scan = ScanHistory.objects.get(scan_id=scan_id)
            
            # Check if user has access to this scan
            if currentACL['admin'] != 1:
                # Non-admin users can only see their own scans and their sub-users' scans
                user_admins = ACLManager.loadUserObjects(userID)
                if scan.admin not in user_admins:
                    return JsonResponse({'success': False, 'error': 'Access denied to this scan'})
        except ScanHistory.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Scan not found'})
        
        # Get the status update for more detailed information
        try:
            status_update = ScanStatusUpdate.objects.get(scan_id=scan_id)
            # Use detailed information from status update if available
            files_scanned = status_update.files_scanned if status_update.files_scanned > 0 else scan.files_scanned
            files_discovered = status_update.files_discovered
            threats_found = status_update.threats_found
            critical_threats = status_update.critical_threats
            high_threats = status_update.high_threats
        except ScanStatusUpdate.DoesNotExist:
            # Fall back to basic information from scan history
            files_scanned = scan.files_scanned
            files_discovered = scan.files_scanned  # Approximate
            threats_found = scan.issues_found
            critical_threats = 0
            high_threats = 0
        
        scan_data = {
            'scan_id': scan.scan_id,
            'domain': scan.domain,
            'status': scan.status,
            'scan_type': scan.scan_type,
            'started_at': scan.started_at.strftime('%Y-%m-%d %H:%M:%S'),
            'completed_at': scan.completed_at.strftime('%Y-%m-%d %H:%M:%S') if scan.completed_at else None,
            'cost_usd': float(scan.cost_usd) if scan.cost_usd else 0,
            'files_scanned': files_scanned,
            'files_discovered': files_discovered,
            'issues_found': scan.issues_found,
            'threats_found': threats_found,
            'critical_threats': critical_threats,
            'high_threats': high_threats,
            'findings': scan.findings,
            'summary': scan.summary,
            'error_message': scan.error_message
        }
        
        return JsonResponse({'success': True, 'scan': scan_data})
        
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    except ScanHistory.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Scan not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(['GET'])
def getPlatformMonitorUrl(request, scan_id):
    """Get the platform monitor URL for a scan"""
    try:
        userID = request.session['userID']
        from loginSystem.models import Administrator
        from .models import ScanHistory, AIScannerSettings
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
        import requests
        
        # Get scan to verify ownership
        try:
            scan = ScanHistory.objects.get(scan_id=scan_id)
            admin = Administrator.objects.get(pk=userID)
            
            # Verify access
            from plogical.acl import ACLManager
            currentACL = ACLManager.loadedACL(userID)
            if currentACL['admin'] != 1:
                user_admins = ACLManager.loadUserObjects(userID)
                if scan.admin not in user_admins:
                    return JsonResponse({'success': False, 'error': 'Access denied'})
        except ScanHistory.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Scan not found'})
        
        # Get API key - first try current user, then scan owner
        api_key = None
        
        # Try current user's API key first
        try:
            current_user_settings = admin.ai_scanner_settings
            if current_user_settings and current_user_settings.api_key:
                api_key = current_user_settings.api_key
        except AIScannerSettings.DoesNotExist:
            pass
        except Exception as e:
            pass
        
        # If current user doesn't have API key, try scan owner's
        if not api_key:
            try:
                scanner_settings = scan.admin.ai_scanner_settings
                if scanner_settings and scanner_settings.api_key:
                    api_key = scanner_settings.api_key
            except AIScannerSettings.DoesNotExist:
                pass
            except Exception as e:
                pass
        
        # If still no API key, check if this might be a VPS free scan
        if not api_key:
            try:
                from plogical.acl import ACLManager
                from .aiScannerManager import AIScannerManager
                
                server_ip = ACLManager.fetchIP()
                sm = AIScannerManager()
                vps_info = sm.check_vps_free_scans(server_ip)
                
                if (vps_info.get('success') and 
                    vps_info.get('is_vps') and 
                    vps_info.get('free_scans_available', 0) > 0):
                    
                    vps_key_data = sm.get_or_create_vps_api_key(server_ip)

                    if vps_key_data and vps_key_data.get('api_key'):
                        api_key = vps_key_data.get('api_key')

                        # Save VPS API key to database for future operations
                        try:
                            admin = Administrator.objects.get(pk=userID)
                            scanner_settings, created = AIScannerSettings.objects.get_or_create(
                                admin=admin,
                                defaults={
                                    'api_key': api_key,
                                    'balance': 0.0000,
                                    'is_payment_configured': True
                                }
                            )

                            if not created and (not scanner_settings.api_key or scanner_settings.api_key != api_key):
                                scanner_settings.api_key = api_key
                                scanner_settings.is_payment_configured = True
                                scanner_settings.save()
                                logging.writeToFile(f"[AI Scanner] Updated VPS API key in database")
                        except Exception as save_error:
                            logging.writeToFile(f"[AI Scanner] Error saving VPS API key: {str(save_error)}")
            except Exception as e:
                pass
        
        # If still no API key, return error
        if not api_key:
            logging.writeToFile(f"[AI Scanner] No API key found for scan {scan_id}")
            return JsonResponse({'success': False, 'error': 'API key not configured. Please configure your AI Scanner API key.'})
        
        # Call platform API to get monitor URL
        try:
            url = f"https://platform.cyberpersons.com/ai-scanner/api/scan/{scan_id}/monitor-url/"
            headers = {
                'X-API-Key': api_key,
                'Content-Type': 'application/json'
            }
            
            logging.writeToFile(f"[AI Scanner] Fetching platform monitor URL for scan {scan_id}")
            
            response = requests.get(url, headers=headers, timeout=10)
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logging.writeToFile(f"[AI Scanner] JSON decode error: {str(e)}")
                return JsonResponse({'success': False, 'error': 'Invalid response from platform'})
            
            if response.status_code == 200 and data.get('success'):
                logging.writeToFile(f"[AI Scanner] Got monitor URL: {data.get('monitor_url')}")
                return JsonResponse({
                    'success': True,
                    'monitor_url': data.get('monitor_url'),
                    'platform_scan_id': data.get('platform_scan_id')
                })
            else:
                error_msg = data.get('error', 'Failed to get monitor URL')
                logging.writeToFile(f"[AI Scanner] Failed to get monitor URL: {error_msg}")
                return JsonResponse({
                    'success': False,
                    'error': error_msg,
                    'scan_exists': data.get('scan_exists', False)
                })
                
        except requests.exceptions.Timeout:
            logging.writeToFile(f"[AI Scanner] Platform request timeout for scan {scan_id}")
            return JsonResponse({'success': False, 'error': 'Platform request timeout'})
        except requests.exceptions.RequestException as e:
            logging.writeToFile(f"[AI Scanner] Platform request error: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Platform error: {str(e)}'})
        except Exception as e:
            logging.writeToFile(f"[AI Scanner] Unexpected error: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Error: {str(e)}'})
            
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    except Exception as e:
        logging.writeToFile(f"[AI Scanner] getPlatformMonitorUrl error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


def getPlatformScanStatus(request, scan_id):
    """Get real-time scan status from AI Scanner platform"""
    try:
        userID = request.session['userID']
        from loginSystem.models import Administrator
        from .models import ScanHistory
        from plogical.acl import ACLManager
        
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)
        
        # Get scan with ACL respect
        try:
            scan = ScanHistory.objects.get(scan_id=scan_id)
            
            # Check if user has access to this scan
            if currentACL['admin'] != 1:
                # Non-admin users can only see their own scans and their sub-users' scans
                user_admins = ACLManager.loadUserObjects(userID)
                if scan.admin not in user_admins:
                    return JsonResponse({'success': False, 'error': 'Access denied to this scan'})
        except ScanHistory.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Scan not found'})
        scanner_settings = admin.ai_scanner_settings
        
        if not scanner_settings.api_key:
            return JsonResponse({'success': False, 'error': 'API key not configured'})
        
        # Get real-time status from platform
        sm = AIScannerManager()
        platform_status = sm.get_scan_status(scanner_settings.api_key, scan_id)
        
        if platform_status and platform_status.get('success'):
            status_data = platform_status.get('data', {})
            
            # Return formatted status data for frontend
            return JsonResponse({
                'success': True,
                'scan_id': scan_id,
                'phase': status_data.get('status', 'unknown'),
                'progress': status_data.get('progress', 0),
                'current_file': status_data.get('current_file', ''),
                'files_discovered': status_data.get('files_discovered', 0),
                'files_scanned': status_data.get('files_scanned', 0), 
                'files_remaining': status_data.get('files_remaining', 0),
                'threats_found': status_data.get('findings_count', 0),
                'critical_threats': status_data.get('critical_threats', 0),
                'high_threats': status_data.get('high_threats', 0),
                'activity_description': status_data.get('activity_description', ''),
                'last_updated': status_data.get('last_updated', ''),
                'is_active': status_data.get('status') in ['scanning', 'discovering_files', 'starting'],
                'cost': status_data.get('cost', '$0.00')
            })
        else:
            # No live status available, return scan database status
            return JsonResponse({
                'success': True,
                'scan_id': scan_id,
                'phase': scan.status,
                'progress': 100 if scan.status == 'completed' else 0,
                'current_file': '',
                'files_discovered': scan.files_scanned,
                'files_scanned': scan.files_scanned,
                'files_remaining': 0,
                'threats_found': scan.issues_found,
                'critical_threats': 0,
                'high_threats': 0,
                'activity_description': scan.error_message if scan.status == 'failed' else 'Scan completed',
                'last_updated': scan.completed_at.isoformat() if scan.completed_at else scan.started_at.isoformat(),
                'is_active': False,
                'cost': f'${scan.cost_usd:.4f}' if scan.cost_usd else '$0.00'
            })
        
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    except ScanHistory.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Scan not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# File Access API for AI Scanner

@csrf_exempt
@require_http_methods(['POST'])
def aiScannerAuthenticate(request):
    """Authenticate AI scanner access"""
    try:
        data = json.loads(request.body)
        access_token = data.get('access_token')
        scan_id = data.get('scan_id')
        
        if not access_token or not scan_id:
            return JsonResponse({'success': False, 'error': 'Missing parameters'})
        
        from .models import FileAccessToken, ScanHistory
        
        # Validate token
        try:
            file_token = FileAccessToken.objects.get(
                token=access_token,
                scan_history__scan_id=scan_id,
                is_active=True
            )
            
            if file_token.is_expired():
                return JsonResponse({'success': False, 'error': 'Token expired'})
            
            # Get WordPress info
            from websiteFunctions.models import Websites
            try:
                website = Websites.objects.get(domain=file_token.domain)
                
                # Detect WordPress path and version
                wp_path = file_token.wp_path
                wp_version = 'Unknown'
                php_version = 'Unknown'
                
                # Try to get WP version from wp-includes/version.php
                version_file = os.path.join(wp_path, 'wp-includes', 'version.php')
                if os.path.exists(version_file):
                    try:
                        with open(version_file, 'r') as f:
                            content = f.read()
                            import re
                            match = re.search(r'\$wp_version\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                            if match:
                                wp_version = match.group(1)
                    except:
                        pass
                
                return JsonResponse({
                    'success': True,
                    'site_info': {
                        'domain': file_token.domain,
                        'wp_path': wp_path,
                        'php_version': php_version,
                        'wp_version': wp_version,
                        'scan_id': scan_id
                    }
                })
                
            except Websites.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Website not found'})
                
        except FileAccessToken.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid token'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(['GET'])
def aiScannerListFiles(request):
    """List directory contents for AI scanner"""
    try:
        path = request.GET.get('path', '')
        access_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not access_token:
            return JsonResponse({'success': False, 'error': 'No authorization token'})
        
        from .models import FileAccessToken
        
        # Validate token
        try:
            file_token = FileAccessToken.objects.get(token=access_token, is_active=True)
            
            if file_token.is_expired():
                return JsonResponse({'success': False, 'error': 'Token expired'})
            
            # Construct full path
            full_path = os.path.join(file_token.wp_path, path)
            
            # Security check - ensure path is within WordPress directory
            if not os.path.abspath(full_path).startswith(os.path.abspath(file_token.wp_path)):
                return JsonResponse({'success': False, 'error': 'Path not allowed'})
            
            if not os.path.exists(full_path):
                return JsonResponse({'success': False, 'error': 'Path not found'})
            
            if not os.path.isdir(full_path):
                return JsonResponse({'success': False, 'error': 'Path is not a directory'})
            
            # List directory contents
            items = []
            try:
                for item in os.listdir(full_path):
                    item_path = os.path.join(full_path, item)
                    
                    # Skip hidden files and certain directories
                    if item.startswith('.') or item in ['__pycache__', 'node_modules']:
                        continue
                    
                    if os.path.isdir(item_path):
                        items.append({
                            'name': item,
                            'type': 'directory',
                            'path': os.path.join(path, item).replace('\\', '/') if path else item
                        })
                    else:
                        # Only include certain file types
                        if item.endswith(('.php', '.js', '.html', '.htm', '.css', '.txt', '.md', '.json', '.xml')):
                            items.append({
                                'name': item,
                                'type': 'file',
                                'path': os.path.join(path, item).replace('\\', '/') if path else item,
                                'size': os.path.getsize(item_path)
                            })
                
                return JsonResponse({
                    'success': True,
                    'path': path,
                    'items': items
                })
                
            except PermissionError:
                return JsonResponse({'success': False, 'error': 'Permission denied'})
                
        except FileAccessToken.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid token'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(['GET'])
def aiScannerGetFile(request):
    """Get file content for AI scanner"""
    try:
        file_path = request.GET.get('path')
        access_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not access_token or not file_path:
            return JsonResponse({'success': False, 'error': 'Missing parameters'})
        
        from .models import FileAccessToken
        
        # Validate token
        try:
            file_token = FileAccessToken.objects.get(token=access_token, is_active=True)
            
            if file_token.is_expired():
                return JsonResponse({'success': False, 'error': 'Token expired'})
            
            # Construct full path
            full_path = os.path.join(file_token.wp_path, file_path)
            
            # Security check - ensure path is within WordPress directory
            if not os.path.abspath(full_path).startswith(os.path.abspath(file_token.wp_path)):
                return JsonResponse({'success': False, 'error': 'Path not allowed'})
            
            if not os.path.exists(full_path):
                return JsonResponse({'success': False, 'error': 'File not found'})
            
            if not os.path.isfile(full_path):
                return JsonResponse({'success': False, 'error': 'Path is not a file'})
            
            # Check file size (max 10MB as per API limits)
            file_size = os.path.getsize(full_path)
            if file_size > 10 * 1024 * 1024:  # 10MB
                return JsonResponse({'success': False, 'error': 'File too large'})
            
            # Read file content
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                return JsonResponse({
                    'success': True,
                    'path': file_path,
                    'content': content,
                    'size': file_size
                })
                
            except UnicodeDecodeError:
                # Try binary mode for non-text files
                with open(full_path, 'rb') as f:
                    content = f.read()
                
                # Return base64 encoded for binary files
                import base64
                return JsonResponse({
                    'success': True,
                    'path': file_path,
                    'content': base64.b64encode(content).decode('utf-8'),
                    'encoding': 'base64',
                    'size': file_size
                })
                
        except FileAccessToken.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid token'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
