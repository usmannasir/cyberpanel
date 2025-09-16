#!/usr/local/CyberCP/bin/python

import os.path
import sys
import django
from datetime import datetime

from plogical.DockerSites import Docker_Sites

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
from plogical.acl import ACLManager
import plogical.CyberCPLogFileWriter as logging
from django.shortcuts import HttpResponse, render, redirect
from django.urls import reverse
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
from plogical.httpProc import httpProc

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
        proc = httpProc(self.request, self.templateName, self.data, 'admin')
        return proc.render()

    def run(self):
        try:
            if self.function == 'submitInstallDocker':
                self.submitInstallDocker()
            elif self.function == 'restartGunicorn':
                command = 'sudo systemctl restart gunicorn.socket'
                ProcessUtilities.executioner(command)
        except Exception as msg:
            logging.CyberCPLogFileWriter.writeToFile( str(msg) + ' [ContainerManager.run]')

    @staticmethod
    def executioner(command, statusFile):
        try:
            res = subprocess.call(shlex.split(command), stdout=statusFile, stderr=statusFile)
            if res == 1:
                return 0
            else:
                return 1
        except Exception as msg:
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

        except Exception as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

    def createContainer(self, request=None, userID=None, data=None):
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
            proc = httpProc(request, 'dockerManager/images.html', {"type": admin.type,
                                                                 'image': image,
                                                                 'tag': tag})
            return proc.render()

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
            return redirect(reverse('containerImage'))

        Data = {"ownerList": adminNames, "image": image, "name": name, "tag": tag, "portConfig": portConfig,
                "envList": envList}

        template = 'dockerManager/runContainer.html'
        proc = httpProc(request, template, Data, 'admin')
        return proc.render()

    def loadContainerHome(self, request=None, userID=None, data=None):
        try:
            name = self.name

            # Check if user is admin or has container access
            currentACL = ACLManager.loadedACL(userID)
            if currentACL['admin'] != 1:
                # For non-admin users, check container ownership
                if ACLManager.checkContainerOwnership(name, userID) != 1:
                    return ACLManager.loadError()
            # Admin users can access any container, including ones not in database

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            try:
                container = client.containers.get(name)
            except docker.errors.NotFound as err:
                return HttpResponse("Container not found")

            data = {}
            try:
                con = Containers.objects.get(name=name)
                data['name'] = name
                data['image'] = con.image + ":" + con.tag
                data['ports'] = json.loads(con.ports)
                data['cid'] = con.cid
                data['envList'] = json.loads(con.env)
                data['volList'] = json.loads(con.volumes)
                data['memoryLimit'] = con.memory
                if con.startOnReboot == 1:
                    data['startOnReboot'] = 'true'
                    data['restartPolicy'] = "Yes"
                else:
                    data['startOnReboot'] = 'false'
                    data['restartPolicy'] = "No"
            except Containers.DoesNotExist:
                # Container exists in Docker but not in database
                data['name'] = name
                data['image'] = container.image.tags[0] if container.image.tags else "Unknown"
                data['ports'] = {}
                data['cid'] = container.id
                data['envList'] = {}
                data['volList'] = {}
                data['memoryLimit'] = 512
                data['startOnReboot'] = 'false'
                data['restartPolicy'] = "No"

            stats = container.stats(decode=False, stream=False)
            logs = container.logs(stream=True)

            data['status'] = container.status

            if 'usage' in stats['memory_stats']:
                # Calculate Usage
                # Source: https://github.com/docker/docker/blob/28a7577a029780e4533faf3d057ec9f6c7a10948/api/client/stats.go#L309
                data['memoryUsage'] = (stats['memory_stats']['usage'] / stats['memory_stats']['limit']) * 100

                try:
                    cpu_count = len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
                except:
                    cpu_count = 0

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

            template = 'dockerManager/viewContainer.html'
            proc = httpProc(request, template, data, 'admin')
            return proc.render()
        except BaseException as msg:
            return HttpResponse(str(msg))

    def listContainers(self, request=None, userID=None, data=None):
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

        template = 'dockerManager/listContainers.html'
        proc = httpProc(request, template, {"pagination": pagination,
                                            "unlistedContainers": unlistedContainers,
                                            "adminNames": adminNames,
                                            "showUnlistedContainer": showUnlistedContainer}, 'admin')
        return proc.render()

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

            # Formatting envList for usage - handle both simple and advanced modes
            envDict = {}
            
            # Check if advanced mode is being used
            advanced_mode = data.get('advancedEnvMode', False)
            
            if advanced_mode:
                # Advanced mode: envList is already a dictionary of key-value pairs
                envDict = envList
            else:
                # Simple mode: envList is an array of objects with name/value properties
                for key, value in envList.items():
                    if isinstance(value, dict) and (value.get('name', '') != '' or value.get('value', '') != ''):
                        envDict[value['name']] = value['value']
                    elif isinstance(value, str) and value != '':
                        # Handle case where value might be a string (fallback)
                        envDict[key] = value

            if 'ExposedPorts' in inspectImage['Config']:
                for item in inspectImage['Config']['ExposedPorts']:
                    # Check if port data exists and is valid
                    if item in data and data[item]:
                        try:
                            port_num = int(data[item])
                            # Do not allow priviledged port numbers
                            if port_num < 1024 or port_num > 65535:
                                data_ret = {'createContainerStatus': 0, 'error_message': "Choose port between 1024 and 65535"}
                                json_data = json.dumps(data_ret)
                                return HttpResponse(json_data)
                            portConfig[item] = data[item]
                        except (ValueError, TypeError):
                            data_ret = {'createContainerStatus': 0, 'error_message': f"Invalid port number: {data[item]}"}
                            json_data = json.dumps(data_ret)
                            return HttpResponse(json_data)

            volumes = {}
            if volList:
                for index, volume in volList.items():
                    if isinstance(volume, dict) and 'src' in volume and 'dest' in volume:
                        volumes[volume['src']] = {'bind': volume['dest'], 'mode': 'rw'}

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
                # Check if it's a port allocation error by converting to string first
                error_message = str(err)
                if "port is already allocated" in error_message:  # We need to delete container if port is not available
                    print("Deleting container")
                    try:
                        container.remove(force=True)
                    except:
                        pass  # Container might not exist yet
                data_ret = {'createContainerStatus': 0, 'error_message': error_message}
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


        except Exception as msg:
            # Ensure error message is properly converted to string
            error_message = str(msg) if msg else "Unknown error occurred"
            data_ret = {'createContainerStatus': 0, 'error_message': error_message}
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


        except Exception as msg:
            data_ret = {'installImageStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def pullImage(self, userID=None, data=None):
        """
        Pull a Docker image from registry with proper error handling and security checks
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('pullImageStatus', 0)

            client = docker.from_env()
            dockerAPI = docker.APIClient()

            image = data['image']
            tag = data.get('tag', 'latest')

            # Validate image name to prevent injection
            if not self._validate_image_name(image):
                data_ret = {'pullImageStatus': 0, 'error_message': 'Invalid image name format'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            # Check if image already exists
            try:
                inspectImage = dockerAPI.inspect_image(image + ":" + tag)
                data_ret = {'pullImageStatus': 0, 'error_message': "Image already exists locally"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except docker.errors.ImageNotFound:
                pass

            # Pull the image
            try:
                pulled_image = client.images.pull(image, tag=tag)
                data_ret = {
                    'pullImageStatus': 1, 
                    'error_message': "None",
                    'image_id': pulled_image.id,
                    'image_name': image,
                    'tag': tag
                }
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except docker.errors.APIError as err:
                data_ret = {'pullImageStatus': 0, 'error_message': f'Docker API error: {str(err)}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except docker.errors.ImageNotFound as err:
                data_ret = {'pullImageStatus': 0, 'error_message': f'Image not found: {str(err)}'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except Exception as msg:
            data_ret = {'pullImageStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def _validate_image_name(self, image_name):
        """Validate Docker image name to prevent injection attacks"""
        if not image_name or len(image_name) > 255:
            return False
        
        # Allow alphanumeric, hyphens, underscores, dots, and forward slashes
        import re
        pattern = r'^[a-zA-Z0-9._/-]+$'
        return re.match(pattern, image_name) is not None

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

            template = 'dockerManager/images.html'
            proc = httpProc(request, template, {"images": images, "test": ''}, 'admin')
            return proc.render()

        except BaseException as msg:
            return HttpResponse(str(msg))

    def manageImages(self, request=None, userID=None, data=None):
        try:

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

            template = 'dockerManager/manageImages.html'
            proc = httpProc(request, template, {"images": images}, 'admin')
            return proc.render()

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
                # Formatting envList for usage - handle both simple and advanced modes
                envDict = {}
                
                # Check if advanced mode is being used
                advanced_mode = data.get('advancedEnvMode', False)
                
                if advanced_mode:
                    # Advanced mode: envList is already a dictionary of key-value pairs
                    envDict = envList
                else:
                    # Simple mode: envList is an array of objects with name/value properties
                    for key, value in envList.items():
                        if isinstance(value, dict) and (value.get('name', '') != '' or value.get('value', '') != ''):
                            envDict[value['name']] = value['value']
                        elif isinstance(value, str) and value != '':
                            # Handle case where value might be a string (fallback)
                            envDict[key] = value

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


    def getDockersiteList(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()


            name = data['name']

            passdata = {}
            passdata["JobID"] = None
            passdata['name'] = name
            da = Docker_Sites(None, passdata)
            retdata = da.ListContainers()

            data_ret = {'status': 1, 'error_message': 'None', 'data':retdata}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'removeImageStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

            # Internal function for recreating containers

    def getContainerAppinfo(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            name = data['name']
            containerID = data['id']

            # Create a Docker client
            client = docker.from_env()
            container = client.containers.get(containerID)

            # Get detailed container info
            container_info = container.attrs

            # Calculate uptime
            started_at = container_info.get('State', {}).get('StartedAt', '')
            if started_at:
                started_time = datetime.strptime(started_at.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                uptime = datetime.now() - started_time
                uptime_str = str(uptime).split('.')[0]  # Format as HH:MM:SS
            else:
                uptime_str = "N/A"

            # Get container details
            details = {
                'id': container.short_id,
                'name': container.name,
                'status': container.status,
                'created': container_info.get('Created', ''),
                'started_at': started_at,
                'uptime': uptime_str,
                'image': container_info.get('Config', {}).get('Image', ''),
                'ports': container_info.get('NetworkSettings', {}).get('Ports', {}),
                'volumes': container_info.get('Mounts', []),
                'environment': self._mask_sensitive_env(container_info.get('Config', {}).get('Env', [])),
                'memory_usage': container.stats(stream=False)['memory_stats'].get('usage', 0),
                'cpu_usage': container.stats(stream=False)['cpu_stats']['cpu_usage'].get('total_usage', 0)
            }

            data_ret = {'status': 1, 'error_message': 'None', 'data': [1, details]}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def _mask_sensitive_env(self, env_vars):
        """Helper method to mask sensitive data in environment variables"""
        masked_vars = []
        sensitive_keywords = ['password', 'secret', 'key', 'token', 'auth']
        
        for var in env_vars:
            if '=' in var:
                name, value = var.split('=', 1)
                # Check if this is a sensitive variable
                if any(keyword in name.lower() for keyword in sensitive_keywords):
                    masked_vars.append(f"{name}=********")
                else:
                    masked_vars.append(var)
            else:
                masked_vars.append(var)
        
        return masked_vars

    def getContainerApplog(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()


            name = data['name']
            containerID = data['id']

            passdata = {}
            passdata["JobID"] = None
            passdata['name'] = name
            passdata['containerID'] = containerID
            passdata['numberOfLines'] = 50
            da = Docker_Sites(None, passdata)
            retdata = da.ContainerLogs()


            data_ret = {'status': 1, 'error_message': 'None', 'data':retdata}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'removeImageStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def recreateappcontainer(self, userID=None, data=None):
        try:
            from websiteFunctions.models import DockerSites
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            name = data['name']
            WPusername = data['WPusername']
            WPemail = data['WPemail']
            WPpasswd = data['WPpasswd']

            dockersite = DockerSites.objects.get(SiteName=name)

            passdata ={}
            data['JobID'] = ''
            data['Domain'] = dockersite.admin.domain
            data['domain'] = dockersite.admin.domain
            data['WPemail'] = WPemail
            data['Owner'] = dockersite.admin.admin.userName
            data['userID'] = userID
            data['MysqlCPU'] = dockersite.CPUsMySQL
            data['MYsqlRam'] = dockersite.MemoryMySQL
            data['SiteCPU'] = dockersite.CPUsSite
            data['SiteRam'] = dockersite.MemorySite
            data['sitename'] = dockersite.SiteName
            data['WPusername'] = WPusername
            data['WPpasswd'] = WPpasswd
            data['externalApp'] = dockersite.admin.externalApp

            da = Docker_Sites(None, passdata)
            da.RebuildApp()


            data_ret = {'status': 1, 'error_message': 'None',}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'removeImageStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def RestartContainerAPP(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            name = data['name']
            containerID = data['id']

            passdata = {}
            passdata['containerID'] = containerID

            da = Docker_Sites(None, passdata)
            retdata = da.RestartContainer()


            data_ret = {'status': 1, 'error_message': 'None', 'data':retdata}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'removeImageStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def StopContainerAPP(self, userID=None, data=None):
        try:
            admin = Administrator.objects.get(pk=userID)

            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            name = data['name']
            containerID = data['id']

            passdata = {}
            passdata['containerID'] = containerID

            da = Docker_Sites(None, passdata)
            retdata = da.StopContainer()


            data_ret = {'status': 1, 'error_message': 'None', 'data':retdata}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'removeImageStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def executeContainerCommand(self, userID=None, data=None):
        """
        Execute a SAFE command inside a running Docker container with comprehensive security checks
        """
        try:
            # Input validation
            if not data or 'name' not in data or 'command' not in data:
                data_ret = {'commandStatus': 0, 'error_message': 'Missing required parameters: name and command'}
                return HttpResponse(json.dumps(data_ret))

            name = data['name']
            command = data['command'].strip()
            
            # Validate container name
            if not self._validate_container_name(name):
                data_ret = {'commandStatus': 0, 'error_message': 'Invalid container name'}
                return HttpResponse(json.dumps(data_ret))
            
            # Validate and sanitize command
            validation_result = self._validate_command(command)
            if not validation_result['valid']:
                data_ret = {'commandStatus': 0, 'error_message': validation_result['reason']}
                return HttpResponse(json.dumps(data_ret))
            
            # Check container ownership
            if Containers.objects.filter(name=name).exists():
                if ACLManager.checkContainerOwnership(name, userID) != 1:
                    return ACLManager.loadErrorJson('commandStatus', 0)

            # Rate limiting check
            if not self._check_rate_limit(userID, name):
                data_ret = {'commandStatus': 0, 'error_message': 'Rate limit exceeded. Please wait before executing more commands'}
                return HttpResponse(json.dumps(data_ret))

            client = docker.from_env()
            
            try:
                container = client.containers.get(name)
            except docker.errors.NotFound:
                data_ret = {'commandStatus': 0, 'error_message': 'Container does not exist'}
                return HttpResponse(json.dumps(data_ret))
            except Exception as err:
                data_ret = {'commandStatus': 0, 'error_message': f'Error accessing container: {str(err)}'}
                return HttpResponse(json.dumps(data_ret))

            # Check if container is running
            if container.status != 'running':
                data_ret = {'commandStatus': 0, 'error_message': 'Container must be running to execute commands'}
                return HttpResponse(json.dumps(data_ret))

            # Log the command execution attempt
            self._log_command_execution(userID, name, command)

            try:
                # Parse command safely
                import shlex
                try:
                    command_parts = shlex.split(command)
                except ValueError as e:
                    data_ret = {'commandStatus': 0, 'error_message': f'Invalid command syntax: {str(e)}'}
                    return HttpResponse(json.dumps(data_ret))
                
                # Execute command with security restrictions
                # Note: Some commands may need privileged access, but we validate commands first
                exec_result = container.exec_run(
                    command_parts,
                    stdout=True,
                    stderr=True,
                    stdin=False,
                    tty=False,
                    privileged=True,   # Allow privileged mode since commands are whitelisted
                    user='',           # Use container's default user (often root, but commands are validated)
                    detach=False,
                    demux=False,
                    workdir=None,      # Use container's default working directory
                    environment=None   # Use container's default environment
                )
                
                # Get output and exit code
                output = exec_result.output.decode('utf-8', errors='replace') if exec_result.output else ''
                exit_code = exec_result.exit_code
                
                # Limit output size to prevent memory exhaustion
                if len(output) > 10000:  # 10KB limit
                    output = output[:10000] + "\n[Output truncated - exceeded 10KB limit]"
                
                # Log successful execution
                self._log_command_result(userID, name, command, exit_code, len(output))
                
                # Format the response
                data_ret = {
                    'commandStatus': 1, 
                    'error_message': 'None' if exit_code == 0 else f'Command executed with exit code {exit_code}',
                    'output': output,
                    'exit_code': exit_code,
                    'command': command,
                    'timestamp': time.time()
                }
                
                return HttpResponse(json.dumps(data_ret, ensure_ascii=False))
                
            except docker.errors.APIError as err:
                error_msg = f'Docker API error: {str(err)}'
                self._log_command_error(userID, name, command, error_msg)
                data_ret = {'commandStatus': 0, 'error_message': error_msg}
                return HttpResponse(json.dumps(data_ret))
            except Exception as err:
                error_msg = f'Execution error: {str(err)}'
                self._log_command_error(userID, name, command, error_msg)
                data_ret = {'commandStatus': 0, 'error_message': error_msg}
                return HttpResponse(json.dumps(data_ret))

        except Exception as msg:
            error_msg = f'System error: {str(msg)}'
            logging.CyberCPLogFileWriter.writeToFile(f'executeContainerCommand error: {error_msg}')
            data_ret = {'commandStatus': 0, 'error_message': error_msg}
            return HttpResponse(json.dumps(data_ret))

    # Security helper methods for executeContainerCommand
    def _validate_container_name(self, name):
        """Validate container name to prevent injection"""
        if not name or len(name) > 100:
            return False
        # Allow only alphanumeric, hyphens, underscores, and dots
        import re
        return re.match(r'^[a-zA-Z0-9._-]+$', name) is not None

    def _validate_command(self, command):
        """Comprehensive command validation with whitelist approach"""
        if not command or len(command) > 1000:  # Reasonable command length limit
            return {'valid': False, 'reason': 'Command is empty or too long (max 1000 characters)'}
        
        # Define allowed commands (whitelist approach)
        ALLOWED_COMMANDS = {
            # System information
            'whoami', 'id', 'pwd', 'date', 'uptime', 'hostname', 'uname', 'df', 'free', 'lscpu',
            # File operations (safe and necessary)
            'ls', 'cat', 'head', 'tail', 'wc', 'find', 'file', 'stat', 'du', 'tree',
            'mkdir', 'touch', 'ln', 'readlink',
            # Process monitoring
            'ps', 'top', 'htop', 'jobs', 'pgrep', 'pkill', 'killall', 'kill',
            # Network tools
            'ping', 'wget', 'curl', 'nslookup', 'dig', 'netstat', 'ss', 'ifconfig', 'ip',
            # Text processing
            'grep', 'awk', 'sed', 'sort', 'uniq', 'cut', 'tr', 'wc', 'diff',
            # Package management
            'dpkg', 'rpm', 'yum', 'apt', 'apt-get', 'apt-cache', 'aptitude',
            'pip', 'pip3', 'npm', 'composer', 'gem',
            # Environment and system
            'env', 'printenv', 'which', 'type', 'locale', 'timedatectl',
            # Archives and compression
            'tar', 'gzip', 'gunzip', 'zip', 'unzip',
            # Editors (safe ones)
            'nano', 'vi', 'vim',
            # Database clients
            'mysql', 'psql', 'sqlite3', 'redis-cli', 'mongo',
            # Development tools
            'git', 'node', 'python', 'python3', 'php', 'ruby', 'perl', 'java',
            # System services (read-only operations)
            'systemctl', 'service', 'journalctl',
            # Safe utilities
            'echo', 'printf', 'test', 'expr', 'basename', 'dirname', 'realpath',
            'sleep', 'timeout', 'watch', 'yes', 'seq',
            # Log viewing
            'dmesg', 'last', 'lastlog', 'w', 'who'
        }
        
        # Dangerous commands/patterns (blacklist - these override the whitelist)
        DANGEROUS_PATTERNS = [
            # Command injection patterns
            ';', '&&', '||', '`', '$(',
            # Path traversal
            '../', '~/', 
            # Destructive file operations
            'rm -rf', 'rm -r', 'dd if=', 'dd of=', '>>', 'mkfs', 'fdisk',
            # System modification
            'mount', 'umount', 'crontab -e', 'crontab -r',
            # Package installation/removal (allow read-only package commands)
            'apt install', 'apt remove', 'apt purge', 'apt-get install', 
            'apt-get remove', 'apt-get purge', 'yum install', 'yum remove',
            'pip install', 'pip uninstall', 'npm install -g', 'gem install',
            # Dangerous network utilities
            'nc ', 'netcat', 'ncat', 'telnet', 'ssh ', 'scp ', 'rsync',
            # Shell escapes and dangerous execution
            'bash', 'sh ', '/bin/sh', '/bin/bash', 'sudo', 'su ', 'exec',
            'chroot', 'docker ', 'systemctl start', 'systemctl stop', 
            'systemctl enable', 'systemctl disable', 'service start',
            'service stop', 'service restart'
        ]
        
        command_lower = command.lower()
        
        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if pattern in command_lower:
                return {'valid': False, 'reason': f'Command contains dangerous pattern: {pattern}'}
        
        # Extract base command
        first_word = command.strip().split()[0] if command.strip() else ''
        base_command = first_word.split('/')[-1]  # Remove path if present
        
        # Check if base command is in whitelist
        if base_command not in ALLOWED_COMMANDS:
            return {'valid': False, 'reason': f'Command "{base_command}" is not in the allowed list'}
        
        # Additional checks for specific commands
        if base_command in ['find']:
            # Ensure no -exec or dangerous flags
            if '-exec' in command_lower or '-delete' in command_lower:
                return {'valid': False, 'reason': 'Dangerous flags (-exec, -delete) not allowed with find'}
        
        if base_command in ['systemctl', 'service']:
            # Only allow read-only operations
            readonly_ops = ['status', 'show', 'list-units', 'list-unit-files', 'is-active', 'is-enabled']
            if not any(op in command_lower for op in readonly_ops):
                return {'valid': False, 'reason': 'Only read-only operations allowed for systemctl/service'}
        
        if base_command in ['kill', 'pkill', 'killall']:
            # Ensure no dangerous signals
            if '-9' in command or 'SIGKILL' in command.upper():
                return {'valid': False, 'reason': 'SIGKILL (-9) not allowed for safety'}
        
        if base_command in ['wget', 'curl']:
            # Ensure no output redirection to critical system locations
            critical_paths = ['/etc/', '/boot/', '/usr/bin/', '/bin/', '/sbin/', '/usr/sbin/']
            if any(path in command_lower for path in critical_paths):
                return {'valid': False, 'reason': 'Cannot download to critical system directories'}
        
        return {'valid': True, 'reason': 'Command passed validation'}

    def _check_rate_limit(self, userID, containerName):
        """Enhanced rate limiting: max 10 commands per minute per user-container pair"""
        import time
        import os
        import json
        
        # Create rate limit tracking directory
        rate_limit_dir = '/tmp/cyberpanel_docker_rate_limit'
        if not os.path.exists(rate_limit_dir):
            try:
                os.makedirs(rate_limit_dir, mode=0o755)
            except Exception as e:
                # If we can't create rate limit tracking, allow the command but log it
                logging.CyberCPLogFileWriter.writeToFile(f'Warning: Could not create rate limit directory: {str(e)}')
                return True
        
        # Rate limit file per user-container
        rate_file = os.path.join(rate_limit_dir, f'user_{userID}_container_{containerName}')
        current_time = time.time()
        
        try:
            # Read existing timestamps
            timestamps = []
            if os.path.exists(rate_file):
                with open(rate_file, 'r') as f:
                    try:
                        data = json.load(f)
                        timestamps = data.get('timestamps', [])
                    except (json.JSONDecodeError, KeyError):
                        # Fallback to old format
                        f.seek(0)
                        timestamps = [float(line.strip()) for line in f if line.strip()]
            
            # Remove timestamps older than 1 minute
            recent_timestamps = [ts for ts in timestamps if current_time - ts < 60]
            
            # Check if limit exceeded
            if len(recent_timestamps) >= 10:
                logging.CyberCPLogFileWriter.writeToFile(f'Rate limit exceeded for user {userID}, container {containerName}')
                return False
            
            # Add current timestamp
            recent_timestamps.append(current_time)
            
            # Write back to file with JSON format
            with open(rate_file, 'w') as f:
                json.dump({
                    'timestamps': recent_timestamps,
                    'last_updated': current_time,
                    'user_id': userID,
                    'container_name': containerName
                }, f)
            
            return True
            
        except Exception as e:
            # If rate limiting fails, log but allow the command
            logging.CyberCPLogFileWriter.writeToFile(f'Rate limiting error: {str(e)}')
            return True

    def _log_command_execution(self, userID, containerName, command):
        """Log command execution attempts for security monitoring"""
        try:
            from loginSystem.models import Administrator
            admin = Administrator.objects.get(pk=userID)
            username = admin.userName
        except:
            username = f'UserID_{userID}'
        
        log_message = f'DOCKER_COMMAND_EXEC: User={username} Container={containerName} Command="{command}" Time={time.time()}'
        logging.CyberCPLogFileWriter.writeToFile(log_message)

    def _log_command_result(self, userID, containerName, command, exitCode, outputLength):
        """Log command execution results"""
        try:
            from loginSystem.models import Administrator
            admin = Administrator.objects.get(pk=userID)
            username = admin.userName
        except:
            username = f'UserID_{userID}'
        
        log_message = f'DOCKER_COMMAND_RESULT: User={username} Container={containerName} ExitCode={exitCode} OutputLength={outputLength} Time={time.time()}'
        logging.CyberCPLogFileWriter.writeToFile(log_message)

    def _log_command_error(self, userID, containerName, command, errorMsg):
        """Log command execution errors"""
        try:
            from loginSystem.models import Administrator
            admin = Administrator.objects.get(pk=userID)
            username = admin.userName
        except:
            username = f'UserID_{userID}'
        
        log_message = f'DOCKER_COMMAND_ERROR: User={username} Container={containerName} Error="{errorMsg}" Command="{command[:100]}" Time={time.time()}'
        logging.CyberCPLogFileWriter.writeToFile(log_message)