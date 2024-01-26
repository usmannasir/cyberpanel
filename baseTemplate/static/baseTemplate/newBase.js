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
let icon40 = document.getElementById("icon40");
let icon41 = document.getElementById("icon41");
let icon42 = document.getElementById("icon42");
let icon43 = document.getElementById("icon43");
let icon44 = document.getElementById("icon44");
let icon45 = document.getElementById("icon45");
let icon46 = document.getElementById("icon46");
let icon47 = document.getElementById("icon47");
let icon48 = document.getElementById("icon48");
let icon49 = document.getElementById("icon49");
let icon450 = document.getElementById("icon450");
let icon451 = document.getElementById("icon451");
let icon452 = document.getElementById("icon452");
let icon453 = document.getElementById("icon453");
let icon454 = document.getElementById("icon454");
let icon455 = document.getElementById("icon455");
let icon456 = document.getElementById("icon456");
let icon457 = document.getElementById("icon457");
let icon458 = document.getElementById("icon458");
let icon459 = document.getElementById("icon459");
let icon460 = document.getElementById("icon460");
let icon461 = document.getElementById("icon461");
let icon462 = document.getElementById("icon462");
let icon463 = document.getElementById("icon463");
let icon464 = document.getElementById("icon464");
let icon465 = document.getElementById("icon465");
const rotate1 = (flag) => {
    if (flag) {
        icon40.classList.toggle("rotate-90");
    }
};
const rotate2 = (flag) => {
    if (flag) {
        icon41.classList.toggle("rotate-90");
    }
};
const rotate3 = (flag) => {
    if (flag) {
        icon42.classList.toggle("rotate-90");
    }
};
const rotate4 = (flag) => {
    if (flag) {
        icon43.classList.toggle("rotate-90");
    }
};
const rotate5 = (flag) => {
    if (flag) {
        icon44.classList.toggle("rotate-90");
    }
};
const rotate6 = (flag) => {
    if (flag) {
        icon45.classList.toggle("rotate-90");
    }
};
const rotate7 = (flag) => {
    if (flag) {
        icon46.classList.toggle("rotate-90");
    }
};
const rotate8 = (flag) => {
    if (flag) {
        icon47.classList.toggle("rotate-90");
    }
};
const rotate9 = (flag) => {
    if (flag) {
        icon48.classList.toggle("rotate-90");
    }
};
const rotate10 = (flag) => {
    if (flag) {
        icon49.classList.toggle("rotate-90");
    }
};
const rotate11 = (flag) => {
    if (flag) {
        icon450.classList.toggle("rotate-90");
    }
};
const rotate12 = (flag) => {
    if (flag) {
        icon451.classList.toggle("rotate-90");
    }
};
const rotate13 = (flag) => {
    if (flag) {
        icon452.classList.toggle("rotate-90");
    }
};
const rotate14 = (flag) => {
    if (flag) {
        icon453.classList.toggle("rotate-90");
    }
};
const rotate15 = (flag) => {
    if (flag) {
        icon454.classList.toggle("rotate-90");
    }
};
const rotate16 = (flag) => {
    if (flag) {
        icon455.classList.toggle("rotate-90");
    }
};
const rotate17 = (flag) => {
    if (flag) {
        icon456.classList.toggle("rotate-90");
    }
};
const rotate18 = (flag) => {
    if (flag) {
        icon457.classList.toggle("rotate-90");
    }
};
const rotate19 = (flag) => {
    if (flag) {
        icon458.classList.toggle("rotate-90");
    }
};
const rotate20 = (flag) => {
    if (flag) {
        icon459.classList.toggle("rotate-90");
    }
};
const rotate21 = (flag) => {
    if (flag) {
        icon460.classList.toggle("rotate-90");
    }
};
const rotate22 = (flag) => {
    if (flag) {
        icon461.classList.toggle("rotate-90");
    }
};
const rotate23 = (flag) => {
    if (flag) {
        icon462.classList.toggle("rotate-90");
    }
};
const rotate24 = (flag) => {
    if (flag) {
        icon463.classList.toggle("rotate-90");
    }
};
const rotate25 = (flag) => {
    if (flag) {
        icon464.classList.toggle("rotate-90");
    }
};
const rotate26 = (flag) => {
    if (flag) {
        icon465.classList.toggle("rotate-90");
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

var newapp = angular.module('cybercpV2', ['angularFileUpload']);

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

