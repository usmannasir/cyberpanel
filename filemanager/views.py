# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from loginSystem.models import Administrator
from loginSystem.views import loadLoginPage


# Create your views here.


def loadFileManagerHome(request,domain):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

        viewStatus = 1

        if admin.type == 3:
            viewStatus = 0

        return render(request,'filemanager/index.html',{"viewStatus":viewStatus})
    except KeyError:
        return redirect(loadLoginPage)