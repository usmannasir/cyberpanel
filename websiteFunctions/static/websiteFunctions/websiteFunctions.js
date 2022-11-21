/**
 * Created by usman on 7/26/17.
 */
function getCookie(name) {
    var cookieValue = null;
    var t = document.cookie;
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


var arry = []

function selectpluginJs(val) {
    $('#mysearch').hide()
    arry.push(val)

    // console.log(arry)
    document.getElementById('selJS').innerHTML = "";

    for (var i = 0; i < arry.length; i++) {
        $('#selJS').show()
        var mlm = '<span style="background-color: #12207a; color: #FFFFFF; padding: 5px;  border-radius: 30px"> ' + arry[i] + ' </span>&nbsp &nbsp'
        $('#selJS').append(mlm)
    }


}


var DeletePluginURL;

function DeletePluginBuucket(url) {
    DeletePluginURL = url;
}

function FinalDeletePluginBuucket() {
    window.location.href = DeletePluginURL;
}

var SPVal;

app.controller('WPAddNewPlugin', function ($scope, $http, $timeout, $window, $compile) {
    $scope.webSiteCreationLoading = true;

    $scope.SearchPluginName = function (val) {
        $scope.webSiteCreationLoading = false;
        SPVal = val;
        url = "/websites/SearchOnkeyupPlugin";

        var searchcontent = $scope.searchcontent;


        var data = {
            pluginname: searchcontent
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.webSiteCreationLoading = true;

            if (response.data.status === 1) {
                if (SPVal == 'add') {
                    $('#mysearch').show()
                    document.getElementById('mysearch').innerHTML = "";
                    var res = response.data.plugns.plugins
                    // console.log(res);
                    for (i = 0; i <= res.length; i++) {
                        //
                        var tml = '<option onclick="selectpluginJs(\'' + res[i].slug + '\')" style="  border-bottom: 1px solid  rgba(90, 91, 92, 0.5); padding: 5px; " value="' + res[i].slug + '">' + res[i].name + '</option> <br>';
                        $('#mysearch').append(tml);
                    }
                } else if (SPVal == 'eidt') {
                    $('#mysearch').show()
                    document.getElementById('mysearch').innerHTML = "";
                    var res = response.data.plugns.plugins
                    // console.log(res);
                    for (i = 0; i <= res.length; i++) {
                        //
                        var tml = '<option  ng-click="Addplugin(\'' + res[i].slug + '\')" style="  border-bottom: 1px solid  rgba(90, 91, 92, 0.5); padding: 5px; " value="' + res[i].slug + '">' + res[i].name + '</option> <br>';
                        var temp = $compile(tml)($scope)
                        angular.element(document.getElementById('mysearch')).append(temp);
                    }

                }


            } else {

                // $scope.errorMessage = response.data.error_message;
                alert("Status not = 1: Error..." + response.data.error_message)
            }


        }

        function cantLoadInitialDatas(response) {

            alert("Error..." + response)

        }
    }

    $scope.AddNewplugin = function () {

        url = "/websites/AddNewpluginAjax";

        var bucketname = $scope.PluginbucketName

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        var data = {
            config: arry,
            Name: bucketname
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Bucket created.',
                    type: 'success'
                });
                location.reload();
            } else {

                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {

            alert("Error..." + response)

        }
    }

    $scope.deletesPlgin = function (val) {

        url = "/websites/deletesPlgin";


        var data = {
            pluginname: val,
            pluginbBucketID: $('#pluginbID').html()
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                location.reload();

            } else {

                // $scope.errorMessage = response.data.error_message;
                alert("Status not = 1: Error..." + response.data.error_message)
            }


        }

        function cantLoadInitialDatas(response) {

            alert("Error..." + response)

        }

    }

    $scope.Addplugin = function (slug) {
        $('#mysearch').hide()

        url = "/websites/Addplugineidt";


        var data = {
            pluginname: slug,
            pluginbBucketID: $('#pluginbID').html()
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                location.reload();

            } else {

                // $scope.errorMessage = response.data.error_message;
                alert("Status not = 1: Error..." + response.data.error_message)
            }


        }

        function cantLoadInitialDatas(response) {

            alert("Error..." + response)

        }


    }

});

var domain_check = 0;

function checkbox_function() {

    var checkBox = document.getElementById("myCheck");
    // Get the output text


    // If the checkbox is checked, display the output text
    if (checkBox.checked == true) {
        domain_check = 0;
        document.getElementById('Test_Domain').style.display = "block";
        document.getElementById('Own_Domain').style.display = "none";

    } else {
        document.getElementById('Test_Domain').style.display = "none";
        document.getElementById('Own_Domain').style.display = "block";
        domain_check = 1;
    }

    // alert(domain_check);
}

app.controller('createWordpress', function ($scope, $http, $timeout, $compile, $window) {
    $scope.webSiteCreationLoading = true;
    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    $scope.goBackDisable = true;


    var statusFile;

    $scope.createWordPresssite = function () {

        $scope.webSiteCreationLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;


        $scope.currentStatus = "Starting creation..";

        var package = $scope.packageForWebsite;
        var websiteOwner = $scope.websiteOwner;
        var WPtitle = $scope.WPtitle;

        if (domain_check == 0) {
            var Part2_domainNameCreate = document.getElementById('Part2_domainNameCreate').value;
            var domainNameCreate = document.getElementById('TestDomainNameCreate').value + Part2_domainNameCreate;
        }
        if (domain_check == 1) {

            var domainNameCreate = $scope.own_domainNameCreate;
        }


        var WPUsername = $scope.WPUsername;
        var adminEmail = $scope.adminEmail;
        var WPPassword = $scope.WPPassword;
        var WPVersions = $scope.WPVersions;
        var pluginbucket = $scope.pluginbucket;
        var autoupdates = $scope.autoupdates;
        var pluginupdates = $scope.pluginupdates;
        var themeupdates = $scope.themeupdates;

        if (domain_check == 0) {

            var path = "";

        }
        if (domain_check = 1) {

            var path = $scope.installPath;

        }


        var home = "1";

        if (typeof path != 'undefined') {
            home = "0";
        }

        //alert(domainNameCreate);
        var data = {

            title: WPtitle,
            domain: domainNameCreate,
            WPVersion: WPVersions,
            pluginbucket: pluginbucket,
            adminUser: WPUsername,
            Email: adminEmail,
            PasswordByPass: WPPassword,
            AutomaticUpdates: autoupdates,
            Plugins: pluginupdates,
            Themes: themeupdates,
            websiteOwner: websiteOwner,
            package: package,
            home: home,
            path: path,
        }

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        var url = "/websites/submitWorpressCreation";

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.webSiteCreationLoading = true;
            if (response.data.status === 1) {
                statusFile = response.data.tempStatusPath;
                getCreationStatus();

            } else {
                $scope.goBackDisable = false;
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {

            alert("Error..." + response)

        }

    };
    $scope.goBack = function () {
        $scope.webSiteCreationLoading = true;
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getCreationStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.webSiteCreationLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = true;
                    $scope.success = false;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;

                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.webSiteCreationLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = false;
                    $scope.success = true;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;

                }

            } else {
                $scope.webSiteCreationLoading = false;
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;
                $timeout(getCreationStatus, 1000);
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.webSiteCreationLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    }


});


//........... delete wp list
var FurlDeleteWP;

function DeleteWPNow(url) {
    FurlDeleteWP = url;
}

function FinalDeleteWPNow() {
    window.location.href = FurlDeleteWP;
}

var DeploytoProductionID;

function DeployToProductionInitial(vall) {
    DeploytoProductionID = vall;
}

var create_staging_domain_check = 0;

function create_staging_checkbox_function() {

    var checkBox = document.getElementById("Create_Staging_Check");
    // Get the output text


    // If the checkbox is checked, display the output text
    if (checkBox.checked == true) {
        create_staging_domain_check = 0;
        document.getElementById('Website_Create_Test_Domain').style.display = "block";
        document.getElementById('Website_Create_Own_Domain').style.display = "none";

    } else {
        document.getElementById('Website_Create_Test_Domain').style.display = "none";
        document.getElementById('Website_Create_Own_Domain').style.display = "block";
        create_staging_domain_check = 1;
    }

    // alert(domain_check);
}

