# -*- coding: utf-8 -*-
"""
Panel Access settings: configure custom panel domain(s) for CSRF when
the panel is behind a reverse proxy (e.g. https://panel.example.com -> IP:2087).
"""
from django.shortcuts import redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _
from loginSystem.views import loadLoginPage
from plogical.httpProc import httpProc
from plogical.mailUtilities import mailUtilities
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
from plogical.processUtilities import ProcessUtilities
from .apps import get_panel_csrf_origins_file, read_panel_csrf_origins
from websiteFunctions.models import Websites, ChildDomains
import os
import subprocess
import json


def _ensure_origins_dir():
    """Ensure directory for panel_csrf_origins.conf exists."""
    path = get_panel_csrf_origins_file()
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        try:
            os.makedirs(d, mode=0o755)
        except (OSError, IOError):
            pass


def _get_all_domains():
    """Get all domains and subdomains from CyberPanel database."""
    domains = []
    try:
        # Get all main websites
        websites = Websites.objects.filter(state=1).values_list('domain', flat=True)
        domains.extend([domain for domain in websites])
        
        # Get all child domains (subdomains)
        child_domains = ChildDomains.objects.all().values_list('domain', flat=True)
        domains.extend([domain for domain in child_domains])
        
        # Remove duplicates and sort
        domains = sorted(list(set(domains)))
    except Exception:
        pass
    return domains


@require_http_methods(['GET'])
def settings_page(request):
    """Show Panel Access settings page with current custom domains."""
    try:
        request.session['userID']
    except KeyError:
        return redirect(loadLoginPage)
    mailUtilities.checkHome()
    origins = read_panel_csrf_origins()
    all_domains = _get_all_domains()
    data = {
        'origins': origins,
        'origins_text': '\n'.join(origins),
        'config_path': get_panel_csrf_origins_file(),
        'all_domains': json.dumps(all_domains),
        'origins_json': json.dumps(origins),
    }
    proc = httpProc(request, 'panelAccess/settings.html', data, 'admin')
    return proc.render()


