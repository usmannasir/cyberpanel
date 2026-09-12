# -*- coding: utf-8 -*-
from plogical.mailUtilities import mailUtilities
from plogical.httpProc import httpProc
from pluginHolder.plugin_metadata import installed_plugin_metadata

def installed(request):
    mailUtilities.checkHome()
    proc = httpProc(request, 'pluginHolder/plugins.html',
                    installed_plugin_metadata(), 'admin')
    return proc.render()
