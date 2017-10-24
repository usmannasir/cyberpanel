from django.shortcuts import render
from django.shortcuts import render_to_response
import json
from django.http import HttpResponse
import shutil
import os

from filemanager import FileManager

fm = FileManager("/home//",True)


def index(request):
    return render(request, 'index.html')



def list_(request):
    fm.root = request.session['fileManagerHome']
    return HttpResponse(json.dumps(fm.list(json.loads(request.body.decode('utf-8')))))


def rename(request):
    fm.root = request.session['fileManagerHome']
    return HttpResponse(json.dumps(fm.rename(json.loads(request.body.decode('utf-8')))))


def copy(request):
    fm.root = request.session['fileManagerHome']
    return HttpResponse(json.dumps(fm.copy(json.loads(request.body.decode('utf-8')))))


def remove(request):
    fm.root = request.session['fileManagerHome']
    return HttpResponse(json.dumps(fm.remove(json.loads(request.body.decode('utf-8')))))


def edit(request):
    fm.root = request.session['fileManagerHome']
    return HttpResponse(json.dumps(fm.edit(json.loads(request.body.decode('utf-8')))))


def createFolder(request):
    fm.root = request.session['fileManagerHome']
    return HttpResponse(json.dumps(fm.createFolder(json.loads(request.body.decode('utf-8')))))


def changePermissions(request):
    fm.root = request.session['fileManagerHome']
    return HttpResponse(json.dumps(fm.changePermissions(json.loads(request.body.decode('utf-8')))))


def compress(request):
    fm.root = request.session['fileManagerHome']
    return HttpResponse(json.dumps(fm.compress(json.loads(request.body.decode('utf-8')))))


def downloadMultiple(request):
    fm.root = request.session['fileManagerHome']
    ret = fm.downloadMultiple(request.GET, HttpResponse)
    os.umask(ret[1])
    shutil.rmtree(ret[2], ignore_errors=True)
    return ret[0]


def move(request):
    fm.root = request.session['fileManagerHome']
    return HttpResponse(json.dumps(fm.move(json.loads(request.body.decode('utf-8')))))


def getContent(request):
    fm.root = request.session['fileManagerHome']
    return HttpResponse(json.dumps(fm.getContent(json.loads(request.body.decode('utf-8')))))


def extract(request):
    fm.root = request.session['fileManagerHome']
    return HttpResponse(json.dumps(fm.extract(json.loads(request.body.decode('utf-8')))))


def download(request):
    fm.root = request.session['fileManagerHome']
    return fm.download(request.GET['path'], HttpResponse)


def upload(request):
    fm.root = request.session['fileManagerHome']
    return HttpResponse(json.dumps(fm.upload(request.FILES, request.POST['destination'])))
