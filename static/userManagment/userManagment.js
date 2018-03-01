/**
 * Created by usman on 8/5/17.
 */



/* Java script code to create account */
app.controller('createUserCtr', function($scope,$http) {

    $scope.acctsLimit = true;
    $scope.webLimits = true;
    $scope.userCreated = true;
    $scope.userCreationFailed = true;
    $scope.couldNotConnect = true;
    $scope.userCreationLoading = true;
    $scope.combinedLength = true;


    $scope.showLimitsBox = function(){

        if($scope.accountType == "Normal User"){
            $scope.webLimits = false;
            $scope.acctsLimit = true;
        }
        else if($scope.accountType == "Reseller"){
            $scope.webLimits = false;
            $scope.acctsLimit = false;
        }
        else{
            $scope.webLimits = true;
            $scope.acctsLimit = true;
        }

    }

    $scope.createUserFunc = function(){

        $scope.webLimits = false;
        $scope.userCreated = true;
        $scope.userCreationFailed = true;
        $scope.couldNotConnect = true;
        $scope.userCreationLoading = false;
        $scope.combinedLength = true;


        var firstName = $scope.firstName;
        var lastName = $scope.lastName;
        var email = $scope.email;
        var accountType = $scope.accountType;
        var userAccountsLimit = $scope.userAccountsLimit;
        var websitesLimit = $scope.websitesLimit;
        var userName = $scope.userName;
        var password = $scope.password;

        if ((firstName.length + lastName.length)>=20){
            $scope.combinedLength = false;
            $scope.userCreationLoading = true;
            return 0;
        }




                var url = "/users/submitUserCreation";

                var data = {
                    firstName:firstName,
                    lastName:lastName,
                    email:email,

                    accountType:accountType,
                    userAccountsLimit:userAccountsLimit,
                    websitesLimit:websitesLimit,


                    userName:userName,
                    password:password,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.createStatus == 1){

                        $scope.userCreated = false;
                        $scope.userCreationFailed = true;
                        $scope.couldNotConnect = true;
                        $scope.userCreationLoading = true;

                        $scope.userName = userName;



                    }

                    else
                    {

                        $scope.acctsLimit = false;
                        $scope.webLimits = false;
                        $scope.userCreated = true;
                        $scope.userCreationFailed = false;
                        $scope.couldNotConnect = true;
                        $scope.userCreationLoading = true;

                        $scope.errorMessage = response.data.error_message;


                    }



                }
                function cantLoadInitialDatas(response) {

                    $scope.acctsLimit = false;
                    $scope.webLimits = false;
                    $scope.userCreated = true;
                    $scope.userCreationFailed = true;
                    $scope.couldNotConnect = false;
                    $scope.userCreationLoading = true;



                }





    };


    $scope.hideSomeThings = function(){

        $scope.userCreated = true;



    };

});
/* Java script code to create account ends here */


