# CyberPanel Plugin Development Guide

**Author:** master3395  
**Version:** 2.0.0  
**Last Updated:** 2026-01-04  
**Repository:** https://github.com/master3395/cyberpanel/tree/v2.5.5-dev

---

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Plugin Architecture Overview](#plugin-architecture-overview)
4. [Creating Your First Plugin](#creating-your-first-plugin)
5. [Plugin Structure & Files](#plugin-structure--files)
6. [Core Components](#core-components)
7. [Advanced Features](#advanced-features)
8. [Best Practices](#best-practices)
9. [Security Guidelines](#security-guidelines)
10. [Testing & Debugging](#testing--debugging)
11. [Packaging & Distribution](#packaging--distribution)
12. [Troubleshooting](#troubleshooting)
13. [Examples & References](#examples--references)

---

## Introduction

CyberPanel's plugin system allows developers to extend the control panel's functionality with custom features. Plugins integrate seamlessly with CyberPanel's Django-based architecture, providing access to the full power of the platform while maintaining security and consistency.

### What Can Plugins Do?

- Add new administrative features
- Integrate with external services (APIs, webhooks, etc.)
- Customize the user interface
- Extend database functionality
- Add automation and monitoring capabilities
- Create custom reporting tools
- Integrate security features

### Plugin Types

- **Utility Plugins**: General-purpose tools and helpers
- **Security Plugins**: Security enhancements and monitoring
- **Performance Plugins**: Optimization and caching tools
- **Backup Plugins**: Backup and restore functionality
- **Integration Plugins**: Third-party service integrations

---

## Prerequisites

### Required Knowledge

- **Python 3.6+**: Basic to intermediate Python knowledge
- **Django Framework**: Understanding of Django views, URLs, templates, and models
- **HTML/CSS/JavaScript**: For creating user interfaces
- **Linux/Unix**: Basic command-line familiarity
- **XML**: Understanding of XML structure for `meta.xml`

### Required Tools

- CyberPanel installed and running
- Admin access to CyberPanel
- SSH access to the server
- Text editor (vim, nano, VS Code, etc.)
- Git (optional, for version control)

### System Requirements

- CyberPanel v2.0.0 or higher
- Python 3.6 or higher
- Django (included with CyberPanel)
- Sufficient disk space for plugin files
- Proper file permissions

---

## Plugin Architecture Overview

### How Plugins Work

1. **Plugin Source Location**: `/home/cyberpanel/plugins/`
   - Plugins are stored here before installation
   - Can be uploaded as ZIP files or placed directly

2. **Installed Location**: `/usr/local/CyberCP/`
   - After installation, plugins are copied here
   - This is where CyberPanel loads plugins from

3. **Integration Points**:
   - `INSTALLED_APPS` in `settings.py`: Registers plugin as Django app
   - `urls.py`: Adds plugin URL routes
   - `meta.xml`: Provides plugin metadata to CyberPanel

4. **Plugin Lifecycle**:
   ```
   Upload → Extract → Install → Enable → Use → (Optional: Disable) → Uninstall
   ```

### Plugin Registration Flow

```
1. Plugin placed in /home/cyberpanel/plugins/pluginName/
2. meta.xml is read by CyberPanel
3. User clicks "Install" in CyberPanel UI
4. PluginInstaller.installPlugin() is called
5. Plugin files copied to /usr/local/CyberCP/pluginName/
6. Plugin added to INSTALLED_APPS in settings.py
7. URL routes added to urls.py
8. Database migrations run (if applicable)
9. Static files collected
10. CyberPanel service restarted
11. Plugin appears in "Installed Plugins" list
```

---

## Creating Your First Plugin

### Step 1: Create Plugin Directory Structure

```bash
# Navigate to plugins directory
cd /home/cyberpanel/plugins

# Create your plugin directory
mkdir myFirstPlugin
cd myFirstPlugin

# Create required subdirectories
mkdir -p templates/myFirstPlugin
mkdir -p static/myFirstPlugin/css
mkdir -p static/myFirstPlugin/js
mkdir -p static/myFirstPlugin/images
mkdir -p migrations
```

### Step 2: Create Required Files

#### 2.1 Create `__init__.py`

```python
# __init__.py
# This file makes Python treat the directory as a package
```

#### 2.2 Create `meta.xml` (REQUIRED)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<cyberpanelPluginConfig>
    <name>My First Plugin</name>
    <type>Utility</type>
    <description>A simple example plugin to demonstrate CyberPanel plugin development</description>
    <version>1.0.0</version>
    <url>/plugins/myFirstPlugin/</url>
    <settings_url>/plugins/myFirstPlugin/settings/</settings_url>
    <author>Your Name</author>
    <website>https://yourwebsite.com</website>
</cyberpanelPluginConfig>
```

**meta.xml Fields Explained:**

- `<name>`: Display name of your plugin (required)
- `<type>`: Plugin category: Utility, Security, Performance, Backup, or custom (optional)
- `<description>`: Brief description shown in plugin list (required)
- `<version>`: Version number (e.g., 1.0.0) (required)
- `<url>`: Main plugin URL route (required)
- `<settings_url>`: Settings page URL (optional, but recommended)
- `<author>`: Plugin author name (optional)
- `<website>`: Author or plugin website (optional)

#### 2.3 Create `urls.py`

```python
# urls.py
from django.urls import path, re_path
from . import views

# IMPORTANT: Register namespace for URL reverse lookups
app_name = 'myFirstPlugin'

urlpatterns = [
    # Main plugin page
    path('', views.main_view, name='main'),
    
    # Settings page
    path('settings/', views.settings_view, name='settings'),
    
    # Example API endpoint
    path('api/info/', views.api_info, name='api_info'),
]
```

#### 2.4 Create `views.py`

```python
# views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from functools import wraps

def cyberpanel_login_required(view_func):
    """
    Custom decorator for CyberPanel session authentication.
    Always use this decorator for plugin views to ensure users are logged in.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            # Check if user is logged in via CyberPanel session
            userID = request.session['userID']
            return view_func(request, *args, **kwargs)
        except KeyError:
            # User not logged in, redirect to login page
            from loginSystem.views import loadLoginPage
            return redirect(loadLoginPage)
    return _wrapped_view


@cyberpanel_login_required
def main_view(request):
    """
    Main plugin page view.
    This is the entry point when users access /plugins/myFirstPlugin/
    """
    context = {
        'plugin_name': 'My First Plugin',
        'version': '1.0.0',
        'message': 'Welcome to your first CyberPanel plugin!'
    }
    return render(request, 'myFirstPlugin/main.html', context)


@cyberpanel_login_required
def settings_view(request):
    """
    Plugin settings page view.
    Accessible at /plugins/myFirstPlugin/settings/
    """
    context = {
        'plugin_name': 'My First Plugin',
        'version': '1.0.0'
    }
    return render(request, 'myFirstPlugin/settings.html', context)


@cyberpanel_login_required
def api_info(request):
    """
    Example API endpoint that returns JSON data.
    Accessible at /plugins/myFirstPlugin/api/info/
    """
    data = {
        'plugin_name': 'My First Plugin',
        'version': '1.0.0',
        'status': 'active',
        'message': 'Plugin is working correctly!'
    }
    return JsonResponse(data)
```

#### 2.5 Create Templates

**`templates/myFirstPlugin/main.html`:**

```html
{% extends "baseTemplate/index.html" %}
{% load static %}
{% load i18n %}

{% block title %}
    My First Plugin - {% trans "CyberPanel" %}
{% endblock %}

{% block header_scripts %}
<style>
    .plugin-container {
        padding: 20px;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    .plugin-header {
        background: white;
        border-radius: 12px;
        padding: 25px;
        margin-bottom: 25px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .plugin-header h1 {
        font-size: 28px;
        font-weight: 700;
        color: #2f3640;
        margin: 0 0 10px 0;
    }
    
    .plugin-content {
        background: white;
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
</style>
{% endblock %}

{% block content %}
<div class="plugin-container">
    <div class="plugin-header">
        <h1>{% trans "My First Plugin" %}</h1>
        <p>Version {{ version }}</p>
    </div>
    
    <div class="plugin-content">
        <h2>{% trans "Welcome!" %}</h2>
        <p>{{ message }}</p>
        
        <div style="margin-top: 20px;">
            <a href="/plugins/myFirstPlugin/settings/" class="btn btn-primary">
                {% trans "Go to Settings" %}
            </a>
        </div>
    </div>
</div>
{% endblock %}
```

**`templates/myFirstPlugin/settings.html`:**

```html
{% extends "baseTemplate/index.html" %}
{% load static %}
{% load i18n %}

{% block title %}
    My First Plugin Settings - {% trans "CyberPanel" %}
{% endblock %}

{% block content %}
<div class="container">
    <div class="panel">
        <div class="panel-heading">
            <h3 class="panel-title">{% trans "Plugin Settings" %}</h3>
        </div>
        <div class="panel-body">
            <p>{% trans "Settings page for My First Plugin" %}</p>
            <!-- Add your settings form here -->
        </div>
    </div>
</div>
{% endblock %}
```

### Step 3: Test Your Plugin Locally

Before installing, verify your plugin structure:

```bash
# Check file structure
cd /home/cyberpanel/plugins/myFirstPlugin
tree -L 3

# Verify Python syntax
python3 -m py_compile views.py urls.py

# Check XML validity
xmllint --noout meta.xml
```

### Step 4: Install Your Plugin

1. **Via CyberPanel UI:**
   - Navigate to **Plugins** → **Installed Plugins**
   - Your plugin should appear in the list
   - Click **Install** button
   - Wait for installation to complete

2. **Verify Installation:**
   ```bash
   # Check if plugin was copied
   ls -la /usr/local/CyberCP/myFirstPlugin/
   
   # Check if added to INSTALLED_APPS
   grep -i "myFirstPlugin" /usr/local/CyberCP/CyberCP/settings.py
   
   # Check if URLs were added
   grep -i "myFirstPlugin" /usr/local/CyberCP/CyberCP/urls.py
   ```

3. **Access Your Plugin:**
   - Navigate to `/plugins/myFirstPlugin/` in CyberPanel
   - Or click **Manage** button in Installed Plugins list

---

## Plugin Structure & Files

### Complete Directory Structure

```
pluginName/
├── __init__.py                 # Python package marker (required)
├── apps.py                     # Django app configuration (optional)
├── models.py                   # Database models (optional)
├── views.py                    # View functions (required)
├── urls.py                     # URL routing (required)
├── forms.py                    # Django forms (optional)
├── admin.py                    # Django admin integration (optional)
├── utils.py                    # Utility functions (optional)
├── signals.py                  # Django signals (optional)
├── tests.py                    # Unit tests (optional)
├── meta.xml                    # Plugin metadata (REQUIRED)
├── README.md                   # Plugin documentation (recommended)
├── requirements.txt            # Python dependencies (optional)
├── pre_install                 # Pre-installation script (optional)
├── post_install                # Post-installation script (optional)
├── pre_remove                  # Pre-removal script (optional)
├── templates/                  # HTML templates
│   └── pluginName/
│       ├── main.html
│       ├── settings.html
│       └── other_templates.html
├── static/                     # Static files (CSS, JS, images)
│   └── pluginName/
│       ├── css/
│       │   └── style.css
│       ├── js/
│       │   └── script.js
│       └── images/
│           └── logo.png
└── migrations/                 # Database migrations
    └── __init__.py
```

### File Descriptions

#### Required Files

1. **`__init__.py`**
   - Makes directory a Python package
   - Can be empty or contain initialization code

2. **`meta.xml`**
   - Plugin metadata for CyberPanel
   - Must be valid XML
   - Required fields: name, description, version

3. **`urls.py`**
   - URL routing configuration
   - Must define `app_name` for namespace
   - Maps URLs to view functions

4. **`views.py`**
   - Contains view functions
   - Must have at least one view
   - Should use `@cyberpanel_login_required` decorator

#### Optional Files

1. **`apps.py`**
   - Django app configuration
   - Useful for signals and app initialization

2. **`models.py`**
   - Database models
   - Use Django ORM for data persistence

3. **`forms.py`**
   - Django forms for user input
   - Provides validation and CSRF protection

4. **`utils.py`**
   - Helper functions
   - Business logic
   - API integrations

5. **`admin.py`**
   - Django admin interface
   - For managing plugin data

6. **`signals.py`**
   - Django signals
   - For event handling

7. **`tests.py`**
   - Unit tests
   - Integration tests

---

## Core Components

### 1. Authentication & Security

#### Using the Login Decorator

**Always use `cyberpanel_login_required` for all views:**

```python
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
def my_view(request):
    # Your view code here
    pass
```

#### CSRF Protection

Django's CSRF protection is enabled by default. For forms:

```html
{% csrf_token %}
```

For AJAX requests:

```javascript
// Get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Use in AJAX
fetch('/plugins/myPlugin/api/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(data)
});
```

### 2. URL Routing

#### Basic URL Patterns

```python
# urls.py
from django.urls import path, re_path
from . import views

app_name = 'myPlugin'

urlpatterns = [
    # Simple path
    path('', views.main_view, name='main'),
    
    # Path with parameter
    path('item/<int:item_id>/', views.item_detail, name='item_detail'),
    
    # Regex pattern
    re_path(r'^user/(?P<username>\w+)/$', views.user_profile, name='user_profile'),
    
    # Multiple parameters
    path('category/<str:category>/item/<int:item_id>/', views.category_item, name='category_item'),
]
```

#### URL Reverse Lookups

```python
# In views.py
from django.urls import reverse
from django.shortcuts import redirect

def my_view(request):
    # Generate URL
    url = reverse('myPlugin:main')
    # Or with parameters
    url = reverse('myPlugin:item_detail', args=[1])
    url = reverse('myPlugin:item_detail', kwargs={'item_id': 1})
    
    return redirect(url)
```

```html
<!-- In templates -->
<a href="{% url 'myPlugin:main' %}">Main Page</a>
<a href="{% url 'myPlugin:item_detail' item_id=1 %}">Item 1</a>
```

### 3. Views & Request Handling

#### Basic View Types

**Function-Based Views:**

```python
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse

@cyberpanel_login_required
def my_view(request):
    if request.method == 'POST':
        # Handle POST request
        data = request.POST.get('data')
        # Process data
        return JsonResponse({'success': True})
    else:
        # Handle GET request
        context = {'data': 'value'}
        return render(request, 'myPlugin/template.html', context)
```

**JSON API Views:**

```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@cyberpanel_login_required
@require_http_methods(["GET", "POST"])
def api_view(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        # Process data
        return JsonResponse({'status': 'success', 'data': data})
    else:
        return JsonResponse({'status': 'ok', 'message': 'API endpoint'})
```

#### Request Data Access

```python
# GET parameters
value = request.GET.get('key', 'default')

# POST data
value = request.POST.get('key', 'default')

# JSON data
import json
data = json.loads(request.body)

# Session data
user_id = request.session.get('userID')
request.session['key'] = 'value'

# Files
uploaded_file = request.FILES.get('file')
```

### 4. Templates

#### Template Inheritance

**Always extend `baseTemplate/index.html`:**

```html
{% extends "baseTemplate/index.html" %}
{% load static %}
{% load i18n %}

{% block title %}
    My Page - {% trans "CyberPanel" %}
{% endblock %}

{% block header_scripts %}
<style>
    /* Custom CSS */
</style>
{% endblock %}

{% block content %}
    <!-- Your content here -->
{% endblock %}

{% block footer_scripts %}
<script>
    // Custom JavaScript
</script>
{% endblock %}
```

#### Template Blocks

Available blocks in `baseTemplate/index.html`:

- `title`: Page title
- `header_scripts`: CSS and head scripts
- `content`: Main page content
- `footer_scripts`: JavaScript at end of page

#### Template Tags & Filters

```html
<!-- Load static files -->
{% load static %}
<img src="{% static 'myPlugin/images/logo.png' %}" alt="Logo">

<!-- Internationalization -->
{% load i18n %}
<h1>{% trans "Welcome" %}</h1>
<p>{% trans "Hello, world!" %}</p>

<!-- URL reverse -->
{% url 'myPlugin:main' %}

<!-- Variables -->
{{ variable }}
{{ object.attribute }}
{{ object.method }}

<!-- Filters -->
{{ text|upper }}
{{ text|truncatewords:10 }}
{{ date|date:"Y-m-d" }}

<!-- Conditionals -->
{% if condition %}
    <!-- content -->
{% elif other_condition %}
    <!-- content -->
{% else %}
    <!-- content -->
{% endif %}

<!-- Loops -->
{% for item in items %}
    <p>{{ item }}</p>
{% empty %}
    <p>No items</p>
{% endfor %}
```

### 5. Static Files

#### Organizing Static Files

```
static/
└── pluginName/
    ├── css/
    │   └── style.css
    ├── js/
    │   └── script.js
    └── images/
        └── logo.png
```

#### Using Static Files in Templates

```html
{% load static %}

<!-- CSS -->
<link rel="stylesheet" href="{% static 'pluginName/css/style.css' %}">

<!-- JavaScript -->
<script src="{% static 'pluginName/js/script.js' %}"></script>

<!-- Images -->
<img src="{% static 'pluginName/images/logo.png' %}" alt="Logo">
```

#### Collecting Static Files

After installation, static files are automatically collected. To manually collect:

```bash
cd /usr/local/CyberCP
python3 manage.py collectstatic --noinput
```

### 6. Database Models

#### Creating Models

```python
# models.py
from django.db import models

class MyModel(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'my_plugin_mymodel'
        ordering = ['-created_at']
        verbose_name = 'My Model'
        verbose_name_plural = 'My Models'
    
    def __str__(self):
        return self.name
```

#### Using Models in Views

```python
from .models import MyModel

@cyberpanel_login_required
def list_items(request):
    items = MyModel.objects.filter(is_active=True)
    context = {'items': items}
    return render(request, 'myPlugin/list.html', context)

@cyberpanel_login_required
def create_item(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        item = MyModel.objects.create(
            name=name,
            description=description
        )
        return redirect('myPlugin:list')
    return render(request, 'myPlugin/create.html')
```

#### Database Migrations

```bash
# Create migrations
cd /usr/local/CyberCP
python3 manage.py makemigrations pluginName

# Apply migrations
python3 manage.py migrate pluginName

# Show migration status
python3 manage.py showmigrations pluginName
```

---

## Advanced Features

### 1. Forms & Validation

#### Creating Forms

```python
# forms.py
from django import forms

class MyForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5})
    )
```

#### Using Forms in Views

```python
from .forms import MyForm

@cyberpanel_login_required
def my_form_view(request):
    if request.method == 'POST':
        form = MyForm(request.POST)
        if form.is_valid():
            # Process valid form data
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            # Save or process data
            return JsonResponse({'success': True})
        else:
            # Return form errors
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = MyForm()
    
    context = {'form': form}
    return render(request, 'myPlugin/form.html', context)
```

#### Rendering Forms in Templates

```html
<form method="post">
    {% csrf_token %}
    
    <div class="form-group">
        {{ form.name.label_tag }}
        {{ form.name }}
        {% if form.name.errors %}
            <div class="error">{{ form.name.errors }}</div>
        {% endif %}
    </div>
    
    <div class="form-group">
        {{ form.email.label_tag }}
        {{ form.email }}
        {% if form.email.errors %}
            <div class="error">{{ form.email.errors }}</div>
        {% endif %}
    </div>
    
    <button type="submit" class="btn btn-primary">Submit</button>
</form>
```

### 2. AJAX & API Endpoints

#### Creating API Endpoints

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@cyberpanel_login_required
@csrf_exempt  # Only if not using CSRF token in AJAX
@require_http_methods(["POST"])
def api_endpoint(request):
    try:
        data = json.loads(request.body)
        # Process data
        result = {
            'success': True,
            'message': 'Operation completed',
            'data': data
        }
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
```

#### JavaScript AJAX Example

```javascript
function sendAjaxRequest(data) {
    // Get CSRF token
    const csrftoken = getCookie('csrftoken');
    
    fetch('/plugins/myPlugin/api/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Success:', data.message);
        } else {
            console.error('Error:', data.error);
        }
    })
    .catch(error => {
        console.error('Request failed:', error);
    });
}
```

### 3. File Uploads

#### Handling File Uploads

```python
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

@cyberpanel_login_required
def upload_file(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        
        # Validate file
        if uploaded_file.size > 10 * 1024 * 1024:  # 10MB limit
            return JsonResponse({'success': False, 'error': 'File too large'})
        
        # Save file
        file_path = f'myPlugin/uploads/{uploaded_file.name}'
        path = default_storage.save(file_path, ContentFile(uploaded_file.read()))
        
        return JsonResponse({
            'success': True,
            'file_path': path
        })
    
    return JsonResponse({'success': False, 'error': 'No file provided'})
```

### 4. Logging

#### Using CyberPanel's Logging System

```python
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

# Write to log file
logging.writeToFile("Plugin message: Something happened")

# Write error
logging.writeToFile(f"Error: {str(exception)}", 1)  # 1 = error level

# Write with plugin name
logging.writeToFile(f"[MyPlugin] Action completed successfully")
```

### 5. Background Tasks

#### Using Subprocess for Long-Running Tasks

```python
import subprocess
import threading

def run_background_task(command):
    """Run a command in the background"""
    def task():
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True
            )
            logging.writeToFile(f"Task completed: {result.stdout}")
        except Exception as e:
            logging.writeToFile(f"Task error: {str(e)}", 1)
    
    thread = threading.Thread(target=task)
    thread.daemon = True
    thread.start()
    return thread
```

---

## Best Practices

### 1. Code Organization

- **Keep files under 500 lines**: Split large files into modules
- **Use descriptive names**: Functions, variables, and classes should be self-documenting
- **Follow PEP 8**: Python style guide
- **Add comments**: Explain complex logic
- **Modular structure**: Separate concerns (views, models, utils)

### 2. Error Handling

```python
from django.http import JsonResponse
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

@cyberpanel_login_required
def my_view(request):
    try:
        # Your code here
        result = perform_operation()
        return JsonResponse({'success': True, 'data': result})
    except ValueError as e:
        logging.writeToFile(f"Validation error: {str(e)}", 1)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logging.writeToFile(f"Unexpected error: {str(e)}", 1)
        return JsonResponse({'success': False, 'error': 'An error occurred'}, status=500)
```

### 3. Security Best Practices

- **Always validate input**: Never trust user input
- **Use parameterized queries**: When using raw SQL
- **Sanitize output**: Escape HTML in templates
- **Check permissions**: Verify user has access
- **Use HTTPS**: For sensitive operations
- **Rate limiting**: Prevent abuse
- **CSRF protection**: Always include CSRF tokens

### 4. Performance Optimization

- **Database queries**: Use `select_related()` and `prefetch_related()`
- **Caching**: Cache expensive operations
- **Lazy loading**: Load data only when needed
- **Pagination**: For large datasets
- **Static files**: Minify CSS/JS in production

### 5. Testing

```python
# tests.py
from django.test import TestCase, Client
from django.urls import reverse

class MyPluginTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Set up test data
    
    def test_main_view(self):
        # Test main view
        response = self.client.get(reverse('myPlugin:main'))
        self.assertEqual(response.status_code, 200)
    
    def test_api_endpoint(self):
        # Test API endpoint
        response = self.client.post(
            reverse('myPlugin:api'),
            data={'key': 'value'},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
```

---

## Security Guidelines

### 1. Input Validation

```python
import re
from django.core.exceptions import ValidationError

def validate_input(data):
    """Validate and sanitize user input"""
    if not data:
        raise ValidationError("Input cannot be empty")
    
    # Remove dangerous characters
    data = re.sub(r'[<>"\']', '', data)
    
    # Check length
    if len(data) > 1000:
        raise ValidationError("Input too long")
    
    return data.strip()
```

### 2. SQL Injection Prevention

**Always use Django ORM (recommended):**

```python
# ✅ GOOD - Using ORM
items = MyModel.objects.filter(name=user_input)

# ❌ BAD - Raw SQL with string formatting
items = MyModel.objects.raw(f"SELECT * FROM table WHERE name = '{user_input}'")
```

**If using raw SQL, use parameterized queries:**

```python
from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT * FROM table WHERE name = %s", [user_input])
```

### 3. XSS Prevention

**Django templates auto-escape by default:**

```html
<!-- ✅ GOOD - Auto-escaped -->
{{ user_input }}

<!-- ❌ BAD - Disables escaping -->
{{ user_input|safe }}
```

**Only use `|safe` if you're certain the content is safe:**

```python
from django.utils.html import escape

# Escape in Python
safe_html = escape(user_input)
```

### 4. File Upload Security

```python
import os
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = ['.jpg', '.png', '.pdf']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_uploaded_file(file):
    """Validate uploaded file"""
    # Check extension
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"File type {ext} not allowed")
    
    # Check size
    if file.size > MAX_FILE_SIZE:
        raise ValidationError("File too large")
    
    # Check content type
    if file.content_type not in ['image/jpeg', 'image/png', 'application/pdf']:
        raise ValidationError("Invalid file type")
    
    return True
```

---

## Testing & Debugging

### 1. Debugging Tools

#### Enable Django Debug Mode (Development Only)

```python
# In your view
import logging
logger = logging.getLogger(__name__)

def my_view(request):
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
```

#### Check Logs

```bash
# CyberPanel logs
tail -f /usr/local/lscp/logs/error.log

# Django logs (if configured)
tail -f /var/log/cyberpanel/error.log

# Plugin-specific logs
tail -f /home/cyberpanel/plugin_logs/myPlugin.log
```

### 2. Common Issues & Solutions

#### Template Not Found

**Problem:** `TemplateDoesNotExist` error

**Solutions:**
- Check template path: `templates/pluginName/template.html`
- Verify template name in `render()` call
- Ensure template extends `baseTemplate/index.html`
- Run `python3 manage.py collectstatic`

#### URL Not Found

**Problem:** 404 error when accessing plugin URL

**Solutions:**
- Verify URL pattern in `urls.py`
- Check `app_name` is set correctly
- Ensure plugin is in `INSTALLED_APPS`
- Restart CyberPanel: `systemctl restart lscpd`

#### Import Errors

**Problem:** `ImportError` or `ModuleNotFoundError`

**Solutions:**
- Check Python syntax: `python3 -m py_compile views.py`
- Verify `__init__.py` exists
- Check import paths
- Ensure plugin is installed correctly

#### Static Files Not Loading

**Problem:** CSS/JS/images not appearing

**Solutions:**
- Run `python3 manage.py collectstatic --noinput`
- Check static file paths in templates
- Verify files exist in `static/pluginName/`
- Clear browser cache

---

## Packaging & Distribution

### 1. Creating Plugin Package

```bash
# Navigate to plugin directory
cd /home/cyberpanel/plugins/myPlugin

# Create ZIP file
zip -r myPlugin-v1.0.0.zip . \
    -x "*.pyc" \
    -x "__pycache__/*" \
    -x "*.log" \
    -x ".git/*" \
    -x ".DS_Store"
```

### 2. Plugin Distribution Checklist

- [ ] Plugin tested and working
- [ ] All required files included
- [ ] `meta.xml` is valid and complete
- [ ] README.md with installation instructions
- [ ] No sensitive data (passwords, API keys)
- [ ] Proper file permissions
- [ ] Version number updated
- [ ] Documentation complete

### 3. Version Management

**Semantic Versioning:**

- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

**Update version in:**
- `meta.xml`
- `views.py` (if version displayed)
- `README.md`
- Git tags (if using version control)

---

## Troubleshooting

### Installation Issues

**Plugin not appearing in list:**
- Check `meta.xml` format and validity
- Verify plugin directory exists in `/home/cyberpanel/plugins/`
- Check file permissions
- Review CyberPanel logs

**Installation fails:**
- Check Python syntax errors
- Verify all required files exist
- Check file permissions
- Review installation logs
- Ensure sufficient disk space

### Runtime Issues

**Plugin page not loading:**
- Verify URL routing
- Check authentication decorator
- Review template paths
- Check for JavaScript errors
- Verify plugin is enabled

**Database errors:**
- Run migrations: `python3 manage.py migrate pluginName`
- Check database permissions
- Verify model definitions
- Review migration files

**Static files missing:**
- Run `python3 manage.py collectstatic`
- Check static file paths
- Verify file permissions
- Clear browser cache

---

## Examples & References

### Reference Plugins

1. **examplePlugin**: Basic plugin structure
   - Location: `/usr/local/CyberCP/examplePlugin/`
   - URL: `/plugins/examplePlugin/`

2. **testPlugin**: Comprehensive example
   - Location: `/usr/local/CyberCP/testPlugin/`
   - URL: `/plugins/testPlugin/`
   - **Author:** usmannasir

3. **discordWebhooks**: Discord webhook integration plugin
   - Location: `/usr/local/CyberCP/discordWebhooks/` (if installed)
   - URL: `/plugins/discordWebhooks/`
   - **Author:** Master3395

### Useful Resources

- **CyberPanel Documentation**: https://cyberpanel.net/KnowledgeBase/
- **Django Documentation**: https://docs.djangoproject.com/
- **Python Documentation**: https://docs.python.org/
- **CyberPanel GitHub**: https://github.com/usmannasir/cyberpanel
- **Plugin Repository**: https://github.com/master3395/cyberpanel-plugins

### Code Examples Repository

Check the `examplePlugin` and `testPlugin` directories in CyberPanel for complete working examples.

---

## Conclusion

This guide provides comprehensive information for developing CyberPanel plugins. Start with a simple plugin and gradually add more features as you become familiar with the system.

### Quick Start Checklist

1. ✅ Create plugin directory structure
2. ✅ Create `meta.xml` with required fields
3. ✅ Create `urls.py` with URL patterns
4. ✅ Create `views.py` with view functions
5. ✅ Create templates extending `baseTemplate/index.html`
6. ✅ Test plugin locally
7. ✅ Install via CyberPanel UI
8. ✅ Verify plugin works correctly

### Getting Help

- Review existing plugins for examples
- Check CyberPanel community forum
- Review Django documentation
- Examine CyberPanel source code
- Create GitHub issues for bugs

---

**Happy Plugin Development!**

**Author:** master3395  
**Last Updated:** 2026-01-04  
**Version:** 2.0.0
