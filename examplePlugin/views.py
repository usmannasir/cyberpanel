from django.shortcuts import render, HttpResponse


# Create your views here.

def examplePlugin(request):
    return render(request, 'examplePlugin/examplePlugin.html')
