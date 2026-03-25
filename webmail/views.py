import json
from django.shortcuts import redirect
from django.http import HttpResponse
from loginSystem.views import loadLoginPage
from .webmailManager import WebmailManager


# ── Page Views ────────────────────────────────────────────────

def loadWebmail(request):
    try:
        wm = WebmailManager(request)
        return wm.loadWebmail()
    except KeyError:
        return redirect(loadLoginPage)


def loadLogin(request):
    wm = WebmailManager(request)
    return wm.loadLogin()


# ── Auth APIs ─────────────────────────────────────────────────

def apiLogin(request):
    try:
        wm = WebmailManager(request)
        return wm.apiLogin()
    except Exception as e:
        return _error_response(e)


def apiLogout(request):
    try:
        wm = WebmailManager(request)
        return wm.apiLogout()
    except Exception as e:
        return _error_response(e)


def apiSSO(request):
    try:
        wm = WebmailManager(request)
        return wm.apiSSO()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiListAccounts(request):
    try:
        wm = WebmailManager(request)
        return wm.apiListAccounts()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiSwitchAccount(request):
    try:
        wm = WebmailManager(request)
        return wm.apiSwitchAccount()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


# ── Folder APIs ───────────────────────────────────────────────

def apiListFolders(request):
    try:
        wm = WebmailManager(request)
        return wm.apiListFolders()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiCreateFolder(request):
    try:
        wm = WebmailManager(request)
        return wm.apiCreateFolder()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiRenameFolder(request):
    try:
        wm = WebmailManager(request)
        return wm.apiRenameFolder()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiDeleteFolder(request):
    try:
        wm = WebmailManager(request)
        return wm.apiDeleteFolder()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


# ── Message APIs ──────────────────────────────────────────────

def apiListMessages(request):
    try:
        wm = WebmailManager(request)
        return wm.apiListMessages()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiSearchMessages(request):
    try:
        wm = WebmailManager(request)
        return wm.apiSearchMessages()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiGetMessage(request):
    try:
        wm = WebmailManager(request)
        return wm.apiGetMessage()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiGetAttachment(request):
    try:
        wm = WebmailManager(request)
        return wm.apiGetAttachment()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


# ── Action APIs ───────────────────────────────────────────────

def apiSendMessage(request):
    try:
        wm = WebmailManager(request)
        return wm.apiSendMessage()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiSaveDraft(request):
    try:
        wm = WebmailManager(request)
        return wm.apiSaveDraft()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiDeleteMessages(request):
    try:
        wm = WebmailManager(request)
        return wm.apiDeleteMessages()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiMoveMessages(request):
    try:
        wm = WebmailManager(request)
        return wm.apiMoveMessages()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiMarkRead(request):
    try:
        wm = WebmailManager(request)
        return wm.apiMarkRead()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiMarkUnread(request):
    try:
        wm = WebmailManager(request)
        return wm.apiMarkUnread()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiMarkFlagged(request):
    try:
        wm = WebmailManager(request)
        return wm.apiMarkFlagged()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


# ── Contact APIs ──────────────────────────────────────────────

def apiListContacts(request):
    try:
        wm = WebmailManager(request)
        return wm.apiListContacts()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiCreateContact(request):
    try:
        wm = WebmailManager(request)
        return wm.apiCreateContact()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiUpdateContact(request):
    try:
        wm = WebmailManager(request)
        return wm.apiUpdateContact()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiDeleteContact(request):
    try:
        wm = WebmailManager(request)
        return wm.apiDeleteContact()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiSearchContacts(request):
    try:
        wm = WebmailManager(request)
        return wm.apiSearchContacts()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiListContactGroups(request):
    try:
        wm = WebmailManager(request)
        return wm.apiListContactGroups()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiCreateContactGroup(request):
    try:
        wm = WebmailManager(request)
        return wm.apiCreateContactGroup()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiDeleteContactGroup(request):
    try:
        wm = WebmailManager(request)
        return wm.apiDeleteContactGroup()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


# ── Sieve Rule APIs ──────────────────────────────────────────

def apiListRules(request):
    try:
        wm = WebmailManager(request)
        return wm.apiListRules()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiCreateRule(request):
    try:
        wm = WebmailManager(request)
        return wm.apiCreateRule()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiUpdateRule(request):
    try:
        wm = WebmailManager(request)
        return wm.apiUpdateRule()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiDeleteRule(request):
    try:
        wm = WebmailManager(request)
        return wm.apiDeleteRule()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiActivateRules(request):
    try:
        wm = WebmailManager(request)
        return wm.apiActivateRules()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


# ── Settings APIs ─────────────────────────────────────────────

def apiGetSettings(request):
    try:
        wm = WebmailManager(request)
        return wm.apiGetSettings()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


def apiSaveSettings(request):
    try:
        wm = WebmailManager(request)
        return wm.apiSaveSettings()
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        return _error_response(e)


# ── Image Proxy ───────────────────────────────────────────────

def apiProxyImage(request):
    try:
        wm = WebmailManager(request)
        return wm.apiProxyImage()
    except Exception as e:
        return _error_response(e)


# ── Helpers ───────────────────────────────────────────────────

def _error_response(e):
    data = {'status': 0, 'error_message': str(e)}
    return HttpResponse(json.dumps(data), content_type='application/json')
