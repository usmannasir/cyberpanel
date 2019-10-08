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

    function($interpolateProvider) {
        $interpolateProvider.startSymbol('{$');
        $interpolateProvider.endSymbol('$}');
    }
]);

application.controller('loginSystem', function($scope,$http,$window) {


    $scope.verifyLoginCredentials = function() {

                $("#verifyingLogin").show();


                var username = $scope.username;
                var password=  $scope.password;
                var languageSelection=  $scope.languageSelection;


                url = "/verifyLogin";

                var data = {
                    username: username,
                    password: password,
                    languageSelection:languageSelection,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


                function ListInitialData(response) {

                    if (response.data.loginStatus === 0)
                    {
                        $scope.errorMessage = response.data.error_message;
                        $("#loginFailed").fadeIn();
                    }
                    else{
                        $("#loginFailed").hide();
                        $window.location.href = '/base/';
                    }



                    $("#verifyingLogin").hide();
                }
                function cantLoadInitialData(response) {}




        };

    $scope.initiateLogin = function($event){
    var keyCode = $event.which || $event.keyCode;
    if (keyCode === 13) {
        $scope.verifyLoginCredentials();

    }

  };


});


/* Java script code to to Check Login status ends here */
