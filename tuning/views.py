# -*- coding: utf-8 -*-


from django.shortcuts import redirect
import json
from loginSystem.views import loadLoginPage
from .tuning import tuningManager
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