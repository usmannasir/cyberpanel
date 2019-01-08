from django.shortcuts import render,redirect
from loginSystem.models import Administrator
import os 
import docker
import json
from django.http import HttpResponse
from loginSystem.views import loadLoginPage

def preDockerRun(function):
    def wrap(request, *args, **kwargs):
        
        try:        
            val = request.session['userID']
        except KeyError:
            return redirect(loadLoginPage)
        
        admin = Administrator.objects.get(pk=val)
        
        if request.method == "POST":
            isPost = True
        else:
            isPost = False
            
        # check if docker is installed
        dockerInstallPath = '/usr/bin/docker'
        if not os.path.exists(dockerInstallPath):
            if isPost:
                data_ret = {'status': 0, 'error_message': 'Docker not installed'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                return render(request, 'dockerManager/install.html', {'status':admin.type, 'conErr':0})
            
        # Check if docker is running and we are able to connect
                
        try:
            client = docker.from_env()
            client.ping()
        except:
            if isPost:
                data_ret = {'status': 0, 'error_message': 'Docker daemon not running or not responsive'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                return render(request, 'dockerManager/install.html', {'status':admin.type, 'conErr':1})
        
        return function(request, *args, **kwargs)
    return wrap