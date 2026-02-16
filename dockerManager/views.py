 # -*- coding: utf-8 -*-


from django.shortcuts import redirect, HttpResponse
from loginSystem.models import Administrator
from loginSystem.views import loadLoginPage
from plogical.DockerSites import Docker_Sites
from plogical.httpProc import httpProc
from .container import ContainerManager
from .decorators import preDockerRun
from plogical.acl import ACLManager
import json

# Create your views here.

# This function checks if user has admin permissions

def dockerPermission(request, userID, context):

    currentACL = ACLManager.loadedACL(userID)

    if currentACL['admin'] != 1:
        if request.method == "POST":
            return ACLManager.loadErrorJson()
        else:
            return ACLManager.loadError()
    else:
        return 0

@preDockerRun
def loadDockerHome(request):
    userID = request.session['userID']
    admin = Administrator.objects.get(pk=userID)
    template = 'dockerManager/index.html'
    proc = httpProc(request, template, {"type": admin.type}, 'admin')
    return proc.render()

def installDocker(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager(userID, 'submitInstallDocker')
        cm.start()

        data_ret = {'status': 1, 'error_message': 'None'}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except Exception as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

@preDockerRun
def installImage(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.submitInstallImage(userID, json.loads(request.body))

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def viewContainer(request, name):
    try:
        if not request.GET._mutable:
            request.GET._mutable = True
        request.GET['name'] = name

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager(name)
        coreResult = cm.loadContainerHome(request, userID)

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        import traceback
        error_msg = f"Error viewing container {name}: {str(e)}\n{traceback.format_exc()}"
        return HttpResponse(error_msg, status=500)

@preDockerRun
def getTags(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.getTags(userID, json.loads(request.body))

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def delContainer(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.submitContainerDeletion(userID, json.loads(request.body))

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def recreateContainer(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.recreateContainer(userID, json.loads(request.body))

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def runContainer(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        return cm.createContainer(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def listContainersPage(request):
    """
    GET /docker/containers: Render HTML page only. Separate URL avoids
    cache/proxy ever serving JSON (listContainers used to return JSON).
    """
    try:
        userID = request.session['userID']
        cm = ContainerManager()
        resp = cm.listContainers(request, userID)
        if hasattr(resp, '__setitem__'):
            resp['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            resp['Pragma'] = 'no-cache'
            resp['Expires'] = '0'
        return resp
    except KeyError:
        return redirect(loadLoginPage)
    except Exception as e:
        from django.shortcuts import render
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
        logging.writeToFile("listContainersPage error: %s" % str(e))
        return render(
            request,
            'baseTemplate/error.html',
            {'error_message': 'Containers page could not be loaded. Check error logs.'},
            status=500
        )


@preDockerRun
def listContainers(request):
    """
    GET: Redirect to /docker/containers (HTML). POST: 405.
    listContainers URL historically returned JSON; caches may serve stale JSON.
    Use /docker/containers for the page to avoid that.
    """
    try:
        request.session['userID']  # ensure logged in
    except KeyError:
        return redirect(loadLoginPage)

    if request.method != 'GET':
        return HttpResponse('Method Not Allowed', status=405)
    from django.urls import reverse
    return redirect(reverse('listContainersPage'))

@preDockerRun
def getContainerLogs(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.getContainerLogs(userID, json.loads(request.body))
        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def submitContainerCreation(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.submitContainerCreation(userID, json.loads(request.body))

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def getContainerList(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        return cm.getContainerList(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def doContainerAction(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.doContainerAction(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def getContainerStatus(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.getContainerStatus(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def exportContainer(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.exportContainer(request, userID)

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def saveContainerSettings(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.saveContainerSettings(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def getContainerTop(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.getContainerTop(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def assignContainer(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.assignContainer(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def searchImage(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.searchImage(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def images(request):
    try:

        userID = request.session['userID']
        cm = ContainerManager()
        coreResult = cm.images(request, userID)

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def manageImages(request):
    try:
        userID = request.session['userID']
        cm = ContainerManager()
        coreResult = cm.manageImages(request, userID)
        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def getImageHistory(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.getImageHistory(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def removeImage(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.removeImage(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def pullImage(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.pullImage(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def getDockersiteList(request):
    import json
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.getDockersiteList(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)



@preDockerRun
def getContainerAppinfo(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.getContainerAppinfo(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


@preDockerRun
def getContainerApplog(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.getContainerApplog(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


@preDockerRun
def recreateappcontainer(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.recreateappcontainer(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


@preDockerRun
def RestartContainerAPP(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.RestartContainerAPP(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


@preDockerRun
def StopContainerAPP(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.StopContainerAPP(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def executeContainerCommand(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.executeContainerCommand(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def updateContainer(request):
    """
    Update container with new image while preserving data using Docker volumes
    """
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.updateContainer(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def deleteContainerWithData(request):
    """
    Delete container and all associated data (volumes)
    """
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.deleteContainerWithData(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def deleteContainerKeepData(request):
    """
    Delete container but preserve data (volumes)
    """
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.deleteContainerKeepData(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


def loadContainersForImport(request):
    """
    Load all containers for import selection, excluding the current container
    """
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        currentContainer = request.GET.get('currentContainer', '')
        
        # Get all containers using Docker API
        import docker
        dockerClient = docker.from_env()
        containers = dockerClient.containers.list(all=True)
        
        containerList = []
        for container in containers:
            # Skip the current container
            if container.name == currentContainer:
                continue
                
            # Get container info
            containerInfo = {
                'name': container.name,
                'image': container.image.tags[0] if container.image.tags else container.image.id,
                'status': container.status,
                'id': container.short_id
            }
            
            # Count environment variables
            try:
                envVars = container.attrs.get('Config', {}).get('Env', [])
                containerInfo['envCount'] = len(envVars)
            except:
                containerInfo['envCount'] = 0
                
            containerList.append(containerInfo)
        
        return HttpResponse(json.dumps({
            'success': 1,
            'containers': containerList
        }), content_type='application/json')
        
    except Exception as e:
        return HttpResponse(json.dumps({
            'success': 0,
            'message': str(e)
        }), content_type='application/json')
    except KeyError:
        return redirect(loadLoginPage)


def getContainerEnv(request):
    """
    Get environment variables from a specific container
    """
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        containerName = request.GET.get('containerName', '')
        
        if not containerName:
            return HttpResponse(json.dumps({
                'success': 0,
                'message': 'Container name is required'
            }), content_type='application/json')
        
        # Get container using Docker API
        import docker
        dockerClient = docker.from_env()
        container = dockerClient.containers.get(containerName)
        
        # Extract environment variables
        envVars = {}
        envList = container.attrs.get('Config', {}).get('Env', [])
        
        for envVar in envList:
            if '=' in envVar:
                key, value = envVar.split('=', 1)
                envVars[key] = value
        
        return HttpResponse(json.dumps({
            'success': 1,
            'envVars': envVars
        }), content_type='application/json')
        
    except Exception as e:
        return HttpResponse(json.dumps({
            'success': 0,
            'message': str(e)
        }), content_type='application/json')
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def getDockerNetworks(request):
    """
    Get list of all Docker networks
    """
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.getDockerNetworks(userID)

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def createDockerNetwork(request):
    """
    Create a new Docker network
    """
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.createDockerNetwork(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def updateContainerPorts(request):
    """
    Update port mappings for an existing container
    """
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        cm = ContainerManager()
        coreResult = cm.updateContainerPorts(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

@preDockerRun
def manageNetworks(request):
    """
    Display the network management page
    """
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        template = 'dockerManager/manageNetworks.html'
        proc = httpProc(request, template, {}, 'admin')
        return proc.render()
    except KeyError:
        return redirect(loadLoginPage)