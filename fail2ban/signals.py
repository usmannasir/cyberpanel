from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.http import HttpResponse
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from .models import SecurityEvent, BannedIP

# Try to import CyberPanel signals (may not be available in all versions)
try:
    from websiteFunctions.signals import postWebsiteCreation, postWebsiteDeletion
    CYBERPANEL_SIGNALS_AVAILABLE = True
except ImportError:
    CYBERPANEL_SIGNALS_AVAILABLE = False
    logging.writeToFile('CyberPanel signals not available - using fallback logging only')

@receiver(post_save, sender=SecurityEvent)
def log_security_event(sender, instance, created, **kwargs):
    """Log security events to system log"""
    if created:
        logging.writeToFile(f"Fail2ban Security Event: {instance.event_type} - {instance.ip_address} - {instance.description}")

@receiver(post_save, sender=BannedIP)
def log_banned_ip(sender, instance, created, **kwargs):
    """Log banned IP events"""
    if created:
        logging.writeToFile(f"Fail2ban IP Banned: {instance.ip_address} from {instance.jail_name}")
    elif not instance.is_active:
        logging.writeToFile(f"Fail2ban IP Unbanned: {instance.ip_address} from {instance.jail_name}")

@receiver(post_delete, sender=BannedIP)
def log_unbanned_ip(sender, instance, **kwargs):
    """Log when banned IP is deleted"""
    logging.writeToFile(f"Fail2ban Banned IP Removed: {instance.ip_address} from {instance.jail_name}")

# CyberPanel core event handlers
if CYBERPANEL_SIGNALS_AVAILABLE:
    @receiver(postWebsiteCreation)
    def handle_website_creation(sender, **kwargs):
        """Handle new website creation - ensure fail2ban protection is active"""
        try:
            request = kwargs.get('request', None)
            if request:
                logging.writeToFile('Fail2ban Plugin: New website created, ensuring fail2ban protection is active')
                # Return 200 to continue processing
                return 200
        except Exception as e:
            logging.writeToFile(f'Fail2ban Plugin: Error handling website creation - {str(e)}')
            return 200
    
    @receiver(postWebsiteDeletion)
    def handle_website_deletion(sender, **kwargs):
        """Handle website deletion - cleanup any related fail2ban rules"""
        try:
            request = kwargs.get('request', None)
            if request:
                logging.writeToFile('Fail2ban Plugin: Website deleted, cleaning up fail2ban rules')
                # Return 200 to continue processing
                return 200
        except Exception as e:
            logging.writeToFile(f'Fail2ban Plugin: Error handling website deletion - {str(e)}')
            return 200
else:
    # Fallback logging for when CyberPanel signals are not available
    logging.writeToFile('Fail2ban Plugin: CyberPanel signals not available, using basic Django signals only')
