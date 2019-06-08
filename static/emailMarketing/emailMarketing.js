/**
 * Created by usman on 8/1/17.
 */

var emailListURL = "/emailMarketing/"+ $("#domainNamePage").text() + "/emailLists";
$("#emailLists").attr("href", emailListURL);
$("#emailListsChild").attr("href", emailListURL);

var manageListsURL = "/emailMarketing/"+ $("#domainNamePage").text() + "/manageLists";
$("#manageLists").attr("href", manageListsURL);
$("#manageListsChild").attr("href", manageListsURL);

var sendEmailsURL = "/emailMarketing/sendEmails";
$("#sendEmailsPage").attr("href", sendEmailsURL);
$("#sendEmailsPageChild").attr("href", sendEmailsURL);

var composeEmailURL = "/emailMarketing/composeEmailMessage";
$("#composeEmails").attr("href", composeEmailURL);
$("#composeEmailsChild").attr("href", composeEmailURL);

var smtpHostsURL = "/emailMarketing/"+ $("#domainNamePage").text() + "/manageSMTP";
$("#manageSMTPHosts").attr("href", smtpHostsURL);
$("#manageSMTPHostsChild").attr("href", smtpHostsURL);


app.controller('emailMarketing', function($scope,$http) {

                $scope.cyberPanelLoading = true;
                $scope.fetchUsers = function(){
                    $scope.cyberPanelLoading = false;

                url = "/emailMarketing/fetchUsers";

                    var data = {};

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.cyberPanelLoading = true;

                    if(response.data.status === 1){
                        $scope.users = JSON.parse(response.data.data);
                    }
                    else{
                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.error_message,
                            type:'error'
                            });
                    }
                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = false;
                        new PNotify({
                            title: 'Operation Failed!',
                            text: 'Could not connect to server, please refresh this page',
                            type:'error'
                            });

                }

               };
                $scope.fetchUsers();
                $scope.enableDisableMarketing = function(status, userName){
                    $scope.cyberPanelLoading = false;

                    url = "/emailMarketing/enableDisableMarketing";

                    var data = {userName: userName};

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                    $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                    function ListInitialDatas(response) {
                        $scope.cyberPanelLoading = true;
                        $scope.fetchUsers();

                        if(response.data.status === 1){
                            new PNotify({
                                title: 'Success!',
                                text: 'Changes successfully saved.',
                                type:'success'
                                });
                        }
                        else{
                            new PNotify({
                                title: 'Operation Failed!',
                                text: response.data.error_message,
                                type:'error'
                                });
                        }
                    }
                    function cantLoadInitialDatas(response) {
                        $scope.cyberPanelLoading = false;
                            new PNotify({
                                title: 'Operation Failed!',
                                text: 'Could not connect to server, please refresh this page',
                                type:'error'
                                });

                    }

               };
});

