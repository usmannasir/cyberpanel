app.controller('installDocker', function ($scope, $http, $timeout, $window) {
    $scope.installDockerStatus = true;
    $scope.installBoxGen = true;
    $scope.dockerInstallBTN = false;

    $scope.installDocker = function () {

        $scope.installDockerStatus = false;
        $scope.installBoxGen = true;
        $scope.dockerInstallBTN = true;

        url = "/docker/installDocker";

        var data = {};
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                $scope.installBoxGen = false;
                getRequestStatus();
            }
            else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };

    function getRequestStatus() {
        $scope.cyberPanelLoading = false;

        url = "/serverstatus/switchTOLSWSStatus";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            if (response.data.abort === 0) {
                $scope.requestData = response.data.requestStatus;
                $timeout(getRequestStatus, 1000);
            }
            else {
                // Notifications
                $scope.cyberPanelLoading = true;
                $timeout.cancel();
                $scope.requestData = response.data.requestStatus;
                if (response.data.installed === 1) {
                    $timeout(function () {
                        $window.location.reload();
                    }, 3000);
                }

            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });


        }

    }
});

/* Java script code for docker management */
var delayTimer = null;

app.controller('dockerImages', function ($scope) {
    $scope.tagList = [];
    $scope.imageTag = {};
});

/* Java script code to install Container */

