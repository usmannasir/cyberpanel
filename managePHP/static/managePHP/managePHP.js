/**
 * Created by usman on 9/20/17.
 */


app.controller('installExtensions', function ($scope, $http, $timeout) {


    var size = 0;
    var extName = '';

    $scope.availableExtensions = true;
    $scope.loadingExtensions = true;
    $scope.canNotFetch = true;
    $scope.couldNotConnect = true;
    $scope.phpSelectionDisabled = false;
    $scope.request = true;
    $scope.canNotPerform = true;
    $scope.goback = true;

    $scope.fetchPHPDetails = function () {
        $scope.loadingExtensions = false;
        $scope.phpSelectionDisabled = false;
        populateCurrentRecords();
        $scope.request = true;
    };

    $scope.installExt = function (extensionName) {

        extName = extensionName;

        $scope.phpSelectionDisabled = true;
        $scope.requestData = "";

        $scope.loadingExtensions = false;
        $scope.availableExtensions = true;
        $scope.request = false;
        $scope.goback = true;

        url = "/managephp/submitExtensionRequest";

        var data = {
            extensionName: extensionName,
            type: "install"
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.extensionRequestStatus === 1) {

                getRequestStatus();
                $scope.canNotPerform = true;


            }
            else {
                $scope.canNotPerform = false;
                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;
            $scope.canNotPerform = true;


        }


    };

    $scope.uninstallExt = function (extensionName) {

        extName = extensionName;

        $scope.phpSelectionDisabled = true;
        $scope.requestData = "";
        $scope.goback = true;

        $scope.loadingExtensions = false;
        $scope.availableExtensions = true;
        $scope.request = false;

        url = "/managephp/submitExtensionRequest";

        var data = {
            extensionName: extensionName,
            type: "uninstall"
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.extensionRequestStatus == 1) {

                getRequestStatus();
                $scope.canNotPerform = true;


            }
            else {
                $scope.canNotPerform = false;
                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;
            $scope.canNotPerform = true;


        }


    };

    function populateCurrentRecords() {

        var phpSelection = $scope.phpSelection;

        url = "/managephp/getExtensionsInformation";

        var data = {
            phpSelection: phpSelection,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.fetchStatus === 1) {

                $scope.records = JSON.parse(response.data.data);

                $scope.availableExtensions = false;
                $scope.loadingExtensions = true;

                $scope.canNotFetch = true;
                $scope.couldNotConnect = true;


            }
            else {
                $scope.errorMessage = response.data.error_message;
                $scope.canNotFetch = false;
                $scope.couldNotConnect = true;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;


        }

    }

    function getRequestStatus() {


        url = "/managephp/getRequestStatus";

        var data = {
            size: size,
            extensionName: extName,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.extensionRequestStatus === 1) {

                if (response.data.finished === 1) {

                    $scope.loadingExtensions = true;
                    $scope.phpSelectionDisabled = false;
                    $scope.requestData = response.data.requestStatus;
                    $scope.goback = false;
                    $timeout.cancel();

                }
                else {
                    size = Number(response.data.size);
                    $scope.requestData = response.data.requestStatus;
                    $timeout(getRequestStatus, 1000);
                }


            }
            else {


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;


        }


    }


});