app.controller('createEmailList', function($scope, $http, $timeout) {

    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.cyberPanelLoading = true;
    $scope.goBackDisable = true;

    var statusFile;
    var path;


    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.cyberPanelLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    $scope.createEmailList = function(){

                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.cyberPanelLoading = false;
                $scope.goBackDisable = true;
                $scope.currentStatus = "Starting to load email addresses..";


                url = "/emailMarketing/submitEmailList";

                var data = {
                    domain: $("#domainNamePage").text(),
                    path:$scope.path,
                    listName: $scope.listName
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if (response.data.status === 1)
                    {
                        statusFile = response.data.tempStatusPath;
                        getInstallStatus();
                    }
                    else{

                        $scope.installationDetailsForm = true;
                        $scope.cyberPanelLoading = true;
                        $scope.goBackDisable = false;

                        new PNotify({
                                title: 'Operation Failed!',
                                text: response.data.error_message,
                                type:'error'
                                });

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    new PNotify({
                        title: 'Operation Failed!',
                        text: 'Could not connect to server, please refresh this page',
                        type:'error'
                    });

                }

    };

    function getInstallStatus(){

                        url = "/websites/installWordpressStatus";

                        var data = {
                            statusFile: statusFile,
                            domainName: $("#domainNamePage").text()
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.abort === 1){

                        if(response.data.installStatus === 1){

                            $scope.installationDetailsForm = true;
                            $scope.installationProgress = false;
                            $scope.cyberPanelLoading = true;
                            $scope.goBackDisable = false;
                            $scope.currentStatus = 'Emails successfully loaded.';
                            $timeout.cancel();

                        }
                        else{

                            $scope.installationDetailsForm = true;
                            $scope.installationProgress = false;
                            $scope.cyberPanelLoading = true;
                            $scope.goBackDisable = false;
                            $scope.currentStatus = response.data.error_message;


                        }

                    }
                    else{
                        $scope.installPercentage = response.data.installationProgress;
                        $scope.currentStatus = response.data.currentStatus;

                        $timeout(getInstallStatus,1000);
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    new PNotify({
                        title: 'Operation Failed!',
                        text: 'Could not connect to server, please refresh this page',
                        type:'error'
                    });


                }


           }

    $scope.fetchEmails = function(){
                $scope.cyberPanelLoading = false;

                url = "/emailMarketing/fetchEmails";

                    var data = {'listName': $scope.listName};

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.cyberPanelLoading = true;

                    if(response.data.status === 1){
                        $scope.records = JSON.parse(response.data.data);
                    }
                    else{
                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.error_message,
                            type:'error'
                            });
                    }
                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = false;
                        new PNotify({
                            title: 'Operation Failed!',
                            text: 'Could not connect to server, please refresh this page',
                            type:'error'
                            });

                }

               };


});

