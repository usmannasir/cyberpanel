/**
 * Created by usman on 7/26/17.
 */


$("#websiteCreationFailed").hide();
$("#websiteCreated").hide();
$("#webSiteCreation").hide();

/* Java script code to create account */
app.controller('createWebsite', function($scope,$http) {


    $scope.createWebsite = function(){

                if ($scope.sslCheck == true){
                    var ssl = 1;
                }
                else{
                    var ssl = 0
                }


                $("#webSiteCreation").fadeIn();

                url = "/websites/submitWebsiteCreation";

                var package = $scope.packageForWebsite;
                var domainName = $scope.domainNameCreate;
                var adminEmail = $scope.adminEmail;
                var phpSelection = $scope.phpSelection;
                var websiteOwner = $scope.websiteOwner;


                var data = {
                    package: package,
                    domainName: domainName,
                    adminEmail: adminEmail,
                    phpSelection: phpSelection,
                    ssl:ssl,
                    websiteOwner:websiteOwner,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    $("#webSiteCreation").fadeOut();

                    if(response.data.existsStatus == 1){
                        $scope.errorMessage = response.data.error_message;
                        $("#websiteCreationFailed").fadeIn();
                        $("#websiteCreated").hide();

                    }

                    else if (response.data.createWebSiteStatus == 0)
                    {
                        $scope.errorMessage = response.data.error_message;
                        $("#websiteCreationFailed").fadeIn();
                        $("#websiteCreated").hide();

                    }
                    else{

                        $("#websiteCreationFailed").hide();
                        $("#websiteCreated").fadeIn();
                        $scope.websiteDomain = domainName;

                    }


                }
                function cantLoadInitialDatas(response) {
                    $("#webSiteCreation").fadeOut();
                    console.log("not good");
                }





    };

});
/* Java script code to create account ends here */

/* Java script code to list accounts */

$("#listFail").hide();


app.controller('listWebsites', function($scope,$http) {


    url = "/websites/submitWebsiteListing";

    var data = {page: 1};

    var config = {
        headers : {
            'X-CSRFToken': getCookie('csrftoken')
        }
    };

    $http.post(url, data,config).then(ListInitialData, cantLoadInitialData);


    function ListInitialData(response) {

        if (response.data.listWebSiteStatus==1) {

            var finalData = JSON.parse(response.data.data);
            $scope.WebSitesList = finalData;
            $("#listFail").hide();
        }
        else
        {
            $("#listFail").fadeIn();
            $scope.errorMessage = response.data.error_message;

        }
    }
    function cantLoadInitialData(response) {
        console.log("not good");
    }


    $scope.getFurtherWebsitesFromDB = function(pageNumber) {

        var config = {
        headers : {
            'X-CSRFToken': getCookie('csrftoken')
        }
    };

    var data = {page: pageNumber};


    dataurl = "/websites/submitWebsiteListing";

    $http.post(dataurl, data,config).then(ListInitialData, cantLoadInitialData);


    function ListInitialData(response) {
        if (response.data.listWebSiteStatus==1) {

            var finalData = JSON.parse(response.data.data);
            $scope.WebSitesList = finalData;
            $("#listFail").hide();
        }
        else
        {
            $("#listFail").fadeIn();
            $scope.errorMessage = response.data.error_message;
            console.log(response.data);

        }
    }
    function cantLoadInitialData(response) {
        console.log("not good");
    }



        };
});

/* Java script code to list accounts ends here */



/* Java script code to delete Website */


$("#websiteDeleteFailure").hide();
$("#websiteDeleteSuccess").hide();

$("#deleteWebsiteButton").hide();
$("#deleteLoading").hide();

app.controller('deleteWebsiteControl', function($scope,$http) {


    $scope.deleteWebsite = function(){

        $("#deleteWebsiteButton").fadeIn();


    };

    $scope.deleteWebsiteFinal = function(){

                $("#deleteLoading").show();

                var websiteName = $scope.websiteToBeDeleted;



                url = "/websites/submitWebsiteDeletion";

                var data = {
                    websiteName: websiteName,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    console.log(response.data)

                    if (response.data.websiteDeleteStatus == 0)
                    {
                        $scope.errorMessage = response.data.error_message;
                        $("#websiteDeleteFailure").fadeIn();
                        $("#websiteDeleteSuccess").hide();
                        $("#deleteWebsiteButton").hide();


                         $("#deleteLoading").hide();

                    }
                    else{
                        $("#websiteDeleteFailure").hide();
                        $("#websiteDeleteSuccess").fadeIn();
                        $("#deleteWebsiteButton").hide();
                        $scope.deletedWebsite = websiteName;
                         $("#deleteLoading").hide();

                    }


                }
                function cantLoadInitialDatas(response) {
                    console.log("not good");
                }


    };

});



