from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from .access import scanner_view
import json
import re


MAX_SCHEDULED_DOMAINS = 200
MAX_NOTIFICATION_EMAILS = 10
# A name is shown in pages and e-mails: no markup characters, no control characters.
SCHEDULE_NAME = re.compile(r'[^<>"`\\\x00-\x1f\x7f]{1,200}')


class InvalidSchedule(Exception):
    """A scheduled scan request that cannot be stored; the message is shown to the user."""


def switch(data, name, default):
    """An on/off setting of a request: only true and false are stored."""
    value = data.get(name, default)
    return value if isinstance(value, bool) else default


def day_number(value, lowest, highest):
    if isinstance(value, bool) or not isinstance(value, (int, str)) or not re.fullmatch(r'[0-9]{1,2}', str(value)):
        raise InvalidSchedule('Invalid day')
    number = int(value)
    if not lowest <= number <= highest:
        raise InvalidSchedule('Invalid day')
    return number


def checked_schedule(data):
    """Check the fields of a new scheduled scan against what the model allows."""
    from datetime import datetime
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email
    from .models import ScheduledScan

    if not isinstance(data, dict):
        raise InvalidSchedule('Invalid request')
    for field in ('name', 'domains', 'frequency', 'scan_type', 'time_of_day'):
        if not data.get(field):
            raise InvalidSchedule('Missing required field: %s' % field)

    name = data['name'].strip() if isinstance(data['name'], str) else ''
    if not SCHEDULE_NAME.fullmatch(name):
        raise InvalidSchedule('Name must be 1 to 200 characters and may not contain < > " ` or \\')

    frequency, scan_type = data['frequency'], data['scan_type']
    if frequency not in [choice[0] for choice in ScheduledScan.FREQUENCY_CHOICES]:
        raise InvalidSchedule('Invalid frequency')
    if scan_type not in [choice[0] for choice in ScheduledScan.SCAN_TYPE_CHOICES]:
        raise InvalidSchedule('Invalid scan type')

    domains = data['domains']
    if not isinstance(domains, list) or len(domains) == 0:
        raise InvalidSchedule('At least one domain must be selected')
    if len(domains) > MAX_SCHEDULED_DOMAINS or not all(
            isinstance(domain, str) and 0 < len(domain) <= 255 for domain in domains):
        raise InvalidSchedule('Invalid domains')

    try:
        time_of_day = datetime.strptime(data['time_of_day'], '%H:%M').time()
    except (TypeError, ValueError):
        raise InvalidSchedule('Invalid time format')

    emails = data.get('notification_emails') or []
    if not isinstance(emails, list) or len(emails) > MAX_NOTIFICATION_EMAILS:
        raise InvalidSchedule('At most %d notification e-mail addresses are allowed' % MAX_NOTIFICATION_EMAILS)
    for email in emails:
        try:
            if not isinstance(email, str) or len(email) > 254:
                raise ValidationError('invalid')
            validate_email(email)
        except ValidationError:
            raise InvalidSchedule('Invalid notification e-mail address')

    checked = {
        'name': name, 'frequency': frequency, 'scan_type': scan_type, 'domains': domains,
        'time_of_day': time_of_day, 'notification_emails': emails,
        'day_of_week': None, 'day_of_month': None,
    }
    if frequency == 'weekly':
        checked['day_of_week'] = day_number(data.get('day_of_week'), 0, 6)
    elif frequency == 'monthly':
        checked['day_of_month'] = day_number(data.get('day_of_month'), 1, 31)
    elif frequency == 'quarterly' and data.get('day_of_month') not in (None, ''):
        checked['day_of_month'] = day_number(data['day_of_month'], 1, 31)
    return checked


