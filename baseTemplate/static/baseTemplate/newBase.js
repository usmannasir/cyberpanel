let icon1 = document.getElementById("icon1");
let menu1 = document.getElementById("menu1");
const showMenu1 = (flag) => {
  if (flag) {
    icon1.classList.toggle("rotate-180");
    menu1.classList.toggle("hidden");
  }
};
let icon2 = document.getElementById("icon2");
let menu2 = document.getElementById("menu2");

const showMenu2 = (flag) => {
  if (flag) {
    icon2.classList.toggle("rotate-180");
    menu2.classList.toggle("hidden");
  }
};
let icon3 = document.getElementById("icon3");
let menu3 = document.getElementById("menu3");

const showMenu3 = (flag) => {
  if (flag) {
    icon3.classList.toggle("rotate-180");
    menu3.classList.toggle("hidden");
  }
};

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

var newapp =angular.module('cybercpV2',[]);

newapp.config(['$interpolateProvider', function ($interpolateProvider) {
    $interpolateProvider.startSymbol('{$');
    $interpolateProvider.endSymbol('$}');
}]);
newapp.controller('dashboardV2', function ($scope, $http, $timeout) {
alert('dashboardV2');
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
            $("#redcircle").addClass("p" + $scope.cpuUsage);
            $("#redcircle").addClass("red");

            $("#greencircle").addClass("c100");
            $("#greencircle").addClass("p" + $scope.ramUsage);
            $("#greencircle").addClass("green");


            $("#pinkcircle").addClass("c100");
            $("#pinkcircle").addClass("p" + $scope.diskUsage);
            $("#pinkcircle").addClass("red");


            // home page cpu,ram and disk update.
            var rotationMultiplier = 3.6;
            // For each div that its id ends with "circle", do the following.
            $("div[id$='circle']").each(function () {
                // Save all of its classes in an array.
                var classList = $(this).attr('class').split(/\s+/);
                // Iterate over the array
                for (var i = 0; i < classList.length; i++) {
                    /* If there's about a percentage class, take the actual percentage and apply the
                         css transformations in all occurences of the specified percentage class,
                         even for the divs without an id ending with "circle" */
                    if (classList[i].match("^p" + $scope.cpuUsage)) {
                        var rotationPercentage = $scope.cpuUsage;
                        var rotationDegrees = rotationMultiplier * rotationPercentage;
                        $('.c100.p' + rotationPercentage + ' .bar').css({
                            '-webkit-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-moz-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-ms-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-o-transform': 'rotate(' + rotationDegrees + 'deg)',
                            'transform': 'rotate(' + rotationDegrees + 'deg)'
                        });
                    } else if (classList[i].match("^p" + $scope.ramUsage)) {
                        var rotationPercentage = response.data.ramUsage;
                        ;
                        var rotationDegrees = rotationMultiplier * rotationPercentage;
                        $('.c100.p' + rotationPercentage + ' .bar').css({
                            '-webkit-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-moz-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-ms-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-o-transform': 'rotate(' + rotationDegrees + 'deg)',
                            'transform': 'rotate(' + rotationDegrees + 'deg)'
                        });
                    } else if (classList[i].match("^p" + $scope.diskUsage)) {
                        var rotationPercentage = response.data.diskUsage;
                        ;
                        var rotationDegrees = rotationMultiplier * rotationPercentage;
                        $('.c100.p' + rotationPercentage + ' .bar').css({
                            '-webkit-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-moz-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-ms-transform': 'rotate(' + rotationDegrees + 'deg)',
                            '-o-transform': 'rotate(' + rotationDegrees + 'deg)',
                            'transform': 'rotate(' + rotationDegrees + 'deg)'
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
    getStuff();
});