app.controller('manageEmailLists', function($scope, $http, $timeout) {

    $scope.installationDetailsForm = true;
    $scope.installationProgress = true;
    $scope.cyberPanelLoading = true;
    $scope.goBackDisable = true;
    $scope.verificationStatus = true;

    var statusFile;
    var path;


    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.cyberPanelLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    $scope.createEmailList = function(){

                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.cyberPanelLoading = false;
                $scope.goBackDisable = true;
                $scope.currentStatus = "Starting to load email addresses..";


                url = "/emailMarketing/submitEmailList";

                var data = {
                    domain: $("#domainNamePage").text(),
                    path:$scope.path,
                    listName: $scope.listName
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if (response.data.status === 1)
                    {
                        statusFile = response.data.tempStatusPath;
                        getInstallStatus();
                    }
                    else{

                        $scope.installationDetailsForm = true;
                        $scope.cyberPanelLoading = true;
                        $scope.goBackDisable = false;

                        new PNotify({
                                title: 'Operation Failed!',
                                text: response.data.error_message,
                                type:'error'
                                });

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    new PNotify({
                        title: 'Operation Failed!',
                        text: 'Could not connect to server, please refresh this page',
                        type:'error'
                    });

                }

    };

    function getInstallStatus(){

                        url = "/websites/installWordpressStatus";

                        var data = {
                            statusFile: statusFile,
                            domainName: $("#domainNamePage").text()
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.abort === 1){

                        if(response.data.installStatus === 1){

                            $scope.installationDetailsForm = true;
                            $scope.installationProgress = false;
                            $scope.cyberPanelLoading = true;
                            $scope.goBackDisable = false;
                            $scope.currentStatus = 'Emails successfully loaded.';
                            $timeout.cancel();

                        }
                        else{

                            $scope.installationDetailsForm = true;
                            $scope.installationProgress = false;
                            $scope.cyberPanelLoading = true;
                            $scope.goBackDisable = false;
                            $scope.currentStatus = response.data.error_message;


                        }

                    }
                    else{
                        $scope.installPercentage = response.data.installationProgress;
                        $scope.currentStatus = response.data.currentStatus;

                        $timeout(getInstallStatus,1000);
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    new PNotify({
                        title: 'Operation Failed!',
                        text: 'Could not connect to server, please refresh this page',
                        type:'error'
                    });


                }


           }


    ///

    $scope.currentRecords = true;

    $scope.recordstoShow = 50;
    var globalPage;

    $scope.fetchRecords = function () {
        $scope.fetchEmails(globalPage);
    };

    $scope.fetchEmails = function(page){
                globalPage = page;
                listVerificationStatus();

                $scope.cyberPanelLoading = false;

                url = "/emailMarketing/fetchEmails";

                    var data = {
                        'listName': $scope.listName,
                        'recordstoShow': $scope.recordstoShow,
                        'page': page

                    };

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.cyberPanelLoading = true;

                    if(response.data.status === 1){
                        $scope.currentRecords = false;
                        $scope.records = JSON.parse(response.data.data);
                        $scope.pagination = response.data.pagination;
                    }
                    else{
                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.error_message,
                            type:'error'
                            });
                    }
                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = false;
                        new PNotify({
                            title: 'Operation Failed!',
                            text: 'Could not connect to server, please refresh this page',
                            type:'error'
                            });

                }

               };

    $scope.deleteList = function () {

                $scope.cyberPanelLoading = false;

                url = "/emailMarketing/deleteList";

                var data = {
                    listName: $scope.listName
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    if (response.data.status === 1)
                    {
                        new PNotify({
                                title: 'Success!',
                                text: 'Emails Successfully Deleted.',
                                type:'success'
                                });
                    }
                    else{

                        $scope.cyberPanelLoading = false;

                        new PNotify({
                                title: 'Operation Failed!',
                                text: response.data.error_message,
                                type:'error'
                                });

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    new PNotify({
                        title: 'Operation Failed!',
                        text: 'Could not connect to server, please refresh this page',
                        type:'error'
                    });

                }

    };

    $scope.showAddEmails = function () {
        $scope.installationDetailsForm = false;
        $scope.verificationStatus = true;
    };

    // List Verification

    $scope.startVerification = function () {

        $scope.currentStatusVerification = 'Email verification job started..';
        $scope.installationDetailsForm = true;
        $scope.verificationStatus = false;
        $scope.verificationButton = true;
        $scope.cyberPanelLoading = false;

        url = "/emailMarketing/emailVerificationJob";

                var data = {
                    listName: $scope.listName
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if (response.data.status === 1)
                    {
                        listVerificationStatus();
                        $scope.verificationButton = true;
                    }
                    else{

                        $scope.cyberPanelLoading = true;
                        $scope.verificationButton = false;

                        new PNotify({
                                title: 'Operation Failed!',
                                text: response.data.error_message,
                                type:'error'
                                });

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    $scope.verificationButton = false;
                    new PNotify({
                        title: 'Operation Failed!',
                        text: 'Could not connect to server, please refresh this page',
                        type:'error'
                    });

                }


    };

    var globalCounter = 0;

    function listVerificationStatus(){

                $scope.verificationButton = true;
                $scope.cyberPanelLoading = false;

                url = "/websites/installWordpressStatus";

                        var data = {
                            domain: $("#domainNamePage").text(),
                            statusFile: "/home/cyberpanel/" + $("#domainNamePage").text() + "/" + $scope.listName
                        };

                var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.abort === 1){

                        if(response.data.installStatus === 1){
                            $scope.cyberPanelLoading = true;
                            $scope.verificationButton = false;
                            $scope.currentStatusVerification = 'Emails successfully verified.';
                            $timeout.cancel();

                        }
                        else{

                            if(response.data.error_message.search('No such file') > -1){
                                $scope.verificationButton = false;
                                return;
                            }
                            $scope.verificationButton = true;
                            $scope.cyberPanelLoading = false;
                            $scope.verificationStatus = false;
                            $scope.currentStatusVerification = response.data.error_message;

                        }

                    }
                    else{
                        $scope.currentStatusVerification = response.data.currentStatus;
                        $timeout(listVerificationStatus,1000);
                        $scope.verificationStatus = false;
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    new PNotify({
                        title: 'Operation Failed!',
                        text: 'Could not connect to server, please refresh this page',
                        type:'error'
                    });


                }


           }

    // Delete Email from list

    $scope.deleteEmail = function(id){

                $scope.cyberPanelLoading = false;

                url = "/emailMarketing/deleteEmail";

                var data = {
                    id: id
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    $scope.fetchEmails(globalPage);

                    if (response.data.status === 1)
                    {
                        $scope.fetchEmails(globalPage);
                        new PNotify({
                            title: 'Success.',
                            text: 'Email Successfully deleted.',
                            type:'success'
                        });

                    }
                    else{

                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.error_message,
                            type:'error'
                        });

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    new PNotify({
                        title: 'Operation Failed!',
                        text: 'Could not connect to server, please refresh this page',
                        type:'error'
                    });

                }

    };


});

