# -*- coding: utf-8 -*-


from django.shortcuts import render
from plogical.mailUtilities import mailUtilities
import os
from xml.etree import ElementTree


def installed(request):

    mailUtilities.checkHome()
    pluginPath = '/home/cyberpanel/plugins'
    pluginList = []

    if os.path.exists(pluginPath):
        for plugin in os.listdir(pluginPath):
            data = {}
            completePath = '/usr/local/CyberCP/' + plugin + '/meta.xml'
            pluginMetaData = ElementTree.parse(completePath)

            data['name'] = pluginMetaData.find('name').text
            data['type'] = pluginMetaData.find('type').text
            data['desc'] = pluginMetaData.find('description').text
            data['version'] = pluginMetaData.find('version').text

            pluginList.append(data)


    return render(request, 'pluginHolder/plugins.html',{'plugins': pluginList})
