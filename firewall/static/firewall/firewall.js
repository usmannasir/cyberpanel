/**
 * Created by usman on 9/5/17.
 */

// Helper function to get CSRF token cookie
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Confirm destructive firewall actions.
 * Prefers PNotify confirm (Docker Manager pattern); falls back to window.confirm.
 */
function firewallConfirmDelete(title, text, onConfirm) {
    var msg = text || 'Are you sure?';
    if (typeof PNotify !== 'undefined') {
        try {
            (new PNotify({
                title: title || 'Confirmation Needed',
                text: msg,
                icon: 'fa fa-question-circle',
                hide: false,
                confirm: {
                    confirm: true
                },
                buttons: {
                    closer: false,
                    sticker: false
                },
                history: {
                    history: false
                }
            })).get().on('pnotify.confirm', function () {
                if (typeof onConfirm === 'function') {
                    onConfirm();
                }
            });
            return;
        } catch (e) {
            /* fall through to window.confirm */
        }
    }
    if (window.confirm(msg) && typeof onConfirm === 'function') {
        onConfirm();
    }
}

/* Java script code to ADD Firewall Rules */

app.controller('firewallController', function ($scope, $http, $timeout) {

    $scope.rulesLoading = true;
    /** Incremented on each rules fetch; stale HTTP responses must not touch rulesLoading. */
    var rulesFetchGen = 0;
    $scope.actionFailed = true;
    $scope.actionSuccess = true;
    $scope.showExportFormatModal = false;
    $scope.showImportFormatModal = false;
    $scope.exportRulesFormat = 'json';
    $scope.importRulesFormat = 'json';
    $scope.showModifyRuleModal = false;
    $scope.modifyRuleData = { id: null, name: '', proto: 'tcp', port: '', ruleIP: '0.0.0.0/0' };

    $scope.canNotAddRule = true;
    $scope.ruleAdded = true;
    $scope.couldNotConnect = true;
    $scope.rulesDetails = false;

    // Initialize rules array - prevents "Cannot read 'length' of undefined" when template evaluates rules.length before API loads
    $scope.rules = [];
    // Banned IPs variables – tab from hash so we stay on /firewall/ (avoids 404 on servers without /firewall/firewall-rules/)
    /* Use window.location.hash only. Angular $location can disagree with the fragment on /firewall/#… and wrongly map to "rules". */
    function tabFromHash() {
        var h = String(window.location.hash || '').replace(/^#/, '').toLowerCase();
        if (h === 'banned-ips' || h === 'banned') return 'banned';
        if (h === 'trusted-ips' || h === 'ssh-whitelist') return 'trusted';
        return 'rules';
    }
    $scope.activeTab = tabFromHash();
    $scope.bannedIPs = [];  // Initialize as empty array

    // Re-apply tab from hash after load (hash can be set after controller init in some browsers)
    function applyTabFromHash() {
        var tab = tabFromHash();
        if ($scope.activeTab !== tab) {
            $scope.activeTab = tab;
            if (tab === 'banned') { populateBannedIPs(); }
            else if (tab === 'trusted') { populateTrustedSSHWhitelist(); }
            else { populateCurrentRecords(); }
            if (!$scope.$$phase && !$scope.$root.$$phase) { $scope.$apply(); }
        }
    }
    $timeout(applyTabFromHash, 0);
    if (document.readyState === 'complete') {
        $timeout(applyTabFromHash, 50);
    } else {
        window.addEventListener('load', function() { $timeout(applyTabFromHash, 0); });
    }

    // Sync tab with hash and load that tab's data on switch (single source of truth from ng-click).
    $scope.setFirewallTab = function(tab, $event) {
        if ($event) {
            try {
                $event.stopPropagation();
            } catch (ignoreErr) {}
        }
        $timeout(function() {
            $scope.activeTab = tab;
            function setHashIfNeeded(frag) {
                try {
                    if ((window.location.hash || '') === frag) {
                        return;
                    }
                    var path = window.location.pathname + window.location.search + frag;
                    if (window.history && typeof window.history.replaceState === 'function') {
                        window.history.replaceState(null, '', path);
                    } else {
                        window.location.hash = frag;
                    }
                } catch (ignoreHash) {}
            }
            if (tab === 'banned') {
                setHashIfNeeded('#banned-ips');
                populateBannedIPs();
            } else if (tab === 'trusted') {
                setHashIfNeeded('#trusted-ips');
                populateTrustedSSHWhitelist();
            } else {
                setHashIfNeeded('#rules');
                populateCurrentRecords();
            }
        }, 0);
    };

    function syncTabFromHash() {
        var tab = tabFromHash();
        $scope.$evalAsync(function() {
            if ($scope.activeTab !== tab) {
                $scope.activeTab = tab;
                if (tab === 'banned') { populateBannedIPs(); }
                else if (tab === 'trusted') { populateTrustedSSHWhitelist(); }
                else { populateCurrentRecords(); }
            }
        });
    }
    window.addEventListener('hashchange', syncTabFromHash);
    
    // Pagination: Firewall Rules (default 10 per page, options 5–100)
    $scope.rulesPage = 1;
    $scope.rulesPageSize = 10;
    $scope.rulesPageSizeOptions = [5, 10, 20, 30, 50, 100];
    $scope.rulesTotalCount = 0;
    
    // Pagination: Banned IPs
    $scope.bannedPage = 1;
    $scope.bannedPageSize = 10;
    $scope.bannedPageSizeOptions = [5, 10, 20, 30, 50, 100];
    $scope.bannedTotalCount = 0;

    // Modify Banned IP modal state
    $scope.showModifyModal = false;
    $scope.modifyBannedIPData = { ip: '', id: null, reason: '', duration: '24h' };
    
    // Initialize banned IPs array - start as null so template shows empty state
    // Will be set to array after API call
    $scope.bannedIPsLoading = false;
    $scope.bannedIPActionFailed = true;
    $scope.bannedIPActionSuccess = true;
    $scope.bannedIPCouldNotConnect = true;
    $scope.banIP = '';
    $scope.banReason = '';
    $scope.banDuration = '24h';
    $scope.trustedSSHWhitelist = [];
    $scope.trustedForm = { ip: '', label: '' };
    $scope.trustedSSHLoading = false;
    $scope.bannedIPSearch = '';
    $scope.searchBannedIPFilter = function(item) {
        var q = ($scope.bannedIPSearch || '').toLowerCase().trim();
        if (!q) return true;
        var ip = (item.ip || '').toLowerCase();
        var reason = (item.reason || '').toLowerCase();
        var status = item.active ? 'active' : 'expired';
        return ip.indexOf(q) !== -1 || reason.indexOf(q) !== -1 || status.indexOf(q) !== -1;
    };

    $scope.onBannedSearchChange = function() {
        if ($scope.bannedSearchTimeout) $timeout.cancel($scope.bannedSearchTimeout);
        $scope.bannedSearchTimeout = $timeout(function() {
            $scope.bannedPage = 1;
            if (typeof populateBannedIPs === 'function') populateBannedIPs();
        }, 350);
    };

    $scope.runBannedSearch = function() {
        $scope.bannedPage = 1;
        if (typeof populateBannedIPs === 'function') populateBannedIPs();
    };

    firewallStatus();

    // Load active tab data on init (avoid flipping UX by always prefetching banned).
    if ($scope.activeTab === 'banned') {
        populateBannedIPs();
    } else if ($scope.activeTab === 'trusted') {
        populateTrustedSSHWhitelist();
    } else {
        populateCurrentRecords();
    }

    $scope.$watch('activeTab', function(newVal, oldVal) {
        if (newVal === oldVal || !newVal) return;
        $timeout(function() {
            try {
                if (newVal === 'banned' && typeof populateBannedIPs === 'function') populateBannedIPs();
                else if (newVal === 'trusted' && typeof populateTrustedSSHWhitelist === 'function') populateTrustedSSHWhitelist();
                else if (newVal === 'rules' && typeof populateCurrentRecords === 'function') populateCurrentRecords();
            } catch (e) {}
        }, 0);
    });

    // Log for debugging
    console.log('=== FIREWALL CONTROLLER INITIALIZING ===');
    console.log('Initializing firewall controller, loading banned IPs...');
    
    // Define populateBannedIPs function first, then call it
    // This ensures the function is available when setTimeout executes
    function populateBannedIPs() {
        console.log('=== populateBannedIPs() START ===');
        console.log('Current scope.bannedIPs:', $scope.bannedIPs);
        console.log('Current activeTab:', $scope.activeTab);
        
        $scope.bannedIPsLoading = true;
        var url = "/firewall/getBannedIPs";
        var csrfToken = getCookie('csrftoken');
        var config = {
            headers: {
                'X-CSRFToken': csrfToken
            }
        };

        var postData = {
            page: Math.max(1, parseInt($scope.bannedPage, 10) || 1),
            page_size: Math.max(5, Math.min(100, parseInt($scope.bannedPageSize, 10) || 10)),
            search: ($scope.bannedIPSearch || '').trim()
        };
        console.log('Making request to:', url, 'page:', postData.page, 'page_size:', postData.page_size, 'search:', postData.search);
        console.log('CSRF Token:', csrfToken ? 'Found (' + csrfToken.substring(0, 10) + '...)' : 'MISSING!');
        
        $http.post(url, postData, config).then(
            function(response) {
                var res = (typeof response.data === 'string') ? (function() { try { return JSON.parse(response.data); } catch (e) { return {}; } })() : response.data;
                console.log('=== API RESPONSE RECEIVED ===');
                console.log('Response status:', response.status);
                console.log('Response data (parsed):', res);
                
                $scope.bannedIPsLoading = false;
                // Reset error flags
                $scope.bannedIPActionFailed = true;
                $scope.bannedIPActionSuccess = true;
                $scope.bannedIPCouldNotConnect = true;
                
                if (res && res.status === 1) {
                    var bannedIPsArray = res.bannedIPs || [];
                    console.log('Raw bannedIPs from API:', bannedIPsArray);
                    console.log('Banned IPs count:', bannedIPsArray.length);
                    console.log('Is array?', Array.isArray(bannedIPsArray));
                    
                    // Ensure it's an array
                    if (!Array.isArray(bannedIPsArray)) {
                        console.error('ERROR: bannedIPs is not an array:', typeof bannedIPsArray);
                        bannedIPsArray = [];
                    }
                    
                    // Assign to scope - Angular $http callbacks already run within $apply
                    console.log('Assigning to scope.bannedIPs...');
                    $scope.bannedIPs = bannedIPsArray;
                    $scope.bannedTotalCount = res.total_count != null ? res.total_count : bannedIPsArray.length;
                    $scope.bannedPage = Math.max(1, res.page != null ? res.page : 1);
                    $scope.bannedPageSize = res.page_size != null ? res.page_size : 10;
                    $scope.bannedPageInput = $scope.bannedPage;
                    console.log('After assignment - scope.bannedIPs:', $scope.bannedIPs);
                    console.log('After assignment - scope.bannedIPs.length:', $scope.bannedIPs ? $scope.bannedIPs.length : 'undefined');
                    console.log('After assignment - activeTab:', $scope.activeTab);
                    
                    // No need to call $apply - $http callbacks run within $apply automatically
                    console.log('View should update automatically (Angular $http handles $apply)');
                    
                    console.log('=== populateBannedIPs() SUCCESS ===');
                } else {
                    console.error('ERROR: API returned status !== 1');
                    console.error('Response data:', res);
                    $scope.bannedIPs = [];
                    $scope.bannedIPActionFailed = false;
                    $scope.bannedIPErrorMessage = (res && res.error_message) || 'Unknown error';
                }
            },
            function(error) {
                console.error('=== HTTP ERROR ===');
                console.error('Error object:', error);
                console.error('Error status:', error.status);
                console.error('Error data:', error.data);
                console.error('Error statusText:', error.statusText);
                
                $scope.bannedIPsLoading = false;
                $scope.bannedIPActionFailed = true;
                $scope.bannedIPActionSuccess = true;
                $scope.bannedIPCouldNotConnect = false;
                $scope.bannedIPs = [];
                
                try {
                    if (!$scope.$$phase && !$scope.$root.$$phase) {
                        $scope.$apply();
                    }
                } catch(e) {
                    console.error('Error in $apply (error handler):', e);
                }
            }
        );
    }

    function populateTrustedSSHWhitelist() {
        $scope.trustedSSHLoading = true;
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') || '' } };
        $http.post('/base/sshSecurityWhitelistList', {}, config).then(
            function(response) {
                $scope.trustedSSHLoading = false;
                var res = response.data;
                if (typeof res === 'string') {
                    try { res = JSON.parse(res); } catch (e) { res = {}; }
                }
                if (res && res.status === 1) {
                    var ent = res.entries || [];
                    $scope.trustedSSHWhitelist = ent.map(function(e) {
                        return {
                            ip: e.ip,
                            label: e.label || '',
                            updated: e.updated || 0,
                            _l: e.label || '',
                            _nip: ''
                        };
                    });
                } else {
                    $scope.trustedSSHWhitelist = [];
                    var errMsg = (res && res.error) ? res.error : 'Could not load trusted IPs';
                    if (typeof PNotify !== 'undefined') {
                        new PNotify({ title: 'Trusted IPs', text: errMsg, type: 'error', delay: 6000 });
                    }
                }
            },
            function(error) {
                $scope.trustedSSHLoading = false;
                $scope.trustedSSHWhitelist = [];
                var msg = (error.data && error.data.error) ? error.data.error : 'Request failed';
                if (typeof PNotify !== 'undefined') {
                    new PNotify({ title: 'Trusted IPs', text: msg, type: 'error', delay: 6000 });
                }
            }
        );
    }

    $scope.populateTrustedSSHWhitelist = function() {
        populateTrustedSSHWhitelist();
    };

    $scope.addTrustedSSHWhitelist = function() {
        var ip = ($scope.trustedForm.ip || '').trim();
        var label = ($scope.trustedForm.label || '').trim();
        if (!ip) {
            if (typeof PNotify !== 'undefined') {
                new PNotify({ title: 'Trusted IPs', text: 'Enter an IP address', type: 'warning', delay: 5000 });
            }
            return;
        }
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') || '' } };
        $http.post('/base/sshSecurityWhitelistAdd', { ip: ip, label: label }, config).then(
            function(response) {
                var res = response.data;
                if (typeof res === 'string') {
                    try { res = JSON.parse(res); } catch (e) { res = {}; }
                }
                if (res && res.status === 1) {
                    $scope.trustedForm.ip = '';
                    $scope.trustedForm.label = '';
                    populateTrustedSSHWhitelist();
                    if (typeof PNotify !== 'undefined') {
                        new PNotify({ title: 'Trusted IPs', text: 'IP added to trusted list', type: 'success', delay: 4000 });
                    }
                } else {
                    var errAdd = (res && res.error) ? res.error : 'Failed to add';
                    if (typeof PNotify !== 'undefined') {
                        new PNotify({ title: 'Trusted IPs', text: errAdd, type: 'error', delay: 6000 });
                    }
                }
            },
            function(err) {
                var em = (err.data && err.data.error) ? err.data.error : 'Request failed';
                if (typeof PNotify !== 'undefined') {
                    new PNotify({ title: 'Trusted IPs', text: em, type: 'error', delay: 6000 });
                }
            }
        );
    };

    $scope.removeTrustedSSHWhitelist = function(ip) {
        if (!ip) return;
        firewallConfirmDelete(
            'Remove Trusted IP',
            'Are you sure you want to remove trusted SSH IP "' + ip + '" from the whitelist?',
            function () {
                var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') || '' } };
                $http.post('/base/sshSecurityWhitelistRemove', { ip: ip }, config).then(
                    function(response) {
                        var res = response.data;
                        if (typeof res === 'string') {
                            try { res = JSON.parse(res); } catch (e) { res = {}; }
                        }
                        if (res && res.status === 1) {
                            populateTrustedSSHWhitelist();
                            if (typeof PNotify !== 'undefined') {
                                new PNotify({ title: 'Trusted IPs', text: 'IP removed', type: 'success', delay: 4000 });
                            }
                        } else {
                            var errRm = (res && res.error) ? res.error : 'Failed to remove';
                            if (typeof PNotify !== 'undefined') {
                                new PNotify({ title: 'Trusted IPs', text: errRm, type: 'error', delay: 6000 });
                            }
                        }
                    },
                    function(err) {
                        var em2 = (err.data && err.data.error) ? err.data.error : 'Request failed';
                        if (typeof PNotify !== 'undefined') {
                            new PNotify({ title: 'Trusted IPs', text: em2, type: 'error', delay: 6000 });
                        }
                    }
                );
            }
        );
    };

    $scope.saveTrustedSSHWhitelistRow = function(row) {
        if (!row || !row.ip) return;
        var payload = { ip: row.ip, label: row._l };
        if (row._nip && String(row._nip).trim()) {
            payload.new_ip = String(row._nip).trim();
        }
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') || '' } };
        $http.post('/base/sshSecurityWhitelistUpdate', payload, config).then(
            function(response) {
                var res = response.data;
                if (typeof res === 'string') {
                    try { res = JSON.parse(res); } catch (e) { res = {}; }
                }
                var ok = res && (res.status === 1 || res.status === '1');
                if (ok) {
                    populateTrustedSSHWhitelist();
                    if (typeof PNotify !== 'undefined') {
                        var unchanged = res.unchanged === true || res.unchanged === 'true' || res.unchanged === 1;
                        var msgOk = (res.message && String(res.message).length) ? res.message : (unchanged ? 'No changes to save.' : 'Entry updated');
                        new PNotify({ title: 'Trusted IPs', text: msgOk, type: unchanged ? 'info' : 'success', delay: 4000 });
                    }
                } else {
                    var errUp = (res && res.error) ? res.error : 'Failed to update';
                    if (typeof PNotify !== 'undefined') {
                        new PNotify({ title: 'Trusted IPs', text: errUp, type: 'error', delay: 6000 });
                    }
                }
            },
            function(err) {
                var em3 = (err.data && err.data.error) ? err.data.error : 'Request failed';
                if (typeof PNotify !== 'undefined') {
                    new PNotify({ title: 'Trusted IPs', text: em3, type: 'error', delay: 6000 });
                }
            }
        );
    };
    
    // Expose to scope for template access
    $scope.populateBannedIPs = function() {
        console.log('$scope.populateBannedIPs() called from template');
        populateBannedIPs();
    };

    $scope.goToBannedPage = function(page) {
        var totalP = Math.max(1, $scope.bannedTotalPages());
        var p = parseInt(page, 10);
        if (isNaN(p) || p < 1 || p > totalP) return;
        $scope.bannedPage = p;
        populateBannedIPs();
    };
    $scope.goToBannedPageByInput = function() {
        var self = $scope;
        $timeout(function() {
            var n = parseInt(self.bannedPageInput, 10);
            if (isNaN(n) || n < 1) n = self.bannedPage || 1;
            var maxP = Math.max(1, self.bannedTotalPages());
            n = Math.min(Math.max(1, n), maxP);
            self.bannedPageInput = n;
            self.bannedPage = n;
            populateBannedIPs();
        }, 0);
    };
    $scope.bannedTotalPages = function() {
        var size = $scope.bannedPageSize || 10;
        var total = $scope.bannedTotalCount || ($scope.bannedIPs ? $scope.bannedIPs.length : 0) || 0;
        return size > 0 ? Math.max(1, Math.ceil(total / size)) : 1;
    };
    $scope.bannedRangeStart = function() {
        var total = $scope.bannedTotalCount || ($scope.bannedIPs ? $scope.bannedIPs.length : 0) || 0;
        if (total === 0) return 0;
        var page = Math.max(1, $scope.bannedPage || 1);
        var size = $scope.bannedPageSize || 10;
        return (page - 1) * size + 1;
    };
    $scope.bannedRangeEnd = function() {
        var start = $scope.bannedRangeStart();
        var size = $scope.bannedPageSize || 10;
        var total = $scope.bannedTotalCount || ($scope.bannedIPs ? $scope.bannedIPs.length : 0) || 0;
        return total === 0 ? 0 : Math.min(start + size - 1, total);
    };
    $scope.setBannedPageSize = function() {
        var size = parseInt($scope.bannedPageSize, 10);
        $scope.bannedPageSize = (size >= 5 && size <= 100) ? size : 10;
        $scope.bannedPage = 1;
        populateBannedIPs();
    };

    if (typeof window !== 'undefined') {
        window.__firewallLoadTab = function(tab) {
            $scope.$evalAsync(function() {
                $scope.activeTab = tab;
                if (tab === 'banned') { populateBannedIPs(); }
                else if (tab === 'trusted') { populateTrustedSSHWhitelist(); }
                else { populateCurrentRecords(); }
            });
        };
    }
    
    // Prefetch banned IPs shortly after load only when that tab is active (avoids tab race noise).
    try {
        $timeout(function() {
            try {
                if ($scope.activeTab === 'banned') {
                    console.log('=== Calling populateBannedIPs from $timeout on page load ===');
                    populateBannedIPs();
                } else if ($scope.activeTab === 'rules') {
                    populateCurrentRecords();
                } else if ($scope.activeTab === 'trusted') {
                    populateTrustedSSHWhitelist();
                }
            } catch(e) {
                console.error('Error in firewall tab prefetch from timeout:', e);
            }
        }, 500);
    } catch(e) {
        console.error('Error setting up timeout for firewall tab prefetch:', e);
    }
    
    $scope.addRule = function () {

        $scope.rulesLoading = false;
        $scope.actionFailed = true;
        $scope.actionSuccess = true;

        $scope.canNotAddRule = true;
        $scope.ruleAdded = true;
        $scope.couldNotConnect = true;


        url = "/firewall/addRule";


        var ruleName = $scope.ruleName;
        var ruleProtocol = $scope.ruleProtocol;
        var rulePort = $scope.rulePort;


        var data = {
            ruleName: ruleName,
            ruleProtocol: ruleProtocol,
            rulePort: rulePort,
            ruleIP: $scope.ruleIP,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.add_status == 1) {


                populateCurrentRecords();

                $scope.actionFailed = true;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = false;
                $scope.couldNotConnect = true;


            }
            else {

                $scope.rulesLoading = false;
                $scope.actionFailed = true;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = false;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;


                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = false;
            $scope.actionFailed = true;
            $scope.actionSuccess = true;

            $scope.canNotAddRule = true;
            $scope.ruleAdded = true;
            $scope.couldNotConnect = false;


        }

    };

    function populateCurrentRecords() {
        var gen = ++rulesFetchGen;
        $scope.rulesLoading = true;
        $scope.actionFailed = true;
        $scope.actionSuccess = true;

        url = "/firewall/getCurrentRules";
        var data = {
            page: Math.max(1, parseInt($scope.rulesPage, 10) || 1),
            page_size: Math.max(5, Math.min(100, parseInt($scope.rulesPageSize, 10) || 10))
        };
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            if (gen !== rulesFetchGen) {
                return;
            }
            try {
                var res = (typeof response.data === 'string') ? (function() { try { return JSON.parse(response.data); } catch (e) { return {}; } })() : response.data;
                if (res && res.fetchStatus == 1) {
                    var parsedRules = [];
                    if (typeof res.data === 'string') {
                        try {
                            parsedRules = JSON.parse(res.data);
                        } catch (parseErr) {
                            parsedRules = [];
                            $scope.errorMessage = (res && res.error_message) ? res.error_message : 'Invalid rules data';
                        }
                    } else {
                        parsedRules = res.data || [];
                    }
                    $scope.rules = parsedRules;
                    $scope.rulesTotalCount = res.total_count != null ? res.total_count : ($scope.rules ? $scope.rules.length : 0);
                    $scope.rulesPage = Math.max(1, res.page != null ? res.page : 1);
                    $scope.rulesPageSize = res.page_size != null ? res.page_size : 10;
                } else {
                    $scope.errorMessage = (res && res.error_message) ? res.error_message : '';
                }
            } catch (e) {
                $scope.errorMessage = 'Could not load firewall rules.';
            } finally {
                if (gen === rulesFetchGen) {
                    $scope.rulesLoading = false;
                }
            }
        }

        function cantLoadInitialDatas(response) {
            if (gen !== rulesFetchGen) {
                return;
            }
            $scope.rulesLoading = false;
            $scope.couldNotConnect = false;
        }
    }

    $scope.goToRulesPage = function(page) {
        var totalP = Math.max(1, $scope.rulesTotalPages());
        var p = parseInt(page, 10);
        if (isNaN(p) || p < 1 || p > totalP) return;
        $scope.rulesPage = p;
        populateCurrentRecords();
    };
    $scope.goToRulesPageByInput = function() {
        $timeout(function() {
            var n = parseInt($scope.rulesPageInput, 10);
            if (isNaN(n) || n < 1) n = $scope.rulesPage || 1;
            var maxP = Math.max(1, $scope.rulesTotalPages());
            n = Math.min(Math.max(1, n), maxP);
            $scope.rulesPageInput = n;
            $scope.rulesPage = n;
            populateCurrentRecords();
        }, 0);
    };
    $scope.rulesTotalPages = function() {
        var size = $scope.rulesPageSize || 10;
        var total = $scope.rulesTotalCount || ($scope.rules && $scope.rules.length) || 0;
        return size > 0 ? Math.max(1, Math.ceil(total / size)) : 1;
    };
    $scope.rulesRangeStart = function() {
        var total = $scope.rulesTotalCount || ($scope.rules && $scope.rules.length) || 0;
        if (total === 0) return 0;
        var page = Math.max(1, $scope.rulesPage || 1);
        var size = $scope.rulesPageSize || 10;
        return (page - 1) * size + 1;
    };
    $scope.rulesRangeEnd = function() {
        var start = $scope.rulesRangeStart();
        var size = $scope.rulesPageSize || 10;
        var total = $scope.rulesTotalCount || ($scope.rules && $scope.rules.length) || 0;
        return total === 0 ? 0 : Math.min(start + size - 1, total);
    };
    $scope.setRulesPageSize = function() {
        var size = parseInt($scope.rulesPageSize, 10);
        $scope.rulesPageSize = (size >= 5 && size <= 100) ? size : 10;
        $scope.rulesPage = 1;
        populateCurrentRecords();
    };

    function renumberDisplayedRuleIds() {
        var start = $scope.rulesRangeStart() || 1;
        ($scope.rules || []).forEach(function(rule, idx) {
            rule.displayId = start + idx;
            rule.sortOrder = rule.displayId;
        });
    }

    function persistPageRuleOrder() {
        var pageIds = ($scope.rules || []).map(function(r) { return r.id; });
        if (!pageIds.length) {
            return;
        }
        $scope.rulesLoading = true;
        var url = '/firewall/reorderRules';
        var data = {
            page_ordered_ids: pageIds,
            page: Math.max(1, parseInt($scope.rulesPage, 10) || 1),
            page_size: Math.max(5, Math.min(100, parseInt($scope.rulesPageSize, 10) || 10))
        };
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') } };
        $http.post(url, data, config).then(function(response) {
            var res = response.data || {};
            if (res.reorder_status === 1 || res.status === 1) {
                renumberDisplayedRuleIds();
                $scope.actionFailed = true;
                $scope.actionSuccess = false;
                $scope.rulesLoading = false;
            } else {
                $scope.actionFailed = false;
                $scope.actionSuccess = true;
                $scope.errorMessage = res.error_message || 'Could not save rule order';
                populateCurrentRecords();
            }
        }, function() {
            $scope.actionFailed = false;
            $scope.actionSuccess = true;
            $scope.errorMessage = 'Could not connect to server. Please refresh this page.';
            populateCurrentRecords();
        });
    }

    $scope.canMoveRuleUp = function(index) {
        var page = Math.max(1, parseInt($scope.rulesPage, 10) || 1);
        return !(page === 1 && index === 0);
    };

    $scope.canMoveRuleDown = function(index) {
        var page = Math.max(1, parseInt($scope.rulesPage, 10) || 1);
        var size = Math.max(5, Math.min(100, parseInt($scope.rulesPageSize, 10) || 10));
        var total = $scope.rulesTotalCount || ($scope.rules ? $scope.rules.length : 0) || 0;
        var globalIndex = (page - 1) * size + index;
        return globalIndex < (total - 1);
    };

    $scope.moveRuleUp = function(rule) {
        if (!rule || !rule.id) {
            return;
        }
        $scope.rulesLoading = true;
        var url = '/firewall/reorderRules';
        var data = { id: rule.id, direction: 'up' };
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') } };
        $http.post(url, data, config).then(function(response) {
            var res = response.data || {};
            if (res.reorder_status === 1 || res.status === 1) {
                $scope.actionFailed = true;
                $scope.actionSuccess = false;
                populateCurrentRecords();
            } else {
                $scope.rulesLoading = false;
                $scope.actionFailed = false;
                $scope.actionSuccess = true;
                $scope.errorMessage = res.error_message || 'Could not move rule';
            }
        }, function() {
            $scope.rulesLoading = false;
            $scope.actionFailed = false;
            $scope.actionSuccess = true;
            $scope.errorMessage = 'Could not connect to server. Please refresh this page.';
        });
    };

    $scope.moveRuleDown = function(rule) {
        if (!rule || !rule.id) {
            return;
        }
        $scope.rulesLoading = true;
        var url = '/firewall/reorderRules';
        var data = { id: rule.id, direction: 'down' };
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') } };
        $http.post(url, data, config).then(function(response) {
            var res = response.data || {};
            if (res.reorder_status === 1 || res.status === 1) {
                $scope.actionFailed = true;
                $scope.actionSuccess = false;
                populateCurrentRecords();
            } else {
                $scope.rulesLoading = false;
                $scope.actionFailed = false;
                $scope.actionSuccess = true;
                $scope.errorMessage = res.error_message || 'Could not move rule';
            }
        }, function() {
            $scope.rulesLoading = false;
            $scope.actionFailed = false;
            $scope.actionSuccess = true;
            $scope.errorMessage = 'Could not connect to server. Please refresh this page.';
        });
    };

    var rulesDragFromIndex = null;

    function bindRulesDragDrop() {
        var tbody = document.getElementById('firewall-rules-tbody');
        if (!tbody || tbody.getAttribute('data-dnd-bound') === '1') {
            return;
        }
        tbody.setAttribute('data-dnd-bound', '1');

        tbody.addEventListener('dragstart', function(ev) {
            var row = ev.target && ev.target.closest ? ev.target.closest('tr[data-rule-id]') : null;
            if (!row || !tbody.contains(row)) {
                return;
            }
            // Allow drag from row/handle; block from action buttons/inputs
            if (ev.target.closest && ev.target.closest('button, a, input, select, textarea')) {
                ev.preventDefault();
                return;
            }
            rulesDragFromIndex = parseInt(row.getAttribute('data-rule-index'), 10);
            if (isNaN(rulesDragFromIndex)) {
                rulesDragFromIndex = null;
                return;
            }
            row.classList.add('rule-row-dragging');
            try {
                ev.dataTransfer.effectAllowed = 'move';
                ev.dataTransfer.setData('text/plain', String(rulesDragFromIndex));
            } catch (ignoreSet) {}
        });

        tbody.addEventListener('dragover', function(ev) {
            var row = ev.target && ev.target.closest ? ev.target.closest('tr[data-rule-id]') : null;
            if (!row || !tbody.contains(row)) {
                return;
            }
            ev.preventDefault();
            try {
                ev.dataTransfer.dropEffect = 'move';
            } catch (ignoreDrop) {}
        });

        tbody.addEventListener('drop', function(ev) {
            var row = ev.target && ev.target.closest ? ev.target.closest('tr[data-rule-id]') : null;
            if (!row || !tbody.contains(row)) {
                return;
            }
            ev.preventDefault();
            var toIndex = parseInt(row.getAttribute('data-rule-index'), 10);
            var fromIndex = rulesDragFromIndex;
            if (fromIndex === null || isNaN(toIndex) || fromIndex === toIndex) {
                return;
            }
            $scope.$applyAsync(function() {
                var list = $scope.rules || [];
                if (fromIndex < 0 || fromIndex >= list.length || toIndex < 0 || toIndex >= list.length) {
                    return;
                }
                var moved = list.splice(fromIndex, 1)[0];
                list.splice(toIndex, 0, moved);
                $scope.rules = list;
                renumberDisplayedRuleIds();
                persistPageRuleOrder();
            });
        });

        tbody.addEventListener('dragend', function(ev) {
            rulesDragFromIndex = null;
            var dragging = tbody.querySelectorAll('.rule-row-dragging');
            for (var i = 0; i < dragging.length; i++) {
                dragging[i].classList.remove('rule-row-dragging');
            }
        });
    }

    // Bind after Angular paints the rules table (tbody is destroyed when rules empty)
    $scope.$watchCollection('rules', function() {
        $timeout(bindRulesDragDrop, 0);
    });

    $scope.openModifyRuleModal = function(rule) {
        if (!rule) return;
        $scope.modifyRuleData = {
            id: rule.id,
            name: rule.name || '',
            proto: rule.proto || 'tcp',
            port: String(rule.port || ''),
            ruleIP: rule.ipAddress || rule.ruleIP || '0.0.0.0/0'
        };
        $scope.showModifyRuleModal = true;
    };

    $scope.closeModifyRuleModal = function() {
        $scope.showModifyRuleModal = false;
        $scope.modifyRuleData = { id: null, name: '', proto: 'tcp', port: '', ruleIP: '0.0.0.0/0' };
    };

    $scope.saveModifyRule = function() {
        var d = $scope.modifyRuleData;
        if (!d.name || !d.name.trim()) {
            $scope.actionFailed = false;
            $scope.actionSuccess = true;
            $scope.errorMessage = 'Rule name is required';
            return;
        }
        if (!d.port || !String(d.port).trim()) {
            $scope.actionFailed = false;
            $scope.actionSuccess = true;
            $scope.errorMessage = 'Port is required';
            return;
        }
        $scope.rulesLoading = true;
        var url = '/firewall/modifyRule';
        var data = {
            id: d.id,
            name: d.name.trim(),
            proto: d.proto || 'tcp',
            port: String(d.port).trim(),
            ruleIP: (d.ruleIP || '0.0.0.0/0').trim()
        };
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') } };
        $http.post(url, data, config).then(function(response) {
            if (response.data && response.data.status === 1) {
                $scope.closeModifyRuleModal();
                $scope.actionFailed = true;
                $scope.actionSuccess = false;
                populateCurrentRecords();
            } else {
                $scope.rulesLoading = false;
                $scope.actionFailed = false;
                $scope.actionSuccess = true;
                $scope.errorMessage = (response.data && response.data.error_message) || 'Modify failed';
            }
        }, function() {
            $scope.rulesLoading = false;
            $scope.actionFailed = false;
            $scope.actionSuccess = true;
            $scope.errorMessage = 'Could not connect to server. Please refresh this page.';
        });
    };

    $scope.deleteRule = function (id, proto, port, ruleIP, ruleName) {
        var nameLabel = (ruleName && String(ruleName).trim()) ? String(ruleName).trim() : ('#' + id);
        var detail = nameLabel + ' (' + (proto || '') + '/' + (port || '') + ', ' + (ruleIP || '') + ')';
        firewallConfirmDelete(
            'Delete Firewall Rule',
            'Are you sure you want to delete firewall rule "' + detail + '"? This cannot be undone.',
            function () {
                $scope.rulesLoading = true;

                url = "/firewall/deleteRule";

                var data = {
                    id: id,
                    proto: proto,
                    port: port,
                    ruleIP: ruleIP
                };

                var config = {
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };


                $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


                function ListInitialDatas(response) {


                    if (response.data.delete_status === 1) {


                        populateCurrentRecords();
                        $scope.actionFailed = true;
                        $scope.actionSuccess = true;

                        $scope.canNotAddRule = true;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;


                    }
                    else {

                        $scope.rulesLoading = false;
                        $scope.actionFailed = true;
                        $scope.actionSuccess = true;

                        $scope.canNotAddRule = false;
                        $scope.ruleAdded = true;
                        $scope.couldNotConnect = true;

                        $scope.errorMessage = response.data.error_message;


                    }

                }

                function cantLoadInitialDatas(response) {

                    $scope.rulesLoading = false;
                    $scope.actionFailed = true;
                    $scope.actionSuccess = true;

                    $scope.canNotAddRule = true;
                    $scope.ruleAdded = true;
                    $scope.couldNotConnect = false;


                }
            }
        );


    };


    $scope.reloadFireWall = function () {


        $scope.actionFailed = true;
        $scope.actionSuccess = true;

        $scope.canNotAddRule = true;
        $scope.ruleAdded = true;
        $scope.couldNotConnect = true;

        $scope.rulesLoading = false;

        url = "/firewall/reloadFirewall";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.reload_status == 1) {


                $scope.rulesLoading = false;
                $scope.actionFailed = true;
                $scope.actionSuccess = false;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.rulesDetails = false;
                populateCurrentRecords();


            }
            else {

                $scope.rulesLoading = false;
                $scope.actionFailed = false;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = false;
            $scope.actionFailed = true;
            $scope.actionSuccess = true;

            $scope.canNotAddRule = true;
            $scope.ruleAdded = true;
            $scope.couldNotConnect = false;


        }


    };

    $scope.startFirewall = function () {


        $scope.actionFailed = true;
        $scope.actionSuccess = true;

        $scope.canNotAddRule = true;
        $scope.ruleAdded = true;
        $scope.couldNotConnect = true;

        $scope.rulesLoading = false;

        url = "/firewall/startFirewall";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.start_status == 1) {


                $scope.rulesLoading = false;
                $scope.actionFailed = true;
                $scope.actionSuccess = false;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.rulesDetails = false;

                firewallStatus();
                /* Reload rules after Start so the table stays visible and populated. */
                populateCurrentRecords();


            }
            else {

                $scope.rulesLoading = false;
                $scope.actionFailed = false;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = false;
            $scope.actionFailed = true;
            $scope.actionSuccess = true;

            $scope.canNotAddRule = true;
            $scope.ruleAdded = true;
            $scope.couldNotConnect = false;


        }


    };


    $scope.stopFirewall = function () {


        $scope.actionFailed = true;
        $scope.actionSuccess = true;

        $scope.canNotAddRule = true;
        $scope.ruleAdded = true;
        $scope.couldNotConnect = true;

        $scope.rulesLoading = false;

        url = "/firewall/stopFirewall";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.stop_status == 1) {


                $scope.rulesLoading = false;
                $scope.actionFailed = true;
                $scope.actionSuccess = false;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                /* Keep rules UI visible while firewall is stopped so operators can still edit stored rules. */
                $scope.rulesDetails = false;

                firewallStatus();
                populateCurrentRecords();


            }
            else {

                $scope.rulesLoading = false;
                $scope.actionFailed = false;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = false;
            $scope.actionFailed = true;
            $scope.actionSuccess = true;

            $scope.canNotAddRule = true;
            $scope.ruleAdded = true;
            $scope.couldNotConnect = false;


        }


    };


    function firewallStatus() {


        url = "/firewall/firewallStatus";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.status == 1) {

                if (response.data.firewallStatus == 1) {
                    $scope.status = "ON";
                }
                else {
                    $scope.status = "OFF";
                }
            }
            else {
                $scope.status = "OFF";
            }
            /* Never hide the rules table/form when firewall is OFF (was rulesDetails=true). */
            $scope.rulesDetails = false;


        }

        function cantLoadInitialDatas(response) {

            $scope.couldNotConnect = false;


        }

    }

    // Banned IPs Functions
    $scope.addBannedIP = function() {
        if (!$scope.banIP || !$scope.banReason) {
            $scope.bannedIPActionFailed = false;
            $scope.bannedIPErrorMessage = "Please fill in all required fields";
            return;
        }

        $scope.bannedIPsLoading = true;
        $scope.bannedIPActionFailed = true;
        $scope.bannedIPActionSuccess = true;
        $scope.bannedIPCouldNotConnect = true;

        var data = {
            ip: $scope.banIP,
            reason: $scope.banReason,
            duration: $scope.banDuration
        };

        var url = "/firewall/addBannedIP";
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(function(response) {
            $scope.bannedIPsLoading = false;
            // Reset error flags
            $scope.bannedIPActionFailed = true;
            $scope.bannedIPActionSuccess = true;
            $scope.bannedIPCouldNotConnect = true;
            
            if (response.data.status === 1) {
                $scope.bannedIPActionSuccess = false;
                $scope.banIP = '';
                $scope.banReason = '';
                $scope.banDuration = '24h';
                console.log('IP banned successfully, refreshing list...');
                populateBannedIPs(); // Refresh the list
            } else {
                $scope.bannedIPActionFailed = false;
                $scope.bannedIPErrorMessage = response.data.error_message || 'Unknown error';
                console.error('Failed to ban IP:', response.data);
            }
        }, function(error) {
            $scope.bannedIPsLoading = false;
            $scope.bannedIPActionFailed = true;
            $scope.bannedIPActionSuccess = true;
            $scope.bannedIPCouldNotConnect = false;
            console.error('Error banning IP:', error);
        });
    };

    $scope.removeBannedIP = function(id, ip) {
        var ipLabel = ip || ('#' + id);
        firewallConfirmDelete(
            'Unban IP Address',
            'Are you sure you want to unban IP address "' + ipLabel + '"?',
            function () {
                $scope.bannedIPsLoading = true;
                $scope.bannedIPActionFailed = true;
                $scope.bannedIPActionSuccess = true;
                $scope.bannedIPCouldNotConnect = true;

                var data = { id: id };

                var url = "/firewall/removeBannedIP";
                var config = {
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data, config).then(function(response) {
                    $scope.bannedIPsLoading = false;
                    if (response.data.status === 1) {
                        $scope.bannedIPActionSuccess = false;
                        populateBannedIPs(); // Refresh the list
                    } else {
                        $scope.bannedIPActionFailed = false;
                        $scope.bannedIPErrorMessage = response.data.error_message;
                    }
                }, function(error) {
                    $scope.bannedIPsLoading = false;
                    $scope.bannedIPCouldNotConnect = false;
                });
            }
        );
    };

    $scope.deleteBannedIP = function(id, ip) {
        var ipLabel = ip || ('#' + id);
        firewallConfirmDelete(
            'Delete Banned IP Record',
            'Are you sure you want to permanently delete the record for IP address "' + ipLabel + '"? This action cannot be undone.',
            function () {
                $scope.bannedIPsLoading = true;
                $scope.bannedIPActionFailed = true;
                $scope.bannedIPActionSuccess = true;
                $scope.bannedIPCouldNotConnect = true;

                var data = { id: id };

                var url = "/firewall/deleteBannedIP";
                var config = {
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                };

                $http.post(url, data, config).then(function(response) {
                    $scope.bannedIPsLoading = false;
                    if (response.data.status === 1) {
                        $scope.bannedIPActionSuccess = false;
                        populateBannedIPs(); // Refresh the list
                    } else {
                        $scope.bannedIPActionFailed = false;
                        $scope.bannedIPErrorMessage = response.data.error_message;
                    }
                }, function(error) {
                    $scope.bannedIPsLoading = false;
                    $scope.bannedIPCouldNotConnect = false;
                });
            }
        );
    };

    $scope.openModifyModal = function(bannedIP) {
        if (!bannedIP) return;
        $scope.modifyBannedIPData = {
            id: bannedIP.id,
            ip: bannedIP.ip || bannedIP.ip_address || '',
            reason: bannedIP.reason || '',
            duration: bannedIP.duration || '24h'
        };
        $scope.showModifyModal = true;
    };

    $scope.closeModifyModal = function() {
        $scope.showModifyModal = false;
        $scope.modifyBannedIPData = { ip: '', id: null, reason: '', duration: '24h' };
    };

    $scope.saveModifyBannedIP = function() {
        var d = $scope.modifyBannedIPData;
        if (!d.reason || !d.reason.trim()) {
            $scope.bannedIPActionFailed = false;
            $scope.bannedIPErrorMessage = 'Reason is required';
            return;
        }
        $scope.bannedIPsLoading = true;
        $scope.bannedIPActionFailed = true;
        $scope.bannedIPActionSuccess = true;
        $scope.bannedIPCouldNotConnect = true;
        var data = {
            id: d.id,
            ip: d.ip,
            reason: d.reason.trim(),
            duration: d.duration || '24h'
        };
        var url = '/firewall/modifyBannedIP';
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') } };
        $http.post(url, data, config).then(function(response) {
            $scope.bannedIPsLoading = false;
            if (response.data && response.data.status === 1) {
                $scope.bannedIPActionSuccess = false;
                $scope.closeModifyModal();
                populateBannedIPs();
            } else {
                $scope.bannedIPActionFailed = false;
                $scope.bannedIPErrorMessage = (response.data && response.data.error_message) || 'Modify failed';
            }
        }, function(error) {
            $scope.bannedIPsLoading = false;
            $scope.bannedIPCouldNotConnect = false;
        });
    };

    $scope.exportBannedIPs = function() {
        $scope.bannedIPsLoading = false;
        var url = "/firewall/exportBannedIPs";
        var config = { headers: { 'X-CSRFToken': getCookie('csrftoken') }, responseType: 'text' };
        $http.post(url, {}, config).then(function(response) {
            $scope.bannedIPsLoading = true;
            var raw = response.data;
            try {
                var data = typeof raw === 'string' ? JSON.parse(raw) : raw;
                if (data && data.exportStatus === 0) {
                    $scope.bannedIPActionFailed = false;
                    $scope.bannedIPErrorMessage = data.error_message || 'Export failed';
                    return;
                }
            } catch (e) {}
            var content = typeof raw === 'string' ? raw : JSON.stringify(raw, null, 2);
            var blob = new Blob([content], { type: 'application/json' });
            var a = document.createElement('a');
            a.href = window.URL.createObjectURL(blob);
            a.download = 'banned_ips_export_' + (Date.now() / 1000 | 0) + '.json';
            a.click();
            window.URL.revokeObjectURL(a.href);
            $scope.bannedIPActionSuccess = false;
        }, function() {
            $scope.bannedIPsLoading = true;
            $scope.bannedIPCouldNotConnect = false;
        });
    };

    $scope.importBannedIPs = function() {
        var input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.style.display = 'none';
        input.onchange = function(event) {
            var file = event.target.files[0];
            if (!file) return;
            $scope.bannedIPsLoading = false;
            var formData = new FormData();
            formData.append('import_file', file);
            var config = {
                headers: { 'X-CSRFToken': getCookie('csrftoken'), 'Content-Type': undefined },
                transformRequest: angular.identity
            };
            $http.post("/firewall/importBannedIPs", formData, config).then(function(response) {
                $scope.bannedIPsLoading = true;
                if (response.data && response.data.importStatus === 1) {
                    $scope.bannedIPActionSuccess = false;
                    populateBannedIPs();
                } else {
                    $scope.bannedIPActionFailed = false;
                    $scope.bannedIPErrorMessage = (response.data && response.data.error_message) || 'Import failed';
                }
            }, function() {
                $scope.bannedIPsLoading = true;
                $scope.bannedIPCouldNotConnect = false;
            });
        };
        document.body.appendChild(input);
        input.click();
        document.body.removeChild(input);
    };

    // Export/Import Firewall Rules: format modals and actions
    $scope.exportRules = function () {
        $scope.showExportFormatModal = true;
        $scope.exportRulesFormat = $scope.exportRulesFormat || 'json';
    };

    $scope.closeExportFormatModal = function () {
        $scope.showExportFormatModal = false;
    };

    $scope.confirmExportRules = function () {
        $scope.showExportFormatModal = false;
        var format = $scope.exportRulesFormat || 'json';
        doExportRules(format);
    };

    function doExportRules(format) {
        $scope.rulesLoading = true;
        $scope.actionFailed = true;
        $scope.actionSuccess = true;

        var url = "/firewall/exportFirewallRules";
        var data = { format: format };
        var config = {
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            responseType: 'text'
        };

        $http.post(url, data, config).then(exportSuccess, exportError);

        function exportSuccess(response) {
            $scope.rulesLoading = false;
            var raw = response.data;
            if (typeof raw === 'string' && raw.indexOf('{') === 0) {
                try {
                    var parsed = JSON.parse(raw);
                    if (parsed.exportStatus === 0) {
                        $scope.actionFailed = false;
                        $scope.actionSuccess = true;
                        $scope.errorMessage = parsed.error_message || 'Export failed';
                        return;
                    }
                } catch (e) {}
            }
            var contentType = format === 'excel' ? 'text/csv' : 'application/json';
            var ext = format === 'excel' ? 'csv' : 'json';
            var blob = new Blob([typeof raw === 'string' ? raw : JSON.stringify(raw)], { type: contentType });
            var a = document.createElement('a');
            a.href = window.URL.createObjectURL(blob);
            a.download = 'firewall_rules_export_' + (Date.now() / 1000 | 0) + '.' + ext;
            a.click();
            window.URL.revokeObjectURL(a.href);
            $scope.actionFailed = true;
            $scope.actionSuccess = false;
        }

        function exportError() {
            $scope.rulesLoading = false;
            $scope.actionFailed = false;
            $scope.actionSuccess = true;
            $scope.errorMessage = "Could not connect to server. Please refresh this page.";
        }
    }

    $scope.importRules = function () {
        $scope.showImportFormatModal = true;
        $scope.importRulesFormat = $scope.importRulesFormat || 'json';
    };

    $scope.closeImportFormatModal = function () {
        $scope.showImportFormatModal = false;
    };

    $scope.confirmImportRules = function () {
        $scope.showImportFormatModal = false;
        var format = $scope.importRulesFormat || 'json';
        var accept = format === 'excel' ? '.csv' : '.json';
        var input = document.createElement('input');
        input.type = 'file';
        input.accept = accept;
        input.style.display = 'none';
        input.onchange = function(event) {
            var file = event.target.files[0];
            if (file) {
                if (format === 'json') {
                    var reader = new FileReader();
                    reader.onload = function(e) {
                        try {
                            var importData = JSON.parse(e.target.result);
                            if (!importData.rules || !Array.isArray(importData.rules)) {
                                $scope.$apply(function() {
                                    $scope.actionFailed = false;
                                    $scope.actionSuccess = true;
                                    $scope.errorMessage = "Invalid import file format. Please select a valid firewall rules export file.";
                                });
                                return;
                            }
                            uploadImportFile(file);
                        } catch (err) {
                            $scope.$apply(function() {
                                $scope.actionFailed = false;
                                $scope.actionSuccess = true;
                                $scope.errorMessage = "Invalid JSON file. Please select a valid firewall rules export file.";
                            });
                        }
                    };
                    reader.readAsText(file);
                } else {
                    uploadImportFile(file);
                }
            }
        };
        document.body.appendChild(input);
        input.click();
        document.body.removeChild(input);
    };

    function uploadImportFile(file) {
        $scope.rulesLoading = true;
        $scope.actionFailed = true;
        $scope.actionSuccess = true;

        var formData = new FormData();
        formData.append('import_file', file);

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': undefined
            },
            transformRequest: angular.identity
        };

        $http.post("/firewall/importFirewallRules", formData, config).then(importSuccess, importError);

        function importSuccess(response) {
            $scope.rulesLoading = false;
            var res = response.data;
            if (typeof res === 'string') {
                try { res = JSON.parse(res); } catch (e) { res = {}; }
            }
            if (res && res.importStatus === 1) {
                $scope.actionFailed = true;
                $scope.actionSuccess = false;
                populateCurrentRecords();
                var summary = "Import completed successfully!\nImported: " + (res.imported_count || 0) + " rules\nSkipped: " + (res.skipped_count || 0) + " rules\nErrors: " + (res.error_count || 0) + " rules";
                if (res.errors && res.errors.length > 0) {
                    summary += "\n\nErrors:\n" + res.errors.join("\n");
                }
                alert(summary);
            } else {
                $scope.actionFailed = false;
                $scope.actionSuccess = true;
                $scope.errorMessage = (res && res.error_message) ? res.error_message : "Import failed.";
            }
        }

        function importError() {
            $scope.rulesLoading = false;
            $scope.actionFailed = false;
            $scope.actionSuccess = true;
            $scope.errorMessage = "Could not connect to server. Please refresh this page.";
        }
    }

    $scope.populateCurrentRecords = populateCurrentRecords;

});


