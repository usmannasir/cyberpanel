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
    $scope.containerCreationLoading = true;
    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    $scope.goBackDisable = true;

    $scope.volList = {};
    $scope.volListNumber = 0;
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

    var statusFile;

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

        var data = {
            name: name,
            tag: tag,
            memory: memory,
            dockerOwner: dockerOwner,
            image: image,
            envList: $scope.envList,
            volList: $scope.volList

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

    $scope.assignContainer = function (name) {
        $("#assign").modal("show");
        $scope.assignActive = name;
    };

    $scope.submitAssignContainer = function () {
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

app.controller('viewContainer', function ($scope, $http) {
    $scope.cName = "";
    $scope.status = "";
    $scope.savingSettings = false;
    $scope.loadingTop = false;

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

    $scope.refreshStatus = function () {
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
                console.log(response.data.status);
                $scope.status = response.data.status;
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
            PNotify.error({
                title: 'Unable to complete request',
                text: "Problem in connecting to server"
            });
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

        var data = {
            name: $scope.cName,
            memory: $scope.memory,
            startOnReboot: $scope.startOnReboot,
            envConfirmation: $scope.envConfirmation,
            envList: $scope.envList,
            volList: $scope.volList
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