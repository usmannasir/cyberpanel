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


/* Java script code to monitor system status */

var app = angular.module('CyberCP', []);


app.config(['$interpolateProvider', function($interpolateProvider) {
        $interpolateProvider.startSymbol('{$');
        $interpolateProvider.endSymbol('$}');
    }]);


app.filter('getwebsitename', function() {
    return function(domain, uppercase) {

        if(domain !== undefined) {

            domain = domain.replace("-", "");

            var domainName = domain.split(".");

            var finalDomainName = domainName[0];

            if (finalDomainName.length > 5) {
                finalDomainName = finalDomainName.substring(0, 4);
            }

            return finalDomainName;
        }
    };
  });

app.controller('systemStatusInfo', function($scope,$http,$timeout) {

    //getStuff();

    function getStuff() {


        url = "/base/getSystemStatus";

        $http.get(url).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {


            $scope.cpuUsage = response.data.cpuUsage;
            $scope.ramUsage = response.data.ramUsage;
            $scope.diskUsage = response.data.diskUsage;

        }

        function cantLoadInitialData(response) {
            console.log("not good");
        }

        //$timeout(getStuff, 2000);

    }
});



/*  Admin status */




app.controller('adminController', function($scope,$http,$timeout) {

        url = "/base/getAdminStatus";

        $http.get(url).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {


            $scope.currentAdmin = response.data.user_name;
            $scope.admin_type = response.data.admin_type;


            $("#serverIPAddress").text(response.data.serverIPAddress);

             if (response.data.admin_type !== "Administrator")
            {

                if(response.data.admin_type !== "Reseller") {
                    $("#normalUser").hide();
                    $("#normalUserA").hide();
                    $("#normalUserB").hide();
                }

                    $("#normalUserC").hide();
                    $("#normalUserD").hide();
                    $("#normalUserE").hide();
                    $("#normalUserF").hide();
                    $("#normalUserG").hide();
                    $("#normalUserH").hide();
                    $("#normalUserP").hide();
                    $("#normalUserI").hide();

                    $("#ssl").hide();
                    $("#sslA").hide();
                    $("#siteState").hide();

                    $("#restoreSite").hide();
                    $("#backupDestinations").hide();
                    $("#scheduleBackup").hide();

                    $("#remoteBackups").hide();
                    $("#packageHome").hide();
                    $("#packageSub").hide();
                    $("#createWebsite").hide();
                    $("#modifyWebSite").hide();
                    $("#deleteWebsite").hide();
                    $("#versionManagement").hide();

            }
        }

        function cantLoadInitialData(response) {
            console.log("not good");
        }
});



/* Load average */


app.controller('loadAvg', function($scope,$http,$timeout) {

    //getStuff();

    function getStuff() {


        url = "/base/getLoadAverage";

        $http.get(url).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {


            $scope.one = response.data.one;
            $scope.two = response.data.two;
            $scope.three = response.data.three;

        }

        function cantLoadInitialData(response) {
            console.log("not good");
        }

        //$timeout(getStuff, 2000);

    }
});





/// home page system status


