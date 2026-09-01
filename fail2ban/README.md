# 🛡️ Fail2ban Security Manager Plugin for CyberPanel

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CyberPanel Compatible](https://img.shields.io/badge/CyberPanel-Compatible-blue.svg)](https://cyberpanel.net/)
[![AlmaLinux 9.6](https://img.shields.io/badge/AlmaLinux-9.6-red.svg)](https://almalinux.org/)
[![OpenLiteSpeed](https://img.shields.io/badge/OpenLiteSpeed-Compatible-green.svg)](https://openlitespeed.org/)

A comprehensive, modern, and mobile-friendly fail2ban management plugin for CyberPanel with OpenLiteSpeed integration. This plugin provides advanced threat protection, real-time monitoring, and intuitive IP management through a beautiful web interface.

## ✨ Features

### 🔒 **Advanced Security Management**
- **Real-time Monitoring**: Live dashboard with instant threat detection
- **IP Whitelist/Blacklist**: Comprehensive IP management system
- **Jail Management**: Control and configure all fail2ban jails
- **Automated Protection**: Smart threat detection and response

### 📱 **Modern User Interface**
- **Mobile-Friendly**: Fully responsive design for all devices
- **SEO Optimized**: Clean, semantic HTML structure
- **Futuristic Design**: Modern CSS with smooth animations
- **Dark/Light Themes**: Adaptive color schemes

### 🚀 **Performance & Reliability**
- **Real-time Updates**: Live data refresh every 30 seconds
- **Efficient API**: RESTful endpoints for all operations
- **Error Handling**: Comprehensive error management
- **Logging**: Detailed security event logging

### 🔧 **Technical Features**
- **OpenLiteSpeed Integration**: Native support for OpenLiteSpeed logs
- **CyberPanel Integration**: Seamless integration with CyberPanel
- **Firewall Integration**: Uses firewall-cmd rich rules
- **Database Support**: SQLite/MySQL/PostgreSQL compatible

## 📋 Requirements

- **Operating System**: AlmaLinux 9.6 (recommended)
- **CyberPanel**: Version 2.0.0 or higher
- **OpenLiteSpeed**: Any recent version
- **Python**: 3.8 or higher
- **Django**: 3.2 or higher
- **fail2ban**: 1.0 or higher
- **firewall-cmd**: For firewall management

## 🚀 Installation

### Method 1: CyberPanel Plugin Installer (Recommended)

1. **Download the Plugin**
   ```bash
   wget https://github.com/master3395/fail2ban-plugin/releases/latest/download/fail2ban-plugin.zip
   ```

2. **Upload to CyberPanel**
   - Log into your CyberPanel admin panel
   - Navigate to **Plugins** → **Plugin Installer**
   - Upload the `fail2ban-plugin.zip` file
   - Click **Install**

3. **Configure the Plugin**
   - The plugin will automatically install fail2ban if not present
   - Configure your settings through the plugin interface
   - Access via **Plugins** → **Fail2ban Security Manager**

### Method 2: Manual Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/master3395/fail2ban-plugin.git
   cd fail2ban-plugin
   ```

2. **Install Dependencies**
   ```bash
   # Install fail2ban
   dnf install -y epel-release
   dnf install -y fail2ban
   
   # Install firewalld
   dnf install -y firewalld
   systemctl enable firewalld
   systemctl start firewalld
   ```

3. **Install the Plugin**
   ```bash
   # Copy plugin files
   cp -r fail2ban_plugin /usr/local/CyberCP/pluginHolder/
   
   # Set permissions
   chown -R cyberpanel:cyberpanel /usr/local/CyberCP/pluginHolder/fail2ban_plugin
   chmod -R 755 /usr/local/CyberCP/pluginHolder/fail2ban_plugin
   
   # Run migrations
   cd /usr/local/CyberCP
   python3 manage.py makemigrations fail2ban_plugin
   python3 manage.py migrate
   ```

4. **Configure fail2ban**
   ```bash
   # Create configuration
   cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
   
   # Add custom filters
   # (See Configuration section below)
   ```

5. **Restart Services**
   ```bash
   systemctl restart fail2ban
   systemctl restart lscpd
   ```

## ⚙️ Configuration

### Basic Configuration

The plugin comes with pre-configured jails for:
- **SSH** (sshd)
- **OpenLiteSpeed** (openlitespeed)
- **CyberPanel** (cyberpanel)

### Custom Configuration

1. **Edit Jail Configuration**
   ```bash
   nano /etc/fail2ban/jail.local
   ```

2. **Add Custom Filters**
   ```bash
   # Create custom filter
   nano /etc/fail2ban/filter.d/custom.conf
   ```

3. **Restart fail2ban**
   ```bash
   systemctl restart fail2ban
   ```

### Whitelist Configuration

Add trusted IPs to the whitelist:
```bash
# Edit jail.local
nano /etc/fail2ban/jail.local

# Add to ignoreip line
ignoreip = 127.0.0.1/8 ::1 192.168.1.0/24 YOUR_TRUSTED_IP
```

## 🎯 Usage

### Dashboard Overview

The main dashboard provides:
- **Service Status**: Real-time fail2ban service status
- **Statistics**: Key security metrics and trends
- **Quick Actions**: One-click IP management
- **Recent Events**: Latest security events

### IP Management

#### Whitelist Management
- Add trusted IPs that should never be banned
- Remove IPs from whitelist
- View current whitelist

#### Blacklist Management
- Permanently ban malicious IPs
- Remove IPs from blacklist
- View current blacklist

#### Ban/Unban IPs
- Manually ban suspicious IPs
- Unban false positives
- Bulk operations for multiple IPs

### Jail Management

- **View All Jails**: See all configured fail2ban jails
- **Enable/Disable**: Control individual jails
- **Monitor Activity**: Real-time jail statistics
- **Configure Settings**: Adjust ban times and thresholds

### Logs & Monitoring

- **Real-time Logs**: Live fail2ban log viewing
- **Security Events**: Detailed event logging
- **Statistics**: Comprehensive security analytics
- **Threat Intelligence**: Attack pattern analysis

## 🔧 API Reference

### Authentication
All API endpoints require authentication via CyberPanel session.

### Endpoints

#### Status
```http
GET /fail2ban_plugin/api/status/
```
Returns fail2ban service status and active jails.

#### Jails
```http
GET /fail2ban_plugin/api/jails/
```
Returns detailed information about all jails.

#### Banned IPs
```http
GET /fail2ban_plugin/api/banned-ips/
```
Returns currently banned IP addresses.

#### Whitelist Management
```http
GET /fail2ban_plugin/api/whitelist/
POST /fail2ban_plugin/api/whitelist/
DELETE /fail2ban_plugin/api/whitelist/
```

#### Blacklist Management
```http
GET /fail2ban_plugin/api/blacklist/
POST /fail2ban_plugin/api/blacklist/
DELETE /fail2ban_plugin/api/blacklist/
```

#### IP Actions
```http
POST /fail2ban_plugin/api/ban-ip/
POST /fail2ban_plugin/api/unban-ip/
```

#### Service Management
```http
POST /fail2ban_plugin/api/restart/
```

#### Logs
```http
GET /fail2ban_plugin/api/logs/
```

#### Statistics
```http
GET /fail2ban_plugin/api/statistics/
```

## 🛠️ Development

### Project Structure
```
fail2ban-plugin/
├── meta.xml                 # Plugin metadata
├── __init__.py             # Plugin initialization
├── apps.py                 # Django app configuration
├── models.py               # Database models
├── views.py                # API views and page views
├── urls.py                 # URL routing
├── utils.py                # Fail2banManager utility class
├── admin.py                # Django admin configuration
├── signals.py              # Django signals
├── tests.py                # Unit tests
├── pre_install             # Pre-installation script
├── post_install            # Post-installation script
├── migrations/             # Database migrations
└── templates/              # HTML templates
    └── fail2ban_plugin/
        ├── dashboard.html
        ├── jails.html
        ├── banned_ips.html
        ├── whitelist.html
        ├── blacklist.html
        ├── settings.html
        ├── logs.html
        └── statistics.html
```

### Adding New Features

1. **Create New View**
   ```python
   # In views.py
   def new_feature(request):
       return render(request, 'fail2ban_plugin/new_feature.html')
   ```

2. **Add URL Route**
   ```python
   # In urls.py
   path('new-feature/', views.new_feature, name='new_feature'),
   ```

3. **Create Template**
   ```html
   <!-- In templates/fail2ban_plugin/new_feature.html -->
   {% extends "baseTemplate/base.html" %}
   {% block content %}
   <!-- Your content here -->
   {% endblock %}
   ```

### Testing

Run the test suite:
```bash
cd /usr/local/CyberCP
python3 manage.py test fail2ban_plugin
```

## 🔒 Security Considerations

### Best Practices

1. **Regular Updates**: Keep fail2ban and the plugin updated
2. **Monitor Logs**: Regularly check security logs
3. **Whitelist Management**: Only whitelist trusted IPs
4. **Backup Configuration**: Backup your fail2ban configuration
5. **Test Rules**: Test new rules in a safe environment

### Security Features

- **CSRF Protection**: All forms protected against CSRF attacks
- **Input Validation**: All inputs validated and sanitized
- **Permission Checks**: Proper authentication and authorization
- **SQL Injection Protection**: Parameterized queries used throughout
- **XSS Protection**: Output properly escaped

## 🐛 Troubleshooting

### Common Issues

#### Plugin Not Loading
```bash
# Check CyberPanel logs
tail -f /usr/local/lscp/logs/error.log

# Check Django logs
tail -f /usr/local/lscp/logs/django.log
```

#### fail2ban Not Working
```bash
# Check fail2ban status
systemctl status fail2ban

# Check configuration
fail2ban-client -t

# Check logs
journalctl -u fail2ban -f
```

#### Firewall Issues
```bash
# Check firewall status
systemctl status firewalld

# Check rules
firewall-cmd --list-rich-rules

# Reload firewall
firewall-cmd --reload
```

### Debug Mode

Enable debug mode in CyberPanel:
1. Go to **Settings** → **Debug Mode**
2. Enable debug logging
3. Check logs for detailed error information

## 📊 Performance

### Optimization Tips

1. **Log Rotation**: Configure log rotation for fail2ban logs
2. **Database Cleanup**: Regularly clean old security events
3. **Memory Usage**: Monitor fail2ban memory usage
4. **Filter Optimization**: Optimize fail2ban filters for better performance

### Monitoring

- **Service Status**: Monitor fail2ban service health
- **Memory Usage**: Track memory consumption
- **Log Size**: Monitor log file sizes
- **Response Time**: Track API response times

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### How to Contribute

1. **Fork the Repository**
2. **Create a Feature Branch**
3. **Make Your Changes**
4. **Add Tests**
5. **Submit a Pull Request**

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/fail2ban-plugin.git
cd fail2ban-plugin

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python manage.py test
```

## 📝 Changelog

### Version 1.0.0
- Initial release
- Basic fail2ban management
- Modern UI with mobile support
- OpenLiteSpeed integration
- CyberPanel compatibility
- Real-time monitoring
- IP whitelist/blacklist management

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **CyberPanel Team** for the excellent hosting control panel
- **OpenLiteSpeed Team** for the high-performance web server
- **fail2ban Community** for the robust intrusion prevention system
- **Django Community** for the powerful web framework

## 📞 Support

### Getting Help

- **Documentation**: Check this README and inline documentation
- **Issues**: Report bugs and request features on GitHub
- **Discussions**: Join community discussions
- **Email**: Contact support at support@newstargeted.com

### Community

- **GitHub**: [https://github.com/master3395/fail2ban-plugin](https://github.com/master3395/fail2ban-plugin)
- **Website**: [https://newstargeted.com](https://newstargeted.com)
- **Discord**: [https://discord.gg/nx9Kzrk](https://discord.gg/nx9Kzrk)

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=master3395/fail2ban-plugin&type=Date)](https://star-history.com/#master3395/fail2ban-plugin&Date)

---

**Made with ❤️ by [Master3395](https://github.com/master3395) for the CyberPanel community**

*Protect your server with the most advanced fail2ban management plugin available!*