/* Java script code to modify user account */
app.controller('modifyUser', function($scope,$http) {

    $scope.userModificationLoading = true;
    $scope.acctDetailsFetched = true;
    $scope.userAccountsLimit = true;
    $scope.userModified = true;
    $scope.canotModifyUser = true;
    $scope.couldNotConnect = true;
    $scope.canotFetchDetails = true;
    $scope.detailsFetched = true;
    $scope.accountTypeView = true;
    $scope.websitesLimit = true;


    $scope.fetchUserDetails = function(){


        var accountUsername = $scope.accountUsername;



                var url = "/users/fetchUserDetails";

                var data = {
                    accountUsername:accountUsername,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.fetchStatus == 1){

                        $scope.acctDetailsFetched = false;

                        var userDetails = response.data.userDetails;

                        $scope.currentAccountType = userDetails.accountType;
                        $scope.firstName = userDetails.firstName;
                        $scope.lastName = userDetails.lastName;
                        $scope.email = userDetails.email;
                        $scope.userAccountsLimit = userDetails.userAccountsLimit;
                        $scope.websitesLimit = userDetails.websitesLimit;

                        $scope.userModificationLoading = true;
                        $scope.acctDetailsFetched = false;
                        $scope.userModified = true;
                        $scope.canotModifyUser = true;
                        $scope.couldNotConnect = true;
                        $scope.canotFetchDetails = true;
                        $scope.detailsFetched = false;
                        $scope.userAccountsLimit = true;
                        $scope.websitesLimit = true;

                        if(userDetails.accountType=="Administrator"){
                            $scope.accountTypeView = true;
                        }
                        else{
                            $scope.accountTypeView = false;
                        }





                    }

                    else
                    {
                        $scope.userModificationLoading = true;
                        $scope.acctDetailsFetched = true;
                        $scope.userAccountsLimit = true;
                        $scope.userModified = true;
                        $scope.canotModifyUser = true;
                        $scope.couldNotConnect = true;
                        $scope.canotFetchDetails = false;
                        $scope.detailsFetched = true;


                        $scope.errorMessage = response.data.error_message;


                    }



                }
                function cantLoadInitialDatas(response) {

                    $scope.userModificationLoading = true;
                    $scope.acctDetailsFetched = true;
                    $scope.userAccountsLimit = true;
                    $scope.userModified = true;
                    $scope.canotModifyUser = true;
                    $scope.couldNotConnect = false;
                    $scope.canotFetchDetails = true;
                    $scope.detailsFetched = true;




                }





    };


    $scope.modifyUser = function(){


        $scope.userModificationLoading = false;
        $scope.acctDetailsFetched = false;
        $scope.userModified = true;
        $scope.canotModifyUser = true;
        $scope.couldNotConnect = true;
        $scope.canotFetchDetails = true;
        $scope.detailsFetched = true;


         var accountUsername = $scope.accountUsername;

         var accountType = $scope.accountType;
         var firstName = $scope.firstName;

         var lastName  = $scope.lastName;
         var email = $scope.email;

         var userAccountsLimit = $scope.userAccountsLimitValue;
         var websitesLimit = $scope.websitesLimitValue;
         var password = $scope.password;



                var url = "/users/saveModifications";

                var data = {
                    accountUsername:accountUsername,
                    accountType:accountType,
                    firstName:firstName,
                    lastName:lastName,
                    email:email,
                    userAccountsLimit:userAccountsLimit,
                    websitesLimit:websitesLimit,
                    password:password,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.saveStatus == 1){

                        $scope.userModificationLoading = true;
                        $scope.acctDetailsFetched = true;
                        $scope.userModified = false;
                        $scope.canotModifyUser = true;
                        $scope.couldNotConnect = true;
                        $scope.canotFetchDetails = true;
                        $scope.detailsFetched = true;
                        $scope.userAccountsLimit = true;
                        $scope.accountTypeView = true;
                        $scope.websitesLimit = true;


                        $scope.userName = accountUsername;



                    }

                    else
                    {

                        $scope.userModificationLoading = true;
                        $scope.acctDetailsFetched = false;
                        $scope.userModified = true;
                        $scope.canotModifyUser = false;
                        $scope.couldNotConnect = true;
                        $scope.canotFetchDetails = true;
                        $scope.detailsFetched = true;


                        $scope.errorMessage = response.data.error_message;


                    }



                }
                function cantLoadInitialDatas(response) {

                    $scope.userModificationLoading = true;
                    $scope.acctDetailsFetched = true;
                    $scope.userModified = true;
                    $scope.canotModifyUser = true;
                    $scope.couldNotConnect = false;
                    $scope.canotFetchDetails = true;
                    $scope.detailsFetched = true;





                }





    };


    $scope.showLimitsBox = function () {

        if ($scope.accountType == "Normal User"){
            $scope.websitesLimit = false;
            $scope.userAccountsLimit = true;
        }
        else if($scope.accountType=="Admin"){
            $scope.websitesLimit = true;
            $scope.userAccountsLimit = true;

        }
        else{
            $scope.userAccountsLimit = false;
            $scope.websitesLimit = false;
        }


    };

});
/* Java script code to modify user account ends here */



/* Java script code to delete user account */
app.controller('deleteUser', function($scope,$http) {


    $scope.deleteUserButton = true;
    $scope.deleteFailure = true;
    $scope.deleteSuccess = true;
    $scope.couldNotConnect = true;


    $scope.deleteUser = function(){
        $scope.deleteUserButton = false;
    }

    $scope.deleteUserFinal = function(){


            var accountUsername = $scope.accountUsername;



                var url = "/users/submitUserDeletion";

                var data = {
                    accountUsername:accountUsername,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.deleteStatus == 1){

                        $scope.deleteUserButton = true;
                        $scope.deleteFailure = true;
                        $scope.deleteSuccess = false;
                        $scope.couldNotConnect = true;

                        $scope.deletedUser = accountUsername;



                    }

                    else
                    {
                        $scope.deleteUserButton = true;
                        $scope.deleteFailure = false;
                        $scope.deleteSuccess = true;
                        $scope.couldNotConnect = true;
                        $scope.deleteUserButton = true;

                        $scope.errorMessage = response.data.error_message;

                    }



                }
                function cantLoadInitialDatas(response) {

                            $scope.deleteUserButton = true;
                            $scope.deleteFailure = true;
                            $scope.deleteSuccess = true;
                            $scope.couldNotConnect = false;
                            $scope.deleteUserButton = true;




                }





    };



});
/* Java script code to delete user account ends here */