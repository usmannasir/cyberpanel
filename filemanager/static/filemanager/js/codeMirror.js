function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

var fileManager = angular.module('editFile', []);

fileManager.config(['$interpolateProvider', function ($interpolateProvider) {
    $interpolateProvider.startSymbol('{$');
    $interpolateProvider.endSymbol('$}');
}]);


fileManager.controller('editFileCtrl', function ($scope, $http, $window) {

    $('form').submit(function (e) {
        e.preventDefault();
    });

    var domainName = $("#domainNameInitial").text();

    $scope.editDisable = true;
    // html editor
    $scope.errorMessageEditor = true;
    $scope.htmlEditorLoading = true;
    $scope.saveSuccess = true;

    var url = '/filemanager/controller';

    $scope.getFileContents = function () {


        var data = {
            fileName: $("#completeFilePath").text(),
            method: "readFileContents",
            domainName: domainName
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.htmlEditorLoading = true;

            if (response.data.status === 1) {

                var cm = new CodeMirror.fromTextArea(document.getElementById("fileContent"), {
                    lineNumbers: true,
                    mode: $("#mode").text(),
                    lineWrapping: false,
                    theme: $("#theme").text()
                });

                cm.setValue(response.data.fileContents);
                cm.setSize(null, 800);
                cm.on("keyup", function (cm, event) {
                    if (!cm.state.completionActive &&
                        event.keyCode != 13) {
                        CodeMirror.commands.autocomplete(cm, null, {completeSingle: false});
                    }
                });

            } else {
                $scope.errorMessageEditor = false;
                $scope.error_message = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };
    $scope.getFileContents();

    $scope.changeTheme = function () {
        $window.location.href = window.location.href + '&theme=' + $scope.theme;
    };

    $scope.putFileContents = function () {

        $scope.htmlEditorLoading = false;
        $scope.saveSuccess = true;
        $scope.errorMessageEditor = true;

        var completePathForFile = $scope.currentPath;

        var data = {
            fileName: completePathForFile,
            method: "writeFileContents",
            fileContent: editor.getValue(),
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            $scope.htmlEditorLoading = true;

            if (response.data.status === 1) {
                $scope.htmlEditorLoading = true;
                $scope.saveSuccess = false;
            } else {
                $scope.errorMessageEditor = false;
                $scope.error_message = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };

});