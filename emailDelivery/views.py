from django.shortcuts import redirect
from django.http import JsonResponse
from loginSystem.views import loadLoginPage
from .emailDeliveryManager import EmailDeliveryManager


def index(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.home(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def connect(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.connect(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def getStatus(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.getStatus(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def disconnect(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.disconnect(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def addDomain(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.addDomain(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def listDomains(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.listDomains(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def verifyDomain(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.verifyDomain(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def getDnsRecords(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.getDnsRecords(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def autoConfigureDns(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.autoConfigureDns(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def removeDomain(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.removeDomain(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def createSmtpCredential(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.createSmtpCredential(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def listSmtpCredentials(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.listSmtpCredentials(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def rotateSmtpPassword(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.rotateSmtpPassword(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def deleteSmtpCredential(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.deleteSmtpCredential(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def enableRelay(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.enableRelay(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def disableRelay(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.disableRelay(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def getStats(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.getStats(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def getDomainStats(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.getDomainStats(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def getLogs(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.getLogs(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})


def checkStatus(request):
    try:
        userID = request.session['userID']
        em = EmailDeliveryManager()
        return em.checkStatus(request, userID)
    except KeyError:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