/* Java script code to ADD Firewall Rules */

/* Java script code to Secure SSH */

app.controller('secureSSHCTRL', function ($scope, $http) {

    $scope.couldNotSave = true;
    $scope.detailsSaved = true;
    $scope.couldNotConnect = true;
    $scope.secureSSHLoading = true;
    $scope.keyDeleted = true;
    $scope.keyBox = true;
    $scope.showKeyBox = false;
    $scope.saveKeyBtn = true;
    $scope.sshPort = "22"; // Initialize with default SSH port as string

    $scope.addKey = function () {
        $scope.saveKeyBtn = false;
        $scope.showKeyBox = true;
        $scope.keyBox = false;
    };


    getSSHConfigs();
    populateCurrentKeys();

    // Checking root login

    var rootLogin = false;

    $('#rootLogin').change(function () {
        rootLogin = $(this).prop('checked');
    });


    function getSSHConfigs() {

        $scope.couldNotSave = true;
        $scope.detailsSaved = true;
        $scope.couldNotConnect = true;
        $scope.secureSSHLoading = false;

        url = "/firewall/getSSHConfigs";

        var data = {
            type: "1",
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.sshPort = response.data.sshPort;

            if (response.data.permitRootLogin == 1) {
                $('#rootLogin').prop('checked', true);
                rootLogin = true;
                $scope.couldNotSave = true;
                $scope.detailsSaved = true;
                $scope.couldNotConnect = true;
                $scope.secureSSHLoading = true;
            }
            else {
                $scope.errorMessage = response.data.error_message;
                $scope.couldNotSave = true;
                $scope.detailsSaved = true;
                $scope.couldNotConnect = true;
                $scope.secureSSHLoading = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;

        }

    }

    $scope.saveChanges = function () {

        $scope.couldNotSave = true;
        $scope.detailsSaved = true;
        $scope.couldNotConnect = true;
        $scope.secureSSHLoading = false;

        url = "/firewall/saveSSHConfigs";

        var data = {
            type: "1",
            sshPort: $scope.sshPort,
            rootLogin: rootLogin
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.saveStatus == 1) {
                $scope.couldNotSave = true;
                $scope.detailsSaved = false;
                $scope.couldNotConnect = true;
                $scope.secureSSHLoading = true;
            }
            else {

                $scope.couldNotSave = false;
                $scope.detailsSaved = true;
                $scope.couldNotConnect = true;
                $scope.secureSSHLoading = true;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotSave = true;
            $scope.detailsSaved = true;
            $scope.couldNotConnect = false;
            $scope.secureSSHLoading = true;

        }
    };


    function populateCurrentKeys() {

        url = "/firewall/getSSHConfigs";

        var data = {
            type: "2"
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

    $scope.deleteKey = function (key) {

        $scope.secureSSHLoading = false;

        url = "/firewall/deleteSSHKey";

        var data = {
            key: key,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.delete_status === 1) {
                $scope.secureSSHLoading = true;
                $scope.keyDeleted = false;
                populateCurrentKeys();
            }
            else {
                $scope.couldNotConnect = false;
                $scope.secureSSHLoading = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;
            $scope.secureSSHLoading = true;

        }


    }

    $scope.saveKey = function (key) {

        $scope.secureSSHLoading = false;

        url = "/firewall/addSSHKey";

        var data = {
            key: $scope.keyData,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            if (response.data.add_status === 1) {
                $scope.secureSSHLoading = true;
                $scope.saveKeyBtn = true;
                $scope.showKeyBox = false;
                $scope.keyBox = true;


                populateCurrentKeys();
            }
            else {
                $scope.secureSSHLoading = true;
                $scope.saveKeyBtn = false;
                $scope.showKeyBox = true;
                $scope.keyBox = true;
                $scope.couldNotConnect = false;
                $scope.secureSSHLoading = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.secureSSHLoading = true;
            $scope.saveKeyBtn = false;
            $scope.showKeyBox = true;
            $scope.keyBox = true;
            $scope.couldNotConnect = false;
            $scope.secureSSHLoading = true;

        }


    }

});

/* Java script code to Secure SSH */

/* Java script code for ModSec */

app.controller('modSec', function ($scope, $http, $timeout, $window) {

    $scope.modSecNotifyBox = true;
    $scope.modeSecInstallBox = true;
    $scope.modsecLoading = true;
    $scope.failedToStartInallation = true;
    $scope.couldNotConnect = true;
    $scope.modSecSuccessfullyInstalled = true;
    $scope.installationFailed = true;


    $scope.installModSec = function () {

        $scope.modSecNotifyBox = true;
        $scope.modeSecInstallBox = true;
        $scope.modsecLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.modSecSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/firewall/installModSec";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.installModSec === 1) {

                $scope.modSecNotifyBox = true;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                getRequestStatus();

            }
            else {
                $scope.errorMessage = response.data.error_message;

                $scope.modSecNotifyBox = false;
                $scope.modeSecInstallBox = true;
                $scope.modsecLoading = true;
                $scope.failedToStartInallation = false;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.modSecNotifyBox = false;
            $scope.modeSecInstallBox = false;
            $scope.modsecLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.modSecSuccessfullyInstalled = true;
            $scope.installationFailed = true;
        }

    };

    function getRequestStatus() {

        $scope.modSecNotifyBox = true;
        $scope.modeSecInstallBox = false;
        $scope.modsecLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.modSecSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/firewall/installStatusModSec";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 0) {

                $scope.modSecNotifyBox = true;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                $scope.requestData = response.data.requestStatus;
                $timeout(getRequestStatus, 1000);
            }
            else {
                // Notifications
                $timeout.cancel();
                $scope.modSecNotifyBox = false;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = true;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;

                $scope.requestData = response.data.requestStatus;

                if (response.data.installed === 0) {
                    $scope.installationFailed = false;
                    $scope.errorMessage = response.data.error_message;
                } else {
                    $scope.modSecSuccessfullyInstalled = false;
                    $timeout(function () {
                        $window.location.reload();
                    }, 3000);
                }

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.modSecNotifyBox = false;
            $scope.modeSecInstallBox = false;
            $scope.modsecLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.modSecSuccessfullyInstalled = true;
            $scope.installationFailed = true;


        }

    }

    ///// ModSec configs

    $scope.modsecurity_status = false;
    $scope.SecAuditEngine = false;
    $scope.SecRuleEngine = false;

    // Initialize change handlers after DOM is ready
    $timeout(function() {
        $('#modsecurity_status').change(function () {
            $scope.modsecurity_status = $(this).prop('checked');
            $scope.$apply();
        });

        $('#SecAuditEngine').change(function () {
            $scope.SecAuditEngine = $(this).prop('checked');
            $scope.$apply();
        });

        $('#SecRuleEngine').change(function () {
            $scope.SecRuleEngine = $(this).prop('checked');
            $scope.$apply();
        });
    }, 100);

    fetchModSecSettings();
    function fetchModSecSettings() {

        $scope.modsecLoading = false;

        $('#modsecurity_status').prop('checked', false);
        $('#SecAuditEngine').prop('checked', false);
        $('#SecRuleEngine').prop('checked', false);

        url = "/firewall/fetchModSecSettings";

        var phpSelection = $scope.phpSelection;

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.fetchStatus === 1) {

                if (response.data.installed === 1) {

                    if (response.data.modsecurity === 1) {
                        $('#modsecurity_status').prop('checked', true);
                        $scope.modsecurity_status = true;
                    }
                    if (response.data.SecAuditEngine === 1) {
                        $('#SecAuditEngine').prop('checked', true);
                        $scope.SecAuditEngine = true;
                    }
                    if (response.data.SecRuleEngine === 1) {
                        $('#SecRuleEngine').prop('checked', true);
                        $scope.SecRuleEngine = true;
                    }

                    $scope.SecDebugLogLevel = response.data.SecDebugLogLevel;
                    $scope.SecAuditLogParts = response.data.SecAuditLogParts;
                    $scope.SecAuditLogRelevantStatus = response.data.SecAuditLogRelevantStatus;
                    $scope.SecAuditLogType = response.data.SecAuditLogType;

                }

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;
        }

    }


    /////

    /// Save ModSec Changes

    $scope.failedToSave = true;
    $scope.successfullySaved = true;

    $scope.saveModSecConfigurations = function () {

        $scope.failedToSave = true;
        $scope.successfullySaved = true;
        $scope.modsecLoading = false;
        $scope.couldNotConnect = true;


        url = "/firewall/saveModSecConfigurations";

        var data = {
            modsecurity_status: $scope.modsecurity_status,
            SecAuditEngine: $scope.SecAuditEngine,
            SecRuleEngine: $scope.SecRuleEngine,
            SecDebugLogLevel: $scope.SecDebugLogLevel,
            SecAuditLogParts: $scope.SecAuditLogParts,
            SecAuditLogRelevantStatus: $scope.SecAuditLogRelevantStatus,
            SecAuditLogType: $scope.SecAuditLogType,
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.saveStatus === 1) {

                $scope.failedToSave = true;
                $scope.successfullySaved = false;
                $scope.modsecLoading = true;
                $scope.couldNotConnect = true;

            }
            else {
                $scope.errorMessage = response.data.error_message;

                $scope.failedToSave = false;
                $scope.successfullySaved = true;
                $scope.modsecLoading = true;
                $scope.couldNotConnect = true;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.failedToSave = true;
            $scope.successfullySaved = false;
            $scope.modsecLoading = true;
            $scope.couldNotConnect = true;
        }


    };

});


app.controller('modSecRules', function ($scope, $http) {

    $scope.modsecLoading = true;
    $scope.rulesSaved = true;
    $scope.couldNotConnect = true;
    $scope.couldNotSave = true;


    fetchModSecRules();
    function fetchModSecRules() {

        $scope.modsecLoading = false;
        $scope.modsecLoading = true;
        $scope.rulesSaved = true;
        $scope.couldNotConnect = true;


        url = "/firewall/fetchModSecRules";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.modSecInstalled === 1) {

                $scope.currentModSecRules = response.data.currentModSecRules;

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;
        }

    }

    $scope.saveModSecRules = function () {

        $scope.modsecLoading = false;
        $scope.rulesSaved = true;
        $scope.couldNotConnect = true;
        $scope.couldNotSave = true;


        url = "/firewall/saveModSecRules";

        var data = {
            modSecRules: $scope.currentModSecRules
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.saveStatus === 1) {

                $scope.rulesSaved = false;
                $scope.couldNotConnect = true;
                $scope.couldNotSave = true;

            } else {
                $scope.rulesSaved = true;
                $scope.couldNotConnect = true;
                $scope.couldNotSave = false;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;
            $scope.rulesSaved = true;
            $scope.couldNotConnect = false;
            $scope.couldNotSave = true;
        }
    }

});


