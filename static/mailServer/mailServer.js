/**
 * Created by usman on 8/15/17.
 */


/* Java script code to create account */
app.controller('createEmailAccount', function($scope,$http) {

    $scope.emailDetails = true;
    $scope.emailLoading = true;
    $scope.canNotCreate = true;
    $scope.successfullyCreated = true;
    $scope.couldNotConnect = true;

    $scope.showEmailDetails = function(){

        $scope.emailDetails = false;
        $scope.emailLoading = true;
        $scope.canNotCreate = true;
        $scope.successfullyCreated = true;
        $scope.couldNotConnect = true;


        $scope.selectedDomain = $scope.emailDomain;


    };



    $scope.createEmailAccount = function(){

                $scope.emailDetails = false;
                $scope.emailLoading = false;
                $scope.canNotCreate = true;
                $scope.successfullyCreated = true;
                $scope.couldNotConnect = true;



                var url = "/email/submitEmailCreation";

                var domain = $scope.emailDomain;
                var username = $scope.emailUsername;
                var password = $scope.emailPassword;


                var data = {
                    domain:domain,
                    username:username,
                    password:password,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.createEmailStatus == 1){

                        $scope.emailDetails = false;
                        $scope.emailLoading = true;
                        $scope.canNotCreate = true;
                        $scope.successfullyCreated = false;
                        $scope.couldNotConnect = true;

                        $scope.createdID = username + "@" + domain;


                    }

                    else
                    {
                        $scope.emailDetails = false;
                        $scope.emailLoading = true;
                        $scope.canNotCreate = false;
                        $scope.successfullyCreated = true;
                        $scope.couldNotConnect = true;

                        $scope.errorMessage = response.data.error_message;


                    }



                }
                function cantLoadInitialDatas(response) {

                    $scope.emailDetails = false;
                    $scope.emailLoading = true;
                    $scope.canNotCreate = true;
                    $scope.successfullyCreated = true;
                    $scope.couldNotConnect = false;



                }





    };

    $scope.hideFewDetails = function(){

        $scope.successfullyCreated = true;


    };

});
/* Java script code to create account ends here */



/* Java script code to create account */
app.controller('deleteEmailAccount', function($scope,$http) {

    $scope.emailDetails = true;
    $scope.emailLoading = true;
    $scope.canNotDelete = true;
    $scope.successfullyDeleted = true;
    $scope.couldNotConnect = true;
    $scope.emailDetailsFinal = true;
    $scope.noEmails = true;

    $scope.showEmailDetails = function(){

        $scope.emailDetails = true;
        $scope.emailLoading = false;
        $scope.canNotDelete = true;
        $scope.successfullyDeleted = true;
        $scope.couldNotConnect = true;
        $scope.emailDetailsFinal = true;
        $scope.noEmails = true;


        var url = "/email/getEmailsForDomain";

        var domain = $scope.emailDomain;



                var data = {
                    domain:domain,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.fetchStatus == 1){

                        $scope.emails = JSON.parse(response.data.data);


                        $scope.emailDetails = false;
                        $scope.emailLoading = true;
                        $scope.canNotDelete = true;
                        $scope.successfullyDeleted = true;
                        $scope.couldNotConnect = true;
                        $scope.emailDetailsFinal = true;
                        $scope.noEmails = true;





                    }

                    else
                    {
                         $scope.emailDetails = true;
                         $scope.emailLoading = true;
                         $scope.canNotDelete = true;
                         $scope.successfullyDeleted = true;
                         $scope.couldNotConnect = true;
                         $scope.emailDetailsFinal = true;
                         $scope.noEmails = false;

                    }



                }
                function cantLoadInitialDatas(response) {

                    $scope.emailDetails = true;
                         $scope.emailLoading = true;
                         $scope.canNotDelete = true;
                         $scope.successfullyDeleted = true;
                         $scope.couldNotConnect = false;
                         $scope.emailDetailsFinal = true;
                         $scope.noEmails = true;



                }






    };


    $scope.deleteEmailAccountFinal = function(){

        $scope.emailLoading = false;


        var url = "/email/submitEmailDeletion";

        var email = $scope.selectedEmail;



                var data = {
                    email:email,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.deleteEmailStatus == 1){


                        $scope.emailDetails = true;
                        $scope.emailLoading = true;
                        $scope.canNotDelete = true;
                        $scope.successfullyDeleted = false;
                        $scope.couldNotConnect = true;
                        $scope.emailDetailsFinal = true;
                        $scope.noEmails = true;

                         $scope.deletedID = email;

                    }

                    else
                    {
                            $scope.emailDetails = true;
                            $scope.emailLoading = true;
                            $scope.canNotDelete = false;
                            $scope.successfullyDeleted = true;
                            $scope.couldNotConnect = true;
                            $scope.emailDetailsFinal = true;
                            $scope.noEmails = true;

                            $scope.errorMessage = response.data.error_message;

                    }



                }
                function cantLoadInitialDatas(response) {

                            $scope.emailDetails = true;
                            $scope.emailLoading = true;
                            $scope.canNotDelete = true;
                            $scope.successfullyDeleted = true;
                            $scope.couldNotConnect = false;
                            $scope.emailDetailsFinal = true;
                            $scope.noEmails = true;



                }






    };



    $scope.deleteEmailAccount = function(){

        var domain = $scope.selectedEmail;

        if(domain.length>0) {
            $scope.emailDetailsFinal = false;
        }

    };

});
/* Java script code to create account ends here */



