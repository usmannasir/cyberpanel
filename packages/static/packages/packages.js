/**
 * Created by usman on 7/25/17.
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


/* Java script code to create Pacakge */

$("#packageCreationFailed").hide();
$("#packageCreated").hide();

app.controller('createPackage', function($scope,$http) {

    //$scope.pname = /([A-Z]){3,10}/gi;

    $scope.insertPackInDB = function(){

                var packageName = $scope.packageName;
                var diskSpace =  $scope.diskSpace;
                var bandwidth =  $scope.bandwidth;
                var ftpAccounts =  $scope.ftpAccounts;
                var dataBases =  $scope.dataBases;
                var emails = $scope.emails;


                url = "/packages/submitPackage";

                var data = {
                    packageName: packageName,
                    diskSpace: diskSpace,
                    bandwidth: bandwidth,
                    ftpAccounts: ftpAccounts,
                    dataBases: dataBases,
                    emails:emails,
                    allowedDomains:$scope.allowedDomains
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    console.log(response.data)

                    if (response.data.saveStatus == 0)
                    {
                        $scope.errorMessage = response.data.error_message;
                        $("#packageCreationFailed").fadeIn();
                        $("#packageCreated").hide();

                    }
                    else{
                        $("#packageCreationFailed").hide();
                        $("#packageCreated").fadeIn();
                        $scope.createdPackage = $scope.packageName;

                    }


                }
                function cantLoadInitialDatas(response) {
                    console.log("not good");
                }


    };

});

/* Java script code to to create Pacakge ends here */

/* Java script code to delete Pacakge */

$("#deleteFailure").hide();
$("#deleteSuccess").hide();

$("#deletePackageButton").hide();

app.controller('deletePackage', function($scope,$http) {


    $scope.deletePackage = function(){

        $("#deletePackageButton").fadeIn();


    };

    $scope.deletePackageFinal = function(){


                var packageName = $scope.packageToBeDeleted;



                url = "/packages/submitDelete";

                var data = {
                    packageName: packageName,
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {
                    console.log(response.data)

                    if (response.data.deleteStatus == 0)
                    {
                        $scope.errorMessage = response.data.error_message;
                        $("#deleteFailure").fadeIn();
                        $("#deleteSuccess").hide();
                        $("#deletePackageButton").hide();

                    }
                    else{
                        $("#deleteFailure").hide();
                        $("#deleteSuccess").fadeIn();
                        $("#deletePackageButton").hide();
                        $scope.deletedPackage = packageName;

                    }


                }
                function cantLoadInitialDatas(response) {
                    console.log("not good");
                }


    };

});

/* Java script code to delete package ends here */

/* Java script code modify package */

$("#packageDetailsToBeModified").hide();
$("#modifyFailure").hide();
$("#modifySuccess").hide();
$("#modifyButton").hide();
$("#packageLoading").hide();
$("#successfullyModified").hide();

app.controller('modifyPackages', function($scope,$http) {

    $scope.fetchDetails = function(){

        $("#packageLoading").show();
        $("#successfullyModified").hide();

        var packageName = $scope.packageToBeModified;
        console.log(packageName);


        url = "/packages/submitModify";

                var data = {
                    packageName: packageName,
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
                        $scope.errorMessage = response.data.error_message;
                        $("#modifyFailure").fadeIn();
                        $("#modifySuccess").hide();
                        $("#modifyButton").hide();
                        $("#packageLoading").hide();


                    }
                    else{
                        $("#modifyButton").show();
                        $scope.diskSpace = response.data.diskSpace;
                        $scope.bandwidth = response.data.bandwidth;
                        $scope.ftpAccounts = response.data.ftpAccounts;
                        $scope.dataBases = response.data.dataBases;
                        $scope.emails = response.data.emails;
                        $scope.allowedDomains = response.data.allowedDomains;

                        $scope.modifyButton = "Save Details"

                        $("#packageDetailsToBeModified").fadeIn();

                        $("#modifyFailure").hide();
                        $("#modifySuccess").fadeIn();
                        $("#packageLoading").hide();




                    }


                }
                function cantLoadInitialDatas(response) {
                    console.log("not good");
                }

    };



    $scope.modifyPackageFunc = function () {

        var packageName = $scope.packageToBeModified;
        var diskSpace = $scope.diskSpace;
        var bandwidth = $scope.bandwidth;
        var ftpAccounts = $scope.ftpAccounts;
        var dataBases = $scope.dataBases;
        var emails = $scope.emails;

        $("#modifyFailure").hide();
        $("#modifySuccess").hide();
        $("#packageLoading").show();
        $("#packageDetailsToBeModified").hide();


        url = "/packages/saveChanges";

                var data = {
                    packageName: packageName,
                    diskSpace:diskSpace,
                    bandwidth:bandwidth,
                    ftpAccounts:ftpAccounts,
                    dataBases:dataBases,
                    emails:emails,
                    allowedDomains:$scope.allowedDomains,
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
                        $scope.errorMessage = response.data.error_message;
                        $("#modifyFailure").fadeIn();
                        $("#modifySuccess").hide();
                        $("#modifyButton").hide();
                        $("#packageLoading").hide();


                    }
                    else{
                        $("#modifyButton").hide();

                        $("#successfullyModified").fadeIn();
                        $("#modifyFailure").hide();
                        $("#packageLoading").hide();
                        $scope.packageModified = packageName;




                    }


                }
                function cantLoadInitialDatas(response) {
                    console.log("not good");
                }



    };

});
/* Java script code to Modify Pacakge ends here */