app.controller('WPsiteHome', function ($scope, $http, $timeout, $compile, $window) {

    var CheckBoxpasssword = 0;

    $scope.wordpresshomeloading = true;
    $scope.stagingDetailsForm = false;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    $scope.goBackDisable = true;
    $(document).ready(function () {
        var checkstatus = document.getElementById("wordpresshome");
        if (checkstatus !== null) {
            $scope.LoadWPdata();

        }
    });


    $scope.LoadWPdata = function () {

        $scope.wordpresshomeloading = false;
        $('#wordpresshomeloading').show();

        var url = "/websites/FetchWPdata";

        var data = {
            WPid: $('#WPid').html(),
        }

        console.log(data);
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            wordpresshomeloading = true;
            $('#wordpresshomeloading').hide();

            if (response.data.status === 1) {
                $('#WPVersion').text(response.data.ret_data.version);
                if (response.data.ret_data.lscache === 1) {
                    $('#lscache').prop('checked', true);
                }
                if (response.data.ret_data.debugging === 1) {
                    $('#debugging').prop('checked', true);
                }
                if (response.data.ret_data.searchIndex === 1) {
                    $('#searchIndex').prop('checked', true);
                }
                if (response.data.ret_data.maintenanceMode === 1) {
                    $('#maintenanceMode').prop('checked', true);
                }
                if (response.data.ret_data.wpcron === 1) {
                    $('#wpcron').prop('checked', true);
                }
                if (response.data.ret_data.passwordprotection == 1) {

                    var dc = '<input  type="checkbox" checked \n' +
                        '        ng-click="UpdateWPSettings(\'PasswordProtection\')" class="custom-control-input ng-pristine ng-untouched ng-valid ng-not-empty"\n' +
                        '                                                       id="passwdprotection">\n' +
                        '                                                <label class="custom-control-label"\n' +
                        '                                                       for="passwdprotection"></label>'
                    var mp = $compile(dc)($scope);
                    angular.element(document.getElementById('prsswdprodata')).append(mp);
                    CheckBoxpasssword = 1;
                } else if (response.data.ret_data.passwordprotection == 0) {
                    var dc = '<input  type="checkbox" data-toggle="modal"\n' +
                        '                                                       data-target="#Passwordprotection"\n' +
                        '                                                       class="custom-control-input ng-pristine ng-untouched ng-valid ng-not-empty"\n' +
                        '                                                       id="passwdprotection">\n' +
                        '                                                <label class="custom-control-label"\n' +
                        '                                                       for="passwdprotection"></label>'
                    $('#prsswdprodata').append(dc);
                    CheckBoxpasssword = 0;
                }

            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();

            $scope.webSiteCreationLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    };

    $scope.UpdateWPSettings = function (setting) {

        $scope.wordpresshomeloading = false;
        $('#wordpresshomeloading').show();


        var url = "/websites/UpdateWPSettings";

        if (setting === "PasswordProtection") {
            if (CheckBoxpasssword == 0) {
                var data = {
                    WPid: $('#WPid').html(),
                    setting: setting,
                    PPUsername: $scope.PPUsername,
                    PPPassword: $scope.PPPassword,
                }

            } else {
                var data = {
                    WPid: $('#WPid').html(),
                    setting: setting,
                    PPUsername: '',
                    PPPassword: '',
                }

            }

        } else {
            var settingValue = 0;
            if ($('#' + setting).is(":checked")) {
                settingValue = 1;
            }
            var data = {
                WPid: $('#WPid').html(),
                setting: setting,
                settingValue: settingValue
            }
        }


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.wordpresshomeloading = true;
            $('#wordpresshomeloading').hide();

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Successfully Updated!.',
                    type: 'success'
                });
                if (setting === "PasswordProtection") {
                    location.reload();
                }
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
                if (setting === "PasswordProtection") {
                    location.reload();
                }

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;
            alert(response)

        }


    };

    $scope.GetCurrentPlugins = function () {
        $('#wordpresshomeloading').show();

        $scope.wordpresshomeloading = false;

        var url = "/websites/GetCurrentPlugins";

        var data = {
            WPid: $('#WPid').html(),
        }

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            wordpresshomeloading = true;
            $('#wordpresshomeloading').hide();

            if (response.data.status === 1) {
                $('#PluginBody').html('');
                var plugins = JSON.parse(response.data.plugins);
                plugins.forEach(AddPlugins);

            } else {
                alert("Error:" + response.data.error_message)

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();

            $scope.webSiteCreationLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    };

    $scope.GetCurrentThemes = function () {
        $('#wordpresshomeloading').show();

        $scope.wordpresshomeloading = false;

        var url = "/websites/GetCurrentThemes";

        var data = {
            WPid: $('#WPid').html(),
        }

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            wordpresshomeloading = true;
            $('#wordpresshomeloading').hide();

            if (response.data.status === 1) {

                $('#ThemeBody').html('');
                var themes = JSON.parse(response.data.themes);
                themes.forEach(AddThemes);

            } else {
                alert("Error:" + response.data.error_message)

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.webSiteCreationLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    };

    $scope.UpdatePlugins = function (plugin) {
        $('#wordpresshomeloading').show();
        var data = {
            plugin: plugin,
            pluginarray: PluginsList,
            WPid: $('#WPid').html(),
        }

        $scope.wordpresshomeloading = false;

        var url = "/websites/UpdatePlugins";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Updating Plugins in Background!.',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;
            alert(response)

        }


    };

    $scope.DeletePlugins = function (plugin) {
        $('#wordpresshomeloading').show();
        var data = {
            plugin: plugin,
            pluginarray: PluginsList,
            WPid: $('#WPid').html(),
        }

        $scope.wordpresshomeloading = false;

        var url = "/websites/DeletePlugins";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Deleting Plugin in Background!',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;
            alert(response)

        }

    }

    $scope.ChangeStatus = function (plugin) {
        $('#wordpresshomeloading').show();
        var data = {
            plugin: plugin,
            WPid: $('#WPid').html(),
        }

        $scope.wordpresshomeloading = false;

        var url = "/websites/ChangeStatus";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Changed Plugin state Successfully !.',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;
            alert(response)

        }

    }

    function AddPlugins(value, index, array) {
        var FinalMarkup = '<tr>'
        FinalMarkup = FinalMarkup + '<td><input onclick="AddPluginToArray(this,\'' + value.name + '\')" type="checkbox" id="' + value.name + '"><label for="' + value.name + '"></label></td>';
        for (let x in value) {
            if (x === 'status') {
                if (value[x] === 'inactive') {
                    FinalMarkup = FinalMarkup + '<td><div ng-click="ChangeStatus(\'' + value.name + '\')" class="form-check form-check-inline switch"><input type="checkbox" id="' + value.name + 'State"><label for="' + value.name + 'State"></label></div></td>';
                } else {
                    FinalMarkup = FinalMarkup + '<td><div ng-click="ChangeStatus(\'' + value.name + '\')" class="form-check form-check-inline switch"><input type="checkbox" id="' + value.name + 'State" checked=""><label for="' + value.name + 'State"></label></div></td>';
                }
            } else if (x === 'update') {
                if (value[x] === 'none') {
                    FinalMarkup = FinalMarkup + '<td><span class="label label-success">Upto Date</span></td>';
                } else {
                    FinalMarkup = FinalMarkup + '<td><button ng-click="UpdatePlugins(\'' + value.name + '\')" aria-label="" type="button" class="btn btn-outline-danger">Update</button></td>';
                }
            } else {
                FinalMarkup = FinalMarkup + '<td>' + value[x] + "</td>";
            }
        }
        FinalMarkup = FinalMarkup + '<td><button ng-click="DeletePlugins(\'' + value.name + '\')" aria-label="" class="btn btn-danger btn-icon-left m-b-10" type="button">Delete</button></td>'
        FinalMarkup = FinalMarkup + '</tr>'
        var temp = $compile(FinalMarkup)($scope)
        AppendToTable('#PluginBody', temp)
    }

    $scope.UpdateThemes = function (theme) {
        $('#wordpresshomeloading').show();
        var data = {
            Theme: theme,
            Themearray: ThemesList,
            WPid: $('#WPid').html(),
        }

        $scope.wordpresshomeloading = false;

        var url = "/websites/UpdateThemes";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Updating Theme in background !.',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;
            alert(response)

        }


    };

    $scope.DeleteThemes = function (theme) {
        $('#wordpresshomeloading').show();
        var data = {
            Theme: theme,
            Themearray: ThemesList,
            WPid: $('#WPid').html(),
        }

        $scope.wordpresshomeloading = false;

        var url = "/websites/DeleteThemes";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Deleting Theme in Background!.',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;
            alert(response)

        }
    };

    $scope.ChangeStatusThemes = function (theme) {
        $('#wordpresshomeloading').show();
        var data = {
            theme: theme,
            WPid: $('#WPid').html(),
        }

        $scope.wordpresshomeloading = false;

        var url = "/websites/StatusThemes";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Change Theme state in Bsckground!.',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;
            alert(response)

        }

    };

    function AddThemes(value, index, array) {
        var FinalMarkup = '<tr>'
        FinalMarkup = FinalMarkup + '<td><input onclick="AddThemeToArray(this,\'' + value.name + '\')" type="checkbox" id="' + value.name + '"><label for="' + value.name + '"></label></td>';
        for (let x in value) {
            if (x === 'status') {
                if (value[x] === 'inactive') {
                    FinalMarkup = FinalMarkup + '<td><div ng-click="ChangeStatusThemes(\'' + value.name + '\')" class="form-check form-check-inline switch"><input type="checkbox" id="' + value.name + 'State"><label for="' + value.name + 'State"></label></div></td>';
                } else {
                    FinalMarkup = FinalMarkup + '<td><div ng-click="ChangeStatusThemes(\'' + value.name + '\')" class="form-check form-check-inline switch"><input type="checkbox" id="' + value.name + 'State" checked=""><label for="' + value.name + 'State"></label></div></td>';
                }
            } else if (x === 'update') {
                if (value[x] === 'none') {
                    FinalMarkup = FinalMarkup + '<td><span class="label label-success">Upto Date</span></td>';
                } else {
                    FinalMarkup = FinalMarkup + '<td><button ng-click="UpdateThemes(\'' + value.name + '\')" aria-label="" type="button" class="btn btn-outline-danger">Update</button></td>';
                }
            } else {
                FinalMarkup = FinalMarkup + '<td>' + value[x] + "</td>";
            }
        }
        FinalMarkup = FinalMarkup + '<td><button ng-click="DeleteThemes(\'' + value.name + '\')" aria-label="" class="btn btn-danger btn-icon-left m-b-10" type="button">Delete</button></td>'
        FinalMarkup = FinalMarkup + '</tr>'
        var temp = $compile(FinalMarkup)($scope)
        AppendToTable('#ThemeBody', temp)
    }

    $scope.CreateStagingNow = function () {
        $('#wordpresshomeloading').show();

        $scope.wordpresshomeloading = false;
        $scope.stagingDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;


        $scope.currentStatus = "Starting creation Staging..";

        //here enter domain name
        if (create_staging_domain_check == 0) {
            var Part2_domainNameCreate = document.getElementById('Part2_domainNameCreate').value;
            var domainNameCreate = document.getElementById('TestDomainNameCreate').value + Part2_domainNameCreate;
        }
        if (create_staging_domain_check == 1) {

            var domainNameCreate = $scope.own_domainNameCreate;
        }
        var data = {
            StagingName: $('#stagingName').val(),
            StagingDomain: domainNameCreate,
            WPid: $('#WPid').html(),
        }
        var url = "/websites/CreateStagingNow";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            if (response.data.status === 1) {
                statusFile = response.data.tempStatusPath;
                getCreationStatus();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;
            alert(response)

        }
    };

    function getCreationStatus() {
        $('#wordpresshomeloading').show();

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            //$('#wordpresshomeloading').hide();

            if (response.data.abort === 1) {
                if (response.data.installStatus === 1) {

                    $scope.wordpresshomeloading = true;
                    $scope.stagingDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = true;
                    $scope.success = false;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;


                    $("#installProgress").css("width", "100%");
                    $("#installProgressbackup").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();


                } else {

                    $scope.wordpresshomeloading = true;
                    $scope.stagingDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = false;
                    $scope.success = true;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $("#installProgressbackup").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;


                }

            } else {

                $("#installProgress").css("width", response.data.installationProgress + "%");
                $("#installProgressbackup").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;
                $timeout(getCreationStatus, 1000);

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;
            $scope.stagingDetailsForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    }

    $scope.goBack = function () {
        $('#wordpresshomeloading').hide();
        $scope.wordpresshomeloading = true;
        $scope.stagingDetailsForm = false;
        $scope.installationProgress = true;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    $scope.fetchstaging = function () {

        $('#wordpresshomeloading').show();
        $scope.wordpresshomeloading = false;

        var url = "/websites/fetchstaging";

        var data = {
            WPid: $('#WPid').html(),
        }

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            wordpresshomeloading = true;
            $('#wordpresshomeloading').hide();

            if (response.data.status === 1) {

                //   $('#ThemeBody').html('');
                // var themes = JSON.parse(response.data.themes);
                // themes.forEach(AddThemes);

                $('#StagingBody').html('');
                var staging = JSON.parse(response.data.wpsites);
                staging.forEach(AddStagings);

            } else {
                alert("Error data.error_message:" + response.data.error_message)

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            alert("Error" + response)

        }

    };

    $scope.fetchDatabase = function () {

        $('#wordpresshomeloading').show();
        $scope.wordpresshomeloading = false;

        var url = "/websites/fetchDatabase";

        var data = {
            WPid: $('#WPid').html(),
        }

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            wordpresshomeloading = true;
            $('#wordpresshomeloading').hide();

            if (response.data.status === 1) {
                $('#DB_Name').html(response.data.DataBaseName);
                $('#DB_User').html(response.data.DataBaseUser);
                $('#tableprefix').html(response.data.tableprefix);
            } else {
                alert("Error data.error_message:" + response.data.error_message)

            }
        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            alert("Error" + response)

        }

    };

    $scope.SaveUpdateConfig = function () {
        $('#wordpresshomeloading').show();
        var data = {
            AutomaticUpdates: $('#AutomaticUpdates').find(":selected").text(),
            Plugins: $('#Plugins').find(":selected").text(),
            Themes: $('#Themes').find(":selected").text(),
            WPid: $('#WPid').html(),
        }

        $scope.wordpresshomeloading = false;

        var url = "/websites/SaveUpdateConfig";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Update Configurations Sucessfully!.',
                    type: 'success'
                });
                $("#autoUpdateConfig").modal('hide');
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            new PNotify({
                title: 'Operation Failed!',
                text: response,
                type: 'error'
            });

        }
    };

    function AddStagings(value, index, array) {
        var FinalMarkup = '<tr>'
        for (let x in value) {
            if (x === 'name') {
                FinalMarkup = FinalMarkup + '<td><a href=/websites/WPHome?ID=' + value.id + '>' + value[x] + '</a></td>';
            } else if (x !== 'url' && x !== 'deleteURL' && x !== 'id') {
                FinalMarkup = FinalMarkup + '<td>' + value[x] + "</td>";
            }
        }
        FinalMarkup = FinalMarkup + '<td><button onclick="DeployToProductionInitial(' + value.id + ')" data-toggle="modal" data-target="#DeployToProduction" style="margin-bottom: 2%; display: block" aria-label="" type="button" class="btn btn-outline-primary">Deploy to Production</button>' +
            '<a href="' + value.deleteURL + '"> <button aria-label="" class="btn btn-danger btn-icon-left m-b-10" type="button">Delete</button></a></td>'
        FinalMarkup = FinalMarkup + '</tr>'
        AppendToTable('#StagingBody', FinalMarkup);
    }

    $scope.FinalDeployToProduction = function () {

        $('#wordpresshomeloading').show();

        $scope.wordpresshomeloading = false;
        $scope.stagingDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;

        var data = {
            WPid: $('#WPid').html(),
            StagingID: DeploytoProductionID
        }

        var url = "/websites/DeploytoProduction";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            $('#wordpresshomeloading').hide();
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Deploy To Production start!.',
                    type: 'success'
                });
                statusFile = response.data.tempStatusPath;
                getCreationStatus();

            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            new PNotify({
                title: 'Operation Failed!',
                text: response,
                type: 'error'
            });

        }

    };


    $scope.CreateBackup = function () {
        $('#wordpresshomeloading').show();

        $scope.wordpresshomeloading = false;
        $scope.stagingDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting creation Backups..";
        var data = {
            WPid: $('#WPid').html(),
            Backuptype: $('#backuptype').val()
        }
        var url = "/websites/WPCreateBackup";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $('createbackupbutton').hide();
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Creating Backups!.',
                    type: 'success'
                });
                statusFile = response.data.tempStatusPath;
                getCreationStatus();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            alert(response)

        }

    };


    $scope.installwpcore = function () {

        $('#wordpresshomeloading').show();
        $('#wordpresshomeloadingsec').show();
        var data = {
            WPid: $('#WPid').html(),
        }

        $scope.wordpresshomeloading = false;

        var url = "/websites/installwpcore";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $('#wordpresshomeloadingsec').hide();
            $scope.wordpresshomeloading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Results fetched..',
                    type: 'success'
                });
                $('#SecurityResult').html(response.data.result);
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $('#wordpresshomeloadingsec').hide();
            $scope.wordpresshomeloading = true;
            alert(response)

        }

    };

    $scope.dataintegrity = function () {

        $('#wordpresshomeloading').show();
        $('#wordpresshomeloadingsec').show();
        var data = {
            WPid: $('#WPid').html(),
        }

        $scope.wordpresshomeloading = false;

        var url = "/websites/dataintegrity";

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $('#wordpresshomeloadingsec').hide();
            $scope.wordpresshomeloading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Results fetched',
                    type: 'success'
                });
                $('#SecurityResult').html(response.data.result);
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $('#wordpresshomeloadingsec').hide();
            $scope.wordpresshomeloading = true;
            alert(response)

        }
    };

});


var PluginsList = [];


function AddPluginToArray(cBox, name) {
    if (cBox.checked) {
        PluginsList.push(name);
        alert(PluginsList);
    } else {
        const index = PluginsList.indexOf(name);
        if (index > -1) {
            PluginsList.splice(index, 1);
        }
        alert(PluginsList);
    }
}

var ThemesList = [];

function AddThemeToArray(cBox, name) {
    if (cBox.checked) {
        ThemesList.push(name);
        alert(ThemesList);
    } else {
        const index = ThemesList.indexOf(name);
        if (index > -1) {
            ThemesList.splice(index, 1);
        }
        alert(ThemesList);
    }
}


function AppendToTable(table, markup) {
    $(table).append(markup);
}


//..................Restore Backup Home


app.controller('RestoreWPBackup', function ($scope, $http, $timeout, $window) {
    $scope.wordpresshomeloading = true;
    $scope.stagingDetailsForm = false;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    $scope.goBackDisable = true;


    $scope.checkmethode = function () {
        var val = $('#RestoreMethode').children("option:selected").val();
        if (val == 1) {
            $('#Newsitediv').show();
            $('#exinstingsitediv').hide();
        } else if (val == 0) {
            $('#exinstingsitediv').show();
            $('#Newsitediv').hide();
        } else {

        }
    };


    $scope.RestoreWPbackupNow = function () {
        $('#wordpresshomeloading').show();
        $scope.wordpresshomeloading = false;
        $scope.stagingDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Start Restoring WordPress..";

        var Domain = $('#wprestoresubdirdomain').val()
        var path = $('#wprestoresubdirpath').val();
        var home = "1";

        if (typeof path != 'undefined' || path != '') {
            home = "0";
        }
        if (typeof path == 'undefined') {
            path = "";
        }


        var backuptype = $('#backuptype').html();
        var data;
        if (backuptype == "DataBase Backup") {
            data = {
                backupid: $('#backupid').html(),
                DesSite: $('#DesSite').children("option:selected").val(),
                Domain: '',
                path: path,
                home: home,
            }
        } else {
            data = {
                backupid: $('#backupid').html(),
                DesSite: $('#DesSite').children("option:selected").val(),
                Domain: Domain,
                path: path,
                home: home,
            }

        }

        var url = "/websites/RestoreWPbackupNow";


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        // console.log(data)

        var d = $('#DesSite').children("option:selected").val();
        var c = $("input[name=Newdomain]").val();
        // if (d == -1 || c == "") {
        //     alert("Please Select Method of Backup Restore");
        // } else {
        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        // }


        function ListInitialDatas(response) {
            wordpresshomeloading = true;
            $('#wordpresshomeloading').hide();

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Restoring process starts!.',
                    type: 'success'
                });
                statusFile = response.data.tempStatusPath;
                getCreationStatus();

            } else {
                $('#wordpresshomeloading').hide();
                $scope.wordpresshomeloading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.errorMessageBox = false;
                $scope.success = true;
                $scope.couldNotConnect = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();

            new PNotify({
                title: 'Operation Failed!',
                text: response.data.error_message,
                type: 'error'
            });


        }
    }

    function getCreationStatus() {
        $('#wordpresshomeloading').show();

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $('#wordpresshomeloading').hide();

            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {


                    $scope.wordpresshomeloading = true;
                    $scope.stagingDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = true;
                    $scope.success = false;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;


                    $("#installProgress").css("width", "100%");
                    $("#installProgressbackup").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();


                } else {

                    $scope.wordpresshomeloading = true;
                    $scope.stagingDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = false;
                    $scope.success = true;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $("#installProgressbackup").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;


                }

            } else {

                $("#installProgress").css("width", response.data.installationProgress + "%");
                $("#installProgressbackup").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;
                $timeout(getCreationStatus, 1000);

            }

        }

        function cantLoadInitialDatas(response) {
            $('#wordpresshomeloading').hide();
            $scope.wordpresshomeloading = true;
            $scope.stagingDetailsForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    }

    $scope.goBack = function () {
        $('#wordpresshomeloading').hide();
        $scope.wordpresshomeloading = true;
        $scope.stagingDetailsForm = false;
        $scope.installationProgress = true;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };
});


