#!/usr/local/CyberCP/bin/python

import os
import os.path
import sys
import django
import mimetypes

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
from plogical.acl import ACLManager
import plogical.CyberCPLogFileWriter as logging
from django.shortcuts import HttpResponse, render, redirect
from loginSystem.models import Administrator
import subprocess
import shlex
import time
from dockerManager.models import Containers
from math import ceil
import docker
import docker.utils
import requests
from plogical.processUtilities import ProcessUtilities
from serverStatus.serverStatusUtil import ServerStatusUtil
import threading as multi


# Use default socket to connect
class ContainerManager(multi.Thread):

    def __init__(self, name=None, function=None, request = None, templateName = None, data = None):
        multi.Thread.__init__(self)
        self.name = name
        self.function = function
        self.request = request
        self.templateName = templateName
        self.data = data

    def renderDM(self):

        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        return render(self.request, self.templateName, self.data)

    def run(self):
        try:
            if self.function == 'submitInstallDocker':
                self.submitInstallDocker()
            elif self.function == 'restartGunicorn':
                command = 'sudo systemctl restart gunicorn.socket'
                ProcessUtilities.executioner(command)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile( str(msg) + ' [ContainerManager.run]')

    @staticmethod
    def executioner(command, statusFile):
        try:
            res = subprocess.call(shlex.split(command), stdout=statusFile, stderr=statusFile)
            if res == 1:
                return 0
            else:
                return 1
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0

    def submitInstallDocker(self):
        try:
            currentACL = ACLManager.loadedACL(self.name)

            if ACLManager.currentContextPermission(currentACL, 'createContainer') == 0:
                return ACLManager.loadError()

            writeToFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')
            writeToFile.close()

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/dockerManager/dockerInstall.py"
            ProcessUtilities.executioner(execPath)

            time.sleep(2)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

    def createContainer(self, request=None, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            adminNames = ACLManager.loadAllUsers(userID)
            tag = request.GET.get('tag')
            image = request.GET.get('image')
            tag = tag.split(" (")[0]

            if "/" in image:
                name = image.split("/")[0] + "." + image.split("/")[1]
            else:
                name = image

            try:
                inspectImage = dockerAPI.inspect_image(image + ":" + tag)
            except docker.errors.ImageNotFound:
                val = request.session['userID']
                admin = Administrator.objects.get(pk=val)
                return render(request, 'dockerManager/images.html', {"type": admin.type,
                                                                     'image': image,
                                                                     'tag': tag})

            envList = {};
            if 'Env' in inspectImage['Config']:
                for item in inspectImage['Config']['Env']:
                    if '=' in item:
                        splitedItem = item.split('=', 1)
                        print(splitedItem)
                        envList[splitedItem[0]] = splitedItem[1]
                    else:
                        envList[item] = ""

            portConfig = {};
            if 'ExposedPorts' in inspectImage['Config']:
                for item in inspectImage['Config']['ExposedPorts']:
                    portDef = item.split('/')
                    portConfig[portDef[0]] = portDef[1]

            if image is None or image is '' or tag is None or tag is '':
                return redirect(loadImages)

            Data = {"ownerList": adminNames, "image": image, "name": name, "tag": tag, "portConfig": portConfig,
                    "envList": envList}

            return render(request, 'dockerManager/runContainer.html', Data)

        except BaseException as msg:
            return HttpResponse(str(msg))

    def loadContainerHome(self, request=None, userID=None, data=None):
        name = self.name

        if ACLManager.checkContainerOwnership(name, userID) != 1:
            return ACLManager.loadError()

        client = docker.from_env()
        dockerAPI = docker.APIClient()
        try:
            container = client.containers.get(name)
        except docker.errors.NotFound as err:
            return HttpResponse("Container not found")

        data = {}
        con = Containers.objects.get(name=name)
        data['name'] = name
        data['image'] = con.image + ":" + con.tag
        data['ports'] = json.loads(con.ports)
        data['cid'] = con.cid
        data['envList'] = json.loads(con.env)
        data['volList'] = json.loads(con.volumes)

        stats = container.stats(decode=False, stream=False)
        logs = container.logs(stream=True)

        data['status'] = container.status
        data['memoryLimit'] = con.memory
        if con.startOnReboot == 1:
            data['startOnReboot'] = 'true'
            data['restartPolicy'] = "Yes"
        else:
            data['startOnReboot'] = 'false'
            data['restartPolicy'] = "No"

        if 'usage' in stats['memory_stats']:
            # Calculate Usage
            # Source: https://github.com/docker/docker/blob/28a7577a029780e4533faf3d057ec9f6c7a10948/api/client/stats.go#L309
            data['memoryUsage'] = (stats['memory_stats']['usage'] / stats['memory_stats']['limit']) * 100

            cpu_count = len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
            data['cpuUsage'] = 0.0
            cpu_delta = float(stats["cpu_stats"]["cpu_usage"]["total_usage"]) - \
                        float(stats["precpu_stats"]["cpu_usage"]["total_usage"])
            system_delta = float(stats["cpu_stats"]["system_cpu_usage"]) - \
                           float(stats["precpu_stats"]["system_cpu_usage"])
            if system_delta > 0.0:
                data['cpuUsage'] = round(cpu_delta / system_delta * 100.0 * cpu_count, 3)
        else:
            data['memoryUsage'] = 0
            data['cpuUsage'] = 0

        return render(request, 'dockerManager/viewContainer.html', data)

    def listContainers(self, request=None, userID=None, data=None):
        try:
            client = docker.from_env()
            dockerAPI = docker.APIClient()

            currentACL = ACLManager.loadedACL(userID)
            containers = ACLManager.findAllContainers(currentACL, userID)

            allContainers = client.containers.list()
            containersList = []
            showUnlistedContainer = True

            # TODO: Add condition to show unlisted Containers only if user has admin level access

            unlistedContainers = []
            for container in allContainers:
                if container.name not in containers:
                    unlistedContainers.append(container)

            if not unlistedContainers:
                showUnlistedContainer = False

            adminNames = ACLManager.loadAllUsers(userID)

            pages = float(len(containers)) / float(10)
            pagination = []

            if pages <= 1.0:
                pages = 1
                pagination.append('<li><a href="\#"></a></li>')
            else:
                pages = ceil(pages)
                finalPages = int(pages) + 1

                for i in range(1, finalPages):
                    pagination.append('<li><a href="\#">' + str(i) + '</a></li>')

            return render(request, 'dockerManager/listContainers.html', {"pagination": pagination,
                                                                         "unlistedContainers": unlistedContainers,
                                                                         "adminNames": adminNames,
                                                                         "showUnlistedContainer": showUnlistedContainer})
        except BaseException as msg:
            return HttpResponse(str(msg))

    def getContainerLogs(self, userID=None, data=None):
        try:
            name = data['name']

            # Check if container is registered in database or unlisted
            if Containers.objects.filter(name=name).exists():
                if ACLManager.checkContainerOwnership(name, userID) != 1:
                    return ACLManager.loadErrorJson('containerLogStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            container = client.containers.get(name)
            logs = container.logs().decode("utf-8")

            data_ret = {'containerLogStatus': 1, 'containerLog': logs, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'containerLogStatus': 0, 'containerLog': 'Error', 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitContainerCreation(self, userID=None, data=None):
        try:

            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('createContainerStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            name = data['name']
            image = data['image']
            tag = data['tag']
            dockerOwner = data['dockerOwner']
            memory = data['memory']
            envList = data['envList']
            volList = data['volList']

            inspectImage = dockerAPI.inspect_image(image + ":" + tag)
            portConfig = {}

            # Formatting envList for usage
            envDict = {}
            for key, value in envList.items():
                if (value['name'] != '') or (value['value'] != ''):
                    envDict[value['name']] = value['value']

            if 'ExposedPorts' in inspectImage['Config']:
                for item in inspectImage['Config']['ExposedPorts']:
                    # Do not allow priviledged port numbers
                    if int(data[item]) < 1024 or int(data[item]) > 65535:
                        data_ret = {'createContainerStatus': 0, 'error_message': "Choose port between 1024 and 65535"}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                    portConfig[item] = data[item]

            volumes = {}
            for index, volume in volList.items():
                volumes[volume['src']] = {'bind': volume['dest'],
                                             'mode': 'rw'}

            ## Create Configurations
            admin = Administrator.objects.get(userName=dockerOwner)

            containerArgs = {'image': image + ":" + tag,
                             'detach': True,
                             'name': name,
                             'ports': portConfig,
                             'publish_all_ports': True,
                             'environment': envDict,
                             'volumes': volumes}

            containerArgs['mem_limit'] = memory * 1048576;  # Converts MB to bytes ( 0 * x = 0 for unlimited memory)

            try:
                container = client.containers.create(**containerArgs)
            except Exception as err:
                if "port is already allocated" in err:  # We need to delete container if port is not available
                    print("Deleting container")
                    container.remove(force=True)
                data_ret = {'createContainerStatus': 0, 'error_message': str(err)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            con = Containers(admin=admin,
                             name=name,
                             tag=tag,
                             image=image,
                             memory=memory,
                             ports=json.dumps(portConfig),
                             volumes=json.dumps(volumes),
                             env=json.dumps(envDict),
                             cid=container.id)

            con.save()

            data_ret = {'createContainerStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'createContainerStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitInstallImage(self, userID=None, data=None):
        try:

            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('installImageStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            image = data['image']
            tag = data['tag']

            try:
                inspectImage = dockerAPI.inspect_image(image + ":" + tag)
                data_ret = {'installImageStatus': 0, 'error_message': "Image already installed"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except docker.errors.ImageNotFound:
                pass

            try:
                image = client.images.pull(image, tag=tag)
                print(image.id)
            except docker.errors.APIError as msg:
                data_ret = {'installImageStatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'installImageStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException as msg:
            data_ret = {'installImageStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitContainerDeletion(self, userID=None, data=None, called=False):
        try:
            name = data['name']
            # Check if container is registered in database or unlisted
            if Containers.objects.filter(name=name).exists():
                if ACLManager.checkContainerOwnership(name, userID) != 1:
                    if called:
                        return 'Permission error'
                    else:
                        return ACLManager.loadErrorJson('websiteDeleteStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            unlisted = data['unlisted']

            if 'force' in data:
                force = True
            else:
                force = False

            if not unlisted:
                containerOBJ = Containers.objects.get(name=name)

            if not force:
                try:
                    container = client.containers.get(name)
                except docker.errors.NotFound as err:
                    if called:
                        return 'Container does not exist'
                    else:
                        data_ret = {'delContainerStatus': 2, 'error_message': 'Container does not exist'}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                try:
                    container.stop()  # Stop container
                    container.kill()  # INCASE graceful stop doesn't work
                except:
                    pass

                try:
                    container.remove()  # Finally remove container
                except docker.errors.APIError as err:
                    data_ret = {'delContainerStatus': 0, 'error_message': str(err)}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                except:
                    if called:
                        return "Unknown"
                    else:
                        data_ret = {'delContainerStatus': 0, 'error_message': 'Unknown error'}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

            if not unlisted and not called:
                containerOBJ.delete()

            if called:
                return 0
            else:
                data_ret = {'delContainerStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            if called:
                return str(msg)
            else:
                data_ret = {'delContainerStatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    def getContainerList(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('listContainerStatus', 0)

            currentACL = ACLManager.loadedACL(userID)
            pageNumber = int(data['page'])
            json_data = self.findContainersJson(currentACL, userID, pageNumber)
            final_dic = {'listContainerStatus': 1, 'error_message': "None", "data": json_data}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
        except BaseException as msg:
            dic = {'listContainerStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def findContainersJson(self, currentACL, userID, pageNumber):
        admin = Administrator.objects.get(pk=userID)
        if admin.acl.adminStatus != 1:
            return ACLManager.loadError()

        finalPageNumber = ((pageNumber * 10)) - 10
        endPageNumber = finalPageNumber + 10
        containers = ACLManager.findContainersObjects(currentACL, userID)[finalPageNumber:endPageNumber]

        json_data = "["
        checker = 0

        for items in containers:
            dic = {'name': items.name, 'admin': items.admin.userName, 'tag': items.tag, 'image': items.image}

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        return json_data

    def doContainerAction(self, userID=None, data=None):
        try:

            name = data['name']
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('containerActionStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            action = data['action']
            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'containerActionStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'containerActionStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                if action == 'start':
                    container.start()
                elif action == 'stop':
                    container.stop()
                elif action == 'restart':
                    container.restart()
                else:
                    data_ret = {'containerActionStatus': 0, 'error_message': 'Unknown Action'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
            except docker.errors.APIError as err:
                data_ret = {'containerActionStatus': 0, 'error_message': str(err)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            time.sleep(3)  # Wait 3 seconds for container to finish starting/stopping/restarting
            status = container.status
            data_ret = {'containerActionStatus': 1, 'error_message': 'None', 'status': status}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'containerActionStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def getContainerStatus(self, userID=None, data=None):
        try:
            name = data['name']
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('containerStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'containerStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'containerStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            status = container.status
            data_ret = {'containerStatus': 1, 'error_message': 'None', 'status': status}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'containerStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def exportContainer(self, request=None, userID=None, data=None):
        try:
            name = request.GET.get('name')
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('containerStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'containerStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'containerStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            eFile = container.export()  # Export with default chunk size
            response = HttpResponse(eFile, content_type='application/force-download')
            response['Content-Disposition'] = 'attachment; filename="' + name + '.tar"'
            return response

        except BaseException as msg:
            data_ret = {'containerStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def getContainerTop(self, userID=None, data=None):
        try:
            name = data['name']
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('containerTopStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'containerTopStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'containerTopStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                top = container.top()
            except docker.errors.APIError as err:
                data_ret = {'containerTopStatus': 0, 'error_message': str(err)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'containerTopStatus': 1, 'error_message': 'None', 'processes': top}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'containerTopStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def assignContainer(self, userID=None, data=None):
        try:
            # Todo: add check only for super user i.e. main admin
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('assignContainerStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            name = data['name']
            dockerOwner = data['admin']

            admin = Administrator.objects.get(userName=dockerOwner)

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'assignContainerStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'assignContainerStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            con = Containers(admin=admin,
                             name=name,
                             cid=container.id)

            con.save()

            data_ret = {'assignContainerStatus': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'assignContainerStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def searchImage(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('searchImageStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            string = data['string']
            try:
                matches = client.images.search(term=string)
            except docker.errors.APIError as err:
                data_ret = {'searchImageStatus': 0, 'error_message': str(err)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'searchImageStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            print(json.dumps(matches))

            for image in matches:
                if "/" in image['name']:
                    image['name2'] = image['name'].split("/")[0] + ":" + image['name'].split("/")[1]
                else:
                    image['name2'] = image['name']

            data_ret = {'searchImageStatus': 1, 'error_message': 'None', 'matches': matches}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'searchImageStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def images(self, request=None, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                imageList = client.images.list()
            except docker.errors.APIError as err:
                return HttpResponse(str(err))

            images = {}
            names = []

            for image in imageList:
                try:
                    name = image.attrs['RepoTags'][0].split(":")[0]
                    if "/" in name:
                        name2 = ""
                        for item in name.split("/"):
                            name2 += ":" + item
                    else:
                        name2 = name

                    tags = []
                    for tag in image.tags:
                        getTag = tag.split(":")
                        if len(getTag) == 2:
                            tags.append(getTag[1])
                    print(tags)
                    if name in names:
                        images[name]['tags'].extend(tags)
                    else:
                        names.append(name)
                        images[name] = {"name": name,
                                        "name2": name2,
                                        "tags": tags}
                except:
                    continue

            return render(request, 'dockerManager/images.html', {"images": images, "test": ''})

        except BaseException as msg:
            return HttpResponse(str(msg))

    def manageImages(self, request=None, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            imageList = client.images.list()

            images = {}
            names = []

            for image in imageList:
                try:
                    name = image.attrs['RepoTags'][0].split(":")[0]
                    if name in names:
                        images[name]['tags'].extend(image.tags)
                    else:
                        names.append(name)
                        images[name] = {"name": name,
                                        "tags": image.tags}
                except:
                    continue

            return render(request, 'dockerManager/manageImages.html', {"images": images})

        except BaseException as msg:
            return HttpResponse(str(msg))

    def getImageHistory(self, userID=None, data=None):
        try:

            name = data['name']

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                image = client.images.get(name)
            except docker.errors.APIError as err:
                data_ret = {'imageHistoryStatus': 0, 'error_message': str(err)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'imageHistoryStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'imageHistoryStatus': 1, 'error_message': 'None', 'history': image.history()}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'imageHistoryStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def removeImage(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            name = data['name']
            try:
                if name == 0:
                    action = client.images.prune()
                else:
                    action = client.images.remove(name)
                print(action)
            except docker.errors.APIError as err:
                data_ret = {'removeImageStatus': 0, 'error_message': str(err)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'removeImageStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'removeImageStatus': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'removeImageStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

            # Internal function for recreating containers

    def doRecreateContainer(self, userID, data, con):
        try:

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            name = data['name']
            unlisted = data['unlisted']  # Pass this as 1 if image is not known for container
            image = data['image']
            tag = data['tag']
            env = data['env']
            volumes = data['volumes']
            port = data['ports']
            memory = data['memory']

            if image == 'unknown':
                return "Image name not known"
            # Call container delete function
            delStatus = self.submitContainerDeletion(userID, data, True)
            if delStatus != 0:
                return delStatus

            containerArgs = {'image': image + ":" + tag,
                             'detach': True,
                             'name': name,
                             'ports': port,
                             'environment': env,
                             'volumes': volumes,
                             'publish_all_ports': True,
                             'mem_limit': memory * 1048576}

            if con.startOnReboot == 1:
                containerArgs['restart_policy'] = {"Name": "always"}

            container = client.containers.create(**containerArgs)
            con.cid = container.id
            con.save()

            return 0
        except BaseException as msg:
            return str(msg)

    def saveContainerSettings(self, userID=None, data=None):
        try:
            name = data['name']
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('saveSettingsStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            memory = data['memory']
            startOnReboot = data['startOnReboot']
            envList = data['envList']
            volList = data['volList']

            if startOnReboot == True:
                startOnReboot = 1
                rPolicy = {"Name": "always"}
            else:
                startOnReboot = 0
                rPolicy = {}

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'saveSettingsStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'saveSettingsStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                container.update(mem_limit=memory * 1048576,
                                 restart_policy=rPolicy)
            except docker.errors.APIError as err:
                data_ret = {'saveSettingsStatus': 0, 'error_message': str(err)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            con = Containers.objects.get(name=name)
            con.memory = memory
            con.startOnReboot = startOnReboot

            if 'envConfirmation' in data and data['envConfirmation']:
                # Formatting envList for usage
                envDict = {}
                for key, value in envList.items():
                    if (value['name'] != '') or (value['value'] != ''):
                        envDict[value['name']] = value['value']

                volumes = {}
                for index, volume in volList.items():
                    if volume['src'] == '' or volume['dest'] == '':
                        continue
                    volumes[volume['src']] = {'bind': volume['dest'],
                                              'mode': 'rw'}
                # Prepare data for recreate function
                data = {
                    'name': name,
                    'unlisted': 0,
                    'image': con.image,
                    'tag': con.tag,
                    'env': envDict,
                    'ports': json.loads(con.ports),
                    'volumes': volumes,
                    'memory': con.memory
                }

                recreateStatus = self.doRecreateContainer(userID, data, con)
                if recreateStatus != 0:
                    data_ret = {'saveSettingsStatus': 0, 'error_message': str(recreateStatus)}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                con.env = json.dumps(envDict)
                con.volumes = json.dumps(volumes)
            con.save()

            data_ret = {'saveSettingsStatus': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'saveSettingsStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def recreateContainer(self, userID=None, data=None):
        try:
            name = data['name']
            if ACLManager.checkContainerOwnership(name, userID) != 1:
                return ACLManager.loadErrorJson('saveSettingsStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                data_ret = {'recreateContainerStatus': 0, 'error_message': 'Container does not exist'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'recreateContainerStatus': 0, 'error_message': 'Unknown'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            con = Containers.objects.get(name=name)

            # Prepare data for recreate function
            data = {
                'name': name,
                'unlisted': 0,
                'image': con.image,
                'tag': con.tag,
                'env': json.loads(con.env),
                'ports': json.loads(con.ports),
                'volumes': json.loads(con.volumes),
                # No filter needed now as its ports are filtered when adding to database
                'memory': con.memory
            }

            recreateStatus = self.doRecreateContainer(userID, data, con)
            if recreateStatus != 0:
                data_ret = {'recreateContainerStatus': 0, 'error_message': str(recreateStatus)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'recreateContainerStatus': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'recreateContainerStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def getTags(self, userID=None, data=None):
        try:

            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            image = data['image']
            page = data['page']

            if ":" in image:
                image2 = image.split(":")[0] + "/" + image.split(":")[1]
            else:
                image2 = "library/" + image

            print(image)
            registryData = requests.get('https://registry.hub.docker.com/v2/repositories/' + image2 + '/tags',
                                        {'page': page}).json()

            tagList = []
            for tag in registryData['results']:
                tagList.append(tag['name'])

            data_ret = {'getTagsStatus': 1, 'list': tagList, 'next': registryData['next'], 'error_message': None}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            data_ret = {'getTagsStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)