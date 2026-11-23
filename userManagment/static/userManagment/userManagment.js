/**
 * Created by usman on 8/5/17.
 */


/* Java script code to create account */
app.controller('createUserCtr', function ($scope, $http) {

    $scope.acctsLimit = true;
    $scope.webLimits = true;
    $scope.userCreated = true;
    $scope.userCreationFailed = true;
    $scope.couldNotConnect = true;
    $scope.userCreationLoading = true;
    $scope.combinedLength = true;

    $scope.createUserFunc = function () {

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
            firstName: firstName,
            lastName: lastName,
            email: email,
            selectedACL: selectedACL,
            websitesLimit: websitesLimits,
            userName: userName,
            password: password,
            securityLevel: $scope.securityLevel
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.createStatus == 1) {

                $scope.userCreated = false;
                $scope.userCreationFailed = true;
                $scope.couldNotConnect = true;
                $scope.userCreationLoading = true;

                $scope.userName = userName;


            } else {

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

    $scope.hideSomeThings = function () {

        $scope.userCreated = true;


    };

    ///

    $scope.generatedPasswordView = true;

    $scope.generatePassword = function () {
        $scope.generatedPasswordView = false;
        $scope.password = randomPassword(16);
    };

    $scope.usePassword = function () {
        $scope.generatedPasswordView = true;
    };

});
/* Java script code to create account ends here */


/* Java script code to modify user account */

// The key to type into an authenticator app instead of scanning: the secret of the address the QR
// code shows, so the key and the code are always the same one.
function manualKeyFromOtpauth(otpauth) {
    var found = /[?&]secret=([^&#]+)/.exec(typeof otpauth === 'string' ? otpauth : '');
    return found ? decodeURIComponent(found[1]) : '';
}

app.controller('modifyUser', function ($scope, $http) {

    var qrCode = window.qr = new QRious({
        element: document.getElementById('qr'),
        size: 200,
        value: 'QRious'
    });


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
    $scope.qrHidden = true;
    // Whether the account loaded has two-factor already; its secret is then not sent to the page.
    $scope.twofaEnrolled = false;
    $scope.secretKey = '';
    $scope.formattedSecretKey = '';

    // Counts the accounts loaded, so that a set-up answer for an earlier one is dropped.
    var accountLoad = 0;
    var setUpAsked = false;

    function forgetSetUpCode() {
        $scope.qrHidden = true;
        $scope.secretKey = '';
        $scope.formattedSecretKey = '';
        setUpAsked = false;
        accountLoad += 1;
    }

    // Asks for the code of the two-factor set-up of the account loaded, once per account loaded,
    // and shows it with the key for typing, which is the secret of that same code.
    function showSetUpCode() {
        if ($scope.secretKey) {
            $scope.qrHidden = false;
            return;
        }
        if (setUpAsked) {
            return;
        }
        setUpAsked = true;
        var load = accountLoad;
        var config = {headers: {'X-CSRFToken': getCookie('csrftoken')}};
        var data = {accountUsername: $scope.accountUsername, twofaSetup: true};

        $http.post("/users/fetchUserDetails", data, config).then(function (response) {
            if (load !== accountLoad) {
                return;
            }
            var details = response.data.fetchStatus === 1 ? response.data.userDetails : null;
            var key = details ? manualKeyFromOtpauth(details.otpauth) : '';
            if (!key) {
                setUpAsked = false;
                $scope.twofa = false;
                $scope.errorMessage = details ? 'Two-factor is already on for this account. Choose the account again.' :
                    response.data.error_message;
                $scope.canotFetchDetails = false;
                return;
            }
            $scope.secretKey = key;
            // Shown in groups of four for reading; the copy button gives the key without spaces.
            $scope.formattedSecretKey = key.match(/.{1,4}/g).join(' ');
            qrCode.set({
                value: details.otpauth
            });
            $scope.qrHidden = $scope.twofa !== true;
        }, function () {
            if (load !== accountLoad) {
                return;
            }
            setUpAsked = false;
            $scope.twofa = false;
            $scope.couldNotConnect = false;
        });
    }

    $scope.decideQRShow = function(){
        $scope.canotFetchDetails = true;
        $scope.couldNotConnect = true;
        if ($scope.twofa === true && !$scope.twofaEnrolled) {
            showSetUpCode();
        } else {
            $scope.qrHidden = true;
        }
    };

    $scope.copySecretKey = function() {
        if ($scope.secretKey) {
            // Create a temporary textarea element
            var tempTextarea = document.createElement('textarea');
            tempTextarea.value = $scope.secretKey;
            tempTextarea.style.position = 'fixed';
            tempTextarea.style.opacity = '0';
            document.body.appendChild(tempTextarea);

            // Select and copy the text
            tempTextarea.select();
            tempTextarea.setSelectionRange(0, 99999); // For mobile devices

            try {
                document.execCommand('copy');
                // Show success feedback (you can add a toast notification here if available)
                alert('Secret key copied to clipboard!');
            } catch (err) {
                alert('Failed to copy secret key. Please copy it manually.');
            }

            // Remove the temporary element
            document.body.removeChild(tempTextarea);
        }
    };


    $scope.fetchUserDetails = function () {


        var accountUsername = $scope.accountUsername;

        forgetSetUpCode();

        var url = "/users/fetchUserDetails";

        var data = {
            accountUsername: accountUsername
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.fetchStatus === 1) {

                $scope.acctDetailsFetched = false;

                var userDetails = response.data.userDetails;

                $scope.firstName = userDetails.firstName;
                $scope.lastName = userDetails.lastName;
                $scope.email = userDetails.email;
                $scope.securityLevel = userDetails.securityLevel;
                $scope.currentSecurityLevel = userDetails.securityLevel;
                $scope.twofa = Boolean(userDetails.twofa);
                $scope.twofaEnrolled = $scope.twofa;

                // The code and the key of an account are asked for when its box is ticked.
                forgetSetUpCode();


                $scope.userModificationLoading = true;
                $scope.acctDetailsFetched = false;
                $scope.userModified = true;
                $scope.canotModifyUser = true;
                $scope.couldNotConnect = true;
                $scope.canotFetchDetails = true;
                $scope.detailsFetched = false;
                $scope.userAccountsLimit = true;
                $scope.websitesLimit = true;

            } else {
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

    $scope.modifyUser = function () {


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

        var lastName = $scope.lastName;
        var email = $scope.email;

        var password = $scope.password;


        var url = "/users/saveModifications";

        var data = {
            accountUsername: accountUsername,
            firstName: firstName,
            lastName: lastName,
            email: email,
            passwordByPass: password,
            securityLevel: $scope.securityLevel,
            twofa: $scope.twofa
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.saveStatus == 1) {

                // The form closes; the key of a set-up does not stay on the page.
                forgetSetUpCode();
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


            } else {

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

        if ($scope.accountType == "Normal User") {
            $scope.websitesLimit = false;
            $scope.userAccountsLimit = true;
        } else if ($scope.accountType == "Admin") {
            $scope.websitesLimit = true;
            $scope.userAccountsLimit = true;

        } else {
            $scope.userAccountsLimit = false;
            $scope.websitesLimit = false;
        }


    };

    ///

    $scope.generatedPasswordView = true;

    $scope.generatePassword = function () {
        $scope.generatedPasswordView = false;
        $scope.password = randomPassword(16);
    };

    $scope.usePassword = function () {
        $scope.generatedPasswordView = true;
    };

});
/* Java script code to modify user account ends here */


/* Java script code to delete user account */
app.controller('deleteUser', function ($scope, $http) {


    $scope.deleteUserButton = true;
    $scope.deleteFailure = true;
    $scope.deleteSuccess = true;
    $scope.couldNotConnect = true;


    $scope.deleteUser = function () {
        $scope.deleteUserButton = false;
    };

    $scope.deleteUserFinal = function () {


        var accountUsername = $scope.accountUsername;


        var url = "/users/submitUserDeletion";

        var data = {
            accountUsername: accountUsername,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.deleteStatus === 1) {

                $scope.deleteUserButton = true;
                $scope.deleteFailure = true;
                $scope.deleteSuccess = false;
                $scope.couldNotConnect = true;

                $scope.deletedUser = accountUsername;


            } else {
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

/* Every permission of an ACL, with its value on a new ACL that is not an admin ACL.
   The Create ACL and Modify ACL pages have one checkbox for each name, and the panel
   stores exactly these names (plogical/aclPermissions.py). A permission is added in
   all three places or in none. */
var aclPermissionDefaults = {
    versionManagement: false,

    // User Management
    createNewUser: false,
    listUsers: false,
    resellerCenter: false,
    deleteUser: false,
    changeUserACL: false,

    // Website Management
    createWebsite: false,
    modifyWebsite: false,
    suspendWebsite: false,
    deleteWebsite: false,

    // Package Management
    createPackage: false,
    listPackages: false,
    deletePackage: false,
    modifyPackage: false,

    // Database Management
    createDatabase: true,
    deleteDatabase: true,
    listDatabases: true,

    // DNS Management
    createNameServer: false,
    createDNSZone: true,
    deleteZone: true,
    addDeleteRecords: true,

    // Email Management
    createEmail: true,
    listEmails: true,
    deleteEmail: true,
    emailForwarding: true,
    changeEmailPassword: true,
    dkimManager: true,

    // FTP Management
    createFTPAccount: true,
    deleteFTPAccount: true,
    listFTPAccounts: true,

    // Backup Management
    createBackup: true,
    googleDriveBackups: true,
    restoreBackup: false,
    addDeleteDestinations: false,
    scheduleBackups: false,
    remoteBackups: false,

    // SSL Management
    manageSSL: true,
    hostnameSSL: false,
    mailServerSSL: false,

    // AI Scanner
    aiScannerAccess: true
};

/* Sets every permission checkbox of the page: valueFor gets the name of a permission
   and its value on a new ACL, and returns whether its box is ticked. */
function setACLPermissions($scope, valueFor) {
    angular.forEach(aclPermissionDefaults, function (standard, name) {
        $scope[name] = valueFor(name, standard) === true;
    });
}

/* Adds every permission to what is sent, as its checkbox stands now. */
function submittedACLPermissions($scope, data) {
    angular.forEach(aclPermissionDefaults, function (standard, name) {
        data[name] = $scope[name] === true;
    });
    return data;
}

/* Make Admin ticks every box; taking it away again puts the boxes back to a new ACL. */
function aclAdminHook($scope) {
    setACLPermissions($scope, function (name, standard) {
        return $scope.makeAdmin === true ? true : standard;
    });
}

app.controller('createACLCTRL', function ($scope, $http) {

    $scope.aclCreated = true;
    $scope.aclCreationFailed = true;
    $scope.couldNotConnect = true;

    $scope.aclLoading = true;
    $scope.makeAdmin = false;

    setACLPermissions($scope, function (name, standard) {
        return standard;
    });


    $scope.createACLFunc = function () {

        $scope.aclLoading = false;

        var url = "/users/createACLFunc";

        var data = submittedACLPermissions($scope, {
            aclName: $scope.aclName,
            makeAdmin: $scope.makeAdmin
        });

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.aclLoading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'ACL Successfully created.',
                    type: 'success'
                });
            } else {

                new PNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.aclLoading = false;

            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });

        }


    };

    $scope.adminHook = function () {
        aclAdminHook($scope);
    };


});
/* Java script code to create acl ends here */


/* Java script code to delete acl */
app.controller('deleteACTCTRL', function ($scope, $http) {

    $scope.aclLoading = true;
    $scope.deleteACLButton = true;

    $scope.deleteACLFunc = function () {

        $scope.deleteACLButton = false;

    };

    $scope.deleteACLFinal = function () {

        $scope.aclLoading = false;

        url = "/users/deleteACLFunc";

        var data = {
            aclToBeDeleted: $scope.aclToBeDeleted
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.aclLoading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'ACL Successfully deleted.',
                    type: 'success'
                });

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.aclLoading = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }


    };

});
/* Java script code to delete acl */


/* Java script code to create acl */
app.controller('modifyACLCtrl', function ($scope, $http) {

    $scope.aclLoading = true;
    $scope.aclDetails = true;

    $scope.fetchDetails = function () {

        $scope.aclLoading = false;

        var url = "/users/fetchACLDetails";

        var data = {
            aclToModify: $scope.aclToModify
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.aclLoading = true;


            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Current settings successfully fetched',
                    type: 'success'
                });

                $scope.aclDetails = false;

                $scope.makeAdmin = Boolean(response.data.adminStatus);

                setACLPermissions($scope, function (name) {
                    return Boolean(response.data[name]);
                });

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.aclLoading = false;

            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });

        }

    };

    $scope.saveChanges = function () {

        $scope.aclLoading = false;

        var url = "/users/submitACLModifications";

        var data = submittedACLPermissions($scope, {
            aclToModify: $scope.aclToModify,
            adminStatus: $scope.makeAdmin
        });

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.aclLoading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'ACL Successfully modified.',
                    type: 'success'
                });
            } else {

                new PNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.aclLoading = false;

            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });

        }


    };

    $scope.adminHook = function () {
        aclAdminHook($scope);
    };

});
/* Java script code to create acl ends here */