app.controller('manageSMTPHostsCTRL', function($scope, $http) {

                $scope.cyberPanelLoading = true;
                $scope.fetchSMTPHosts = function(){
                    $scope.cyberPanelLoading = false;

                url = "/emailMarketing/fetchSMTPHosts";

                    var data = {};

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.cyberPanelLoading = true;

                    if(response.data.status === 1){
                        $scope.records = JSON.parse(response.data.data);
                    }
                    else{
                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.error_message,
                            type:'error'
                            });
                    }
                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = false;
                        new PNotify({
                            title: 'Operation Failed!',
                            text: 'Could not connect to server, please refresh this page',
                            type:'error'
                            });

                }

               };
                $scope.fetchSMTPHosts();
                $scope.saveSMTPHost = function(status, userName){
                    $scope.cyberPanelLoading = false;

                    url = "/emailMarketing/saveSMTPHost";

                    var data = {
                        smtpHost: $scope.smtpHost,
                        smtpPort: $scope.smtpPort,
                        smtpUserName: $scope.smtpUserName,
                        smtpPassword: $scope.smtpPassword
                    };

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                    $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                    function ListInitialDatas(response) {
                        $scope.cyberPanelLoading = true;

                        if(response.data.status === 1){
                            $scope.fetchSMTPHosts();
                            new PNotify({
                                title: 'Success!',
                                text: 'Successfully saved new SMTP host.',
                                type:'success'
                                });
                        }
                        else{
                            new PNotify({
                                title: 'Operation Failed!',
                                text: response.data.error_message,
                                type:'error'
                                });
                        }
                    }
                    function cantLoadInitialDatas(response) {
                        $scope.cyberPanelLoading = false;
                            new PNotify({
                                title: 'Operation Failed!',
                                text: 'Could not connect to server, please refresh this page',
                                type:'error'
                                });

                    }

               };
                $scope.smtpHostOperations = function(operation, id){
                    $scope.cyberPanelLoading = false;

                    url = "/emailMarketing/smtpHostOperations";

                    var data = {
                        id: id,
                        operation: operation
                    };

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                    $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                    function ListInitialDatas(response) {
                        $scope.cyberPanelLoading = true;
                        $scope.fetchSMTPHosts();

                        if(response.data.status === 1){
                            new PNotify({
                                title: 'Success!',
                                text: response.data.message,
                                type:'success'
                                });
                        }
                        else{
                            new PNotify({
                                title: 'Operation Failed!',
                                text: response.data.error_message,
                                type:'error'
                                });
                        }
                    }
                    function cantLoadInitialDatas(response) {
                        $scope.cyberPanelLoading = false;
                            new PNotify({
                                title: 'Operation Failed!',
                                text: 'Could not connect to server, please refresh this page',
                                type:'error'
                                });

                    }

               };
});

