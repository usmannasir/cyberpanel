import requests
import json
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
from plogical.acl import ACLManager
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


class AIScannerManager:
    AI_SCANNER_API_BASE = 'https://platform.cyberpersons.com/ai-scanner'
    
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
            self.logger.writeToFile(f'[AIScannerManager.scannerHome] Stored balance: {current_balance}')
            
            if scanner_settings.is_payment_configured:
                # Try to fetch latest balance from API (now supports flexible auth)
                self.logger.writeToFile(f'[AIScannerManager.scannerHome] Fetching balance from API...')
                api_balance = self.get_account_balance(scanner_settings.api_key)
                self.logger.writeToFile(f'[AIScannerManager.scannerHome] API returned balance: {api_balance}')
                
                if api_balance is not None:
                    scanner_settings.balance = api_balance
                    scanner_settings.save()
                    current_balance = api_balance
                    self.logger.writeToFile(f'[AIScannerManager.scannerHome] Updated balance to: {current_balance}')
                else:
                    self.logger.writeToFile(f'[AIScannerManager.scannerHome] API balance call failed, keeping stored balance: {current_balance}')
            
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
                'error': f'Failed to load AI Scanner page: {str(e)}',
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
            
            self.logger.writeToFile(f'[AIScannerManager.setupPayment] Admin: {admin.userName}, Email: {admin_email}, Host: {cyberpanel_host}')
            
            # Setup payment with AI Scanner API
            self.logger.writeToFile(f'[AIScannerManager.setupPayment] Attempting payment setup for {admin_email} on {cyberpanel_host}')
            setup_data = self.setup_ai_scanner_payment(admin_email, cyberpanel_host)
            
            if setup_data:
                self.logger.writeToFile(f'[AIScannerManager.setupPayment] Payment setup successful for {admin_email}')
                return JsonResponse({
                    'success': True,
                    'payment_url': setup_data['payment_url'],
                    'token': setup_data['token']
                })
            else:
                self.logger.writeToFile(f'[AIScannerManager.setupPayment] Payment setup failed for {admin_email}')
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to setup payment. Please check the logs and try again.'
                })
                
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.setupPayment] Error: {str(e)}')
            return JsonResponse({'success': False, 'error': 'Internal server error'})
    
    def setupComplete(self, request, userID):
        """Handle return from payment setup"""
        try:
            admin = Administrator.objects.get(pk=userID)
            status = request.GET.get('status')
            
            # Log all URL parameters for debugging
            self.logger.writeToFile(f'[AIScannerManager.setupComplete] All URL params: {dict(request.GET)}')
            
            if status == 'success':
                api_key = request.GET.get('api_key')
                balance = request.GET.get('balance', '0.00')
                charged = request.GET.get('charged') == 'true'
                amount = request.GET.get('amount', '0.00')
                
                self.logger.writeToFile(f'[AIScannerManager.setupComplete] API Key: {api_key[:20] if api_key else "None"}...')
                self.logger.writeToFile(f'[AIScannerManager.setupComplete] Balance from URL: {balance}')
                self.logger.writeToFile(f'[AIScannerManager.setupComplete] Charged: {charged}, Amount: {amount}')
                
                if api_key:
                    try:
                        # Convert balance to float with error handling
                        balance_float = float(balance) if balance else 0.0
                        
                        # Update scanner settings
                        scanner_settings, created = AIScannerSettings.objects.get_or_create(
                            admin=admin,
                            defaults={
                                'api_key': api_key,
                                'balance': balance_float,
                                'is_payment_configured': True
                            }
                        )
                        
                        if not created:
                            # Update existing record
                            scanner_settings.api_key = api_key
                            scanner_settings.balance = balance_float
                            scanner_settings.is_payment_configured = True
                            scanner_settings.save()
                            self.logger.writeToFile(f'[AIScannerManager.setupComplete] Updated existing scanner settings')
                        else:
                            self.logger.writeToFile(f'[AIScannerManager.setupComplete] Created new scanner settings')
                        
                        # Verify the save worked
                        scanner_settings.refresh_from_db()
                        self.logger.writeToFile(f'[AIScannerManager.setupComplete] Final state - API Key: {scanner_settings.api_key[:20] if scanner_settings.api_key else "None"}..., Balance: {scanner_settings.balance}, Configured: {scanner_settings.is_payment_configured}')
                        
                        # Success message
                        if charged:
                            messages.success(request, f'Payment setup successful! ${amount} charged to your card. You have ${balance} credit.')
                        else:
                            messages.success(request, f'Payment setup successful! You have ${balance} credit.')
                        
                        self.logger.writeToFile(f'[AIScannerManager] Payment setup completed for {admin.userName} with balance ${balance}')
                        
                    except ValueError as e:
                        self.logger.writeToFile(f'[AIScannerManager.setupComplete] Balance conversion error: {str(e)}')
                        messages.error(request, 'Payment setup completed but balance format invalid.')
                    except Exception as e:
                        self.logger.writeToFile(f'[AIScannerManager.setupComplete] Database save error: {str(e)}')
                        messages.error(request, 'Payment setup completed but failed to save settings.')
                else:
                    self.logger.writeToFile(f'[AIScannerManager.setupComplete] No API key received in success callback')
                    messages.error(request, 'Payment setup completed but API key not received.')
                    
            elif status == 'partial_success':
                # Handle partial success (payment method added but charge failed)
                api_key = request.GET.get('api_key')
                if api_key:
                    try:
                        scanner_settings, created = AIScannerSettings.objects.get_or_create(
                            admin=admin,
                            defaults={
                                'api_key': api_key,
                                'balance': 0.0,
                                'is_payment_configured': True
                            }
                        )
                        
                        if not created:
                            scanner_settings.api_key = api_key
                            scanner_settings.is_payment_configured = True
                            scanner_settings.save()
                        
                        messages.warning(request, 'Payment method added but initial charge failed. Please add funds manually.')
                        self.logger.writeToFile(f'[AIScannerManager] Partial payment setup for {admin.userName}')
                    except Exception as e:
                        self.logger.writeToFile(f'[AIScannerManager.setupComplete] Partial success save error: {str(e)}')
                        messages.error(request, 'Payment method setup partially failed.')
                else:
                    messages.error(request, 'Payment method setup failed - no API key received.')
                    
            elif status in ['failed', 'cancelled', 'error']:
                error = request.GET.get('error', 'Payment setup failed')
                messages.error(request, f'Payment setup failed: {error}')
                self.logger.writeToFile(f'[AIScannerManager] Payment setup failed for {admin.userName}: {error}')
            
            return redirect('aiScannerHome')
            
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.setupComplete] Error: {str(e)}')
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
                vps_key_data = self.get_or_create_vps_api_key(server_ip)

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
            
            if not domain:
                return JsonResponse({'success': False, 'error': 'Domain is required'})
            
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
            callback_url = f"https://{request.get_host()}/api/ai-scanner/callback"
            file_access_base_url = f"https://{request.get_host()}/api/ai-scanner/"
            
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
                        vps_key_data = self.get_or_create_vps_api_key(server_ip)
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
                    vps_key_data = self.get_or_create_vps_api_key(server_ip)
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
                self.logger.writeToFile(f'[AIScannerManager.addPaymentMethod] Payment method setup successful for {admin_email}')
                return JsonResponse({
                    'success': True,
                    'setup_url': setup_data['setup_url'],
                    'token': setup_data.get('token', '')
                })
            else:
                self.logger.writeToFile(f'[AIScannerManager.addPaymentMethod] Payment method setup failed for {admin_email}')
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
            
            # Log all URL parameters for debugging
            self.logger.writeToFile(f'[AIScannerManager.paymentMethodComplete] All URL params: {dict(request.GET)}')
            
            if status == 'success':
                payment_method_id = request.GET.get('payment_method_id')
                card_last4 = request.GET.get('card_last4')
                card_brand = request.GET.get('card_brand')
                
                self.logger.writeToFile(f'[AIScannerManager.paymentMethodComplete] Payment method added: {payment_method_id} ({card_brand} ****{card_last4})')
                
                if payment_method_id:
                    messages.success(request, f'Payment method added successfully! New {card_brand} card ending in {card_last4}.')
                    self.logger.writeToFile(f'[AIScannerManager] Payment method added for {admin.userName}: {card_brand} ****{card_last4}')
                else:
                    messages.success(request, 'Payment method added successfully!')
                    
            elif status in ['failed', 'cancelled', 'error']:
                error = request.GET.get('error', 'Failed to add payment method')
                messages.error(request, f'Failed to add payment method: {error}')
                self.logger.writeToFile(f'[AIScannerManager] Payment method add failed for {admin.userName}: {error}')
            
            return redirect('aiScannerHome')
            
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.paymentMethodComplete] Error: {str(e)}')
            messages.error(request, 'An error occurred while adding payment method.')
            return redirect('aiScannerHome')
    
    def scanCallback(self, request):
        """Handle scan results callback from AI Scanner API"""
        try:
            if request.method != 'POST':
                return JsonResponse({'success': False, 'error': 'Invalid request method'})
            
            data = json.loads(request.body)
            scan_id = data.get('scan_id')
            status = data.get('status')
            
            if not scan_id:
                return JsonResponse({'success': False, 'error': 'Scan ID required'})
            
            # Find scan history record
            try:
                scan_history = ScanHistory.objects.get(scan_id=scan_id)
            except ScanHistory.DoesNotExist:
                self.logger.writeToFile(f'[AIScannerManager.scanCallback] Scan not found: {scan_id}')
                return JsonResponse({'success': False, 'error': 'Scan not found'})
            
            # Update scan status and results
            scan_history.status = status
            scan_history.completed_at = timezone.now()
            
            if status == 'completed':
                findings = data.get('findings', [])
                summary = data.get('summary', {})
                cost_usd = data.get('cost_usd', 0)
                files_scanned = data.get('files_scanned', 0)
                
                scan_history.set_findings(findings)
                scan_history.set_summary(summary)
                scan_history.cost_usd = cost_usd
                scan_history.files_scanned = files_scanned
                scan_history.issues_found = len(findings)
                
                # Update user balance
                scanner_settings = scan_history.admin.ai_scanner_settings
                if cost_usd and scanner_settings.balance >= cost_usd:
                    scanner_settings.balance -= cost_usd
                    scanner_settings.save()
                
                self.logger.writeToFile(f'[AIScannerManager] Scan completed: {scan_id}, Cost: ${cost_usd}, Issues: {len(findings)}')
                
            elif status == 'failed':
                error_message = data.get('error', 'Scan failed')
                scan_history.error_message = error_message
                self.logger.writeToFile(f'[AIScannerManager] Scan failed: {scan_id}, Error: {error_message}')
            
            scan_history.save()
            
            # Deactivate file access tokens
            FileAccessToken.objects.filter(scan_history=scan_history).update(is_active=False)
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.scanCallback] Error: {str(e)}')
            return JsonResponse({'success': False, 'error': 'Internal server error'})
    
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
    
    def setup_ai_scanner_payment(self, user_email, cyberpanel_host):
        """Setup payment method with AI Scanner API"""
        try:
            payload = {
                'email': user_email,
                'domain': cyberpanel_host.split(':')[0],  # Send domain without port
                'return_url': f'https://{cyberpanel_host}/aiscanner/setup-complete/'  # Include port in URL
            }
            
            self.logger.writeToFile(f'[AIScannerManager.setup_ai_scanner_payment] Sending request to: {self.AI_SCANNER_API_BASE}/cyberpanel/setup-payment/')
            self.logger.writeToFile(f'[AIScannerManager.setup_ai_scanner_payment] Payload: {payload}')
            
            response = requests.post(
                f'{self.AI_SCANNER_API_BASE}/cyberpanel/setup-payment/',
                json=payload,
                timeout=10
            )
            
            self.logger.writeToFile(f'[AIScannerManager.setup_ai_scanner_payment] Response status: {response.status_code}')
            self.logger.writeToFile(f'[AIScannerManager.setup_ai_scanner_payment] Response content: {response.text}')
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return {
                        'payment_url': data['payment_url'],
                        'token': data['token']
                    }
                else:
                    self.logger.writeToFile(f'[AIScannerManager.setup_ai_scanner_payment] API returned success=false: {data.get("error", "Unknown error")}')
            else:
                self.logger.writeToFile(f'[AIScannerManager.setup_ai_scanner_payment] Non-200 status code: {response.status_code}')
            
            return None
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.setup_ai_scanner_payment] Exception: {str(e)}')
            return None
    
    def get_account_balance(self, api_key):
        """Get current account balance"""
        try:
            self.logger.writeToFile(f'[AIScannerManager.get_account_balance] Requesting balance from: {self.AI_SCANNER_API_BASE}/api/account/balance/')
            
            response = requests.get(
                f'{self.AI_SCANNER_API_BASE}/api/account/balance/',
                headers={'X-API-Key': api_key},
                timeout=10
            )
            
            self.logger.writeToFile(f'[AIScannerManager.get_account_balance] Response status: {response.status_code}')
            self.logger.writeToFile(f'[AIScannerManager.get_account_balance] Response content: {response.text}')
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # Use the new balance_usd field from flexible API
                    balance = float(data.get('balance_usd', data.get('balance', 0)))
                    auth_method = data.get('authenticated_via', 'unknown')
                    self.logger.writeToFile(f'[AIScannerManager.get_account_balance] Parsed balance: {balance} (auth: {auth_method})')
                    return balance
                else:
                    # Even failed responses now include balance_usd hint
                    balance_hint = data.get('balance_usd', 0)
                    self.logger.writeToFile(f'[AIScannerManager.get_account_balance] API returned success=false: {data.get("error", "Unknown error")} (balance hint: {balance_hint})')
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
            self.logger.writeToFile(f'[AIScannerManager.submit_wordpress_scan] Payload: {payload}')
            
            response = requests.post(
                f'{self.AI_SCANNER_API_BASE}/api/scan/submit-v2/',
                headers={'X-API-Key': api_key},
                json=payload,
                timeout=10
            )
            
            self.logger.writeToFile(f'[AIScannerManager.submit_wordpress_scan] Response status: {response.status_code}')
            self.logger.writeToFile(f'[AIScannerManager.submit_wordpress_scan] Response content: {response.text}')
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    platform_scan_id = data.get('scan_id')
                    self.logger.writeToFile(f'[AIScannerManager.submit_wordpress_scan] Platform assigned scan ID: {platform_scan_id}')
                    return platform_scan_id
                else:
                    self.logger.writeToFile(f'[AIScannerManager.submit_wordpress_scan] Platform returned success=false: {data.get("error", "Unknown error")}')
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
                data = response.json()
                self.logger.writeToFile(f'[AIScannerManager.check_vps_free_scans] Response data: {data}')
                return data
            else:
                self.logger.writeToFile(f'[AIScannerManager.check_vps_free_scans] API error: {response.text}')
                return {'success': False, 'is_vps': False, 'error': 'API call failed'}
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.check_vps_free_scans] Error: {str(e)}')
            return {'success': False, 'is_vps': False, 'error': str(e)}

    def setup_add_payment_method(self, api_key, user_email, cyberpanel_host):
        """Setup additional payment method with AI Scanner API"""
        try:
            payload = {
                'domain': cyberpanel_host.split(':')[0],  # Send domain without port
                'return_url': f'https://{cyberpanel_host}/aiscanner/payment-method-complete/',  # Include port in URL
                'action': 'add_payment_method'  # Indicate this is adding a payment method, not initial setup
            }
            
            self.logger.writeToFile(f'[AIScannerManager.setup_add_payment_method] Sending request to: {self.AI_SCANNER_API_BASE}/cyberpanel/add-payment-method/')
            self.logger.writeToFile(f'[AIScannerManager.setup_add_payment_method] Payload: {payload}')
            
            response = requests.post(
                f'{self.AI_SCANNER_API_BASE}/cyberpanel/add-payment-method/',
                headers={'X-API-Key': api_key},
                json=payload,
                timeout=10
            )
            
            self.logger.writeToFile(f'[AIScannerManager.setup_add_payment_method] Response status: {response.status_code}')
            self.logger.writeToFile(f'[AIScannerManager.setup_add_payment_method] Response content: {response.text}')
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return {
                        'setup_url': data['setup_url'],
                        'token': data.get('token', '')
                    }
                else:
                    self.logger.writeToFile(f'[AIScannerManager.setup_add_payment_method] API returned success=false: {data.get("error", "Unknown error")}')
            else:
                self.logger.writeToFile(f'[AIScannerManager.setup_add_payment_method] Non-200 status code: {response.status_code}')
            
            return None
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.setup_add_payment_method] Exception: {str(e)}')
            return None

    def get_or_create_vps_api_key(self, server_ip):
        """Get API key for VPS free scans from platform"""
        try:
            payload = {'server_ip': server_ip}
            
            self.logger.writeToFile(f'[AIScannerManager.get_or_create_vps_api_key] Requesting VPS API key for IP: {server_ip}')
            
            response = requests.post(
                f'{self.AI_SCANNER_API_BASE}/api/vps/generate-api-key/',
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            self.logger.writeToFile(f'[AIScannerManager.get_or_create_vps_api_key] Response status: {response.status_code}')
            self.logger.writeToFile(f'[AIScannerManager.get_or_create_vps_api_key] Response content: {response.text}')
            
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
                    self.logger.writeToFile(f'[AIScannerManager.get_or_create_vps_api_key] API returned success=false: {data.get("error", "Unknown error")}')
            else:
                self.logger.writeToFile(f'[AIScannerManager.get_or_create_vps_api_key] Non-200 status code: {response.status_code}')
            
            return None
        except Exception as e:
            self.logger.writeToFile(f'[AIScannerManager.get_or_create_vps_api_key] Exception: {str(e)}')
            return None

    def generate_file_access_token(self):
        """Generate secure file access token"""
        return f'cp_{secrets.token_urlsafe(32)}'