//.......................................Remote Backup

//........... delete DeleteBackupConfigNow

function DeleteBackupConfigNow(url) {
    window.location.href = url;
}

function DeleteRemoteBackupsiteNow(url) {
    window.location.href = url;
}

function DeleteBackupfileConfigNow(url) {
    window.location.href = url;
}


app.controller('RemoteBackupConfig', function ($scope, $http, $timeout, $window) {
    $scope.RemoteBackupLoading = true;
    $scope.SFTPBackUpdiv = true;

    $scope.EndpointURLdiv = true;
    $scope.Selectprovider = true;
    $scope.S3keyNamediv = true;
    $scope.Accesskeydiv = true;
    $scope.SecretKeydiv = true;
    $scope.SelectRemoteBackuptype = function () {
        var val = $scope.RemoteBackuptype;
        if (val == "SFTP") {
            $scope.SFTPBackUpdiv = false;
            $scope.EndpointURLdiv = true;
            $scope.Selectprovider = true;
            $scope.S3keyNamediv = true;
            $scope.Accesskeydiv = true;
            $scope.SecretKeydiv = true;
        } else if (val == "S3") {
            $scope.EndpointURLdiv = true;
            $scope.Selectprovider = false;
            $scope.S3keyNamediv = false;
            $scope.Accesskeydiv = false;
            $scope.SecretKeydiv = false;
            $scope.SFTPBackUpdiv = true;
        } else {
            $scope.RemoteBackupLoading = true;
            $scope.SFTPBackUpdiv = true;

            $scope.EndpointURLdiv = true;
            $scope.Selectprovider = true;
            $scope.S3keyNamediv = true;
            $scope.Accesskeydiv = true;
            $scope.SecretKeydiv = true;
        }
    }

    $scope.SelectProvidertype = function () {
        $scope.EndpointURLdiv = true;
        var provider = $scope.Providervalue
        if (provider == 'Backblaze') {
            $scope.EndpointURLdiv = false;
        } else {
            $scope.EndpointURLdiv = true;
        }
    }

    $scope.SaveBackupConfig = function () {
        $scope.RemoteBackupLoading = false;
        var Hname = $scope.Hostname;
        var Uname = $scope.Username;
        var Passwd = $scope.Password;
        var path = $scope.path;
        var type = $scope.RemoteBackuptype;
        var Providervalue = $scope.Providervalue;
        var data;
        if (type == "SFTP") {

            data = {
                Hname: Hname,
                Uname: Uname,
                Passwd: Passwd,
                path: path,
                type: type
            }
        } else if (type == "S3") {
            if (Providervalue == "Backblaze") {
                data = {
                    S3keyname: $scope.S3keyName,
                    Provider: Providervalue,
                    AccessKey: $scope.Accesskey,
                    SecertKey: $scope.SecretKey,
                    EndUrl: $scope.EndpointURL,
                    type: type
                }
            } else {
                data = {
                    S3keyname: $scope.S3keyName,
                    Provider: Providervalue,
                    AccessKey: $scope.Accesskey,
                    SecertKey: $scope.SecretKey,
                    type: type
                }

            }

        }
        var url = "/websites/SaveBackupConfig";


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.RemoteBackupLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Successfully Saved!.',
                    type: 'success'
                });
                location.reload();


            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.RemoteBackupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: response.data.error_message,
                type: 'error'
            });


        }


    }

});

var UpdatescheduleID;
app.controller('BackupSchedule', function ($scope, $http, $timeout, $window) {
    $scope.BackupScheduleLoading = true;
    $scope.SaveBackupSchedule = function () {
        $scope.RemoteBackupLoading = false;
        var FileRetention = $scope.Fretention;
        var Backfrequency = $scope.Bfrequency;


        var data = {
            FileRetention: FileRetention,
            Backfrequency: Backfrequency,
            ScheduleName: $scope.ScheduleName,
            RemoteConfigID: $('#RemoteConfigID').html(),
            BackupType: $scope.BackupType
        }
        var url = "/websites/SaveBackupSchedule";


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.RemoteBackupLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Successfully Saved!.',
                    type: 'success'
                });
                location.reload();


            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.RemoteBackupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: response.data.error_message,
                type: 'error'
            });


        }


    };


    $scope.getupdateid = function (ID) {
        UpdatescheduleID = ID;
    }

    $scope.UpdateRemoteschedules = function () {
        $scope.RemoteBackupLoading = false;
        var Frequency = $scope.RemoteFrequency;
        var fretention = $scope.RemoteFileretention;

        var data = {
            ScheduleID: UpdatescheduleID,
            Frequency: Frequency,
            FileRetention: fretention
        }
        var url = "/websites/UpdateRemoteschedules";


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.RemoteBackupLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Successfully Updated!.',
                    type: 'success'
                });
                location.reload();


            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.RemoteBackupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: response.data.error_message,
                type: 'error'
            });


        }
    };

    $scope.AddWPsiteforRemoteBackup = function () {
        $scope.RemoteBackupLoading = false;


        var data = {
            WpsiteID: $('#Wpsite').val(),
            RemoteScheduleID: $('#RemoteScheduleID').html()
        }
        var url = "/websites/AddWPsiteforRemoteBackup";


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };
        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.RemoteBackupLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Successfully Saved!.',
                    type: 'success'
                });
                location.reload();


            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.RemoteBackupLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: response.data.error_message,
                type: 'error'
            });


        }


    };
});
/* Java script code to create account */

var website_create_domain_check = 0;

function website_create_checkbox_function() {

    var checkBox = document.getElementById("myCheck");
    // Get the output text


    // If the checkbox is checked, display the output text
    if (checkBox.checked == true) {
        website_create_domain_check = 0;
        document.getElementById('Website_Create_Test_Domain').style.display = "block";
        document.getElementById('Website_Create_Own_Domain').style.display = "none";

    } else {
        document.getElementById('Website_Create_Test_Domain').style.display = "none";
        document.getElementById('Website_Create_Own_Domain').style.display = "block";
        website_create_domain_check = 1;
    }

    // alert(domain_check);
}

app.controller('createWebsite', function ($scope, $http, $timeout, $window) {

    $scope.webSiteCreationLoading = true;
    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    $scope.goBackDisable = true;

    var statusFile;

    $scope.createWebsite = function () {

        $scope.webSiteCreationLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;

        $scope.currentStatus = "Starting creation..";

        var ssl, dkimCheck, openBasedir, mailDomain;

        if ($scope.sslCheck === true) {
            ssl = 1;
        } else {
            ssl = 0
        }

        if ($scope.dkimCheck === true) {
            dkimCheck = 1;
        } else {
            dkimCheck = 0
        }

        if ($scope.openBasedir === true) {
            openBasedir = 1;
        } else {
            openBasedir = 0
        }

        if ($scope.mailDomain === true) {
            mailDomain = 1;
        } else {
            mailDomain = 0
        }


        url = "/websites/submitWebsiteCreation";

        var package = $scope.packageForWebsite;

        if (website_create_domain_check == 0) {
            var Part2_domainNameCreate = document.getElementById('Part2_domainNameCreate').value;
            var domainName = document.getElementById('TestDomainNameCreate').value + Part2_domainNameCreate;
        }
        if (website_create_domain_check == 1) {

            var domainName = $scope.own_domainNameCreate;
        }

        // var domainName = $scope.domainNameCreate;

        var adminEmail = $scope.adminEmail;
        var phpSelection = $scope.phpSelection;
        var websiteOwner = $scope.websiteOwner;


        var data = {
            package: package,
            domainName: domainName,
            adminEmail: adminEmail,
            phpSelection: phpSelection,
            ssl: ssl,
            websiteOwner: websiteOwner,
            dkimCheck: dkimCheck,
            openBasedir: openBasedir,
            mailDomain: mailDomain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.createWebSiteStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getCreationStatus();
            } else {

                $scope.webSiteCreationLoading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.errorMessageBox = false;
                $scope.success = true;
                $scope.couldNotConnect = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.webSiteCreationLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    };
    $scope.goBack = function () {
        $scope.webSiteCreationLoading = true;
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getCreationStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.webSiteCreationLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = true;
                    $scope.success = false;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;

                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.webSiteCreationLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = false;
                    $scope.success = true;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;
                $timeout(getCreationStatus, 1000);
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.webSiteCreationLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    }

});
/* Java script code to create account ends here */

/* Java script code to list accounts */

$("#listFail").hide();


app.controller('listWebsites', function ($scope, $http) {


    $scope.currentPage = 1;
    $scope.recordsToShow = 10;

    $scope.getFurtherWebsitesFromDB = function () {

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            page: $scope.currentPage,
            recordsToShow: $scope.recordsToShow
        };


        dataurl = "/websites/fetchWebsitesList";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            if (response.data.listWebSiteStatus === 1) {

                $scope.WebSitesList = JSON.parse(response.data.data);
                $scope.pagination = response.data.pagination;
                $scope.clients = JSON.parse(response.data.data);
                $("#listFail").hide();
            } else {
                $("#listFail").fadeIn();
                $scope.errorMessage = response.data.error_message;

            }
        }

        function cantLoadInitialData(response) {
        }


    };
    $scope.getFurtherWebsitesFromDB();

    $scope.cyberPanelLoading = true;

    $scope.issueSSL = function (virtualHost) {
        $scope.cyberPanelLoading = false;

        var url = "/manageSSL/issueSSL";


        var data = {
            virtualHost: virtualHost
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.SSL === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'SSL successfully issued.',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    $scope.cyberPanelLoading = true;

    $scope.searchWebsites = function () {

        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            patternAdded: $scope.patternAdded
        };

        dataurl = "/websites/searchWebsites";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.listWebSiteStatus === 1) {

                var finalData = JSON.parse(response.data.data);
                $scope.WebSitesList = finalData;
                $("#listFail").hide();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }
        }

        function cantLoadInitialData(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Connect disrupted, refresh the page.',
                type: 'error'
            });
        }


    };

    $scope.ScanWordpressSite = function () {

        $('#cyberPanelLoading').show();


        var url = "/websites/ScanWordpressSite";

        var data = {}


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $('#cyberPanelLoading').hide();

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Successfully Saved!.',
                    type: 'success'
                });
                location.reload();

            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $('#cyberPanelLoading').hide();
            new PNotify({
                title: 'Operation Failed!',
                text: response.data.error_message,
                type: 'error'
            });


        }


    };


});

app.controller('listChildDomainsMain', function ($scope, $http, $timeout) {

    $scope.currentPage = 1;
    $scope.recordsToShow = 10;

    $scope.getFurtherWebsitesFromDB = function () {

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            page: $scope.currentPage,
            recordsToShow: $scope.recordsToShow
        };


        dataurl = "/websites/fetchChildDomainsMain";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            if (response.data.listWebSiteStatus === 1) {

                $scope.WebSitesList = JSON.parse(response.data.data);
                $scope.pagination = response.data.pagination;
                $scope.clients = JSON.parse(response.data.data);
                $("#listFail").hide();
            } else {
                $("#listFail").fadeIn();
                $scope.errorMessage = response.data.error_message;

            }
        }

        function cantLoadInitialData(response) {
        }


    };
    $scope.getFurtherWebsitesFromDB();

    $scope.cyberPanelLoading = true;

    $scope.issueSSL = function (virtualHost) {
        $scope.cyberPanelLoading = false;

        var url = "/manageSSL/issueSSL";


        var data = {
            virtualHost: virtualHost
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.SSL === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'SSL successfully issued.',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }


    };

    $scope.cyberPanelLoading = true;

    $scope.searchWebsites = function () {

        $scope.cyberPanelLoading = false;

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            patternAdded: $scope.patternAdded
        };

        dataurl = "/websites/searchChilds";

        $http.post(dataurl, data, config).then(ListInitialData, cantLoadInitialData);


        function ListInitialData(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.listWebSiteStatus === 1) {

                var finalData = JSON.parse(response.data.data);
                $scope.WebSitesList = finalData;
                $("#listFail").hide();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }
        }

        function cantLoadInitialData(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Connect disrupted, refresh the page.',
                type: 'error'
            });
        }


    };

    $scope.initConvert = function (virtualHost) {
        $scope.domainName = virtualHost;
    };

    var statusFile;

    $scope.installationProgress = true;

    $scope.convert = function () {

        $scope.cyberPanelLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.goBackDisable = true;

        $scope.currentStatus = "Starting creation..";

        var ssl, dkimCheck, openBasedir;

        if ($scope.sslCheck === true) {
            ssl = 1;
        } else {
            ssl = 0
        }

        if ($scope.dkimCheck === true) {
            dkimCheck = 1;
        } else {
            dkimCheck = 0
        }

        if ($scope.openBasedir === true) {
            openBasedir = 1;
        } else {
            openBasedir = 0
        }

        url = "/websites/convertDomainToSite";


        var data = {
            package: $scope.packageForWebsite,
            domainName: $scope.domainName,
            adminEmail: $scope.adminEmail,
            phpSelection: $scope.phpSelection,
            websiteOwner: $scope.websiteOwner,
            ssl: ssl,
            dkimCheck: dkimCheck,
            openBasedir: openBasedir
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.createWebSiteStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getCreationStatus();
            } else {

                $scope.cyberPanelLoading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.goBackDisable = false;

                $scope.currentStatus = response.data.error_message;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.cyberPanelLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.goBackDisable = false;

        }


    };
    $scope.goBack = function () {
        $scope.cyberPanelLoading = true;
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getCreationStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.cyberPanelLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.goBackDisable = false;

                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.cyberPanelLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.goBackDisable = false;

                    $scope.currentStatus = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;
                $timeout(getCreationStatus, 1000);
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.cyberPanelLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.goBackDisable = false;

        }


    }

    var DeleteDomain;
    $scope.deleteDomainInit = function (childDomainForDeletion) {
        DeleteDomain = childDomainForDeletion;
    };

    $scope.deleteChildDomain = function () {
        $scope.cyberPanelLoading = false;
        url = "/websites/submitDomainDeletion";

        var data = {
            websiteName: DeleteDomain,
            DeleteDocRoot: $scope.DeleteDocRoot
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.websiteDeleteStatus === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Child Domain successfully deleted.',
                    type: 'success'
                });
                $scope.getFurtherWebsitesFromDB();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });

        }

    };

});

/* Java script code to list accounts ends here */


/* Java script code to delete Website */


$("#websiteDeleteFailure").hide();
$("#websiteDeleteSuccess").hide();

$("#deleteWebsiteButton").hide();
$("#deleteLoading").hide();

