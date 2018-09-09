# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect
from hypervisor import HVManager
from loginSystem.views import loadLoginPage
import json
# Create your views here.

def loadHVHome(request):
    try:
        userID = request.session['userID']
        hvm = HVManager()
        return hvm.loadHVHome(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def createHypervisor(request):
    try:
        userID = request.session['userID']
        hvm = HVManager()
        return hvm.createHypervisor(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def listHVs(request):
    try:
        userID = request.session['userID']
        hvm = HVManager()
        return hvm.listHVs(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def submitCreateHyperVisor(request):
    try:
        userID = request.session['userID']
        hvm = HVManager()
        return hvm.submitCreateHyperVisor(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def submitHyperVisorChanges(request):
    try:
        userID = request.session['userID']
        hvm = HVManager()
        return hvm.submitHyperVisorChanges(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def controlCommands(request):
    try:
        userID = request.session['userID']
        hvm = HVManager()
        return hvm.controlCommands(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)