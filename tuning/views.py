# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from django.http import HttpResponse
import json
import plogical.CyberCPLogFileWriter as logging
from plogical.tuning import tuning
from loginSystem.views import loadLoginPage
from plogical.virtualHostUtilities import virtualHostUtilities
import subprocess
import shlex
from plogical.acl import ACLManager
from tuning import tuningManager
# Create your views here.


def loadTuningHome(request):
    try:
        userID = request.session['userID']
        tm = tuningManager()
        return tm.loadTuningHome(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def liteSpeedTuning(request):
    try:
        userID = request.session['userID']
        tm = tuningManager()
        return tm.liteSpeedTuning(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def phpTuning(request):
    try:
        userID = request.session['userID']
        tm = tuningManager()
        return tm.phpTuning(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def tuneLitespeed(request):
    try:
        userID = request.session['userID']
        tm = tuningManager()
        return tm.tuneLitespeed(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def tunePHP(request):
    try:
        userID = request.session['userID']
        tm = tuningManager()
        return tm.tunePHP(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)