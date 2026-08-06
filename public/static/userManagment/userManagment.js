/**
 * Created by usman on 8/5/17.
 */

/* Safe notification - use PNotify if available, else fallback to alert */
function safePNotify(opts) {
    if (typeof PNotify !== 'undefined') {
        new PNotify(opts);
    } else {
        var msg = (opts.title || '') + (opts.text ? ': ' + opts.text : '');
        alert(msg || JSON.stringify(opts));
    }
}

/* Java script code to create account */
app.controller('createUserCtr', function ($scope, $http) {

    // Home directory functionality
    $scope.homeDirectories = [];
    $scope.selectedHomeDirectory = '';
    $scope.selectedHomeDirectoryInfo = null;
    
    // Load home directories on page load
    $scope.loadHomeDirectories = function() {
        var url = '/users/getUserHomeDirectories';
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        $http.post(url, {}, config)
            .then(function(response) {
                if (response.data && response.data.status === 1) {
                    $scope.homeDirectories = response.data.directories || [];
                } else {
                    console.error('Error loading home directories:', response.data);
                    $scope.homeDirectories = [];
                }
            })
            .catch(function(error) {
                console.error('Error loading home directories:', error);
                $scope.homeDirectories = [];
            });
    };
    
    // Update home directory info when selection changes
    $scope.updateHomeDirectoryInfo = function() {
        if ($scope.selectedHomeDirectory) {
            $scope.selectedHomeDirectoryInfo = $scope.homeDirectories.find(function(dir) {
                return dir.id == $scope.selectedHomeDirectory;
            });
        } else {
            $scope.selectedHomeDirectoryInfo = null;
        }
    };
    
    // Initialize home directories
    $scope.loadHomeDirectories();

    $scope.acctsLimit = true;
    $scope.webLimits = true;
    $scope.userCreated = true;
    $scope.userCreationFailed = false;  // false = don't show error alert on load
    $scope.couldNotConnect = true;
    $scope.userCreationLoading = true;
    $scope.combinedLength = true;

    $scope.createUserFunc = function () {

        $scope.webLimits = false;
        $scope.userCreated = true;
        $scope.userCreationFailed = false;  // hide error until we know the result
        $scope.couldNotConnect = true;
        $scope.userCreationLoading = false;
        $scope.combinedLength = true;

        var firstName = $scope.firstName || '';
        var lastName = $scope.lastName || '';
        var email = $scope.email;
        var selectedACL = $scope.selectedACL;
        var websitesLimits = $scope.websitesLimits;
        var userName = $scope.userName;
        var password = $scope.password;

        if (firstName.length + lastName.length > 20) {
            $scope.combinedLength = false;
            $scope.userCreationLoading = true;
            return;
        }

        var url = "/users/submitUserCreation";

        var data = {
            firstName: firstName,
            lastName: lastName,
            email: email,
            selectedACL: selectedACL,
            websitesLimit: websitesLimits,
            userName: userName,
            password: password,
            securityLevel: $scope.securityLevel,
            selectedHomeDirectory: $scope.selectedHomeDirectory || ''
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.createStatus == 1) {
                $scope.userCreated = false;   // show success
                $scope.userCreationFailed = false;  // hide error
                $scope.couldNotConnect = true;
                $scope.userCreationLoading = true;
                $scope.userName = userName;
            } else {
                $scope.acctsLimit = false;
                $scope.webLimits = false;
                $scope.userCreated = true;
                $scope.userCreationFailed = true;   // true = show error alert
                $scope.couldNotConnect = true;
                $scope.userCreationLoading = true;
                $scope.errorMessage = (response.data && (response.data.error_message || response.data.message || response.data.errorMessage)) || 'Unknown error';
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.acctsLimit = false;
            $scope.webLimits = false;
            $scope.userCreated = true;
            $scope.userCreationFailed = false;  // hide server error, show connection error instead
            $scope.couldNotConnect = false;    // show "Could not connect" message
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
app.controller('modifyUser', function ($scope, $http, $timeout) {

    var qrEl = document.getElementById('qr');
    var qrCode = window.qr = (qrEl && typeof QRious !== 'undefined') ? new QRious({
        element: qrEl,
        size: 200,
        value: 'QRious'
    }) : null;
    if (!qrCode && qrEl) {
        try { window.qr = new QRious({ element: qrEl, size: 200, value: 'QRious' }); } catch (e) { /* ignore */ }
    }

    $scope.userSearch = '';
    /* Prefer global set by inline script (before Angular); fallback to script tag */
    var list = (typeof window.__CP_ACCT_NAMES !== 'undefined' && Array.isArray(window.__CP_ACCT_NAMES))
        ? window.__CP_ACCT_NAMES
        : (function() {
            var el = document.getElementById('acctNamesData');
            if (!el || !el.textContent) return [];
            try { return JSON.parse(el.textContent); } catch (e) { return []; }
        })();
    $scope.acctNamesList = Array.isArray(list) ? list : [];

    $scope.userModificationLoading = true;
    $scope.acctDetailsFetched = true;
    $scope.userAccountsLimit = true;
    $scope.userModified = true;
    $scope.canotModifyUser = false;   // false = don't show error alert on load
    $scope.couldNotConnect = true;
    $scope.canotFetchDetails = false; // false = don't show fetch error on load
    $scope.detailsFetched = false;    // false = don't show "details loaded" on load
    $scope.accountTypeView = true;
    $scope.websitesLimit = true;
    $scope.qrHidden = true;

    $scope.decideQRShow = function(){
        if($scope.twofa === true){
            $scope.qrHidden = false;
        }else{
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
    
    $scope.regenerateSecret = function() {
        if (!$scope.accountUsername) {
            alert('Please select a user first.');
            return;
        }
        
        if (!confirm('Are you sure you want to regenerate the 2FA secret? This will generate a new secret key and you will need to update your authenticator app.')) {
            return;
        }
        
        var url = "/users/regenerateTwoFASecret";
        var data = {
            accountUsername: $scope.accountUsername
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        
        $http.post(url, data, config).then(function(response) {
            if (response.data.status === 1) {
                // Update the secret key and formatted version
                $scope.secretKey = response.data.secretKey;
                $scope.formattedSecretKey = response.data.secretKey.match(/.{1,4}/g).join(' ');
                
                // Update the QR code with new provisioning URI
                if (qrCode) qrCode.set({ value: response.data.otpauth });
                
                // Show success message
                alert('2FA secret has been successfully regenerated! Please update your authenticator app with the new QR code or secret key.');
            } else {
                alert('Error regenerating 2FA secret: ' + response.data.error_message);
            }
        }, function(error) {
            console.error('Error regenerating 2FA secret:', error);
            alert('Failed to regenerate 2FA secret. Please try again.');
        });
    };
    
    // WebAuthn Functions
    $scope.loadWebAuthnData = function() {
        if (!$scope.accountUsername) return;
        $scope.webauthnDataLoaded = false;
        var url = '/webauthn/credentials/' + $scope.accountUsername + '/';
        $http.get(url).then(function(response) {
            if (response.data.success) {
                $scope.webauthnCredentials = response.data.credentials || [];
                $scope.webauthnEnabled = response.data.settings.enabled;
                $scope.webauthnRequirePasskey = response.data.settings.require_passkey;
                $scope.webauthnAllowMultiple = response.data.settings.allow_multiple_credentials;
                $scope.webauthnMaxCredentials = response.data.settings.max_credentials;
                $scope.canAddCredential = !!response.data.settings.can_add_credential;
                $scope.webauthnDataLoaded = true;
            } else {
                $scope.canAddCredential = true;
            }
        }, function(error) {
            console.error('Error loading WebAuthn data:', error);
            $scope.canAddCredential = true;
            $scope.webauthnCredentials = [];
        });
    };
    
    $scope.toggleWebAuthn = function() {
        if ($scope.webauthnEnabled) {
            $scope.loadWebAuthnData();
        } else {
            $scope.webauthnCredentials = [];
            $scope.canAddCredential = true;
            $scope.webauthnDataLoaded = false;
        }
    };
    
    /* Inline passkey UX like diabetes.newstargeted.com/profile?tab=2fa: name input + button + message area, no modal */
    $scope.newPasskeyName = '';
    $scope.webauthnMessage = '';
    $scope.webauthnMessageError = false;
    $scope.registerPasskeyLoading = false;
    
    $scope.registerNewPasskey = function() {
        if (!$scope.accountUsername) {
            $scope.webauthnMessage = 'Please select a user account first.';
            $scope.webauthnMessageError = true;
            return;
        }
        if (typeof window.cyberPanelWebAuthn === 'undefined') {
            $scope.webauthnMessage = 'WebAuthn script not loaded. Refresh the page (Ctrl+F5) and try again.';
            $scope.webauthnMessageError = true;
            return;
        }
        if (typeof window.cyberPanelWebAuthn.isSupported !== 'function' || !window.cyberPanelWebAuthn.isSupported()) {
            $scope.webauthnMessage = 'WebAuthn is not supported in this browser.';
            $scope.webauthnMessageError = true;
            return;
        }
        var name = ($scope.newPasskeyName || '').trim() || 'Security key';
        $scope.webauthnMessage = '';
        $scope.webauthnMessageError = false;
        $scope.registerPasskeyLoading = true;
        var username = $scope.accountUsername;
        window.cyberPanelWebAuthn.registerPasskey(username, name, { silent: true })
            .then(function(response) {
                if (response && response.success) {
                    $scope.webauthnMessage = 'Passkey registered successfully.';
                    $scope.webauthnMessageError = false;
                    $scope.newPasskeyName = '';
                    $timeout(function() { $scope.loadWebAuthnData(); }, 0);
                } else {
                    $scope.webauthnMessage = (response && response.error) ? response.error : 'Registration failed.';
                    $scope.webauthnMessageError = true;
                }
            })
            .catch(function(error) {
                var msg = (error && error.message) ? error.message : 'Passkey registration failed.';
                if (error && error.name === 'NotAllowedError') msg = 'Registration was cancelled or timed out.';
                $scope.webauthnMessage = msg;
                $scope.webauthnMessageError = true;
                console.error('Error registering passkey:', error);
            })
            .finally(function() {
                $scope.registerPasskeyLoading = false;
                if (!$scope.$$phase && !$scope.$root.$$phase) { try { $scope.$apply(); } catch (e) { /* already applied */ } }
            });
    };
    
    $scope.deleteCredential = function(credentialId) {
        if (!confirm('Are you sure you want to delete this passkey?')) return;
        
        if (!window.cyberPanelWebAuthn) {
            alert('WebAuthn is not supported in this browser');
            return;
        }
        
        window.cyberPanelWebAuthn.deleteCredential($scope.accountUsername, credentialId)
            .then(function(response) {
                if (response.success) {
                    $scope.loadWebAuthnData();
                    $scope.$apply();
                }
            })
            .catch(function(error) {
                console.error('Error deleting credential:', error);
            });
    };
    
    $scope.updateCredentialName = function(credentialId, newName) {
        if (!window.cyberPanelWebAuthn) return;
        
        window.cyberPanelWebAuthn.updateCredentialName($scope.accountUsername, credentialId, newName)
            .then(function(response) {
                if (response.success) {
                    $scope.loadWebAuthnData();
                    $scope.$apply();
                }
            })
            .catch(function(error) {
                console.error('Error updating credential name:', error);
            });
    };
    
    $scope.refreshCredentials = function() {
        $scope.loadWebAuthnData();
    };
    
    $scope.saveWebAuthnSettings = function() {
        if (!window.cyberPanelWebAuthn) {
            alert('WebAuthn is not supported in this browser');
            return;
        }
        
        var settings = {
            enabled: $scope.webauthnEnabled,
            require_passkey: $scope.webauthnRequirePasskey,
            allow_multiple_credentials: $scope.webauthnAllowMultiple,
            max_credentials: $scope.webauthnMaxCredentials,
            timeout_seconds: $scope.webauthnTimeout
        };
        
        window.cyberPanelWebAuthn.updateSettings($scope.accountUsername, settings)
            .then(function(response) {
                if (response.success) {
                    $scope.loadWebAuthnData();
                    $scope.$apply();
                }
            })
            .catch(function(error) {
                console.error('Error updating WebAuthn settings:', error);
            });
    };


    $scope.fetchUserDetails = function () {


        var accountUsername = $scope.accountUsername;
        if ($scope.newUserName && $scope.newUserName.trim()) {
            var proposedName = $scope.newUserName.trim();
            var originalName = ($scope.originalUserName || accountUsername || '').trim();
            if (proposedName !== originalName) {
                var usernameErr = $scope.validateUsernameFormat(proposedName);
                if (usernameErr) {
                    alert(usernameErr);
                    return;
                }
            }
        }



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


                $scope.originalUserName = accountUsername;
                $scope.newUserName = accountUsername;
                $scope.firstName = userDetails.firstName;
                $scope.lastName = userDetails.lastName;
                $scope.email = userDetails.email;
                $scope.securityLevel = userDetails.securityLevel;
                $scope.currentSecurityLevel = userDetails.securityLevel;
                $scope.sizeDisplayUnit = userDetails.sizeDisplayUnit || 'auto';
                $scope.twofa = Boolean(userDetails.twofa);
                
                // Format secret key with spaces for better readability
                if (userDetails.secretKey) {
                    $scope.secretKey = userDetails.secretKey;
                    $scope.formattedSecretKey = userDetails.secretKey.match(/.{1,4}/g).join(' ');
                }
                
                // Initialize WebAuthn settings
                $scope.webauthnEnabled = false;
                $scope.webauthnRequirePasskey = false;
                $scope.webauthnAllowMultiple = true;
                $scope.webauthnMaxCredentials = 10;
                $scope.webauthnTimeout = 60;
                $scope.webauthnCredentials = [];
                $scope.canAddCredential = true;
                $scope.webauthnDataLoaded = false;
                // Load WebAuthn settings and credentials
                $scope.loadWebAuthnData();

                if (qrCode) qrCode.set({ value: userDetails.otpauth });

                $scope.userModificationLoading = true;
                $scope.acctDetailsFetched = false;
                $scope.userModified = true;
                $scope.canotModifyUser = false;   // hide modify error (we only fetched details)
                $scope.couldNotConnect = true;
                $scope.canotFetchDetails = false;  // hide fetch error on success
                $scope.detailsFetched = false;
                $scope.userAccountsLimit = true;
                $scope.websitesLimit = true;

            } else {
                $scope.userModificationLoading = true;
                $scope.acctDetailsFetched = true;
                $scope.userAccountsLimit = true;
                $scope.userModified = true;
                $scope.canotModifyUser = false;   // hide modify error (only fetch failed)
                $scope.couldNotConnect = true;
                $scope.canotFetchDetails = true;   // show fetch error on failure
                $scope.detailsFetched = false;


                $scope.errorMessage = (response.data && (response.data.error_message || response.data.message || response.data.errorMessage)) || 'Unknown error';


            }


        }

        function cantLoadInitialDatas(response) {

            $scope.userModificationLoading = true;
            $scope.acctDetailsFetched = true;
            $scope.userAccountsLimit = true;
            $scope.userModified = true;
            $scope.canotModifyUser = false;   // hide modify error (only connection/fetch failed)
            $scope.couldNotConnect = false;
            $scope.canotFetchDetails = true;
            $scope.detailsFetched = true;


        }


    };


    $scope.validateUsernameFormat = function (name) {
        if (!name || !String(name).trim()) {
            return 'Username is required.';
        }
        name = String(name).trim();
        if (name.length < 3 || name.length > 50) {
            return 'Username must be 3 to 50 characters.';
        }
        if (!/^[A-Za-z0-9_-]+$/.test(name)) {
            return 'Username may only contain letters, numbers, underscore, and hyphen.';
        }
        return '';
    };

    $scope.modifyUser = function () {


        $scope.userModificationLoading = false;
        $scope.acctDetailsFetched = false;
        $scope.userModified = true;
        $scope.canotModifyUser = false;  // hide modify error until we know result
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
            securityLevel: $scope.securityLevel,
            twofa: $scope.twofa,
            sizeDisplayUnit: $scope.sizeDisplayUnit || 'auto'
        };
        if ($scope.newUserName && String($scope.newUserName).trim()) {
            data.newUserName = String($scope.newUserName).trim();
        }

        // Only include password if it's provided and not empty
        if (password && password.trim()) {
            data.passwordByPass = password;
        }

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(function(response) {
            ListInitialDatas(response);
            // Save WebAuthn settings after successful user modification (only if WebAuthn script loaded)
            if (response.data.saveStatus == 1 && window.cyberPanelWebAuthn) {
                $scope.saveWebAuthnSettings();
            }
        }, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.saveStatus == 1) {

                $scope.userModificationLoading = true;
                $scope.acctDetailsFetched = true;
                $scope.userModified = false;
                $scope.canotModifyUser = false;  // hide modify error on success
                $scope.couldNotConnect = true;
                $scope.canotFetchDetails = false;  // hide "Cannot fetch details" on save success
                $scope.detailsFetched = true;
                $scope.userAccountsLimit = true;
                $scope.accountTypeView = true;
                $scope.websitesLimit = true;

                if (response.data.userName) {
                    $scope.accountUsername = response.data.userName;
                    $scope.originalUserName = response.data.userName;
                    $scope.newUserName = response.data.userName;
                }
                if (response.data.userRenamed == 1) {
                    if (response.data.forceLogout == 1) {
                        alert('Username updated to ' + response.data.userName + '. You will be logged out now; sign in with the new username.');
                        window.location.href = '/logout';
                        return;
                    }
                    alert('Username updated. User must sign in as: ' + response.data.userName);
                }

                $scope.userName = response.data.userName || accountUsername;


            } else {

                $scope.userModificationLoading = true;
                $scope.acctDetailsFetched = false;
                $scope.userModified = true;
                $scope.canotModifyUser = true;   // show modify error on failure
                $scope.couldNotConnect = true;
                $scope.canotFetchDetails = true;
                $scope.detailsFetched = true;


                $scope.errorMessage = (response.data && (response.data.error_message || response.data.message || response.data.errorMessage)) || 'Unknown error';


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
            $scope.errorMessage = (response && response.data && (response.data.error_message || response.data.message || response.data.errorMessage)) || 'Unknown error';

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

app.controller('createACLCTRL', function ($scope, $http) {

    $scope.aclCreated = true;
    $scope.aclCreationFailed = false;  // false = don't show error alert on load
    $scope.couldNotConnect = true;

    $scope.aclLoading = true;
    $scope.makeAdmin = false;

    //

    $scope.versionManagement = false;

    // Plugin Management (granular)

    $scope.viewPlugins = false;
    $scope.usePlugins = false;
    $scope.installPlugins = false;

    // User Management

    $scope.createNewUser = false;
    $scope.listUsers = false;
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
    $scope.listPackages = false;
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
    $scope.listEmails = true;
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
    $scope.googleDriveBackups = true;
    $scope.restoreBackup = false;
    $scope.addDeleteDestinations = false;
    $scope.scheduleBackups = false;
    $scope.remoteBackups = false;


    // SSL Management

    $scope.manageSSL = true;
    $scope.hostnameSSL = false;
    $scope.mailServerSSL = false;


    $scope.createACLFunc = function () {

        $scope.aclLoading = false;

        var url = "/users/createACLFunc";

        var data = {

            aclName: $scope.aclName,
            makeAdmin: $scope.makeAdmin,

            //
            versionManagement: $scope.versionManagement,

            // Plugin Management (granular)

            viewPlugins: $scope.viewPlugins,
            usePlugins: $scope.usePlugins,
            installPlugins: $scope.installPlugins,

            // User Management

            createNewUser: $scope.createNewUser,
            listUsers: $scope.listUsers,
            resellerCenter: $scope.resellerCenter,
            deleteUser: $scope.deleteUser,
            changeUserACL: $scope.changeUserACL,

            // Website Management

            createWebsite: $scope.createWebsite,
            modifyWebsite: $scope.modifyWebsite,
            suspendWebsite: $scope.suspendWebsite,
            deleteWebsite: $scope.deleteWebsite,

            // Package Management

            createPackage: $scope.createPackage,
            listPackages: $scope.listPackages,
            deletePackage: $scope.deletePackage,
            modifyPackage: $scope.modifyPackage,

            // Database Management

            createDatabase: $scope.createDatabase,
            deleteDatabase: $scope.deleteDatabase,
            listDatabases: $scope.listDatabases,

            // DNS Management

            createNameServer: $scope.createNameServer,
            createDNSZone: $scope.createDNSZone,
            deleteZone: $scope.deleteZone,
            addDeleteRecords: $scope.addDeleteRecords,

            // Email Management

            createEmail: $scope.createEmail,
            listEmails: $scope.listEmails,
            deleteEmail: $scope.deleteEmail,
            emailForwarding: $scope.emailForwarding,
            changeEmailPassword: $scope.changeEmailPassword,
            dkimManager: $scope.dkimManager,

            // FTP Management

            createFTPAccount: $scope.createFTPAccount,
            deleteFTPAccount: $scope.deleteFTPAccount,
            listFTPAccounts: $scope.listFTPAccounts,

            // Backup Management

            createBackup: $scope.createBackup,
            googleDriveBackups: $scope.googleDriveBackups,
            restoreBackup: $scope.restoreBackup,
            addDeleteDestinations: $scope.addDeleteDestinations,
            scheduleBackups: $scope.scheduleBackups,
            remoteBackups: $scope.remoteBackups,

            // SSL Management

            manageSSL: $scope.manageSSL,
            hostnameSSL: $scope.hostnameSSL,
            mailServerSSL: $scope.mailServerSSL

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
                safePNotify({
                    title: 'Success!',
                    text: 'ACL Successfully created.',
                    type: 'success'
                });
            } else {

                safePNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.aclLoading = false;

            safePNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });

        }


    };

    $scope.adminHook = function () {

        if ($scope.makeAdmin === true) {

            $scope.makeAdmin = true;

            //

            $scope.versionManagement = true;
            $scope.viewPlugins = true;
            $scope.usePlugins = true;
            $scope.installPlugins = true;

            // User Management

            $scope.createNewUser = true;
            $scope.listUsers = true;
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
            $scope.listPackages = true;
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
            $scope.listEmails = true;
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
            $scope.scheduleBackups = true;
            $scope.remoteBackups = true;

            // SSL Management

            $scope.manageSSL = true;
            $scope.hostnameSSL = true;
            $scope.mailServerSSL = true;

        } else {
            $scope.makeAdmin = false;

            //

            $scope.versionManagement = false;
            $scope.viewPlugins = false;
            $scope.usePlugins = false;
            $scope.installPlugins = false;

            // User Management

            $scope.createNewUser = false;
            $scope.listUsers = false;
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
            $scope.listPackages = false;
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
            $scope.listEmails = true;
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
            $scope.scheduleBackups = false;
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
                safePNotify({
                    title: 'Success!',
                    text: 'ACL Successfully deleted.',
                    type: 'success'
                });

            } else {
                safePNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.aclLoading = true;
            safePNotify({
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
                safePNotify({
                    title: 'Success!',
                    text: 'Current settings successfully fetched',
                    type: 'success'
                });

                $scope.aclDetails = false;

                $scope.makeAdmin = Boolean(response.data.adminStatus);

                //

                $scope.versionManagement = Boolean(response.data.versionManagement);

                $scope.viewPlugins = Boolean(response.data.viewPlugins);
                $scope.usePlugins = Boolean(response.data.usePlugins);
                $scope.installPlugins = Boolean(response.data.installPlugins);

                // User Management

                $scope.createNewUser = Boolean(response.data.createNewUser);
                $scope.listUsers = Boolean(response.data.listUsers);
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
                $scope.listPackages = Boolean(response.data.listPackages);
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
                $scope.listEmails = Boolean(response.data.listEmails);
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
                $scope.googleDriveBackups = Boolean(response.data.googleDriveBackups);
                $scope.restoreBackup = Boolean(response.data.restoreBackup);
                $scope.addDeleteDestinations = Boolean(response.data.addDeleteDestinations);
                $scope.scheduleBackups = Boolean(response.data.scheduleBackups);
                $scope.remoteBackups = Boolean(response.data.remoteBackups);

                // SSL Management

                $scope.manageSSL = Boolean(response.data.manageSSL);
                $scope.hostnameSSL = Boolean(response.data.hostnameSSL);
                $scope.mailServerSSL = Boolean(response.data.mailServerSSL);

            } else {
                safePNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.aclLoading = false;

            safePNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });

        }

    };

    $scope.saveChanges = function () {

        $scope.aclLoading = false;

        var url = "/users/submitACLModifications";

        var data = {
            aclToModify: $scope.aclToModify,
            adminStatus: $scope.makeAdmin,
            //
            versionManagement: $scope.versionManagement,

            // Plugin Management (granular)

            viewPlugins: $scope.viewPlugins,
            usePlugins: $scope.usePlugins,
            installPlugins: $scope.installPlugins,

            // User Management

            createNewUser: $scope.createNewUser,
            listUsers: $scope.listUsers,
            resellerCenter: $scope.resellerCenter,
            deleteUser: $scope.deleteUser,
            changeUserACL: $scope.changeUserACL,

            // Website Management

            createWebsite: $scope.createWebsite,
            modifyWebsite: $scope.modifyWebsite,
            suspendWebsite: $scope.suspendWebsite,
            deleteWebsite: $scope.deleteWebsite,

            // Package Management

            createPackage: $scope.createPackage,
            listPackages: $scope.listPackages,
            deletePackage: $scope.deletePackage,
            modifyPackage: $scope.modifyPackage,

            // Database Management

            createDatabase: $scope.createDatabase,
            deleteDatabase: $scope.deleteDatabase,
            listDatabases: $scope.listDatabases,

            // DNS Management

            createNameServer: $scope.createNameServer,
            createDNSZone: $scope.createDNSZone,
            deleteZone: $scope.deleteZone,
            addDeleteRecords: $scope.addDeleteRecords,

            // Email Management

            createEmail: $scope.createEmail,
            listEmails: $scope.listEmails,
            deleteEmail: $scope.deleteEmail,
            emailForwarding: $scope.emailForwarding,
            changeEmailPassword: $scope.changeEmailPassword,
            dkimManager: $scope.dkimManager,

            // FTP Management

            createFTPAccount: $scope.createFTPAccount,
            deleteFTPAccount: $scope.deleteFTPAccount,
            listFTPAccounts: $scope.listFTPAccounts,

            // Backup Management

            createBackup: $scope.createBackup,
            googleDriveBackups: $scope.googleDriveBackups,
            restoreBackup: $scope.restoreBackup,
            addDeleteDestinations: $scope.addDeleteDestinations,
            scheduleBackups: $scope.scheduleBackups,
            remoteBackups: $scope.remoteBackups,

            // SSL Management

            manageSSL: $scope.manageSSL,
            hostnameSSL: $scope.hostnameSSL,
            mailServerSSL: $scope.mailServerSSL

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
                safePNotify({
                    title: 'Success!',
                    text: 'ACL Successfully modified.',
                    type: 'success'
                });
            } else {

                safePNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.aclLoading = false;

            safePNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });

        }


    };

    $scope.adminHook = function () {

        if ($scope.makeAdmin === true) {

            $scope.makeAdmin = true;

            //

            $scope.versionManagement = true;
            $scope.viewPlugins = true;
            $scope.usePlugins = true;
            $scope.installPlugins = true;

            // User Management

            $scope.createNewUser = true;
            $scope.listUsers = true;
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
            $scope.listPackages = true;
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
            $scope.listEmails = true;
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
            $scope.scheduleBackups = true;
            $scope.remoteBackups = true;

            // SSL Management

            $scope.manageSSL = true;
            $scope.hostnameSSL = true;
            $scope.mailServerSSL = true;

        } else {
            $scope.makeAdmin = false;

            //

            $scope.versionManagement = false;
            $scope.viewPlugins = false;
            $scope.usePlugins = false;
            $scope.installPlugins = false;

            // User Management

            $scope.createNewUser = false;
            $scope.listUsers = false;
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
            $scope.listPackages = false;
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
            $scope.listEmails = true;
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
            $scope.scheduleBackups = false;
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
                safePNotify({
                    title: 'Success!',
                    text: 'ACL Successfully changed.',
                    type: 'success'
                });

            } else {
                safePNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.aclLoading = true;
            safePNotify({
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
                safePNotify({
                    title: 'Success!',
                    text: 'Changes successfully applied!',
                    type: 'success'
                });

            } else {
                safePNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.aclLoading = true;
            safePNotify({
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
                safePNotify({
                    title: 'Success!',
                    text: 'Changes successfully applied!',
                    type: 'success'
                });

            } else {
                safePNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            safePNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }


    };


});
/* Java script code for api access */

/* Java script code for api users list */
app.controller('apiUsersCTRL', function ($scope, $http) {
    $scope.apiUsers = [];
    $scope.filteredUsers = [];
    $scope.searchQuery = '';
    $scope.apiUsersLoading = true;

    $scope.loadAPIUsers = function() {
        $scope.apiUsersLoading = false;
        
        var url = "/users/fetchAPIUsers";
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.get(url, config).then(loadAPIUsersSuccess, loadAPIUsersError);
    };

    function loadAPIUsersSuccess(response) {
        $scope.apiUsersLoading = true;
        
        if (response.data.status === 1) {
            $scope.apiUsers = response.data.users;
            $scope.filteredUsers = response.data.users;
            
            safePNotify({
                title: 'Success!',
                text: 'API users loaded successfully',
                type: 'success'
            });
        } else {
            safePNotify({
                title: 'Error!',
                text: response.data.error_message,
                type: 'error'
            });
        }
    }

    function loadAPIUsersError(response) {
        $scope.apiUsersLoading = true;
        safePNotify({
            title: 'Error!',
            text: 'Could not load API users. Please refresh the page.',
            type: 'error'
        });
    }

    $scope.searchUsers = function() {
        if (!$scope.searchQuery || $scope.searchQuery.trim() === '') {
            $scope.filteredUsers = $scope.apiUsers;
            return;
        }
        
        var query = $scope.searchQuery.toLowerCase();
        $scope.filteredUsers = $scope.apiUsers.filter(function(user) {
            return user.userName.toLowerCase().includes(query) ||
                   user.firstName.toLowerCase().includes(query) ||
                   user.lastName.toLowerCase().includes(query) ||
                   user.email.toLowerCase().includes(query) ||
                   user.aclName.toLowerCase().includes(query);
        });
    };

    $scope.clearSearch = function() {
        $scope.searchQuery = '';
        $scope.filteredUsers = $scope.apiUsers;
    };

    $scope.viewUserDetails = function(user) {
        safePNotify({
            title: 'User Details',
            text: 'Username: ' + user.userName + '<br>' +
                  'Full Name: ' + user.firstName + ' ' + user.lastName + '<br>' +
                  'Email: ' + user.email + '<br>' +
                  'ACL: ' + user.aclName + '<br>' +
                  'Token Status: ' + user.tokenStatus + '<br>' +
                  'State: ' + user.state,
            type: 'info',
            styling: 'bootstrap3',
            delay: 10000
        });
    };

    $scope.disableAPI = function(user) {
        if (confirm('Are you sure you want to disable API access for ' + user.userName + '?')) {
            $scope.apiUsersLoading = false;
            
            var url = "/users/saveChangesAPIAccess";
            var data = {
                accountUsername: user.userName,
                access: 'Disable'
            };
            var config = {
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            };

            $http.post(url, data, config).then(disableAPISuccess, disableAPIError);
        }
    };

    function disableAPISuccess(response) {
        $scope.apiUsersLoading = true;
        
        if (response.data.status === 1) {
            // Remove user from the list
            $scope.apiUsers = $scope.apiUsers.filter(function(u) {
                return u.userName !== response.data.accountUsername;
            });
            $scope.filteredUsers = $scope.apiUsers;
            
            safePNotify({
                title: 'Success!',
                text: 'API access disabled for ' + response.data.accountUsername,
                type: 'success'
            });
        } else {
            safePNotify({
                title: 'Error!',
                text: response.data.error_message,
                type: 'error'
            });
        }
    }

    function disableAPIError(response) {
        $scope.apiUsersLoading = true;
        safePNotify({
            title: 'Error!',
            text: 'Could not disable API access. Please try again.',
            type: 'error'
        });
    }

    // Load API users when controller initializes
    $scope.loadAPIUsers();
});

/* Java script code to list table users */

/* Show modal by id - works with Bootstrap 3 (jQuery) or Bootstrap 5 (native) */
function showModalById(modalId) {
    var el = document.getElementById(modalId);
    if (!el) return;
    if (typeof jQuery !== 'undefined' && jQuery(el).modal) {
        jQuery(el).modal('show');
    } else if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        var m = bootstrap.Modal.getOrCreateInstance(el);
        if (m) m.show();
    } else {
        el.style.display = 'block';
        el.classList.add('in');
        if (el.getAttribute('aria-hidden') !== null) el.setAttribute('aria-hidden', 'false');
        var backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop fade in';
        backdrop.setAttribute('data-modal-backdrop', modalId);
        document.body.appendChild(backdrop);
    }
}

function hideModalById(modalId) {
    var el = document.getElementById(modalId);
    if (!el) return;
    if (typeof jQuery !== 'undefined' && jQuery(el).modal) {
        jQuery(el).modal('hide');
    } else if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        var m = bootstrap.Modal.getInstance(el);
        if (m) m.hide();
    } else {
        el.style.display = 'none';
        el.classList.remove('in');
        if (el.getAttribute('aria-hidden') !== null) el.setAttribute('aria-hidden', 'true');
        var backdrops = document.querySelectorAll('[data-modal-backdrop="' + modalId + '"]');
        backdrops.forEach(function (b) { if (b.parentNode) b.parentNode.removeChild(b); });
    }
}

app.controller('listTableUsers', function ($scope, $http) {

    $scope.cyberpanelLoading = true;

    var UserToDelete;

    /**
     * Reload the user table from the server.
     * @param {boolean} [suppressSuccessNotify=false] - When true, no success toast (avoids double popups after delete/edit/suspend when the caller already notified).
     */
    $scope.populateCurrentRecords = function (suppressSuccessNotify) {
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

                if (!suppressSuccessNotify) {
                    safePNotify({
                        title: 'Success!',
                        text: 'Users successfully fetched!',
                        type: 'success'
                    });
                }

            } else {
                safePNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            safePNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });
        }

    };
    /* Initial load: silent (no "fetched" toast on every page open) */
    $scope.populateCurrentRecords(true);


    $scope.deleteUserInitial = function (name){
        UserToDelete = name;
        $scope.UserToDelete = name;
        showModalById('deleteModal');
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
                $scope.populateCurrentRecords(true);
                hideModalById('deleteModal');
                safePNotify({
                    title: 'Success!',
                    text: 'Users successfully deleted!',
                    type: 'success'
                });

            } else {

                safePNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.cyberpanelLoading = false;
            safePNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }


    };

    $scope.editInitial = function (name) {
        $scope.name = name;
        showModalById('editModal');
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
                $scope.populateCurrentRecords(true);
                hideModalById('editModal');
                safePNotify({
                    title: 'Success!',
                    text: 'Changes successfully applied!',
                    type: 'success'
                });

            } else {
                safePNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            safePNotify({
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
                $scope.populateCurrentRecords(true);
                hideModalById('editModal');
                safePNotify({
                    title: 'Success!',
                    text: 'ACL Successfully changed.',
                    type: 'success'
                });

            } else {
                safePNotify({
                    title: 'Error!',
                    text: response.data.errorMessage,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.aclLoading = true;
            safePNotify({
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
                $scope.populateCurrentRecords(true);
                safePNotify({
                    title: 'Success!',
                    text: 'Action successfully started.',
                    type: 'success'
                });

            } else {

                safePNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.cyberpanelLoading = false;
            safePNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    }

});


/* Java script code to list table users */