app.controller('runContainer', function ($scope, $http) {
    $scope.containerCreationLoading = false;
    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    $scope.goBackDisable = true;

    $scope.volList = {};
    $scope.volListNumber = 0;
    $scope.eport = {};
    $scope.iport = {};
    $scope.portType = {};
    $scope.envList = {};
    
    // Advanced Environment Variable Mode
    $scope.advancedEnvMode = false;
    $scope.advancedEnvText = '';
    $scope.advancedEnvCount = 0;
    $scope.parsedEnvVars = {};
    $scope.addVolField = function () {
        $scope.volList[$scope.volListNumber] = {'dest': '', 'src': ''};
        $scope.volListNumber = $scope.volListNumber + 1;
        console.log($scope.volList)
    };
    $scope.removeVolField = function () {
        delete $scope.volList[$scope.volListNumber - 1];
        $scope.volListNumber = $scope.volListNumber - 1;
    };

    $scope.addEnvField = function () {
        var countEnv = Object.keys($scope.envList).length;
        $scope.envList[countEnv + 1] = {'name': '', 'value': ''};
    };

    // Advanced Environment Variable Functions
    $scope.toggleEnvMode = function() {
        if ($scope.advancedEnvMode) {
            // Switching to advanced mode - convert existing envList to text format
            $scope.convertToAdvancedFormat();
        } else {
            // Switching to simple mode - convert advanced text to envList
            $scope.convertToSimpleFormat();
        }
    };

    $scope.convertToAdvancedFormat = function() {
        var envLines = [];
        for (var key in $scope.envList) {
            if ($scope.envList[key].name && $scope.envList[key].value) {
                envLines.push($scope.envList[key].name + '=' + $scope.envList[key].value);
            }
        }
        $scope.advancedEnvText = envLines.join('\n');
        $scope.parseAdvancedEnv();
    };

    $scope.convertToSimpleFormat = function() {
        $scope.parseAdvancedEnv();
        var newEnvList = {};
        var index = 0;
        for (var key in $scope.parsedEnvVars) {
            newEnvList[index] = {'name': key, 'value': $scope.parsedEnvVars[key]};
            index++;
        }
        $scope.envList = newEnvList;
    };

    $scope.parseAdvancedEnv = function() {
        $scope.parsedEnvVars = {};
        $scope.advancedEnvCount = 0;
        
        if (!$scope.advancedEnvText) {
            return;
        }
        
        var lines = $scope.advancedEnvText.split('\n');
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            
            // Skip empty lines and comments
            if (!line || line.startsWith('#')) {
                continue;
            }
            
            // Parse KEY=VALUE format
            var equalIndex = line.indexOf('=');
            if (equalIndex > 0) {
                var key = line.substring(0, equalIndex).trim();
                var value = line.substring(equalIndex + 1).trim();
                
                // Remove quotes if present
                if ((value.startsWith('"') && value.endsWith('"')) || 
                    (value.startsWith("'") && value.endsWith("'"))) {
                    value = value.slice(1, -1);
                }
                
                if (key && key.match(/^[A-Za-z_][A-Za-z0-9_]*$/)) {
                    $scope.parsedEnvVars[key] = value;
                    $scope.advancedEnvCount++;
                }
            }
        }
    };

    $scope.loadEnvTemplate = function() {
        var templates = {
            'web-app': 'NODE_ENV=production\nPORT=3000\nDATABASE_URL=postgresql://user:pass@localhost/db\nREDIS_URL=redis://localhost:6379\nJWT_SECRET=your-jwt-secret\nAPI_KEY=your-api-key',
            'database': 'POSTGRES_DB=myapp\nPOSTGRES_USER=user\nPOSTGRES_PASSWORD=password\nPOSTGRES_HOST=localhost\nPOSTGRES_PORT=5432',
            'api': 'API_HOST=0.0.0.0\nAPI_PORT=8080\nLOG_LEVEL=info\nCORS_ORIGIN=*\nRATE_LIMIT=1000\nAPI_KEY=your-secret-key',
            'monitoring': 'PROMETHEUS_PORT=9090\nGRAFANA_PORT=3000\nALERTMANAGER_PORT=9093\nRETENTION_TIME=15d\nSCRAPE_INTERVAL=15s'
        };
        
        var templateNames = Object.keys(templates);
        var templateChoice = prompt('Choose a template:\n' + templateNames.map((name, i) => (i + 1) + '. ' + name).join('\n') + '\n\nEnter number or template name:');
        
        if (templateChoice) {
            var templateIndex = parseInt(templateChoice) - 1;
            var selectedTemplate = null;
            
            if (templateIndex >= 0 && templateIndex < templateNames.length) {
                selectedTemplate = templates[templateNames[templateIndex]];
            } else {
                // Try to find by name
                var templateName = templateChoice.toLowerCase().replace(/\s+/g, '-');
                if (templates[templateName]) {
                    selectedTemplate = templates[templateName];
                }
            }
            
            if (selectedTemplate) {
                if ($scope.advancedEnvMode) {
                    $scope.advancedEnvText = selectedTemplate;
                    $scope.parseAdvancedEnv();
                } else {
                    // Convert template to simple format
                    var lines = selectedTemplate.split('\n');
                    $scope.envList = {};
                    var index = 0;
                    for (var i = 0; i < lines.length; i++) {
                        var line = lines[i].trim();
                        if (line && !line.startsWith('#')) {
                            var equalIndex = line.indexOf('=');
                            if (equalIndex > 0) {
                                $scope.envList[index] = {
                                    'name': line.substring(0, equalIndex).trim(),
                                    'value': line.substring(equalIndex + 1).trim()
                                };
                                index++;
                            }
                        }
                    }
                }
                
                new PNotify({
                    title: 'Template Loaded',
                    text: 'Environment variable template has been loaded successfully',
                    type: 'success'
                });
            }
        }
    };

    // Helper function to generate Docker Compose YAML
    function generateDockerComposeYml(containerInfo) {
        var yml = 'version: \'3.8\'\n\n';
        yml += 'services:\n';
        yml += '  ' + containerInfo.name + ':\n';
        yml += '    image: ' + containerInfo.image + '\n';
        yml += '    container_name: ' + containerInfo.name + '\n';
        
        // Add ports
        var ports = Object.keys(containerInfo.ports);
        if (ports.length > 0) {
            yml += '    ports:\n';
            for (var i = 0; i < ports.length; i++) {
                var port = ports[i];
                if (containerInfo.ports[port]) {
                    yml += '      - "' + containerInfo.ports[port] + ':' + port + '"\n';
                }
            }
        }
        
        // Add volumes
        var volumes = Object.keys(containerInfo.volumes);
        if (volumes.length > 0) {
            yml += '    volumes:\n';
            for (var i = 0; i < volumes.length; i++) {
                var volume = volumes[i];
                if (containerInfo.volumes[volume]) {
                    yml += '      - ' + containerInfo.volumes[volume] + ':' + volume + '\n';
                }
            }
        }
        
        // Add environment variables
        var envVars = Object.keys(containerInfo.environment);
        if (envVars.length > 0) {
            yml += '    environment:\n';
            for (var i = 0; i < envVars.length; i++) {
                var envVar = envVars[i];
                yml += '      - ' + envVar + '=' + containerInfo.environment[envVar] + '\n';
            }
        }
        
        // Add restart policy
        yml += '    restart: unless-stopped\n';
        
        return yml;
    }

    // Docker Compose Functions for runContainer
    $scope.generateDockerCompose = function() {
        // Get container information from form
        var containerInfo = {
            name: $scope.name || 'my-container',
            image: $scope.image || 'nginx:latest',
            ports: $scope.eport || {},
            volumes: $scope.volList || {},
            environment: {}
        };
        
        // Collect environment variables
        if ($scope.advancedEnvMode && $scope.parsedEnvVars) {
            containerInfo.environment = $scope.parsedEnvVars;
        } else {
            for (var key in $scope.envList) {
                if ($scope.envList[key].name && $scope.envList[key].value) {
                    containerInfo.environment[$scope.envList[key].name] = $scope.envList[key].value;
                }
            }
        }
        
        // Generate docker-compose.yml content
        var composeContent = generateDockerComposeYml(containerInfo);
        
        // Create and download file
        var blob = new Blob([composeContent], { type: 'text/yaml' });
        var url = window.URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'docker-compose.yml';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        new PNotify({
            title: 'Docker Compose Generated',
            text: 'docker-compose.yml file has been generated and downloaded',
            type: 'success'
        });
    };

    $scope.generateEnvFile = function() {
        var envText = '';
        
        if ($scope.advancedEnvMode && $scope.advancedEnvText) {
            envText = $scope.advancedEnvText;
        } else {
            // Convert simple mode to .env format
            for (var key in $scope.envList) {
                if ($scope.envList[key].name && $scope.envList[key].value) {
                    envText += $scope.envList[key].name + '=' + $scope.envList[key].value + '\n';
                }
            }
        }
        
        if (!envText.trim()) {
            new PNotify({
                title: 'Nothing to Generate',
                text: 'No environment variables to generate .env file',
                type: 'warning'
            });
            return;
        }
        
        // Create and download file
        var blob = new Blob([envText], { type: 'text/plain' });
        var url = window.URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = '.env';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        new PNotify({
            title: '.env File Generated',
            text: '.env file has been generated and downloaded',
            type: 'success'
        });
    };

    $scope.showComposeHelp = function() {
        var helpContent = `
            <div class="compose-help-content">
                <h4><i class="fas fa-info-circle"></i> How to use Docker Compose with Environment Variables</h4>
                <div class="help-steps">
                    <h5>Step 1: Download Files</h5>
                    <p>Click "Generate docker-compose.yml" and "Generate .env file" to download both files.</p>
                    
                    <h5>Step 2: Place Files</h5>
                    <p>Place both files in the same directory on your server.</p>
                    
                    <h5>Step 3: Run Docker Compose</h5>
                    <p>Run the following commands in your terminal:</p>
                    <pre><code>docker compose up -d</code></pre>
                    
                    <h5>Step 4: Update Environment Variables</h5>
                    <p>To update environment variables:</p>
                    <ol>
                        <li>Edit the .env file</li>
                        <li>Run: <code>docker compose up -d</code></li>
                        <li>Only the environment variables will be reloaded (no container rebuild needed!)</li>
                    </ol>
                    
                    <h5>Benefits:</h5>
                    <ul>
                        <li>No need to recreate containers</li>
                        <li>Faster environment variable updates</li>
                        <li>Version control friendly</li>
                        <li>Easy to share configurations</li>
                    </ul>
                </div>
            </div>
        `;
        
        // Create modal for help
        var modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h4 class="modal-title">
                            <i class="fas fa-question-circle"></i>
                            Docker Compose Help
                        </h4>
                        <button type="button" class="close" data-dismiss="modal">
                            <span>&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        ${helpContent}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        $(modal).modal('show');
        
        // Remove modal when closed
        $(modal).on('hidden.bs.modal', function() {
            document.body.removeChild(modal);
        });
    };

    $scope.loadEnvFromFile = function() {
        var input = document.createElement('input');
        input.type = 'file';
        input.accept = '.env,text/plain';
        input.onchange = function(event) {
            var file = event.target.files[0];
            if (file) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    $scope.advancedEnvText = e.target.result;
                    $scope.parseAdvancedEnv();
                    $scope.$apply();
                    
                    new PNotify({
                        title: 'File Loaded',
                        text: 'Environment variables loaded from file successfully',
                        type: 'success'
                    });
                };
                reader.readAsText(file);
            }
        };
        input.click();
    };

    $scope.copyEnvToClipboard = function() {
        var textToCopy = '';
        
        if ($scope.advancedEnvMode) {
            textToCopy = $scope.advancedEnvText;
        } else {
            // Convert simple format to text
            var envLines = [];
            for (var key in $scope.envList) {
                if ($scope.envList[key].name && $scope.envList[key].value) {
                    envLines.push($scope.envList[key].name + '=' + $scope.envList[key].value);
                }
            }
            textToCopy = envLines.join('\n');
        }
        
        if (textToCopy) {
            navigator.clipboard.writeText(textToCopy).then(function() {
                new PNotify({
                    title: 'Copied to Clipboard',
                    text: 'Environment variables copied to clipboard',
                    type: 'success'
                });
            }).catch(function(err) {
                // Fallback for older browsers
                var textArea = document.createElement('textarea');
                textArea.value = textToCopy;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                
                new PNotify({
                    title: 'Copied to Clipboard',
                    text: 'Environment variables copied to clipboard',
                    type: 'success'
                });
            });
        }
    };

    $scope.clearAdvancedEnv = function() {
        $scope.advancedEnvText = '';
        $scope.parsedEnvVars = {};
        $scope.advancedEnvCount = 0;
    };

    var statusFile;

    // Watch for changes to validate ports
    $scope.$watchGroup(['name', 'dockerOwner', 'memory'], function() {
        $scope.updateFormValidity();
    });
    
    $scope.$watch('eport', function() {
        $scope.updateFormValidity();
    }, true);
    
    $scope.formIsValid = false;
    
    $scope.updateFormValidity = function() {
        // Basic required fields
        if (!$scope.name || !$scope.dockerOwner || !$scope.memory) {
            $scope.formIsValid = false;
            return;
        }
        
        // Check if all port mappings are filled (if they exist)
        if ($scope.portType && Object.keys($scope.portType).length > 0) {
            for (var port in $scope.portType) {
                if (!$scope.eport || !$scope.eport[port]) {
                    $scope.formIsValid = false;
                    return;
                }
            }
        }
        
        $scope.formIsValid = true;
    };

    $scope.createContainer = function () {

        $scope.containerCreationLoading = true;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;

        $scope.currentStatus = "Starting creation..";

        url = "/docker/submitContainerCreation";

        var name = $scope.name;
        var tag = $scope.tag;
        var memory = $scope.memory;
        var dockerOwner = $scope.dockerOwner;
        var image = $scope.image;
        var numberOfEnv = Object.keys($scope.envList).length;

        // Prepare environment variables based on mode
        var finalEnvList = {};
        if ($scope.advancedEnvMode && $scope.parsedEnvVars) {
            // Use parsed environment variables from advanced mode
            finalEnvList = $scope.parsedEnvVars;
        } else {
            // Convert simple envList to proper format
            for (var key in $scope.envList) {
                if ($scope.envList[key].name && $scope.envList[key].value) {
                    finalEnvList[$scope.envList[key].name] = $scope.envList[key].value;
                }
            }
        }

        var data = {
            name: name,
            tag: tag,
            memory: memory,
            dockerOwner: dockerOwner,
            image: image,
            envList: finalEnvList,
            volList: $scope.volList,
            advancedEnvMode: $scope.advancedEnvMode

        };

        try {
            $.each($scope.portType, function (port, protocol) {
                data[port + "/" + protocol] = $scope.eport[port];
            });
        }
        catch (err) {
        }

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.createContainerStatus === 1) {
                $scope.currentStatus = "Successful. Redirecting...";
                window.location.href = "/docker/view/" + $scope.name
            }
            else {

                $scope.containerCreationLoading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.errorMessageBox = false;
                $scope.success = true;
                $scope.couldNotConnect = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.containerCreationLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }
    };
    $scope.goBack = function () {
        $scope.containerCreationLoading = true;
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

});

