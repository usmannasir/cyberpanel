# CyberPanel Plugin System Guide

**Author:** master3395  
**Version:** 1.0.0  
**Last Updated:** 2026-01-04

---

## Overview

CyberPanel includes a plugin system that allows developers to extend the functionality of the control panel. Plugins can add new features, integrate with external services, and customize the user experience.

This guide covers:
- Installing and managing plugins
- Developing your own plugins
- Plugin structure and requirements
- Using the testPlugin as a reference

---

## Table of Contents

1. [Plugin Installation](#plugin-installation)
2. [Plugin Management](#plugin-management)
3. [Plugin Development](#plugin-development)
4. [Plugin Structure](#plugin-structure)
5. [TestPlugin Reference](#testplugin-reference)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Plugin Installation

### Prerequisites

- CyberPanel installed and running
- Admin access to CyberPanel
- Server with appropriate permissions

### Installation Steps

1. **Access Plugin Manager**
   - Log into CyberPanel as administrator
   - Navigate to **Plugins** → **Installed Plugins**
   - Click **Upload Plugin** button

2. **Upload Plugin**
   - Select the plugin ZIP file
   - Click **Upload**
   - Wait for upload to complete

3. **Install Plugin**
   - After upload, the plugin will appear in the plugin list
   - Click **Install** button next to the plugin
   - Installation process will:
     - Extract plugin files to `/usr/local/CyberCP/`
     - Add plugin to `INSTALLED_APPS` in `settings.py`
     - Add URL routing to `urls.py`
     - Run database migrations (if applicable)
     - Collect static files
     - Restart CyberPanel service

4. **Verify Installation**
   - Plugin should appear in the installed plugins list
   - Status should show as "Installed" and "Enabled"
   - Click **Manage** or **Settings** to access plugin interface

### Manual Installation (Advanced)

If automatic installation fails or you need to install manually:

```bash
# 1. Extract plugin to CyberPanel directory
cd /home/cyberpanel/plugins
unzip plugin-name.zip
cd plugin-name

# 2. Copy plugin to CyberPanel directory
cp -r plugin-name /usr/local/CyberCP/

# 3. Add to INSTALLED_APPS
# Edit /usr/local/CyberCP/CyberCP/settings.py
# Add 'pluginName', to INSTALLED_APPS list (alphabetically ordered)

# 4. Add URL routing
# Edit /usr/local/CyberCP/CyberCP/urls.py
# Add before generic plugin route:
# path('plugins/pluginName/', include('pluginName.urls')),

# 5. Run migrations (if plugin has models)
cd /usr/local/CyberCP
python3 manage.py makemigrations pluginName
python3 manage.py migrate pluginName

# 6. Collect static files
python3 manage.py collectstatic --noinput

# 7. Set proper permissions
chown -R cyberpanel:cyberpanel /usr/local/CyberCP/pluginName/

# 8. Restart CyberPanel
systemctl restart lscpd
```

---

## Plugin Management

### Accessing Plugins

- **Plugin List**: Navigate to **Plugins** → **Installed Plugins**
- **Plugin Settings**: Click **Manage** or **Settings** button for each plugin
- **Plugin URL**: Typically `/plugins/pluginName/` or `/plugins/pluginName/settings/`

### Enabling/Disabling Plugins

Plugins are automatically enabled after installation. To disable:
- Some plugins may have enable/disable functionality in their settings
- To fully disable, you can remove from `INSTALLED_APPS` (advanced)

### Uninstalling Plugins

1. Navigate to **Plugins** → **Installed Plugins**
2. Click **Uninstall** button (if available)
3. Manual uninstallation:
   - Remove from `INSTALLED_APPS` in `settings.py`
   - Remove URL routing from `urls.py`
   - Remove plugin directory: `rm -rf /usr/local/CyberCP/pluginName/`
   - Restart CyberPanel: `systemctl restart lscpd`

---

## Plugin Development

### Creating a New Plugin

1. **Create Plugin Directory Structure**
   ```
   pluginName/
   ├── __init__.py
   ├── models.py          # Database models (optional)
   ├── views.py           # View functions
   ├── urls.py            # URL routing
   ├── forms.py           # Forms (optional)
   ├── utils.py           # Utility functions (optional)
   ├── admin.py           # Admin interface (optional)
   ├── templates/         # HTML templates
   │   └── pluginName/
   │       └── settings.html
   ├── static/            # Static files (CSS, JS, images)
   │   └── pluginName/
   ├── migrations/        # Database migrations
   │   └── __init__.py
   ├── meta.xml           # Plugin metadata (REQUIRED)
   └── README.md          # Plugin documentation
   ```

2. **Create meta.xml**
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <cyberpanelPluginConfig>
       <name>Plugin Name</name>
       <type>Utility</type>
       <description>Plugin description</description>
       <version>1.0.0</version>
       <url>/plugins/pluginName/</url>
       <settings_url>/plugins/pluginName/settings/</settings_url>
   </cyberpanelPluginConfig>
   ```

3. **Create URLs (urls.py)**
   ```python
   from django.urls import re_path
   from . import views

   app_name = 'pluginName'  # Important: Register namespace

   urlpatterns = [
       re_path(r'^$', views.main_view, name='main'),
       re_path(r'^settings/$', views.settings_view, name='settings'),
   ]
   ```

4. **Create Views (views.py)**
   ```python
   from django.shortcuts import render, redirect
   from functools import wraps

   def cyberpanel_login_required(view_func):
       """Custom decorator for CyberPanel session authentication"""
       @wraps(view_func)
       def _wrapped_view(request, *args, **kwargs):
           try:
               userID = request.session['userID']
               return view_func(request, *args, **kwargs)
           except KeyError:
               from loginSystem.views import loadLoginPage
               return redirect(loadLoginPage)
       return _wrapped_view

   @cyberpanel_login_required
   def main_view(request):
       context = {
           'plugin_name': 'Plugin Name',
           'version': '1.0.0'
       }
       return render(request, 'pluginName/index.html', context)

   @cyberpanel_login_required
   def settings_view(request):
       context = {
           'plugin_name': 'Plugin Name',
           'version': '1.0.0'
       }
       return render(request, 'pluginName/settings.html', context)
   ```

5. **Create Templates**
   - Templates should extend `baseTemplate/index.html`
   - Place templates in `templates/pluginName/` directory
   ```html
   {% extends "baseTemplate/index.html" %}
   {% load static %}
   {% load i18n %}

   {% block title %}
       Plugin Name Settings - {% trans "CyberPanel" %}
   {% endblock %}

   {% block content %}
   <div class="container">
       <h1>Plugin Name Settings</h1>
       <!-- Your plugin content here -->
   </div>
   {% endblock %}
   ```

6. **Package Plugin**
   ```bash
   cd /home/cyberpanel/plugins
   zip -r pluginName.zip pluginName/
   ```

---

## Plugin Structure

### Required Files

- **meta.xml**: Plugin metadata (name, version, description, URLs)
- **__init__.py**: Python package marker
- **urls.py**: URL routing configuration
- **views.py**: View functions (at minimum, a main view)

### Optional Files

- **models.py**: Database models
- **forms.py**: Django forms
- **utils.py**: Utility functions
- **admin.py**: Django admin integration
- **templates/**: HTML templates
- **static/**: CSS, JavaScript, images
- **migrations/**: Database migrations

### Template Requirements

- Must extend `baseTemplate/index.html` (not `baseTemplate/base.html`)
- Use Django template tags: `{% load static %}`, `{% load i18n %}`
- Follow CyberPanel UI conventions

### Authentication

Plugins should use the custom `cyberpanel_login_required` decorator:
- Checks for `request.session['userID']`
- Redirects to login if not authenticated
- Compatible with CyberPanel's session-based authentication

---

## TestPlugin Reference

The **testPlugin** is a reference implementation included with CyberPanel that demonstrates:

- Basic plugin structure
- Authentication handling
- Settings page implementation
- Clean URL routing
- Template inheritance

### TestPlugin Location

- **Source**: `/usr/local/CyberCP/testPlugin/`
- **URL**: `/plugins/testPlugin/`
- **Settings URL**: `/plugins/testPlugin/settings/`

### TestPlugin Features

1. **Main View**: Simple plugin information page
2. **Settings View**: Plugin settings interface
3. **Plugin Info API**: JSON endpoint for plugin information

### Examining TestPlugin

```bash
# View plugin structure
ls -la /usr/local/CyberCP/testPlugin/

# View meta.xml
cat /usr/local/CyberCP/testPlugin/meta.xml

# View URLs
cat /usr/local/CyberCP/testPlugin/urls.py

# View views
cat /usr/local/CyberCP/testPlugin/views.py

# View templates
ls -la /usr/local/CyberCP/testPlugin/templates/testPlugin/
```

### Using TestPlugin as Template

1. Copy testPlugin directory:
   ```bash
   cp -r /usr/local/CyberCP/testPlugin /home/cyberpanel/plugins/myPlugin
   ```

2. Rename files and update content:
   - Update `meta.xml` with your plugin information
   - Rename template files
   - Update views with your functionality
   - Update URLs as needed

3. Customize for your needs:
   - Add models if you need database storage
   - Add forms for user input
   - Add utilities for complex logic
   - Add static files for styling

---

## Best Practices

### Security

- Always use `cyberpanel_login_required` decorator for views
- Validate and sanitize all user input
- Use Django's form validation
- Follow CyberPanel security guidelines
- Never expose sensitive information in templates or responses

### Code Organization

- Keep files under 500 lines (split into modules if needed)
- Use descriptive function and variable names
- Add comments for complex logic
- Follow Python PEP 8 style guide
- Organize code into logical modules

### Templates

- Always extend `baseTemplate/index.html`
- Use CyberPanel's existing CSS classes
- Make templates mobile-friendly
- Use Django's internationalization (`{% trans %}`)
- Keep templates clean and readable

### Database

- Use Django migrations for schema changes
- Add proper indexes for performance
- Use transactions for multi-step operations
- Clean up old data when uninstalling

### Testing

- Test plugin installation process
- Test all plugin functionality
- Test error handling
- Test on multiple CyberPanel versions
- Test plugin uninstallation

### Documentation

- Include README.md with installation instructions
- Document all configuration options
- Provide usage examples
- Include troubleshooting section
- Document any dependencies

---

## Troubleshooting

### Plugin Not Appearing in List

- Check `meta.xml` format (must be valid XML)
- Verify plugin directory exists in `/home/cyberpanel/plugins/`
- Check CyberPanel logs: `tail -f /var/log/cyberpanel/error.log`

### Plugin Installation Fails

- Check file permissions: `ls -la /usr/local/CyberCP/pluginName/`
- Verify `INSTALLED_APPS` entry in `settings.py`
- Check URL routing in `urls.py`
- Review installation logs
- Check Python syntax: `python3 -m py_compile pluginName/views.py`

### Plugin Settings Page Not Loading

- Verify URL routing is correct
- Check template path (must be `templates/pluginName/settings.html`)
- Verify template extends `baseTemplate/index.html`
- Check for JavaScript errors in browser console
- Verify authentication decorator is used

### Template Not Found Error

- Check template directory structure: `templates/pluginName/`
- Verify template name in `render()` call matches file name
- Ensure template extends correct base template
- Check template syntax for errors

### Authentication Issues

- Verify `cyberpanel_login_required` decorator is used
- Check session is active: `request.session.get('userID')`
- Verify user is logged into CyberPanel
- Check redirect logic in decorator

### Static Files Not Loading

- Run `python3 manage.py collectstatic`
- Check static file URLs in templates
- Verify static files are in `static/pluginName/` directory
- Clear browser cache

### Database Migration Issues

- Check migrations directory exists: `migrations/__init__.py`
- Verify models are properly defined
- Run migrations: `python3 manage.py makemigrations pluginName`
- Apply migrations: `python3 manage.py migrate pluginName`

### Plugin Conflicts

- Check for duplicate plugin names
- Verify URL patterns don't conflict
- Check for namespace conflicts in `urls.py`
- Review `INSTALLED_APPS` for duplicate entries

---

## Plugin Examples

### Available Plugins

1. **testPlugin**: Reference implementation for plugin development
2. **discordWebhooks**: Server monitoring and notifications via Discord
3. **fail2ban**: Fail2ban security manager for CyberPanel

### Plugin Repository

Community plugins are available at:
- GitHub: https://github.com/master3395/cyberpanel-plugins

---

## Additional Resources

- **CyberPanel Documentation**: https://cyberpanel.net/KnowledgeBase/
- **Django Documentation**: https://docs.djangoproject.com/
- **Plugin System Source**: `/usr/local/CyberCP/pluginInstaller/`
- **Plugin Holder**: `/usr/local/CyberCP/pluginHolder/`

---

## Support

For plugin development questions:
- Check existing plugins for examples
- Review CyberPanel source code
- Ask in CyberPanel community forum
- Create an issue on GitHub

---

**Last Updated:** 2026-01-04  
**Author:** master3395
