import json
import requests
from django.http import JsonResponse
from loginSystem.models import Administrator
from plogical.acl import ACLManager
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.httpProc import httpProc
from plogical.processUtilities import ProcessUtilities
from .models import CyberMailAccount, CyberMailDomain


class EmailDeliveryManager:

    PLATFORM_URL = 'https://platform.cyberpersons.com/email/cp/'

    def __init__(self):
        self.logger = logging

    def _apiCall(self, endpoint, data=None, apiKey=None):
        """POST to platform API. If apiKey provided, sends Bearer auth."""
        headers = {'Content-Type': 'application/json'}
        if apiKey:
            headers['Authorization'] = 'Bearer %s' % apiKey
        url = self.PLATFORM_URL + endpoint
        try:
            resp = requests.post(url, json=data or {}, headers=headers, timeout=30)
            return resp.json()
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Platform API request timed out.'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': 'Could not connect to CyberMail platform.'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _accountApiCall(self, account, endpoint, data=None):
        """API call using a CyberMailAccount's stored per-user key."""
        if not account.api_key:
            return {'success': False, 'error': 'No API key found. Please reconnect your account.'}
        return self._apiCall(endpoint, data, apiKey=account.api_key)

    def home(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)

            isConnected = False
            try:
                account = CyberMailAccount.objects.get(admin=admin)
                isConnected = account.is_connected
            except CyberMailAccount.DoesNotExist:
                pass

            data = {
                'isConnected': isConnected,
                'adminEmail': admin.email,
                'adminName': admin.firstName if hasattr(admin, 'firstName') else admin.userName,
            }

            proc = httpProc(request, 'emailDelivery/index.html', data, 'admin')
            return proc.render()

        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.home] Error: %s' % str(e))
            proc = httpProc(request, 'emailDelivery/index.html', {
                'isConnected': False,
                'adminEmail': '',
                'adminName': '',
            })
            return proc.render()

    def getStatus(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)

            result = self._accountApiCall(account, 'api/account/', {'email': account.email})
            if not result.get('success', False):
                return JsonResponse({'success': False, 'error': result.get('error', 'Failed to get account status')})

            accountData = result.get('data', {})

            # Platform returns plan info nested under data.plan
            planInfo = accountData.get('plan', {})
            if planInfo.get('name'):
                account.plan_name = planInfo['name']
                account.plan_slug = planInfo.get('slug', account.plan_slug)
                account.emails_per_month = planInfo.get('emails_per_month', account.emails_per_month)
                account.save()

            # Sync domains from platform to local DB
            try:
                domainResult = self._accountApiCall(account, 'api/domains/list/', {'email': account.email})
                if domainResult.get('success', False):
                    platformDomains = domainResult.get('data', {}).get('domains', [])
                    for pd in platformDomains:
                        try:
                            cmDomain = CyberMailDomain.objects.get(account=account, domain=pd['domain'])
                            cmDomain.status = pd.get('status', cmDomain.status)
                            cmDomain.spf_verified = pd.get('spf_verified', False)
                            cmDomain.dkim_verified = pd.get('dkim_verified', False)
                            cmDomain.dmarc_verified = pd.get('dmarc_verified', False)
                            cmDomain.save()
                        except CyberMailDomain.DoesNotExist:
                            CyberMailDomain.objects.create(
                                account=account,
                                domain=pd['domain'],
                                platform_domain_id=pd.get('id'),
                                status=pd.get('status', 'pending'),
                                spf_verified=pd.get('spf_verified', False),
                                dkim_verified=pd.get('dkim_verified', False),
                                dmarc_verified=pd.get('dmarc_verified', False),
                            )
            except Exception as e:
                self.logger.writeToFile('[EmailDeliveryManager.getStatus] Domain sync error: %s' % str(e))

            domains = list(CyberMailDomain.objects.filter(account=account).values(
                'id', 'domain', 'platform_domain_id', 'status',
                'spf_verified', 'dkim_verified', 'dmarc_verified', 'dns_configured'
            ))

            return JsonResponse({
                'success': True,
                'account': {
                    'email': account.email,
                    'plan_name': account.plan_name,
                    'plan_slug': account.plan_slug,
                    'emails_per_month': account.emails_per_month,
                    'relay_enabled': account.relay_enabled,
                    'smtp_host': account.smtp_host,
                    'smtp_port': account.smtp_port,
                },
                'domains': domains,
                'stats': {
                    'emails_sent': accountData.get('emails_sent_this_month', 0),
                    'reputation_score': accountData.get('reputation_score', 0),
                },
            })

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.getStatus] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def connect(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            data = json.loads(request.body)
            password = data.get('password', '')
            email = data.get('email', admin.email)

            if not password:
                return JsonResponse({'success': False, 'error': 'Password is required'})

            fullName = admin.firstName if hasattr(admin, 'firstName') and admin.firstName else admin.userName

            # Public endpoint — no API key needed for registration
            result = self._apiCall('api/register/', {
                'email': email,
                'password': password,
                'full_name': fullName,
            })

            if not result.get('success', False):
                return JsonResponse({'success': False, 'error': result.get('error', 'Registration failed')})

            accountData = result.get('data', {})
            apiKey = accountData.get('api_key', '')

            account, created = CyberMailAccount.objects.get_or_create(
                admin=admin,
                defaults={
                    'email': email,
                    'api_key': apiKey,
                    'platform_account_id': accountData.get('account_id'),
                    'plan_name': accountData.get('plan_name', 'Free'),
                    'plan_slug': accountData.get('plan_slug', 'free'),
                    'emails_per_month': accountData.get('emails_per_month', 15000),
                    'is_connected': True,
                }
            )

            if not created:
                account.email = email
                account.api_key = apiKey
                account.platform_account_id = accountData.get('account_id')
                account.plan_name = accountData.get('plan_name', 'Free')
                account.plan_slug = accountData.get('plan_slug', 'free')
                account.emails_per_month = accountData.get('emails_per_month', 15000)
                account.is_connected = True
                # Reset relay fields from previous account
                account.smtp_credential_id = None
                account.smtp_username = ''
                account.relay_enabled = False
                account.save()
                # Clear stale domains from previous account
                CyberMailDomain.objects.filter(account=account).delete()

            return JsonResponse({'success': True, 'message': 'Connected to CyberMail successfully'})

        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.connect] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def addDomain(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)
            data = json.loads(request.body)
            domainName = data.get('domain', '')

            if not domainName:
                return JsonResponse({'success': False, 'error': 'Domain name is required'})

            result = self._accountApiCall(account, 'api/domains/add/', {
                'email': account.email,
                'domain': domainName,
            })

            if not result.get('success', False):
                return JsonResponse({'success': False, 'error': result.get('error', 'Failed to add domain')})

            domainData = result.get('data', {})

            cmDomain, created = CyberMailDomain.objects.get_or_create(
                account=account,
                domain=domainName,
                defaults={
                    'platform_domain_id': domainData.get('id') or domainData.get('domain_id'),
                    'status': domainData.get('status', 'pending'),
                }
            )
            if not created:
                cmDomain.platform_domain_id = domainData.get('id') or domainData.get('domain_id')
                cmDomain.status = domainData.get('status', 'pending')
                cmDomain.save()

            # Auto-configure DNS if domain exists in PowerDNS
            dnsResult = self._autoConfigureDnsForDomain(account, domainName)

            return JsonResponse({
                'success': True,
                'message': 'Domain added successfully',
                'dns_configured': dnsResult.get('success', False),
                'dns_message': dnsResult.get('message', ''),
            })

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.addDomain] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def _autoConfigureDnsForDomain(self, account, domainName):
        try:
            from dns.models import Domains as dnsDomains
            from plogical.dnsUtilities import DNS

            try:
                zone = dnsDomains.objects.get(name=domainName)
            except dnsDomains.DoesNotExist:
                return {'success': False, 'message': 'Domain not found in PowerDNS. Please add DNS records manually.'}

            recordsResult = self._accountApiCall(account, 'api/domains/dns-records/', {
                'email': account.email,
                'domain': domainName,
            })

            if not recordsResult.get('success', False):
                return {'success': False, 'message': 'Could not fetch DNS records from platform.'}

            records = recordsResult.get('data', {}).get('records', [])
            added = 0
            for rec in records:
                try:
                    # Platform returns 'host' for the DNS hostname, 'type' for record type, 'value' for content
                    recordHost = rec.get('host', '')
                    recordType = rec.get('type', '')
                    recordValue = rec.get('value', '')

                    if not recordHost or not recordType or not recordValue:
                        continue

                    DNS.createDNSRecord(
                        zone,
                        recordHost,
                        recordType,
                        recordValue,
                        rec.get('priority', 0),
                        rec.get('ttl', 3600)
                    )
                    added += 1
                except Exception as e:
                    self.logger.writeToFile('[EmailDeliveryManager._autoConfigureDnsForDomain] Record error: %s' % str(e))

            try:
                cmDomain = CyberMailDomain.objects.get(account=account, domain=domainName)
                cmDomain.dns_configured = True
                cmDomain.save()
            except CyberMailDomain.DoesNotExist:
                pass

            return {'success': True, 'message': '%d DNS records configured automatically.' % added}

        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager._autoConfigureDnsForDomain] Error: %s' % str(e))
            return {'success': False, 'message': str(e)}

    def verifyDomain(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)
            data = json.loads(request.body)
            domainName = data.get('domain', '')

            result = self._accountApiCall(account, 'api/domains/verify/', {
                'email': account.email,
                'domain': domainName,
            })

            if not result.get('success', False):
                return JsonResponse({'success': False, 'error': result.get('error', 'Verification failed')})

            verifyData = result.get('data', {})

            # Platform returns: spf, dkim, dmarc, all_verified, verification_token
            allVerified = verifyData.get('all_verified', False)

            try:
                cmDomain = CyberMailDomain.objects.get(account=account, domain=domainName)
                cmDomain.status = 'verified' if allVerified else 'pending'
                cmDomain.spf_verified = verifyData.get('spf', False)
                cmDomain.dkim_verified = verifyData.get('dkim', False)
                cmDomain.dmarc_verified = verifyData.get('dmarc', False)
                cmDomain.save()
            except CyberMailDomain.DoesNotExist:
                pass

            return JsonResponse({'success': True, 'data': {
                'status': 'verified' if allVerified else 'pending',
                'spf_verified': verifyData.get('spf', False),
                'dkim_verified': verifyData.get('dkim', False),
                'dmarc_verified': verifyData.get('dmarc', False),
                'all_verified': allVerified,
            }})

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.verifyDomain] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def listDomains(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)

            result = self._accountApiCall(account, 'api/domains/list/', {'email': account.email})
            if not result.get('success', False):
                return JsonResponse({'success': False, 'error': result.get('error', 'Failed to list domains')})

            platformDomains = result.get('data', {}).get('domains', [])

            for pd in platformDomains:
                try:
                    cmDomain = CyberMailDomain.objects.get(account=account, domain=pd['domain'])
                    cmDomain.status = pd.get('status', cmDomain.status)
                    cmDomain.spf_verified = pd.get('spf_verified', False)
                    cmDomain.dkim_verified = pd.get('dkim_verified', False)
                    cmDomain.dmarc_verified = pd.get('dmarc_verified', False)
                    cmDomain.save()
                except CyberMailDomain.DoesNotExist:
                    CyberMailDomain.objects.create(
                        account=account,
                        domain=pd['domain'],
                        platform_domain_id=pd.get('id'),
                        status=pd.get('status', 'pending'),
                        spf_verified=pd.get('spf_verified', False),
                        dkim_verified=pd.get('dkim_verified', False),
                        dmarc_verified=pd.get('dmarc_verified', False),
                    )

            domains = list(CyberMailDomain.objects.filter(account=account).values(
                'id', 'domain', 'platform_domain_id', 'status',
                'spf_verified', 'dkim_verified', 'dmarc_verified', 'dns_configured'
            ))

            return JsonResponse({'success': True, 'domains': domains})

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.listDomains] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def getDnsRecords(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)
            data = json.loads(request.body)
            domainName = data.get('domain', '')

            result = self._accountApiCall(account, 'api/domains/dns-records/', {
                'email': account.email,
                'domain': domainName,
            })

            return JsonResponse(result)

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.getDnsRecords] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def removeDomain(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)
            data = json.loads(request.body)
            domainName = data.get('domain', '')

            result = self._accountApiCall(account, 'api/domains/remove/', {
                'email': account.email,
                'domain': domainName,
            })

            if not result.get('success', False):
                return JsonResponse({'success': False, 'error': result.get('error', 'Failed to remove domain')})

            CyberMailDomain.objects.filter(account=account, domain=domainName).delete()

            return JsonResponse({'success': True, 'message': 'Domain removed successfully'})

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.removeDomain] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def autoConfigureDns(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)
            data = json.loads(request.body)
            domainName = data.get('domain', '')

            result = self._autoConfigureDnsForDomain(account, domainName)

            return JsonResponse({
                'success': result.get('success', False),
                'message': result.get('message', ''),
            })

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.autoConfigureDns] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def createSmtpCredential(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)
            data = json.loads(request.body)

            result = self._accountApiCall(account, 'api/smtp/create/', {
                'email': account.email,
                'description': data.get('description', ''),
            })

            return JsonResponse(result)

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.createSmtpCredential] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def listSmtpCredentials(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)

            result = self._accountApiCall(account, 'api/smtp/list/', {'email': account.email})

            # Normalize: platform returns 'id' per credential, JS expects 'credential_id'
            if result.get('success') and result.get('data', {}).get('credentials'):
                for cred in result['data']['credentials']:
                    if 'id' in cred and 'credential_id' not in cred:
                        cred['credential_id'] = cred['id']

            return JsonResponse(result)

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.listSmtpCredentials] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def rotateSmtpPassword(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)
            data = json.loads(request.body)

            result = self._accountApiCall(account, 'api/smtp/rotate/', {
                'email': account.email,
                'credential_id': data.get('credential_id'),
            })

            # Normalize: platform returns 'new_password', JS expects 'password'
            if result.get('success') and result.get('data', {}).get('new_password'):
                result['data']['password'] = result['data'].pop('new_password')

            return JsonResponse(result)

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.rotateSmtpPassword] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def deleteSmtpCredential(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)
            data = json.loads(request.body)

            result = self._accountApiCall(account, 'api/smtp/delete/', {
                'email': account.email,
                'credential_id': data.get('credential_id'),
            })

            if result.get('success', False):
                if account.smtp_credential_id == data.get('credential_id'):
                    account.smtp_credential_id = None
                    account.smtp_username = ''
                    account.save()

            return JsonResponse(result)

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.deleteSmtpCredential] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def enableRelay(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)

            # Create SMTP credential if none exists
            if not account.smtp_credential_id:
                result = self._accountApiCall(account, 'api/smtp/create/', {
                    'email': account.email,
                    'description': 'CyberPanel Relay',
                })
                if not result.get('success', False):
                    return JsonResponse({'success': False, 'error': result.get('error', 'Failed to create SMTP credential')})

                credData = result.get('data', {})
                account.smtp_credential_id = credData.get('credential_id')
                account.smtp_username = credData.get('username', '')
                account.save()

                smtpPassword = credData.get('password', '')
            else:
                # Rotate to get a fresh password
                result = self._accountApiCall(account, 'api/smtp/rotate/', {
                    'email': account.email,
                    'credential_id': account.smtp_credential_id,
                })
                if not result.get('success', False):
                    return JsonResponse({'success': False, 'error': result.get('error', 'Failed to get SMTP password')})

                smtpPassword = result.get('data', {}).get('new_password', '')

            # Configure Postfix relay via mailUtilities subprocess
            import shlex
            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/mailUtilities.py" \
                       " configureRelayHost --smtpHost %s --smtpPort %s --smtpUser %s --smtpPassword %s" % (
                shlex.quote(str(account.smtp_host)),
                shlex.quote(str(account.smtp_port)),
                shlex.quote(str(account.smtp_username)),
                shlex.quote(str(smtpPassword))
            )
            output = ProcessUtilities.outputExecutioner(execPath)

            if output and '1,None' in output:
                account.relay_enabled = True
                account.save()
                return JsonResponse({'success': True, 'message': 'SMTP relay enabled successfully'})
            else:
                return JsonResponse({'success': False, 'error': 'Failed to configure Postfix relay: %s' % str(output)})

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.enableRelay] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def disableRelay(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/mailUtilities.py removeRelayHost"
            output = ProcessUtilities.outputExecutioner(execPath)

            if output and '1,None' in output:
                account.relay_enabled = False
                account.save()
                return JsonResponse({'success': True, 'message': 'SMTP relay disabled successfully'})
            else:
                return JsonResponse({'success': False, 'error': 'Failed to remove Postfix relay: %s' % str(output)})

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.disableRelay] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def getStats(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)

            result = self._accountApiCall(account, 'api/stats/', {'email': account.email})

            # Normalize for JS: platform returns data.total_sent etc at top level
            if result.get('success') and result.get('data'):
                d = result['data']
                result['data'] = {
                    'total_sent': d.get('total_sent', 0),
                    'delivered': d.get('delivered', 0),
                    'bounced': d.get('bounced', 0),
                    'failed': d.get('failed', 0),
                    'delivery_rate': d.get('delivery_rate', 0),
                }

            return JsonResponse(result)

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.getStats] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def getDomainStats(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)

            result = self._accountApiCall(account, 'api/stats/domains/', {'email': account.email})

            # Normalize: platform returns data.domains as dict, JS expects array
            if result.get('success') and result.get('data'):
                domainsData = result['data'].get('domains', {})
                if isinstance(domainsData, dict):
                    domainsList = []
                    for domainName, stats in domainsData.items():
                        entry = {'domain': domainName}
                        if isinstance(stats, dict):
                            entry.update(stats)
                        domainsList.append(entry)
                    result['data']['domains'] = domainsList

            return JsonResponse(result)

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.getDomainStats] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def getLogs(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)
            data = json.loads(request.body)

            result = self._accountApiCall(account, 'api/logs/', {
                'email': account.email,
                'page': data.get('page', 1),
                'per_page': data.get('per_page', 50),
                'status': data.get('status', ''),
                'from_domain': data.get('from_domain', ''),
                'days': data.get('days', 7),
            })

            # Normalize field names and pagination
            if result.get('success') and result.get('data'):
                pagination = result['data'].get('pagination', {})
                result['data']['total_pages'] = pagination.get('total_pages', 1)
                result['data']['page'] = pagination.get('page', 1)

                # Map platform field names to what JS/template expects
                logs = result['data'].get('logs', [])
                for log in logs:
                    log['date'] = log.get('queued_at', '')
                    log['from'] = log.get('from_email', '')
                    log['to'] = log.get('to_email', '')

            return JsonResponse(result)

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.getLogs] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def disconnect(self, request, userID):
        try:
            admin = Administrator.objects.get(pk=userID)
            account = CyberMailAccount.objects.get(admin=admin, is_connected=True)

            # Disable relay first if enabled
            if account.relay_enabled:
                execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/mailUtilities.py removeRelayHost"
                ProcessUtilities.outputExecutioner(execPath)

            account.is_connected = False
            account.relay_enabled = False
            account.api_key = ''
            account.smtp_credential_id = None
            account.smtp_username = ''
            account.platform_account_id = None
            account.save()

            # Remove local domain records
            CyberMailDomain.objects.filter(account=account).delete()

            return JsonResponse({'success': True, 'message': 'Disconnected from CyberMail'})

        except CyberMailAccount.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Account not connected'})
        except Exception as e:
            self.logger.writeToFile('[EmailDeliveryManager.disconnect] Error: %s' % str(e))
            return JsonResponse({'success': False, 'error': str(e)})

    def checkStatus(self, request, userID):
        try:
            result = self._apiCall('api/health/', {})
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
