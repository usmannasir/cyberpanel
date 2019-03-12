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
        var selectedACL = $scope.selectedACL;
        var websitesLimits = $scope.websitesLimits;
        var userName = $scope.userName;
        var password = $scope.password;


                var url = "/users/submitUserCreation";

                var data = {
                    firstName:firstName,
                    lastName:lastName,
                    email:email,
                    selectedACL:selectedACL,
                    websitesLimit:websitesLimits,
                    userName:userName,
                    password:password
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

    ///

    $scope.generatedPasswordView = true;

    $scope.generatePassword = function () {
      $scope.generatedPasswordView = false;
      $scope.password = randomPassword(12);
    };

    $scope.usePassword = function () {
        $scope.generatedPasswordView = true;
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
                    accountUsername:accountUsername
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.fetchStatus === 1){

                        $scope.acctDetailsFetched = false;

                        var userDetails = response.data.userDetails;

                        $scope.firstName = userDetails.firstName;
                        $scope.lastName = userDetails.lastName;
                        $scope.email = userDetails.email;

                        $scope.userModificationLoading = true;
                        $scope.acctDetailsFetched = false;
                        $scope.userModified = true;
                        $scope.canotModifyUser = true;
                        $scope.couldNotConnect = true;
                        $scope.canotFetchDetails = true;
                        $scope.detailsFetched = false;
                        $scope.userAccountsLimit = true;
                        $scope.websitesLimit = true;
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

         var password = $scope.password;



                var url = "/users/saveModifications";

                var data = {
                    accountUsername:accountUsername,
                    firstName:firstName,
                    lastName:lastName,
                    email:email,
                    password:password
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

    ///

    $scope.generatedPasswordView = true;

    $scope.generatePassword = function () {
      $scope.generatedPasswordView = false;
      $scope.password = randomPassword(12);
    };

    $scope.usePassword = function () {
        $scope.generatedPasswordView = true;
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


/* Java script code to create acl */
app.controller('createACLCTRL', function($scope,$http) {

    $scope.aclLoading = true;

    $scope.makeAdmin = false;

    //

    $scope.versionManagement = false;

    // User Management

    $scope.createNewUser = false;
    $scope.resellerCenter = false;
    $scope.deleteUser = false;
    $scope.changeUserACL = false;

    // Website Management

    $scope.createWebsite = false;
    $scope.modifyWebsite = false;
    $scope.suspendWebsite = false;
    $scope.deleteWebsite = false;

    // Package Management

    $scope.createPackage = false;
    $scope.deletePackage = false;
    $scope.modifyPackage = false;

    // Database Management

    $scope.createDatabase = true;
    $scope.deleteDatabase = true;
    $scope.listDatabases = true;

    // DNS Management

    $scope.createNameServer = false;
    $scope.createDNSZone = true;
    $scope.deleteZone = true;
    $scope.addDeleteRecords = true;

    // Email Management

    $scope.createEmail = true;
    $scope.deleteEmail = true;
    $scope.emailForwarding = true;
    $scope.changeEmailPassword = true;
    $scope.dkimManager = true;

    // FTP Management

    $scope.createFTPAccount = true;
    $scope.deleteFTPAccount = true;
    $scope.listFTPAccounts = true;

    // Backup Management

    $scope.createBackup = true;
    $scope.restoreBackup = false;
    $scope.addDeleteDestinations = false;
    $scope.scheDuleBackups = false;
    $scope.remoteBackups = false;

    // SSL Management

    $scope.manageSSL = true;
    $scope.hostnameSSL = false;
    $scope.mailServerSSL = false;



    $scope.createACLFunc = function(){

        $scope.aclLoading = false;

                var url = "/users/createACLFunc";

                var data = {

                   aclName : $scope.aclName,
                   makeAdmin : $scope.makeAdmin,

                   //
                   versionManagement : $scope.versionManagement,

                   // User Management

                   createNewUser  : $scope.createNewUser,
                   resellerCenter : $scope.resellerCenter,
                   deleteUser  : $scope.deleteUser,
                   changeUserACL : $scope.changeUserACL,

                   // Website Management

                   createWebsite  : $scope.createWebsite,
                   modifyWebsite  : $scope.modifyWebsite,
                   suspendWebsite  : $scope.suspendWebsite,
                   deleteWebsite  : $scope.deleteWebsite,

                   // Package Management

                   createPackage  : $scope.createPackage,
                   deletePackage  : $scope.deletePackage,
                   modifyPackage  : $scope.modifyPackage,

                   // Database Management

                   createDatabase  : $scope.createDatabase,
                   deleteDatabase  : $scope.deleteDatabase,
                   listDatabases  : $scope.listDatabases,

                   // DNS Management

                   createNameServer  : $scope.createNameServer,
                   createDNSZone  : $scope.createDNSZone,
                   deleteZone  : $scope.deleteZone,
                   addDeleteRecords  : $scope.addDeleteRecords,

                   // Email Management

                   createEmail  : $scope.createEmail,
                   deleteEmail  : $scope.deleteEmail,
                   emailForwarding  : $scope.emailForwarding,
                   changeEmailPassword  : $scope.changeEmailPassword,
                   dkimManager  : $scope.dkimManager,

                   // FTP Management

                   createFTPAccount  : $scope.createFTPAccount,
                   deleteFTPAccount  : $scope.deleteFTPAccount,
                   listFTPAccounts  : $scope.listFTPAccounts,

                   // Backup Management

                   createBackup  : $scope.createBackup,
                   restoreBackup  : $scope.restoreBackup,
                   addDeleteDestinations  : $scope.addDeleteDestinations,
                   scheDuleBackups  : $scope.scheDuleBackups,
                   remoteBackups  : $scope.remoteBackups,

                   // SSL Management

                   manageSSL  : $scope.manageSSL,
                   hostnameSSL  : $scope.hostnameSSL,
                   mailServerSSL  : $scope.mailServerSSL

                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.aclLoading = true;

                    if(response.data.status === 1){
                        new PNotify({
                            title: 'Success!',
                            text: 'ACL Successfully created.',
                            type:'success'
                          });
                    }

                    else
                    {

                        new PNotify({
                            title: 'Error!',
                            text: response.data.errorMessage,
                            type:'error'
                          });


                    }

                }
                function cantLoadInitialDatas(response) {

                    $scope.aclLoading = false;

                    new PNotify({
                            title: 'Error!',
                            text: 'Could not connect to server, please refresh this page.',
                            type:'error'
                          });

                }





    };

    $scope.adminHook = function () {

        if($scope.makeAdmin === true){

            $scope.makeAdmin = true;

            //

            $scope.versionManagement = true;

            // User Management

            $scope.createNewUser = true;
            $scope.resellerCenter = true;
            $scope.deleteUser = true;
            $scope.changeUserACL = true;

            // Website Management

            $scope.createWebsite = true;
            $scope.modifyWebsite = true;
            $scope.suspendWebsite = true;
            $scope.deleteWebsite = true;

            // Package Management

            $scope.createPackage = true;
            $scope.deletePackage = true;
            $scope.modifyPackage = true;

            // Database Management

            $scope.createDatabase = true;
            $scope.deleteDatabase = true;
            $scope.listDatabases = true;

            // DNS Management

            $scope.createNameServer = true;
            $scope.createDNSZone = true;
            $scope.deleteZone = true;
            $scope.addDeleteRecords = true;

            // Email Management

            $scope.createEmail = true;
            $scope.deleteEmail = true;
            $scope.emailForwarding = true;
            $scope.changeEmailPassword = true;
            $scope.dkimManager = true;

            // FTP Management

            $scope.createFTPAccount = true;
            $scope.deleteFTPAccount = true;
            $scope.listFTPAccounts = true;

            // Backup Management

            $scope.createBackup = true;
            $scope.restoreBackup = true;
            $scope.addDeleteDestinations = true;
            $scope.scheDuleBackups = true;
            $scope.remoteBackups = true;

            // SSL Management

            $scope.manageSSL = true;
            $scope.hostnameSSL = true;
            $scope.mailServerSSL = true;

        }
        else{
            $scope.makeAdmin = false;

            //

            $scope.versionManagement = false;

            // User Management

            $scope.createNewUser = false;
            $scope.resellerCenter = false;
            $scope.deleteUser = false;
            $scope.changeUserACL = false;

            // Website Management

            $scope.createWebsite = false;
            $scope.modifyWebsite = false;
            $scope.suspendWebsite = false;
            $scope.deleteWebsite = false;

            // Package Management

            $scope.createPackage = false;
            $scope.deletePackage = false;
            $scope.modifyPackage = false;

            // Database Management

            $scope.createDatabase = true;
            $scope.deleteDatabase = true;
            $scope.listDatabases = true;

            // DNS Management

            $scope.createNameServer = false;
            $scope.createDNSZone = true;
            $scope.deleteZone = true;
            $scope.addDeleteRecords = true;

            // Email Management

            $scope.createEmail = true;
            $scope.deleteEmail = true;
            $scope.emailForwarding = true;
            $scope.changeEmailPassword = true;
            $scope.dkimManager = true;

            // FTP Management

            $scope.createFTPAccount = true;
            $scope.deleteFTPAccount = true;
            $scope.listFTPAccounts = true;

            // Backup Management

            $scope.createBackup = true;
            $scope.restoreBackup = false;
            $scope.addDeleteDestinations = false;
            $scope.scheDuleBackups = false;
            $scope.remoteBackups = false;

            // SSL Management

            $scope.manageSSL = true;
            $scope.hostnameSSL = false;
            $scope.mailServerSSL = false;
        }

    };


});
/* Java script code to create acl ends here */


/* Java script code to delete acl */
app.controller('deleteACTCTRL', function($scope,$http) {

    $scope.aclLoading = true;
    $scope.deleteACLButton = true;

    $scope.deleteACLFunc = function(){

        $scope.deleteACLButton = false;

    };

    $scope.deleteACLFinal = function(){

                $scope.aclLoading = false;

                url = "/users/deleteACLFunc";

                var data = {
                    aclToBeDeleted: $scope.aclToBeDeleted
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.aclLoading = true;

                    if (response.data.status === 1)
                    {
                        new PNotify({
                            title: 'Success!',
                            text: 'ACL Successfully deleted.',
                            type:'success'
                          });

                    }
                    else{
                        new PNotify({
                            title: 'Error!',
                            text: response.data.errorMessage,
                            type:'error'
                          });
                    }


                }
                function cantLoadInitialDatas(response) {
                    $scope.aclLoading = true;
                    new PNotify({
                            title: 'Error!',
                            text: 'Could not connect to server, please refresh this page.',
                            type:'error'
                          });
                }


    };

});
/* Java script code to delete acl */


/* Java script code to create acl */
app.controller('modifyACLCtrl', function($scope,$http) {

    $scope.aclLoading = true;
    $scope.aclDetails = true;

    $scope.fetchDetails = function () {

        $scope.aclLoading = false;

                var url = "/users/fetchACLDetails";

                var data = {
                   aclToModify : $scope.aclToModify
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.aclLoading = true;


                    if(response.data.status === 1){
                        new PNotify({
                            title: 'Success!',
                            text: 'Current settings successfully fetched',
                            type:'success'
                          });

                        $scope.aclDetails = false;

                        $scope.makeAdmin = Boolean(response.data.adminStatus);

                        //

                        $scope.versionManagement = Boolean(response.data.versionManagement);

                        // User Management

                        $scope.createNewUser = Boolean(response.data.createNewUser);
                        $scope.resellerCenter = Boolean(response.data.resellerCenter);
                        $scope.deleteUser = Boolean(response.data.deleteUser);
                        $scope.changeUserACL = Boolean(response.data.changeUserACL);

                        // Website Management

                        $scope.createWebsite = Boolean(response.data.createWebsite);
                        $scope.modifyWebsite = Boolean(response.data.modifyWebsite);
                        $scope.suspendWebsite = Boolean(response.data.suspendWebsite);
                        $scope.deleteWebsite = Boolean(response.data.deleteWebsite);

                        // Package Management

                        $scope.createPackage = Boolean(response.data.createPackage);
                        $scope.deletePackage = Boolean(response.data.deletePackage);
                        $scope.modifyPackage = Boolean(response.data.modifyPackage);

                        // Database Management

                        $scope.createDatabase = Boolean(response.data.createDatabase);
                        $scope.deleteDatabase = Boolean(response.data.deleteDatabase);
                        $scope.listDatabases = Boolean(response.data.listDatabases);

                        // DNS Management

                        $scope.createNameServer = Boolean(response.data.createNameServer);
                        $scope.createDNSZone = Boolean(response.data.createDNSZone);
                        $scope.deleteZone = Boolean(response.data.deleteZone);
                        $scope.addDeleteRecords = Boolean(response.data.addDeleteRecords);

                        // Email Management

                        $scope.createEmail = Boolean(response.data.createEmail);
                        $scope.deleteEmail = Boolean(response.data.deleteEmail);
                        $scope.emailForwarding = Boolean(response.data.emailForwarding);
                        $scope.changeEmailPassword = Boolean(response.data.changeEmailPassword);
                        $scope.dkimManager = Boolean(response.data.dkimManager);

                        // FTP Management

                        $scope.createFTPAccount = Boolean(response.data.createFTPAccount);
                        $scope.deleteFTPAccount = Boolean(response.data.deleteFTPAccount);
                        $scope.listFTPAccounts = Boolean(response.data.listFTPAccounts);

                        // Backup Management

                        $scope.createBackup = Boolean(response.data.createBackup);
                        $scope.restoreBackup = Boolean(response.data.restoreBackup);
                        $scope.addDeleteDestinations = Boolean(response.data.addDeleteDestinations);
                        $scope.scheDuleBackups = Boolean(response.data.scheDuleBackups);
                        $scope.remoteBackups = Boolean(response.data.remoteBackups);

                        // SSL Management

                        $scope.manageSSL = Boolean(response.data.manageSSL);
                        $scope.hostnameSSL = Boolean(response.data.hostnameSSL);
                        $scope.mailServerSSL = Boolean(response.data.mailServerSSL);

                    }
                    else
                    {
                        new PNotify({
                            title: 'Error!',
                            text: response.data.errorMessage,
                            type:'error'
                          });
                    }

                }
                function cantLoadInitialDatas(response) {

                    $scope.aclLoading = false;

                    new PNotify({
                            title: 'Error!',
                            text: 'Could not connect to server, please refresh this page.',
                            type:'error'
                          });

                }

    };

    $scope.saveChanges = function(){

        $scope.aclLoading = false;

                var url = "/users/submitACLModifications";

                var data = {
                   aclToModify : $scope.aclToModify,
                   adminStatus : $scope.makeAdmin,
                   //
                   versionManagement : $scope.versionManagement,

                   // User Management

                   createNewUser  : $scope.createNewUser,
                   resellerCenter : $scope.resellerCenter,
                   deleteUser  : $scope.deleteUser,
                   changeUserACL : $scope.changeUserACL,

                   // Website Management

                   createWebsite  : $scope.createWebsite,
                   modifyWebsite  : $scope.modifyWebsite,
                   suspendWebsite  : $scope.suspendWebsite,
                   deleteWebsite  : $scope.deleteWebsite,

                   // Package Management

                   createPackage  : $scope.createPackage,
                   deletePackage  : $scope.deletePackage,
                   modifyPackage  : $scope.modifyPackage,

                   // Database Management

                   createDatabase  : $scope.createDatabase,
                   deleteDatabase  : $scope.deleteDatabase,
                   listDatabases  : $scope.listDatabases,

                   // DNS Management

                   createNameServer  : $scope.createNameServer,
                   createDNSZone  : $scope.createDNSZone,
                   deleteZone  : $scope.deleteZone,
                   addDeleteRecords  : $scope.addDeleteRecords,

                   // Email Management

                   createEmail  : $scope.createEmail,
                   deleteEmail  : $scope.deleteEmail,
                   emailForwarding  : $scope.emailForwarding,
                   changeEmailPassword  : $scope.changeEmailPassword,
                   dkimManager  : $scope.dkimManager,

                   // FTP Management

                   createFTPAccount  : $scope.createFTPAccount,
                   deleteFTPAccount  : $scope.deleteFTPAccount,
                   listFTPAccounts  : $scope.listFTPAccounts,

                   // Backup Management

                   createBackup  : $scope.createBackup,
                   restoreBackup  : $scope.restoreBackup,
                   addDeleteDestinations  : $scope.addDeleteDestinations,
                   scheDuleBackups  : $scope.scheDuleBackups,
                   remoteBackups  : $scope.remoteBackups,

                   // SSL Management

                   manageSSL  : $scope.manageSSL,
                   hostnameSSL  : $scope.hostnameSSL,
                   mailServerSSL  : $scope.mailServerSSL

                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.aclLoading = true;

                    if(response.data.status === 1){
                        new PNotify({
                            title: 'Success!',
                            text: 'ACL Successfully modified.',
                            type:'success'
                          });
                    }

                    else
                    {

                        new PNotify({
                            title: 'Error!',
                            text: response.data.errorMessage,
                            type:'error'
                          });


                    }

                }
                function cantLoadInitialDatas(response) {

                    $scope.aclLoading = false;

                    new PNotify({
                            title: 'Error!',
                            text: 'Could not connect to server, please refresh this page.',
                            type:'error'
                          });

                }





    };

    $scope.adminHook = function () {

        if($scope.makeAdmin === true){

            $scope.makeAdmin = true;

            //

            $scope.versionManagement = true;

            // User Management

            $scope.createNewUser = true;
            $scope.resellerCenter = true;
            $scope.deleteUser = true;
            $scope.changeUserACL = true;

            // Website Management

            $scope.createWebsite = true;
            $scope.modifyWebsite = true;
            $scope.suspendWebsite = true;
            $scope.deleteWebsite = true;

            // Package Management

            $scope.createPackage = true;
            $scope.deletePackage = true;
            $scope.modifyPackage = true;

            // Database Management

            $scope.createDatabase = true;
            $scope.deleteDatabase = true;
            $scope.listDatabases = true;

            // DNS Management

            $scope.createNameServer = true;
            $scope.createDNSZone = true;
            $scope.deleteZone = true;
            $scope.addDeleteRecords = true;

            // Email Management

            $scope.createEmail = true;
            $scope.deleteEmail = true;
            $scope.emailForwarding = true;
            $scope.changeEmailPassword = true;
            $scope.dkimManager = true;

            // FTP Management

            $scope.createFTPAccount = true;
            $scope.deleteFTPAccount = true;
            $scope.listFTPAccounts = true;

            // Backup Management

            $scope.createBackup = true;
            $scope.restoreBackup = true;
            $scope.addDeleteDestinations = true;
            $scope.scheDuleBackups = true;
            $scope.remoteBackups = true;

            // SSL Management

            $scope.manageSSL = true;
            $scope.hostnameSSL = true;
            $scope.mailServerSSL = true;

        }
        else{
            $scope.makeAdmin = false;

            //

            $scope.versionManagement = false;

            // User Management

            $scope.createNewUser = false;
            $scope.resellerCenter = false;
            $scope.deleteUser = false;
            $scope.changeUserACL = false;

            // Website Management

            $scope.createWebsite = false;
            $scope.modifyWebsite = false;
            $scope.suspendWebsite = false;
            $scope.deleteWebsite = false;

            // Package Management

            $scope.createPackage = false;
            $scope.deletePackage = false;
            $scope.modifyPackage = false;

            // Database Management

            $scope.createDatabase = true;
            $scope.deleteDatabase = true;
            $scope.listDatabases = true;

            // DNS Management

            $scope.createNameServer = false;
            $scope.createDNSZone = true;
            $scope.deleteZone = true;
            $scope.addDeleteRecords = true;

            // Email Management

            $scope.createEmail = true;
            $scope.deleteEmail = true;
            $scope.emailForwarding = true;
            $scope.changeEmailPassword = true;
            $scope.dkimManager = true;

            // FTP Management

            $scope.createFTPAccount = true;
            $scope.deleteFTPAccount = true;
            $scope.listFTPAccounts = true;

            // Backup Management

            $scope.createBackup = true;
            $scope.restoreBackup = false;
            $scope.addDeleteDestinations = false;
            $scope.scheDuleBackups = false;
            $scope.remoteBackups = false;

            // SSL Management

            $scope.manageSSL = true;
            $scope.hostnameSSL = false;
            $scope.mailServerSSL = false;
        }

    };

});
/* Java script code to create acl ends here */


/* Java script code to change user acl */
app.controller('changeUserACLCTRL', function($scope,$http) {

    $scope.aclLoading = true;

    $scope.changeACLFunc = function(){

                $scope.aclLoading = false;

                url = "/users/changeACLFunc";

                var data = {
                    selectedUser: $scope.selectedUser,
                    selectedACL: $scope.selectedACL
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.aclLoading = true;

                    if (response.data.status === 1)
                    {
                        new PNotify({
                            title: 'Success!',
                            text: 'ACL Successfully changed.',
                            type:'success'
                          });

                    }
                    else{
                        new PNotify({
                            title: 'Error!',
                            text: response.data.errorMessage,
                            type:'error'
                          });
                    }


                }
                function cantLoadInitialDatas(response) {
                    $scope.aclLoading = true;
                    new PNotify({
                            title: 'Error!',
                            text: 'Could not connect to server, please refresh this page.',
                            type:'error'
                          });
                }


    };

});
/* Java script code to change user acl */

/* Java script code for reseller center */
app.controller('resellerCenterCTRL', function($scope,$http) {

    $scope.aclLoading = true;

    $scope.saveResellerChanges = function(){

                $scope.aclLoading = false;

                url = "/users/saveResellerChanges";

                var data = {
                    userToBeModified: $scope.userToBeModified,
                    newOwner: $scope.newOwner,
                    websitesLimit: $scope.websitesLimit
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.aclLoading = true;

                    if (response.data.status === 1)
                    {
                        new PNotify({
                            title: 'Success!',
                            text: 'Changes successfully applied!',
                            type:'success'
                          });

                    }
                    else{
                        new PNotify({
                            title: 'Error!',
                            text: response.data.errorMessage,
                            type:'error'
                          });
                    }


                }
                function cantLoadInitialDatas(response) {
                    $scope.aclLoading = true;
                    new PNotify({
                            title: 'Error!',
                            text: 'Could not connect to server, please refresh this page.',
                            type:'error'
                          });
                }


    };

});
/* Java script code for reseller center acl */