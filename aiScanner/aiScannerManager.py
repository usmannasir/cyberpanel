import requests
import json
import re
import time
import uuid
import secrets
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.contrib import messages
from loginSystem.models import Administrator
from .models import AIScannerSettings, ScanHistory, FileAccessToken
from .access import scanner_allowed
from .panel_address import panel_address
from .platform_auth import platform_page_url, saved_scanner_auth_headers, scanner_payment_setup_request
from plogical.acl import ACLManager
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


class AIScannerManager:
    AI_SCANNER_API_BASE = 'https://platform.cyberpersons.com/ai-scanner'
    # Payment set-up must come back to the session that started it within this many seconds.
    SETUP_TIME_LIMIT = 3600
    API_KEY_SHAPE = re.compile(r'cp_[A-Za-z0-9_-]{20,200}')
    
    def __init__(self):
        self.logger = logging
    
    def scannerHome(self, request, userID):
        """Main AI Scanner page"""
        try:
            admin = Administrator.objects.get(pk=userID)
            
            # Load ACL permissions
            currentACL = ACLManager.loadedACL(userID)
            
            # Check ACL permissions (with fallback for new field)
            try:
                if currentACL.get('aiScannerAccess', 1) == 0:
                    return ACLManager.loadError()
            except (AttributeError, KeyError):
                # Field doesn't exist yet, allow access for now
                self.logger.writeToFile(f'[AIScannerManager.scannerHome] aiScannerAccess field not found, allowing access')
                pass
            
            # Get or create scanner settings
            scanner_settings, created = AIScannerSettings.objects.get_or_create(
                admin=admin,
                defaults={'balance': 0.0000, 'is_payment_configured': False}
            )
            
            # Get current pricing from API
            pricing_data = self.get_ai_scanner_pricing()
            
            # Get recent scan history with ACL respect
            if currentACL['admin'] == 1:
                # Admin can see all scans
                recent_scans = ScanHistory.objects.all().order_by('-started_at')[:10]
            else:
                # Users can only see their own scans and their sub-users' scans
                user_admins = ACLManager.loadUserObjects(userID)
                recent_scans = ScanHistory.objects.filter(admin__in=user_admins).order_by('-started_at')[:10]
            
            # Get current balance if payment is configured
            current_balance = scanner_settings.balance
            
            if scanner_settings.is_payment_configured:
                # Try to fetch latest balance from API (now supports flexible auth)
                api_balance = self.get_account_balance(scanner_settings.api_key)
                
                if api_balance is not None:
                    scanner_settings.balance = api_balance
                    scanner_settings.save()
                    current_balance = api_balance
                else:
                    self.logger.writeToFile('[AIScannerManager.scannerHome] Balance request failed, keeping the stored balance')
            
            # Check VPS free scans availability
            server_ip = ACLManager.fetchIP()
            vps_info = self.check_vps_free_scans(server_ip)
            
            # Get user's websites for scan selection using ACL-aware method
            try:
                websites = ACLManager.findWebsiteObjects(currentACL, userID)
                self.logger.writeToFile(f'[AIScannerManager.scannerHome] Found {len(websites)} websites for {admin.userName}')
            except Exception as e:
                self.logger.writeToFile(f'[AIScannerManager.scannerHome] Error fetching websites: {str(e)}')
                websites = []
            
            # Build context safely
            self.logger.writeToFile(f'[AIScannerManager.scannerHome] Building context for {admin.userName}')
            
            context = {
                'admin': admin,
                'scanner_settings': scanner_settings,
                'pricing_data': pricing_data,
                'recent_scans': recent_scans,
                'current_balance': current_balance,
                'websites': websites,
                'is_payment_configured': scanner_settings.is_payment_configured,
                'vps_info': vps_info,
                'server_ip': server_ip,
            }
            
            self.logger.writeToFile(f'[AIScannerManager.scannerHome] Context built successfully, rendering template')
            
            return render(request, 'aiScanner/scanner.html', context)
            
        except Exception as e:
            import traceback
            self.logger.writeToFile(f'[AIScannerManager.scannerHome] Error: {str(e)}')
            self.logger.writeToFile(f'[AIScannerManager.scannerHome] Traceback: {traceback.format_exc()}')
            
            return render(request, 'aiScanner/scanner.html', {
                'error': 'Failed to load AI Scanner page. Please check the panel log.',
                'is_payment_configured': False,
                'websites': [],
                'recent_scans': [],
                'current_balance': 0,
                'pricing_data': None
            })
    
    def setupPayment(self, request, userID):
        """Setup payment method for AI scanner"""
        try:
            if request.method != 'POST':
                return JsonResponse({'success': False, 'error': 'Invalid request method'})
            
            admin = Administrator.objects.get(pk=userID)
            
            # Load ACL permissions
            currentACL = ACLManager.loadedACL(userID)
            
            # Check ACL permissions (with fallback for new field)
            try:
                if currentACL.get('aiScannerAccess', 1) == 0:
                    return JsonResponse({'success': False, 'error': 'Access denied'})
            except (AttributeError, KeyError):
                # Field doesn't exist yet, allow access for now
                pass
            
            # Get admin email and domain
            cyberpanel_host = request.get_host()  # Keep full host including port
            cyberpanel_domain = cyberpanel_host.split(':')[0]  # Domain only for email fallback
            admin_email = admin.email if hasattr(admin, 'email') and admin.email else f'{admin.userName}@{cyberpanel_domain}'
            
            # Setup payment with AI Scanner API
            self.logger.writeToFile(f'[AIScannerManager.setupPayment] Attempting payment setup for {admin.userName} on {cyberpanel_host}')
            setup_data = self.setup_ai_scanner_payment(admin_email, cyberpanel_host, admin=admin)
            
            if setup_data:
                self.logger.writeToFile(f'[AIScannerManager.setupPayment] Payment setup started for {admin.userName}')
                # Only the session that started the set-up may complete it, once and soon.
                request.session['aiScannerSetupStarted'] = int(time.time())
                return JsonResponse({
                    'success': True,
                    'payment_url': setup_data['payment_url'],
                    'token': setup_data['token']
                })
            else:
                self.logger.writeToFile(f'[AIScannerManager.setupPayment] Payment setup failed for {admin.userName}')
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to setup payment. Please check the logs and try again.'
                })
                
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.setupPayment] Error: {str(e)}')
            return JsonResponse({'success': False, 'error': 'Internal server error'})
    
    def setupComplete(self, request, userID):
        """Handle return from payment setup

        The platform sends the browser back here with the new key in the
        address. It is stored only for a signed-in user who may use the
        scanner and who started the set-up in this session a short while ago.
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if not scanner_allowed(ACLManager.loadedACL(userID)):
                return ACLManager.loadError()

            # The marker of a started set-up is used up whatever comes back.
            started = request.session.pop('aiScannerSetupStarted', None)
            status = request.GET.get('status')

            if status in ('success', 'partial_success'):
                api_key = request.GET.get('api_key') or ''
                if isinstance(started, bool) or not isinstance(started, int) \
                        or not 0 <= time.time() - started <= self.SETUP_TIME_LIMIT:
                    self.logger.writeToFile(f'[AIScannerManager.setupComplete] No payment setup in progress for {admin.userName}')
                    messages.error(request, 'Payment setup was not started from this session or took too long. Please start it again.')
                elif not self.API_KEY_SHAPE.fullmatch(api_key):
                    self.logger.writeToFile('[AIScannerManager.setupComplete] No valid API key received')
                    messages.error(request, 'Payment setup completed but no valid API key was received.')
                else:
                    # The balance is asked from the platform; what the address says is never stored.
                    settings_values = {'api_key': api_key, 'is_payment_configured': True}
                    balance = self.get_account_balance(api_key)
                    if balance is not None:
                        settings_values['balance'] = balance
                    AIScannerSettings.objects.update_or_create(admin=admin, defaults=settings_values)

                    if status == 'success':
                        messages.success(request, 'Payment setup successful!')
                    else:
                        messages.warning(request, 'Payment method added but initial charge failed. Please add funds manually.')
                    self.logger.writeToFile(f'[AIScannerManager] Payment setup completed for {admin.userName} ({status})')

            elif status in ['failed', 'cancelled', 'error']:
                messages.error(request, 'Payment setup failed or was cancelled.')
                self.logger.writeToFile(f'[AIScannerManager] Payment setup failed for {admin.userName}')

            return redirect('aiScannerHome')

        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.setupComplete] Error: {type(e).__name__}')
            messages.error(request, 'An error occurred during payment setup.')
            return redirect('aiScannerHome')

    def startScan(self, request, userID):
        """Start a new AI security scan"""
        try:
            if request.method != 'POST':
                return JsonResponse({'success': False, 'error': 'Invalid request method'})
            
            admin = Administrator.objects.get(pk=userID)
            
            # Load ACL permissions
            currentACL = ACLManager.loadedACL(userID)
            
            # Check ACL permissions (with fallback for new field)
            try:
                if currentACL.get('aiScannerAccess', 1) == 0:
                    return JsonResponse({'success': False, 'error': 'Access denied'})
            except (AttributeError, KeyError):
                # Field doesn't exist yet, allow access for now
                pass
            
            # Check VPS free scans availability first
            server_ip = ACLManager.fetchIP()
            vps_info = self.check_vps_free_scans(server_ip)
            
            # If VPS is eligible for free scans, get or create API key
            vps_api_key = None
            vps_key_data = None
            if (vps_info.get('success') and 
                vps_info.get('is_vps') and 
                vps_info.get('free_scans_available', 0) > 0):
                
                self.logger.writeToFile(f'[AIScannerManager.startScan] VPS eligible for free scans, getting API key for IP: {server_ip}')
                vps_key_data = self.get_or_create_vps_api_key(server_ip, admin=admin)

                if vps_key_data:
                    vps_api_key = vps_key_data.get('api_key')
                    free_scans_remaining = vps_key_data.get('free_scans_remaining', 0)
                    self.logger.writeToFile(f'[AIScannerManager.startScan] VPS API key obtained, {free_scans_remaining} free scans remaining')

                    # Save VPS API key to database for future operations (file fixes, etc.)
                    try:
                        scanner_settings, created = AIScannerSettings.objects.get_or_create(
                            admin=admin,
                            defaults={
                                'api_key': vps_api_key,
                                'balance': 0.0000,
                                'is_payment_configured': True  # VPS accounts have implicit payment
                            }
                        )

                        # Update existing settings if API key is different or empty
                        if not created and (not scanner_settings.api_key or scanner_settings.api_key != vps_api_key):
                            scanner_settings.api_key = vps_api_key
                            scanner_settings.is_payment_configured = True
                            scanner_settings.save()
                            self.logger.writeToFile(f'[AIScannerManager.startScan] Updated VPS API key in database')
                        elif created:
                            self.logger.writeToFile(f'[AIScannerManager.startScan] Saved new VPS API key to database')
                    except Exception as e:
                        self.logger.writeToFile(f'[AIScannerManager.startScan] Error saving VPS API key: {str(e)}')
                        # Continue even if saving fails - scan can still proceed
                else:
                    self.logger.writeToFile(f'[AIScannerManager.startScan] Failed to get VPS API key')
                    return JsonResponse({'success': False, 'error': 'Failed to authenticate VPS for free scans'})
            
            # Get scanner settings (only required if not using VPS free scan)
            scanner_settings = None
            if not vps_api_key:
                try:
                    scanner_settings = AIScannerSettings.objects.get(admin=admin)
                    if not scanner_settings.is_payment_configured or not scanner_settings.api_key:
                        return JsonResponse({'success': False, 'error': 'Payment not configured'})
                except AIScannerSettings.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Scanner not configured'})
            
            # Parse request data
            data = json.loads(request.body)
            domain = data.get('domain')
            scan_type = data.get('scan_type', 'full')
            
            if not domain or not isinstance(domain, str):
                return JsonResponse({'success': False, 'error': 'Domain is required'})
            if scan_type not in [choice[0] for choice in ScanHistory.SCAN_TYPE_CHOICES]:
                return JsonResponse({'success': False, 'error': 'Invalid scan type'})
            
            # Validate domain belongs to user using ACL-aware method
            from websiteFunctions.models import Websites
            try:
                # Check if user has access to this domain through ACL system
                if not ACLManager.checkOwnership(domain, admin, currentACL):
                    return JsonResponse({'success': False, 'error': 'Access denied to this domain'})
                
                # Get the website object (we know it exists due to checkOwnership)
                website = Websites.objects.get(domain=domain)
            except Websites.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Domain not found'})
            
            # Generate scan ID and file access token
            scan_id = f'cp_{uuid.uuid4().hex[:12]}'
            file_access_token = self.generate_file_access_token()
            
            # Create scan history record
            scan_history = ScanHistory.objects.create(
                admin=admin,
                scan_id=scan_id,
                domain=domain,
                scan_type=scan_type,
                status='pending'
            )
            
            # Create file access token
            FileAccessToken.objects.create(
                token=file_access_token,
                scan_history=scan_history,
                domain=domain,
                wp_path=f'/home/{domain}/public_html',  # Adjust path as needed
                expires_at=timezone.now() + timedelta(hours=2)
            )
            
            # Submit scan to AI Scanner API
            panel_host = panel_address(request, admin, currentACL)
            callback_url = f"https://{panel_host}/api/ai-scanner/callback"
            file_access_base_url = f"https://{panel_host}/api/ai-scanner/"
            
            # Use VPS API key if available, otherwise use regular scanner settings
            api_key_to_use = vps_api_key if vps_api_key else scanner_settings.api_key
            
            scan_response = self.submit_wordpress_scan(
                api_key_to_use,
                domain,
                scan_type,
                callback_url,
                file_access_token,
                file_access_base_url,
                scan_id,
                server_ip
            )
            
            if scan_response:
                scan_history.status = 'running'
                scan_history.save()
                
                # Create appropriate success message
                if vps_api_key:
                    message = f'Free VPS scan started successfully! {vps_key_data.get("free_scans_remaining", 0)} free scans remaining.'
                else:
                    message = 'Scan started successfully'
                
                return JsonResponse({
                    'success': True,
                    'scan_id': scan_id,
                    'message': message
                })
            else:
                scan_history.status = 'failed'
                scan_history.error_message = 'Failed to submit scan to AI Scanner API'
                scan_history.save()
                
                return JsonResponse({'success': False, 'error': 'Failed to start scan'})
                
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.startScan] Error: {str(e)}')
            return JsonResponse({'success': False, 'error': 'Internal server error'})
    
    def refreshBalance(self, request, userID):
        """Refresh account balance from API"""
        try:
            if request.method != 'POST':
                return JsonResponse({'success': False, 'error': 'Invalid request method'})
            
            admin = Administrator.objects.get(pk=userID)
            
            # Load ACL permissions
            currentACL = ACLManager.loadedACL(userID)
            
            # Check ACL permissions (with fallback for new field)
            try:
                if currentACL.get('aiScannerAccess', 1) == 0:
                    return JsonResponse({'success': False, 'error': 'Access denied'})
            except (AttributeError, KeyError):
                # Field doesn't exist yet, allow access for now
                pass
            
            # Get scanner settings
            try:
                scanner_settings = AIScannerSettings.objects.get(admin=admin)
                if not scanner_settings.is_payment_configured or not scanner_settings.api_key:
                    return JsonResponse({'success': False, 'error': 'Payment not configured'})
            except AIScannerSettings.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Scanner not configured'})
            
            # Fetch balance from API
            api_balance = self.get_account_balance(scanner_settings.api_key)
            
            if api_balance is not None:
                old_balance = scanner_settings.balance
                scanner_settings.balance = api_balance
                scanner_settings.save()
                
                self.logger.writeToFile(f'[AIScannerManager.refreshBalance] Updated balance from ${old_balance} to ${api_balance} for {admin.userName}')
                
                return JsonResponse({
                    'success': True,
                    'balance': float(api_balance),
                    'message': f'Balance refreshed: ${api_balance:.4f}'
                })
            else:
                return JsonResponse({'success': False, 'error': 'Failed to fetch balance from API'})
                
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.refreshBalance] Error: {str(e)}')
            return JsonResponse({'success': False, 'error': 'Internal server error'})
    
    def addPaymentMethod(self, request, userID):
        """Add a new payment method for the user"""
        try:
            if request.method != 'POST':
                return JsonResponse({'success': False, 'error': 'Invalid request method'})
            
            admin = Administrator.objects.get(pk=userID)
            
            # Load ACL permissions
            currentACL = ACLManager.loadedACL(userID)
            
            # Check ACL permissions (with fallback for new field)
            try:
                if currentACL.get('aiScannerAccess', 1) == 0:
                    return JsonResponse({'success': False, 'error': 'Access denied'})
            except (AttributeError, KeyError):
                # Field doesn't exist yet, allow access for now
                pass
            
            # Check if user has scanner configured (create if VPS user)
            try:
                scanner_settings = AIScannerSettings.objects.get(admin=admin)
                if not scanner_settings.is_payment_configured or not scanner_settings.api_key:
                    # Check if this is a VPS with free scans
                    server_ip = ACLManager.fetchIP()
                    vps_info = self.check_vps_free_scans(server_ip)
                    
                    if vps_info.get('is_vps'):
                        # VPS users can add payment methods without initial setup
                        # Get or create VPS API key
                        vps_key_data = self.get_or_create_vps_api_key(server_ip, admin=admin)
                        if vps_key_data and vps_key_data.get('api_key'):
                            # Use VPS API key for adding payment method
                            api_key_to_use = vps_key_data.get('api_key')

                            # Save VPS API key to database
                            scanner_settings.api_key = api_key_to_use
                            scanner_settings.is_payment_configured = True
                            scanner_settings.save()
                            self.logger.writeToFile(f'[AIScannerManager.addPaymentMethod] Saved VPS API key to database')
                        else:
                            return JsonResponse({'success': False, 'error': 'Failed to authenticate VPS'})
                    else:
                        return JsonResponse({'success': False, 'error': 'Initial payment setup required first'})
                else:
                    api_key_to_use = scanner_settings.api_key
            except AIScannerSettings.DoesNotExist:
                # Check if this is a VPS with free scans
                server_ip = ACLManager.fetchIP()
                vps_info = self.check_vps_free_scans(server_ip)
                
                if vps_info.get('is_vps'):
                    # VPS users can add payment methods without initial setup
                    # Get or create VPS API key
                    vps_key_data = self.get_or_create_vps_api_key(server_ip, admin=admin)
                    if vps_key_data and vps_key_data.get('api_key'):
                        # Use VPS API key for adding payment method
                        api_key_to_use = vps_key_data.get('api_key')

                        # Create scanner settings with VPS API key
                        AIScannerSettings.objects.create(
                            admin=admin,
                            api_key=api_key_to_use,
                            balance=0.0000,
                            is_payment_configured=True
                        )
                        self.logger.writeToFile(f'[AIScannerManager.addPaymentMethod] Created new scanner settings with VPS API key')
                    else:
                        return JsonResponse({'success': False, 'error': 'Failed to authenticate VPS'})
                else:
                    return JsonResponse({'success': False, 'error': 'Scanner not configured'})
            
            # Get admin email and domain
            cyberpanel_host = request.get_host()  # Keep full host including port
            cyberpanel_domain = cyberpanel_host.split(':')[0]  # Domain only for email fallback
            admin_email = admin.email if hasattr(admin, 'email') and admin.email else f'{admin.userName}@{cyberpanel_domain}'
            
            self.logger.writeToFile(f'[AIScannerManager.addPaymentMethod] Setting up new payment method for {admin.userName} (API key authentication)')
            
            # Call platform API to add payment method
            setup_data = self.setup_add_payment_method(api_key_to_use, admin_email, cyberpanel_host)
            
            if setup_data:
                self.logger.writeToFile(f'[AIScannerManager.addPaymentMethod] Payment method setup started for {admin.userName}')
                return JsonResponse({
                    'success': True,
                    'setup_url': setup_data['setup_url'],
                    'token': setup_data.get('token', '')
                })
            else:
                self.logger.writeToFile(f'[AIScannerManager.addPaymentMethod] Payment method setup failed for {admin.userName}')
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to setup payment method. Please try again.'
                })
                
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.addPaymentMethod] Error: {str(e)}')
            return JsonResponse({'success': False, 'error': 'Internal server error'})
    
    def paymentMethodComplete(self, request, userID):
        """Handle return from adding payment method"""
        try:
            admin = Administrator.objects.get(pk=userID)
            
            # Load ACL permissions
            currentACL = ACLManager.loadedACL(userID)
            
            # Check ACL permissions (with fallback for new field)
            try:
                if currentACL.get('aiScannerAccess', 1) == 0:
                    messages.error(request, 'Access denied to AI Scanner')
                    return redirect('dashboard')
            except (AttributeError, KeyError):
                # Field doesn't exist yet, allow access for now
                pass
            
            status = request.GET.get('status')
            
            if status == 'success':
                # What the address says about the card is shown only when it looks like a card.
                card_last4 = request.GET.get('card_last4') or ''
                card_brand = request.GET.get('card_brand') or ''
                
                if re.fullmatch(r'[0-9]{4}', card_last4) and re.fullmatch(r'[A-Za-z][A-Za-z ]{0,19}', card_brand):
                    messages.success(request, f'Payment method added successfully! New {card_brand} card ending in {card_last4}.')
                else:
                    messages.success(request, 'Payment method added successfully!')
                self.logger.writeToFile(f'[AIScannerManager] Payment method added for {admin.userName}')
                    
            elif status in ['failed', 'cancelled', 'error']:
                messages.error(request, 'Failed to add payment method.')
                self.logger.writeToFile(f'[AIScannerManager] Payment method add failed for {admin.userName}')
            
            return redirect('aiScannerHome')
            
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.paymentMethodComplete] Error: {str(e)}')
            messages.error(request, 'An error occurred while adding payment method.')
            return redirect('aiScannerHome')
    
    # API Helper Methods
    
    def get_ai_scanner_pricing(self):
        """Get current pricing from AI Scanner API"""
        try:
            response = requests.get(f'{self.AI_SCANNER_API_BASE}/api/plan/', timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.get_ai_scanner_pricing] Error: {str(e)}')
            return None
    
    def setup_ai_scanner_payment(self, user_email, cyberpanel_host, admin=None):
        """Setup payment method with AI Scanner API"""
        try:
            setup_request = scanner_payment_setup_request(admin, cyberpanel_host)
            if setup_request is None:
                self.logger.writeToFile('[AIScannerManager.setup_ai_scanner_payment] Authenticated account and valid callback host are required')
                return None
            payload, auth_headers = setup_request

            response = requests.post(
                f'{self.AI_SCANNER_API_BASE}/cyberpanel/setup-payment/',
                json=payload,
                headers=auth_headers,
                timeout=10
            )
            
            self.logger.writeToFile(f'[AIScannerManager.setup_ai_scanner_payment] Response status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    payment_url = platform_page_url(data.get('payment_url'))
                    if payment_url is None:
                        self.logger.writeToFile('[AIScannerManager.setup_ai_scanner_payment] The platform returned an address outside the platform')
                        return None
                    return {
                        'payment_url': payment_url,
                        'token': data['token']
                    }
                else:
                    self.logger.writeToFile('[AIScannerManager.setup_ai_scanner_payment] API returned success=false')
            else:
                self.logger.writeToFile(f'[AIScannerManager.setup_ai_scanner_payment] Non-200 status code: {response.status_code}')
            
            return None
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.setup_ai_scanner_payment] Exception: {str(e)}')
            return None
    
    def get_account_balance(self, api_key):
        """Get current account balance"""
        try:
            response = requests.get(
                f'{self.AI_SCANNER_API_BASE}/api/account/balance/',
                headers={'X-API-Key': api_key},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # Use the new balance_usd field from flexible API
                    balance = float(data.get('balance_usd', data.get('balance', 0)))
                    return balance
                else:
                    # Even failed responses now include balance_usd hint
                    balance_hint = data.get('balance_usd', 0)
                    self.logger.writeToFile('[AIScannerManager.get_account_balance] API returned success=false')
                    # Return the balance hint if available, even on auth failure
                    if balance_hint > 0:
                        return float(balance_hint)
            else:
                self.logger.writeToFile(f'[AIScannerManager.get_account_balance] Non-200 status code: {response.status_code}')
            
            return None
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.get_account_balance] Exception: {str(e)}')
            return None
    
    def submit_wordpress_scan(self, api_key, domain, scan_type, callback_url, file_access_token, file_access_base_url, scan_id, server_ip):
        """Submit scan request to AI Scanner API"""
        try:
            payload = {
                'domain': domain,
                'site_url': domain,
                'scan_type': scan_type,
                'cyberpanel_callback': callback_url,
                'file_access_token': file_access_token,
                'file_access_base_url': file_access_base_url,
                'scan_id': scan_id,
                'server_ip': server_ip
            }
            
            self.logger.writeToFile(f'[AIScannerManager.submit_wordpress_scan] Submitting scan {scan_id} for {domain}')
            
            response = requests.post(
                f'{self.AI_SCANNER_API_BASE}/api/scan/submit-v2/',
                headers={'X-API-Key': api_key},
                json=payload,
                timeout=10
            )
            
            self.logger.writeToFile(f'[AIScannerManager.submit_wordpress_scan] Response status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    platform_scan_id = data.get('scan_id')
                    self.logger.writeToFile(f'[AIScannerManager.submit_wordpress_scan] Platform assigned scan ID: {platform_scan_id}')
                    return platform_scan_id
                else:
                    self.logger.writeToFile('[AIScannerManager.submit_wordpress_scan] Platform returned success=false')
            else:
                self.logger.writeToFile(f'[AIScannerManager.submit_wordpress_scan] Non-200 status code: {response.status_code}')
            
            return None
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.submit_wordpress_scan] Error: {str(e)}')
            return None
    
    def get_scan_status(self, api_key, scan_id):
        """Get scan status from AI Scanner API"""
        try:
            response = requests.get(
                f'{self.AI_SCANNER_API_BASE}/api/scan/{scan_id}/status/',
                headers={'X-API-Key': api_key},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.get_scan_status] Error: {str(e)}')
            return None
    
    def get_scan_results(self, api_key, scan_id):
        """Get scan results from AI Scanner API"""
        try:
            response = requests.get(
                f'{self.AI_SCANNER_API_BASE}/api/scan/{scan_id}/results/',
                headers={'X-API-Key': api_key},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.get_scan_results] Error: {str(e)}')
            return None
    
    def check_vps_free_scans(self, server_ip):
        """Check if server IP belongs to VPS hosting and has free scans available"""
        try:
            self.logger.writeToFile(f'[AIScannerManager.check_vps_free_scans] Checking VPS free scans for IP: {server_ip}')
            
            response = requests.post(
                'https://platform.cyberpersons.com/ai-scanner/api/vps/check-free-scans/',
                json={'ip': server_ip},
                timeout=10
            )
            
            self.logger.writeToFile(f'[AIScannerManager.check_vps_free_scans] Response status: {response.status_code}')
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'success': False, 'is_vps': False, 'error': 'API call failed'}
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.check_vps_free_scans] Error: {type(e).__name__}')
            return {'success': False, 'is_vps': False, 'error': 'API call failed'}

    def setup_add_payment_method(self, api_key, user_email, cyberpanel_host):
        """Setup additional payment method with AI Scanner API"""
        try:
            payload = {
                'domain': cyberpanel_host.split(':')[0],  # Send domain without port
                'return_url': f'https://{cyberpanel_host}/aiscanner/payment-method-complete/',  # Include port in URL
                'action': 'add_payment_method'  # Indicate this is adding a payment method, not initial setup
            }
            
            response = requests.post(
                f'{self.AI_SCANNER_API_BASE}/cyberpanel/add-payment-method/',
                headers={'X-API-Key': api_key},
                json=payload,
                timeout=10
            )
            
            self.logger.writeToFile(f'[AIScannerManager.setup_add_payment_method] Response status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    setup_url = platform_page_url(data.get('setup_url'))
                    if setup_url is None:
                        self.logger.writeToFile('[AIScannerManager.setup_add_payment_method] The platform returned an address outside the platform')
                        return None
                    return {
                        'setup_url': setup_url,
                        'token': data.get('token', '')
                    }
                else:
                    self.logger.writeToFile('[AIScannerManager.setup_add_payment_method] API returned success=false')
            else:
                self.logger.writeToFile(f'[AIScannerManager.setup_add_payment_method] Non-200 status code: {response.status_code}')
            
            return None
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.setup_add_payment_method] Exception: {str(e)}')
            return None

    def get_or_create_vps_api_key(self, server_ip, admin=None):
        """Get API key for VPS free scans from platform"""
        try:
            auth_headers = saved_scanner_auth_headers(admin)
            if not auth_headers:
                self.logger.writeToFile('[AIScannerManager.get_or_create_vps_api_key] Connect an authenticated scanner or CyberMail account before requesting a scanner key')
                return None
            payload = {'server_ip': server_ip}
            
            self.logger.writeToFile(f'[AIScannerManager.get_or_create_vps_api_key] Requesting VPS API key for IP: {server_ip}')
            
            response = requests.post(
                f'{self.AI_SCANNER_API_BASE}/api/vps/generate-api-key/',
                json=payload,
                headers={'Content-Type': 'application/json', **auth_headers},
                timeout=10
            )
            
            self.logger.writeToFile(f'[AIScannerManager.get_or_create_vps_api_key] Response status: {response.status_code}')
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return {
                        'api_key': data.get('api_key'),
                        'free_scans_remaining': data.get('free_scans_remaining'),
                        'account_type': data.get('account_type'),
                        'vps_name': data.get('vps_name'),
                        'vps_id': data.get('vps_id')
                    }
                else:
                    self.logger.writeToFile('[AIScannerManager.get_or_create_vps_api_key] API returned success=false')
            else:
                self.logger.writeToFile(f'[AIScannerManager.get_or_create_vps_api_key] Non-200 status code: {response.status_code}')
            
            return None
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.get_or_create_vps_api_key] Exception: {str(e)}')
            return None

    def generate_file_access_token(self):
        """Generate secure file access token"""
        return f'cp_{secrets.token_urlsafe(32)}'