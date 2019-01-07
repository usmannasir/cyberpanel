 # -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from loginSystem.models import Administrator
from loginSystem.views import loadLoginPage
from django.http import HttpResponse
from plogical.container import ContainerManager
from dockerManager.pluginManager import pluginManager
from decorators import preDockerRun
from plogical.acl import ACLManager
import json
import requests
import docker

# Use default socket to connect
client = docker.from_env()
# Create your views here.

# This function checks if user has admin permissions
def dockerPermission(request, userID, context):
    currentACL = ACLManager.loadedACL(userID)
    
    if currentACL['admin'] != 1:
        if request.method == "POST":
            return ACLManager.loadErrorJson()
        else:
            return ACLManager.loadError()
    else:
        return None
        
@preDockerRun
def loadDockerHome(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        admin = Administrator.objects.get(pk=userID)
        return render(request,'dockerManager/index.html',{"type":admin.type})
    except KeyError:
        return redirect(loadLoginPage)

def installDocker(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        result = pluginManager.preDockerInstallation(request) # Later change to preInstallInstallation

        if  result != 200:
            return result

        cm = ContainerManager()
        coreResult = cm.submitInstallDocker(userID, json.loads(request.body))

        result = pluginManager.postDockerInstallation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun    
def installImage(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm

        cm = ContainerManager()
        coreResult = cm.submitInstallImage(userID, json.loads(request.body))

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)
    
@preDockerRun
def viewContainer(request, name):
    try:
        if not request.GET._mutable:
            request.GET._mutable = True
        request.GET['name'] = name

        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        cm = ContainerManager(name)
        coreResult = cm.loadContainerHome(request, userID)

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)    

@preDockerRun
def getTags(request): 
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm

        cm = ContainerManager()
        coreResult = cm.getTags(userID, json.loads(request.body))

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)
    
@preDockerRun
def delContainer(request): 
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm

        cm = ContainerManager()
        coreResult = cm.submitContainerDeletion(userID, json.loads(request.body))

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)
    
@preDockerRun    
def recreateContainer(request): 
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm

        cm = ContainerManager()
        coreResult = cm.recreateContainer(userID, json.loads(request.body))

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)    
    
@preDockerRun    
def runContainer(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        cm = ContainerManager()
        return cm.createContainer(request, userID)
    except KeyError:
        return redirect(loadLoginPage)    

@preDockerRun    
def listContainers(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        cm = ContainerManager()
        return cm.listContainers(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun    
def getContainerLogs(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm

        cm = ContainerManager()
        coreResult = cm.getContainerLogs(userID, json.loads(request.body))
        return coreResult

    except KeyError:
        return redirect(loadLoginPage)    

@preDockerRun    
def submitContainerCreation(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm

        cm = ContainerManager()
        coreResult = cm.submitContainerCreation(userID, json.loads(request.body))

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun    
def getContainerList(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        cm = ContainerManager()
        return cm.getContainerList(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun    
def doContainerAction(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        cm = ContainerManager()
        coreResult = cm.doContainerAction(userID, json.loads(request.body))
        
        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun    
def getContainerStatus(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        cm = ContainerManager()
        coreResult = cm.getContainerStatus(userID, json.loads(request.body))
        
        return coreResult
    except KeyError:
        return redirect(loadLoginPage)    

@preDockerRun    
def exportContainer(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        cm = ContainerManager()
        coreResult = cm.exportContainer(request, userID)
        
        return coreResult
    except KeyError:
        return redirect(loadLoginPage)    
        
@preDockerRun        
def saveContainerSettings(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        cm = ContainerManager()
        coreResult = cm.saveContainerSettings(userID, json.loads(request.body))
        
        return coreResult
    except KeyError:
        return redirect(loadLoginPage) 
    
@preDockerRun    
def getContainerTop(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        cm = ContainerManager()
        coreResult = cm.getContainerTop(userID, json.loads(request.body))
        
        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun    
def assignContainer(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        cm = ContainerManager()
        coreResult = cm.assignContainer(userID, json.loads(request.body))
        
        return coreResult
    except KeyError:
        return redirect(loadLoginPage)
    
@preDockerRun    
def searchImage(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        cm = ContainerManager()
        coreResult = cm.searchImage(userID, json.loads(request.body))
        
        return coreResult
    except KeyError:
        return redirect(loadLoginPage)
    
@preDockerRun    
def images(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'images')
        if perm: return perm
        
        
        cm = ContainerManager()
        coreResult = cm.images(request, userID)
        
        return coreResult
    except KeyError:
        return redirect(loadLoginPage)
    
@preDockerRun    
def manageImages(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        cm = ContainerManager()
        coreResult = cm.manageImages(request, userID)
        
        return coreResult
    except KeyError:
        return redirect(loadLoginPage)
    
@preDockerRun    
def getImageHistory(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        cm = ContainerManager()
        coreResult = cm.getImageHistory(userID, json.loads(request.body))
        
        return coreResult
    except KeyError:
        return redirect(loadLoginPage)
    
@preDockerRun    
def removeImage(request):
    try:
        userID = request.session['userID']
        perm = dockerPermission(request, userID, 'loadDockerHome')
        if perm: return perm
        
        cm = ContainerManager()
        coreResult = cm.removeImage(userID, json.loads(request.body))
        
        return coreResult
    except KeyError:
        return redirect(loadLoginPage)    