app.controller('composeMessageCTRL', function($scope, $http) {

                $scope.cyberPanelLoading = true;
                $scope.saveTemplate = function(status, userName){
                    $scope.cyberPanelLoading = false;

                    url = "/emailMarketing/saveEmailTemplate";

                    var data = {
                        name: $scope.name,
                        subject: $scope.subject,
                        fromName: $scope.fromName,
                        fromEmail: $scope.fromEmail,
                        replyTo: $scope.replyTo,
                        emailMessage: $scope.emailMessage
                    };

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                    $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                    function ListInitialDatas(response) {
                        $scope.cyberPanelLoading = true;

                        if(response.data.status === 1){
                            new PNotify({
                                title: 'Success!',
                                text: 'Template successfully saved.',
                                type:'success'
                                });
                        }
                        else{
                            new PNotify({
                                title: 'Operation Failed!',
                                text: response.data.error_message,
                                type:'error'
                                });
                        }
                    }
                    function cantLoadInitialDatas(response) {
                        $scope.cyberPanelLoading = false;
                            new PNotify({
                                title: 'Operation Failed!',
                                text: 'Could not connect to server, please refresh this page',
                                type:'error'
                                });

                    }

               };
});

app.controller('sendEmailsCTRL', function($scope, $http, $timeout) {

                $scope.cyberPanelLoading = true;
                $scope.availableFunctions = true;
                $scope.sendEmailsView = true;
                $scope.jobStatus = true;

                // Button

                $scope.deleteTemplateBTN = false;
                $scope.sendEmailBTN = false;

                $scope.templateSelected = function () {
                    $scope.availableFunctions = false;
                    $scope.sendEmailsView = true;
                    $scope.previewLink = '/emailMarketing/preview/' + $scope.selectedTemplate;
                    $scope.jobStatus = true;
                    emailJobStatus();

                };

                $scope.sendEmails = function () {
                    $scope.sendEmailsView = false;
                    $scope.fetchJobs();
                };

                $scope.fetchJobs = function(){

                $scope.cyberPanelLoading = false;

                url = "/emailMarketing/fetchJobs";

                    var data = {
                        'selectedTemplate': $scope.selectedTemplate
                    };

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.cyberPanelLoading = true;

                    if(response.data.status === 1){
                        $scope.currentRecords = false;
                        $scope.records = JSON.parse(response.data.data);
                    }
                    else{
                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.error_message,
                            type:'error'
                            });
                    }
                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = false;
                        new PNotify({
                            title: 'Operation Failed!',
                            text: 'Could not connect to server, please refresh this page',
                            type:'error'
                            });

                }

               };

                $scope.startEmailJob = function () {
                    $scope.cyberPanelLoading = false;
                    $scope.deleteTemplateBTN = true;
                    $scope.sendEmailBTN = true;
                    $scope.sendEmailsView = true;
                    $scope.goBackDisable = true;

                    url = "/emailMarketing/startEmailJob";


                    var data = {
                        'selectedTemplate': $scope.selectedTemplate,
                        'listName': $scope.listName,
                        'host': $scope.host,
                        'verificationCheck': $scope.verificationCheck,
                        'unsubscribeCheck': $scope.unsubscribeCheck
                    };

                    var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.cyberPanelLoading = true;

                    if(response.data.status === 1){
                        emailJobStatus();
                    }
                    else{
                        $scope.cyberPanelLoading = true;
                        $scope.deleteTemplateBTN = false;
                        $scope.sendEmailBTN = false;
                        $scope.sendEmailsView = false;
                        $scope.jobStatus = true;
                        $scope.goBackDisable = false;
                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.error_message,
                            type:'error'
                            });
                    }
                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = false;
                        new PNotify({
                            title: 'Operation Failed!',
                            text: 'Could not connect to server, please refresh this page',
                            type:'error'
                            });

                }


                };

                function emailJobStatus(){

                    $scope.cyberPanelLoading = false;
                    $scope.deleteTemplateBTN = true;
                    $scope.sendEmailBTN = true;
                    $scope.sendEmailsView = true;
                    $scope.jobStatus = false;
                    $scope.goBackDisable = true;

                url = "/websites/installWordpressStatus";

                        var data = {
                            domain: 'example.com',
                            statusFile: "/home/cyberpanel/" + $scope.selectedTemplate + "_pendingJob"
                        };

                var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.abort === 1){

                        if(response.data.installStatus === 1){
                            $scope.cyberPanelLoading = true;
                            $scope.deleteTemplateBTN = false;
                            $scope.sendEmailBTN = false;
                            $scope.sendEmailsView = true;
                            $scope.jobStatus = false;
                            $scope.goBackDisable = false;
                            $scope.currentStatus = 'Emails successfully sent.';
                            $scope.fetchJobs();
                            $timeout.cancel();

                        }
                        else{

                            if(response.data.error_message.search('No such file') > -1){
                                $scope.cyberPanelLoading = true;
                                $scope.deleteTemplateBTN = false;
                                $scope.sendEmailBTN = false;
                                $scope.sendEmailsView = true;
                                $scope.jobStatus = true;
                                $scope.goBackDisable = false;
                                return;
                            }
                            $scope.cyberPanelLoading = true;
                            $scope.deleteTemplateBTN = false;
                            $scope.sendEmailBTN = false;
                            $scope.sendEmailsView = true;
                            $scope.jobStatus = false;
                            $scope.goBackDisable = false;
                            $scope.currentStatus = response.data.error_message;

                        }

                    }
                    else{
                        $scope.currentStatus = response.data.currentStatus;
                        $timeout(emailJobStatus,1000);
                        $scope.cyberPanelLoading = false;
                        $scope.deleteTemplateBTN = true;
                        $scope.sendEmailBTN = true;
                        $scope.sendEmailsView = true;
                        $scope.jobStatus = false;
                        $scope.goBackDisable = true;
                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    new PNotify({
                        title: 'Operation Failed!',
                        text: 'Could not connect to server, please refresh this page.',
                        type:'error'
                    });


                }


           }

                $scope.goBack = function () {
                    $scope.cyberPanelLoading = true;
                    $scope.deleteTemplateBTN = false;
                    $scope.sendEmailBTN = false;
                    $scope.sendEmailsView = false;
                    $scope.jobStatus = true;

                };

                $scope.deleteTemplate = function(){

                $scope.cyberPanelLoading = false;

                url = "/emailMarketing/deleteTemplate";

                var data = {
                    selectedTemplate: $scope.selectedTemplate
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.cyberPanelLoading = true;

                    if (response.data.status === 1)
                    {
                        new PNotify({
                            title: 'Success.',
                            text: 'Template Successfully deleted.',
                            type:'success'
                        });

                    }
                    else{

                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.error_message,
                            type:'error'
                        });

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    new PNotify({
                        title: 'Operation Failed!',
                        text: 'Could not connect to server, please refresh this page',
                        type:'error'
                    });

                }

    };
                $scope.deleteJob = function(id){

                $scope.cyberPanelLoading = false;

                url = "/emailMarketing/deleteJob";

                var data = {
                    id: id
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    $scope.fetchJobs();

                    if (response.data.status === 1)
                    {
                        new PNotify({
                            title: 'Success.',
                            text: 'Template Successfully deleted.',
                            type:'success'
                        });

                    }
                    else{

                        new PNotify({
                            title: 'Operation Failed!',
                            text: response.data.error_message,
                            type:'error'
                        });

                    }

                }
                function cantLoadInitialDatas(response) {
                    $scope.cyberPanelLoading = true;
                    new PNotify({
                        title: 'Operation Failed!',
                        text: 'Could not connect to server, please refresh this page',
                        type:'error'
                    });

                }

    };
});


