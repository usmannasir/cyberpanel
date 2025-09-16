# -*- coding: utf-8 -*-
"""
phpMyAdmin Access Control Middleware

This middleware checks if users are trying to access phpMyAdmin directly
without being logged into CyberPanel and redirects them to the login page.
"""

from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.urls import reverse


class PhpMyAdminAccessMiddleware:
    """
    Middleware to control phpMyAdmin access and redirect unauthenticated users to login page.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for phpMyAdmin
        if request.path.startswith('/phpmyadmin/'):
            # Check if user is authenticated (has session)
            if 'userID' not in request.session:
                # Redirect to CyberPanel login page
                login_url = '/base/'
                return HttpResponseRedirect(login_url)
        
        response = self.get_response(request)
        return response