app.controller('homePageStatus', function($scope,$http,$timeout) {

    getStuff();

    function getStuff() {


        url = "/base/getSystemStatus";

        $http.get(url).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            console.log(response.data);

            $("#redcircle").removeClass();
            $("#greencircle").removeClass();
            $("#pinkcircle").removeClass();


            $scope.cpuUsage = response.data.cpuUsage;
            $scope.ramUsage = response.data.ramUsage;
            $scope.diskUsage = response.data.diskUsage;

            $scope.RequestProcessing = response.data.RequestProcessing;
            $scope.TotalRequests = response.data.TotalRequests;

            $scope.MAXCONN = response.data.MAXCONN;
            $scope.MAXSSL = response.data.MAXSSL;
            $scope.Avail = response.data.Avail;
            $scope.AvailSSL = response.data.AvailSSL;



            $("#redcircle").addClass("c100");
            $("#redcircle").addClass("p"+$scope.cpuUsage);
            $("#redcircle").addClass("red");

            $("#greencircle").addClass("c100");
            $("#greencircle").addClass("p"+$scope.ramUsage);
            $("#greencircle").addClass("green");


            $("#pinkcircle").addClass("c100");
            $("#pinkcircle").addClass("p"+$scope.diskUsage);
            $("#pinkcircle").addClass("red");


            // home page cpu,ram and disk update.
            var rotationMultiplier = 3.6;
            // For each div that its id ends with "circle", do the following.
            $( "div[id$='circle']" ).each(function() {
                // Save all of its classes in an array.
                var classList = $( this ).attr('class').split(/\s+/);
                // Iterate over the array
                for (var i = 0; i < classList.length; i++) {
                   /* If there's about a percentage class, take the actual percentage and apply the
                        css transformations in all occurences of the specified percentage class,
                        even for the divs without an id ending with "circle" */
                   if (classList[i].match("^p"+$scope.cpuUsage)) {
                    var rotationPercentage = $scope.cpuUsage;
                    var rotationDegrees = rotationMultiplier*rotationPercentage;
                    $('.c100.p'+rotationPercentage+ ' .bar').css({
                      '-webkit-transform' : 'rotate(' + rotationDegrees + 'deg)',
                      '-moz-transform'    : 'rotate(' + rotationDegrees + 'deg)',
                      '-ms-transform'     : 'rotate(' + rotationDegrees + 'deg)',
                      '-o-transform'      : 'rotate(' + rotationDegrees + 'deg)',
                      'transform'         : 'rotate(' + rotationDegrees + 'deg)'
                    });
                   }
                   else if(classList[i].match("^p"+$scope.ramUsage)){
                       var rotationPercentage = response.data.ramUsage;;
                    var rotationDegrees = rotationMultiplier*rotationPercentage;
                    $('.c100.p'+rotationPercentage+ ' .bar').css({
                      '-webkit-transform' : 'rotate(' + rotationDegrees + 'deg)',
                      '-moz-transform'    : 'rotate(' + rotationDegrees + 'deg)',
                      '-ms-transform'     : 'rotate(' + rotationDegrees + 'deg)',
                      '-o-transform'      : 'rotate(' + rotationDegrees + 'deg)',
                      'transform'         : 'rotate(' + rotationDegrees + 'deg)'
                    });
                   }
                   else if(classList[i].match("^p"+$scope.diskUsage)){
                       var rotationPercentage = response.data.diskUsage;;
                    var rotationDegrees = rotationMultiplier*rotationPercentage;
                    $('.c100.p'+rotationPercentage+ ' .bar').css({
                      '-webkit-transform' : 'rotate(' + rotationDegrees + 'deg)',
                      '-moz-transform'    : 'rotate(' + rotationDegrees + 'deg)',
                      '-ms-transform'     : 'rotate(' + rotationDegrees + 'deg)',
                      '-o-transform'      : 'rotate(' + rotationDegrees + 'deg)',
                      'transform'         : 'rotate(' + rotationDegrees + 'deg)'
                    });
                   }
                }
            });









        }

        function cantLoadInitialData(response) {
            console.log("not good");
        }

        $timeout(getStuff, 2000);

    }
});




////////////

function increment(){
  $('.box').hide();
  setTimeout(function(){
    $('.box').show();
  },100);


}

increment();



////////////


app.controller('versionManagment', function($scope,$http,$timeout) {

    $scope.upgradeLoading = true;
    $scope.upgradelogBox = true;

    $scope.updateError = true;
    $scope.updateStarted = true;
    $scope.updateFinish = true;
    $scope.couldNotConnect = true;




    $scope.upgrade = function() {

        $scope.upgradeLoading = false;
        $scope.updateError = true;
        $scope.updateStarted = true;
        $scope.updateFinish = true;
        $scope.couldNotConnect = true;


        url = "/base/upgrade";

        $http.get(url).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {

            if(response.data.upgrade == 1){
                        $scope.upgradeLoading = true;
                        $scope.updateError = true;
                        $scope.updateStarted = false;
                        $scope.updateFinish = true;
                        $scope.couldNotConnect = true;
                        getUpgradeStatus();
                    }
                    else{
                            $scope.updateError = false;
                            $scope.updateStarted = true;
                            $scope.updateFinish = true;
                            $scope.couldNotConnect = true;
                            $scope.errorMessage = response.data.error_message;
                    }
        }

        function cantLoadInitialData(response) {

            $scope.updateError = true;
            $scope.updateStarted = true;
            $scope.updateFinish = true;
            $scope.couldNotConnect = false;

        }


    }


    function getUpgradeStatus(){

                        $scope.upgradeLoading = false;

                        url = "/base/UpgradeStatus";

                        var data = {
                        };

                        var config = {
                            headers : {
                                'X-CSRFToken': getCookie('csrftoken')
                                }
                            };



                $http.post(url, data,config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if(response.data.upgradeStatus === 1){

                        if(response.data.finished===1){
                            $timeout.cancel();
                            $scope.upgradelogBox = false;
                            $scope.upgradeLog = response.data.upgradeLog;
                            $scope.upgradeLoading = true;
                            $scope.updateError = true;
                            $scope.updateStarted = true;
                            $scope.updateFinish = false;
                            $scope.couldNotConnect = true;

                        }
                        else{
                            $scope.upgradelogBox = false;
                            $scope.upgradeLog = response.data.upgradeLog;
                            $timeout(getUpgradeStatus,2000);
                        }
                    }

                }
                function cantLoadInitialDatas(response) {

                    $scope.updateError = true;
                    $scope.updateStarted = true;
                    $scope.updateFinish = true;
                    $scope.couldNotConnect = false;

                }


           };

});