/* Java script code to delete website ends here */


/* Java script code to modify package ends here */

$("#canNotModify").hide();
$("#webSiteDetailsToBeModified").hide();
$("#websiteModifyFailure").hide();
$("#websiteModifySuccess").hide();
$("#websiteSuccessfullyModified").hide();
$("#modifyWebsiteLoading").hide();
$("#modifyWebsiteButton").hide();

app.controller('modifyWebsitesController', function($scope,$http) {

    $scope.fetchWebsites = function(){

        $("#modifyWebsiteLoading").show();


        var websiteToBeModified = $scope.websiteToBeModified;

        url = "/websites/getWebsiteDetails";

                var data = {
                    websiteToBeModified: websiteToBeModified,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if (response.data.modifyStatus == 0)
                    {
                        console.log(response.data);
                        $scope.errorMessage = response.data.error_message;
                        $("#websiteModifyFailure").fadeIn();
                        $("#websiteModifySuccess").hide();
                        $("#modifyWebsiteButton").hide();
                        $("#modifyWebsiteLoading").hide();
                        $("#canNotModify").hide();


                    }
                    else{
                        console.log(response.data);
                        $("#modifyWebsiteButton").fadeIn();

                        $scope.adminEmail = response.data.adminEmail;
                        $scope.currentPack = response.data.current_pack;
                        $scope.webpacks = JSON.parse(response.data.packages);
                        $scope.adminNames = JSON.parse(response.data.adminNames);
                        $scope.currentAdmin = response.data.currentAdmin;

                        $("#webSiteDetailsToBeModified").fadeIn();
                        $("#websiteModifySuccess").fadeIn();
                        $("#modifyWebsiteButton").fadeIn();
                        $("#modifyWebsiteLoading").hide();
                        $("#canNotModify").hide();




                    }


                }
                function cantLoadInitialDatas(response) {
                    $("#websiteModifyFailure").fadeIn();
                }

    };



    $scope.modifyWebsiteFunc = function () {

        var domain = $scope.websiteToBeModified;
        var packForWeb = $scope.selectedPack;
        var email = $scope.adminEmail;
        var phpVersion = $scope.phpSelection;
        var admin = $scope.selectedAdmin;



        $("#websiteModifyFailure").hide();
        $("#websiteModifySuccess").hide();
        $("#websiteSuccessfullyModified").hide();
        $("#canNotModify").hide();
        $("#modifyWebsiteLoading").fadeIn();



        url = "/websites/saveWebsiteChanges";

                var data = {
                    domain: domain,
                    packForWeb:packForWeb,
                    email:email,
                    phpVersion:phpVersion,
                    admin:admin,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if (response.data.saveStatus == 0)
                    {
                        $scope.errMessage = response.data.error_message;

                        $("#canNotModify").fadeIn();
                        $("#websiteModifyFailure").hide();
                        $("#websiteModifySuccess").hide();
                        $("#websiteSuccessfullyModified").hide();
                        $("#modifyWebsiteLoading").hide();


                    }
                    else{
                        $("#modifyWebsiteButton").hide();
                        $("#canNotModify").hide();
                        $("#websiteModifyFailure").hide();
                        $("#websiteModifySuccess").hide();

                        $("#websiteSuccessfullyModified").fadeIn();
                        $("#modifyWebsiteLoading").hide();

                        $scope.websiteModified = domain;


                    }


                }
                function cantLoadInitialDatas(response) {
                    $scope.errMessage = response.data.error_message;
                    $("#canNotModify").fadeIn();
                }



    };

});



/* Java script code to Modify Pacakge ends here */


/* Java script code to create account */