@scanner_view()
@require_http_methods(['GET', 'POST'])
def scheduledScans(request):
    """Manage scheduled scans"""
    try:
        userID = request.session['userID']
        from loginSystem.models import Administrator
        from .models import ScheduledScan
        from plogical.acl import ACLManager
        
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)
        
        if request.method == 'GET':
            # Get scheduled scans with ACL respect
            if currentACL['admin'] == 1:
                # Admin can see all scheduled scans
                scheduled_scans = ScheduledScan.objects.all()
            else:
                # Users can only see their own scheduled scans and their sub-users' scans
                user_admins = ACLManager.loadUserObjects(userID)
                scheduled_scans = ScheduledScan.objects.filter(admin__in=user_admins)
            
            scan_data = []
            for scan in scheduled_scans:
                scan_data.append({
                    'id': scan.id,
                    'name': scan.name,
                    'domains': scan.domain_list,
                    'frequency': scan.frequency,
                    'scan_type': scan.scan_type,
                    'time_of_day': scan.time_of_day.strftime('%H:%M'),
                    'day_of_week': scan.day_of_week,
                    'day_of_month': scan.day_of_month,
                    'status': scan.status,
                    'last_run': scan.last_run.isoformat() if scan.last_run else None,
                    'next_run': scan.next_run.isoformat() if scan.next_run else None,
                    'email_notifications': scan.email_notifications,
                    'notification_emails': scan.notification_email_list,
                    'notify_on_threats': scan.notify_on_threats,
                    'notify_on_completion': scan.notify_on_completion,
                    'notify_on_failure': scan.notify_on_failure,
                    'created_at': scan.created_at.isoformat()
                })
            
            return JsonResponse({'success': True, 'scheduled_scans': scan_data})
        
        elif request.method == 'POST':
            # Create new scheduled scan
            try:
                data = json.loads(request.body)
                checked = checked_schedule(data)
            except InvalidSchedule as refusal:
                return JsonResponse({'success': False, 'error': str(refusal)})
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid request'})

            # Check if user has access to these domains
            if currentACL['admin'] != 1:
                from websiteFunctions.models import Websites
                user_domains = set(Websites.objects.filter(admin=admin).values_list('domain', flat=True))
                requested_domains = set(checked['domains'])

                if not requested_domains.issubset(user_domains):
                    return JsonResponse({'success': False, 'error': 'You do not have access to some of the selected domains'})

            # Create scheduled scan
            scheduled_scan = ScheduledScan(
                admin=admin,
                name=checked['name'],
                frequency=checked['frequency'],
                scan_type=checked['scan_type'],
                time_of_day=checked['time_of_day'],
                day_of_week=checked['day_of_week'],
                day_of_month=checked['day_of_month'],
                email_notifications=switch(data, 'email_notifications', True),
                notify_on_threats=switch(data, 'notify_on_threats', True),
                notify_on_completion=switch(data, 'notify_on_completion', False),
                notify_on_failure=switch(data, 'notify_on_failure', True)
            )

            scheduled_scan.set_domains(checked['domains'])
            if checked['notification_emails']:
                scheduled_scan.set_notification_emails(checked['notification_emails'])

            scheduled_scan.save()

            return JsonResponse({'success': True, 'id': scheduled_scan.id})
            
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    except Exception as e:
        logging.writeToFile('[AI Scanner] Scheduled scan request failed: %s' % type(e).__name__)
        return JsonResponse({'success': False, 'error': 'Internal server error'})


@scanner_view()
@require_http_methods(['GET', 'DELETE'])
def scheduledScanDetail(request, scan_id):
    """Get or delete a specific scheduled scan"""
    try:
        userID = request.session['userID']
        from loginSystem.models import Administrator
        from .models import ScheduledScan
        from plogical.acl import ACLManager
        
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)
        
        # Get scheduled scan with ACL respect
        try:
            scheduled_scan = ScheduledScan.objects.get(id=scan_id)
            
            # Check if user has access to this scheduled scan
            if currentACL['admin'] != 1:
                user_admins = ACLManager.loadUserObjects(userID)
                if scheduled_scan.admin not in user_admins:
                    return JsonResponse({'success': False, 'error': 'Access denied to this scheduled scan'})
        except ScheduledScan.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Scheduled scan not found'})
        
        if request.method == 'GET':
            # Return scheduled scan details
            scan_data = {
                'id': scheduled_scan.id,
                'name': scheduled_scan.name,
                'domains': scheduled_scan.domain_list,
                'frequency': scheduled_scan.frequency,
                'scan_type': scheduled_scan.scan_type,
                'time_of_day': scheduled_scan.time_of_day.strftime('%H:%M'),
                'day_of_week': scheduled_scan.day_of_week,
                'day_of_month': scheduled_scan.day_of_month,
                'status': scheduled_scan.status,
                'last_run': scheduled_scan.last_run.isoformat() if scheduled_scan.last_run else None,
                'next_run': scheduled_scan.next_run.isoformat() if scheduled_scan.next_run else None,
                'email_notifications': scheduled_scan.email_notifications,
                'notification_emails': scheduled_scan.notification_email_list,
                'notify_on_threats': scheduled_scan.notify_on_threats,
                'notify_on_completion': scheduled_scan.notify_on_completion,
                'notify_on_failure': scheduled_scan.notify_on_failure,
                'created_at': scheduled_scan.created_at.isoformat()
            }
            
            return JsonResponse({'success': True, 'scheduled_scan': scan_data})
        
        elif request.method == 'DELETE':
            # Delete scheduled scan
            scheduled_scan.delete()
            return JsonResponse({'success': True})
            
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    except Exception as e:
        logging.writeToFile('[AI Scanner] Scheduled scan request failed: %s' % type(e).__name__)
        return JsonResponse({'success': False, 'error': 'Internal server error'})