app.controller('deleteWebsiteControl', function ($scope, $http) {


    $scope.deleteWebsite = function () {

        $("#deleteWebsiteButton").fadeIn();


    };

    $scope.deleteWebsiteFinal = function () {

        $("#deleteLoading").show();

        var websiteName = $scope.websiteToBeDeleted;


        url = "/websites/submitWebsiteDeletion";

        var data = {
            websiteName: websiteName
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.websiteDeleteStatus === 0) {
                $scope.errorMessage = response.data.error_message;
                $("#websiteDeleteFailure").fadeIn();
                $("#websiteDeleteSuccess").hide();
                $("#deleteWebsiteButton").hide();


                $("#deleteLoading").hide();

            } else {
                $("#websiteDeleteFailure").hide();
                $("#websiteDeleteSuccess").fadeIn();
                $("#deleteWebsiteButton").hide();
                $scope.deletedWebsite = websiteName;
                $("#deleteLoading").hide();

            }


        }

        function cantLoadInitialDatas(response) {
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

app.controller('modifyWebsitesController', function ($scope, $http) {

    $scope.fetchWebsites = function () {

        $("#modifyWebsiteLoading").show();


        var websiteToBeModified = $scope.websiteToBeModified;

        url = "/websites/getWebsiteDetails";

        var data = {
            websiteToBeModified: websiteToBeModified,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.modifyStatus === 0) {
                console.log(response.data);
                $scope.errorMessage = response.data.error_message;
                $("#websiteModifyFailure").fadeIn();
                $("#websiteModifySuccess").hide();
                $("#modifyWebsiteButton").hide();
                $("#modifyWebsiteLoading").hide();
                $("#canNotModify").hide();


            } else {
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
            packForWeb: packForWeb,
            email: email,
            phpVersion: phpVersion,
            admin: admin
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.saveStatus === 0) {
                $scope.errMessage = response.data.error_message;

                $("#canNotModify").fadeIn();
                $("#websiteModifyFailure").hide();
                $("#websiteModifySuccess").hide();
                $("#websiteSuccessfullyModified").hide();
                $("#modifyWebsiteLoading").hide();


            } else {
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
var website_child_domain_check = 0;

function website_child_domain_checkbox_function() {

    var checkBox = document.getElementById("myCheck");
    // Get the output text


    // If the checkbox is checked, display the output text
    if (checkBox.checked == true) {
        website_child_domain_check = 0;
        document.getElementById('Website_Create_Test_Domain').style.display = "block";
        document.getElementById('Website_Create_Own_Domain').style.display = "none";

    } else {
        document.getElementById('Website_Create_Test_Domain').style.display = "none";
        document.getElementById('Website_Create_Own_Domain').style.display = "block";
        website_child_domain_check = 1;
    }

    // alert(domain_check);
}

app.controller('websitePages', function ($scope, $http, $timeout, $window) {

    $scope.logFileLoading = true;
    $scope.logsFeteched = true;
    $scope.couldNotFetchLogs = true;
    $scope.couldNotConnect = true;
    $scope.fetchedData = true;
    $scope.hideLogs = true;
    $scope.hideErrorLogs = true;

    $scope.hidelogsbtn = function () {
        $scope.hideLogs = true;
    };

    $scope.hideErrorLogsbtn = function () {
        $scope.hideLogs = true;
    };

    $scope.fileManagerURL = "/filemanager/" + $("#domainNamePage").text();
    $scope.wordPressInstallURL = $("#domainNamePage").text() + "/wordpressInstall";
    $scope.joomlaInstallURL = $("#domainNamePage").text() + "/joomlaInstall";
    $scope.setupGit = $("#domainNamePage").text() + "/setupGit";
    $scope.installPrestaURL = $("#domainNamePage").text() + "/installPrestaShop";
    $scope.installMagentoURL = $("#domainNamePage").text() + "/installMagento";
    $scope.installMauticURL = $("#domainNamePage").text() + "/installMautic";
    $scope.domainAliasURL = "/websites/" + $("#domainNamePage").text() + "/domainAlias";
    $scope.previewUrl = "/preview/" + $("#domainNamePage").text() + "/";

    var logType = 0;
    $scope.pageNumber = 1;

    $scope.fetchLogs = function (type) {

        var pageNumber = $scope.pageNumber;


        if (type == 3) {
            pageNumber = $scope.pageNumber + 1;
            $scope.pageNumber = pageNumber;
        } else if (type == 4) {
            pageNumber = $scope.pageNumber - 1;
            $scope.pageNumber = pageNumber;
        } else {
            logType = type;
        }


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;
        $scope.couldNotConnect = true;
        $scope.fetchedData = false;
        $scope.hideErrorLogs = true;


        url = "/websites/getDataFromLogFile";

        var domainNamePage = $("#domainNamePage").text();


        var data = {
            logType: logType,
            virtualHost: domainNamePage,
            page: pageNumber,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.logstatus == 1) {


                $scope.logFileLoading = true;
                $scope.logsFeteched = false;
                $scope.couldNotFetchLogs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedData = false;
                $scope.hideLogs = false;


                $scope.records = JSON.parse(response.data.data);

            } else {

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

    $scope.errorPageNumber = 1;


    $scope.fetchErrorLogs = function (type) {

        var errorPageNumber = $scope.errorPageNumber;


        if (type == 3) {
            errorPageNumber = $scope.errorPageNumber + 1;
            $scope.errorPageNumber = errorPageNumber;
        } else if (type == 4) {
            errorPageNumber = $scope.errorPageNumber - 1;
            $scope.errorPageNumber = errorPageNumber;
        } else {
            logType = type;
        }

        // notifications

        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;
        $scope.couldNotConnect = true;
        $scope.fetchedData = true;
        $scope.hideErrorLogs = true;
        $scope.hideLogs = false;


        url = "/websites/fetchErrorLogs";

        var domainNamePage = $("#domainNamePage").text();


        var data = {
            virtualHost: domainNamePage,
            page: errorPageNumber,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.logstatus === 1) {


                // notifications

                $scope.logFileLoading = true;
                $scope.logsFeteched = false;
                $scope.couldNotFetchLogs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedData = true;
                $scope.hideLogs = false;
                $scope.hideErrorLogs = false;


                $scope.errorLogsData = response.data.data;

            } else {

                // notifications

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = false;
                $scope.couldNotConnect = true;
                $scope.fetchedData = true;
                $scope.hideLogs = true;
                $scope.hideErrorLogs = true;


                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            // notifications

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = true;
            $scope.couldNotConnect = false;
            $scope.fetchedData = true;
            $scope.hideLogs = true;
            $scope.hideErrorLogs = true;

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

    $scope.hideconfigbtn = function () {

        $scope.configurationsBox = true;
    };

    $scope.fetchConfigurations = function () {


        $scope.hidsslconfigs = true;
        $scope.configurationsBoxRewrite = true;
        $scope.changePHPView = true;


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
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.configstatus === 1) {

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

            } else {

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

    $scope.saveCongiruations = function () {

        $scope.configFileLoading = false;


        url = "/websites/saveConfigsToFile";

        var virtualHost = $("#domainNamePage").text();
        var configData = $scope.configData;


        var data = {
            virtualHost: virtualHost,
            configData: configData,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.configstatus === 1) {

                $scope.configurationsBox = false;
                $scope.configsFetched = true;
                $scope.couldNotFetchConfigs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedConfigsData = true;
                $scope.configFileLoading = true;
                $scope.configSaved = false;
                $scope.couldNotSaveConfigurations = true;
                $scope.saveConfigBtn = true;


            } else {
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

    $scope.hideRewriteRulesbtn = function () {
        $scope.configurationsBoxRewrite = true;
    };

    $scope.fetchRewriteFules = function () {

        $scope.hidsslconfigs = true;
        $scope.configurationsBox = true;
        $scope.changePHPView = true;


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
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.rewriteStatus == 1) {


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

            } else {
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

    $scope.saveRewriteRules = function () {

        $scope.configFileLoading = false;


        url = "/websites/saveRewriteRules";

        var virtualHost = $("#domainNamePage").text();
        var rewriteRules = $scope.rewriteRules;


        var data = {
            virtualHost: virtualHost,
            rewriteRules: rewriteRules,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.rewriteStatus == 1) {

                $scope.configurationsBoxRewrite = false;
                $scope.rewriteRulesFetched = true;
                $scope.couldNotFetchRewriteRules = true;
                $scope.rewriteRulesSaved = false;
                $scope.couldNotSaveRewriteRules = true;
                $scope.fetchedRewriteRules = true;
                $scope.saveRewriteRulesBTN = true;
                $scope.configFileLoading = true;


            } else {
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
    $scope.installationDetailsFormJoomla = true;
    $scope.applicationInstallerLoading = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;


    $scope.installationDetails = function () {

        $scope.installationDetailsForm = !$scope.installationDetailsForm;
        $scope.installationDetailsFormJoomla = true;

    };

    $scope.installationDetailsJoomla = function () {

        $scope.installationDetailsFormJoomla = !$scope.installationDetailsFormJoomla;
        $scope.installationDetailsForm = true;

    };

    $scope.installWordpress = function () {


        $scope.installationDetailsForm = false;
        $scope.applicationInstallerLoading = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;

        var domain = $("#domainNamePage").text();
        var path = $scope.installPath;

        url = "/websites/installWordpress";

        var home = "1";

        if (typeof path != 'undefined') {
            home = "0";
        }


        var data = {
            domain: domain,
            home: home,
            path: path,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                if (typeof path != 'undefined') {
                    $scope.installationURL = "http://" + domain + "/" + path;
                } else {
                    $scope.installationURL = domain;
                }

                $scope.installationDetailsForm = false;
                $scope.applicationInstallerLoading = true;
                $scope.installationFailed = true;
                $scope.installationSuccessfull = false;
                $scope.couldNotConnect = true;

            } else {

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

    $scope.installJoomla = function () {


        $scope.installationDetailsFormJoomla = false;
        $scope.applicationInstallerLoading = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;

        var domain = $("#domainNamePage").text();
        var path = $scope.installPath;
        var username = 'admin';
        var password = $scope.password;
        var prefix = $scope.prefix;


        url = "/websites/installJoomla";

        var home = "1";

        if (typeof path != 'undefined') {
            home = "0";
        }


        var data = {
            domain: domain,
            siteName: $scope.siteName,
            home: home,
            path: path,
            password: password,
            prefix: prefix,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                if (typeof path != 'undefined') {
                    $scope.installationURL = "http://" + domain + "/" + path;
                } else {
                    $scope.installationURL = domain;
                }

                $scope.installationDetailsFormJoomla = false;
                $scope.applicationInstallerLoading = true;
                $scope.installationFailed = true;
                $scope.installationSuccessfull = false;
                $scope.couldNotConnect = true;

            } else {

                $scope.installationDetailsFormJoomla = false;
                $scope.applicationInstallerLoading = true;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.installationDetailsFormJoomla = false;
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


    $scope.hidesslbtn = function () {
        $scope.hidsslconfigs = true;
    };

    $scope.addSSL = function () {
        $scope.hidsslconfigs = false;
        $scope.configurationsBox = true;
        $scope.configurationsBoxRewrite = true;
        $scope.changePHPView = true;
    };

    $scope.saveSSL = function () {


        $scope.configFileLoading = false;

        url = "/websites/saveSSL";

        var virtualHost = $("#domainNamePage").text();
        var cert = $scope.cert;
        var key = $scope.key;


        var data = {
            virtualHost: virtualHost,
            cert: cert,
            key: key
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.sslStatus === 1) {

                $scope.sslSaved = false;
                $scope.couldNotSaveSSL = true;
                $scope.couldNotConnect = true;
                $scope.configFileLoading = true;


            } else {

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

    //// Change PHP Master

    $scope.failedToChangePHPMaster = true;
    $scope.phpChangedMaster = true;
    $scope.couldNotConnect = true;

    $scope.changePHPView = true;


    $scope.hideChangePHPMaster = function () {
        $scope.changePHPView = true;
    };

    $scope.changePHPMaster = function () {
        $scope.hidsslconfigs = true;
        $scope.configurationsBox = true;
        $scope.configurationsBoxRewrite = true;
        $scope.changePHPView = false;
    };

    $scope.changePHPVersionMaster = function (childDomain, phpSelection) {

        // notifcations

        $scope.configFileLoading = false;

        var url = "/websites/changePHP";

        var data = {
            childDomain: $("#domainNamePage").text(),
            phpSelection: $scope.phpSelectionMaster,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changePHP === 1) {

                $scope.configFileLoading = true;
                $scope.websiteDomain = $("#domainNamePage").text();


                // notifcations

                $scope.failedToChangePHPMaster = true;
                $scope.phpChangedMaster = false;
                $scope.couldNotConnect = true;


            } else {

                $scope.configFileLoading = true;
                $scope.errorMessage = response.data.error_message;

                // notifcations

                $scope.failedToChangePHPMaster = false;
                $scope.phpChangedMaster = true;
                $scope.couldNotConnect = true;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.configFileLoading = true;

            // notifcations

            $scope.failedToChangePHPMaster = true;
            $scope.phpChangedMaster = true;
            $scope.couldNotConnect = false;

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
    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.errorMessageBox = true;
    $scope.success = true;
    $scope.couldNotConnect = true;
    $scope.goBackDisable = true;
    $scope.DomainCreateForm = true;

    var statusFile;

    $scope.WebsiteSelection = function () {
        $scope.DomainCreateForm = false;
    };

    $scope.createDomain = function () {

        $scope.domainLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting creation..";
        $scope.DomainCreateForm = true;

        var ssl, dkimCheck, openBasedir;

        if ($scope.sslCheck === true) {
            ssl = 1;
        } else {
            ssl = 0
        }

        if ($scope.dkimCheck === true) {
            dkimCheck = 1;
        } else {
            dkimCheck = 0
        }

        if ($scope.openBasedir === true) {
            openBasedir = 1;
        } else {
            openBasedir = 0
        }


        url = "/websites/submitDomainCreation";
        var domainName = $scope.domainNameCreate;
        var phpSelection = $scope.phpSelection;

        var path = $scope.docRootPath;

        if (typeof path === 'undefined') {
            path = "";
        }
        var package = $scope.packageForWebsite;

        if (website_child_domain_check == 0) {
            var Part2_domainNameCreate = document.getElementById('Part2_domainNameCreate').value;
            var domainName = document.getElementById('TestDomainNameCreate').value + Part2_domainNameCreate;
        }
        if (website_child_domain_check == 1) {

            var domainName = $scope.own_domainNameCreate;
        }


        var data = {
            domainName: domainName,
            phpSelection: phpSelection,
            ssl: ssl,
            path: path,
            masterDomain: $scope.masterDomain,
            dkimCheck: dkimCheck,
            openBasedir: openBasedir
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.createWebSiteStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getCreationStatus();
            } else {

                $scope.domainLoading = true;
                $scope.installationDetailsForm = true;
                $scope.DomainCreateForm = true;
                $scope.installationProgress = false;
                $scope.errorMessageBox = false;
                $scope.success = true;
                $scope.couldNotConnect = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.domainLoading = true;
            $scope.installationDetailsForm = true;
            $scope.DomainCreateForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    };

    $scope.goBack = function () {
        $scope.domainLoading = true;
        $scope.installationDetailsForm = false;
        $scope.DomainCreateForm = true;
        $scope.installationProgress = true;
        $scope.errorMessageBox = true;
        $scope.success = true;
        $scope.couldNotConnect = true;
        $scope.goBackDisable = true;
        $scope.DomainCreateForm = true;
        $("#installProgress").css("width", "0%");
    };

    function getCreationStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.domainLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = true;
                    $scope.success = false;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;

                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.domainLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.DomainCreateForm = true;
                    $scope.installationProgress = false;
                    $scope.errorMessageBox = false;
                    $scope.success = true;
                    $scope.couldNotConnect = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;
                $timeout(getCreationStatus, 1000);
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.domainLoading = true;
            $scope.installationDetailsForm = true;
            $scope.DomainCreateForm = true;
            $scope.installationProgress = false;
            $scope.errorMessageBox = true;
            $scope.success = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;

        }


    }


    ////// List Domains Part

    ////////////////////////

    // notifcations

    $scope.phpChanged = true;
    $scope.domainError = true;
    $scope.couldNotConnect = true;
    $scope.domainDeleted = true;
    $scope.sslIssued = true;
    $scope.childBaseDirChanged = true;

    $("#listDomains").hide();


    $scope.showListDomains = function () {
        fetchDomains();
        $("#listDomains").fadeIn();
    };

    $scope.hideListDomains = function () {
        $("#listDomains").fadeOut();
    };

    function fetchDomains() {
        $scope.domainLoading = false;

        var url = "/websites/fetchDomains";

        var data = {
            masterDomain: $("#domainNamePage").text(),
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.fetchStatus === 1) {

                $scope.childDomains = JSON.parse(response.data.data);
                $scope.domainLoading = true;


            } else {
                $scope.domainError = false;
                $scope.errorMessage = response.data.error_message;
                $scope.domainLoading = true;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.couldNotConnect = false;

        }

    }


    $scope.changePHP = function (childDomain, phpSelection) {

        // notifcations

        $scope.phpChanged = true;
        $scope.domainError = true;
        $scope.couldNotConnect = true;
        $scope.domainDeleted = true;
        $scope.sslIssued = true;
        $scope.domainLoading = false;
        $scope.childBaseDirChanged = true;

        var url = "/websites/changePHP";

        var data = {
            childDomain: childDomain,
            phpSelection: phpSelection,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changePHP === 1) {

                $scope.domainLoading = true;

                $scope.changedPHPVersion = phpSelection;


                // notifcations

                $scope.phpChanged = false;
                $scope.domainError = true;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;
                $scope.childBaseDirChanged = true;


            } else {
                $scope.errorMessage = response.data.error_message;
                $scope.domainLoading = true;

                // notifcations

                $scope.phpChanged = true;
                $scope.domainError = false;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;
                $scope.childBaseDirChanged = true;
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
            $scope.childBaseDirChanged = true;

        }

    };

    $scope.changeChildBaseDir = function (childDomain, openBasedirValue) {

        // notifcations

        $scope.phpChanged = true;
        $scope.domainError = true;
        $scope.couldNotConnect = true;
        $scope.domainDeleted = true;
        $scope.sslIssued = true;
        $scope.domainLoading = false;
        $scope.childBaseDirChanged = true;


        var url = "/websites/changeOpenBasedir";

        var data = {
            domainName: childDomain,
            openBasedirValue: openBasedirValue
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changeOpenBasedir === 1) {

                $scope.phpChanged = true;
                $scope.domainError = true;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;
                $scope.domainLoading = true;
                $scope.childBaseDirChanged = false;

            } else {

                $scope.phpChanged = true;
                $scope.domainError = false;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;
                $scope.domainLoading = true;
                $scope.childBaseDirChanged = true;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.phpChanged = true;
            $scope.domainError = true;
            $scope.couldNotConnect = false;
            $scope.domainDeleted = true;
            $scope.sslIssued = true;
            $scope.domainLoading = true;
            $scope.childBaseDirChanged = true;


        }

    }

    $scope.deleteChildDomain = function (childDomain) {
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
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.websiteDeleteStatus === 1) {

                $scope.domainLoading = true;
                $scope.deletedDomain = childDomain;

                fetchDomains();


                // notifications

                $scope.phpChanged = true;
                $scope.domainError = true;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = false;
                $scope.sslIssued = true;


            } else {
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

    };

    $scope.issueSSL = function (childDomain, path) {
        $scope.domainLoading = false;

        // notifcations

        $scope.phpChanged = true;
        $scope.domainError = true;
        $scope.couldNotConnect = true;
        $scope.domainDeleted = true;
        $scope.sslIssued = true;
        $scope.childBaseDirChanged = true;

        var url = "/manageSSL/issueSSL";


        var data = {
            virtualHost: childDomain,
            path: path,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.SSL === 1) {

                $scope.domainLoading = true;

                // notifcations

                $scope.phpChanged = true;
                $scope.domainError = true;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = false;
                $scope.childBaseDirChanged = true;


                $scope.sslDomainIssued = childDomain;


            } else {
                $scope.domainLoading = true;

                $scope.errorMessage = response.data.error_message;

                // notifcations

                $scope.phpChanged = true;
                $scope.domainError = false;
                $scope.couldNotConnect = true;
                $scope.domainDeleted = true;
                $scope.sslIssued = true;
                $scope.childBaseDirChanged = true;

            }


        }

        function cantLoadInitialDatas(response) {

            // notifcations

            $scope.phpChanged = true;
            $scope.domainError = true;
            $scope.couldNotConnect = false;
            $scope.domainDeleted = true;
            $scope.sslIssued = true;
            $scope.childBaseDirChanged = true;


        }


    };


    /// Open_basedir protection

    $scope.baseDirLoading = true;
    $scope.operationFailed = true;
    $scope.operationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.openBaseDirBox = true;


    $scope.openBaseDirView = function () {
        $scope.openBaseDirBox = false;
    };

    $scope.hideOpenBasedir = function () {
        $scope.openBaseDirBox = true;
    };

    $scope.applyOpenBasedirChanges = function (childDomain, phpSelection) {

        // notifcations

        $scope.baseDirLoading = false;
        $scope.operationFailed = true;
        $scope.operationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.openBaseDirBox = false;


        var url = "/websites/changeOpenBasedir";

        var data = {
            domainName: $("#domainNamePage").text(),
            openBasedirValue: $scope.openBasedirValue
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changeOpenBasedir === 1) {

                $scope.baseDirLoading = true;
                $scope.operationFailed = true;
                $scope.operationSuccessfull = false;
                $scope.couldNotConnect = true;
                $scope.openBaseDirBox = false;

            } else {

                $scope.baseDirLoading = true;
                $scope.operationFailed = false;
                $scope.operationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.openBaseDirBox = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.baseDirLoading = true;
            $scope.operationFailed = true;
            $scope.operationSuccessfull = true;
            $scope.couldNotConnect = false;
            $scope.openBaseDirBox = false;


        }

    }


    // REWRITE Template

    const httpToHTTPS = `### Rewrite Rules Added by CyberPanel Rewrite Rule Generator

RewriteEngine On
RewriteCond %{HTTPS}  !=on
RewriteRule ^/?(.*) https://%{SERVER_NAME}/$1 [R,L]

### End CyberPanel Generated Rules.

`;

    const WWWToNonWWW = `### Rewrite Rules Added by CyberPanel Rewrite Rule Generator

RewriteEngine On
RewriteCond %{HTTP_HOST} ^www\.(.*)$
RewriteRule ^(.*)$ http://%1/$1 [L,R=301]

### End CyberPanel Generated Rules.

`;

    const nonWWWToWWW = `### Rewrite Rules Added by CyberPanel Rewrite Rule Generator

RewriteEngine On
RewriteCond %{HTTP_HOST} !^www\. [NC]
RewriteRule ^(.*)$ http://www.%{HTTP_HOST}%{REQUEST_URI} [R=301,L]

### End CyberPanel Generated Rules.

`;

    const WordpressProtect = `### Rewrite Rules Added by CyberPanel Rewrite Rule Generator

RewriteEngine On
RewriteRule ^/(xmlrpc|wp-trackback)\.php - [F,L,NC]

### End CyberPanel Generated Rules.

`;

    $scope.applyRewriteTemplate = function () {

        if ($scope.rewriteTemplate === "Force HTTP -> HTTPS") {
            $scope.rewriteRules = httpToHTTPS + $scope.rewriteRules;
        } else if ($scope.rewriteTemplate === "Force NON-WWW -> WWW") {
            $scope.rewriteRules = nonWWWToWWW + $scope.rewriteRules;
        } else if ($scope.rewriteTemplate === "Force WWW -> NON-WWW") {
            $scope.rewriteRules = WWWToNonWWW + $scope.rewriteRules;
        } else if ($scope.rewriteTemplate === "Disable Wordpress XMLRPC & Trackback") {
            $scope.rewriteRules = WordpressProtect + $scope.rewriteRules;
        }
    };


});

/* Java script code to create account ends here */

/* Java script code to suspend/un-suspend Website */

app.controller('suspendWebsiteControl', function ($scope, $http) {

    $scope.suspendLoading = true;
    $scope.stateView = true;

    $scope.websiteSuspendFailure = true;
    $scope.websiteUnsuspendFailure = true;
    $scope.websiteSuccess = true;
    $scope.couldNotConnect = true;

    $scope.showSuspendUnsuspend = function () {

        $scope.stateView = false;


    };

    $scope.save = function () {

        $scope.suspendLoading = false;

        var websiteName = $scope.websiteToBeSuspended
        var state = $scope.state;


        url = "/websites/submitWebsiteStatus";

        var data = {
            websiteName: websiteName,
            state: state,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.websiteStatus === 1) {
                if (state == "Suspend") {

                    $scope.suspendLoading = true;
                    $scope.stateView = false;

                    $scope.websiteSuspendFailure = true;
                    $scope.websiteUnsuspendFailure = true;
                    $scope.websiteSuccess = false;
                    $scope.couldNotConnect = true;

                    $scope.websiteStatus = websiteName;
                    $scope.finalStatus = "Suspended";

                } else {
                    $scope.suspendLoading = true;
                    $scope.stateView = false;

                    $scope.websiteSuspendFailure = true;
                    $scope.websiteUnsuspendFailure = true;
                    $scope.websiteSuccess = false;
                    $scope.couldNotConnect = true;

                    $scope.websiteStatus = websiteName;
                    $scope.finalStatus = "Un-suspended";

                }

            } else {

                if (state == "Suspend") {

                    $scope.suspendLoading = true;
                    $scope.stateView = false;

                    $scope.websiteSuspendFailure = false;
                    $scope.websiteUnsuspendFailure = true;
                    $scope.websiteSuccess = true;
                    $scope.couldNotConnect = true;


                } else {
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

/* Java script code to manage cron */

app.controller('manageCronController', function ($scope, $http) {
    $("#manageCronLoading").hide();
    $("#modifyCronForm").hide();
    $("#cronTable").hide();
    $("#saveCronButton").hide();
    $("#addCronButton").hide();

    $("#addCronFailure").hide();
    $("#cronEditSuccess").hide();
    $("#fetchCronFailure").hide();

    $scope.websiteToBeModified = $("#domain").text();

    $scope.fetchWebsites = function () {

        $("#manageCronLoading").show();
        $("#addCronFailure").hide();
        $("#cronEditSuccess").hide();
        $("#fetchCronFailure").hide();
        var websiteToBeModified = $scope.websiteToBeModified;
        url = "/websites/getWebsiteCron";

        var data = {
            domain: websiteToBeModified,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            if (response.data.getWebsiteCron === 0) {
                console.log(response.data);
                $scope.errorMessage = response.data.error_message;
                $("#cronTable").hide();
                $("#manageCronLoading").hide();
                $("#modifyCronForm").hide();
                $("#saveCronButton").hide();
                $("#addCronButton").hide();
            } else {
                console.log(response.data);
                var finalData = response.data.crons;
                $scope.cronList = finalData;
                $("#cronTable").show();
                $("#manageCronLoading").hide();
                $("#modifyCronForm").hide();
                $("#saveCronButton").hide();
                $("#addCronButton").hide();
            }
        }

        function cantLoadInitialDatas(response) {
            $("#manageCronLoading").hide();
            $("#cronTable").hide();
            $("#fetchCronFailure").show();
            $("#addCronFailure").hide();
            $("#cronEditSuccess").hide();
        }
    };
    $scope.fetchWebsites();

    $scope.fetchCron = function (cronLine) {

        $("#cronTable").show();
        $("#manageCronLoading").show();
        $("#modifyCronForm").show();
        $("#saveCronButton").show();
        $("#addCronButton").hide();

        $("#addCronFailure").hide();
        $("#cronEditSuccess").hide();
        $("#fetchCronFailure").hide();

        $scope.line = cronLine;
        console.log($scope.line);

        var websiteToBeModified = $scope.websiteToBeModified;
        url = "/websites/getCronbyLine";
        var data = {
            domain: websiteToBeModified,
            line: cronLine
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            console.log(response);

            if (response.data.getWebsiteCron === 0) {
                console.log(response.data);
                $scope.errorMessage = response.data.error_message;
                $("#cronTable").show();
                $("#manageCronLoading").hide();
                $("#modifyCronForm").hide();
                $("#saveCronButton").hide();
                $("#addCronButton").hide();
            } else {
                console.log(response.data);

                $scope.minute = response.data.cron.minute
                $scope.hour = response.data.cron.hour
                $scope.monthday = response.data.cron.monthday
                $scope.month = response.data.cron.month
                $scope.weekday = response.data.cron.weekday
                $scope.command = response.data.cron.command
                $scope.line = response.data.line

                $("#cronTable").show();
                $("#manageCronLoading").hide();
                $("#modifyCronForm").fadeIn();
                $("#addCronButton").hide();
                $("#saveCronButton").show();

            }
        }

        function cantLoadInitialDatas(response) {
            $("#manageCronLoading").hide();
            $("#fetchCronFailure").show();
            $("#addCronFailure").hide();
            $("#cronEditSuccess").hide();
        }
    };

    $scope.populate = function () {
        splitTime = $scope.defined.split(" ");
        $scope.minute = splitTime[0];
        $scope.hour = splitTime[1];
        $scope.monthday = splitTime[2];
        $scope.month = splitTime[3];
        $scope.weekday = splitTime[4];
    }

    $scope.addCronForm = function () {

        $("#addCronFailure").hide();
        $("#cronEditSuccess").hide();
        $("#fetchCronFailure").hide();
        $("#manageCronLoading").hide();
        if (!$scope.websiteToBeModified) {
            alert("Please select a domain first");
        } else {
            $scope.minute = $scope.hour = $scope.monthday = $scope.month = $scope.weekday = $scope.command = $scope.line = "";

            $("#cronTable").hide();
            $("#manageCronLoading").hide();
            $("#modifyCronForm").show();
            $("#saveCronButton").hide()
            $("#addCronButton").show();
        }
    };

    $scope.addCronFunc = function () {

        $("#manageCronLoading").show();
        $("#addCronFailure").hide();
        $("#cronEditSuccess").hide();
        $("#fetchCronFailure").hide();

        var websiteToBeModified = $scope.websiteToBeModified;

        url = "/websites/addNewCron";
        var data = {
            domain: websiteToBeModified,
            minute: $scope.minute,
            hour: $scope.hour,
            monthday: $scope.monthday,
            month: $scope.month,
            weekday: $scope.weekday,
            cronCommand: $scope.command
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            console.log(response);

            if (response.data.addNewCron === 0) {
                $scope.errorMessage = response.data.error_message
                $("#manageCronLoading").hide();
                $("#cronEditSuccess").hide();
                $("#fetchCronFailure").hide();
                $("#addCronFailure").show();
            } else {
                $("#cronTable").hide();
                $("#manageCronLoading").hide();
                $("#cronEditSuccess").show();
                $("#fetchCronFailure").hide();
                $("#addCronFailure").hide();

            }
        }

        function cantLoadInitialDatas(response) {
            $("#manageCronLoading").hide();
            $("#addCronFailure").show();
            $("#cronEditSuccess").hide();
            $("#fetchCronFailure").hide();
        }
    };

    $scope.removeCron = function (line) {

        $("#manageCronLoading").show();

        $("#addCronFailure").hide();
        $("#cronEditSuccess").hide();
        $("#fetchCronFailure").hide();

        url = "/websites/remCronbyLine";
        var data = {
            domain: $scope.websiteToBeModified,
            line: line
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            console.log(response);

            if (response.data.remCronbyLine === 0) {
                $scope.errorMessage = response.data.error_message;
                $("#manageCronLoading").hide();
                $("#cronEditSuccess").hide();
                $("#fetchCronFailure").hide();
                $("#addCronFailure").show();
            } else {
                $("#cronTable").hide();
                $("#manageCronLoading").hide();
                $("#cronEditSuccess").show();
                $("#fetchCronFailure").hide();
                $("#addCronFailure").hide();

            }
        }

        function cantLoadInitialDatas(response) {
            $("#manageCronLoading").hide();
            $("#addCronFailure").show();
            $("#cronEditSuccess").hide();
            $("#fetchCronFailure").hide();
        }
    };

    $scope.modifyCronFunc = function () {

        $("#manageCronLoading").show();
        $("#addCronFailure").hide();
        $("#cronEditSuccess").hide();
        $("#fetchCronFailure").hide();

        var websiteToBeModified = $scope.websiteToBeModified;

        url = "/websites/saveCronChanges";
        var data = {
            domain: websiteToBeModified,
            line: $scope.line,
            minute: $scope.minute,
            hour: $scope.hour,
            monthday: $scope.monthday,
            month: $scope.month,
            weekday: $scope.weekday,
            cronCommand: $scope.command
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.addNewCron === 0) {

                $scope.errorMessage = response.data.error_message;
                $("#manageCronLoading").hide();
                $("#cronEditSuccess").hide();
                $("#fetchCronFailure").hide();
                $("#addCronFailure").show();
            } else {
                console.log(response.data);
                $("#cronTable").hide();
                $("#manageCronLoading").hide();
                $("#cronEditSuccess").show();
                $("#fetchCronFailure").hide();
                $("#addCronFailure").hide();

            }
        }

        function cantLoadInitialDatas(response) {
            $("#manageCronLoading").hide();
            $("#addCronFailure").show();
            $("#cronEditSuccess").hide();
            $("#fetchCronFailure").hide();
        }
    };

});

/* Java script code to manage cron ends here */

/* Java script code to manage cron */

app.controller('manageAliasController', function ($scope, $http, $timeout, $window) {

    $('form').submit(function (e) {
        e.preventDefault();
    });

    var masterDomain = "";

    $scope.aliasTable = false;
    $scope.addAliasButton = false;
    $scope.domainAliasForm = true;
    $scope.aliasError = true;
    $scope.couldNotConnect = true;
    $scope.aliasCreated = true;
    $scope.manageAliasLoading = true;
    $scope.operationSuccess = true;

    $scope.createAliasEnter = function ($event) {
        var keyCode = $event.which || $event.keyCode;
        if (keyCode === 13) {
            $scope.manageAliasLoading = false;
            $scope.addAliasFunc();
        }
    };

    $scope.showAliasForm = function (domainName) {

        $scope.domainAliasForm = false;
        $scope.aliasTable = true;
        $scope.addAliasButton = true;

        masterDomain = domainName;

    };

    $scope.addAliasFunc = function () {

        $scope.manageAliasLoading = false;

        var ssl;

        if ($scope.sslCheck === true) {
            ssl = 1;
        } else {
            ssl = 0
        }

        url = "/websites/submitAliasCreation";

        var data = {
            masterDomain: masterDomain,
            aliasDomain: $scope.aliasDomain,
            ssl: ssl

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.createAliasStatus === 1) {

                $scope.aliasTable = true;
                $scope.addAliasButton = true;
                $scope.domainAliasForm = false;
                $scope.aliasError = true;
                $scope.couldNotConnect = true;
                $scope.aliasCreated = false;
                $scope.manageAliasLoading = true;
                $scope.operationSuccess = true;

                $timeout(function () {
                    $window.location.reload();
                }, 3000);


            } else {

                $scope.aliasTable = true;
                $scope.addAliasButton = true;
                $scope.domainAliasForm = false;
                $scope.aliasError = false;
                $scope.couldNotConnect = true;
                $scope.aliasCreated = true;
                $scope.manageAliasLoading = true;
                $scope.operationSuccess = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.aliasTable = true;
            $scope.addAliasButton = true;
            $scope.domainAliasForm = false;
            $scope.aliasError = true;
            $scope.couldNotConnect = false;
            $scope.aliasCreated = true;
            $scope.manageAliasLoading = true;
            $scope.operationSuccess = true;


        }


    };

    $scope.issueSSL = function (masterDomain, aliasDomain) {

        $scope.manageAliasLoading = false;


        url = "/websites/issueAliasSSL";

        var data = {
            masterDomain: masterDomain,
            aliasDomain: aliasDomain,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.sslStatus === 1) {

                $scope.aliasTable = false;
                $scope.addAliasButton = true;
                $scope.domainAliasForm = true;
                $scope.aliasError = true;
                $scope.couldNotConnect = true;
                $scope.aliasCreated = true;
                $scope.manageAliasLoading = true;
                $scope.operationSuccess = false;


            } else {

                $scope.aliasTable = false;
                $scope.addAliasButton = true;
                $scope.domainAliasForm = true;
                $scope.aliasError = false;
                $scope.couldNotConnect = true;
                $scope.aliasCreated = true;
                $scope.manageAliasLoading = true;
                $scope.operationSuccess = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.aliasTable = false;
            $scope.addAliasButton = true;
            $scope.domainAliasForm = true;
            $scope.aliasError = true;
            $scope.couldNotConnect = false;
            $scope.aliasCreated = true;
            $scope.manageAliasLoading = true;
            $scope.operationSuccess = true;


        }


    };

    $scope.removeAlias = function (masterDomain, aliasDomain) {

        $scope.manageAliasLoading = false;

        url = "/websites/delateAlias";

        var data = {
            masterDomain: masterDomain,
            aliasDomain: aliasDomain,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.deleteAlias === 1) {

                $scope.aliasTable = false;
                $scope.addAliasButton = true;
                $scope.domainAliasForm = true;
                $scope.aliasError = true;
                $scope.couldNotConnect = true;
                $scope.aliasCreated = true;
                $scope.manageAliasLoading = true;
                $scope.operationSuccess = false;

                $timeout(function () {
                    $window.location.reload();
                }, 3000);


            } else {

                $scope.aliasTable = false;
                $scope.addAliasButton = true;
                $scope.domainAliasForm = true;
                $scope.aliasError = false;
                $scope.couldNotConnect = true;
                $scope.aliasCreated = true;
                $scope.manageAliasLoading = true;
                $scope.operationSuccess = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.aliasTable = false;
            $scope.addAliasButton = true;
            $scope.domainAliasForm = true;
            $scope.aliasError = true;
            $scope.couldNotConnect = false;
            $scope.aliasCreated = true;
            $scope.manageAliasLoading = true;
            $scope.operationSuccess = true;


        }


    };


});

/* Java script code to manage cron ends here */

app.controller('launchChild', function ($scope, $http) {

    $scope.logFileLoading = true;
    $scope.logsFeteched = true;
    $scope.couldNotFetchLogs = true;
    $scope.couldNotConnect = true;
    $scope.fetchedData = true;
    $scope.hideLogs = true;
    $scope.hideErrorLogs = true;

    $scope.hidelogsbtn = function () {
        $scope.hideLogs = true;
    };

    $scope.hideErrorLogsbtn = function () {
        $scope.hideLogs = true;
    };

    $scope.fileManagerURL = "/filemanager/" + $("#domainNamePage").text();
    $scope.previewUrl = "/preview/" + $("#childDomain").text() + "/";
    $scope.wordPressInstallURL = "/websites/" + $("#childDomain").text() + "/wordpressInstall";
    $scope.joomlaInstallURL = "/websites/" + $("#childDomain").text() + "/joomlaInstall";
    $scope.setupGit = "/websites/" + $("#childDomain").text() + "/setupGit";
    $scope.installPrestaURL = "/websites/" + $("#childDomain").text() + "/installPrestaShop";
    $scope.installMagentoURL = "/websites/" + $("#childDomain").text() + "/installMagento";

    var logType = 0;
    $scope.pageNumber = 1;

    $scope.fetchLogs = function (type) {

        var pageNumber = $scope.pageNumber;


        if (type == 3) {
            pageNumber = $scope.pageNumber + 1;
            $scope.pageNumber = pageNumber;
        } else if (type == 4) {
            pageNumber = $scope.pageNumber - 1;
            $scope.pageNumber = pageNumber;
        } else {
            logType = type;
        }


        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;
        $scope.couldNotConnect = true;
        $scope.fetchedData = false;
        $scope.hideErrorLogs = true;


        url = "/websites/getDataFromLogFile";

        var domainNamePage = $("#domainNamePage").text();


        var data = {
            logType: logType,
            virtualHost: domainNamePage,
            page: pageNumber,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.logstatus === 1) {


                $scope.logFileLoading = true;
                $scope.logsFeteched = false;
                $scope.couldNotFetchLogs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedData = false;
                $scope.hideLogs = false;


                $scope.records = JSON.parse(response.data.data);

            } else {

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

    $scope.errorPageNumber = 1;


    $scope.fetchErrorLogs = function (type) {

        var errorPageNumber = $scope.errorPageNumber;


        if (type === 3) {
            errorPageNumber = $scope.errorPageNumber + 1;
            $scope.errorPageNumber = errorPageNumber;
        } else if (type === 4) {
            errorPageNumber = $scope.errorPageNumber - 1;
            $scope.errorPageNumber = errorPageNumber;
        } else {
            logType = type;
        }

        // notifications

        $scope.logFileLoading = false;
        $scope.logsFeteched = true;
        $scope.couldNotFetchLogs = true;
        $scope.couldNotConnect = true;
        $scope.fetchedData = true;
        $scope.hideErrorLogs = true;
        $scope.hideLogs = false;


        url = "/websites/fetchErrorLogs";

        var domainNamePage = $("#domainNamePage").text();


        var data = {
            virtualHost: domainNamePage,
            page: errorPageNumber,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.logstatus === 1) {


                // notifications

                $scope.logFileLoading = true;
                $scope.logsFeteched = false;
                $scope.couldNotFetchLogs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedData = true;
                $scope.hideLogs = false;
                $scope.hideErrorLogs = false;


                $scope.errorLogsData = response.data.data;

            } else {

                // notifications

                $scope.logFileLoading = true;
                $scope.logsFeteched = true;
                $scope.couldNotFetchLogs = false;
                $scope.couldNotConnect = true;
                $scope.fetchedData = true;
                $scope.hideLogs = true;
                $scope.hideErrorLogs = true;


                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            // notifications

            $scope.logFileLoading = true;
            $scope.logsFeteched = true;
            $scope.couldNotFetchLogs = true;
            $scope.couldNotConnect = false;
            $scope.fetchedData = true;
            $scope.hideLogs = true;
            $scope.hideErrorLogs = true;

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

    $scope.hideconfigbtn = function () {

        $scope.configurationsBox = true;
    };

    $scope.fetchConfigurations = function () {


        $scope.hidsslconfigs = true;
        $scope.configurationsBoxRewrite = true;
        $scope.changePHPView = true;


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

        var virtualHost = $("#childDomain").text();


        var data = {
            virtualHost: virtualHost,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.configstatus === 1) {

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

            } else {

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

    $scope.saveCongiruations = function () {

        $scope.configFileLoading = false;


        url = "/websites/saveConfigsToFile";

        var virtualHost = $("#childDomain").text();
        var configData = $scope.configData;


        var data = {
            virtualHost: virtualHost,
            configData: configData,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.configstatus == 1) {

                $scope.configurationsBox = false;
                $scope.configsFetched = true;
                $scope.couldNotFetchConfigs = true;
                $scope.couldNotConnect = true;
                $scope.fetchedConfigsData = true;
                $scope.configFileLoading = true;
                $scope.configSaved = false;
                $scope.couldNotSaveConfigurations = true;
                $scope.saveConfigBtn = true;


            } else {
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

    $scope.hideRewriteRulesbtn = function () {
        $scope.configurationsBoxRewrite = true;
    };


    $scope.fetchRewriteFules = function () {

        $scope.hidsslconfigs = true;
        $scope.configurationsBox = true;
        $scope.changePHPView = true;


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

        var virtualHost = $("#childDomain").text();


        var data = {
            virtualHost: virtualHost,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.rewriteStatus == 1) {


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

            } else {
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

    $scope.saveRewriteRules = function () {

        $scope.configFileLoading = false;


        url = "/websites/saveRewriteRules";

        var virtualHost = $("#childDomain").text();
        var rewriteRules = $scope.rewriteRules;


        var data = {
            virtualHost: virtualHost,
            rewriteRules: rewriteRules,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.rewriteStatus == 1) {

                $scope.configurationsBoxRewrite = false;
                $scope.rewriteRulesFetched = true;
                $scope.couldNotFetchRewriteRules = true;
                $scope.rewriteRulesSaved = false;
                $scope.couldNotSaveRewriteRules = true;
                $scope.fetchedRewriteRules = true;
                $scope.saveRewriteRulesBTN = true;
                $scope.configFileLoading = true;


            } else {
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


    //////// SSL Part

    $scope.sslSaved = true;
    $scope.couldNotSaveSSL = true;
    $scope.hidsslconfigs = true;
    $scope.couldNotConnect = true;


    $scope.hidesslbtn = function () {
        $scope.hidsslconfigs = true;
    };

    $scope.addSSL = function () {
        $scope.hidsslconfigs = false;
        $scope.configurationsBox = true;
        $scope.configurationsBoxRewrite = true;
        $scope.changePHPView = true;
    };


    $scope.saveSSL = function () {


        $scope.configFileLoading = false;

        url = "/websites/saveSSL";

        var virtualHost = $("#childDomain").text();
        var cert = $scope.cert;
        var key = $scope.key;


        var data = {
            virtualHost: virtualHost,
            cert: cert,
            key: key,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.sslStatus === 1) {

                $scope.sslSaved = false;
                $scope.couldNotSaveSSL = true;
                $scope.couldNotConnect = true;
                $scope.configFileLoading = true;


            } else {

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


    //// Change PHP Master

    $scope.failedToChangePHPMaster = true;
    $scope.phpChangedMaster = true;
    $scope.couldNotConnect = true;

    $scope.changePHPView = true;


    $scope.hideChangePHPMaster = function () {
        $scope.changePHPView = true;
    };

    $scope.changePHPMaster = function () {
        $scope.hidsslconfigs = true;
        $scope.configurationsBox = true;
        $scope.configurationsBoxRewrite = true;
        $scope.changePHPView = false;
    };


    $scope.changePHPVersionMaster = function (childDomain, phpSelection) {

        // notifcations

        $scope.configFileLoading = false;

        var url = "/websites/changePHP";

        var data = {
            childDomain: $("#childDomain").text(),
            phpSelection: $scope.phpSelectionMaster,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changePHP === 1) {

                $scope.configFileLoading = true;
                $scope.websiteDomain = $("#childDomain").text();


                // notifcations

                $scope.failedToChangePHPMaster = true;
                $scope.phpChangedMaster = false;
                $scope.couldNotConnect = true;


            } else {

                $scope.configFileLoading = true;
                $scope.errorMessage = response.data.error_message;

                // notifcations

                $scope.failedToChangePHPMaster = false;
                $scope.phpChangedMaster = true;
                $scope.couldNotConnect = true;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.configFileLoading = true;

            // notifcations

            $scope.failedToChangePHPMaster = true;
            $scope.phpChangedMaster = true;
            $scope.couldNotConnect = false;

        }

    };


    /// Open_basedir protection

    $scope.baseDirLoading = true;
    $scope.operationFailed = true;
    $scope.operationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.openBaseDirBox = true;


    $scope.openBaseDirView = function () {
        $scope.openBaseDirBox = false;
    };

    $scope.hideOpenBasedir = function () {
        $scope.openBaseDirBox = true;
    };

    $scope.applyOpenBasedirChanges = function (childDomain, phpSelection) {

        // notifcations

        $scope.baseDirLoading = false;
        $scope.operationFailed = true;
        $scope.operationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.openBaseDirBox = false;


        var url = "/websites/changeOpenBasedir";

        var data = {
            domainName: $("#childDomain").text(),
            openBasedirValue: $scope.openBasedirValue
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.changeOpenBasedir === 1) {

                $scope.baseDirLoading = true;
                $scope.operationFailed = true;
                $scope.operationSuccessfull = false;
                $scope.couldNotConnect = true;
                $scope.openBaseDirBox = false;

            } else {

                $scope.baseDirLoading = true;
                $scope.operationFailed = false;
                $scope.operationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.openBaseDirBox = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {

            $scope.baseDirLoading = true;
            $scope.operationFailed = true;
            $scope.operationSuccessfull = true;
            $scope.couldNotConnect = false;
            $scope.openBaseDirBox = false;


        }

    }

});

/* Application Installer */

app.controller('installWordPressCTRL', function ($scope, $http, $timeout) {

    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.wpInstallLoading = true;
    $scope.goBackDisable = true;

    var statusFile;
    var domain = $("#domainNamePage").text();
    var path;


    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    $scope.installWordPress = function () {

        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = false;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting installation..";

        path = $scope.installPath;


        url = "/websites/installWordpress";

        var home = "1";

        if (typeof path !== 'undefined') {
            home = "0";
        }


        var data = {
            domain: domain,
            home: home,
            path: path,
            blogTitle: $scope.blogTitle,
            adminUser: $scope.adminUser,
            passwordByPass: $scope.adminPassword,
            adminEmail: $scope.adminEmail
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getInstallStatus();
            } else {

                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.wpInstallLoading = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {


        }

    };

    function getInstallStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile,
            domainName: domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = true;
                    $scope.installationSuccessfull = false;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    if (typeof path !== 'undefined') {
                        $scope.installationURL = "http://" + domain + "/" + path;
                    } else {
                        $scope.installationURL = domain;
                    }


                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = false;
                    $scope.installationSuccessfull = true;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;

                $timeout(getInstallStatus, 1000);


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;


        }


    }


});

app.controller('installJoomlaCTRL', function ($scope, $http, $timeout) {

    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.wpInstallLoading = true;
    $scope.goBackDisable = true;

    $scope.databasePrefix = 'jm_';

    var statusFile;
    var domain = $("#domainNamePage").text();
    var path;


    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getInstallStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile,
            domainName: domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = true;
                    $scope.installationSuccessfull = false;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    if (typeof path !== 'undefined') {
                        $scope.installationURL = "http://" + domain + "/" + path;
                    } else {
                        $scope.installationURL = domain;
                    }


                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = false;
                    $scope.installationSuccessfull = true;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;

                $timeout(getInstallStatus, 1000);


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;


        }


    }

    $scope.installJoomla = function () {

        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = false;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting installation..";

        path = $scope.installPath;


        url = "/websites/installJoomla";

        var home = "1";

        if (typeof path !== 'undefined') {
            home = "0";
        }


        var data = {
            domain: domain,
            home: home,
            path: path,
            siteName: $scope.siteName,
            username: $scope.adminUser,
            passwordByPass: $scope.adminPassword,
            prefix: $scope.databasePrefix
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getInstallStatus();
            } else {

                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.wpInstallLoading = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {


        }

    };


});

app.controller('setupGit', function ($scope, $http, $timeout, $window) {

    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.gitLoading = true;
    $scope.githubBranch = 'master';
    $scope.installProg = true;
    $scope.goBackDisable = true;

    var defaultProvider = 'github';

    $scope.setProvider = function (provider) {
        defaultProvider = provider;
    };


    var statusFile;
    var domain = $("#domainNamePage").text();

    function getInstallStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile,
            domainName: domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = true;
                    $scope.installationSuccessfull = false;
                    $scope.couldNotConnect = true;
                    $scope.gitLoading = true;
                    $scope.goBackDisable = true;

                    $scope.installationURL = domain;

                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();
                    $timeout(function () {
                        $window.location.reload();
                    }, 3000);

                } else {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = false;
                    $scope.installationSuccessfull = true;
                    $scope.couldNotConnect = true;
                    $scope.gitLoading = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;

                $timeout(getInstallStatus, 1000);


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;
            $scope.goBackDisable = false;


        }


    }

    $scope.attachRepo = function () {

        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.gitLoading = false;
        $scope.installProg = false;

        $scope.currentStatus = "Attaching GIT..";

        url = "/websites/setupGitRepo";

        var data = {
            domain: domain,
            username: $scope.githubUserName,
            reponame: $scope.githubRepo,
            branch: $scope.githubBranch,
            defaultProvider: defaultProvider
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getInstallStatus();
            } else {

                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.gitLoading = true;

                $scope.errorMessage = response.data.error_message;
                $scope.goBackDisable = false;

            }


        }

        function cantLoadInitialDatas(response) {


        }

    };

    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.installProg = true;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.gitLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    /// Detach Repo

    $scope.failedMesg = true;
    $scope.successMessage = true;
    $scope.couldNotConnect = true;
    $scope.gitLoading = true;
    $scope.successMessageBranch = true;

    $scope.detachRepo = function () {

        $scope.failedMesg = true;
        $scope.successMessage = true;
        $scope.couldNotConnect = true;
        $scope.gitLoading = false;
        $scope.successMessageBranch = true;

        url = "/websites/detachRepo";

        var data = {
            domain: domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.gitLoading = true;

            if (response.data.status === 1) {
                $scope.failedMesg = true;
                $scope.successMessage = false;
                $scope.couldNotConnect = true;
                $scope.successMessageBranch = true;

                $timeout(function () {
                    $window.location.reload();
                }, 3000);

            } else {

                $scope.failedMesg = false;
                $scope.successMessage = true;
                $scope.couldNotConnect = true;
                $scope.successMessageBranch = true;

                $scope.errorMessage = response.data.error_message;


            }


        }

        function cantLoadInitialDatas(response) {
            $scope.failedMesg = true;
            $scope.successMessage = true;
            $scope.couldNotConnect = false;
            $scope.gitLoading = true;
            $scope.successMessageBranch = true;
        }

    };
    $scope.changeBranch = function () {

        $scope.failedMesg = true;
        $scope.successMessage = true;
        $scope.couldNotConnect = true;
        $scope.gitLoading = false;
        $scope.successMessageBranch = true;

        url = "/websites/changeBranch";

        var data = {
            domain: domain,
            githubBranch: $scope.githubBranch
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.gitLoading = true;

            if (response.data.status === 1) {
                $scope.failedMesg = true;
                $scope.successMessage = true;
                $scope.couldNotConnect = true;
                $scope.successMessageBranch = false;

            } else {

                $scope.failedMesg = false;
                $scope.successMessage = true;
                $scope.couldNotConnect = true;
                $scope.successMessageBranch = true;

                $scope.errorMessage = response.data.error_message;


            }


        }

        function cantLoadInitialDatas(response) {
            $scope.failedMesg = true;
            $scope.successMessage = true;
            $scope.couldNotConnect = false;
            $scope.gitLoading = true;
            $scope.successMessageBranch = true;
        }

    };


});

app.controller('installPrestaShopCTRL', function ($scope, $http, $timeout) {

    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.wpInstallLoading = true;
    $scope.goBackDisable = true;

    $scope.databasePrefix = 'ps_';

    var statusFile;
    var domain = $("#domainNamePage").text();
    var path;


    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getInstallStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile,
            domainName: domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = true;
                    $scope.installationSuccessfull = false;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    if (typeof path !== 'undefined') {
                        $scope.installationURL = "http://" + domain + "/" + path;
                    } else {
                        $scope.installationURL = domain;
                    }


                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = false;
                    $scope.installationSuccessfull = true;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;

                $timeout(getInstallStatus, 1000);


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;


        }


    }

    $scope.installPrestShop = function () {

        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = false;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting installation..";

        path = $scope.installPath;


        url = "/websites/prestaShopInstall";

        var home = "1";

        if (typeof path !== 'undefined') {
            home = "0";
        }


        var data = {
            domain: domain,
            home: home,
            path: path,
            shopName: $scope.shopName,
            firstName: $scope.firstName,
            lastName: $scope.lastName,
            databasePrefix: $scope.databasePrefix,
            email: $scope.email,
            passwordByPass: $scope.password
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getInstallStatus();
            } else {

                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.wpInstallLoading = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {
        }

    };


});

app.controller('installMauticCTRL', function ($scope, $http, $timeout) {

    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.wpInstallLoading = true;
    $scope.goBackDisable = true;

    $scope.databasePrefix = 'ps_';

    var statusFile;
    var domain = $("#domainNamePage").text();
    var path;


    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getInstallStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile,
            domainName: domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = true;
                    $scope.installationSuccessfull = false;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    if (typeof path !== 'undefined') {
                        $scope.installationURL = "http://" + domain + "/" + path;
                    } else {
                        $scope.installationURL = domain;
                    }


                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = false;
                    $scope.installationSuccessfull = true;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;

                $timeout(getInstallStatus, 1000);


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;


        }


    }

    $scope.installMautic = function () {

        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = false;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting installation..";

        path = $scope.installPath;


        url = "/websites/mauticInstall";

        var home = "1";

        if (typeof path !== 'undefined') {
            home = "0";
        }


        var data = {
            domain: domain,
            home: home,
            path: path,
            username: $scope.adminUserName,
            email: $scope.email,
            passwordByPass: $scope.password
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getInstallStatus();
            } else {

                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.wpInstallLoading = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {
        }

    };


});

app.controller('sshAccess', function ($scope, $http, $timeout) {

    $scope.wpInstallLoading = true;

    $scope.setupSSHAccess = function () {
        $scope.wpInstallLoading = false;

        url = "/websites/saveSSHAccessChanges";

        var data = {
            domain: $("#domainName").text(),
            externalApp: $("#externalApp").text(),
            password: $scope.password
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.wpInstallLoading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Changes Successfully Applied.',
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

            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }

    };

    /// SSH Key at user level

    $scope.keyBox = true;
    $scope.saveKeyBtn = true;

    $scope.addKey = function () {
        $scope.showKeyBox = true;
        $scope.keyBox = false;
        $scope.saveKeyBtn = false;
    };

    function populateCurrentKeys() {

        url = "/websites/getSSHConfigs";

        var data = {
            domain: $("#domainName").text(),
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                $scope.records = JSON.parse(response.data.data);
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;
        }


    }

    populateCurrentKeys();

    $scope.deleteKey = function (key) {

        $scope.wpInstallLoading = false;

        url = "/websites/deleteSSHKey";

        var data = {
            domain: $("#domainName").text(),
            key: key,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.wpInstallLoading = true;
            if (response.data.delete_status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Key deleted successfully.',
                    type: 'success'
                });
                populateCurrentKeys();
            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.wpInstallLoading = true;
            new PNotify({
                title: 'Error!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });

        }


    }

    $scope.saveKey = function (key) {

        $scope.wpInstallLoading = false;

        url = "/websites/addSSHKey";

        var data = {
            domain: $("#domainName").text(),
            key: $scope.keyData,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.wpInstallLoading = true;
            if (response.data.add_status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Key added successfully.',
                    type: 'success'
                });
                populateCurrentKeys();
            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
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


    }


});


/* Java script code to cloneWebsite */
app.controller('cloneWebsite', function ($scope, $http, $timeout, $window) {

    $('form').submit(function (e) {
        e.preventDefault();
    });

    $scope.cyberpanelLoading = true;
    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.goBackDisable = true;

    $scope.cloneEnter = function ($event) {
        var keyCode = $event.which || $event.keyCode;
        if (keyCode === 13) {
            $scope.cyberpanelLoading = false;
            $scope.startCloning();
        }
    };

    var statusFile;

    $scope.startCloning = function () {

        $scope.cyberpanelLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.goBackDisable = true;

        $scope.currentStatus = "Cloning started..";

        url = "/websites/startCloning";


        var data = {
            masterDomain: $("#domainName").text(),
            domainName: $scope.domain

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                statusFile = response.data.tempStatusPath;
                getCreationStatus();
            } else {

                $scope.cyberpanelLoading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.goBackDisable = false;

                $scope.currentStatus = response.data.error_message;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.cyberpanelLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.goBackDisable = false;

        }

    };
    $scope.goBack = function () {
        $scope.cyberpanelLoading = true;
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getCreationStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.cyberpanelLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.goBackDisable = false;

                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.cyberpanelLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.goBackDisable = false;

                    $scope.currentStatus = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;
                $timeout(getCreationStatus, 1000);
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.cyberpanelLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.goBackDisable = false;

        }


    }

});
/* Java script code to cloneWebsite ends here */


/* Java script code to syncWebsite */
app.controller('syncWebsite', function ($scope, $http, $timeout, $window) {

    $scope.cyberpanelLoading = true;
    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.goBackDisable = true;

    var statusFile;

    $scope.startSyncing = function () {

        $scope.cyberpanelLoading = false;
        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.goBackDisable = true;

        $scope.currentStatus = "Cloning started..";

        url = "/websites/startSync";


        var data = {
            childDomain: $("#childDomain").text(),
            eraseCheck: $scope.eraseCheck,
            dbCheck: $scope.dbCheck,
            copyChanged: $scope.copyChanged

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                statusFile = response.data.tempStatusPath;
                getCreationStatus();
            } else {

                $scope.cyberpanelLoading = true;
                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.goBackDisable = false;

                $scope.currentStatus = response.data.error_message;
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.cyberpanelLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.goBackDisable = false;

        }

    };
    $scope.goBack = function () {
        $scope.cyberpanelLoading = true;
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getCreationStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.cyberpanelLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.goBackDisable = false;

                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.cyberpanelLoading = true;
                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.goBackDisable = false;

                    $scope.currentStatus = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";
                    $scope.goBackDisable = false;

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;
                $timeout(getCreationStatus, 1000);
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.cyberpanelLoading = true;
            $scope.installationDetailsForm = true;
            $scope.installationProgress = false;
            $scope.goBackDisable = false;

        }


    }

});
/* Java script code to syncWebsite ends here */


app.controller('installMagentoCTRL', function ($scope, $http, $timeout) {

    $scope.installationDetailsForm = false;
    $scope.installationProgress = true;
    $scope.installationFailed = true;
    $scope.installationSuccessfull = true;
    $scope.couldNotConnect = true;
    $scope.wpInstallLoading = true;
    $scope.goBackDisable = true;

    $scope.databasePrefix = 'ps_';

    var statusFile;
    var domain = $("#domainNamePage").text();
    var path;


    $scope.goBack = function () {
        $scope.installationDetailsForm = false;
        $scope.installationProgress = true;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = true;
        $scope.goBackDisable = true;
        $("#installProgress").css("width", "0%");
    };

    function getInstallStatus() {

        url = "/websites/installWordpressStatus";

        var data = {
            statusFile: statusFile,
            domainName: domain
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 1) {

                if (response.data.installStatus === 1) {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = true;
                    $scope.installationSuccessfull = false;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    if (typeof path !== 'undefined') {
                        $scope.installationURL = "http://" + domain + "/" + path;
                    } else {
                        $scope.installationURL = domain;
                    }


                    $("#installProgress").css("width", "100%");
                    $scope.installPercentage = "100";
                    $scope.currentStatus = response.data.currentStatus;
                    $timeout.cancel();

                } else {

                    $scope.installationDetailsForm = true;
                    $scope.installationProgress = false;
                    $scope.installationFailed = false;
                    $scope.installationSuccessfull = true;
                    $scope.couldNotConnect = true;
                    $scope.wpInstallLoading = true;
                    $scope.goBackDisable = false;

                    $scope.errorMessage = response.data.error_message;

                    $("#installProgress").css("width", "0%");
                    $scope.installPercentage = "0";

                }

            } else {
                $("#installProgress").css("width", response.data.installationProgress + "%");
                $scope.installPercentage = response.data.installationProgress;
                $scope.currentStatus = response.data.currentStatus;

                $timeout(getInstallStatus, 1000);


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.canNotFetch = true;
            $scope.couldNotConnect = false;


        }


    }

    $scope.installMagento = function () {

        $scope.installationDetailsForm = true;
        $scope.installationProgress = false;
        $scope.installationFailed = true;
        $scope.installationSuccessfull = true;
        $scope.couldNotConnect = true;
        $scope.wpInstallLoading = false;
        $scope.goBackDisable = true;
        $scope.currentStatus = "Starting installation..";

        path = $scope.installPath;


        url = "/websites/magentoInstall";

        var home = "1";

        if (typeof path !== 'undefined') {
            home = "0";
        }
        var sampleData;
        if ($scope.sampleData === true) {
            sampleData = 1;
        } else {
            sampleData = 0
        }


        var data = {
            domain: domain,
            home: home,
            path: path,
            firstName: $scope.firstName,
            lastName: $scope.lastName,
            username: $scope.username,
            email: $scope.email,
            passwordByPass: $scope.password,
            sampleData: sampleData
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.installStatus === 1) {
                statusFile = response.data.tempStatusPath;
                getInstallStatus();
            } else {

                $scope.installationDetailsForm = true;
                $scope.installationProgress = false;
                $scope.installationFailed = false;
                $scope.installationSuccessfull = true;
                $scope.couldNotConnect = true;
                $scope.wpInstallLoading = true;
                $scope.goBackDisable = false;

                $scope.errorMessage = response.data.error_message;

            }


        }

        function cantLoadInitialDatas(response) {
        }

    };


});

/* Java script code to git tracking */
app.controller('manageGIT', function ($scope, $http, $timeout, $window) {

    $scope.cyberpanelLoading = true;
    $scope.loadingSticks = true;
    $scope.gitTracking = true;
    $scope.gitEnable = true;
    $scope.statusBox = true;
    $scope.gitCommitsTable = true;

    var statusFile;

    $scope.fetchFolderDetails = function () {

        $scope.cyberpanelLoading = false;
        $scope.gitCommitsTable = true;

        url = "/websites/fetchFolderDetails";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder
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
                if (response.data.repo === 1) {
                    $scope.gitTracking = true;
                    $scope.gitEnable = false;
                    $scope.branches = response.data.finalBranches;
                    $scope.deploymentKey = response.data.deploymentKey;
                    $scope.remote = response.data.remote;
                    $scope.remoteResult = response.data.remoteResult;
                    $scope.totalCommits = response.data.totalCommits;
                    $scope.home = response.data.home;
                    $scope.webHookURL = response.data.webHookURL;
                    $scope.autoCommitCurrent = response.data.autoCommitCurrent;
                    $scope.autoPushCurrent = response.data.autoPushCurrent;
                    $scope.emailLogsCurrent = response.data.emailLogsCurrent;
                    document.getElementById("currentCommands").value = response.data.commands;
                    $scope.webhookCommandCurrent = response.data.webhookCommandCurrent;
                } else {
                    $scope.gitTracking = false;
                    $scope.gitEnable = true;
                    $scope.home = response.data.home;
                    $scope.deploymentKey = response.data.deploymentKey;
                }
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }

    };

    $scope.initRepo = function () {

        $scope.cyberpanelLoading = false;

        url = "/websites/initRepo";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder

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
                new PNotify({
                    title: 'Success',
                    text: 'Repo initiated.',
                    type: 'success'
                });
                $scope.fetchFolderDetails();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }

    };

    $scope.setupRemote = function () {

        $scope.cyberpanelLoading = false;

        url = "/websites/setupRemote";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder,
            gitHost: $scope.gitHost,
            gitUsername: $scope.gitUsername,
            gitReponame: $scope.gitReponame,
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
                new PNotify({
                    title: 'Success',
                    text: 'Remote successfully set.',
                    type: 'success'
                });
                $scope.fetchFolderDetails();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }

    };

    var changeBranch = 0;

    $scope.changeBranch = function () {

        if (changeBranch === 1) {
            changeBranch = 0;
            return 0;
        }

        $scope.loadingSticks = false;
        $("#showStatus").modal();

        url = "/websites/changeGitBranch";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder,
            branchName: $scope.branchName

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.loadingSticks = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Changes applied.',
                    type: 'success'
                });
                $scope.commandStatus = response.data.commandStatus;
                $timeout(function () {
                    $window.location.reload();
                }, 3000);
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
                $scope.commandStatus = response.data.commandStatus;
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.loadingSticks = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    };

    $scope.createNewBranch = function () {
        $scope.cyberpanelLoading = false;
        $scope.commandStatus = "";
        $scope.statusBox = false;
        changeBranch = 1;

        url = "/websites/createNewBranch";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder,
            newBranchName: $scope.newBranchName

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
                new PNotify({
                    title: 'Success',
                    text: 'Changes applied.',
                    type: 'success'
                });
                $scope.commandStatus = response.data.commandStatus;
                $scope.fetchFolderDetails();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
                $scope.commandStatus = response.data.commandStatus;
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = false;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    };

    $scope.commitChanges = function () {
        $scope.cyberpanelLoading = false;
        $scope.commandStatus = "";
        $scope.statusBox = false;

        url = "/websites/commitChanges";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder,
            commitMessage: $scope.commitMessage

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
                new PNotify({
                    title: 'Success',
                    text: 'Changes applied.',
                    type: 'success'
                });
                $scope.commandStatus = response.data.commandStatus;
                $scope.fetchFolderDetails();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
                $scope.commandStatus = response.data.commandStatus;
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = false;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    };

    $scope.gitPull = function () {

        $scope.loadingSticks = false;
        $("#showStatus").modal();

        url = "/websites/gitPull";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.loadingSticks = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Changes applied.',
                    type: 'success'
                });
                $scope.commandStatus = response.data.commandStatus;
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
                $scope.commandStatus = response.data.commandStatus;
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.loadingSticks = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    };

    $scope.gitPush = function () {

        $scope.loadingSticks = false;
        $("#showStatus").modal();

        url = "/websites/gitPush";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.loadingSticks = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Changes applied.',
                    type: 'success'
                });
                $scope.commandStatus = response.data.commandStatus;
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
                $scope.commandStatus = response.data.commandStatus;
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.loadingSticks = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    };

    $scope.attachRepoGIT = function () {
        $scope.cyberpanelLoading = false;
        $scope.commandStatus = "";
        $scope.statusBox = false;

        url = "/websites/attachRepoGIT";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder,
            gitHost: $scope.gitHost,
            gitUsername: $scope.gitUsername,
            gitReponame: $scope.gitReponame,
            overrideData: $scope.overrideData
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
                new PNotify({
                    title: 'Success',
                    text: 'Changes applied.',
                    type: 'success'
                });
                $scope.commandStatus = response.data.commandStatus;
                $scope.fetchFolderDetails();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
                $scope.commandStatus = response.data.commandStatus;
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = false;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    };

    $scope.removeTracking = function () {

        $scope.cyberpanelLoading = false;

        url = "/websites/removeTracking";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder
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
                new PNotify({
                    title: 'Success',
                    text: 'Changes applied.',
                    type: 'success'
                });
                $scope.fetchFolderDetails();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    };

    $scope.fetchGitignore = function () {

        $scope.cyberpanelLoading = false;

        url = "/websites/fetchGitignore";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder
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
                new PNotify({
                    title: 'Success',
                    text: 'Successfully fetched.',
                    type: 'success'
                });
                $scope.gitIgnoreContent = response.data.gitIgnoreContent;
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    };

    $scope.saveGitIgnore = function () {

        $scope.cyberpanelLoading = false;

        url = "/websites/saveGitIgnore";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder,
            gitIgnoreContent: $scope.gitIgnoreContent

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
                new PNotify({
                    title: 'Success',
                    text: 'Successfully saved.',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    };

    $scope.fetchCommits = function () {

        $scope.cyberpanelLoading = false;

        url = "/websites/fetchCommits";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            $scope.gitCommitsTable = false;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Successfully fetched.',
                    type: 'success'
                });
                $scope.commits = JSON.parse(response.data.commits);
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    };

    var currentComit;
    var fetchFileCheck = 0;
    var initial = 1;

    $scope.fetchFiles = function (commit) {

        currentComit = commit;
        $scope.cyberpanelLoading = false;

        if (initial === 1) {
            initial = 0;
        } else {
            fetchFileCheck = 1;
        }

        url = "/websites/fetchFiles";


        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder,
            commit: commit
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            $scope.gitCommitsTable = false;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Successfully fetched.',
                    type: 'success'
                });
                $scope.files = response.data.files;
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }


        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    };

    $scope.fileStatus = true;

    $scope.fetchChangesInFile = function () {
        $scope.fileStatus = true;

        if (fetchFileCheck === 1) {
            fetchFileCheck = 0;
            return 0;
        }

        $scope.cyberpanelLoading = false;
        $scope.currentSelectedFile = $scope.changeFile;

        url = "/websites/fetchChangesInFile";

        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder,
            file: $scope.changeFile,
            commit: currentComit
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
                new PNotify({
                    title: 'Success',
                    text: 'Successfully fetched.',
                    type: 'success'
                });
                $scope.fileStatus = false;
                document.getElementById("fileChangedContent").innerHTML = response.data.fileChangedContent;
            } else {
                $scope.fileStatus = true;
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    };

    $scope.saveGitConfigurations = function () {

        $scope.cyberpanelLoading = false;

        url = "/websites/saveGitConfigurations";

        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder,
            autoCommit: $scope.autoCommit,
            autoPush: $scope.autoPush,
            emailLogs: $scope.emailLogs,
            commands: document.getElementById("currentCommands").value,
            webhookCommand: $scope.webhookCommand
        };

        if ($scope.autoCommit === undefined) {
            $scope.autoCommitCurrent = 'Never';
        } else {
            $scope.autoCommitCurrent = $scope.autoCommit;
        }

        if ($scope.autoPush === undefined) {
            $scope.autoPushCurrent = 'Never';
        } else {
            $scope.autoPushCurrent = $scope.autoPush;
        }

        if ($scope.emailLogs === undefined) {
            $scope.emailLogsCurrent = false;
        } else {
            $scope.emailLogsCurrent = $scope.emailLogs;
        }

        if ($scope.webhookCommand === undefined) {
            $scope.webhookCommandCurrent = false;
        } else {
            $scope.webhookCommandCurrent = $scope.webhookCommand;
        }

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Successfully saved.',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }
    };

    $scope.currentPage = 1;
    $scope.recordsToShow = 10;

    $scope.fetchGitLogs = function () {
        $scope.cyberpanelLoading = false;
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        var data = {
            domain: $("#domain").text(),
            folder: $scope.folder,
            page: $scope.currentPage,
            recordsToShow: $scope.recordsToShow
        };


        dataurl = "/websites/fetchGitLogs";

        $http.post(dataurl, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            if (response.data.status === 1) {
                new PNotify({
                    title: 'Success',
                    text: 'Successfully fetched.',
                    type: 'success'
                });
                $scope.logs = JSON.parse(response.data.logs);
                $scope.pagination = response.data.pagination;
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }


    };

});

/* Java script code to git tracking ends here */