app.controller('websitePages', function($scope,$http) {

    $scope.logFileLoading = true;
    $scope.logsFeteched = true;
    $scope.couldNotFetchLogs = true;
    $scope.couldNotConnect = true;
    $scope.fetchedData = true;
    $scope.hideLogs = true;

    $scope.hidelogsbtn = function(){
        $scope.hideLogs = true;
    };

    $scope.fileManagerURL = "filemanager/"+$("#domainNamePage").text();

    var logType = 0;
    $scope.pageNumber = 1;

    $scope.fetchLogs = function(type){

                pageNumber = $scope.pageNumber;


                if(type==3){
                    pageNumber = $scope.pageNumber+1;
                    $scope.pageNumber = pageNumber;
                }
                else if(type==4){
                    pageNumber = $scope.pageNumber-1;
                    $scope.pageNumber = pageNumber;
                }
                else{
                    logType = type;
                }


                $scope.logFileLoading = false;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedData = false;



                url = "/websites/getDataFromLogFile";

                var domainNamePage = $("#domainNamePage").text();





                var data = {
                    logType: logType,
                    virtualHost:domainNamePage,
                    page:pageNumber,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.logstatus == 1){


                        $scope.logFileLoading = true;
                        $scope.logsFeteched = false;
                        $scope.couldNotFetchLogs = true;
                        $scope.couldNotConnect = true;
                        $scope.fetchedData = false;
                        $scope.hideLogs = false;


                        $scope.records = JSON.parse(response.data.data);

                    }

                    else
                    {

                        $scope.logFileLoading = true;
                        $scope.logsFeteched = true;
                        $scope.couldNotFetchLogs = false;
                        $scope.couldNotConnect = true;
                        $scope.fetchedData = true;
                        $scope.hideLogs = false;


                        $scope.errorMessage = response.data.error_message;
                        console.log(domainNamePage)

                    }


                }
                function cantLoadInitialDatas(response) {

                    $scope.logFileLoading = true;
                    $scope.logsFeteched = true;
                    $scope.couldNotFetchLogs = true;
                    $scope.couldNotConnect = false;
                    $scope.fetchedData = true;
                    $scope.hideLogs = false;

                }



    };


    ///////// Configurations Part

    $scope.configurationsBox = true;
    $scope.configsFetched = true;
    $scope.couldNotFetchConfigs = true;
    $scope.couldNotConnect = true;
    $scope.fetchedConfigsData = true;
    $scope.configFileLoading = true;
    $scope.configSaved = true;
    $scope.couldNotSaveConfigurations = true;

    $scope.hideconfigbtn = function(){

        $scope.configurationsBox = true;
    };

    $scope.fetchConfigurations = function(){


                $scope.hidsslconfigs = true;
                $scope.configurationsBoxRewrite = true;


                //Rewrite rules
                $scope.configurationsBoxRewrite = true;
                $scope.rewriteRulesFetched = true;
                $scope.couldNotFetchRewriteRules = true;
                $scope.rewriteRulesSaved = true;
                $scope.couldNotSaveRewriteRules = true;
                $scope.fetchedRewriteRules = true;
                $scope.saveRewriteRulesBTN = true;

                ///

                $scope.configFileLoading = false;



                url = "/websites/getDataFromConfigFile";

                var virtualHost = $("#domainNamePage").text();



                var data = {
                    virtualHost: virtualHost,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.configstatus == 1){

                        //Rewrite rules

                            $scope.configurationsBoxRewrite = true;
                            $scope.rewriteRulesFetched = true;
                            $scope.couldNotFetchRewriteRules = true;
                            $scope.rewriteRulesSaved = true;
                            $scope.couldNotSaveRewriteRules = true;
                            $scope.fetchedRewriteRules = true;
                            $scope.saveRewriteRulesBTN = true;

                        ///

                        $scope.configurationsBox = false;
                        $scope.configsFetched = false;
                        $scope.couldNotFetchConfigs = true;
                        $scope.couldNotConnect = true;
                        $scope.fetchedConfigsData = false;
                        $scope.configFileLoading = true;
                        $scope.configSaved = true;
                        $scope.couldNotSaveConfigurations = true;
                        $scope.saveConfigBtn = false;



                        $scope.configData = response.data.configData;

                    }

                    else
                    {

                        //Rewrite rules
                            $scope.configurationsBoxRewrite = true;
                            $scope.rewriteRulesFetched = true;
                            $scope.couldNotFetchRewriteRules = true;
                            $scope.rewriteRulesSaved = true;
                            $scope.couldNotSaveRewriteRules = true;
                            $scope.fetchedRewriteRules = true;
                            $scope.saveRewriteRulesBTN = true;

                        ///
                        $scope.configurationsBox = false;
                        $scope.configsFetched = true;
                        $scope.couldNotFetchConfigs = false;
                        $scope.couldNotConnect = true;
                        $scope.fetchedConfigsData = true;
                        $scope.configFileLoading = true;
                        $scope.configSaved = true;
                        $scope.couldNotSaveConfigurations = true;



                        $scope.errorMessage = response.data.error_message;

                    }


                }
                function cantLoadInitialDatas(response) {

                    //Rewrite rules
                        $scope.configurationsBoxRewrite = true;
                        $scope.rewriteRulesFetched = true;
                        $scope.couldNotFetchRewriteRules = true;
                        $scope.rewriteRulesSaved = true;
                        $scope.couldNotSaveRewriteRules = true;
                        $scope.fetchedRewriteRules = true;
                        $scope.saveRewriteRulesBTN = true;
                ///

                    $scope.configurationsBox = false;
                    $scope.configsFetched = true;
                    $scope.couldNotFetchConfigs = true;
                    $scope.couldNotConnect = false;
                    $scope.fetchedConfigsData = true;
                    $scope.configFileLoading = true;
                    $scope.configSaved = true;
                    $scope.couldNotSaveConfigurations = true;


                }



    };

    $scope.saveCongiruations = function(){

                $scope.configFileLoading = false;



                url = "/websites/saveConfigsToFile";

                var virtualHost = $("#domainNamePage").text();
                var configData = $scope.configData;



                var data = {
                    virtualHost: virtualHost,
                    configData:configData,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.configstatus == 1){

                        $scope.configurationsBox = false;
                        $scope.configsFetched = true;
                        $scope.couldNotFetchConfigs = true;
                        $scope.couldNotConnect = true;
                        $scope.fetchedConfigsData = true;
                        $scope.configFileLoading = true;
                        $scope.configSaved = false;
                        $scope.couldNotSaveConfigurations = true;
                        $scope.saveConfigBtn = true;


                    }

                    else
                    {
                        $scope.configurationsBox = false;
                        $scope.configsFetched = true;
                        $scope.couldNotFetchConfigs = true;
                        $scope.couldNotConnect = true;
                        $scope.fetchedConfigsData = false;
                        $scope.configFileLoading = true;
                        $scope.configSaved = true;
                        $scope.couldNotSaveConfigurations = false;


                        $scope.errorMessage = response.data.error_message;

                    }


                }
                function cantLoadInitialDatas(response) {

                    $scope.configurationsBox = false;
                        $scope.configsFetched = true;
                        $scope.couldNotFetchConfigs = true;
                        $scope.couldNotConnect = false;
                        $scope.fetchedConfigsData = true;
                        $scope.configFileLoading = true;
                        $scope.configSaved = true;
                        $scope.couldNotSaveConfigurations = true;


                }



    };


    ///////// Rewrite Rules

    $scope.configurationsBoxRewrite = true;
    $scope.rewriteRulesFetched = true;
    $scope.couldNotFetchRewriteRules = true;
    $scope.rewriteRulesSaved = true;
    $scope.couldNotSaveRewriteRules = true;
    $scope.fetchedRewriteRules = true;
    $scope.saveRewriteRulesBTN = true;

    $scope.hideRewriteRulesbtn = function() {
        $scope.configurationsBoxRewrite = true;
    };


    $scope.fetchRewriteFules = function(){

                $scope.hidsslconfigs = true;
                $scope.configurationsBox = true;


                $scope.configurationsBox = true;
                $scope.configsFetched = true;
                $scope.couldNotFetchConfigs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedConfigsData = true;
                $scope.configFileLoading = true;
                $scope.configSaved = true;
                $scope.couldNotSaveConfigurations = true;
                $scope.saveConfigBtn = true;

                $scope.configFileLoading = false;



                url = "/websites/getRewriteRules";

                var virtualHost = $("#domainNamePage").text();



                var data = {
                    virtualHost: virtualHost,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.rewriteStatus == 1){


                        // from main

                        $scope.configurationsBox = true;
                        $scope.configsFetched = true;
                        $scope.couldNotFetchConfigs = true;
                        $scope.fetchedConfigsData = true;
                        $scope.configSaved = true;
                        $scope.couldNotSaveConfigurations = true;
                        $scope.saveConfigBtn = true;

                        // main ends

                        $scope.configFileLoading = true;

                        //


                        $scope.configurationsBoxRewrite = false;
                        $scope.rewriteRulesFetched = false;
                        $scope.couldNotFetchRewriteRules = true;
                        $scope.rewriteRulesSaved = true;
                        $scope.couldNotSaveRewriteRules = true;
                        $scope.fetchedRewriteRules = false;
                        $scope.saveRewriteRulesBTN = false;
                        $scope.couldNotConnect = true;



                        $scope.rewriteRules = response.data.rewriteRules;

                    }

                    else
                    {
                        // from main
                        $scope.configurationsBox = true;
                        $scope.configsFetched = true;
                        $scope.couldNotFetchConfigs = true;
                        $scope.fetchedConfigsData = true;
                        $scope.configFileLoading = true;
                        $scope.configSaved = true;
                        $scope.couldNotSaveConfigurations = true;
                        $scope.saveConfigBtn = true;
                        // from main

                        $scope.configFileLoading = true;

                        ///

                        $scope.configurationsBoxRewrite = true;
                        $scope.rewriteRulesFetched = true;
                        $scope.couldNotFetchRewriteRules = false;
                        $scope.rewriteRulesSaved = true;
                        $scope.couldNotSaveRewriteRules = true;
                        $scope.fetchedRewriteRules = true;
                        $scope.saveRewriteRulesBTN = true;
                        $scope.couldNotConnect = true;



                        $scope.errorMessage = response.data.error_message;

                    }


                }
                function cantLoadInitialDatas(response) {
                        // from main

                        $scope.configurationsBox = true;
                        $scope.configsFetched = true;
                        $scope.couldNotFetchConfigs = true;
                        $scope.fetchedConfigsData = true;
                        $scope.configFileLoading = true;
                        $scope.configSaved = true;
                        $scope.couldNotSaveConfigurations = true;
                        $scope.saveConfigBtn = true;

                        // from main

                        $scope.configFileLoading = true;

                        ///

                        $scope.configurationsBoxRewrite = true;
                        $scope.rewriteRulesFetched = true;
                        $scope.couldNotFetchRewriteRules = true;
                        $scope.rewriteRulesSaved = true;
                        $scope.couldNotSaveRewriteRules = true;
                        $scope.fetchedRewriteRules = true;
                        $scope.saveRewriteRulesBTN = true;

                        $scope.couldNotConnect = false;


                }



    };

    $scope.saveRewriteRules = function(){

                $scope.configFileLoading = false;



                url = "/websites/saveRewriteRules";

                var virtualHost = $("#domainNamePage").text();
                var rewriteRules = $scope.rewriteRules;



                var data = {
                    virtualHost: virtualHost,
                    rewriteRules:rewriteRules,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.rewriteStatus == 1){

                        $scope.configurationsBoxRewrite = false;
                        $scope.rewriteRulesFetched = true;
                        $scope.couldNotFetchRewriteRules = true;
                        $scope.rewriteRulesSaved = false;
                        $scope.couldNotSaveRewriteRules = true;
                        $scope.fetchedRewriteRules = true;
                        $scope.saveRewriteRulesBTN = true;
                        $scope.configFileLoading = true;


                    }

                    else
                    {
                        $scope.configurationsBoxRewrite = false;
                        $scope.rewriteRulesFetched = false;
                        $scope.couldNotFetchRewriteRules = true;
                        $scope.rewriteRulesSaved = true;
                        $scope.couldNotSaveRewriteRules = false;
                        $scope.fetchedRewriteRules = true;
                        $scope.saveRewriteRulesBTN = false;

                        $scope.configFileLoading = true;


                        $scope.errorMessage = response.data.error_message;

                    }


                }
                function cantLoadInitialDatas(response) {

                        $scope.configurationsBoxRewrite = false;
                        $scope.rewriteRulesFetched = false;
                        $scope.couldNotFetchRewriteRules = true;
                        $scope.rewriteRulesSaved = true;
                        $scope.couldNotSaveRewriteRules = true;
                        $scope.fetchedRewriteRules = true;
                        $scope.saveRewriteRulesBTN = false;

                        $scope.configFileLoading = true;

                        $scope.couldNotConnect = false;


                }



    };





    //////// Application Installation part

    $scope.installationDetailsForm = true;
    $scope.applicationInstallerLoading = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;



    $scope.installationDetails = function(){

        $scope.installationDetailsForm = false;


    }


    $scope.installWordpress = function(){


                $scope.installationDetailsForm = false;
                $scope.applicationInstallerLoading = false;
                $scope.installationFailed = true;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;

                var domain = $("#domainNamePage").text();
                var path = $scope.installPath;

                url = "/websites/installWordpress";

                var home = "1";

                if (typeof path != 'undefined'){
                    home = "0";
                }


                var data = {
                    domain: domain,
                    home:home,
                    path:path,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if (response.data.installStatus == 1)
                    {
                        if (typeof path != 'undefined'){
                            $scope.installationURL = "http://"+domain+"/"+path;
                        }
                        else{
                            $scope.installationURL = domain;
                        }

                        $scope.installationDetailsForm = false;
                        $scope.applicationInstallerLoading = true;
                        $scope.installationFailed = true;
                        $scope.installationSuccessfull = false;
                        $scope.couldNotConnect = true;

                    }
                    else{

                        $scope.installationDetailsForm = false;
                        $scope.applicationInstallerLoading = true;
                        $scope.installationFailed = false;
                        $scope.installationSuccessfull = true;
                        $scope.couldNotConnect = true;

                        $scope.errorMessage = response.data.error_message;

                    }


                }
                function cantLoadInitialDatas(response) {

                    $scope.installationDetailsForm = false;
                    $scope.applicationInstallerLoading = true;
                    $scope.installationFailed = true;
                    $scope.installationSuccessfull = true;
                    $scope.couldNotConnect = false;

                }

    };




    //////// SSL Part

    $scope.sslSaved = true;
    $scope.couldNotSaveSSL = true;
    $scope.hidsslconfigs = true;
    $scope.couldNotConnect = true;


    $scope.hidesslbtn = function(){
        $scope.hidsslconfigs = true;
    };

    $scope.addSSL = function(){
        $scope.hidsslconfigs = false;
        $scope.configurationsBox = true;
        $scope.configurationsBoxRewrite = true;
    };


    $scope.saveSSL = function(){


                $scope.configFileLoading = false;

                url = "/websites/saveSSL";

                var virtualHost = $("#domainNamePage").text();
                var cert = $scope.cert;
                var key = $scope.key;



                var data = {
                    virtualHost: virtualHost,
                    cert:cert,
                    key:key,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if(response.data.sslStatus == 1){

                        $scope.sslSaved = false;
                        $scope.couldNotSaveSSL = true;
                        $scope.couldNotConnect = true;
                        $scope.configFileLoading = true;


                    }

                    else
                    {

                        $scope.sslSaved = true;
                        $scope.couldNotSaveSSL = false;
                        $scope.couldNotConnect = true;
                        $scope.configFileLoading = true;

                        $scope.errorMessage = response.data.error_message;

                    }


                }
                function cantLoadInitialDatas(response) {

                        $scope.sslSaved = true;
                        $scope.couldNotSaveSSL = true;
                        $scope.couldNotConnect = false;
                        $scope.configFileLoading = true;




                }

    };


    ////// create domain part

    $("#domainCreationForm").hide();

    $scope.showCreateDomainForm = function () {
        $("#domainCreationForm").fadeIn();
    };

    $scope.hideDomainCreationForm = function () {
        $("#domainCreationForm").fadeOut();
    };

    $scope.masterDomain = $("#domainNamePage").text();

    // notifcations settings
    $scope.domainLoading = true;
    $scope.websiteCreationFailed = true;
    $scope.domainCreated = true;
    $scope.couldNotConnect = true;

    $scope.createDomain = function(){

                // notifcations settings
                $scope.domainLoading = false;
                $scope.websiteCreationFailed = true;
                $scope.domainCreated = true;
                $scope.couldNotConnect = true;

                if ($scope.sslCheck === true){
                    var ssl = 1;
                }
                else{
                    var ssl = 0
                }


                url = "/websites/submitDomainCreation";
                var domainName = $scope.domainNameCreate;
                var phpSelection = $scope.phpSelection;

                var path = $scope.docRootPath;

                if (typeof path === 'undefined'){
                    path = "";
                }


                var data = {
                    domainName: domainName,
                    phpSelection: phpSelection,
                    ssl:ssl,
                    path:path,
                    masterDomain:$("#domainNamePage").text(),
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.createWebSiteStatus === 1){

                        $scope.websiteDomain = domainName;

                        // notifcations settings
                        $scope.domainLoading = true;
                        $scope.websiteCreationFailed = true;
                        $scope.domainCreated = false;
                        $scope.couldNotConnect = true


                    }
                    else{

                        $scope.errorMessage = response.data.error_message;

                        // notifcations settings
                        $scope.domainLoading = true;
                        $scope.websiteCreationFailed = false;
                        $scope.domainCreated = true;
                        $scope.couldNotConnect = true;

                    }


                }
                function cantLoadInitialDatas(response) {

                        // notifcations settings
                        $scope.domainLoading = true;
                        $scope.websiteCreationFailed = true;
                        $scope.domainCreated = true;
                        $scope.couldNotConnect = false;

                }





    };


    ////// List Domains Part

    ////////////////////////

    // notifcations

    $scope.phpChanged = true;
    $scope.domainError = true;
    $scope.couldNotConnect = true;
    $scope.domainDeleted = true;
    $scope.sslIssued = true;

    $("#listDomains").hide();


    $scope.showListDomains = function () {
        fetchDomains();
        $("#listDomains").fadeIn();
    };

    $scope.hideListDomains = function () {
        $("#listDomains").fadeOut();
    };

    function fetchDomains(){
                $scope.domainLoading = false;

                var url = "/websites/fetchDomains";

                var data = {
                    masterDomain:$("#domainNamePage").text(),
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.fetchStatus === 1){

                        $scope.childDomains = JSON.parse(response.data.data);
                        $scope.domainLoading = true;


                    }
                    else{
                        $scope.domainError = false;
                        $scope.errorMessage = response.data.error_message;
                        $scope.domainLoading = true;
                    }


                }
                function cantLoadInitialDatas(response) {

                $scope.couldNotConnect = false;

                }

    }


    $scope.changePHP = function(childDomain,phpSelection){

                // notifcations

                $scope.phpChanged = true;
                $scope.domainError = true;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;
                $scope.domainLoading = false;

                var url = "/websites/changePHP";

                var data = {
                    childDomain:childDomain,
                    phpSelection:phpSelection,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.changePHP === 1){

                        $scope.domainLoading = true;

                        $scope.changedPHPVersion = phpSelection;


                        // notifcations

                        $scope.phpChanged = false;
                        $scope.domainError = true;
                        $scope.couldNotConnect = true;
                        $scope.domainDeleted = true;
                        $scope.sslIssued = true;


                    }
                    else{
                        $scope.errorMessage = response.data.error_message;
                        $scope.domainLoading = true;

                        // notifcations

                        $scope.phpChanged = true;
                        $scope.domainError = false;
                        $scope.couldNotConnect = true;
                        $scope.domainDeleted = true;
                        $scope.sslIssued = true;
                    }


                }
                function cantLoadInitialDatas(response) {

                        $scope.domainLoading = true;

                         // notifcations

                        $scope.phpChanged = true;
                        $scope.domainError = false;
                        $scope.couldNotConnect = true;
                        $scope.domainDeleted = true;
                        $scope.sslIssued = true;

                }

    }

    $scope.deleteChildDomain = function(childDomain){
                $scope.domainLoading = false;

                // notifcations

                $scope.phpChanged = true;
                $scope.domainError = true;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;

                url = "/websites/submitDomainDeletion";

                var data = {
                    websiteName: childDomain,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.websiteDeleteStatus === 1){

                        $scope.domainLoading = true;
                        $scope.deletedDomain = childDomain;

                        fetchDomains();


                        // notifications

                        $scope.phpChanged = true;
                        $scope.domainError = true;
                        $scope.couldNotConnect = true;
                        $scope.domainDeleted = false;
                        $scope.sslIssued = true;



                    }
                    else{
                        $scope.errorMessage = response.data.error_message;
                        $scope.domainLoading = true;

                        // notifcations

                        $scope.phpChanged = true;
                        $scope.domainError = false;
                        $scope.couldNotConnect = true;
                        $scope.domainDeleted = true;
                        $scope.sslIssued = true;
                    }


                }
                function cantLoadInitialDatas(response) {

                        $scope.domainLoading = true;

                         // notifcations

                        $scope.phpChanged = true;
                        $scope.domainError = true;
                        $scope.couldNotConnect = false;
                        $scope.domainDeleted = true;
                        $scope.sslIssued = true;

                }

    }

    $scope.issueSSL = function(childDomain,path){
                $scope.domainLoading = false;

                // notifcations

                $scope.phpChanged = true;
                $scope.domainError = true;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;

                var url = "/manageSSL/issueSSL";


                var data = {
                    virtualHost:childDomain,
                    path:path,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.SSL == 1){

                        $scope.domainLoading = true;

                        // notifcations

                        $scope.phpChanged = true;
                        $scope.domainError = true;
                        $scope.couldNotConnect = true;
                        $scope.domainDeleted = true;
                        $scope.sslIssued = false;



                        $scope.sslDomainIssued = childDomain;


                    }

                    else
                    {
                        $scope.domainLoading = true;

                        $scope.errorMessage = response.data.error_message;

                        // notifcations

                        $scope.phpChanged = true;
                        $scope.domainError = false;
                        $scope.couldNotConnect = true;
                        $scope.domainDeleted = true;
                        $scope.sslIssued = true;

                    }



                }
                function cantLoadInitialDatas(response) {

                    // notifcations

                    $scope.phpChanged = true;
                    $scope.domainError = true;
                    $scope.couldNotConnect = false;
                    $scope.domainDeleted = true;
                    $scope.sslIssued = true;


                }





    };




});