@scanner_view()
@require_http_methods(['POST'])
def toggleScheduledScan(request, scan_id):
    """Toggle scheduled scan status (active/paused)"""
    try:
        userID = request.session['userID']
        from loginSystem.models import Administrator
        from .models import ScheduledScan
        from plogical.acl import ACLManager
        
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)
        
        # Get scheduled scan with ACL respect
        try:
            scheduled_scan = ScheduledScan.objects.get(id=scan_id)
            
            # Check if user has access to this scheduled scan
            if currentACL['admin'] != 1:
                user_admins = ACLManager.loadUserObjects(userID)
                if scheduled_scan.admin not in user_admins:
                    return JsonResponse({'success': False, 'error': 'Access denied to this scheduled scan'})
        except ScheduledScan.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Scheduled scan not found'})
        
        # Toggle status
        if scheduled_scan.status == 'active':
            scheduled_scan.status = 'paused'
        else:
            scheduled_scan.status = 'active'
        
        scheduled_scan.save()
        
        return JsonResponse({'success': True, 'status': scheduled_scan.status})
        
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    except Exception as e:
        logging.writeToFile('[AI Scanner] Scheduled scan request failed: %s' % type(e).__name__)
        return JsonResponse({'success': False, 'error': 'Internal server error'})


@scanner_view()
@require_http_methods(['GET'])
def scheduledScanExecutions(request, scan_id):
    """Get execution history for a scheduled scan"""
    try:
        userID = request.session['userID']
        from loginSystem.models import Administrator
        from .models import ScheduledScan, ScheduledScanExecution
        from plogical.acl import ACLManager
        
        admin = Administrator.objects.get(pk=userID)
        currentACL = ACLManager.loadedACL(userID)
        
        # Get scheduled scan with ACL respect
        try:
            scheduled_scan = ScheduledScan.objects.get(id=scan_id)
            
            # Check if user has access to this scheduled scan
            if currentACL['admin'] != 1:
                user_admins = ACLManager.loadUserObjects(userID)
                if scheduled_scan.admin not in user_admins:
                    return JsonResponse({'success': False, 'error': 'Access denied to this scheduled scan'})
        except ScheduledScan.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Scheduled scan not found'})
        
        # Get execution history
        executions = ScheduledScanExecution.objects.filter(scheduled_scan=scheduled_scan).order_by('-execution_time')[:20]
        
        execution_data = []
        for execution in executions:
            execution_data.append({
                'id': execution.id,
                'execution_time': execution.execution_time.isoformat(),
                'status': execution.status,
                'domains_scanned': execution.scanned_domains,
                'total_scans': execution.total_scans,
                'successful_scans': execution.successful_scans,
                'failed_scans': execution.failed_scans,
                'total_cost': float(execution.total_cost),
                'scan_ids': execution.scan_id_list,
                'error_message': execution.error_message,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None
            })
        
        return JsonResponse({'success': True, 'executions': execution_data})
        
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    except Exception as e:
        logging.writeToFile('[AI Scanner] Scheduled scan request failed: %s' % type(e).__name__)
        return JsonResponse({'success': False, 'error': 'Internal server error'})