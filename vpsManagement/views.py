# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import redirect
from loginSystem.views import loadLoginPage
import json
from vpsManager import VPSManager


def vpsHome(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.vpsHome(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def createVPS(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.createVPS(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def submitVPSCreation(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.submitVPSCreation(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def findIPs(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.findIPs(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def listVPSs(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.listVPSs(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def fetchVPS(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.fetchVPS(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def deleteVPS(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.deleteVPS(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def restartVPS(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.restartVPS(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def shutdownVPS(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.shutdownVPS(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def manageVPS(request, hostName):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.manageVPS(request, userID, hostName)
    except KeyError:
        return redirect(loadLoginPage)

def getVPSDetails(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.getVPSDetails(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def changeHostname(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.changeHostname(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def changeRootPassword(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.changeRootPassword(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def reInstallOS(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.reInstallOS(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def startWebsocketServer(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.startWebsocketServer(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

##

def sshKeys(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.sshKeys(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def addKey(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.addKey(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def fetchKeys(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.fetchKeys(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def deleteKey(request):
    try:
        userID = request.session['userID']
        vmm = VPSManager()
        return vmm.deleteKey(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)


