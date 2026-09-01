from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Fail2banSettings, SecurityEvent, BannedIP
from .utils import Fail2banManager
import json

class Fail2banPluginTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_dashboard_view(self):
        """Test dashboard view loads correctly"""
        response = self.client.get(reverse('fail2ban_plugin:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fail2ban Security Manager')
    
    def test_api_status(self):
        """Test API status endpoint"""
        response = self.client.get(reverse('fail2ban_plugin:api_status'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('success', data)
    
    def test_api_jails(self):
        """Test API jails endpoint"""
        response = self.client.get(reverse('fail2ban_plugin:api_jails'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('success', data)
    
    def test_api_banned_ips(self):
        """Test API banned IPs endpoint"""
        response = self.client.get(reverse('fail2ban_plugin:api_banned_ips'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('success', data)
    
    def test_security_event_creation(self):
        """Test security event creation"""
        event = SecurityEvent.objects.create(
            event_type='ban',
            ip_address='192.168.1.100',
            jail_name='sshd',
            description='Test ban event',
            severity='high'
        )
        self.assertEqual(event.event_type, 'ban')
        self.assertEqual(event.ip_address, '192.168.1.100')
    
    def test_banned_ip_creation(self):
        """Test banned IP creation"""
        banned_ip = BannedIP.objects.create(
            ip_address='192.168.1.100',
            jail_name='sshd',
            ban_reason='Test ban',
            expires_at='2024-12-31 23:59:59'
        )
        self.assertEqual(banned_ip.ip_address, '192.168.1.100')
        self.assertTrue(banned_ip.is_active)
    
    def test_fail2ban_settings_creation(self):
        """Test fail2ban settings creation"""
        settings = Fail2banSettings.objects.create(
            user=self.user,
            email_notifications=True,
            auto_ban_threshold=5,
            ban_duration=3600
        )
        self.assertEqual(settings.user, self.user)
        self.assertTrue(settings.email_notifications)
        self.assertEqual(settings.auto_ban_threshold, 5)

class Fail2banManagerTestCase(TestCase):
    def setUp(self):
        self.manager = Fail2banManager()
    
    def test_is_valid_ip(self):
        """Test IP validation"""
        self.assertTrue(self.manager.is_valid_ip('192.168.1.1'))
        self.assertTrue(self.manager.is_valid_ip('8.8.8.8'))
        self.assertFalse(self.manager.is_valid_ip('invalid'))
        self.assertFalse(self.manager.is_valid_ip('192.168.1.256'))
    
    def test_run_command(self):
        """Test command execution"""
        result = self.manager.run_command('echo "test"')
        self.assertTrue(result['success'])
        self.assertEqual(result['stdout'], 'test')