/* Javascript code for listing containers */


app.controller('listContainers', function ($scope, $http) {
    $scope.activeLog = "";
    $scope.assignActive = "";
    $scope.dockerOwner = "";

    $scope.assignContainer = function (name) {
        console.log('assignContainer called with:', name);
        $scope.assignActive = name;
        console.log('assignActive set to:', $scope.assignActive);
        $("#assign").modal("show");
    };
    
    // Test function to verify scope is working
    $scope.testScope = function() {
        alert('Scope is working! assignActive: ' + $scope.assignActive + ', dockerOwner: ' + $scope.dockerOwner);
    };

    $scope.submitAssignContainer = function () {
        console.log('submitAssignContainer called');
        console.log('dockerOwner:', $scope.dockerOwner);
        console.log('assignActive:', $scope.assignActive);
        
        if (!$scope.dockerOwner) {
            new PNotify({
                title: 'Error',
                text: 'Please select an owner',
                type: 'error'
            });
            return;
        }
        
        if (!$scope.assignActive) {
            new PNotify({
                title: 'Error', 
                text: 'No container selected',
                type: 'error'
            });
            return;
        }

        url = "/docker/assignContainer";

        var data = {name: $scope.assignActive, admin: $scope.dockerOwner};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {

            if (response.data.assignContainerStatus === 1) {
                new PNotify({
                    title: 'Container assigned successfully',
                    type: 'success'
                });
                window.location.href = '/docker/listContainers';
            }
            else {
                new PNotify({
                    title: 'Unable to complete request',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
            $("#assign").modal("hide");
        }

        function cantLoadInitialData(response) {
            console.log("not good");
            new PNotify({
                title: 'Unable to complete request',
                type: 'error'
            });
            $("#assign").modal("hide");
        }
    };

    $scope.delContainer = function (name, unlisted=false) {
        (new PNotify({
            title: 'Confirmation Needed',
            text: 'Are you sure?',
            icon: 'fa fa-question-circle',
            hide: false,
            confirm: {
                confirm: true
            },
            buttons: {
                closer: false,
                sticker: false
            },
            history: {
                history: false
            }
        })).get().on('pnotify.confirm', function () {
            $('#imageLoading').show();
            url = "/docker/delContainer";

            var data = {name: name, unlisted: unlisted};

            var config = {
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            };

            $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


            function ListInitialData(response) {
                console.log(response);

                if (response.data.delContainerStatus === 1) {
                    location.reload();
                }
                else if (response.data.delContainerStatus === 2) {
                    (new PNotify({
                        title: response.data.error_message,
                        text: 'Delete anyway?',
                        icon: 'fa fa-question-circle',
                        hide: false,
                        confirm: {
                            confirm: true
                        },
                        buttons: {
                            closer: false,
                            sticker: false
                        },
                        history: {
                            history: false
                        }
                    })).get().on('pnotify.confirm', function () {
                        url = "/docker/delContainer";

                        var data = {name: name, unlisted: unlisted, force: 1};

                        var config = {
                            headers: {
                                'X-CSRFToken': getCookie('csrftoken')
                            }
                        };

                        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


                        function ListInitialData(response) {
                            if (response.data.delContainerStatus === 1) {
                                location.reload();
                            }
                            else {
                                $("#listFail").fadeIn();
                                $scope.errorMessage = response.data.error_message;
                            }
                            $('#imageLoading').hide();
                        }

                        function cantLoadInitialData(response) {
                            $('#imageLoading').hide();
                        }
                    })
                }
                else {
                    $("#listFail").fadeIn();
                    $scope.errorMessage = response.data.error_message;
                }
                $('#imageLoading').hide();
            }

            function cantLoadInitialData(response) {
                $('#imageLoading').hide();
            }
        })
    }

    $scope.showLog = function (name, refresh = false) {
        $scope.logs = "";
        if (refresh === false) {
            $('#logs').modal('show');
            $scope.activeLog = name;
        }
        else {
            name = $scope.activeLog;
        }
        $scope.logs = "Loading...";

        url = "/docker/getContainerLogs";

        var data = {name: name};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            console.log(response);

            if (response.data.containerLogStatus === 1) {
                $scope.logs = response.data.containerLog;
            }
            else {
                new PNotify({
                    title: 'Unable to complete request',
                    text: response.data.error_message,
                    type: 'error'
                });

            }
        }

        function cantLoadInitialData(response) {
            new PNotify({
                title: 'Unable to complete request',
                type: 'error'
            });
        }
    };

    url = "/docker/getContainerList";

    var data = {page: 1};

    var config = {
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    };

    $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


    function ListInitialData(response) {
        console.log(response);

        if (response.data.listContainerStatus === 1) {

            var finalData = JSON.parse(response.data.data);
            $scope.ContainerList = finalData;
            console.log($scope.ContainerList);
            $("#listFail").hide();
        }
        else {
            $("#listFail").fadeIn();
            $scope.errorMessage = response.data.error_message;

        }
    }

    function cantLoadInitialData(response) {
        console.log("not good");
    }


    $scope.getFurtherContainersFromDB = function (pageNumber) {

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {page: pageNumber};


        dataurl = "/docker/getContainerList";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            if (response.data.listContainerStatus === 1) {

                var finalData = JSON.parse(response.data.data);
                $scope.ContainerList = finalData;
                $("#listFail").hide();
            }
            else {
                $("#listFail").fadeIn();
                $scope.errorMessage = response.data.error_message;
                console.log(response.data);

            }
        }

        function cantLoadInitialData(response) {
            console.log("not good");
        }


    };
});

/* Java script code for containerr home page */

app.controller('viewContainer', function ($scope, $http, $interval, $timeout) {
    $scope.cName = "";
    $scope.status = "";
    $scope.savingSettings = false;
    $scope.loadingTop = false;
    $scope.statusInterval = null;
    $scope.statsInterval = null;
    
    // Advanced Environment Variable Functions for viewContainer
    $scope.advancedEnvMode = false;
    $scope.advancedEnvText = '';
    $scope.advancedEnvCount = 0;
    $scope.parsedEnvVars = {};
    
    // Auto-refresh status every 5 seconds
    $scope.startStatusMonitoring = function() {
        $scope.statusInterval = $interval(function() {
            $scope.refreshStatus(true); // Silent refresh
        }, 5000);
    };
    
    // Stop monitoring on scope destroy
    $scope.$on('$destroy', function() {
        if ($scope.statusInterval) {
            $interval.cancel($scope.statusInterval);
        }
        if ($scope.statsInterval) {
            $interval.cancel($scope.statsInterval);
        }
    });
    
    // Start monitoring when controller loads
    $timeout(function() {
        $scope.startStatusMonitoring();
    }, 1000);

    $scope.recreate = function () {
        (new PNotify({
            title: 'Confirmation Needed',
            text: 'Are you sure?',
            icon: 'fa fa-question-circle',
            hide: false,
            confirm: {
                confirm: true
            },
            buttons: {
                closer: false,
                sticker: false
            },
            history: {
                history: false
            }
        })).get().on('pnotify.confirm', function () {
            $('#infoLoading').show();

            url = "/docker/recreateContainer";
            var data = {name: $scope.cName};
            var config = {
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            };

            $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);
            function ListInitialData(response) {
                if (response.data.recreateContainerStatus === 1) {
                    new PNotify({
                        title: 'Action completed!',
                        text: 'Redirecting...',
                        type: 'success'
                    });
                    location.reload();
                }
                else {
                    new PNotify({
                        title: 'Unable to complete request',
                        text: response.data.error_message,
                        type: 'error'
                    });

                }
                $('#infoLoading').hide();
            }

            function cantLoadInitialData(response) {
                PNotify.error({
                    title: 'Unable to complete request',
                    text: "Problem in connecting to server"
                });
                $('#actionLoading').hide();
            }
        })
    };

    $scope.addEnvField = function () {
        var countEnv = Object.keys($scope.envList).length;
        $scope.envList[countEnv + 1] = {'name': '', 'value': ''};
    };

    // Advanced Environment Variable Functions for viewContainer
    $scope.toggleEnvMode = function() {
        if ($scope.advancedEnvMode) {
            // Switching to advanced mode - convert existing envList to text format
            $scope.convertToAdvancedFormat();
        } else {
            // Switching to simple mode - convert advanced text to envList
            $scope.convertToSimpleFormat();
        }
    };

    $scope.convertToAdvancedFormat = function() {
        var envLines = [];
        for (var key in $scope.envList) {
            if ($scope.envList[key].name && $scope.envList[key].value) {
                envLines.push($scope.envList[key].name + '=' + $scope.envList[key].value);
            }
        }
        $scope.advancedEnvText = envLines.join('\n');
        $scope.parseAdvancedEnv();
    };

    $scope.convertToSimpleFormat = function() {
        $scope.parseAdvancedEnv();
        var newEnvList = {};
        var index = 0;
        for (var key in $scope.parsedEnvVars) {
            newEnvList[index] = {'name': key, 'value': $scope.parsedEnvVars[key]};
            index++;
        }
        $scope.envList = newEnvList;
    };

    $scope.parseAdvancedEnv = function() {
        $scope.parsedEnvVars = {};
        $scope.advancedEnvCount = 0;
        
        if (!$scope.advancedEnvText) {
            return;
        }
        
        var lines = $scope.advancedEnvText.split('\n');
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i].trim();
            
            // Skip empty lines and comments
            if (!line || line.startsWith('#')) {
                continue;
            }
            
            // Parse KEY=VALUE format
            var equalIndex = line.indexOf('=');
            if (equalIndex > 0) {
                var key = line.substring(0, equalIndex).trim();
                var value = line.substring(equalIndex + 1).trim();
                
                // Remove quotes if present
                if ((value.startsWith('"') && value.endsWith('"')) || 
                    (value.startsWith("'") && value.endsWith("'"))) {
                    value = value.slice(1, -1);
                }
                
                if (key && key.match(/^[A-Za-z_][A-Za-z0-9_]*$/)) {
                    $scope.parsedEnvVars[key] = value;
                    $scope.advancedEnvCount++;
                }
            }
        }
    };

    $scope.copyEnvToClipboard = function() {
        var textToCopy = '';
        
        if ($scope.advancedEnvMode) {
            textToCopy = $scope.advancedEnvText;
        } else {
            // Convert simple format to text
            var envLines = [];
            for (var key in $scope.envList) {
                if ($scope.envList[key].name && $scope.envList[key].value) {
                    envLines.push($scope.envList[key].name + '=' + $scope.envList[key].value);
                }
            }
            textToCopy = envLines.join('\n');
        }
        
        if (textToCopy) {
            navigator.clipboard.writeText(textToCopy).then(function() {
                new PNotify({
                    title: 'Copied to Clipboard',
                    text: 'Environment variables copied to clipboard',
                    type: 'success'
                });
            }).catch(function(err) {
                // Fallback for older browsers
                var textArea = document.createElement('textarea');
                textArea.value = textToCopy;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                
                new PNotify({
                    title: 'Copied to Clipboard',
                    text: 'Environment variables copied to clipboard',
                    type: 'success'
                });
            });
        }
    };

    // Import/Export Functions
    $scope.importEnvFromContainer = function() {
        // Show modal to select container to import from
        $scope.showContainerImportModal = true;
        $scope.loadContainersForImport();
    };

    $scope.loadContainersForImport = function() {
        $scope.importLoading = true;
        $scope.importContainers = [];
        
        $http.get('/dockerManager/loadContainersForImport/', {
            params: {
                currentContainer: $scope.cName
            }
        }).then(function(response) {
            $scope.importContainers = response.data.containers || [];
            $scope.importLoading = false;
        }).catch(function(error) {
            new PNotify({
                title: 'Import Failed',
                text: 'Failed to load containers for import',
                type: 'error'
            });
            $scope.importLoading = false;
        });
    };

    $scope.selectContainerForImport = function(container) {
        $scope.selectedImportContainer = container;
        $scope.loadEnvFromContainer(container.name);
    };

    $scope.loadEnvFromContainer = function(containerName) {
        $scope.importEnvLoading = true;
        
        $http.get('/dockerManager/getContainerEnv/', {
            params: {
                containerName: containerName
            }
        }).then(function(response) {
            if (response.data.success) {
                var envVars = response.data.envVars || {};
                
                if ($scope.advancedEnvMode) {
                    // Convert to .env format
                    var envText = '';
                    for (var key in envVars) {
                        envText += key + '=' + envVars[key] + '\n';
                    }
                    $scope.advancedEnvText = envText;
                    $scope.parseAdvancedEnv();
                } else {
                    // Convert to simple mode
                    $scope.envList = {};
                    var index = 0;
                    for (var key in envVars) {
                        $scope.envList[index] = {'name': key, 'value': envVars[key]};
                        index++;
                    }
                }
                
                $scope.showContainerImportModal = false;
                new PNotify({
                    title: 'Import Successful',
                    text: 'Environment variables imported from ' + containerName,
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Import Failed',
                    text: response.data.message || 'Failed to import environment variables',
                    type: 'error'
                });
            }
            $scope.importEnvLoading = false;
        }).catch(function(error) {
            new PNotify({
                title: 'Import Failed',
                text: 'Failed to import environment variables',
                type: 'error'
            });
            $scope.importEnvLoading = false;
        });
    };

    $scope.exportEnvToFile = function() {
        var envText = '';
        
        if ($scope.advancedEnvMode && $scope.advancedEnvText) {
            envText = $scope.advancedEnvText;
        } else {
            // Convert simple mode to .env format
            for (var key in $scope.envList) {
                if ($scope.envList[key].name && $scope.envList[key].value) {
                    envText += $scope.envList[key].name + '=' + $scope.envList[key].value + '\n';
                }
            }
        }
        
        if (!envText.trim()) {
            new PNotify({
                title: 'Nothing to Export',
                text: 'No environment variables to export',
                type: 'warning'
            });
            return;
        }
        
        // Create and download file
        var blob = new Blob([envText], { type: 'text/plain' });
        var url = window.URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = $scope.cName + '_environment.env';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        new PNotify({
            title: 'Export Successful',
            text: 'Environment variables exported to file',
            type: 'success'
        });
    };

    // Docker Compose Functions
    $scope.generateDockerCompose = function() {
        // Get container information
        var containerInfo = {
            name: $scope.cName,
            image: $scope.image || 'nginx:latest',
            ports: $scope.ports || {},
            volumes: $scope.volList || {},
            environment: {}
        };
        
        // Collect environment variables
        if ($scope.advancedEnvMode && $scope.parsedEnvVars) {
            containerInfo.environment = $scope.parsedEnvVars;
        } else {
            for (var key in $scope.envList) {
                if ($scope.envList[key].name && $scope.envList[key].value) {
                    containerInfo.environment[$scope.envList[key].name] = $scope.envList[key].value;
                }
            }
        }
        
        // Generate docker-compose.yml content
        var composeContent = generateDockerComposeYml(containerInfo);
        
        // Create and download file
        var blob = new Blob([composeContent], { type: 'text/yaml' });
        var url = window.URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'docker-compose.yml';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        new PNotify({
            title: 'Docker Compose Generated',
            text: 'docker-compose.yml file has been generated and downloaded',
            type: 'success'
        });
    };

    $scope.generateEnvFile = function() {
        var envText = '';
        
        if ($scope.advancedEnvMode && $scope.advancedEnvText) {
            envText = $scope.advancedEnvText;
        } else {
            // Convert simple mode to .env format
            for (var key in $scope.envList) {
                if ($scope.envList[key].name && $scope.envList[key].value) {
                    envText += $scope.envList[key].name + '=' + $scope.envList[key].value + '\n';
                }
            }
        }
        
        if (!envText.trim()) {
            new PNotify({
                title: 'Nothing to Generate',
                text: 'No environment variables to generate .env file',
                type: 'warning'
            });
            return;
        }
        
        // Create and download file
        var blob = new Blob([envText], { type: 'text/plain' });
        var url = window.URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = '.env';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        new PNotify({
            title: '.env File Generated',
            text: '.env file has been generated and downloaded',
            type: 'success'
        });
    };

    $scope.showComposeHelp = function() {
        var helpContent = `
            <div class="compose-help-content">
                <h4><i class="fas fa-info-circle"></i> How to use Docker Compose with Environment Variables</h4>
                <div class="help-steps">
                    <h5>Step 1: Download Files</h5>
                    <p>Click "Generate docker-compose.yml" and "Generate .env file" to download both files.</p>
                    
                    <h5>Step 2: Place Files</h5>
                    <p>Place both files in the same directory on your server.</p>
                    
                    <h5>Step 3: Run Docker Compose</h5>
                    <p>Run the following commands in your terminal:</p>
                    <pre><code>docker compose up -d</code></pre>
                    
                    <h5>Step 4: Update Environment Variables</h5>
                    <p>To update environment variables:</p>
                    <ol>
                        <li>Edit the .env file</li>
                        <li>Run: <code>docker compose up -d</code></li>
                        <li>Only the environment variables will be reloaded (no container rebuild needed!)</li>
                    </ol>
                    
                    <h5>Benefits:</h5>
                    <ul>
                        <li>No need to recreate containers</li>
                        <li>Faster environment variable updates</li>
                        <li>Version control friendly</li>
                        <li>Easy to share configurations</li>
                    </ul>
                </div>
            </div>
        `;
        
        // Create modal for help
        var modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h4 class="modal-title">
                            <i class="fas fa-question-circle"></i>
                            Docker Compose Help
                        </h4>
                        <button type="button" class="close" data-dismiss="modal">
                            <span>&times;</span>
                        </button>
                    </div>
                    <div class="modal-body">
                        ${helpContent}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        $(modal).modal('show');
        
        // Remove modal when closed
        $(modal).on('hidden.bs.modal', function() {
            document.body.removeChild(modal);
        });
    };


    $scope.showTop = function () {
        $scope.topHead = [];
        $scope.topProcesses = [];
        $scope.loadingTop = true;
        $("#processes").modal("show");

        url = "/docker/getContainerTop";
        var data = {name: $scope.cName};
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);
        function ListInitialData(response) {
            if (response.data.containerTopStatus === 1) {
                $scope.topHead = response.data.processes.Titles;
                $scope.topProcesses = response.data.processes.Processes;
            }
            else {
                new PNotify({
                    title: 'Unable to complete request',
                    text: response.data.error_message,
                    type: 'error'
                });

            }
            $scope.loadingTop = false;
        }

        function cantLoadInitialData(response) {
            PNotify.error({
                title: 'Unable to complete request',
                text: "Problem in connecting to server"
            });
            $scope.loadingTop = false;
        }

    };

    $scope.cRemove = function () {
        (new PNotify({
            title: 'Confirmation Needed',
            text: 'Are you sure?',
            icon: 'fa fa-question-circle',
            hide: false,
            confirm: {
                confirm: true
            },
            buttons: {
                closer: false,
                sticker: false
            },
            history: {
                history: false
            }
        })).get().on('pnotify.confirm', function () {
            $('#actionLoading').show();

            url = "/docker/delContainer";
            var data = {name: $scope.cName, unlisted: false};
            var config = {
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            };

            $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);
            function ListInitialData(response) {
                if (response.data.delContainerStatus === 1) {
                    new PNotify({
                        title: 'Container deleted!',
                        text: 'Redirecting...',
                        type: 'success'
                    });
                    window.location.href = '/docker/listContainers';
                }
                else {
                    new PNotify({
                        title: 'Unable to complete request',
                        text: response.data.error_message,
                        type: 'error'
                    });
                }
                $('#actionLoading').hide();
            }

            function cantLoadInitialData(response) {
                PNotify.error({
                    title: 'Unable to complete request',
                    text: "Problem in connecting to server"
                });
                $('#actionLoading').hide();
            }
        })
    };

    $scope.refreshStatus = function (silent) {
        url = "/docker/getContainerStatus";
        var data = {name: $scope.cName};
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);
        function ListInitialData(response) {
            if (response.data.containerStatus === 1) {
                var oldStatus = $scope.status;
                $scope.status = response.data.status;
                
                // Animate status change
                if (oldStatus !== $scope.status && !silent) {
                    // Add animation class
                    var statusBadge = document.querySelector('.status-badge');
                    if (statusBadge) {
                        statusBadge.classList.add('status-changed');
                        setTimeout(function() {
                            statusBadge.classList.remove('status-changed');
                        }, 600);
                    }
                    
                    new PNotify({
                        title: 'Status Updated',
                        text: 'Container is now ' + $scope.status,
                        type: 'info',
                        delay: 2000
                    });
                }
            }
            else {
                if (!silent) {
                    new PNotify({
                        title: 'Unable to complete request',
                        text: response.data.error_message,
                        type: 'error'
                    });
                }
            }
        }

        function cantLoadInitialData(response) {
            if (!silent) {
                PNotify.error({
                    title: 'Unable to complete request',
                    text: "Problem in connecting to server"
                });
            }
        }
    };

    $scope.addVolField = function () {
        $scope.volList[$scope.volListNumber] = {'dest': '', 'src': ''};
        $scope.volListNumber = $scope.volListNumber + 1;
    };
    $scope.removeVolField = function () {
        delete $scope.volList[$scope.volListNumber - 1];
        $scope.volListNumber = $scope.volListNumber - 1;
    };

    $scope.saveSettings = function () {
        $('#containerSettingLoading').show();
        url = "/docker/saveContainerSettings";
        $scope.savingSettings = true;

        // Prepare environment variables based on mode
        var finalEnvList = {};
        if ($scope.advancedEnvMode && $scope.parsedEnvVars) {
            // Use parsed environment variables from advanced mode
            finalEnvList = $scope.parsedEnvVars;
        } else {
            // Convert simple envList to proper format
            for (var key in $scope.envList) {
                if ($scope.envList[key].name && $scope.envList[key].value) {
                    finalEnvList[$scope.envList[key].name] = $scope.envList[key].value;
                }
            }
        }

        var data = {
            name: $scope.cName,
            memory: $scope.memory,
            startOnReboot: $scope.startOnReboot,
            envConfirmation: $scope.envConfirmation,
            envList: finalEnvList,
            volList: $scope.volList,
            advancedEnvMode: $scope.advancedEnvMode
        };


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);
        function ListInitialData(response) {
            if (response.data.saveSettingsStatus === 1) {
                if ($scope.envConfirmation) {
                    new PNotify({
                        title: 'Done. Redirecting...',
                        type: 'success'
                    });
                    location.reload();
                }
                else {
                    new PNotify({
                        title: 'Settings Saved',
                        type: 'success'
                    });
                }
            }
            else {
                new PNotify({
                    title: 'Unable to complete request',
                    text: response.data.error_message,
                    type: 'error'
                });

            }
            $('#containerSettingLoading').hide();
            $scope.savingSettings = false;
        }

        function cantLoadInitialData(response) {
            new PNotify({
                title: 'Unable to complete request',
                text: "Problem in connecting to server",
                type: 'error'
            });
            $('#containerSettingLoading').hide();
            $scope.savingSettings = false;
        }

        if ($scope.startOnReboot === true) {
            $scope.rPolicy = "Yes";
        }
        else {
            $scope.rPolicy = "No";
        }

    };

    $scope.cAction = function (action) {
        $('#actionLoading').show();
        url = "/docker/doContainerAction";
        var data = {name: $scope.cName, action: action};
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            console.log(response);

            if (response.data.containerActionStatus === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Action completed',
                    type: 'success'
                });
                $scope.status = response.data.status;
                $scope.refreshStatus()
            }
            else {
                new PNotify({
                    title: 'Unable to complete request',
                    text: response.data.error_message,
                    type: 'error'
                });

            }
            $('#actionLoading').hide();
        }

        function cantLoadInitialData(response) {
            PNotify.error({
                title: 'Unable to complete request',
                text: "Problem in connecting to server"
            });
            $('#actionLoading').hide();
        }

    };

    $scope.loadLogs = function (name) {
        $scope.logs = "Loading...";

        url = "/docker/getContainerLogs";

        var data = {name: name};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            console.log(response);

            if (response.data.containerLogStatus === 1) {
                $scope.logs = response.data.containerLog;
            }
            else {
                $scope.logs = response.data.error_message;

            }
        }

        function cantLoadInitialData(response) {
            console.log("not good");
            $scope.logs = "Error loading log";
        }
    };

    // Command execution functionality
    $scope.commandToExecute = '';
    $scope.executingCommand = false;
    $scope.commandOutput = null;
    $scope.commandHistory = [];

    $scope.showCommandModal = function() {
        $scope.commandToExecute = '';
        $scope.commandOutput = null;
        $("#commandModal").modal("show");
    };

    $scope.executeCommand = function() {
        if (!$scope.commandToExecute.trim()) {
            new PNotify({
                title: 'Error',
                text: 'Please enter a command to execute',
                type: 'error'
            });
            return;
        }

        $scope.executingCommand = true;
        $scope.commandOutput = null;

        url = "/docker/executeContainerCommand";
        var data = {
            name: $scope.cName,
            command: $scope.commandToExecute.trim()
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);

        function ListInitialData(response) {
            console.log(response);
            $scope.executingCommand = false;

            if (response.data.commandStatus === 1) {
                $scope.commandOutput = {
                    command: response.data.command,
                    output: response.data.output,
                    exit_code: response.data.exit_code
                };

                // Add to command history
                $scope.commandHistory.unshift({
                    command: response.data.command,
                    timestamp: new Date()
                });

                // Keep only last 10 commands
                if ($scope.commandHistory.length > 10) {
                    $scope.commandHistory = $scope.commandHistory.slice(0, 10);
                }

                // Show success notification
                new PNotify({
                    title: 'Command Executed',
                    text: 'Command completed with exit code: ' + response.data.exit_code,
                    type: response.data.exit_code === 0 ? 'success' : 'warning'
                });
            }
            else {
                new PNotify({
                    title: 'Command Execution Failed',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialData(response) {
            $scope.executingCommand = false;
            new PNotify({
                title: 'Command Execution Failed',
                text: 'Could not connect to server',
                type: 'error'
            });
        }
    };

    $scope.selectCommand = function(command) {
        $scope.commandToExecute = command;
    };

    $scope.clearOutput = function() {
        $scope.commandOutput = null;
    };

});


/* Java script code for docker image management */
app.controller('manageImages', function ($scope, $http) {
    $scope.tagList = [];
    $scope.showingSearch = false;
    $("#searchResult").hide();

    $scope.pullImage = function (image, tag) {
        function ListInitialDatas(response) {
            if (response.data.installImageStatus === 1) {
                new PNotify({
                    title: 'Image pulled successfully',
                    text: 'Reloading...',
                    type: 'success'
                });
                location.reload()
            }
            else {
                new PNotify({
                    title: 'Failed to complete request',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

            $('#imageLoading').hide();

        }

        function cantLoadInitialDatas(response) {
            $('#imageLoading').hide();
            new PNotify({
                title: 'Failed to complete request',
                type: 'error'
            });
        }

        if (image && tag) {
            $('#imageLoading').show();

            url = "/docker/installImage";
            var data = {
                image: image,
                tag: tag
            };
            var config = {
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            };

            $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        }
        else {
            new PNotify({
                title: 'Unable to complete request',
                text: 'Please select a tag',
                type: 'info'
            });
        }

    }

    $scope.searchImages = function () {
        console.log($scope.searchString);
        if (!$scope.searchString) {
            $("#searchResult").hide();
        }
        else {
            $("#searchResult").show();
        }
        clearTimeout(delayTimer);
        delayTimer = setTimeout(function () {
            $('#imageLoading').show();

            url = "/docker/searchImage";
            var data = {
                string: $scope.searchString
            };
            var config = {
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            };

            $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

            function ListInitialDatas(response) {
                if (response.data.searchImageStatus === 1) {
                    $scope.images = response.data.matches;
                    console.log($scope.images)
                }
                else {
                    new PNotify({
                        title: 'Failed to complete request',
                        text: response.data.error,
                        type: 'error'
                    });
                }

                $('#imageLoading').hide();

            }

            function cantLoadInitialDatas(response) {
                $('#imageLoading').hide();
                new PNotify({
                    title: 'Failed to complete request',
                    type: 'error'
                });
            }
        }, 500);
    }

    function populateTagList(image, page) {
        $('imageLoading').show();
        url = "/docker/getTags"
        var data = {
            image: image,
            page: page + 1
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            if (response.data.getTagsStatus === 1) {
                $scope.tagList[image].splice(-1, 1);
                $scope.tagList[image] = $scope.tagList[image].concat(response.data.list);

                if (response.data.next != null) {
                    $scope.tagList[image].push("Load more");
                }
            }
            else {
                new PNotify({
                    title: 'Unable to complete request',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
            $('#imageLoading').hide();
        }

        function cantLoadInitialData(response) {
            new PNotify({
                title: 'Unable to complete request',
                text: response.data.error_message,
                type: 'error'
            });
            $('#imageLoading').hide();
        }
    }

    $scope.runContainer = function (image) {
        $("#errorMessage").hide();
        if ($scope.imageTag[image] !== undefined) {
            $("#imageList").css("pointer-events", "none");
        }
        else {
            $("#errorMessage").show();
            $scope.errorMessage = "Please select a tag";
        }
    }

    $scope.loadTags = function (event) {
        var pagesloaded = $(event.target).data('pageloaded');
        var image = event.target.id;

        if (!pagesloaded) {
            $scope.tagList[image] = ['Loading...'];
            $(event.target).data('pageloaded', 1);

            populateTagList(image, pagesloaded);
//             $("#"+image+" option:selected").prop("selected", false);
        }
    }

    $scope.selectTag = function () {
        var image = event.target.id;
        var selectedTag = $('#' + image).find(":selected").text();

        if (selectedTag == 'Load more') {
            var pagesloaded = $(event.target).data('pageloaded');
            $(event.target).data('pageloaded', pagesloaded + 1);

            populateTagList(image, pagesloaded);
        }
    }

    $scope.getHistory = function (counter) {
        $('#imageLoading').show();
        var name = $("#" + counter).val()

        url = "/docker/getImageHistory";

        var data = {name: name};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            console.log(response);

            if (response.data.imageHistoryStatus === 1) {
                $('#history').modal('show');
                $scope.historyList = response.data.history;
            }
            else {
                new PNotify({
                    title: 'Unable to complete request',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
            $('#imageLoading').hide();
        }

        function cantLoadInitialData(response) {
            new PNotify({
                title: 'Unable to complete request',
                text: response.data.error_message,
                type: 'error'
            });
            $('#imageLoading').hide();
        }
    }

    $scope.rmImage = function (counter) {

        (new PNotify({
            title: 'Confirmation Needed',
            text: 'Are you sure?',
            icon: 'fa fa-question-circle',
            hide: false,
            confirm: {
                confirm: true
            },
            buttons: {
                closer: false,
                sticker: false
            },
            history: {
                history: false
            }
        })).get().on('pnotify.confirm', function () {
            $('#imageLoading').show();

            if (counter == '0') {
                var name = 0;
            }
            else {
                var name = $("#" + counter).val()
            }

            url = "/docker/removeImage";

            var data = {name: name};

            var config = {
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            };

            $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


            function ListInitialData(response) {
                console.log(response);

                if (response.data.removeImageStatus === 1) {
                    new PNotify({
                        title: 'Image(s) removed',
                        type: 'success'
                    });
                    window.location.href = "/docker/manageImages";
                }
                else {
                    new PNotify({
                        title: 'Unable to complete request',
                        text: response.data.error_message,
                        type: 'error'
                    });
                }
                $('#imageLoading').hide();
            }

            function cantLoadInitialData(response) {
                new PNotify({
                    title: 'Unable to complete request',
                    text: response.data.error_message,
                    type: 'error'
                });
                $('#imageLoading').hide();
            }

        })
    }
});