/* Java script code to create account */
app.controller('changeEmailPassword', function($scope,$http) {

    $scope.emailLoading = true;
    $scope.emailDetails = true;
    $scope.canNotChangePassword = true;
    $scope.passwordChanged = true;
    $scope.couldNotConnect = true;
    $scope.noEmails = true;

    $scope.showEmailDetails = function(){

        $scope.emailLoading = false;
        $scope.emailDetails = true;
        $scope.canNotChangePassword = true;
        $scope.passwordChanged = true;
        $scope.couldNotConnect = true;
        $scope.noEmails = true;


        var url = "/email/getEmailsForDomain";

        var domain = $scope.emailDomain;



                var data = {
                    domain:domain,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.fetchStatus == 1){

                        $scope.emails = JSON.parse(response.data.data);


                        $scope.emailLoading = true;
                        $scope.emailDetails = false;
                        $scope.canNotChangePassword = true;
                        $scope.passwordChanged = true;
                        $scope.couldNotConnect = true;
                        $scope.noEmails = true;





                    }

                    else
                    {
                         $scope.emailLoading = true;
                        $scope.emailDetails = true;
                        $scope.canNotChangePassword = true;
                        $scope.passwordChanged = true;
                        $scope.couldNotConnect = true;
                        $scope.noEmails = false;

                    }



                }
                function cantLoadInitialDatas(response) {

                    $scope.emailLoading = true;
                    $scope.emailDetails = true;
                    $scope.canNotChangePassword = true;
                    $scope.passwordChanged = true;
                    $scope.couldNotConnect = false;
                    $scope.noEmails = true;



                }

    };


    $scope.changePassword = function(){

        $scope.emailLoading = false;


        var url = "/email/submitPasswordChange";

        var email = $scope.selectedEmail;
        var password = $scope.emailPassword;
        var domain = $scope.emailDomain;



                var data = {
                    domain:domain,
                    email:email,
                    password:password,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.passChangeStatus == 1){


                        $scope.emailLoading = true;
                        $scope.emailDetails = true;
                        $scope.canNotChangePassword = true;
                        $scope.passwordChanged = false;
                        $scope.couldNotConnect = true;
                        $scope.noEmails = true;

                        $scope.passEmail = email;

                    }

                    else
                    {
                        $scope.emailLoading = true;
                        $scope.emailDetails = false;
                        $scope.canNotChangePassword = false;
                        $scope.passwordChanged = true;
                        $scope.couldNotConnect = true;
                        $scope.noEmails = true;


                        $scope.errorMessage = response.data.error_message;

                    }



                }
                function cantLoadInitialDatas(response) {

                    $scope.emailLoading = true;
                    $scope.emailDetails = false;
                    $scope.canNotChangePassword = true;
                    $scope.passwordChanged = true;
                    $scope.couldNotConnect = false;
                    $scope.noEmails = true;





                }






    };



    $scope.deleteEmailAccount = function(){

        var domain = $scope.selectedEmail;

        if(domain.length>0) {
            $scope.emailDetailsFinal = false;
        }

    };

});
/* Java script code to create account ends here */