/* Java script code for ModSec */

app.controller('modSecRulesPack', function ($scope, $http, $timeout, $window) {

    $scope.modsecLoading = true;
    $scope.owaspDisable = true;
    $scope.comodoDisable = true;


    //

    $scope.installationQuote = true;
    $scope.couldNotConnect = true;
    $scope.installationFailed = true;
    $scope.installationSuccess = true;
    $scope.ruleFiles = true;

    /////

    var owaspInstalled = false;
    var comodoInstalled = false;
    var updatingOWASPStatus = false;
    var updatingComodoStatus = false;


    $('#owaspInstalled').change(function () {

        // Prevent triggering installation when status check updates the toggle
        if (updatingOWASPStatus) {
            return;
        }

        owaspInstalled = $(this).prop('checked');
        $scope.ruleFiles = true;

        if (owaspInstalled === true) {
            installModSecRulesPack('installOWASP');
        } else {
            installModSecRulesPack('disableOWASP');
        }
    });

    $('#comodoInstalled').change(function () {

        // Prevent triggering installation when status check updates the toggle
        if (updatingComodoStatus) {
            return;
        }

        $scope.ruleFiles = true;
        comodoInstalled = $(this).prop('checked');

        if (comodoInstalled === true) {
            installModSecRulesPack('installComodo');
        } else {
            installModSecRulesPack('disableComodo');
        }
    });


    getOWASPAndComodoStatus(true);
    function getOWASPAndComodoStatus(updateToggle, showLoader) {

        // Only show loader if explicitly requested (during installations)
        if (showLoader === true) {
            $scope.modsecLoading = false;
        }


        url = "/firewall/getOWASPAndComodoStatus";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.modSecInstalled === 1) {

                if (updateToggle === true) {

                    // Set flags to prevent change event from triggering installation
                    updatingOWASPStatus = true;
                    updatingComodoStatus = true;

                    if (response.data.owaspInstalled === 1) {
                        $('#owaspInstalled').prop('checked', true);
                        $scope.owaspDisable = false;
                        owaspInstalled = true;
                    } else {
                        $('#owaspInstalled').prop('checked', false);
                        $scope.owaspDisable = true;
                        owaspInstalled = false;
                    }
                    if (response.data.comodoInstalled === 1) {
                        $('#comodoInstalled').prop('checked', true);
                        $scope.comodoDisable = false;
                        comodoInstalled = true;
                    } else {
                        $('#comodoInstalled').prop('checked', false);
                        $scope.comodoDisable = true;
                        comodoInstalled = false;
                    }

                } else {

                    if (response.data.owaspInstalled === 1) {
                        $scope.owaspDisable = false;
                        owaspInstalled = true;
                    } else {
                        $scope.owaspDisable = true;
                        owaspInstalled = false;
                    }
                    if (response.data.comodoInstalled === 1) {
                        $scope.comodoDisable = false;
                        comodoInstalled = true;
                    } else {
                        $scope.comodoDisable = true;
                        comodoInstalled = false;
                    }
                }

            }

            // Always reset flags after status check completes
            $timeout(function() {
                updatingOWASPStatus = false;
                updatingComodoStatus = false;
            }, 100);

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;
            // Reset flags even on error
            updatingOWASPStatus = false;
            updatingComodoStatus = false;
        }

    }

    /////

    function installModSecRulesPack(packName) {

        $scope.modsecLoading = false;

        url = "/firewall/installModSecRulesPack";

        var data = {
            packName: packName
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.installStatus === 1) {

                $scope.modsecLoading = true;

                //

                $scope.installationQuote = true;
                $scope.couldNotConnect = true;
                $scope.installationFailed = true;
                $scope.installationSuccess = false;

                // Update toggle state after a short delay to reflect installation result
                $timeout(function() {
                    getOWASPAndComodoStatus(true);
                }, 500);

            } else {
                $scope.modsecLoading = true;

                //

                $scope.installationQuote = true;
                $scope.couldNotConnect = true;
                $scope.installationFailed = false;
                $scope.installationSuccess = true;

                $scope.errorMessage = response.data.error_message;

                // Update toggle to reflect failed installation (will show OFF)
                $timeout(function() {
                    getOWASPAndComodoStatus(true);
                }, 500);
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;

            //

            $scope.installationQuote = true;
            $scope.couldNotConnect = false;
            $scope.installationFailed = true;
            $scope.installationSuccess = true;
        }


    }

    /////

    $scope.fetchRulesFile = function (packName) {

        $scope.modsecLoading = false;
        $scope.ruleFiles = false;
        $scope.installationQuote = true;
        $scope.couldNotConnect = true;
        $scope.installationFailed = true;
        $scope.installationSuccess = true;

        url = "/firewall/getRulesFiles";

        var data = {
            packName: packName
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.fetchStatus === 1) {
                $scope.records = JSON.parse(response.data.data);
                $scope.installationQuote = true;
                $scope.couldNotConnect = true;
                $scope.installationFailed = true;
                $scope.installationSuccess = false;

            }
            else {
                $scope.installationQuote = true;
                $scope.couldNotConnect = true;
                $scope.installationFailed = false;
                $scope.installationSuccess = true;
                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;
            $scope.installationQuote = true;
            $scope.couldNotConnect = false;
            $scope.installationFailed = true;
            $scope.installationSuccess = true;
        }

    };


    $scope.removeRuleFile = function (fileName, packName, status) {

        $scope.modsecLoading = false;


        url = "/firewall/enableDisableRuleFile";

        var data = {
            packName: packName,
            fileName: fileName,
            status: status
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.saveStatus === 1) {

                $scope.modsecLoading = true;

                //

                $scope.installationQuote = true;
                $scope.couldNotConnect = true;
                $scope.installationFailed = true;
                $scope.installationSuccess = false;

                $scope.fetchRulesFile(packName);

            } else {
                $scope.modsecLoading = true;

                //

                $scope.installationQuote = true;
                $scope.couldNotConnect = true;
                $scope.installationFailed = false;
                $scope.installationSuccess = true;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;

            //

            $scope.installationQuote = true;
            $scope.couldNotConnect = false;
            $scope.installationFailed = true;
            $scope.installationSuccess = true;
        }

    }


});