@require_http_methods(['POST'])
def save_origins(request):
    """Save custom panel origins (one per line). Admin only. Returns JSON."""
    try:
        # Check session
        try:
            request.session['userID']
        except KeyError:
            return JsonResponse({
                'save': 0,
                'error_message': _('Session expired. Please refresh the page and log in again.'),
            }, status=401)
        
        # Check admin permissions
        try:
            from loginSystem.models import Administrator
            from plogical.acl import ACLManager
            user_id = request.session['userID']
            current_acl = ACLManager.loadedACL(user_id)
            if not current_acl.get('admin'):
                return JsonResponse({
                    'save': 0,
                    'error_message': _('Only administrators can change Panel Access settings.'),
                }, status=403)
        except Exception as e:
            CyberCPLogFileWriter.writeToFile(f"Panel Access: Authorization check error: {str(e)}")
            return JsonResponse({
                'save': 0,
                'error_message': _('Authorization check failed.'),
            }, status=500)
        
        # Handle both old textarea format and new select format
        origins_raw = request.POST.get('origins', '').strip()
        # Try both with and without brackets (security middleware blocks brackets in param names)
        origins_list = request.POST.getlist('origins_list') or request.POST.getlist('origins_list[]')  # New format: array of selected domains
        
        # If new format is used, convert to origin format (add https:// and http://)
        lines = []
        if origins_list:
            for domain in origins_list:
                domain = domain.strip()
                if domain:
                    # Add both https and http versions
                    lines.append(f'https://{domain}')
                    lines.append(f'http://{domain}')
        elif origins_raw:
            # Fallback to old textarea format
            lines = [ln.strip() for ln in origins_raw.splitlines() if ln.strip() and not ln.strip().startswith('#')]
        path = get_panel_csrf_origins_file()
        _ensure_origins_dir()
        try:
            with open(path, 'w') as f:
                f.write('# Custom panel domain(s) for CSRF (one origin per line)\n')
                for line in lines:
                    f.write(line + '\n')
            try:
                os.chmod(path, 0o600)
            except (OSError, IOError):
                pass
        except (OSError, IOError) as e:
            return JsonResponse({
                'save': 0,
                'error_message': _('Could not write config file: %s') % str(e),
            })

        message = _('Custom domains saved. Restart the CyberPanel backend (e.g. systemctl restart lscpd) for CSRF to take effect.')
        proxy_results = []

        setup_ols = request.POST.get('setup_ols_proxy', '').strip().lower() in ('1', 'true', 'yes', 'on')
        if setup_ols and lines:
            try:
                from .ols_proxy import setup_panel_proxy_vhost, domain_from_origin
            except ImportError as e:
                CyberCPLogFileWriter.writeToFile(f"Panel Access: Failed to import ols_proxy: {str(e)}")
            except Exception as e:
                CyberCPLogFileWriter.writeToFile(f"Panel Access: Error importing ols_proxy: {str(e)}")
            else:
                try:
                    seen = set()
                    for origin in lines:
                        try:
                            domain = domain_from_origin(origin)
                            if not domain or domain in seen:
                                continue
                            seen.add(domain)
                            ok, msg = setup_panel_proxy_vhost(domain)
                            proxy_results.append({'domain': domain, 'success': ok, 'message': msg})
                        except Exception as e:
                            CyberCPLogFileWriter.writeToFile(f"Panel Access: Error processing origin {origin}: {str(e)}")
                            proxy_results.append({'domain': origin, 'success': False, 'message': f'Error: {str(e)}'})
                except Exception as e:
                    CyberCPLogFileWriter.writeToFile(f"Panel Access: Error in OLS proxy setup: {str(e)}")
                    # Don't fail the entire save if OLS setup fails
                if proxy_results:
                    parts = [message]
                    for r in proxy_results:
                        parts.append('{}: {}'.format(r['domain'], r['message']))
                    message = ' '.join(parts)

        # Restart lscpd so Django loads the new CSRF origins
        restart_ok = False
        restart_error = None
        try:
            # Use ProcessUtilities like RestartCyberPanel does
            command = 'systemctl restart lscpd'
            ProcessUtilities.popenExecutioner(command)
            restart_ok = True
        except Exception as e:
            restart_error = str(e)
            CyberCPLogFileWriter.writeToFile(f"Panel Access: Failed to restart lscpd: {str(e)}")

        if restart_ok:
            message = _('Custom domains saved. CyberPanel backend (lscpd) restarted; CSRF changes are active.')
            if proxy_results:
                message = message + ' ' + ' '.join('{}: {}.'.format(r['domain'], r['message']) for r in proxy_results)
        else:
            message = _('Custom domains saved. Restart the CyberPanel backend manually (systemctl restart lscpd) for CSRF to take effect.')
            if restart_error:
                message = message + ' ' + _('Restart failed: %s') % restart_error
            if proxy_results:
                message = message + ' ' + ' '.join('{}: {}.'.format(r['domain'], r['message']) for r in proxy_results)

        return JsonResponse({
            'save': 1,
            'message': message,
            'proxy_results': proxy_results,
            'lscpd_restarted': restart_ok,
        })
    except Exception as e:
        CyberCPLogFileWriter.writeToFile(f"Panel Access: Save error: {str(e)}")
        import traceback
        CyberCPLogFileWriter.writeToFile(f"Panel Access: Traceback: {traceback.format_exc()}")
        return JsonResponse({
            'save': 0,
            'error_message': _('An error occurred while saving: %s') % str(e),
        }, status=500)


@require_http_methods(['GET'])
def get_domains_api(request):
    """API endpoint to get all domains and subdomains for the selector."""
    try:
        request.session['userID']
    except KeyError:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        from loginSystem.models import Administrator
        from plogical.acl import ACLManager
        user_id = request.session['userID']
        current_acl = ACLManager.loadedACL(user_id)
        if not current_acl.get('admin'):
            return JsonResponse({'error': 'Admin access required'}, status=403)
    except Exception:
        return JsonResponse({'error': 'Authorization check failed'}, status=500)
    
    domains = _get_all_domains()
    return JsonResponse({'domains': domains})
