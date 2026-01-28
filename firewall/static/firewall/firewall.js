/**
 * Created by usman on 9/5/17.
 */

// TEST: Verify file is loading
console.log('🔥🔥🔥 firewall.js FILE LOADED 🔥🔥🔥');
console.log('Timestamp:', new Date().toISOString());
if (typeof app === 'undefined') {
    console.error('❌ ERROR: app (AngularJS module) is not defined!');
} else {
    console.log('✅ app (AngularJS module) is defined');
}

// Global function for inline onclick handler - MUST be defined BEFORE controller
window.handleModifyClick = function(buttonElement, event) {
    console.log('========================================');
    console.log('=== handleModifyClick CALLED ===');
    console.log('========================================');
    console.log('Button:', buttonElement);
    
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    var ip = buttonElement.getAttribute('data-ip');
    var id = buttonElement.getAttribute('data-id');
    console.log('IP:', ip, 'ID:', id);
    
    var controllerEl = document.querySelector('[ng-controller="firewallController"]');
    if (!controllerEl) {
        console.error('Controller element not found');
        alert('Error: Controller not found. Please refresh the page.');
        return false;
    }
    
    var scope = angular.element(controllerEl).scope();
    if (!scope) {
        console.error('AngularJS scope not found');
        alert('Error: AngularJS scope not found. Please refresh the page.');
        return false;
    }
    
    console.log('Scope found, bannedIPs:', scope.bannedIPs ? scope.bannedIPs.length : 0);
    
    if (!scope.bannedIPs || scope.bannedIPs.length === 0) {
        console.error('No bannedIPs found in scope');
        alert('Error: No banned IPs found. Please refresh the page.');
        return false;
    }
    
    var bannedIP = null;
    for (var i = 0; i < scope.bannedIPs.length; i++) {
        if (scope.bannedIPs[i].ip === ip || (id && scope.bannedIPs[i].id == id)) {
            bannedIP = scope.bannedIPs[i];
            console.log('Found bannedIP:', bannedIP);
            break;
        }
    }
    
    if (!bannedIP) {
        console.error('Could not find bannedIP for IP:', ip, 'ID:', id);
        alert('Error: Could not find IP data. IP: ' + ip + ', ID: ' + id);
        return false;
    }
    
    if (!scope.showModifyBannedIPModal) {
        console.error('showModifyBannedIPModal function not found in scope');
        alert('Error: Modify function not found. Please refresh the page.');
        return false;
    }
    
    console.log('Calling showModifyBannedIPModal');
    try {
        scope.$apply(function() {
            scope.showModifyBannedIPModal(bannedIP, event);
        });
    } catch (err) {
        console.error('Error calling showModifyBannedIPModal:', err);
        alert('Error: ' + err.message);
    }
    
    return false;
};

console.log('✅ window.handleModifyClick function defined');
console.log('Function test:', typeof window.handleModifyClick);

// Verify function is available globally
if (typeof window.handleModifyClick === 'undefined') {
    console.error('❌ CRITICAL: window.handleModifyClick was not defined!');
} else {
    console.log('✅ window.handleModifyClick is available and ready');
    // Test that it's callable
    try {
        console.log('Function type:', typeof window.handleModifyClick);
    } catch (e) {
        console.error('Error testing function:', e);
    }
}

// Also make it available immediately on window load
if (typeof window !== 'undefined') {
    window.addEventListener('load', function() {
        console.log('Page loaded - verifying handleModifyClick:', typeof window.handleModifyClick);
    });
}

/* Java script code to ADD Firewall Rules */