/* Java script code to change user acl */
app.controller('changeUserACLCTRL', function ($scope, $http) {

    $scope.aclLoading = true;

    $scope.changeACLFunc = function () {

        $scope.aclLoading = false;

        url = "/users/changeACLFunc";

        var data = {
            selectedUser: $scope.selectedUser,
            selectedACL: $scope.selectedACL
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.aclLoading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'ACL Successfully changed.',
                    type: 'success'
                });

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.aclLoading = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }


    };

});
/* Java script code to change user acl */

/* Java script code for reseller center */
app.controller('resellerCenterCTRL', function ($scope, $http) {

    $scope.aclLoading = true;

    $scope.saveResellerChanges = function () {

        $scope.aclLoading = false;

        url = "/users/saveResellerChanges";

        var data = {
            userToBeModified: $scope.userToBeModified,
            newOwner: $scope.newOwner,
            websitesLimit: $scope.websitesLimit
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.aclLoading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Changes successfully applied!',
                    type: 'success'
                });

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.aclLoading = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }


    };

});
/* Java script code for reseller center acl */


/* Java script code for api access */
app.controller('apiAccessCTRL', function ($scope, $http) {


    $scope.apiAccessDropDown = true;
    $scope.cyberpanelLoading = true;

    $scope.showApiAccessDropDown = function () {
        $scope.apiAccessDropDown = false;
    };

    $scope.saveChanges = function () {

        $scope.cyberpanelLoading = false;

        var url = "/users/saveChangesAPIAccess";

        var data = {
            accountUsername: $scope.accountUsername,
            access: $scope.access,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;

            if (response.data.status === 1) {
                $scope.apiAccessDropDown = true;
                $scope.apiToken = response.data.apiToken || '';
                new PNotify({
                    title: 'Success!',
                    text: 'Changes successfully applied!',
                    type: 'success'
                });

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }


    };


});
/* Java script code for api access */


/* Java script code to list table users */


app.controller('listTableUsers', function ($scope, $http) {

    $scope.cyberpanelLoading = true;

    var UserToDelete;

    $scope.populateCurrentRecords = function () {
        $scope.cyberpanelLoading = false;

        url = "/users/fetchTableUsers";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;

            if (response.data.status === 1) {

                $scope.records = JSON.parse(response.data.data);

                new PNotify({
                    title: 'Success!',
                    text: 'Users successfully fetched!',
                    type: 'success'
                });

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }

    };
    $scope.populateCurrentRecords();


    $scope.deleteUserInitial = function (name){
        UserToDelete = name;
        $scope.UserToDelete = name;
        $('#deleteModal').modal('show');
    };

    $scope.deleteUserFinal = function () {
        $scope.cyberpanelLoading = false;

        var url = "/users/submitUserDeletion";

        var data = {
            accountUsername: UserToDelete,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.deleteStatus === 1) {
                $scope.populateCurrentRecords();
                $('#deleteModal').modal('hide');
                new PNotify({
                    title: 'Success!',
                    text: 'Users successfully deleted!',
                    type: 'success'
                });

            } else {

                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.cyberpanelLoading = false;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }


    };

    $scope.editInitial = function (name) {
        $scope.name = name;
        $('#editModal').modal('show');
    };

    $scope.saveResellerChanges = function () {

        $scope.cyberpanelLoading = false;

        url = "/users/saveResellerChanges";

        var data = {
            userToBeModified: $scope.name,
            newOwner: $scope.newOwner
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                $scope.populateCurrentRecords();
                $('#editModal').modal('hide');
                new PNotify({
                    title: 'Success!',
                    text: 'Changes successfully applied!',
                    type: 'success'
                });

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }


    };

    $scope.changeACLFunc = function () {

        $scope.cyberpanelLoading = false;

        url = "/users/changeACLFunc";

        var data = {
            selectedUser: $scope.name,
            selectedACL: $scope.selectedACL
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;

            if (response.data.status === 1) {
                $scope.populateCurrentRecords();
                $('#editModal').modal('hide');
                new PNotify({
                    title: 'Success!',
                    text: 'ACL Successfully changed.',
                    type: 'success'
                });

            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.aclLoading = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }


    };

    $scope.controlUserState = function (userName, state) {

        $scope.cyberpanelLoading = false;

        var url = "/users/controlUserState";

        var data = {
            accountUsername: userName,
            state: state
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                $scope.populateCurrentRecords();
                new PNotify({
                    title: 'Success!',
                    text: 'Action successfully started.',
                    type: 'success'
                });

            } else {

                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.cyberpanelLoading = false;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    }

});


/* Java script code to list table users */
