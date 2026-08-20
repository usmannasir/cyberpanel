# -*- coding: utf-8 -*-


from django.shortcuts import render, redirect
from .models import Administrator
from plogical import hashPassword
import json
from packages.models import Package
from baseTemplate.models import version
from plogical.getSystemInformation import SystemInformation
from .models import ACL
from plogical.acl import ACLManager
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings
from django.http import HttpResponse
from django.utils import translation
# Create your views here.

VERSION = '2.5.5'
BUILD = 'dev'


def verifyLogin(request):
    try:
        userID = request.session['userID']
        data = {'userID': userID, 'loginStatus': 1, 'error_message': "None"}
        json_data = json.dumps(data)
        return HttpResponse(json_data)
    except KeyError:
        username = "not logged in"
        password = ""

        try:
            if request.method == "POST":
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    data = {'userID': 0, 'loginStatus': 0, 'error_message': 'Invalid request format'}
                    json_data = json.dumps(data)
                    return HttpResponse(json_data)

                username = data.get('username', '')
                password = data.get('password', '')

                # Secure logging (no sensitive data)
                from plogical.errorSanitizer import secure_log_error
                secure_log_error(Exception(f"Login attempt for user: {username}"), 'verifyLogin')

                try:
                    language_selection = data.get('languageSelection', 'english')
                    if language_selection == "English":
                        user_Language = "en"
                    elif language_selection == "Chinese":
                        user_Language = "cn"
                    elif language_selection == "Bulgarian":
                        user_Language = "br"
                    elif language_selection == "Portuguese":
                        user_Language = "pt"
                    elif language_selection == "Japanese":
                        user_Language = "ja"
                    elif language_selection == "Bosnian":
                        user_Language = "bs"
                    elif language_selection == "Greek":
                        user_Language = "gr"
                    elif language_selection == "Russian":
                        user_Language = "ru"
                    elif language_selection == "Turkish":
                        user_Language = "tr"
                    elif language_selection == "Spanish":
                        user_Language = "es"
                    elif language_selection == "French":
                        user_Language = "fr"
                    elif language_selection == "Polish":
                        user_Language = "pl"
                    elif language_selection == "Vietnamese":
                        user_Language = "vi"
                    elif language_selection == "Italian":
                        user_Language = "it"
                    elif language_selection == "German":
                        user_Language = "de"
                    elif language_selection == "Indonesian":
                        user_Language = "id"
                    elif language_selection == "Bangla":
                        user_Language = "bn"
                    else:
                        user_Language = 'en'

                    translation.activate(user_Language)
                    response = HttpResponse()
                    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_Language)
                except:
                    user_Language = 'en'
                    translation.activate(user_Language)
                    response = HttpResponse()
                    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_Language)

            from plogical.usernameUtils import resolve_administrator_by_login_name, GENERIC_AUTH_FAIL
            admin, exact_match = resolve_administrator_by_login_name(username)
            if not admin:
                data = {'userID': 0, 'loginStatus': 0, 'error_message': GENERIC_AUTH_FAIL}
                json_data = json.dumps(data)
                return HttpResponse(json_data)
            # Username match is case-sensitive (Admin != admin). Give a clear hint
            # when the account exists under a different capitalisation.
            if not exact_match:
                data = {
                    'userID': 0,
                    'loginStatus': 0,
                    'error_message': 'Username is case-sensitive. Check capitalisation (e.g. Admin).',
                }
                json_data = json.dumps(data)
                return HttpResponse(json_data)

            if admin.state == 'SUSPENDED':
                data = {'userID': 0, 'loginStatus': 0, 'error_message': 'Account currently suspended.'}
                json_data = json.dumps(data)
                return HttpResponse(json_data)

            if admin.twoFA:
                try:
                    twoinit = request.session['twofa']
                except:
                    request.session['twofa'] = 0
                    request.session.save()
                    data = {'userID': admin.pk, 'loginStatus': 2, 'error_message': "None"}
                    json_data = json.dumps(data)
                    response.write(json_data)
                    return response

            password_check_result = hashPassword.check_password(admin.password, password)

            if password_check_result:
                try:
                    from plogical import hashPassword as hp
                    if hp.needs_password_rehash(admin.password):
                        admin.password = hp.hash_password(password)
                        admin.save(update_fields=['password'])
                except Exception:
                    pass
                if admin.twoFA:
                    if request.session.get('twofa', 1) == 0:
                        import pyotp
                        totp = pyotp.TOTP(admin.secretKey)
                        twofa_code = data.get('twofa', '')
                        if not twofa_code or not totp.verify(str(twofa_code).strip(), valid_window=1):
                            request.session['twofa'] = 0
                            request.session.save()
                            data = {'userID': 0, 'loginStatus': 0, 'error_message': "Invalid verification code."}
                            json_data = json.dumps(data)
                            response.write(json_data)
                            return response
                        # Clear the session flag after successful 2FA verification
                        del request.session['twofa']

                # Rotate session key on privilege elevation (mitigate fixation).
                try:
                    request.session.cycle_key()
                except Exception:
                    pass

                request.session['userID'] = admin.pk

                ipAddr = request.META.get('HTTP_CF_CONNECTING_IP')
                if ipAddr is None:
                    ipAddr = request.META.get('REMOTE_ADDR')

                if ipAddr.find(':') > -1:
                    ipAddr = ':'.join(ipAddr.split(':')[:3])
                    request.session['ipAddr'] = ipAddr
                else:
                    request.session['ipAddr'] = ipAddr

                remember = bool(data.get('rememberMe'))
                request.session.set_expiry(2592000 if remember else 43200)
                try:
                    from plogical.sshSecurityWhitelistUtilities import SSHSecurityWhitelistUtilities
                    SSHSecurityWhitelistUtilities.on_successful_panel_login(request, admin)
                except Exception:
                    pass
                request.session.save()
                data = {'userID': admin.pk, 'loginStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data)
                response.write(json_data)
                return response

            else:
                data = {'userID': 0, 'loginStatus': 0, 'error_message': "login failed."}
                json_data = json.dumps(data)
                response.write(json_data)
                return response

        except Exception as e:
            from plogical.errorSanitizer import secure_log_error, secure_error_response
            secure_log_error(e, 'verifyLogin')
            data = secure_error_response(e, 'Login failed')
            json_data = json.dumps(data)
            return HttpResponse(json_data)

def _passkey_login_enabled():
    """Return True only when passkey login should be shown (at least one passkey registered)."""
    try:
        from .webauthn_models import WebAuthnCredential
        return WebAuthnCredential.objects.filter(is_active=True).exists()
    except Exception:
        return False


@ensure_csrf_cookie
def loadLoginPage(request):
    try:
        return _loadLoginPage(request)
    except Exception as e:
        try:
            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
            import traceback
            logging.writeToFile("loadLoginPage error: %s\n%s" % (str(e), traceback.format_exc()))
        except Exception:
            pass
        # User-friendly message for database connection errors
        from django.db.utils import OperationalError
        err_str = str(e).lower()
        if isinstance(e, OperationalError) or 'access denied' in err_str or '1045' in err_str:
            msg = (
                "Database connection failed (Access denied for user 'cyberpanel'@'localhost'). "
                "Check: 1) MariaDB is running (systemctl status mariadb). "
                "2) Password in /etc/cyberpanel/mysqlPassword matches the MySQL user used by the panel. "
                "3) User exists: mysql -u root -p -e \"SELECT User,Host FROM mysql.user WHERE User='cyberpanel';\""
            )
            return HttpResponse(msg, status=503, content_type="text/plain; charset=utf-8")
        try:
            # Minimal cosmetic so template does not break (login.html uses cosmetic.MainDashboardCSS)
            class _MinimalCosmetic:
                MainDashboardCSS = ''
            return render(request, 'loginSystem/login.html', {'cosmetic': _MinimalCosmetic(), 'passkey_login_available': False})
        except Exception:
            return HttpResponse("Server error. Check /home/cyberpanel/error-logs.txt", status=500, content_type="text/plain")


def _loadLoginPage(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        cpuRamDisk = SystemInformation.cpuRamDisk()

        if currentACL['admin'] == 1:
            admin = 1
        else:
            admin = 0

        finaData = {"admin": admin, 'ramUsage': cpuRamDisk['ramUsage'], 'cpuUsage': cpuRamDisk['cpuUsage'],
                    'diskUsage': cpuRamDisk['diskUsage']}

        from baseTemplate.views import renderBase
        return redirect(renderBase)

        #return render(request, 'baseTemplate/homePage.html', finaData)
    except KeyError:
        from firewall.models import FirewallRules

        numberOfAdministrator = Administrator.objects.count()
        password = hashPassword.hash_password('1234567')
        noOfRules = FirewallRules.objects.count()

        if noOfRules == 0:
            newFWRule = FirewallRules(name="panel", proto="tcp", port="8090")
            newFWRule.save()

            newFWRule = FirewallRules(name="http", proto="tcp", port="80")
            newFWRule.save()

            newFWRule = FirewallRules(name="https", proto="tcp", port="443")
            newFWRule.save()

            newFWRule = FirewallRules(name="ftp", proto="tcp", port="21")
            newFWRule.save()

            newFWRule = FirewallRules(name="smtp", proto="tcp", port="25")
            newFWRule.save()

            newFWRule = FirewallRules(name="smtps", proto="tcp", port="587")
            newFWRule.save()

            newFWRule = FirewallRules(name="ssmtp", proto="tcp", port="465")
            newFWRule.save()

            newFWRule = FirewallRules(name="pop3", proto="tcp", port="110")
            newFWRule.save()

            newFWRule = FirewallRules(name="imap", proto="tcp", port="143")
            newFWRule.save()

            newFWRule = FirewallRules(name="simap", proto="tcp", port="993")
            newFWRule.save()

            newFWRule = FirewallRules(name="dns", proto="udp", port="53")
            newFWRule.save()

            newFWRule = FirewallRules(name="dnstcp", proto="tcp", port="53")
            newFWRule.save()

            newFWRule = FirewallRules(name="ftptls", proto="tcp", port="40110-40210")
            newFWRule.save()

            newFWRule = FirewallRules(name="POP3S", proto="tcp", port="995")
            newFWRule.save()

            newFWRule = FirewallRules(name="quic", proto="udp", port="443")
            newFWRule.save()

        if numberOfAdministrator == 0:
            ACLManager.createDefaultACLs()
            acl = ACL.objects.get(name='admin')

            token = hashPassword.generateToken('admin', '1234567')

            email = 'admin@cyberpanel.net'
            admin = Administrator(userName="admin", password=password, type=1, email=email,
                                  firstName="Cyber", lastName="Panel", acl=acl, token=token)
            admin.save()

            vers = version(currentVersion=VERSION, build=BUILD)
            vers.save()

            package = Package(admin=admin, packageName="Default", diskSpace=1000, bandwidth=1000, ftpAccounts=1000,
                              dataBases=1000, emailAccounts=1000, allowedDomains=20)
            package.save()

            ### Load Custom CSS
            try:
                from baseTemplate.models import CyberPanelCosmetic
                cosmetic = CyberPanelCosmetic.objects.get(pk=1)
            except:
                from baseTemplate.models import CyberPanelCosmetic
                cosmetic = CyberPanelCosmetic()
                cosmetic.save()

            passkey_login_available = _passkey_login_enabled()
            return render(request, 'loginSystem/login.html', {'cosmetic': cosmetic, 'passkey_login_available': passkey_login_available})
        else:
            ### Load Custom CSS
            try:
                from baseTemplate.models import CyberPanelCosmetic
                cosmetic = CyberPanelCosmetic.objects.get(pk=1)
            except:
                from baseTemplate.models import CyberPanelCosmetic
                cosmetic = CyberPanelCosmetic()
                cosmetic.save()
            passkey_login_available = _passkey_login_enabled()
            return render(request, 'loginSystem/login.html', {'cosmetic': cosmetic, 'passkey_login_available': passkey_login_available})


@ensure_csrf_cookie
def logout(request):
    try:
        del request.session['userID']
    except KeyError:
        pass
    try:
        from baseTemplate.models import CyberPanelCosmetic
        cosmetic = CyberPanelCosmetic.objects.get(pk=1)
    except Exception:
        class _MinimalCosmetic:
            MainDashboardCSS = ''
        cosmetic = _MinimalCosmetic()
    return render(request, 'loginSystem/login.html', {'cosmetic': cosmetic, 'passkey_login_available': _passkey_login_enabled()})
