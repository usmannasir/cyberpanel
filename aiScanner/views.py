from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from loginSystem.views import loadLoginPage
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from .access import scanner_view
from .aiScannerManager import AIScannerManager
from .platform_auth import platform_page_url
import json


@scanner_view(page=True)
def aiScannerHome(request):
    """Main AI Scanner page"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.scannerHome(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


@scanner_view()
def setupPayment(request):
    """Setup payment method for AI scanner"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.setupPayment(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


@scanner_view(page=True)
def setupComplete(request):
    """Handle return from payment setup"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.setupComplete(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


@scanner_view()
def startScan(request):
    """Start a new AI security scan"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.startScan(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


@scanner_view()
def refreshBalance(request):
    """Refresh account balance from API"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.refreshBalance(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


@scanner_view()
def addPaymentMethod(request):
    """Add a new payment method"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.addPaymentMethod(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


@scanner_view(page=True)
def paymentMethodComplete(request):
    """Handle return from adding payment method"""
    try:
        userID = request.session['userID']
        sm = AIScannerManager()
        return sm.paymentMethodComplete(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


@scanner_view()
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
        logging.writeToFile('[AI Scanner] Request failed: %s' % type(e).__name__)
        return JsonResponse({'success': False, 'error': 'Internal server error'})


@scanner_view()
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
        logging.writeToFile('[AI Scanner] Request failed: %s' % type(e).__name__)
        return JsonResponse({'success': False, 'error': 'Internal server error'})


@scanner_view()
@require_http_methods(['GET'])
def getPlatformMonitorUrl(request, scan_id):
    """Get the platform monitor URL for a scan"""
    try:
        userID = request.session['userID']
        from loginSystem.models import Administrator
        from .models import ScanHistory, AIScannerSettings
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
                # The browser opens this address: it must be a page of the platform itself.
                monitor_url = platform_page_url(data.get('monitor_url'))
                if monitor_url is None:
                    logging.writeToFile(f"[AI Scanner] The platform returned no usable monitor address for scan {scan_id}")
                    return JsonResponse({'success': False, 'error': 'Invalid response from platform'})
                return JsonResponse({
                    'success': True,
                    'monitor_url': monitor_url,
                    'platform_scan_id': data.get('platform_scan_id')
                })
            else:
                logging.writeToFile(f"[AI Scanner] Failed to get monitor URL for scan {scan_id}")
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to get monitor URL',
                    'scan_exists': bool(data.get('scan_exists', False))
                })
                
        except requests.exceptions.Timeout:
            logging.writeToFile(f"[AI Scanner] Platform request timeout for scan {scan_id}")
            return JsonResponse({'success': False, 'error': 'Platform request timeout'})
        except requests.exceptions.RequestException as e:
            logging.writeToFile(f"[AI Scanner] Platform request error: {type(e).__name__}")
            return JsonResponse({'success': False, 'error': 'Platform request failed'})
        except Exception as e:
            logging.writeToFile(f"[AI Scanner] Unexpected error: {type(e).__name__}")
            return JsonResponse({'success': False, 'error': 'Internal server error'})
            
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    except Exception as e:
        logging.writeToFile(f"[AI Scanner] getPlatformMonitorUrl error: {type(e).__name__}")
        return JsonResponse({'success': False, 'error': 'Internal server error'})


@scanner_view()
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
        logging.writeToFile('[AI Scanner] Request failed: %s' % type(e).__name__)
        return JsonResponse({'success': False, 'error': 'Internal server error'})