app.controller('firewallController', function ($scope, $http, $timeout, $window, $location) {
    console.log('========================================');
    console.log('=== firewallController INITIALIZED ===');
    console.log('========================================');
    console.log('Timestamp:', new Date().toISOString());
    console.log('$scope:', $scope);
    console.log('$timeout:', typeof $timeout);
    console.log('$window:', typeof $window);

    $scope.rulesLoading = true;
    $scope.actionFailed = true;
    $scope.actionSuccess = true;

    $scope.canNotAddRule = true;
    $scope.ruleAdded = true;
    $scope.couldNotConnect = true;
    $scope.rulesDetails = false;

    // Banned IPs variables
    // Check URL hash for active tab (handle #!# pattern from AngularJS)
    var hash = $window.location.hash || $location.hash();
    if (hash) {
        // Remove # or #! or #!# prefix
        hash = hash.replace(/^#!?#?/, '');
        console.log('Initial hash parsed:', hash);
        if (hash === 'bannedips' || hash === 'banned') {
            $scope.activeTab = 'banned';
        } else if (hash === 'rules') {
            $scope.activeTab = 'rules';
        } else {
            $scope.activeTab = 'rules';
        }
    } else {
        $scope.activeTab = 'rules';
    }
    
    // Also listen for hashchange events to handle direct URL navigation
    var hashChangeHandler = function() {
        var currentHash = $window.location.hash;
        var newHash = currentHash.replace(/^#!?#?/, '');
        console.log('Hash changed event - current:', currentHash, 'parsed:', newHash);
        
        // Only update if different from current tab
        if ((newHash === 'bannedips' || newHash === 'banned') && $scope.activeTab !== 'banned') {
            $scope.$apply(function() {
                $scope.activeTab = 'banned';
            });
        } else if (newHash === 'rules' && $scope.activeTab !== 'rules') {
            $scope.$apply(function() {
                $scope.activeTab = 'rules';
            });
        }
    };
    
    $window.addEventListener('hashchange', hashChangeHandler);
    
    // Clean up hash on page load if it has #!# pattern
    $timeout(function() {
        var currentHash = $window.location.hash;
        if (currentHash && currentHash.includes('#!')) {
            var cleanHash = currentHash.replace(/^#!?#?/, '');
            var cleanUrl = $window.location.href.split('#')[0] + '#' + cleanHash;
            if ($window.history && $window.history.replaceState) {
                $window.history.replaceState(null, '', cleanUrl);
                console.log('Cleaned hash from', currentHash, 'to', cleanHash);
            }
        }
    }, 100);
    
    $scope.bannedIPs = [];
    $scope.bannedIPsLoading = false;
    $scope.bannedIPActionFailed = true;
    $scope.bannedIPActionSuccess = true;
    $scope.bannedIPCouldNotConnect = true;
    $scope.banIP = '';
    $scope.banReason = '';
    $scope.banDuration = '24h';

    firewallStatus();

    populateCurrentRecords();
    populateBannedIPs();
    
    // Use MutationObserver to catch buttons as they're created
    var observer = new MutationObserver(function(mutations) {
        var modifyButtons = document.querySelectorAll('.btn-modify');
        if (modifyButtons.length > 0) {
            console.log('MutationObserver: Found', modifyButtons.length, 'Modify buttons');
            modifyButtons.forEach(function(btn) {
                if (!btn.hasAttribute('data-listener-attached')) {
                    btn.setAttribute('data-listener-attached', 'true');
                    console.log('MutationObserver: Attaching listener to button');
                    
                    // Force visibility
                    btn.style.setProperty('display', 'flex', 'important');
                    btn.style.setProperty('visibility', 'visible', 'important');
                    btn.style.setProperty('opacity', '1', 'important');
                    btn.style.setProperty('pointer-events', 'auto', 'important');
                }
            });
        }
    });
    
    // Start observing
    $timeout(function() {
        var container = document.querySelector('[ng-controller="firewallController"]');
        if (container) {
            console.log('Starting MutationObserver on controller container');
            observer.observe(container, {
                childList: true,
                subtree: true
            });
        }
    }, 500);
    
    // Also try immediate setup
    var setupModifyButtons = function() {
        console.log('=== setupModifyButtons CALLED ===');
        var modifyButtons = document.querySelectorAll('.btn-modify');
        console.log('Found', modifyButtons.length, 'Modify buttons in DOM');
        
        modifyButtons.forEach(function(btn, index) {
            if (btn && !btn.hasAttribute('data-listener-attached')) {
                btn.setAttribute('data-listener-attached', 'true');
                console.log('Setting up button', index + ':', btn);
                
                // Force visibility
                btn.style.setProperty('display', 'flex', 'important');
                btn.style.setProperty('visibility', 'visible', 'important');
                btn.style.setProperty('opacity', '1', 'important');
                btn.style.setProperty('pointer-events', 'auto', 'important');
                btn.classList.remove('ng-hide', 'hide', 'disabled');
            }
        });
    };
    
    // Run multiple times to catch buttons
    $timeout(setupModifyButtons, 100);
    $timeout(setupModifyButtons, 500);
    $timeout(setupModifyButtons, 1000);
    $timeout(setupModifyButtons, 2000);
    
    // Also run after bannedIPs load
    $scope.$watch('bannedIPs', function(newVal, oldVal) {
        if (newVal && newVal.length > 0) {
            console.log('=== bannedIPs changed, found', newVal.length, 'IPs ===');
            $timeout(setupModifyButtons, 100);
            $timeout(setupModifyButtons, 500);
        }
    }, true);
    
    // Watch for tab changes and update URL hash (without #!#)
    $scope.$watch('activeTab', function(newTab, oldTab) {
        if (newTab !== oldTab && newTab) {
            // Use replaceState to avoid AngularJS adding #! prefix
            var newHash = newTab === 'banned' ? 'bannedips' : 'rules';
            
            // Get clean base URL (without hash or query params)
            var baseUrl = $window.location.protocol + '//' + 
                         $window.location.host + 
                         $window.location.pathname;
            var newUrl = baseUrl + '#' + newHash;
            
            // Use replaceState to update URL - this bypasses AngularJS hash handling
            if ($window.history && $window.history.replaceState) {
                try {
                    // Use replaceState to set clean hash without AngularJS interference
                    $window.history.replaceState(null, '', newUrl);
                    console.log('Tab changed to:', newTab, 'Hash set to:', newHash);
                    
                    // Small delay to ensure URL is updated, then clean up if AngularJS added #!
                    $timeout(function() {
                        var currentHash = $window.location.hash;
                        if (currentHash && currentHash.includes('#!')) {
                            // AngularJS added #! prefix, clean it up
                            var cleanHash = currentHash.replace(/^#!?#?/, '');
                            var cleanUrl = baseUrl + '#' + cleanHash;
                            $window.history.replaceState(null, '', cleanUrl);
                            console.log('Cleaned AngularJS hashbang from', currentHash, 'to', cleanHash);
                        }
                    }, 50);
                } catch (e) {
                    console.warn('replaceState failed:', e);
                    // Fallback: set hash directly
                    $window.location.hash = newHash;
                }
            } else {
                // Fallback to direct hash setting
                $window.location.hash = newHash;
            }
        }
    });

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

                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = false;
                $scope.couldNotConnect = true;


            }
            else {

                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = false;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;


                $scope.errorMessage = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = true;
            $scope.actionFailed = true;
            $scope.actionSuccess = true;

            $scope.canNotAddRule = true;
            $scope.ruleAdded = true;
            $scope.couldNotConnect = false;


        }

    };

    function populateCurrentRecords() {

        $scope.rulesLoading = false;
        $scope.actionFailed = true;
        $scope.actionSuccess = true;


        url = "/firewall/getCurrentRules";

        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {
            if (response.data.fetchStatus === 1) {
                $scope.rules = JSON.parse(response.data.data);
                $scope.rulesLoading = true;
            }
            else {
                $scope.rulesLoading = true;
                $scope.errorMessage = response.data.error_message;
            }
        }

        function cantLoadInitialDatas(response) {
            $scope.couldNotConnect = false;

        }

    };

    $scope.deleteRule = function (id, proto, port, ruleIP) {

        $scope.rulesLoading = false;

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
                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;


            }
            else {

                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = false;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.rulesLoading = true;
                $scope.errorMessage = response.data.error_message;


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = true;
            $scope.actionFailed = true;
            $scope.actionSuccess = true;

            $scope.canNotAddRule = true;
            $scope.ruleAdded = true;
            $scope.couldNotConnect = false;


        }


    };

    // Modify Firewall Rule Functions
    $scope.handleModifyRuleClick = function(rule, event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        if (!rule) {
            console.error('No rule provided');
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Error',
                    text: 'No rule data provided',
                    type: 'error'
                });
            }
            return false;
        }
        
        $scope.showModifyRuleModal(rule, event);
        return false;
    };

    $scope.showModifyRuleModal = function(rule, event) {
        console.log('=== showModifyRuleModal CALLED ===');
        console.log('Rule:', rule);
        
        if (!rule) {
            console.error('No rule provided');
            return false;
        }
        
        // Get modal element
        var modalElement = document.getElementById('modifyRuleModal');
        if (!modalElement) {
            console.error('Modal element not found');
            alert('Error: Modal element not found. Please refresh the page.');
            return false;
        }
        
        // Set form values
        var idField = document.getElementById('modifyRuleId');
        var nameField = document.getElementById('modifyRuleName');
        var protocolField = document.getElementById('modifyRuleProtocol');
        var ipField = document.getElementById('modifyRuleIP');
        var portField = document.getElementById('modifyRulePort');
        
        if (idField) idField.value = rule.id || '';
        if (nameField) nameField.value = rule.name || '';
        if (protocolField) protocolField.value = rule.proto || 'tcp';
        if (ipField) ipField.value = rule.ipAddress || '';
        if (portField) portField.value = rule.port || '';
        
        // Show modal using AngularJS $timeout
        $timeout(function() {
            // Clean up existing modals/backdrops
            var existingBackdrops = document.querySelectorAll('.modal-backdrop');
            existingBackdrops.forEach(function(b) { b.remove(); });
            
            var existingModals = document.querySelectorAll('.modal.show');
            existingModals.forEach(function(m) {
                m.classList.remove('show');
            });
            
            document.body.classList.remove('modal-open');
            
            // Move modal to body if needed
            if (modalElement.parentElement !== document.body) {
                document.body.appendChild(modalElement);
            }
            
            // Show modal
            modalElement.classList.add('show', 'fade');
            modalElement.style.cssText = 'display: flex !important; position: fixed !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; z-index: 99999 !important; opacity: 1 !important; visibility: visible !important; align-items: center !important; justify-content: center !important;';
            modalElement.removeAttribute('aria-hidden');
            modalElement.setAttribute('aria-hidden', 'false');
            modalElement.setAttribute('aria-modal', 'true');
            
            document.body.classList.add('modal-open');
            document.body.style.overflow = 'hidden';
            
            // Create backdrop
            var backdrop = document.createElement('div');
            backdrop.className = 'modal-backdrop fade show';
            backdrop.style.cssText = 'position: fixed !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; z-index: 99998 !important; background-color: rgba(0, 0, 0, 0.5) !important;';
            backdrop.id = 'modifyRuleModalBackdrop';
            document.body.appendChild(backdrop);
            
            // Handle backdrop click
            backdrop.addEventListener('click', function(e) {
                if (e.target === backdrop) {
                    $scope.closeModifyRuleModal();
                }
            });
            
            // Try jQuery/Bootstrap modal if available
            if (typeof $ !== 'undefined' && $.fn.modal) {
                try {
                    var $modal = $('#modifyRuleModal');
                    if ($modal.length > 0) {
                        if ($modal.parent()[0] !== document.body) {
                            $modal.appendTo('body');
                        }
                        if (!$modal.data('bs.modal')) {
                            $modal.modal({show: false, backdrop: true, keyboard: true});
                        }
                        $modal.modal('show');
                    }
                } catch (e) {
                    console.warn('jQuery modal failed, using direct display:', e);
                }
            }
        }, 10);
    };

    $scope.closeModifyRuleModal = function() {
        var modalElement = document.getElementById('modifyRuleModal');
        if (modalElement) {
            // Try jQuery/Bootstrap modal first
            if (typeof $ !== 'undefined' && $.fn.modal) {
                try {
                    $('#modifyRuleModal').modal('hide');
                } catch (e) {
                    // Fall through to manual cleanup
                }
            }
            
            // Manual cleanup
            modalElement.classList.remove('show', 'fade');
            modalElement.style.display = 'none';
            modalElement.setAttribute('aria-hidden', 'true');
            
            // Remove backdrop
            var backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(function(b) { b.remove(); });
            
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
        }
    };

    $scope.modifyRule = function() {
        var ruleId = document.getElementById('modifyRuleId').value;
        var ruleName = document.getElementById('modifyRuleName').value.trim();
        var ruleProtocol = document.getElementById('modifyRuleProtocol').value;
        var ruleIP = document.getElementById('modifyRuleIP').value.trim();
        var rulePort = document.getElementById('modifyRulePort').value.trim();

        // Validation
        if (!ruleName) {
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Validation Error',
                    text: 'Please enter a rule name',
                    type: 'error'
                });
            } else {
                alert('Please enter a rule name');
            }
            return;
        }

        if (!ruleProtocol || (ruleProtocol !== 'tcp' && ruleProtocol !== 'udp')) {
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Validation Error',
                    text: 'Please select a valid protocol (TCP or UDP)',
                    type: 'error'
                });
            } else {
                alert('Please select a valid protocol');
            }
            return;
        }

        if (!ruleIP) {
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Validation Error',
                    text: 'Please enter an IP address',
                    type: 'error'
                });
            } else {
                alert('Please enter an IP address');
            }
            return;
        }

        if (!rulePort) {
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Validation Error',
                    text: 'Please enter a port number',
                    type: 'error'
                });
            } else {
                alert('Please enter a port number');
            }
            return;
        }

        $scope.rulesLoading = false;
        $scope.actionFailed = true;
        $scope.actionSuccess = true;
        $scope.couldNotConnect = true;

        var url = "/firewall/modifyRule";
        var data = {
            id: ruleId,
            ruleName: ruleName,
            ruleProtocol: ruleProtocol,
            rulePort: rulePort,
            ruleIP: ruleIP
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(function(response) {
            $scope.rulesLoading = true;
            
            if (response.data && response.data.modify_status === 1) {
                // Close modal
                $scope.closeModifyRuleModal();
                
                // Refresh rules list
                populateCurrentRecords();
                
                $scope.actionFailed = true;
                $scope.actionSuccess = false;
                $scope.canNotAddRule = true;
                $scope.ruleAdded = false;
                $scope.couldNotConnect = true;
                
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Success!',
                        text: 'Firewall rule modified successfully',
                        type: 'success'
                    });
                }
            } else {
                $scope.actionFailed = false;
                $scope.actionSuccess = true;
                $scope.errorMessage = (response.data && response.data.error_message) || 'Failed to modify firewall rule';
                
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Error!',
                        text: (response.data && response.data.error_message) || 'Failed to modify firewall rule',
                        type: 'error'
                    });
                }
            }
        }, function(error) {
            $scope.rulesLoading = true;
            $scope.couldNotConnect = false;
            
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Connection Error',
                    text: 'Could not connect to server. Please refresh this page.',
                    type: 'error'
                });
            }
        });
    };

    // Make modify rule functions available globally
    window.showModifyRuleModalScope = $scope.showModifyRuleModal;
    window.closeModifyRuleModalScope = $scope.closeModifyRuleModal;
    window.modifyRuleScope = $scope.modifyRule;

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


                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = false;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;


            }
            else {

                $scope.rulesLoading = true;
                $scope.actionFailed = false;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = true;
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


                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = false;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.rulesDetails = false;

                firewallStatus();


            }
            else {

                $scope.rulesLoading = true;
                $scope.actionFailed = false;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = true;
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


                $scope.rulesLoading = true;
                $scope.actionFailed = true;
                $scope.actionSuccess = false;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.rulesDetails = true;

                firewallStatus();


            }
            else {

                $scope.rulesLoading = true;
                $scope.actionFailed = false;
                $scope.actionSuccess = true;

                $scope.canNotAddRule = true;
                $scope.ruleAdded = true;
                $scope.couldNotConnect = true;

                $scope.errorMessage = response.data.error_message;


            }

        }

        function cantLoadInitialDatas(response) {

            $scope.rulesLoading = true;
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
                    $scope.rulesDetails = false;
                    $scope.status = "ON";
                }
                else {
                    $scope.rulesDetails = true;
                    $scope.status = "OFF";
                }
            }
            else {

                $scope.rulesDetails = true;
                $scope.status = "OFF";
            }


        }

        function cantLoadInitialDatas(response) {

            $scope.couldNotConnect = false;


        }

    };


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
    var counterOWASP = 0;
    var counterComodo = 0;


    $('#owaspInstalled').change(function () {

        owaspInstalled = $(this).prop('checked');
        $scope.ruleFiles = true;

        if (counterOWASP !== 0) {
            if (owaspInstalled === true) {
                installModSecRulesPack('installOWASP');
            } else {
                installModSecRulesPack('disableOWASP')
            }
        }

        counterOWASP = counterOWASP + 1;
    });

    $('#comodoInstalled').change(function () {

        $scope.ruleFiles = true;
        comodoInstalled = $(this).prop('checked');

        if (counterComodo !== 0) {

            if (comodoInstalled === true) {
                installModSecRulesPack('installComodo');
            } else {
                installModSecRulesPack('disableComodo')
            }
        }

        counterComodo = counterComodo + 1;

    });


    getOWASPAndComodoStatus(true);
    function getOWASPAndComodoStatus(updateToggle) {

        $scope.modsecLoading = false;


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

        }

        function cantLoadInitialDatas(response) {
            $scope.modsecLoading = true;
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

                getOWASPAndComodoStatus(false);

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

    // Banned IPs Functions
    function populateBannedIPs() {
        $scope.bannedIPsLoading = true;
        var url = "/firewall/getBannedIPs";
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, {}, config).then(function(response) {
            $scope.bannedIPsLoading = false;
            if (response.data.status === 1) {
                $scope.bannedIPs = response.data.bannedIPs || [];
                
                // Ensure Modify buttons are visible after data loads
                $timeout(function() {
                    var modifyButtons = document.querySelectorAll('.btn-modify');
                    modifyButtons.forEach(function(btn) {
                        btn.style.display = 'flex';
                        btn.style.visibility = 'visible';
                        btn.style.opacity = '1';
                    });
                    console.log('Ensured', modifyButtons.length, 'Modify buttons are visible');
                }, 100);
            } else {
                $scope.bannedIPs = [];
                $scope.bannedIPActionFailed = false;
                $scope.bannedIPErrorMessage = response.data.error_message;
            }
        }, function(error) {
            $scope.bannedIPsLoading = false;
            $scope.bannedIPCouldNotConnect = false;
        });
    }

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
            if (response.data.status === 1) {
                $scope.bannedIPActionSuccess = false;
                $scope.banIP = '';
                $scope.banReason = '';
                $scope.banDuration = '24h';
                populateBannedIPs(); // Refresh the list
            } else {
                $scope.bannedIPActionFailed = false;
                $scope.bannedIPErrorMessage = response.data.error_message;
            }
        }, function(error) {
            $scope.bannedIPsLoading = false;
            $scope.bannedIPCouldNotConnect = false;
        });
    };

    $scope.removeBannedIP = function(id, ip) {
        if (!confirm('Are you sure you want to unban IP address ' + ip + '?')) {
            return;
        }

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
    };

    // Make function available globally for onclick fallback - uses data attributes
    window.showModifyModal = function(buttonElement) {
        console.log('========================================');
        console.log('=== ONCLICK FALLBACK TRIGGERED ===');
        console.log('========================================');
        console.log('Button element:', buttonElement);
        console.log('Button data-ip:', buttonElement ? buttonElement.getAttribute('data-ip') : 'null');
        console.log('Button data-id:', buttonElement ? buttonElement.getAttribute('data-id') : 'null');
        try {
            // Get data from button attributes first (most reliable)
            var ip = buttonElement.getAttribute('data-ip');
            var id = buttonElement.getAttribute('data-id');
            
            var bannedIP = null;
            
            // Try to get from AngularJS scope
            var row = buttonElement.closest('tr');
            if (row) {
                var scope = angular.element(row).scope();
                if (scope) {
                    bannedIP = scope.bannedIP || (scope.$parent && scope.$parent.bannedIP);
                }
            }
            
            // If not found in scope, try to find by IP/id from controller scope
            if (!bannedIP && ip) {
                var controllerElement = document.querySelector('[ng-controller="firewallController"]');
                if (controllerElement) {
                    var controllerScope = angular.element(controllerElement).scope();
                    if (controllerScope && controllerScope.bannedIPs) {
                        for (var i = 0; i < controllerScope.bannedIPs.length; i++) {
                            if (controllerScope.bannedIPs[i].ip === ip || 
                                (id && controllerScope.bannedIPs[i].id == id)) {
                                bannedIP = controllerScope.bannedIPs[i];
                                break;
                            }
                        }
                    }
                }
            }
            
            if (bannedIP) {
                console.log('Found bannedIP:', bannedIP);
                var controllerElement = document.querySelector('[ng-controller="firewallController"]');
                if (controllerElement) {
                    var controllerScope = angular.element(controllerElement).scope();
                    if (controllerScope && controllerScope.showModifyBannedIPModal) {
                        controllerScope.$apply(function() {
                            controllerScope.showModifyBannedIPModal(bannedIP);
                        });
                    } else {
                        // Direct call if $apply not available
                        if (controllerScope.showModifyBannedIPModal) {
                            controllerScope.showModifyBannedIPModal(bannedIP);
                        }
                    }
                }
            } else {
                console.error('Could not find bannedIP for IP:', ip, 'ID:', id);
                alert('Error: Could not find IP data. Please refresh the page.');
            }
        } catch (error) {
            console.error('Error in onclick fallback:', error);
            alert('Error opening modify dialog: ' + error.message);
        }
    };
    
    // Make showModifyBannedIPModal available globally for debugging
    window.showModifyBannedIPModalGlobal = function(bannedIP) {
        console.log('=== GLOBAL FUNCTION CALLED ===');
        console.log('bannedIP:', bannedIP);
        var controllerElement = document.querySelector('[ng-controller="firewallController"]');
        if (controllerElement) {
            var controllerScope = angular.element(controllerElement).scope();
            if (controllerScope && controllerScope.showModifyBannedIPModal) {
                console.log('Calling scope function');
                controllerScope.$apply(function() {
                    controllerScope.showModifyBannedIPModal(bannedIP, null);
                });
            } else {
                console.error('Controller scope or function not found');
                console.log('controllerScope:', controllerScope);
                console.log('showModifyBannedIPModal exists:', controllerScope ? !!controllerScope.showModifyBannedIPModal : false);
            }
        } else {
            console.error('Controller element not found');
        }
    };
    
    // Test function - call this from console: window.testModifyModal()
    window.testModifyModal = function() {
        console.log('=== TEST FUNCTION CALLED ===');
        var controllerElement = document.querySelector('[ng-controller="firewallController"]');
        console.log('Controller element:', controllerElement);
        if (controllerElement) {
            var controllerScope = angular.element(controllerElement).scope();
            console.log('Controller scope:', controllerScope);
            console.log('bannedIPs:', controllerScope ? controllerScope.bannedIPs : 'null');
            if (controllerScope && controllerScope.bannedIPs && controllerScope.bannedIPs.length > 0) {
                var testIP = controllerScope.bannedIPs[0];
                console.log('Testing with first bannedIP:', testIP);
                if (controllerScope.showModifyBannedIPModal) {
                    controllerScope.$apply(function() {
                        controllerScope.showModifyBannedIPModal(testIP, null);
                    });
                } else {
                    console.error('showModifyBannedIPModal function not found in scope');
                }
            } else {
                console.error('No bannedIPs found');
            }
        } else {
            console.error('Controller element not found');
        }
    };
    
    // Wrapper function for ng-click - MUST be simple and direct
    $scope.handleModifyButtonClick = function(bannedIP, event) {
        console.log('========================================');
        console.log('=== handleModifyButtonClick CALLED ===');
        console.log('========================================');
        console.log('bannedIP:', bannedIP);
        console.log('bannedIP type:', typeof bannedIP);
        console.log('event:', event);
        
        // Prevent default
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        
        if (!bannedIP) {
            console.error('❌ ERROR: No bannedIP provided');
            alert('Error: No IP data provided');
            return false;
        }
        
        console.log('✅ bannedIP is valid, calling showModifyBannedIPModal');
        
        // Direct call - don't check if function exists, just call it
        try {
            $scope.showModifyBannedIPModal(bannedIP, event);
        } catch (err) {
            console.error('❌ ERROR calling showModifyBannedIPModal:', err);
            alert('Error calling showModifyBannedIPModal: ' + err.message);
        }
        
        return false;
    };
    
    // Also create openModifyModal alias since it's expected by the onclick handler
    $scope.openModifyModal = function(bannedIP, event) {
        console.log('=== openModifyModal CALLED (alias) ===');
        console.log('bannedIP:', bannedIP);
        // Call showModifyBannedIPModal directly
        if ($scope.showModifyBannedIPModal) {
            $scope.showModifyBannedIPModal(bannedIP, event);
        } else {
            console.error('showModifyBannedIPModal not found!');
            alert('showModifyBannedIPModal function not found!');
        }
    };
    
    console.log('✅ handleModifyButtonClick function defined in scope');
    console.log('✅ openModifyModal alias created');
    console.log('Function exists check:', typeof $scope.handleModifyButtonClick, typeof $scope.openModifyModal);
    
    // CRITICAL: Define showModifyBannedIPModal FIRST and make it available on window immediately
    $scope.showModifyBannedIPModal = function(bannedIP, event) {
        console.log('========================================');
        console.log('=== showModifyBannedIPModal CALLED ===');
        console.log('========================================');
        console.log('Timestamp:', new Date().toISOString());
        console.log('bannedIP:', JSON.stringify(bannedIP, null, 2));
        console.log('bannedIP type:', typeof bannedIP);
        console.log('bannedIP keys:', bannedIP ? Object.keys(bannedIP) : 'null');
        console.log('event:', event);
        console.log('event type:', typeof event);
        console.log('$scope:', $scope);
        console.log('$scope.activeTab:', $scope.activeTab);
        
        // If bannedIP is not an object, try to find it
        if (!bannedIP || typeof bannedIP !== 'object') {
            console.warn('bannedIP is not an object, trying to find it...');
            if (event && event.target) {
                var btn = event.target.closest('.btn-modify');
                if (btn) {
                    var ip = btn.getAttribute('data-ip');
                    var id = btn.getAttribute('data-id');
                    console.log('Found data-ip:', ip, 'data-id:', id);
                    if ($scope.bannedIPs) {
                        for (var i = 0; i < $scope.bannedIPs.length; i++) {
                            if ($scope.bannedIPs[i].ip === ip || 
                                (id && $scope.bannedIPs[i].id == id)) {
                                bannedIP = $scope.bannedIPs[i];
                                console.log('Found bannedIP:', bannedIP);
                                break;
                            }
                        }
                    }
                }
            }
        }
        
        // Prevent default and stop propagation if event provided
        if (event) {
            console.log('Preventing default and stopping propagation');
            event.preventDefault();
            event.stopPropagation();
        }
        
        if (!bannedIP) {
            console.error('❌ ERROR: No bannedIP data provided');
            console.trace('Stack trace:');
            alert('Error: No IP data provided');
            return false;
        }
        
        console.log('✅ bannedIP validation passed');
        
        // Store bannedIP in scope for debugging
        $scope.currentBannedIP = bannedIP;
        console.log('Stored bannedIP in $scope.currentBannedIP');
        
        // Get modal element immediately
        var modalElement = document.getElementById('modifyBannedIPModal');
        console.log('Modal element lookup:');
        console.log('  - Element found:', !!modalElement);
        console.log('  - Element type:', modalElement ? modalElement.tagName : 'null');
        console.log('  - Element ID:', modalElement ? modalElement.id : 'null');
        
        if (modalElement) {
            console.log('  - Element classes:', modalElement.className);
            console.log('  - Element style.display:', modalElement.style.display);
            console.log('  - Element computed display:', window.getComputedStyle(modalElement).display);
            console.log('  - Element parent:', modalElement.parentElement ? modalElement.parentElement.tagName : 'null');
            console.log('  - Element in DOM:', document.body.contains(modalElement));
        }
        
        if (!modalElement) {
            console.error('❌ ERROR: Modal element not found in DOM');
            alert('ERROR: Modal element not found in DOM!');
            console.log('Searching for modal in DOM...');
            var allModals = document.querySelectorAll('.modal, [id*="modal"], [id*="Modal"]');
            console.log('Found', allModals.length, 'potential modal elements:');
            allModals.forEach(function(m, i) {
                console.log('  Modal', i + ':', m.id, m.className);
            });
            alert('Error: Modal not found. Found ' + allModals.length + ' modals. Please refresh the page.');
            return false;
        }
        
        console.log('✅ Modal element found');
        
        // Check jQuery availability
        console.log('jQuery check:');
        console.log('  - jQuery available:', typeof $ !== 'undefined');
        console.log('  - jQuery version:', typeof $ !== 'undefined' ? $.fn.jquery : 'N/A');
        console.log('  - jQuery modal available:', typeof $ !== 'undefined' && $.fn.modal);
        console.log('  - Bootstrap available:', typeof bootstrap !== 'undefined');
        
        // Use AngularJS $timeout instead of setTimeout for proper digest cycle
        console.log('Setting up $timeout for modal display...');
        $timeout(function() {
            console.log('--- $timeout callback executed ---');
            try {
                console.log('--- Inside try block ---');
                console.log('Modal element still available:', !!modalElement);
                
                // Set modal form values
                console.log('Looking for form fields...');
                var idField = document.getElementById('modifyBannedIPId');
                var ipField = document.getElementById('modifyBannedIPAddress');
                var reasonField = document.getElementById('modifyBannedIPReason');
                var durationField = document.getElementById('modifyBannedIPDuration');
                
                console.log('Form fields lookup results:');
                console.log('  - idField:', !!idField, idField ? idField.id : 'not found');
                console.log('  - ipField:', !!ipField, ipField ? ipField.id : 'not found');
                console.log('  - reasonField:', !!reasonField, reasonField ? reasonField.id : 'not found');
                console.log('  - durationField:', !!durationField, durationField ? durationField.id : 'not found');
                
                if (!idField || !ipField || !reasonField || !durationField) {
                    console.error('❌ ERROR: Modal form fields not found');
                    console.log('Checking modal structure...');
                    var modalCheck = document.getElementById('modifyBannedIPModal');
                    console.log('Modal element exists:', !!modalCheck);
                    if (modalCheck) {
                        console.log('Modal innerHTML length:', modalCheck.innerHTML ? modalCheck.innerHTML.length : 0);
                        console.log('Modal first 1000 chars:', modalCheck.outerHTML.substring(0, 1000));
                        var formCheck = modalCheck.querySelector('form, #modifyBannedIPForm');
                        console.log('Form element in modal:', !!formCheck);
                        if (formCheck) {
                            console.log('Form children:', formCheck.children.length);
                            Array.from(formCheck.children).forEach(function(child, i) {
                                console.log('  Child', i + ':', child.tagName, child.id || child.className);
                            });
                        }
                    }
                    alert('Error: Modal form not found. Please refresh the page.');
                    return;
                }
                
                console.log('✅ All form fields found');
                
                console.log('Setting form field values...');
                idField.value = bannedIP.id || '';
                ipField.value = bannedIP.ip || '';
                ipField.removeAttribute('readonly');
                ipField.removeAttribute('disabled');
                ipField.readOnly = false;
                ipField.disabled = false;
                reasonField.value = bannedIP.reason || '';
                console.log('Form values set:');
                console.log('  - ID:', idField.value);
                console.log('  - IP:', ipField.value);
                console.log('  - Reason:', reasonField.value);
                
                // Set duration - convert expires to duration format
                var duration = bannedIP.duration || 'never';
                console.log('Calculating duration...');
                console.log('  - Initial duration:', duration);
                console.log('  - expires_timestamp:', bannedIP.expires_timestamp);
                console.log('  - banned_on_timestamp:', bannedIP.banned_on_timestamp);
                
                // If we have expires_timestamp, try to calculate duration
                if (bannedIP.expires_timestamp && bannedIP.banned_on_timestamp) {
                    var expiresMs = bannedIP.expires_timestamp;
                    var bannedMs = bannedIP.banned_on_timestamp;
                    var diffMs = expiresMs - bannedMs;
                    var diffHours = diffMs / (1000 * 60 * 60);
                    console.log('  - Diff in hours:', diffHours);
                    
                    if (diffHours <= 1) {
                        duration = '1h';
                    } else if (diffHours <= 6) {
                        duration = '6h';
                    } else if (diffHours <= 12) {
                        duration = '12h';
                    } else if (diffHours <= 24) {
                        duration = '24h';
                    } else if (diffHours <= 48) {
                        duration = '48h';
                    } else if (diffHours <= 168) { // 7 days
                        duration = '7d';
                    } else if (diffHours <= 720) { // 30 days
                        duration = '30d';
                    } else {
                        duration = 'never';
                    }
                    console.log('  - Calculated duration:', duration);
                } else if (bannedIP.expires === 'Never' || !bannedIP.expires_timestamp) {
                    duration = 'never';
                    console.log('  - Using never (no expiration)');
                }
                
                durationField.value = duration;
                console.log('✅ Duration set to:', duration);
                
                console.log('========================================');
                console.log('=== ATTEMPTING TO SHOW MODAL ===');
                console.log('========================================');
                
                // Re-check modal element
                modalElement = document.getElementById('modifyBannedIPModal');
                console.log('Modal element re-check:');
                console.log('  - Found:', !!modalElement);
                console.log('  - Current display:', modalElement ? window.getComputedStyle(modalElement).display : 'N/A');
                console.log('  - Current visibility:', modalElement ? window.getComputedStyle(modalElement).visibility : 'N/A');
                console.log('  - Current opacity:', modalElement ? window.getComputedStyle(modalElement).opacity : 'N/A');
                console.log('  - Current z-index:', modalElement ? window.getComputedStyle(modalElement).zIndex : 'N/A');
                console.log('  - Has show class:', modalElement ? modalElement.classList.contains('show') : false);
                
                // Direct display approach - most reliable
                console.log('Step 1: Cleaning up existing modals/backdrops...');
                
                // Clean up any existing modals/backdrops first
                var existingBackdrops = document.querySelectorAll('.modal-backdrop');
                console.log('  - Found', existingBackdrops.length, 'existing backdrops');
                existingBackdrops.forEach(function(b, i) {
                    console.log('    Removing backdrop', i + ':', b.id || 'no-id');
                    b.remove();
                });
                
                var existingModals = document.querySelectorAll('.modal.show');
                console.log('  - Found', existingModals.length, 'existing open modals');
                existingModals.forEach(function(m, i) {
                    console.log('    Closing modal', i + ':', m.id || 'no-id');
                    m.classList.remove('show');
                });
                
                if (typeof $ !== 'undefined') {
                    $('.modal-backdrop').remove();
                    $('.modal.show').removeClass('show');
                    console.log('  - jQuery cleanup completed');
                }
                document.body.classList.remove('modal-open');
                console.log('  - Removed modal-open from body');
                
                console.log('Step 2: Preparing modal element...');
                // Remove any inline styles that might hide it
                console.log('  - Removing inline styles...');
                modalElement.removeAttribute('style');
                console.log('  - Inline styles removed');
                
                console.log('Step 3: Moving modal to body and setting display properties...');
                
                // CRITICAL: Move modal to body if it's not already there
                if (modalElement.parentElement !== document.body) {
                    console.log('Moving modal to body (currently in:', modalElement.parentElement.tagName + ')');
                    document.body.appendChild(modalElement);
                    console.log('Modal moved to body');
                }
                
                // Show modal directly with all necessary attributes
                modalElement.classList.add('show');
                modalElement.classList.add('fade');
                modalElement.style.cssText = 'display: flex !important; position: fixed !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; z-index: 99999 !important; opacity: 1 !important; visibility: visible !important; align-items: center !important; justify-content: center !important;';
                modalElement.removeAttribute('aria-hidden');
                modalElement.setAttribute('aria-hidden', 'false');
                modalElement.setAttribute('aria-modal', 'true');
                // Force remove aria-hidden again after a brief delay to ensure it sticks
                setTimeout(function() {
                    modalElement.removeAttribute('aria-hidden');
                    modalElement.setAttribute('aria-hidden', 'false');
                }, 50);
                document.body.classList.add('modal-open');
                document.body.style.overflow = 'hidden';
                
                console.log('Modal styles applied:');
                console.log('  - display:', modalElement.style.display);
                console.log('  - position:', modalElement.style.position);
                console.log('  - z-index:', modalElement.style.zIndex);
                console.log('  - opacity:', modalElement.style.opacity);
                console.log('  - visibility:', modalElement.style.visibility);
                console.log('  - has show class:', modalElement.classList.contains('show'));
                console.log('  - body has modal-open:', document.body.classList.contains('modal-open'));
                
                console.log('Step 4: Creating backdrop...');
                // Create and show backdrop
                var backdrop = document.createElement('div');
                backdrop.className = 'modal-backdrop fade show';
                backdrop.style.position = 'fixed';
                backdrop.style.top = '0';
                backdrop.style.left = '0';
                backdrop.style.width = '100%';
                backdrop.style.height = '100%';
                backdrop.style.zIndex = '99998';
                backdrop.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
                backdrop.id = 'modifyBannedIPModalBackdrop';
                document.body.appendChild(backdrop);
                console.log('  - Backdrop created and appended to body');
                console.log('  - Backdrop ID:', backdrop.id);
                console.log('  - Backdrop in DOM:', document.body.contains(backdrop));
                
                // Handle backdrop click to close
                backdrop.addEventListener('click', function(e) {
                    console.log('Backdrop clicked');
                    if (e.target === backdrop) {
                        $scope.closeModifyModal();
                    }
                });
                
                console.log('Step 5: Configuring modal dialog...');
                // Ensure modal dialog is centered and visible
                var modalDialog = modalElement.querySelector('.modal-dialog');
                if (modalDialog) {
                    console.log('  - Modal dialog found');
                    modalDialog.style.zIndex = '100000';
                    modalDialog.style.position = 'relative';
                    modalDialog.style.margin = '1.75rem auto';
                    console.log('  - Dialog styles applied');
                } else {
                    console.error('  - ❌ Modal dialog NOT found!');
                    console.log('  - Modal children:', modalElement.children.length);
                    Array.from(modalElement.children).forEach(function(child, i) {
                        console.log('    Child', i + ':', child.tagName, child.className);
                    });
                }
                
                console.log('========================================');
                console.log('=== MODAL DISPLAY COMPLETE ===');
                console.log('========================================');
                console.log('Final checks:');
                console.log('  - Modal display (computed):', window.getComputedStyle(modalElement).display);
                console.log('  - Modal visibility (computed):', window.getComputedStyle(modalElement).visibility);
                console.log('  - Modal opacity (computed):', window.getComputedStyle(modalElement).opacity);
                console.log('  - Modal z-index (computed):', window.getComputedStyle(modalElement).zIndex);
                console.log('  - Modal in viewport:', modalElement.getBoundingClientRect());
                console.log('  - Backdrop display:', window.getComputedStyle(backdrop).display);
                console.log('  - Body modal-open:', document.body.classList.contains('modal-open'));
                
                // Verify modal is actually visible
                var rect = modalElement.getBoundingClientRect();
                console.log('Modal bounding rect:', {
                    top: rect.top,
                    left: rect.left,
                    width: rect.width,
                    height: rect.height,
                    visible: rect.width > 0 && rect.height > 0
                });
                
                // CRITICAL: Force modal to be visible with multiple approaches
                console.log('=== FORCING MODAL VISIBILITY ===');
                
                // Remove any hiding classes
                modalElement.classList.remove('hide', 'ng-hide', 'hidden');
                
                // Force display with multiple methods
                modalElement.style.setProperty('display', 'block', 'important');
                modalElement.style.setProperty('visibility', 'visible', 'important');
                modalElement.style.setProperty('opacity', '1', 'important');
                modalElement.style.setProperty('z-index', '99999', 'important');
                modalElement.style.setProperty('position', 'fixed', 'important');
                modalElement.removeAttribute('aria-hidden');
                modalElement.setAttribute('aria-hidden', 'false');
                
                // Check parent containers for overflow issues
                var parent = modalElement.parentElement;
                var depth = 0;
                while (parent && depth < 5) {
                    var parentOverflow = window.getComputedStyle(parent).overflow;
                    var parentZIndex = window.getComputedStyle(parent).zIndex;
                    console.log('Parent', depth + ':', parent.tagName, parent.className, 'overflow:', parentOverflow, 'z-index:', parentZIndex);
                    if (parentOverflow === 'hidden') {
                        console.warn('⚠️ Parent has overflow:hidden, might hide modal');
                        parent.style.setProperty('overflow', 'visible', 'important');
                    }
                    parent = parent.parentElement;
                    depth++;
                }
                
                // Final verification
                setTimeout(function() {
                    var finalDisplay = window.getComputedStyle(modalElement).display;
                    var finalVisibility = window.getComputedStyle(modalElement).visibility;
                    var finalOpacity = window.getComputedStyle(modalElement).opacity;
                    console.log('=== FINAL MODAL STATE (after 100ms) ===');
                    console.log('Display:', finalDisplay);
                    console.log('Visibility:', finalVisibility);
                    console.log('Opacity:', finalOpacity);
                    if (finalDisplay === 'none' || finalVisibility === 'hidden' || finalOpacity === '0') {
                        console.error('❌ MODAL IS STILL HIDDEN!');
                        console.error('Trying emergency show...');
                        modalElement.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; z-index: 99999 !important; position: fixed !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important;';
                    } else {
                        console.log('✅ Modal should be visible');
                    }
                }, 100);
                
                // Try jQuery/Bootstrap modal as primary method (most reliable)
                console.log('Step 6: Attempting to show modal...');
                console.log('  - jQuery available:', typeof $ !== 'undefined');
                console.log('  - Bootstrap modal available:', typeof $ !== 'undefined' && $.fn.modal);
                
                if (typeof $ !== 'undefined' && $.fn.modal) {
                    console.log('  - Using jQuery/Bootstrap modal...');
                    var $modal = $('#modifyBannedIPModal');
                    console.log('  - jQuery modal object found:', !!$modal.length);
                    console.log('  - Modal element:', $modal[0]);
                    
                    if ($modal.length === 0) {
                        console.error('  - ❌ Modal element not found by jQuery!');
                        console.log('  - Searching DOM for modal...');
                        var modalCheck = document.getElementById('modifyBannedIPModal');
                        console.log('  - Found by getElementById:', !!modalCheck);
                        if (modalCheck) {
                            console.log('  - Modal parent:', modalCheck.parentElement ? modalCheck.parentElement.tagName : 'null');
                            console.log('  - Modal display:', window.getComputedStyle(modalCheck).display);
                        }
                    } else {
                        // Ensure modal is in body
                        var modalParent = $modal.parent()[0];
                        console.log('  - Modal parent:', modalParent ? modalParent.tagName : 'null');
                        if (modalParent !== document.body) {
                            console.log('  - Moving modal to body...');
                            $modal.appendTo('body');
                            console.log('  - ✅ Modal moved to body');
                        }
                        
                        // CRITICAL: Show modal using Bootstrap - this is the most reliable method
                        console.log('  - Attempting to show modal with Bootstrap...');
                        
                        // Initialize modal if not already initialized
                        if (!$modal.data('bs.modal')) {
                            console.log('  - Initializing Bootstrap modal first...');
                            try {
                                $modal.modal({show: false, backdrop: true, keyboard: true});
                                console.log('  - ✅ Modal initialized');
                            } catch (initErr) {
                                console.warn('  - ⚠️ Modal initialization failed:', initErr);
                            }
                        }
                        
                        // Show using Bootstrap modal
                        try {
                            console.log('  - Calling Bootstrap modal.show()...');
                            alert('About to call Bootstrap modal.show()'); // TEST ALERT
                            $modal.modal('show');
                            console.log('  - ✅ Bootstrap modal.show() called successfully');
                            alert('Bootstrap modal.show() called!'); // TEST ALERT
                            
                            // Force display immediately as backup (don't wait)
                            $modal.addClass('show');
                            $modal[0].style.cssText = 'display: flex !important; position: fixed !important; z-index: 99999 !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; align-items: center !important; justify-content: center !important; opacity: 1 !important; visibility: visible !important;';
                            
                            // Ensure backdrop exists
                            if (!$('.modal-backdrop').length) {
                                var backdrop = $('<div class="modal-backdrop fade show"></div>');
                                backdrop.css({
                                    'position': 'fixed',
                                    'top': '0',
                                    'left': '0',
                                    'width': '100%',
                                    'height': '100%',
                                    'z-index': '99998',
                                    'background-color': 'rgba(0, 0, 0, 0.5)'
                                });
                                $('body').append(backdrop);
                                console.log('  - Created backdrop');
                            }
                            
                            // Force body styles
                            $('body').addClass('modal-open').css('overflow', 'hidden');
                            
                            console.log('  - ✅ Modal display forced');
                            alert('Modal should be visible now! Check if you see it.'); // TEST ALERT
                            
                            // Verify modal is visible after a short delay
                            setTimeout(function() {
                                var modalEl = $modal[0];
                                var isVisible = $modal.hasClass('show') && $modal.is(':visible');
                                var display = window.getComputedStyle(modalEl).display;
                                var visibility = window.getComputedStyle(modalEl).visibility;
                                var opacity = window.getComputedStyle(modalEl).opacity;
                                var zIndex = window.getComputedStyle(modalEl).zIndex;
                                
                                console.log('  - === MODAL VISIBILITY CHECK (after 200ms) ===');
                                console.log('  - Has show class:', $modal.hasClass('show'));
                                console.log('  - jQuery :visible:', $modal.is(':visible'));
                                console.log('  - Display:', display);
                                console.log('  - Visibility:', visibility);
                                console.log('  - Opacity:', opacity);
                                console.log('  - Z-index:', zIndex);
                                console.log('  - In DOM:', document.body.contains(modalEl));
                                
                                if (!isVisible || display === 'none' || visibility === 'hidden' || opacity === '0') {
                                    console.error('  - ❌ MODAL IS STILL NOT VISIBLE!');
                                    console.log('  - Applying emergency CSS override...');
                                    modalEl.style.cssText = 'display: flex !important; position: fixed !important; z-index: 99999 !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; align-items: center !important; justify-content: center !important; opacity: 1 !important; visibility: visible !important;';
                                    modalEl.classList.add('show');
                                    
                                    // Also ensure backdrop exists
                                    if (!$('.modal-backdrop').length) {
                                        var backdrop = $('<div class="modal-backdrop fade show"></div>');
                                        backdrop.css({
                                            'position': 'fixed',
                                            'top': '0',
                                            'left': '0',
                                            'width': '100%',
                                            'height': '100%',
                                            'z-index': '99998',
                                            'background-color': 'rgba(0, 0, 0, 0.5)'
                                        });
                                        $('body').append(backdrop);
                                        console.log('  - Created backdrop manually');
                                    }
                                } else {
                                    console.log('  - ✅ Modal appears to be visible');
                                }
                            }, 200);
                        } catch (modalErr) {
                            console.error('  - ❌ Bootstrap modal.show() failed:', modalErr);
                            console.error('  - Error details:', modalErr.message, modalErr.stack);
                            // Fallback to manual display
                            console.log('  - Using fallback manual display...');
                            $modal.addClass('show').css({
                                'display': 'flex',
                                'position': 'fixed',
                                'z-index': '99999',
                                'top': '0',
                                'left': '0',
                                'width': '100%',
                                'height': '100%',
                                'align-items': 'center',
                                'justify-content': 'center',
                                'opacity': '1',
                                'visibility': 'visible'
                            });
                        }
                    }
                } else {
                    console.warn('  - ❌ jQuery/Bootstrap modal not available!');
                    console.warn('  - jQuery:', typeof $);
                    console.warn('  - $.fn.modal:', typeof $ !== 'undefined' ? typeof $.fn.modal : 'N/A');
                    console.log('  - Using manual display fallback...');
                }
                
                console.log('========================================');
                console.log('=== END OF MODAL DISPLAY LOGIC ===');
                console.log('========================================');
                
                // Try Bootstrap 5 as additional backup
                if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
                    console.log('Also trying Bootstrap 5 modal...');
                    try {
                        var modal = new bootstrap.Modal(modalElement);
                        modal.show();
                    } catch (bsErr) {
                        console.log('Bootstrap 5 modal failed:', bsErr);
                    }
                }
                    console.log('Using manual modal display');
                    modalElement.classList.add('show');
                    modalElement.style.display = 'block';
                    modalElement.removeAttribute('aria-hidden');
                    modalElement.setAttribute('aria-hidden', 'false');
                    modalElement.setAttribute('aria-modal', 'true');
                    document.body.classList.add('modal-open');
                    
                    // Create backdrop
                    var backdrop = document.createElement('div');
                    backdrop.className = 'modal-backdrop fade show';
                    backdrop.id = 'modifyBannedIPModalBackdrop';
                    backdrop.style.position = 'fixed';
                    backdrop.style.top = '0';
                    backdrop.style.left = '0';
                    backdrop.style.zIndex = '99998';
                    backdrop.style.width = '100%';
                    backdrop.style.height = '100%';
                    backdrop.style.backgroundColor = 'rgba(0,0,0,0.5)';
                    document.body.appendChild(backdrop);
                    
                    // Handle backdrop click to close
                    backdrop.addEventListener('click', function() {
                        $scope.closeModifyModal();
                    });
                    
                    // Ensure modal is on top with very high z-index
                    modalElement.style.zIndex = '99999';
                    modalElement.style.position = 'fixed';
                    modalElement.style.top = '0';
                    modalElement.style.left = '0';
                    modalElement.style.width = '100%';
                    modalElement.style.height = '100%';
                    modalElement.style.display = 'flex';
                    modalElement.style.alignItems = 'center';
                    modalElement.style.justifyContent = 'center';
                    
                    // Ensure modal dialog is visible
                    var modalDialog = modalElement.querySelector('.modal-dialog');
                    if (modalDialog) {
                        modalDialog.style.zIndex = '100000';
                        modalDialog.style.position = 'relative';
                    }
                }
            } catch (error) {
                console.error('========================================');
                console.error('❌ ERROR in showModifyBannedIPModal');
                console.error('========================================');
                console.error('Error type:', error.name);
                console.error('Error message:', error.message);
                console.error('Error stack:', error.stack);
                console.error('Error object:', error);
                console.trace('Full stack trace:');
                
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Error',
                        text: 'Failed to open modify dialog: ' + error.message,
                        type: 'error'
                    });
                } else {
                    alert('Error: Failed to open modify dialog - ' + error.message + '\n\nCheck console for details.');
                }
            }
        }, 100);
        
        console.log('=== showModifyBannedIPModal function completed (timeout scheduled) ===');
        return true;
    };
    
    // Make showModifyBannedIPModal available on window immediately after definition
    window.showModifyBannedIPModalScope = $scope.showModifyBannedIPModal;
    window.handleModifyButtonClickScope = $scope.handleModifyButtonClick;
    window.openModifyModalScope = $scope.openModifyModal;
    console.log('✅ All functions available on window:', {
        showModifyBannedIPModal: typeof window.showModifyBannedIPModalScope,
        handleModifyButtonClick: typeof window.handleModifyButtonClickScope,
        openModifyModal: typeof window.openModifyModalScope
    });
    
    $scope.closeModifyModal = function() {
        console.log('=== closeModifyModal called ===');
        
        var modalElement = document.getElementById('modifyBannedIPModal');
        if (!modalElement) {
            console.warn('Modal element not found for closing');
            return;
        }
        
        // Try jQuery/Bootstrap modal first
        if (typeof $ !== 'undefined' && $.fn.modal) {
            try {
                $('#modifyBannedIPModal').modal('hide');
                console.log('Closed modal using Bootstrap');
            } catch (e) {
                console.warn('Bootstrap modal hide failed:', e);
            }
        }
        
        // Manual cleanup
        modalElement.classList.remove('show');
        modalElement.style.display = 'none';
        modalElement.removeAttribute('aria-hidden');
        modalElement.setAttribute('aria-hidden', 'true');
        
        // Remove backdrop
        var backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(function(b) { b.remove(); });
        
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
    };
    
    // Make closeModifyModal available globally for onclick handlers
    window.closeModifyModalGlobal = function() {
        var controllerEl = document.querySelector('[ng-controller=firewallController]');
        if (controllerEl) {
            var scope = angular.element(controllerEl).scope();
            if (scope && scope.closeModifyModal) {
                scope.$apply(function() {
                    scope.closeModifyModal();
                });
                return;
            }
        }
        // Fallback if AngularJS not available
        var modal = document.getElementById('modifyBannedIPModal');
        if (modal) {
            modal.classList.remove('show');
            modal.removeAttribute('aria-hidden');
            modal.setAttribute('aria-hidden', 'true');
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            var backdrops = document.querySelectorAll('.modal-backdrop');
            for (var i = 0; i < backdrops.length; i++) backdrops[i].remove();
        }
    };
    
    // Make modifyBannedIP available globally for onclick handlers
    window.modifyBannedIPGlobal = function() {
        var controllerEl = document.querySelector('[ng-controller=firewallController]');
        if (controllerEl) {
            var scope = angular.element(controllerEl).scope();
            if (scope && scope.modifyBannedIP) {
                scope.$apply(function() {
                    scope.modifyBannedIP();
                });
                return;
            }
        }
        alert('Error: Cannot save changes. Please refresh the page.');
    };
        
        console.log('Modal closed');
        var modalElement = document.getElementById('modifyBannedIPModal');
        var backdrop = document.getElementById('modifyBannedIPModalBackdrop') || document.querySelector('.modal-backdrop');
        
        // Hide modal
        if (modalElement) {
            modalElement.classList.remove('show', 'fade');
            modalElement.style.display = 'none';
            modalElement.removeAttribute('style');
            modalElement.setAttribute('aria-hidden', 'true');
        }
        
        // Remove backdrop
        if (backdrop) {
            backdrop.remove();
        }
        
        // Also remove any jQuery-created backdrops
        if (typeof $ !== 'undefined') {
            $('.modal-backdrop').remove();
            $('#modifyBannedIPModal').modal('hide');
        }
        
        document.body.classList.remove('modal-open');
        console.log('Modal closed');
    };

    $scope.modifyBannedIP = function() {
        var banId = document.getElementById('modifyBannedIPId').value;
        var ipAddress = document.getElementById('modifyBannedIPAddress').value.trim();
        var reason = document.getElementById('modifyBannedIPReason').value.trim();
        var duration = document.getElementById('modifyBannedIPDuration').value;

        if (!ipAddress) {
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Validation Error',
                    text: 'Please enter an IP address',
                    type: 'error'
                });
            } else {
                alert('Please enter an IP address');
            }
            return;
        }

        // Validate IP address format
        var ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:\/(?:[0-9]|[1-2][0-9]|3[0-2]))?$/;
        if (!ipRegex.test(ipAddress)) {
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Validation Error',
                    text: 'Please enter a valid IP address (e.g., 192.168.1.1 or 192.168.1.0/24)',
                    type: 'error'
                });
            } else {
                alert('Please enter a valid IP address');
            }
            return;
        }

        if (!reason) {
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Validation Error',
                    text: 'Please enter a reason for the ban',
                    type: 'error'
                });
            } else {
                alert('Please enter a reason for the ban');
            }
            return;
        }

        $scope.bannedIPsLoading = true;
        $scope.bannedIPActionFailed = true;
        $scope.bannedIPActionSuccess = true;
        $scope.bannedIPCouldNotConnect = true;

        var data = {
            id: banId,
            ip: ipAddress,
            reason: reason,
            duration: duration
        };

        var url = "/firewall/modifyBannedIP";
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };

        $http.post(url, data, config).then(function(response) {
            $scope.bannedIPsLoading = false;
            if (response.data.status === 1) {
                $scope.bannedIPActionSuccess = false;
                $('#modifyBannedIPModal').modal('hide');
                populateBannedIPs(); // Refresh the list
                
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Success!',
                        text: 'Banned IP modified successfully',
                        type: 'success'
                    });
                }
            } else {
                $scope.bannedIPActionFailed = false;
                $scope.bannedIPErrorMessage = response.data.error_message || 'Failed to modify banned IP';
                
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Error!',
                        text: response.data.error_message || 'Failed to modify banned IP',
                        type: 'error'
                    });
                }
            }
        }, function(error) {
            $scope.bannedIPsLoading = false;
            $scope.bannedIPCouldNotConnect = false;
            
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Connection Error',
                    text: 'Could not connect to server. Please refresh this page.',
                    type: 'error'
                });
            }
        });
    };

    $scope.deleteBannedIP = function(id, ip) {
        if (!confirm('Are you sure you want to permanently delete the record for IP address ' + ip + '? This action cannot be undone.')) {
            return;
        }

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
    };

    // Export/Import Banned IPs Functions
    $scope.exportBannedIPs = function () {
        $scope.bannedIPsLoading = false;
        $scope.bannedIPActionFailed = true;
        $scope.bannedIPActionSuccess = true;

        var url = "/firewall/exportBannedIPs";
        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            responseType: 'blob'
        };

        $http.post(url, data, config).then(function(response) {
            $scope.bannedIPsLoading = true;
            
            // Check if response is JSON (error) or file download
            if (response.data instanceof Blob) {
                // Create blob URL and trigger download
                var blob = new Blob([response.data], { type: 'application/json' });
                var url = window.URL.createObjectURL(blob);
                var a = document.createElement('a');
                a.href = url;
                a.download = 'banned_ips_export_' + Math.floor(Date.now() / 1000) + '.json';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                $scope.bannedIPActionFailed = true;
                $scope.bannedIPActionSuccess = false;
                
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Success!',
                        text: 'Banned IPs exported successfully',
                        type: 'success'
                    });
                }
            } else {
                // Handle error response
                try {
                    var errorData = typeof response.data === 'string' ? JSON.parse(response.data) : response.data;
                    if (errorData.exportStatus === 0) {
                        $scope.bannedIPActionFailed = false;
                        $scope.bannedIPActionSuccess = true;
                        $scope.bannedIPErrorMessage = errorData.error_message;
                        
                        if (typeof PNotify !== 'undefined') {
                            new PNotify({
                                title: 'Export Failed',
                                text: errorData.error_message,
                                type: 'error'
                            });
                        }
                    }
                } catch (e) {
                    // If not JSON, try reading as text
                    var reader = new FileReader();
                    reader.onload = function() {
                        try {
                            var errorData = JSON.parse(reader.result);
                            if (errorData.exportStatus === 0) {
                                $scope.bannedIPActionFailed = false;
                                $scope.bannedIPActionSuccess = true;
                                $scope.bannedIPErrorMessage = errorData.error_message;
                            }
                        } catch (e2) {
                            $scope.bannedIPActionFailed = false;
                            $scope.bannedIPActionSuccess = true;
                            $scope.bannedIPErrorMessage = 'Failed to export banned IPs';
                        }
                    };
                    reader.readAsText(response.data);
                }
            }
        }, function(error) {
            $scope.bannedIPsLoading = true;
            $scope.bannedIPActionFailed = false;
            $scope.bannedIPActionSuccess = true;
            $scope.bannedIPErrorMessage = 'Could not connect to server. Please refresh this page.';
            
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Connection Error',
                    text: 'Could not connect to server. Please refresh this page.',
                    type: 'error'
                });
            }
        });
    };

    $scope.importBannedIPs = function () {
        // Create file input element
        var input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.style.display = 'none';
        
        input.onchange = function(event) {
            var file = event.target.files[0];
            if (file) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    try {
                        var importData = JSON.parse(e.target.result);
                        
                        // Validate file format
                        if (!importData.banned_ips || !Array.isArray(importData.banned_ips)) {
                            $scope.$apply(function() {
                                $scope.bannedIPActionFailed = false;
                                $scope.bannedIPActionSuccess = true;
                                $scope.bannedIPErrorMessage = "Invalid import file format. Please select a valid banned IPs export file.";
                            });
                            
                            if (typeof PNotify !== 'undefined') {
                                new PNotify({
                                    title: 'Invalid File',
                                    text: 'Invalid import file format. Please select a valid banned IPs export file.',
                                    type: 'error'
                                });
                            }
                            return;
                        }
                        
                        // Upload file to server
                        uploadBannedIPsImportFile(file);
                    } catch (error) {
                        $scope.$apply(function() {
                            $scope.bannedIPActionFailed = false;
                            $scope.bannedIPActionSuccess = true;
                            $scope.bannedIPErrorMessage = "Invalid JSON file. Please select a valid banned IPs export file.";
                        });
                        
                        if (typeof PNotify !== 'undefined') {
                            new PNotify({
                                title: 'Invalid File',
                                text: 'Invalid JSON file. Please select a valid banned IPs export file.',
                                type: 'error'
                            });
                        }
                    }
                };
                reader.readAsText(file);
            }
        };
        
        document.body.appendChild(input);
        input.click();
        document.body.removeChild(input);
    };

    function uploadBannedIPsImportFile(file) {
        $scope.bannedIPsLoading = false;
        $scope.bannedIPActionFailed = true;
        $scope.bannedIPActionSuccess = true;
        $scope.bannedIPCouldNotConnect = true;

        var formData = new FormData();
        formData.append('import_file', file);

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': undefined
            },
            transformRequest: angular.identity
        };

        $http.post("/firewall/importBannedIPs", formData, config).then(function(response) {
            $scope.bannedIPsLoading = true;
            
            if (response.data.importStatus === 1) {
                $scope.bannedIPActionSuccess = false;
                populateBannedIPs(); // Refresh the list
                
                var message = `Import completed: ${response.data.imported_count} imported, ${response.data.skipped_count} skipped`;
                if (response.data.error_count > 0) {
                    message += `, ${response.data.error_count} errors`;
                    if (response.data.errors && response.data.errors.length > 0) {
                        message += '\nErrors: ' + response.data.errors.slice(0, 5).join('; ');
                        if (response.data.errors.length > 5) {
                            message += ` ... and ${response.data.errors.length - 5} more`;
                        }
                    }
                }
                
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Import Completed!',
                        text: message,
                        type: response.data.error_count > 0 ? 'notice' : 'success'
                    });
                } else {
                    alert(message);
                }
            } else {
                $scope.bannedIPActionFailed = false;
                $scope.bannedIPErrorMessage = response.data.error_message || 'Failed to import banned IPs';
                
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Import Failed',
                        text: response.data.error_message || 'Failed to import banned IPs',
                        type: 'error'
                    });
                }
            }
        }, function(error) {
            $scope.bannedIPsLoading = true;
            $scope.bannedIPCouldNotConnect = false;
            
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Connection Error',
                    text: 'Could not connect to server. Please refresh this page.',
                    type: 'error'
                });
            }
        });
    }

    // Export/Import Firewall Rules Functions
    $scope.exportRules = function () {
        $scope.rulesLoading = false;
        $scope.actionFailed = true;
        $scope.actionSuccess = true;

        var url = "/firewall/exportFirewallRules";
        var data = {};

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            responseType: 'blob'
        };

        $http.post(url, data, config).then(function(response) {
            $scope.rulesLoading = true;
            
            // Check if response is JSON (error) or file download
            if (response.data instanceof Blob) {
                // Check if it's actually a JSON error by reading the blob
                var reader = new FileReader();
                reader.onload = function() {
                    try {
                        var text = reader.result;
                        // Check if it's JSON error
                        if (text.trim().startsWith('{')) {
                            var errorData = JSON.parse(text);
                            if (errorData.exportStatus === 0) {
                                $scope.$apply(function() {
                                    $scope.actionFailed = false;
                                    $scope.actionSuccess = true;
                                    $scope.errorMessage = errorData.error_message;
                                });
                                
                                if (typeof PNotify !== 'undefined') {
                                    new PNotify({
                                        title: 'Export Failed',
                                        text: errorData.error_message,
                                        type: 'error'
                                    });
                                }
                                return;
                            }
                        }
                    } catch (e) {
                        // Not JSON, proceed with download
                    }
                    
                    // It's a valid file, trigger download
                    var blob = new Blob([response.data], { type: 'application/json' });
                    var url = window.URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = 'firewall_rules_export_' + Math.floor(Date.now() / 1000) + '.json';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                    
                    $scope.$apply(function() {
                        $scope.actionFailed = true;
                        $scope.actionSuccess = false;
                    });
                    
                    if (typeof PNotify !== 'undefined') {
                        new PNotify({
                            title: 'Success!',
                            text: 'Firewall rules exported successfully',
                            type: 'success'
                        });
                    }
                };
                reader.readAsText(response.data);
            } else {
                // Handle as text response (shouldn't happen with blob)
                $scope.actionFailed = true;
                $scope.actionSuccess = false;
            }
        }, function(error) {
            $scope.rulesLoading = true;
            $scope.actionFailed = false;
            $scope.actionSuccess = true;
            $scope.errorMessage = "Could not connect to server. Please refresh this page.";
            
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Connection Error',
                    text: 'Could not connect to server. Please refresh this page.',
                    type: 'error'
                });
            }
        });
    };

    $scope.importRules = function () {
        // Create file input element
        var input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.style.display = 'none';
        
        input.onchange = function(event) {
            var file = event.target.files[0];
            if (file) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    try {
                        var importData = JSON.parse(e.target.result);
                        
                        // Validate file format
                        if (!importData.rules || !Array.isArray(importData.rules)) {
                            $scope.$apply(function() {
                                $scope.actionFailed = false;
                                $scope.actionSuccess = true;
                                $scope.errorMessage = "Invalid import file format. Please select a valid firewall rules export file.";
                            });
                            return;
                        }
                        
                        // Upload file to server
                        uploadImportFile(file);
                    } catch (error) {
                        $scope.$apply(function() {
                            $scope.actionFailed = false;
                            $scope.actionSuccess = true;
                            $scope.errorMessage = "Invalid JSON file. Please select a valid firewall rules export file.";
                        });
                    }
                };
                reader.readAsText(file);
            }
        };
        
        document.body.appendChild(input);
        input.click();
        document.body.removeChild(input);
    };

    function uploadImportFile(file) {
        $scope.rulesLoading = false;
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
            $scope.rulesLoading = true;
            
            if (response.data && response.data.importStatus === 1) {
                $scope.actionFailed = true;
                $scope.actionSuccess = false;
                
                // Refresh rules list
                populateCurrentRecords();
                
                // Show import summary
                var message = `Import completed: ${response.data.imported_count} imported, ${response.data.skipped_count} skipped`;
                if (response.data.error_count > 0) {
                    message += `, ${response.data.error_count} errors`;
                    if (response.data.errors && response.data.errors.length > 0) {
                        message += '\nErrors: ' + response.data.errors.slice(0, 5).join('; ');
                        if (response.data.errors.length > 5) {
                            message += ` ... and ${response.data.errors.length - 5} more`;
                        }
                    }
                }
                
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Import Completed!',
                        text: message,
                        type: response.data.error_count > 0 ? 'notice' : 'success'
                    });
                } else {
                    alert(message);
                }
            } else {
                $scope.actionFailed = false;
                $scope.actionSuccess = true;
                $scope.errorMessage = (response.data && response.data.error_message) || 'Failed to import firewall rules';
                
                if (typeof PNotify !== 'undefined') {
                    new PNotify({
                        title: 'Import Failed',
                        text: (response.data && response.data.error_message) || 'Failed to import firewall rules',
                        type: 'error'
                    });
                }
            }
        }

        function importError(response) {
            $scope.rulesLoading = true;
            $scope.actionFailed = false;
            $scope.actionSuccess = true;
            $scope.errorMessage = "Could not connect to server. Please refresh this page.";
            
            if (typeof PNotify !== 'undefined') {
                new PNotify({
                    title: 'Connection Error',
                    text: 'Could not connect to server. Please refresh this page.',
                    type: 'error'
                });
            }
        }
    }

});