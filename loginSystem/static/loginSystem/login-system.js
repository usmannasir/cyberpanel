/**
 * Created by usman on 7/24/17.
 */

/* Utilities */


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

/* Utilities ends here */


/* Java script code to Check Login status */
$("#verifyingLogin").hide();
$("#loginFailed").hide();


var application = angular.module('loginSystem', []);

application.config(['$interpolateProvider',

    function ($interpolateProvider) {
        $interpolateProvider.startSymbol('{$');
        $interpolateProvider.endSymbol('$}');
    }
]);

application.controller('loginSystem', function ($scope, $http, $window) {

    $scope.verifyCode = true;
    $scope.rememberMe = false;
    $scope.username = '';

    // Username only (never store password in localStorage).
    try {
        if ($window.localStorage.getItem('cpRememberMe') === '1') {
            $scope.rememberMe = true;
            var savedUser = $window.localStorage.getItem('cpRememberUsername') || '';
            // Basic sanitize: strip control chars / keep short login names
            savedUser = String(savedUser).replace(/[\u0000-\u001f\u007f]/g, '').slice(0, 64);
            $scope.username = savedUser;
        }
    } catch (e) { /* private mode */ }

    $scope.verifyLoginCredentials = function () {

        $("#verifyingLogin").show();


        var username = $scope.username;
        var password = $scope.password;
        var languageSelection = $scope.languageSelection;
        var rememberMe = !!$scope.rememberMe;


        url = "/verifyLogin";

        var data = {
            username: username,
            password: password,
            languageSelection: languageSelection,
            twofa: $scope.twofa,
            rememberMe: rememberMe
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            if (response.data.loginStatus === 0) {
                $scope.errorMessage = response.data.error_message;
                $("#loginFailed").fadeIn();
            }else if(response.data.loginStatus === 2){
                $scope.verifyCode = false;
            }
            else {
                $("#loginFailed").hide();
                try {
                    if (rememberMe) {
                        $window.localStorage.setItem('cpRememberMe', '1');
                        $window.localStorage.setItem('cpRememberUsername', String(username || '').slice(0, 64));
                    } else {
                        $window.localStorage.removeItem('cpRememberMe');
                        $window.localStorage.removeItem('cpRememberUsername');
                    }
                } catch (e) { /* private mode */ }
                $window.location.href = '/base/';
            }


            $("#verifyingLogin").hide();
        }

        function cantLoadInitialData(response) {
            $("#verifyingLogin").hide();
        }


    };

    $scope.initiateLogin = function ($event) {
        var keyCode = $event.which || $event.keyCode;
        if (keyCode === 13) {
            $scope.verifyLoginCredentials();

        }

    };


});


/* Java script code to to Check Login status ends here */
