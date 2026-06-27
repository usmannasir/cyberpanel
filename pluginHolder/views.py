# -*- coding: utf-8 -*-
from django.shortcuts import render
from plogical.mailUtilities import mailUtilities
import os
from xml.etree import ElementTree
from plogical.httpProc import httpProc

def installed(request):
    mailUtilities.checkHome()
    pluginPath = '/home/cyberpanel/plugins'
    pluginList = []
    seen = set()

    if os.path.exists(pluginPath):
        for plugin in os.listdir(pluginPath):
            if plugin.startswith('.'):
                continue
            data = {}
            completePath = '/usr/local/CyberCP/' + plugin + '/meta.xml'
            if not os.path.exists(completePath):
                continue
            pluginMetaData = ElementTree.parse(completePath)

            data['name'] = pluginMetaData.find('name').text
            data['type'] = pluginMetaData.find('type').text
            data['desc'] = pluginMetaData.find('description').text
            data['version'] = pluginMetaData.find('version').text
            data['plugin_dir'] = plugin

            pluginList.append(data)
            seen.add(plugin)

    installedPath = '/usr/local/CyberCP'
    for plugin in os.listdir(installedPath):
        if plugin in seen or plugin.startswith('.'):
            continue
        completePath = os.path.join(installedPath, plugin, 'meta.xml')
        if not os.path.exists(completePath):
            continue
        data = {}
        pluginMetaData = ElementTree.parse(completePath)

        data['name'] = pluginMetaData.find('name').text
        data['type'] = pluginMetaData.find('type').text
        data['desc'] = pluginMetaData.find('description').text
        data['version'] = pluginMetaData.find('version').text
        data['plugin_dir'] = plugin

        pluginList.append(data)

    proc = httpProc(request, 'pluginHolder/plugins.html',
                    {'plugins': pluginList}, 'admin')
    return proc.render()
