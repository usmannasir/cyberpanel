/**
 * Created by usman on 9/26/17.
 */


/* Java script code to issue SSL */
app.controller('sslIssueCtrl', function($scope,$http) {

    $scope.sslIssueCtrl = true;
    $scope.manageSSLLoading = true;
    $scope.issueSSLBtn = true;
    $scope.canNotIssue = true;
    $scope.sslIssued = true;
    $scope.couldNotConnect = true;

    $scope.showbtn = function () {
      $scope.issueSSLBtn = false;
    };

    $scope.issueSSL = function(){
                $scope.manageSSLLoading = false;

                var url = "/manageSSL/issueSSL";


                var data = {
                    virtualHost:$scope.virtualHost,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.SSL == 1){

                        $scope.sslIssueCtrl = true;
                        $scope.manageSSLLoading = true;
                        $scope.issueSSLBtn = false;
                        $scope.canNotIssue = true;
                        $scope.sslIssued = false;
                        $scope.couldNotConnect = true;

                        $scope.sslDomain = $scope.virtualHost;


                    }

                    else
                    {
                        $scope.sslIssueCtrl = true;
                        $scope.manageSSLLoading = true;
                        $scope.issueSSLBtn = false;
                        $scope.canNotIssue = false;
                        $scope.sslIssued = true;
                        $scope.couldNotConnect = true;
                        $scope.errorMessage = response.data.error_message;

                    }



                }
                function cantLoadInitialDatas(response) {
                    $scope.sslIssueCtrl = true;
                    $scope.manageSSLLoading = true;
                    $scope.issueSSLBtn = false;
                    $scope.canNotIssue = true;
                    $scope.sslIssued = true;
                    $scope.couldNotConnect = false;

                }





    };

});
/* Java script code to issue SSL ends here */


/* Java script code to issue SSL for hostname */
app.controller('sslIssueForHostNameCtrl', function($scope,$http) {

    $scope.sslIssueCtrl = true;
    $scope.manageSSLLoading = true;
    $scope.issueSSLBtn = true;
    $scope.canNotIssue = true;
    $scope.sslIssued = true;
    $scope.couldNotConnect = true;

    $scope.showbtn = function () {
      $scope.issueSSLBtn = false;
    };



    $scope.issueSSL = function(){
                $scope.manageSSLLoading = false;

                var url = "/manageSSL/obtainHostNameSSL";


                var data = {
                    virtualHost:$scope.virtualHost,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.SSL == 1){

                        $scope.sslIssueCtrl = true;
                        $scope.manageSSLLoading = true;
                        $scope.issueSSLBtn = false;
                        $scope.canNotIssue = true;
                        $scope.sslIssued = false;
                        $scope.couldNotConnect = true;

                        $scope.sslDomain = $scope.virtualHost;


                    }

                    else
                    {
                        $scope.sslIssueCtrl = true;
                        $scope.manageSSLLoading = true;
                        $scope.issueSSLBtn = false;
                        $scope.canNotIssue = false;
                        $scope.sslIssued = true;
                        $scope.couldNotConnect = true;
                        $scope.errorMessage = response.data.error_message;

                    }



                }
                function cantLoadInitialDatas(response) {
                    $scope.sslIssueCtrl = true;
                    $scope.manageSSLLoading = true;
                    $scope.issueSSLBtn = false;
                    $scope.canNotIssue = true;
                    $scope.sslIssued = true;
                    $scope.couldNotConnect = false;

                }





    };

});
/* Java script code to issue SSL for hostname */


/* Java script code to issue SSL for MailServer */
app.controller('sslIssueForMailServer', function($scope,$http) {

    $scope.sslIssueCtrl = true;
    $scope.manageSSLLoading = true;
    $scope.issueSSLBtn = true;
    $scope.canNotIssue = true;
    $scope.sslIssued = true;
    $scope.couldNotConnect = true;

    $scope.showbtn = function () {
      $scope.issueSSLBtn = false;
    };


    $scope.issueSSL = function(){

                $scope.manageSSLLoading = false;

                var url = "/manageSSL/obtainMailServerSSL";


                var data = {
                    virtualHost:$scope.virtualHost,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.SSL === 1){

                        $scope.sslIssueCtrl = true;
                        $scope.manageSSLLoading = true;
                        $scope.issueSSLBtn = false;
                        $scope.canNotIssue = true;
                        $scope.sslIssued = false;
                        $scope.couldNotConnect = true;

                        $scope.sslDomain = $scope.virtualHost;


                    }

                    else
                    {
                        $scope.sslIssueCtrl = true;
                        $scope.manageSSLLoading = true;
                        $scope.issueSSLBtn = false;
                        $scope.canNotIssue = false;
                        $scope.sslIssued = true;
                        $scope.couldNotConnect = true;
                        $scope.errorMessage = response.data.error_message;

                    }



                }
                function cantLoadInitialDatas(response) {
                    $scope.sslIssueCtrl = true;
                    $scope.manageSSLLoading = true;
                    $scope.issueSSLBtn = false;
                    $scope.canNotIssue = true;
                    $scope.sslIssued = true;
                    $scope.couldNotConnect = false;

                }





    };

});
/* Java script code to issue SSL for MailServer */