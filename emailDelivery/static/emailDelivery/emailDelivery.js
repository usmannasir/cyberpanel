app.controller('emailDeliveryCtrl', ['$scope', '$http', '$timeout', function($scope, $http, $timeout) {

    function apiCall(url, data, callback, errback) {
        var config = {headers: {'X-CSRFToken': getCookie('csrftoken')}};
        $http.post(url, data || {}, config).then(function(resp) {
            if (callback) callback(resp.data);
        }, function(err) {
            console.error('API error:', url, err);
            if (errback) errback(err);
        });
    }

    function notify(msg, type) {
        new PNotify({title: type === 'error' ? 'Error' : 'Email Delivery', text: msg, type: type || 'success'});
    }

    $scope.loading = true;
    $scope.activeTab = 'domains';

    // Account data
    $scope.account = {};
    $scope.stats = {};
    $scope.domains = [];
    $scope.smtpCredentials = [];
    $scope.logs = [];
    $scope.detailedStats = {};
    $scope.domainStats = [];

    // Form data
    $scope.connectEmail = '';
    $scope.connectPassword = '';
    $scope.connectLoading = false;
    $scope.newDomainName = '';
    $scope.addDomainLoading = false;
    $scope.newSmtpDescription = '';
    $scope.createSmtpLoading = false;
    $scope.oneTimePassword = null;

    // Relay
    $scope.relayLoading = false;

    // Logs
    $scope.logFilters = {status: '', from_domain: '', days: 7};
    $scope.logsPage = 1;
    $scope.logsTotalPages = 1;
    $scope.logsLoading = false;

    // Domain stats
    $scope.domainStatsLoading = false;

    // Disconnect
    $scope.disconnectLoading = false;

    $scope.init = function(isConnected, adminEmail) {
        $scope.isConnected = isConnected;
        $scope.connectEmail = adminEmail || '';
        if (isConnected) {
            $scope.refreshDashboard();
        } else {
            $scope.loading = false;
        }
    };

    $scope.refreshDashboard = function() {
        $scope.loading = true;
        apiCall('/emailDelivery/status/', {}, function(data) {
            if (data.success) {
                $scope.account = data.account;
                $scope.stats = data.stats || {};
                $scope.domains = data.domains || [];
            }
            $scope.loading = false;
        }, function() {
            $scope.loading = false;
            notify('Failed to load dashboard data', 'error');
        });
    };

    $scope.getUsagePercent = function() {
        if (!$scope.account.emails_per_month) return 0;
        return Math.min(100, Math.round(($scope.stats.emails_sent || 0) / $scope.account.emails_per_month * 100));
    };

    // ============ Connect ============
    $scope.connectAccount = function() {
        if (!$scope.connectEmail || !$scope.connectPassword) {
            notify('Please fill in all fields.', 'error');
            return;
        }
        $scope.connectLoading = true;
        apiCall('/emailDelivery/connect/', {
            email: $scope.connectEmail,
            password: $scope.connectPassword
        }, function(data) {
            $scope.connectLoading = false;
            if (data.success) {
                $('#connectModal').modal('hide');
                notify('Connected to CyberMail successfully!');
                $timeout(function() { window.location.reload(); }, 1000);
            } else {
                notify(data.error || 'Connection failed.', 'error');
            }
        }, function() {
            $scope.connectLoading = false;
            notify('Connection failed. Please try again.', 'error');
        });
    };

    // ============ Domains ============
    $scope.addDomain = function() {
        if (!$scope.newDomainName) {
            notify('Please enter a domain name.', 'error');
            return;
        }
        $scope.addDomainLoading = true;
        apiCall('/emailDelivery/domains/add/', {
            domain: $scope.newDomainName
        }, function(data) {
            $scope.addDomainLoading = false;
            if (data.success) {
                $('#addDomainModal').modal('hide');
                $scope.newDomainName = '';
                $scope.refreshDashboard();
                var msg = 'Domain added successfully.';
                if (data.dns_configured) msg += ' ' + data.dns_message;
                notify(msg);
            } else {
                notify(data.error || 'Failed to add domain.', 'error');
            }
        }, function() {
            $scope.addDomainLoading = false;
            notify('Failed to add domain.', 'error');
        });
    };

    $scope.verifyDomain = function(domain) {
        apiCall('/emailDelivery/domains/verify/', {domain: domain}, function(data) {
            if (data.success) {
                $scope.refreshDashboard();
                notify('Domain verification completed.');
            } else {
                notify(data.error || 'Verification failed.', 'error');
            }
        });
    };

    $scope.configureDns = function(domain) {
        apiCall('/emailDelivery/domains/auto-configure-dns/', {domain: domain}, function(data) {
            if (data.success) {
                $scope.refreshDashboard();
                notify(data.message || 'DNS configured.');
            } else {
                notify(data.message || data.error || 'DNS configuration failed.', 'error');
            }
        });
    };

    $scope.removeDomain = function(domain) {
        if (!confirm('Remove domain ' + domain + ' from CyberMail?')) return;
        apiCall('/emailDelivery/domains/remove/', {domain: domain}, function(data) {
            if (data.success) {
                $scope.refreshDashboard();
                notify('Domain removed.');
            } else {
                notify(data.error || 'Failed to remove domain.', 'error');
            }
        });
    };

    // ============ SMTP Credentials ============
    $scope.switchTab = function(tab) {
        $scope.activeTab = tab;
        if (tab === 'smtp') $scope.loadSmtpCredentials();
        if (tab === 'logs') $scope.loadLogs();
        if (tab === 'stats') $scope.loadStats();
    };

    $scope.loadSmtpCredentials = function() {
        apiCall('/emailDelivery/smtp/list/', {}, function(data) {
            if (data.success) {
                $scope.smtpCredentials = data.data ? data.data.credentials || [] : [];
            }
        });
    };

    $scope.createSmtpCredential = function() {
        $scope.createSmtpLoading = true;
        apiCall('/emailDelivery/smtp/create/', {
            description: $scope.newSmtpDescription
        }, function(data) {
            $scope.createSmtpLoading = false;
            if (data.success) {
                $('#createSmtpModal').modal('hide');
                $scope.newSmtpDescription = '';
                $scope.oneTimePassword = data.data ? data.data.password : null;
                $scope.loadSmtpCredentials();
                if ($scope.oneTimePassword) {
                    $timeout(function() { $('#passwordModal').modal('show'); }, 500);
                }
                notify('SMTP credential created.');
            } else {
                notify(data.error || 'Failed to create credential.', 'error');
            }
        }, function() {
            $scope.createSmtpLoading = false;
            notify('Failed to create credential.', 'error');
        });
    };

    $scope.rotatePassword = function(credId) {
        if (!confirm("Rotate this credential's password? The old password will stop working immediately.")) return;
        apiCall('/emailDelivery/smtp/rotate/', {credential_id: credId}, function(data) {
            if (data.success) {
                $scope.oneTimePassword = data.data ? data.data.password : null;
                if ($scope.oneTimePassword) {
                    $timeout(function() { $('#passwordModal').modal('show'); }, 300);
                }
                notify('Password rotated.');
            } else {
                notify(data.error || 'Failed to rotate password.', 'error');
            }
        });
    };

    $scope.deleteCredential = function(credId) {
        if (!confirm('Delete this SMTP credential? This cannot be undone.')) return;
        apiCall('/emailDelivery/smtp/delete/', {credential_id: credId}, function(data) {
            if (data.success) {
                $scope.loadSmtpCredentials();
                notify('Credential deleted.');
            } else {
                notify(data.error || 'Failed to delete credential.', 'error');
            }
        });
    };

    // ============ Relay ============
    $scope.enableRelay = function() {
        $scope.relayLoading = true;
        apiCall('/emailDelivery/relay/enable/', {}, function(data) {
            $scope.relayLoading = false;
            if (data.success) {
                $scope.account.relay_enabled = true;
                notify('SMTP relay enabled!');
            } else {
                notify(data.error || 'Failed to enable relay.', 'error');
            }
        }, function() {
            $scope.relayLoading = false;
            notify('Failed to enable relay.', 'error');
        });
    };

    $scope.disableRelay = function() {
        if (!confirm('Disable SMTP relay? Postfix will send directly again.')) return;
        $scope.relayLoading = true;
        apiCall('/emailDelivery/relay/disable/', {}, function(data) {
            $scope.relayLoading = false;
            if (data.success) {
                $scope.account.relay_enabled = false;
                notify('SMTP relay disabled.');
            } else {
                notify(data.error || 'Failed to disable relay.', 'error');
            }
        }, function() {
            $scope.relayLoading = false;
            notify('Failed to disable relay.', 'error');
        });
    };

    // ============ Logs ============
    $scope.loadLogs = function() {
        $scope.logsLoading = true;
        apiCall('/emailDelivery/logs/', {
            page: $scope.logsPage,
            status: $scope.logFilters.status,
            from_domain: $scope.logFilters.from_domain,
            days: $scope.logFilters.days || 7
        }, function(data) {
            $scope.logsLoading = false;
            if (data.success) {
                $scope.logs = data.data ? data.data.logs || [] : [];
                $scope.logsTotalPages = data.data ? data.data.total_pages || 1 : 1;
            }
        }, function() {
            $scope.logsLoading = false;
        });
    };

    // ============ Stats ============
    $scope.loadStats = function() {
        apiCall('/emailDelivery/stats/', {}, function(data) {
            if (data.success) {
                $scope.detailedStats = data.data || {};
            }
        });
        $scope.domainStatsLoading = true;
        apiCall('/emailDelivery/stats/domains/', {}, function(data) {
            $scope.domainStatsLoading = false;
            if (data.success) {
                $scope.domainStats = data.data ? data.data.domains || [] : [];
            }
        }, function() {
            $scope.domainStatsLoading = false;
        });
    };

    // ============ Disconnect ============
    $scope.disconnectAccount = function() {
        $scope.disconnectLoading = true;
        apiCall('/emailDelivery/disconnect/', {}, function(data) {
            $scope.disconnectLoading = false;
            if (data.success) {
                $('#disconnectModal').modal('hide');
                notify('Disconnected from CyberMail.');
                $timeout(function() { window.location.reload(); }, 1000);
            } else {
                notify(data.error || 'Failed to disconnect.', 'error');
            }
        }, function() {
            $scope.disconnectLoading = false;
            notify('Failed to disconnect.', 'error');
        });
    };

}]);
