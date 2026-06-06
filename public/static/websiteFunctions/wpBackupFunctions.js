// WordPress Backup and Staging Functions Extension
// Simple fixes for backup and staging functionality

$(document).ready(function() {
    // Override getCreationStatus to show progress
    if (typeof window.getCreationStatus === 'undefined') {
        window.getCreationStatus = function() {
            var url = "/websites/installWordpressStatus";
            var data = {
                statusFile: window.statusFile
            };
            
            $.ajax({
                type: 'POST',
                url: url,
                data: JSON.stringify(data),
                contentType: 'application/json',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                success: function(response) {
                    if (response.abort === 1) {
                        // Operation complete
                        $('#wordpresshomeloading').hide();
                        $('#createBackupBtn').prop('disabled', false).html('<i class="fas fa-download"></i> Create Backup');
                        $('button[ng-click="CreateStagingNow()"]')
                            .prop('disabled', false).html('<i class="fas fa-clone"></i> Create Staging Site');
                        
                        // Hide progress bar, show success/error
                        if (response.installStatus === 1) {
                            if (window.statusFile && window.statusFile.includes('backup')) {
                                $('#backupStatus').html('<span style="color: #10b981;">✓ Backup created successfully!</span>');
                                // Show new progress section as success
                                $('#backupProgressSection').show();
                                $('#backupStatusMessage').show();
                                $('#backupCurrentStatus').text('Backup successfully created.');
                                $('#backupProgressBar').css('width', '100%').attr('aria-valuenow', 100);
                                $('#backupProgressPercent').text('100%');
                                $('#backupErrorBox').hide();
                                $('#backupSuccessBox').show();
                            } else {
                                $('#stagingStatus').html('<span style="color: #10b981;">✓ Staging site created successfully!</span>');
                                var scope = angular.element($('[ng-controller="WPsiteHome"]')).scope();
                                if (scope && scope.fetchstaging) {
                                    scope.$apply(function() {
                                        scope.fetchstaging();
                                    });
                                }
                            }
                        } else {
                            var errorMsg = response.error_message || 'Operation failed';
                            if (window.statusFile && window.statusFile.includes('backup')) {
                                $('#backupStatus').html('<span style="color: #ef4444;">✗ ' + errorMsg + '</span>');
                                // Show error in new progress section
                                $('#backupProgressSection').show();
                                $('#backupStatusMessage').hide();
                                $('#backupProgressBar').css('width', '0%').attr('aria-valuenow', 0);
                                $('#backupProgressPercent').text('0%');
                                $('#backupErrorBox').show();
                                $('#backupErrorMessage').text(errorMsg);
                                $('#backupSuccessBox').hide();
                            } else {
                                $('#stagingStatus').html('<span style="color: #ef4444;">✗ ' + errorMsg + '</span>');
                            }
                        }
                    } else {
                        // Still in progress
                        var status = response.currentStatus || 'Processing...';
                        var progress = response.installationProgress || 0;
                        var statusHtml = '<i class="fas fa-spinner fa-pulse"></i> ' + status + ' (' + progress + '%)';
                        if (window.statusFile && window.statusFile.includes('backup')) {
                            $('#backupStatus').html(statusHtml);
                            // Show and update progress bar
                            $('#backupProgressSection').show();
                            $('#backupStatusMessage').show();
                            $('#backupCurrentStatus').text(status);
                            $('#backupProgressBar').css('width', progress + '%').attr('aria-valuenow', progress);
                            $('#backupProgressPercent').text(progress + '%');
                            $('#backupErrorBox').hide();
                            $('#backupSuccessBox').hide();
                        } else {
                            $('#stagingStatus').html(statusHtml);
                        }
                        setTimeout(window.getCreationStatus, 1000);
                    }
                },
                error: function() {
                    $('#wordpresshomeloading').hide();
                    $('#createBackupBtn').prop('disabled', false).html('<i class="fas fa-download"></i> Create Backup');
                    $('button[ng-click="CreateStagingNow()"]')
                        .prop('disabled', false).html('<i class="fas fa-clone"></i> Create Staging Site');
                    // Show error in progress section if backup
                    if (window.statusFile && window.statusFile.includes('backup')) {
                        $('#backupProgressSection').show();
                        $('#backupStatusMessage').hide();
                        $('#backupProgressBar').css('width', '0%').attr('aria-valuenow', 0);
                        $('#backupProgressPercent').text('0%');
                        $('#backupErrorBox').show();
                        $('#backupErrorMessage').text('Error loading backup status.');
                        $('#backupSuccessBox').hide();
                    }
                }
            });
        };
    }

});