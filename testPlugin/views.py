from django.shortcuts import render, redirect
from django.http import JsonResponse
from functools import wraps

def cyberpanel_login_required(view_func):
    """
    Custom decorator that checks for CyberPanel session userID
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            userID = request.session['userID']
            # User is authenticated via CyberPanel session
            return view_func(request, *args, **kwargs)
        except KeyError:
            # Not logged in, redirect to login
            return redirect('/')
    return _wrapped_view

@cyberpanel_login_required
def test_plugin_view(request):
    """
    Main view for the test plugin
    """
    context = {
        'plugin_name': 'Test Plugin',
        'version': '1.0.0',
        'description': 'A simple test plugin for CyberPanel'
    }
    return render(request, 'testPlugin/index.html', context)

@cyberpanel_login_required
def plugin_info_view(request):
    """
    API endpoint for plugin information
    """
    return JsonResponse({
        'plugin_name': 'Test Plugin',
        'version': '1.0.0',
        'status': 'active',
        'description': 'A simple test plugin for CyberPanel testing'
    })

@cyberpanel_login_required
def settings_view(request):
    """
    Settings page for the test plugin
    """
    context = {
        'plugin_name': 'Test Plugin',
        'version': '1.0.0',
        'description': 'A simple test plugin for CyberPanel'
    }
    return render(request, 'testPlugin/settings.html', context)
