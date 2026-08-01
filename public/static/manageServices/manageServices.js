/**
 * Created by usman on 6/22/18.
 */

/* Java script code */

app.controller('powerDNS', function ($scope, $http, $timeout, $window) {

    $scope.pdnsLoading = true;
    $scope.failedToFetch = true;
    $scope.couldNotConnect = true;
    $scope.changesApplied = true;
    $scope.slaveIPs = true;
    $scope.masterServerHD = true;
    $scope.pdnsEnabled = false;
    if (!$scope.dnsMode) {
        $scope.dnsMode = 'Default';
    }

    $scope.pdnsToggleChanged = function () {
        // ng-model already synced; keep for future hooks
    };

    fetchPDNSStatus('powerdns');

    function fetchPDNSStatus(service) {

        $scope.pdnsLoading = false;
        $scope.pdnsEnabled = false;

        url = "/manageservices/fetchStatus";

        var data = {
            'service': service
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.pdnsLoading = true;

            if (response.data.status === 1) {

                $scope.pdnsEnabled = (response.data.installCheck === 1 || response.data.installCheck === '1' || response.data.installCheck === true);
                if (response.data.dnsMode) {
                    $scope.dnsMode = response.data.dnsMode;
                }
                $scope.modeChange();
                $scope.slaveIPData = response.data.slaveIPData;

            } else {
                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.pdnsLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }

    }

    $scope.saveStatus = function (service) {

        $scope.pdnsLoading = false;
        $scope.failedToFetch = true;
        $scope.couldNotConnect = true;
        $scope.changesApplied = true;


        url = "/manageservices/saveStatus";

        if (service === 'powerdns') {
            var data = {
                status: !!$scope.pdnsEnabled,
                service: service,
                dnsMode: $scope.dnsMode,
                slaveServerNS: $scope.slaveServerNS,
                masterServerIP: $scope.masterServerIP,
                slaveServer: $scope.slaveServer,
                slaveServerIP: $scope.slaveServerIP,
                slaveServer2: $scope.slaveServer2,
                slaveServerIP2: $scope.slaveServerIP2,
                slaveServer3: $scope.slaveServer3,
                slaveServerIP3: $scope.slaveServerIP3,
            };
        } else {
            var data = {
                status: !!$scope.pdnsEnabled,
                service: service
            };
        }

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.pdnsLoading = true;

            if (response.data.status === 1) {

                $scope.failedToFetch = true;
                $scope.couldNotConnect = true;
                $scope.changesApplied = false;

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.policyServerLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }


    };

    $scope.modeChange = function () {
        if ($scope.dnsMode === 'MASTER') {
            $scope.slaveIPs = false;
            $scope.masterServerHD = true;

        } else if ($scope.dnsMode == 'SLAVE') {
            $scope.slaveIPs = true;
            $scope.masterServerHD = false;
        } else {
            $scope.slaveIPs = true;
            $scope.masterServerHD = true;
        }
    }

});

/* Java script code */

/* Java script code */

app.controller('postfix', function ($scope, $http, $timeout, $window) {

    $scope.serviceLoading = true;
    $scope.failedToFetch = true;
    $scope.couldNotConnect = true;
    $scope.changesApplied = true;


    var serviceStatus = false;


    $('#serviceStatus').change(function () {
        serviceStatus = $(this).prop('checked');
    });

    fetchPDNSStatus('postfix');

    function fetchPDNSStatus(service) {

        $scope.serviceLoading = false;

        $('#serviceStatus').bootstrapToggle('off');

        url = "/manageservices/fetchStatus";

        var data = {
            'service': service
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.serviceLoading = true;

            if (response.data.status === 1) {

                if (response.data.installCheck === 1) {
                    $('#serviceStatus').bootstrapToggle('on');
                }

            } else {
                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.serviceLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }

    }


    $scope.saveStatus = function (service) {

        $scope.serviceLoading = false;
        $scope.failedToFetch = true;
        $scope.couldNotConnect = true;
        $scope.changesApplied = true;


        url = "/manageservices/saveStatus";

        var data = {
            status: serviceStatus,
            service: service
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.serviceLoading = true;

            if (response.data.status === 1) {

                $scope.failedToFetch = true;
                $scope.couldNotConnect = true;
                $scope.changesApplied = false;

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.serviceLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }


    };

});

/* Java script code */

/* Java script code */

app.controller('pureFTPD', function ($scope, $http, $timeout, $window) {

    $scope.serviceLoading = true;
    $scope.failedToFetch = true;
    $scope.couldNotConnect = true;
    $scope.changesApplied = true;


    var serviceStatus = false;


    $('#serviceStatus').change(function () {
        serviceStatus = $(this).prop('checked');
    });

    fetchPDNSStatus('pureftpd');

    function fetchPDNSStatus(service) {

        $scope.serviceLoading = false;

        $('#serviceStatus').bootstrapToggle('off');

        url = "/manageservices/fetchStatus";

        var data = {
            'service': service
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.serviceLoading = true;

            if (response.data.status === 1) {

                if (response.data.installCheck === 1) {
                    $('#serviceStatus').bootstrapToggle('on');
                }

            } else {
                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;

                $scope.errorMessage = response.data.error_message;

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.serviceLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }

    }


    $scope.saveStatus = function (service) {

        $scope.serviceLoading = false;
        $scope.failedToFetch = true;
        $scope.couldNotConnect = true;
        $scope.changesApplied = true;


        url = "/manageservices/saveStatus";

        var data = {
            status: serviceStatus,
            service: service
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            $scope.serviceLoading = true;

            if (response.data.status === 1) {

                $scope.failedToFetch = true;
                $scope.couldNotConnect = true;
                $scope.changesApplied = false;

            } else {
                $scope.errorMessage = response.data.error_message;

                $scope.failedToFetch = false;
                $scope.couldNotConnect = true;
                $scope.changesApplied = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.serviceLoading = true;
            $scope.failedToFetch = true;
            $scope.couldNotConnect = false;
            $scope.changesApplied = true;
        }


    };

});

/* Java script code */

/* Java script code */

app.controller('manageApplications', function ($scope, $http, $timeout, $window) {

    /**
     * Normalize entries from applicationMeta (strings, numbers, or rare object shapes)
     * so version pickers never show blank rows. CyberPanel uses {$ ... $} interpolation
     * in templates; list labels use versionLabel() for consistent display.
     */
    function normalizeVersionToken(v) {
        if (v === null || v === undefined) {
            return '';
        }
        if (v === 'latest') {
            return 'latest';
        }
        if (typeof v === 'number' && isFinite(v)) {
            return String(v);
        }
        if (angular.isObject(v)) {
            var o = v;
            var cand = o.version || o.Version || o.value || o.name || o.ver || o.label;
            if (cand !== undefined && cand !== null) {
                return String(cand).trim();
            }
            try {
                return JSON.stringify(o);
            } catch (ignore) {
                return '';
            }
        }
        return String(v).trim();
    }

    function sanitizeVersionsArray(vers) {
        if (!angular.isArray(vers)) {
            return [];
        }
        var out = [];
        var seen = {};
        vers.forEach(function (raw) {
            var t = normalizeVersionToken(raw);
            if (!t || t === 'latest') {
                return;
            }
            if (!seen[t]) {
                seen[t] = true;
                out.push(t);
            }
        });
        return out;
    }

    function versionMatchesRabbitmqStream(ver, stream) {
        var s = String(stream || '4').trim();
        var t = normalizeVersionToken(ver);
        if (!t || t === 'latest') {
            return false;
        }
        var m = /^(\d+)\./.exec(t);
        return !!(m && m[1] === s);
    }

    function versionMatchesEsMajor(ver, major) {
        var mjr = String(major || '8').trim();
        var t = normalizeVersionToken(ver);
        if (!t || t === 'latest') {
            return false;
        }
        var m = /^(\d+)\./.exec(t);
        return !!(m && m[1] === mjr);
    }

    $scope.versionLabel = function (v) {
        if (v === 'latest') {
            return 'latest';
        }
        var t = normalizeVersionToken(v);
        return t || '(unknown)';
    };

    $scope.versionTrackId = function (idx, v) {
        return String(idx) + '|' + $scope.versionLabel(v);
    };

    /* false = long-running install/remove/poll (show spinners); true = idle */
    $scope.cyberpanelLoading = true;
    /** Background applicationMeta refresh — separate from cyberpanelLoading so the page does not “freeze” on every modal open. */
    $scope.appsMetaRefreshing = false;
    $scope.apps = [
        {name: 'Elasticsearch', image: '/static/manageServices/images/elastic-search.png'},
        {name: 'Redis', image: '/static/manageServices/images/redis.png'},
        {name: 'RabbitMQ', image: '/static/manageServices/images/rabbitmq-logo.svg'}
    ];

    (function mergeMetaBootstrap() {
        var el = document.getElementById('manageApplicationsMetaBootstrap');
        if (!el || !el.textContent) {
            return;
        }
        var raw = el.textContent.trim();
        if (!raw) {
            return;
        }
        try {
            var boot = JSON.parse(raw);
            if (!boot || Number(boot.status) !== 1) {
                return;
            }
            var appMap = {};
            (boot.apps || []).forEach(function (a) {
                if (a && a.name) {
                    appMap[a.name] = a;
                }
            });
            $scope.apps = $scope.apps.map(function (baseApp) {
                var meta = appMap[baseApp.name] || {};
                var vers = meta.versions;
                if (!angular.isArray(vers)) {
                    vers = [];
                }
                vers = sanitizeVersionsArray(vers);
                return {
                    name: baseApp.name,
                    image: baseApp.image,
                    installed: !!meta.installed,
                    installedVersion: meta.installedVersion || '',
                    updateAvailable: !!meta.updateAvailable,
                    crossBranchUpdateSuggested: !!meta.crossBranchUpdateSuggested,
                    versions: vers,
                    latestAvailable: meta.latestAvailable || '',
                    latestOverall: meta.latestOverall || '',
                    rabbitmqVersionsHint: meta.rabbitmqVersionsHint || ''
                };
            });
        } catch (ignore) {
            /* keep bare apps list */
        }
    })();

    $scope.selectedVersion = 'latest';
    /** Row highlight uses $index so only one row looks selected (avoids sticky :focus / repeater quirks). */
    $scope.selectedVersionRowIndex = 0;
    $scope.selectedVersions = ['latest'];

    $scope.recalcSelectedVersionRowIndex = function () {
        var list = $scope.selectedVersions || [];
        var sel = $scope.selectedVersion;
        var i = list.indexOf(sel);
        if (i < 0) {
            var normSel = normalizeVersionToken(sel);
            if (normSel) {
                for (var j = 0; j < list.length; j += 1) {
                    if (normalizeVersionToken(list[j]) === normSel) {
                        i = j;
                        $scope.selectedVersion = list[j];
                        break;
                    }
                }
            }
        }
        $scope.selectedVersionRowIndex = (i >= 0) ? i : 0;
    };

    $scope.selectManagedAppVersion = function (idx, v, $event) {
        var n = (typeof idx === 'number') ? idx : parseInt(idx, 10);
        if (!isFinite(n) || n < 0) {
            n = 0;
        }
        $scope.selectedVersionRowIndex = n;
        $scope.selectedVersion = v;
        if ($event && $event.target && typeof $event.target.blur === 'function') {
            $event.target.blur();
        } else if (typeof document !== 'undefined' && document.activeElement && typeof document.activeElement.blur === 'function') {
            document.activeElement.blur();
        }
    };
    $scope.selectedEsMajor = '8';
    $scope.selectedRabbitmqStream = '4';
    /** RabbitMQ: 4.x is default for new installs (metadata prefetched). Upgrade may require picking stream if version line is unknown. ES major still user-picked before version list loads. */
    $scope.rabbitmqBranchChosen = false;
    $scope.esMajorChosen = false;
    $scope.confirmAction = false;
    $scope.selectedCurrentVersion = '';

    $scope.chooseRabbitmqStream = function (stream) {
        var s = String(stream || '4').trim();
        if (s !== '3' && s !== '4') {
            s = '4';
        }
        $scope.selectedRabbitmqStream = s;
        $scope.rabbitmqBranchChosen = true;
        $scope.refreshMeta();
    };

    $scope.chooseEsMajor = function (major) {
        var m = String(major || '8').trim();
        if (m !== '7' && m !== '8' && m !== '9') {
            m = '8';
        }
        $scope.selectedEsMajor = m;
        $scope.esMajorChosen = true;
        $scope.refreshMeta();
    };

    /**
     * When the install/upgrade modal is open, re-apply version list from latest applicationMeta.
     * (Page-load meta can be empty for ES if dnf was slow; opening the modal must refetch.)
     */
    $scope.syncModalVersionLists = function () {
        if (!$scope.appName || ($scope.status !== 'Installing' && $scope.status !== 'Upgrading')) {
            return;
        }
        if ($scope.appName !== 'Elasticsearch' && $scope.appName !== 'Redis' && $scope.appName !== 'RabbitMQ') {
            return;
        }
        if ($scope.appName === 'RabbitMQ' && !$scope.rabbitmqBranchChosen) {
            $scope.selectedVersions = ['latest'];
            $scope.selectedVersion = 'latest';
            $scope.repoShowsOnlyOneStream = false;
            $scope.recalcSelectedVersionRowIndex();
            return;
        }
        if ($scope.appName === 'Elasticsearch' && !$scope.esMajorChosen) {
            $scope.selectedVersions = ['latest'];
            $scope.selectedVersion = 'latest';
            $scope.repoShowsOnlyOneStream = false;
            $scope.recalcSelectedVersionRowIndex();
            return;
        }
        var meta = $scope.findAppMeta($scope.appName);
        var vers = sanitizeVersionsArray((meta && meta.versions) ? meta.versions : []);
        $scope.selectedVersions = ['latest'].concat(vers);
        var curRaw = (meta && meta.installedVersion) ? meta.installedVersion : ($scope.selectedCurrentVersion || '');
        var cur = normalizeVersionToken(curRaw) || String(curRaw || '').trim();
        if (cur && $scope.selectedVersions.indexOf(cur) === -1) {
            var allowCur = true;
            if ($scope.appName === 'RabbitMQ') {
                allowCur = versionMatchesRabbitmqStream(cur, $scope.selectedRabbitmqStream);
            } else if ($scope.appName === 'Elasticsearch') {
                allowCur = versionMatchesEsMajor(cur, $scope.selectedEsMajor);
            }
            if (allowCur) {
                $scope.selectedVersions.push(cur);
            }
        }
        if (cur) {
            $scope.selectedCurrentVersion = cur;
        }
        var prevSel = $scope.selectedVersion;
        if (prevSel && $scope.selectedVersions.indexOf(prevSel) !== -1) {
            $scope.selectedVersion = prevSel;
        } else {
            $scope.selectedVersion = 'latest';
        }
        var realVers = ($scope.selectedVersions || []).filter(function (v) {
            return v && v !== 'latest';
        });
        $scope.repoShowsOnlyOneStream = ($scope.status === 'Upgrading' && realVers.length <= 1);
        $scope.recalcSelectedVersionRowIndex();
    };

    $scope.refreshMeta = function () {
        $scope.appsMetaRefreshing = true;
        var url = "/manageservices/applicationMeta";
        var data = {
            esMajor: $scope.selectedEsMajor,
            rabbitmqStream: $scope.selectedRabbitmqStream
        };
        var config = {
            headers: {
                'Content-Type': 'application/json;charset=UTF-8',
                'X-CSRFToken': getCookie('csrftoken')
            },
            transformRequest: function (payload) {
                return angular.toJson(payload);
            }
        };

        return $http.post(url, data, config).then(function (response) {
            $scope.appsMetaRefreshing = false;
            var payload = response.data;
            var ok = payload && (payload.status === 1 || payload.status === '1');
            if (ok) {
                var appMap = {};
                (payload.apps || []).forEach(function (app) {
                    appMap[app.name] = app;
                });
                var esMetaResp = appMap['Elasticsearch'];
                var rmqMetaResp = appMap['RabbitMQ'];
                var respEsMaj = String(esMetaResp && esMetaResp.major != null ? esMetaResp.major : '').trim();
                if (respEsMaj && respEsMaj !== String($scope.selectedEsMajor || '8').trim()) {
                    return;
                }
                var respRmqStream = String(rmqMetaResp && rmqMetaResp.rabbitmqStream != null ? rmqMetaResp.rabbitmqStream : '').trim();
                if (respRmqStream && respRmqStream !== String($scope.selectedRabbitmqStream || '4').trim()) {
                    return;
                }
                $scope.apps = $scope.apps.map(function (baseApp) {
                    var meta = appMap[baseApp.name] || {};
                    var vers = meta.versions;
                    if (!angular.isArray(vers)) {
                        vers = [];
                    }
                    vers = sanitizeVersionsArray(vers);
                    return {
                        name: baseApp.name,
                        image: baseApp.image,
                        installed: !!meta.installed,
                        installedVersion: meta.installedVersion || '',
                        updateAvailable: !!meta.updateAvailable,
                        crossBranchUpdateSuggested: !!meta.crossBranchUpdateSuggested,
                        versions: vers,
                        latestAvailable: meta.latestAvailable || '',
                        latestOverall: meta.latestOverall || '',
                        rabbitmqVersionsHint: meta.rabbitmqVersionsHint || ''
                    };
                });
                $scope.syncModalVersionLists();
            } else {
                new PNotify({
                    title: 'Operation Failed!',
                    text: (payload && (payload.error_message || payload.errorMessage)) || 'Could not load application metadata.',
                    type: 'error'
                });
            }
        }, function () {
            $scope.appsMetaRefreshing = false;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        });
    };

    $scope.prepareAction = function (service, status, bootstrapInstalledVersion) {
        if (bootstrapInstalledVersion === undefined || bootstrapInstalledVersion === null) {
            bootstrapInstalledVersion = '';
        } else {
            bootstrapInstalledVersion = String(bootstrapInstalledVersion).trim();
        }
        $scope.status = status;
        $scope.appName = service.name;
        $scope.confirmAction = false;
        var effectiveInstalled = (service.installedVersion || bootstrapInstalledVersion || '').trim();
        $scope.selectedCurrentVersion = effectiveInstalled;

        if (service.name === 'RabbitMQ') {
            if (effectiveInstalled && /^4\./.test(effectiveInstalled)) {
                $scope.selectedRabbitmqStream = '4';
            } else if (effectiveInstalled && /^3\./.test(effectiveInstalled)) {
                $scope.selectedRabbitmqStream = '3';
            } else if (status === 'Installing') {
                $scope.selectedRabbitmqStream = '4';
            }
            if (status === 'Upgrading' && effectiveInstalled) {
                if (/^4\./.test(effectiveInstalled) || /^3\./.test(effectiveInstalled)) {
                    $scope.rabbitmqBranchChosen = true;
                }
            }
        }

        if (service.name === 'Elasticsearch' && effectiveInstalled) {
            var iv = effectiveInstalled;
            if (/^9\./.test(iv)) {
                $scope.selectedEsMajor = '9';
            } else if (/^8\./.test(iv)) {
                $scope.selectedEsMajor = '8';
            } else if (/^7\./.test(iv)) {
                $scope.selectedEsMajor = '7';
            }
        }

        $scope.selectedVersions = ['latest'];
        // RabbitMQ upgrade: bootstrap meta is often stream 4; stream follows installed line — do not
        // reuse service.versions until refreshMeta returns for selectedRabbitmqStream (avoids mismatched list).
        var deferVersionList = (service.name === 'RabbitMQ' && (!$scope.rabbitmqBranchChosen || status === 'Upgrading'))
            || (service.name === 'Elasticsearch' && !$scope.esMajorChosen);
        if (!deferVersionList) {
            var svcVers = sanitizeVersionsArray(service.versions || []);
            if (svcVers.length > 0) {
                $scope.selectedVersions = ['latest'].concat(svcVers);
            }
            var curPick = normalizeVersionToken(effectiveInstalled) || effectiveInstalled;
            if (curPick && $scope.selectedVersions.indexOf(curPick) === -1) {
                $scope.selectedVersions.push(curPick);
            }
        }
        $scope.selectedVersion = 'latest';
        $scope.requestData = '';

        var realVers = ($scope.selectedVersions || []).filter(function (v) {
            return v && v !== 'latest';
        });
        if (deferVersionList) {
            $scope.repoShowsOnlyOneStream = false;
        } else {
            $scope.repoShowsOnlyOneStream = ($scope.status === 'Upgrading' && realVers.length <= 1);
        }
        $scope.recalcSelectedVersionRowIndex();
    };

    $scope.findAppMeta = function (appName) {
        var found = null;
        ($scope.apps || []).forEach(function (item) {
            if (item.name === appName) {
                found = item;
            }
        });
        return found || {};
    };

    $scope.prepareActionByName = function (appName, status, bootstrapInstalledVersion) {
        var meta = $scope.findAppMeta(appName);
        if (!meta.name) {
            meta = {name: appName, versions: []};
        }
        var mver = meta.versions;
        if (!angular.isArray(mver)) {
            mver = [];
        }
        var merged = {
            name: meta.name,
            image: meta.image,
            installed: meta.installed,
            installedVersion: meta.installedVersion || '',
            versions: mver
        };
        $scope.prepareAction(merged, status, bootstrapInstalledVersion);
    };

    /**
     * Prepare scope then show modal (do not use data-toggle + ng-click — Bootstrap can
     * open the dialog before Angular runs ng-click, leaving status/appName unset).
     * For managed apps, wait for applicationMeta so version lists and installedVersion are correct (upgrade vs downgrade).
     */
    $scope.openApplicationsModal = function (appName, status, bootstrapInstalledVersion) {
        var needMeta = (appName === 'RabbitMQ' || appName === 'Elasticsearch' || appName === 'Redis');
        var showModal = function () {
            if (typeof window.jQuery !== 'undefined' && jQuery('#settings').modal) {
                jQuery('#settings').modal('show');
            }
        };
        if (needMeta) {
            if (appName === 'RabbitMQ') {
                if (status === 'Installing') {
                    $scope.selectedRabbitmqStream = '4';
                    $scope.rabbitmqBranchChosen = true;
                } else {
                    $scope.rabbitmqBranchChosen = false;
                }
            }
            if (appName === 'Elasticsearch') {
                $scope.esMajorChosen = false;
            }
            // RabbitMQ install: default 4.x stream and prefetch metadata. Upgrade: pick stream from installed version.
            // Elasticsearch: still wait for user major. Redis refreshes on open.
            $scope.appName = appName;
            $scope.status = status;
            $scope.prepareActionByName(appName, status, bootstrapInstalledVersion);
            showModal();
            if (appName === 'Redis' || (appName === 'RabbitMQ' && $scope.rabbitmqBranchChosen)) {
                $timeout(function () {
                    $scope.refreshMeta();
                }, 0);
            }
        } else {
            $scope.prepareActionByName(appName, status, bootstrapInstalledVersion);
            showModal();
        }
    };

    $scope.runAction = function () {
        var appName = $scope.appName;
        var status = $scope.status;
        if (!appName || !status) {
            return;
        }
        if ((status === 'Removing' || status === 'Upgrading') && !$scope.confirmAction) {
            new PNotify({
                title: 'Confirmation Required',
                text: 'Please confirm this action before proceeding.',
                type: 'warning'
            });
            return;
        }
        if (appName === 'RabbitMQ' && (status === 'Installing' || status === 'Upgrading') && !$scope.rabbitmqBranchChosen) {
            new PNotify({
                title: 'Stream required',
                text: 'Choose RabbitMQ 4.x or 3.x above to load versions for that line.',
                type: 'warning'
            });
            return;
        }
        if (appName === 'Elasticsearch' && (status === 'Installing' || status === 'Upgrading') && !$scope.esMajorChosen) {
            new PNotify({
                title: 'Major version required',
                text: 'Choose Elasticsearch major (7, 8, or 9) above to load versions for that line.',
                type: 'warning'
            });
            return;
        }
        $scope.status = status;
        $scope.appName = appName;

        $scope.cyberpanelLoading = false;

        url = "/manageservices/removeInstall";

        var data = {
            appName: appName,
            status: status,
            version: $scope.selectedVersion || 'latest',
            esMajor: $scope.selectedEsMajor || '8',
            rabbitmqStream: $scope.selectedRabbitmqStream || '4',
            confirmAction: $scope.confirmAction === true
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
                getRequestStatus();
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
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };

    function getRequestStatus() {
        $scope.cyberpanelLoading = false;

        url = "/serverstatus/switchTOLSWSStatus";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            if (response.data.abort === 0) {
                $scope.requestData = response.data.requestStatus;
                $timeout(getRequestStatus, 1000);
            } else {
                // Notifications
                $timeout.cancel();
                $scope.requestData = response.data.requestStatus;
                if (response.data.installed === 1) {
                    $timeout(function () {
                        $window.location.reload();
                    }, 3000);
                }

            }
        }

        function cantLoadInitialDatas(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    }

    // Do not fetch package metadata on page load; it can block workers under DNF load.
    // Metadata is fetched on-demand when opening install/version-change modals.

    if (typeof window.jQuery !== 'undefined' && jQuery.fn.on) {
        jQuery('#settings').on('hidden.bs.modal', function () {
            $scope.$evalAsync(function () {
                $scope.rabbitmqBranchChosen = false;
                $scope.esMajorChosen = false;
            });
        });
    }

});

/* Java script code */