// Modern File Manager Enhancement
// This file extends the original fileManager.js with modern UI features

// Wait for the DOM to be ready
$(document).ready(function() {
    // Check if we're on the modern file manager page
    if (!$('.fm-container').length) return;
    
    // Get the Angular scope of the file manager
    var getScope = function() {
        var elem = angular.element($('[ng-controller="fileManagerCtrl"]'));
        return elem.scope();
    };
    
    // Wait a bit for Angular to initialize
    setTimeout(function() {
        var $scope = getScope();
        if (!$scope) {
            console.error('Could not get file manager scope');
            return;
        }
        
        // Add modern UI properties
        $scope.viewMode = localStorage.getItem('fileManagerViewMode') || 'grid';
        $scope.searchFilter = '';
        $scope.sortBy = 'name';
        $scope.sortReverse = false;
        $scope.selectedFiles = [];
        $scope.copiedFiles = [];
        $scope.cutFiles = [];
        $scope.isCtrlPressed = false;
        $scope.pathSegments = [];
        $scope.isLoading = false;
        $scope.uploadProgress = 0;
        
        // View mode toggle
        $scope.setViewMode = function(mode) {
            $scope.viewMode = mode;
            localStorage.setItem('fileManagerViewMode', mode);
            $scope.$apply();
        };
        
        // Sort functionality
        $scope.sortFiles = function(sortBy) {
            if ($scope.sortBy === sortBy) {
                $scope.sortReverse = !$scope.sortReverse;
            } else {
                $scope.sortBy = sortBy;
                $scope.sortReverse = false;
            }
            $scope.$apply();
        };
        
        // Enhanced file selection
        $scope.toggleFileSelection = function(file, event) {
            if (event) {
                event.stopPropagation();
            }
            
            var fileName = file.fileName;
            var index = allFilesAndFolders.indexOf(fileName);
            
            if (index === -1) {
                if (!$scope.isCtrlPressed && !event.shiftKey) {
                    allFilesAndFolders = [];
                    $scope.selectedFiles = [];
                }
                allFilesAndFolders.push(fileName);
                $scope.selectedFiles.push(file);
            } else {
                if ($scope.isCtrlPressed || event.ctrlKey || event.metaKey) {
                    allFilesAndFolders.splice(index, 1);
                    var selectedIndex = $scope.selectedFiles.indexOf(file);
                    if (selectedIndex > -1) {
                        $scope.selectedFiles.splice(selectedIndex, 1);
                    }
                } else {
                    allFilesAndFolders = [fileName];
                    $scope.selectedFiles = [file];
                }
            }
            
            $scope.buttonActivator();
            $scope.$apply();
        };
        
        $scope.isFileSelected = function(file) {
            return allFilesAndFolders.indexOf(file.fileName) !== -1;
        };
        
        // Open file/folder on double click
        $scope.openFile = function(file) {
            if (file.dirCheck) {
                var node = { textContent: file.fileName };
                $scope.fetchForTableSecondary(node, "doubleClick");
            } else {
                // Check if it's editable
                var ext = findFileExtension(file.fileName);
                if (ext) {
                    var editableExts = ['txt', 'html', 'htm', 'css', 'js', 'php', 'py', 'rb', 'java', 'c', 'cpp', 'h', 'sh', 'conf', 'json', 'xml', 'yml', 'yaml', 'ini', 'log', 'md'];
                    if (editableExts.indexOf(ext[0].toLowerCase()) !== -1) {
                        allFilesAndFolders = [file.fileName];
                        $scope.showHTMLEditorModal();
                    }
                }
            }
        };
        
        // Get file icon based on extension
        $scope.getFileIcon = function(file) {
            if (file.dirCheck) {
                return 'fa-folder';
            }
            
            var ext = findFileExtension(file.fileName);
            if (!ext) return 'fa-file';
            
            ext = ext[0].toLowerCase();
            
            var iconMap = {
                // Images
                'jpg': 'fa-file-image', 'jpeg': 'fa-file-image', 'png': 'fa-file-image',
                'gif': 'fa-file-image', 'bmp': 'fa-file-image', 'svg': 'fa-file-image',
                // Documents
                'pdf': 'fa-file-pdf', 'doc': 'fa-file-word', 'docx': 'fa-file-word',
                'xls': 'fa-file-excel', 'xlsx': 'fa-file-excel', 'ppt': 'fa-file-powerpoint',
                'pptx': 'fa-file-powerpoint', 'txt': 'fa-file-alt',
                // Code
                'html': 'fa-file-code', 'css': 'fa-file-code', 'js': 'fa-file-code',
                'php': 'fa-file-code', 'py': 'fa-file-code', 'java': 'fa-file-code',
                'cpp': 'fa-file-code', 'c': 'fa-file-code', 'h': 'fa-file-code',
                'json': 'fa-file-code', 'xml': 'fa-file-code', 'sql': 'fa-file-code',
                // Archives
                'zip': 'fa-file-archive', 'rar': 'fa-file-archive', 'tar': 'fa-file-archive',
                'gz': 'fa-file-archive', '7z': 'fa-file-archive', 'bz2': 'fa-file-archive',
                // Media
                'mp3': 'fa-file-audio', 'wav': 'fa-file-audio', 'ogg': 'fa-file-audio',
                'mp4': 'fa-file-video', 'avi': 'fa-file-video', 'mkv': 'fa-file-video',
                'mov': 'fa-file-video', 'wmv': 'fa-file-video'
            };
            
            return iconMap[ext] || 'fa-file';
        };
        
        // Update path segments for breadcrumb navigation
        $scope.updatePathSegments = function() {
            var path = $scope.currentPath || $scope.completeStartingPath;
            var segments = path.split('/').filter(function(s) { return s; });
            
            $scope.pathSegments = [];
            var currentPath = '';
            
            segments.forEach(function(segment, index) {
                currentPath += '/' + segment;
                $scope.pathSegments.push({
                    name: segment,
                    path: currentPath,
                    isLast: index === segments.length - 1
                });
            });
        };
        
        $scope.navigateToPath = function(path) {
            $scope.currentPath = path;
            $scope.completeStartingPath = path;
            $scope.fetchForTableSecondary(null, "pathNavigation");
        };
        
        // Enhanced copy/cut/paste
        $scope.copySelectedFiles = function() {
            $scope.copiedFiles = $scope.selectedFiles.slice();
            $scope.cutFiles = [];
            new PNotify({
                title: 'Success!',
                text: $scope.copiedFiles.length + ' file(s) copied to clipboard',
                type: 'success'
            });
        };
        
        $scope.cutSelectedFiles = function() {
            $scope.cutFiles = $scope.selectedFiles.slice();
            $scope.copiedFiles = [];
            new PNotify({
                title: 'Success!',
                text: $scope.cutFiles.length + ' file(s) cut to clipboard',
                type: 'success'
            });
        };
        
        $scope.pasteFiles = function() {
            if ($scope.copiedFiles.length > 0) {
                $scope.newPath = $scope.completeStartingPath;
                allFilesAndFolders = $scope.copiedFiles.map(function(f) { return f.fileName; });
                $scope.startCopying();
                $scope.copiedFiles = [];
            } else if ($scope.cutFiles.length > 0) {
                $scope.newPath = $scope.completeStartingPath;
                allFilesAndFolders = $scope.cutFiles.map(function(f) { return f.fileName; });
                $scope.startMoving();
                $scope.cutFiles = [];
            }
        };
        
        // Keyboard shortcuts
        $scope.handleKeyDown = function(event) {
            if (event.ctrlKey || event.metaKey) {
                $scope.isCtrlPressed = true;
                
                switch(event.key.toLowerCase()) {
                    case 'a':
                        event.preventDefault();
                        $scope.selectAll();
                        $scope.$apply();
                        break;
                    case 'c':
                        event.preventDefault();
                        if (allFilesAndFolders.length > 0) {
                            $scope.copySelectedFiles();
                        }
                        break;
                    case 'x':
                        event.preventDefault();
                        if (allFilesAndFolders.length > 0) {
                            $scope.cutSelectedFiles();
                        }
                        break;
                    case 'v':
                        event.preventDefault();
                        $scope.pasteFiles();
                        break;
                }
            } else if (event.key === 'Delete') {
                event.preventDefault();
                if (allFilesAndFolders.length > 0) {
                    $scope.showDeleteModal();
                }
            } else if (event.key === 'F2') {
                event.preventDefault();
                if (allFilesAndFolders.length === 1) {
                    $scope.showRenameModal();
                }
            }
        };
        
        $scope.handleKeyUp = function(event) {
            if (!event.ctrlKey && !event.metaKey) {
                $scope.isCtrlPressed = false;
            }
        };
        
        // Bind keyboard events
        $(window).on('keydown', $scope.handleKeyDown);
        $(window).on('keyup', $scope.handleKeyUp);
        
        // Override the original fetchForTableSecondary to add loading state
        var originalFetch = $scope.fetchForTableSecondary;
        $scope.fetchForTableSecondary = function(node, functionName, completePath) {
            $scope.isLoading = true;
            $scope.selectedFiles = [];
            var result = originalFetch.call($scope, node, functionName, completePath);
            
            // The response will update isLoading when complete
            setTimeout(function() {
                $scope.isLoading = false;
                $scope.updatePathSegments();
                $scope.$apply();
            }, 500);
            
            return result;
        };
        
        // Enhance file uploader
        if ($scope.uploader) {
            $scope.uploader.onProgressItem = function(item, progress) {
                $scope.uploadProgress = progress;
                $scope.$apply();
            };
            
            $scope.uploader.onCompleteAll = function() {
                $scope.uploadProgress = 100;
                setTimeout(function() {
                    $scope.uploadProgress = 0;
                    $("#uploadModal").modal('hide');
                    $scope.$apply();
                }, 1000);
            };
        }
        
        // Initialize
        $scope.updatePathSegments();
        
        // Apply changes
        $scope.$apply();
        
        console.log('Modern file manager enhancements loaded');
        
    }, 500); // Wait for Angular to initialize
});