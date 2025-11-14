/**
 * Enhanced Remote Transfer JavaScript
 * Provides intelligent transfer mode selection and disk space analysis
 */

app.controller('enhancedRemoteTransfer', function($scope, $http) {

    $scope.transferModes = {
        'sequential': {
            name: 'Sequential Transfer (Recommended for Low Space)',
            description: 'Processes websites one by one, cleaning up after each transfer. Requires minimal disk space.',
            icon: 'fa-arrow-right'
        },
        'rsync': {
            name: 'Rsync Transfer (Most Efficient)',
            description: 'Direct file synchronization without compression. Almost no additional disk space needed.',
            icon: 'fa-sync'
        },
        'parallel': {
            name: 'Parallel Transfer (Current Method)',
            description: 'Transfers all websites simultaneously. Fastest but requires 50%+ free disk space.',
            icon: 'fa-layer-group'
        }
    };

    $scope.selectedWebsites = [];
    $scope.diskAnalysis = null;
    $scope.recommendedMode = null;
    $scope.selectedMode = null;
    $scope.transferring = false;
    $scope.transferProgress = 0;
    $scope.currentWebsite = '';

    // Initialize controller
    $scope.init = function() {
        $scope.analyzeDiskSpace();
        $scope.fetchRemoteAccounts();
    };

    // Analyze disk space and get recommendations
    $scope.analyzeDiskSpace = function() {
        $scope.cyberpanelLoading = false;

        $http.get('/backup/diskAnalysis').then(function(response) {
            $scope.diskAnalysis = response.data;
            $scope.cyberpanelLoading = true;

            if (response.data.recommended_mode) {
                $scope.recommendedMode = response.data.recommended_mode;
                $scope.selectedMode = response.data.recommended_mode;
            }

            new PNotify({
                title: 'Disk Analysis Complete',
                text: `Disk Usage: ${response.data.disk_usage_percent.toFixed(1)}% (${response.data.free_space_gb.toFixed(1)}GB free)`,
                type: 'info'
            });

        }, function(error) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Error',
                text: 'Could not analyze disk space',
                type: 'error'
            });
        });
    };

    // Fetch accounts from remote server
    $scope.fetchRemoteAccounts = function() {
        $scope.cyberpanelLoading = false;

        var formData = {
            ipAddress: $scope.ipAddress,
            rootPassword: $scope.rootPassword,
            rootSSHKey: $scope.rootSSHKey
        };

        $http.post('/backup/fetchRemoteAccounts', formData).then(function(response) {
            $scope.remoteAccounts = response.data.accounts;
            $scope.cyberpanelLoading = true;
            $scope.accountsFetched = true;

        }, function(error) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Connection Failed',
                text: 'Could not connect to remote server',
                type: 'error'
            });
        });
    };

    // Toggle website selection
    $scope.toggleWebsiteSelection = function(website) {
        var index = $scope.selectedWebsites.indexOf(website);
        if (index > -1) {
            $scope.selectedWebsites.splice(index, 1);
        } else {
            $scope.selectedWebsites.push(website);
        }
        $scope.updateRecommendations();
    };

    // Select all websites
    $scope.selectAllWebsites = function() {
        $scope.selectedWebsites = angular.copy($scope.remoteAccounts);
        $scope.updateRecommendations();
    };

    // Clear selection
    $scope.clearSelection = function() {
        $scope.selectedWebsites = [];
        $scope.updateRecommendations();
    };

    // Update recommendations based on selection
    $scope.updateRecommendations = function() {
        if ($scope.selectedWebsites.length === 0) {
            return;
        }

        $scope.cyberpanelLoading = false;

        $http.post('/backup/updateRecommendations', {
            websites: $scope.selectedWebsites
        }).then(function(response) {
            $scope.recommendedMode = response.data.recommended_mode;
            if (!$scope.selectedMode) {
                $scope.selectedMode = response.data.recommended_mode;
            }

            // Update estimated requirements
            $scope.estimatedSize = response.data.estimated_size_gb;
            $scope.spaceRequirement = response.data.space_requirement_text;

            $scope.cyberpanelLoading = true;

        }, function(error) {
            $scope.cyberpanelLoading = true;
        });
    };

    // Get disk space indicator class
    $scope.getDiskSpaceClass = function() {
        if (!$scope.diskAnalysis) return '';

        var percent = $scope.diskAnalysis.disk_usage_percent;
        if (percent < 50) return 'success';
        if (percent < 80) return 'warning';
        return 'danger';
    };

    // Get transfer mode recommendation badge
    $scope.getModeRecommendationBadge = function(mode) {
        if ($scope.recommendedMode === mode) {
            return '<span class="badge badge-primary">Recommended</span>';
        }
        return '';
    };

    // Get mode compatibility indicator
    $scope.getModeCompatibility = function(mode) {
        if (!$scope.diskAnalysis) return 'Unknown';

        var freePercent = 100 - $scope.diskAnalysis.disk_usage_percent;
        var freeSpaceGb = $scope.diskAnalysis.free_space_gb;

        switch(mode) {
            case 'parallel':
                if (freePercent > 50) return 'Excellent';
                if (freePercent > 30) return 'Good';
                return 'Poor';
            case 'sequential':
                if (freePercent > 20) return 'Good';
                if (freePercent > 10) return 'Fair';
                return 'Poor';
            case 'rsync':
                if (freeSpaceGb > 1) return 'Excellent';
                if (freeSpaceGb > 0.5) return 'Good';
                return 'Fair';
            default:
                return 'Unknown';
        }
    };

    // Start enhanced transfer
    $scope.startEnhancedTransfer = function() {
        if ($scope.selectedWebsites.length === 0) {
            new PNotify({
                title: 'No Websites Selected',
                text: 'Please select at least one website to transfer',
                type: 'warning'
            });
            return;
        }

        if (!$scope.selectedMode) {
            new PNotify({
                title: 'No Transfer Mode Selected',
                text: 'Please select a transfer mode',
                type: 'warning'
            });
            return;
        }

        // Show confirmation dialog
        var confirmMessage = `Start transfer with ${$scope.transferModes[$scope.selectedMode].name}?\\n\\n` +
                           `Websites: ${$scope.selectedWebsites.length}\\n` +
                           `Mode: ${$scope.transferModes[$scope.selectedMode].description}\\n\\n` +
                           `This will begin the transfer process immediately.`;

        if (!confirm(confirmMessage)) {
            return;
        }

        $scope.transferring = true;
        $scope.transferProgress = 0;
        $scope.cyberpanelLoading = false;

        var formData = {
            ipAddress: $scope.ipAddress,
            websites: $scope.selectedWebsites,
            transferMode: $scope.selectedMode
        };

        $http.post('/backup/startEnhancedTransfer', formData).then(function(response) {
            $scope.cyberpanelLoading = true;

            if (response.data.status === 1) {
                new PNotify({
                    title: 'Transfer Started',
                    text: 'Enhanced remote transfer has been initiated',
                    type: 'success'
                });

                $scope.transferBoxBtn = true;
                $scope.stopTransferbtn = false;
                $scope.startTransferbtn = true;

                // Start monitoring progress
                $scope.monitorTransferProgress();

            } else {
                new PNotify({
                    title: 'Transfer Failed',
                    text: response.data.error,
                    type: 'error'
                });
                $scope.transferring = false;
            }

        }, function(error) {
            $scope.cyberpanelLoading = true;
            $scope.transferring = false;
            new PNotify({
                title: 'Transfer Failed',
                text: 'Could not start transfer process',
                type: 'error'
            });
        });
    };

    // Monitor transfer progress
    $scope.monitorTransferProgress = function() {
        if (!$scope.transferring) return;

        $http.get('/backup/transferProgress').then(function(response) {
            var data = response.data;

            $scope.transferProgress = data.progress_percentage || 0;
            $scope.currentWebsite = data.current_website || '';
            $scope.transferredCount = data.transferred_count || 0;
            $scope.totalCount = data.total_count || 0;

            if (data.completed) {
                $scope.transferring = false;
                $scope.transferProgress = 100;
                new PNotify({
                    title: 'Transfer Complete',
                    text: `Successfully transferred ${data.transferred_count} websites`,
                    type: 'success'
                });

                // Reset UI
                $scope.transferBoxBtn = false;
                $scope.stopTransferbtn = true;
                $scope.startTransferbtn = false;

            } else if (data.failed) {
                $scope.transferring = false;
                new PNotify({
                    title: 'Transfer Failed',
                    text: data.error || 'Transfer process failed',
                    type: 'error'
                });

            } else {
                // Continue monitoring
                setTimeout(function() {
                    $scope.monitorTransferProgress();
                }, 2000);
            }

        }, function(error) {
            // Continue monitoring even if request fails
            setTimeout(function() {
                $scope.monitorTransferProgress();
            }, 5000);
        });
    };

    // Cancel transfer
    $scope.cancelTransfer = function() {
        if (!confirm('Are you sure you want to cancel the transfer?')) {
            return;
        }

        $scope.transferring = false;
        $scope.cyberpanelLoading = false;

        $http.post('/backup/cancelTransfer').then(function(response) {
            $scope.cyberpanelLoading = true;
            new PNotify({
                title: 'Transfer Cancelled',
                text: 'Transfer process has been cancelled',
                type: 'info'
            });

        }, function(error) {
            $scope.cyberpanelLoading = true;
        });
    };

    // Format file size
    $scope.formatFileSize = function(bytes) {
        if (bytes === 0) return '0 B';

        var k = 1024;
        var sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        var i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    // Get progress bar class based on mode
    $scope.getProgressBarClass = function() {
        switch($scope.selectedMode) {
            case 'sequential': return 'progress-bar-striped progress-bar-animated bg-info';
            case 'rsync': return 'progress-bar-striped progress-bar-animated bg-success';
            case 'parallel': return 'progress-bar-striped progress-bar-animated bg-primary';
            default: return 'progress-bar-striped progress-bar-animated';
        }
    };

    // Initialize on load
    $scope.init();
});