/* Java script code to create account ends here */



/* Java script code to suspend/un-suspend Website */




app.controller('suspendWebsiteControl', function($scope,$http) {

    $scope.suspendLoading = true;
    $scope.stateView = true;

    $scope.websiteSuspendFailure = true;
    $scope.websiteUnsuspendFailure = true;
    $scope.websiteSuccess = true;
    $scope.couldNotConnect = true;

    $scope.showSuspendUnsuspend = function(){

        $scope.stateView = false;


    };

    $scope.save = function(){

                $scope.suspendLoading = false;

                var websiteName = $scope.websiteToBeSuspended
                var state = $scope.state;


                url = "/websites/submitWebsiteStatus";

                var data = {
                    websiteName: websiteName,
                    state: state,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    console.log(response.data)

                    if (response.data.websiteStatus == 1)
                    {
                        if(state=="Suspend"){

                            $scope.suspendLoading = true;
                            $scope.stateView = false;

                            $scope.websiteSuspendFailure = true;
                            $scope.websiteUnsuspendFailure = true;
                            $scope.websiteSuccess = false;
                            $scope.couldNotConnect = true;

                            $scope.websiteStatus = websiteName;
                            $scope.finalStatus = "Suspended";

                        }
                        else{
                            $scope.suspendLoading = true;
                            $scope.stateView = false;

                            $scope.websiteSuspendFailure = true;
                            $scope.websiteUnsuspendFailure = true;
                            $scope.websiteSuccess = false;
                            $scope.couldNotConnect = true;

                            $scope.websiteStatus = websiteName;
                            $scope.finalStatus = "Un-suspended";

                        }

                    }
                    else{

                            if(state=="Suspend"){

                            $scope.suspendLoading = true;
                            $scope.stateView = false;

                            $scope.websiteSuspendFailure = false;
                            $scope.websiteUnsuspendFailure = true;
                            $scope.websiteSuccess = true;
                            $scope.couldNotConnect = true;


                        }
                        else{
                            $scope.suspendLoading = true;
                            $scope.stateView = false;

                            $scope.websiteSuspendFailure = true;
                            $scope.websiteUnsuspendFailure = false;
                            $scope.websiteSuccess = true;
                            $scope.couldNotConnect = true;


                        }


                        $scope.errorMessage = response.data.error_message;

                    }


                }
                function cantLoadInitialDatas(response) {
                    $scope.couldNotConnect = false;
                    $scope.suspendLoading = true;
                    $scope.stateView = true;

                    $scope.websiteSuspendFailure = true;
                    $scope.websiteUnsuspendFailure = true;
                    $scope.websiteSuccess = true;

                }


    };

});



/* Java script code to suspend/un-suspend ends here */