/**** VMM */



/* Java script code to create Pacakge */

app.controller('createPackageVMM', function($scope,$http) {

    $scope.tronLoading = true;
    $scope.poolCreationFailed = true;
    $scope.poolCreated = true;
    $scope.couldNotConnect = true;


    $scope.insertPackInDB = function(){

        $scope.tronLoading = false;
        $scope.poolCreationFailed = true;
        $scope.poolCreated = true;
        $scope.couldNotConnect = true;



        var url = "/packages/submitPackageVMM";

        var data = {
                    packageName: $scope.packageName,
                    diskSpace: $scope.diskSpace,
                    guaranteedRam: $scope.guaranteedRam,
                    bandwidth: $scope.bandwidth,
                    cpuCores: $scope.cpuCores,
                };

        var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

                    if(response.data.success === 1){

                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = true;
                        $scope.poolCreated = false;
                        $scope.couldNotConnect = true;

                        $scope.successMessage = response.data.successMessage;
                    }
                    else
                    {
                        $scope.tronLoading = true;
                        $scope.poolCreationFailed = false;
                        $scope.poolCreated = true;
                        $scope.couldNotConnect = true;
                        $scope.errorMessage = response.data.error_message;

                    }
                }
        function cantLoadInitialDatas(response) {
                    $scope.tronLoading = true;
                    $scope.poolCreationFailed = true;
                    $scope.poolCreated = true;
                    $scope.couldNotConnect = false;

                }

    };

});

/* Java script code to to create Pacakge ends here */



/* Java script code to delete Pacakge */


$("#deleteFailure").hide();
$("#deleteSuccess").hide();

$("#deletePackageButton").hide();


app.controller('deletePackageVMM', function($scope,$http) {


    $scope.deletePackage = function(){

        $("#deletePackageButton").fadeIn();


    };

    $scope.deletePackageFinal = function(){


                var packageName = $scope.packageToBeDeleted;



                url = "/packages/submitDeleteVMM";

                var data = {
                    packageName: packageName
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if (response.data.deleteStatus === 0)
                    {
                        $scope.errorMessage = response.data.error_message;
                        $("#deleteFailure").fadeIn();
                        $("#deleteSuccess").hide();
                        $("#deletePackageButton").hide();

                    }
                    else{
                        $("#deleteFailure").hide();
                        $("#deleteSuccess").fadeIn();
                        $("#deletePackageButton").hide();
                        $scope.deletedPackage = packageName;

                    }


                }
                function cantLoadInitialDatas(response) {
                    console.log("not good");
                }


    };

});



/* Java script code to delete package ends here */

$("#packageDetailsToBeModified").hide();
$("#modifyFailure").hide();
$("#modifySuccess").hide();
$("#modifyButton").hide();
$("#packageLoading").hide();
$("#successfullyModified").hide();

app.controller('modifyPackagesVMM', function($scope,$http) {

    $scope.fetchDetails = function(){

        $("#packageLoading").show();
        $("#successfullyModified").hide();

        var packageName = $scope.packageToBeModified;
        console.log(packageName);


        url = "/packages/submitModifyVMM";

                var data = {
                    packageName: packageName
                };

                var config = {
                    headers : {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {

                    if (response.data.modifyStatus === 0)
                    {
                        $scope.errorMessage = response.data.error_message;
                        $("#modifyFailure").fadeIn();
                        $("#modifySuccess").hide();
                        $("#modifyButton").hide();
                        $("#packageLoading").hide();


                    }
                    else{
                        $("#modifyButton").show();
                        $scope.packageName = response.data.packageName;
                        $scope.diskSpace = response.data.diskSpace;
                        $scope.guaranteedRam = response.data.guaranteedRam;
                        $scope.bandwidth = response.data.bandwidth;
                        $scope.cpuCores = response.data.cpuCores;

                        $scope.modifyButton = "Save Details";

                        $("#packageDetailsToBeModified").fadeIn();

                        $("#modifyFailure").hide();
                        $("#modifySuccess").fadeIn();
                        $("#packageLoading").hide();
                    }


                }
                function cantLoadInitialDatas(response) {
                    console.log("not good");
                }

    };



    $scope.modifyPackageFunc = function () {


        $("#modifyFailure").hide();
        $("#modifySuccess").hide();
        $("#packageLoading").show();
        $("#packageDetailsToBeModified").hide();


        url = "/packages/saveChangesVMM";

                var data = {
                    packageName: $scope.packageToBeModified,
                    diskSpace:$scope.diskSpace,
                    bandwidth:$scope.bandwidth,
                    guaranteedRam:$scope.guaranteedRam,
                    cpuCores:$scope.cpuCores
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
                        $scope.errorMessage = response.data.error_message;
                        $("#modifyFailure").fadeIn();
                        $("#modifySuccess").hide();
                        $("#modifyButton").hide();
                        $("#packageLoading").hide();


                    }
                    else{
                        $("#modifyButton").hide();

                        $("#successfullyModified").fadeIn();
                        $("#modifyFailure").hide();
                        $("#packageLoading").hide();
                        $scope.packageModified = packageName;




                    }


                }
                function cantLoadInitialDatas(response) {
                    console.log("not good");
                }



    };

});
