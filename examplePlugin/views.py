# -*- coding: utf-8 -*-


from django.shortcuts import render, HttpResponse

# Create your views here.

def examplePlugin(request):
    return HttpResponse('This is homepage of an example plugin.')