/* Java script code for ModSec */


/* Java script code for CSF */

app.controller('csf', function ($scope, $http, $timeout, $window) {

    $scope.csfLoading = true;
    $scope.modeSecInstallBox = true;
    $scope.modsecLoading = true;
    $scope.failedToStartInallation = true;
    $scope.couldNotConnect = true;
    $scope.modSecSuccessfullyInstalled = true;
    $scope.installationFailed = true;


    $scope.installCSF = function () {

        $scope.modSecNotifyBox = true;
        $scope.modeSecInstallBox = false;
        $scope.modsecLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.modSecSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/firewall/installCSF";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.installStatus === 1) {

                $scope.modSecNotifyBox = true;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                getRequestStatus();

            }
            else {
                $scope.errorMessage = response.data.error_message;

                $scope.modSecNotifyBox = false;
                $scope.modeSecInstallBox = true;
                $scope.modsecLoading = true;
                $scope.failedToStartInallation = false;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.modSecNotifyBox = false;
            $scope.modeSecInstallBox = false;
            $scope.modsecLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.modSecSuccessfullyInstalled = true;
            $scope.installationFailed = true;
        }

    };
    function getRequestStatus() {

        $scope.modSecNotifyBox = true;
        $scope.modeSecInstallBox = false;
        $scope.modsecLoading = false;
        $scope.failedToStartInallation = true;
        $scope.couldNotConnect = true;
        $scope.modSecSuccessfullyInstalled = true;
        $scope.installationFailed = true;

        url = "/firewall/installStatusCSF";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {


            if (response.data.abort === 0) {

                $scope.modSecNotifyBox = true;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = false;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;
                $scope.modSecSuccessfullyInstalled = true;
                $scope.installationFailed = true;

                $scope.requestData = response.data.requestStatus;
                $timeout(getRequestStatus, 1000);
            }
            else {
                // Notifications
                $timeout.cancel();
                $scope.modSecNotifyBox = false;
                $scope.modeSecInstallBox = false;
                $scope.modsecLoading = true;
                $scope.failedToStartInallation = true;
                $scope.couldNotConnect = true;

                $scope.requestData = response.data.requestStatus;

                if (response.data.installed === 0) {
                    $scope.installationFailed = false;
                    $scope.errorMessage = response.data.error_message;
                } else {
                    $scope.modSecSuccessfullyInstalled = false;
                    $timeout(function () {
                        $window.location.reload();
                    }, 3000);
                }

            }

        }

        function cantLoadInitialDatas(response) {

            $scope.modSecNotifyBox = false;
            $scope.modeSecInstallBox = false;
            $scope.modsecLoading = true;
            $scope.failedToStartInallation = true;
            $scope.couldNotConnect = false;
            $scope.modSecSuccessfullyInstalled = true;
            $scope.installationFailed = true;


        }

    }


    // After installation

    var currentMain = "generalLI";
    var currentChild = "general";

    $scope.activateTab = function (newMain, newChild) {
        // Remove active class from all tabs
        $('.tab-button').removeClass('active');
        
        // Add active class to clicked tab
        $('#' + newMain).addClass('active');
        
        // Hide all tab contents
        $('.tab-content').removeClass('active');
        
        // Show selected tab content
        $('#' + newChild).addClass('active');
        
        currentMain = newMain;
        currentChild = newChild;
    };


    $scope.removeCSF = function () {

        $scope.csfLoading = false;


        url = "/firewall/removeCSF";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.csfLoading = true;


            if (response.data.installStatus === 1) {

                new PNotify({
                    title: 'Successfully removed!',
                    text: 'CSF successfully removed from server, refreshing page in 3 seconds..',
                    type: 'success'
                });

                $timeout(function () {
                    $window.location.reload();
                }, 3000);

            }
            else {
                new PNotify({
                    title: 'Operation failed!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {

            new PNotify({
                title: 'Operation failed!',
                text: 'Could not connect to server, please refresh this page.',
                type: 'error'
            });


        }

    };

    //////// Fetch settings

    //
    var testingMode = false;
    var testingCounter = 0;


    $('#testingMode').change(function () {
        testingMode = $(this).prop('checked');

        if (testingCounter !== 0) {

            if (testingMode === true) {
                $scope.changeStatus('testingMode', 'enable');
            } else {
                $scope.changeStatus('testingMode', 'disable');
            }
        }
        testingCounter = testingCounter + 1;
    });
    //

    //
    var firewallStatus = false;
    var firewallCounter = 0;


    $('#firewallStatus').change(function () {
        firewallStatus = $(this).prop('checked');

        if (firewallCounter !== 0) {

            if (firewallStatus === true) {
                $scope.changeStatus('csf', 'enable');
            } else {
                $scope.changeStatus('csf', 'disable');
            }
        }
        firewallCounter = firewallCounter + 1;
    });
    //


    $scope.fetchSettings = function () {

        $scope.csfLoading = false;

        $('#testingMode').prop('checked', false);
        $('#firewallStatus').prop('checked', false);

        url = "/firewall/fetchCSFSettings";


        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.csfLoading = true;

            if (response.data.fetchStatus === 1) {

                new PNotify({
                    title: 'Successfully fetched!',
                    text: 'CSF settings successfully fetched.',
                    type: 'success'
                });

                if (response.data.testingMode === 1) {
                    $('#testingMode').prop('checked', true);
                }
                if (response.data.firewallStatus === 1) {
                    $('#firewallStatus').prop('checked', true);
                }

                $scope.tcpIN = response.data.tcpIN;
                $scope.tcpOUT = response.data.tcpOUT;
                $scope.udpIN = response.data.udpIN;
                $scope.udpOUT = response.data.udpOUT;
            } else {

                new PNotify({
                    title: 'Failed to load!',
                    text: response.data.error_message,
                    type: 'error'
                });

            }

        }

        function cantLoadInitialDatas(response) {
            $scope.csfLoading = true;

            new PNotify({
                title: 'Failed to load!',
                text: 'Failed to fetch CSF settings.',
                type: 'error'
            });
        }

    };
    $scope.fetchSettings();


    $scope.changeStatus = function (controller, status) {

        $scope.csfLoading = false;


        url = "/firewall/changeStatus";


        var data = {
            controller: controller,
            status: status
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.csfLoading = true;

            if (response.data.status === 1) {

                new PNotify({
                    title: 'Success!',
                    text: 'Changes successfully applied.',
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
            $scope.csfLoading = true;

            new PNotify({
                title: 'Failed to load!',
                text: 'Failed to fetch CSF settings.',
                type: 'error'
            });
        }

    };

    $scope.modifyPorts = function (protocol) {

        $scope.csfLoading = false;

        var ports;

        if (protocol === 'TCP_IN') {
            ports = $scope.tcpIN;
        } else if (protocol === 'TCP_OUT') {
            ports = $scope.tcpOUT;
        } else if (protocol === 'UDP_IN') {
            ports = $scope.udpIN;
        } else if (protocol === 'UDP_OUT') {
            ports = $scope.udpOUT;
        }


        url = "/firewall/modifyPorts";


        var data = {
            protocol: protocol,
            ports: ports
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.csfLoading = true;

            if (response.data.status === 1) {

                new PNotify({
                    title: 'Success!',
                    text: 'Changes successfully applied.',
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
            $scope.csfLoading = true;

            new PNotify({
                title: 'Failed to load!',
                text: 'Failed to fetch CSF settings.',
                type: 'error'
            });
        }

    };

    $scope.modifyIPs = function (mode) {

        $scope.csfLoading = false;

        var ipAddress;

        if (mode === 'allowIP') {
            ipAddress = $scope.allowIP;
        } else if (mode === 'blockIP') {
            ipAddress = $scope.blockIP;
        }


        url = "/firewall/modifyIPs";


        var data = {
            mode: mode,
            ipAddress: ipAddress
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.csfLoading = true;

            if (response.data.status === 1) {

                new PNotify({
                    title: 'Success!',
                    text: 'Changes successfully applied.',
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
            $scope.csfLoading = true;

            new PNotify({
                title: 'Failed to load!',
                text: 'Failed to fetch CSF settings.',
                type: 'error'
            });
        }

    };

});


/* Imunify */

app.controller('installImunify', function ($scope, $http, $timeout, $window) {

    $scope.installDockerStatus = true;
    $scope.installBoxGen = true;
    $scope.dockerInstallBTN = false;

    $scope.submitinstallImunify = function () {

        $scope.installDockerStatus = false;
        $scope.installBoxGen = true;
        $scope.dockerInstallBTN = true;

        url = "/firewall/submitinstallImunify";

        var data = {
            key: $scope.key
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                $scope.installBoxGen = false;
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
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };

    function getRequestStatus() {
        $scope.installDockerStatus = false;

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
                $scope.installDockerStatus = true;
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
            $scope.installDockerStatus = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    }
});

/* ImunifyAV */

app.controller('installImunifyAV', function ($scope, $http, $timeout, $window) {

    $scope.installDockerStatus = true;
    $scope.installBoxGen = true;
    $scope.dockerInstallBTN = false;

    $scope.submitinstallImunify = function () {

        $scope.installDockerStatus = false;
        $scope.installBoxGen = true;
        $scope.dockerInstallBTN = true;

        url = "/firewall/submitinstallImunifyAV";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.cyberPanelLoading = true;
            if (response.data.status === 1) {
                $scope.installBoxGen = false;
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
            $scope.cyberPanelLoading = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    };

    function getRequestStatus() {
        $scope.installDockerStatus = false;

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
                $scope.installDockerStatus = true;
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
            $scope.installDockerStatus = true;
            new PNotify({
                title: 'Operation Failed!',
                text: 'Could not connect to server, please refresh this page',
                type: 'error'
            });
        }

    }
});


app.controller('litespeed_ent_conf', function ($scope, $http, $timeout, $window){
    $scope.modsecLoading = true;
    $scope.rulesSaved = true;
    $scope.couldNotConnect = true;
    $scope.couldNotSave = true;
    fetchlitespeed_conf();
    function fetchlitespeed_conf() {

        $scope.modsecLoading = false;
        $scope.modsecLoading = true;
        $scope.rulesSaved = true;
        $scope.couldNotConnect = true;


        url = "/firewall/fetchlitespeed_conf";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.status === 1) {

                $scope.currentLitespeed_conf = response.data.currentLitespeed_conf;

            }
            else
            {
                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;
        }

    }



    $scope.saveLitespeed_conf  = function () {
        // alert('test-----------------')

        $scope.modsecLoading = false;
        $scope.rulesSaved = true;
        $scope.couldNotConnect = true;
        $scope.couldNotSave = true;


        url = "/firewall/saveLitespeed_conf";

        var data = {
            modSecRules: $scope.currentLitespeed_conf

        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.modsecLoading = true;

            if (response.data.status === 1) {

                $scope.rulesSaved = false;
                $scope.couldNotConnect = true;
                $scope.couldNotSave = true;

                $scope.currentLitespeed_conf = response.data.currentLitespeed_conf;

            } else {
                $scope.rulesSaved = true;
                $scope.couldNotConnect = false;
                $scope.couldNotSave = false;

                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;
            $scope.rulesSaved = true;
            $scope.couldNotConnect = false;
            $scope.couldNotSave = true;
        }
    }

});

(function() {
    // Do not capture tab clicks – let Angular ng-click run setFirewallTab() so data loads.
    // Only sync tab from hash on load and hashchange (back/forward) via __firewallLoadTab.
    function syncFirewallTabFromHash() {
        var nav = document.getElementById('firewall-tab-nav');
        if (!nav) return;
        var h = (window.location.hash || '').replace(/^#/, '').toLowerCase();
        var tab = 'rules';
        if (h === 'banned-ips' || h === 'banned') tab = 'banned';
        else if (h === 'trusted-ips' || h === 'ssh-whitelist') tab = 'trusted';
        if (window.__firewallLoadTab) {
            try { window.__firewallLoadTab(tab); } catch (e) {}
        }
    }

    /* Initial sync only — hashchange is handled by Angular syncTabFromHash in firewallController
       (multiple listeners were racing and could reset #trusted-ips to #rules). */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', syncFirewallTabFromHash);
    } else {
        syncFirewallTabFromHash();
    }
})();