app.controller('editPHPConfig', function ($scope, $http, $timeout) {

    $scope.loadingPHP = true;
    $scope.canNotFetch = true;
    $scope.phpDetailsBox = true;
    $scope.couldNotConnect = true;
    $scope.detailsSaved = true;
    $scope.savebtn = true;
    $scope.configDataView = true;
    $scope.canNotFetchAdvanced = true;
    $scope.detailsSavedAdvanced = true;
    $scope.savebtnAdvance = true;

    var allow_url_fopen = false;
    var display_errors = false;
    var file_uploads = false;
    var allow_url_include = false;


    $('#allow_url_fopen').change(function () {
        allow_url_fopen = $(this).prop('checked');
    });

    $('#display_errors').change(function () {
        display_errors = $(this).prop('checked');
    });


    $('#file_uploads').change(function () {
        file_uploads = $(this).prop('checked');
    });

    $('#allow_url_include').change(function () {
        allow_url_include = $(this).prop('checked');
    });


    $scope.fetchPHPDetails = function () {
        $scope.loadingPHP = false;
        $scope.canNotFetch = true;
        $scope.detailsSaved = true;


        $('#allow_url_fopen').bootstrapToggle('off');
        $('#display_errors').bootstrapToggle('off');
        $('#file_uploads').bootstrapToggle('off');
        $('#allow_url_include').bootstrapToggle('off');

        url = "/managephp/getCurrentPHPConfig";

        var phpSelection = $scope.phpSelection;

        var data = {
            phpSelection: phpSelection,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.fetchStatus == 1) {

                $scope.savebtn = false;


                if (response.data.allow_url_fopen === "1") {
                    $('#allow_url_fopen').bootstrapToggle('on');
                }
                if (response.data.display_errors === "1") {
                    $('#display_errors').bootstrapToggle('on');
                }
                if (response.data.file_uploads === "1") {
                    $('#file_uploads').bootstrapToggle('on');
                }
                if (response.data.allow_url_include === "1") {
                    $('#allow_url_include').bootstrapToggle('on');
                }

                $scope.loadingPHP = true;

                $scope.memory_limit = response.data.memory_limit;
                $scope.max_execution_time = response.data.max_execution_time;
                $scope.upload_max_filesize = response.data.upload_max_filesize;
                $scope.max_input_time = response.data.max_input_time;
                $scope.post_max_size = response.data.post_max_size;

                $scope.phpDetailsBox = false;


            }
            else {

                $scope.errorMessage = response.data.error_message;
                $scope.canNotFetch = false;
                $scope.loadingPHP = true;
                $scope.phpDetailsBox = true;
            }

        }

        function cantLoadInitialDatas(response) {


            $scope.couldNotConnect = false;


        }

    };


    $scope.saveChanges = function () {

        $scope.loadingPHP = false;

        var phpSelection = $scope.phpSelection;

        url = "/managephp/savePHPConfigBasic";

        var data = {
            phpSelection: phpSelection,
            allow_url_fopen: allow_url_fopen,
            display_errors: display_errors,
            file_uploads: file_uploads,
            allow_url_include: allow_url_include,
            memory_limit: $scope.memory_limit,
            max_execution_time: $scope.max_execution_time,
            upload_max_filesize: $scope.upload_max_filesize,
            max_input_time: $scope.max_input_time,
            post_max_size: $scope.post_max_size,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.saveStatus === 1) {

                $scope.detailsSaved = false;
                $scope.loadingPHP = true;

            }
            else {
                $scope.errorMessage = response.data.error_message;
                $scope.canNotFetch = false;
                $scope.couldNotConnect = true;
                $scope.loadingPHP = true;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;
            $scope.loadingPHP = true;


        }


    };


    $scope.fetchAdvancePHPDetails = function () {
        $scope.loadingPHP = false;
        $scope.savebtnAdvance = true;


        url = "/managephp/getCurrentAdvancedPHPConfig";

        var phpSelection = $scope.phpSelection;

        var data = {
            phpSelection: phpSelection,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.fetchStatus == 1) {

                $scope.configDataView = false;
                $scope.configData = response.data.configData;
                $scope.loadingPHP = true;

                $scope.canNotFetchAdvanced = true;
                $scope.detailsSavedAdvanced = true;
                $scope.savebtnAdvance = false;


            }
            else {
                $scope.canNotFetchAdvanced = false;
                $scope.detailsSavedAdvanced = true;
                $scope.loadingPHP = true;

                $scope.errorMessage = response.data.error_message;
                $scope.configDataView = true;

            }

        }

        function cantLoadInitialDatas(response) {


            $scope.couldNotConnect = false;
            $scope.loadingPHP = true;


        }

    };


    $scope.saveChangesAdvance = function () {

        $scope.loadingPHP = false;

        var phpSelection = $scope.phpSelection;

        url = "/managephp/savePHPConfigAdvance";

        var data = {
            phpSelection: phpSelection,
            configData: $scope.configData,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.saveStatus == 1) {

                $scope.detailsSavedAdvanced = false;
                $scope.loadingPHP = true;

            }
            else {
                $scope.errorMessage = response.data.error_message;
                $scope.canNotFetchAdvanced = false;
                $scope.couldNotConnect = true;
                $scope.loadingPHP = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;
            $scope.canNotFetchAdvanced = true;
            $scope.couldNotConnect = true;
            $scope.loadingPHP = true;


        }


    };


});


