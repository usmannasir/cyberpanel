// Modern File Manager JavaScript
angular.module('fileManagerApp', ['angularFileUpload'])
    .config(['$interpolateProvider', function($interpolateProvider) {
        // Change Angular delimiters to avoid conflict with Django
        $interpolateProvider.startSymbol('[[');
        $interpolateProvider.endSymbol(']]');
    }])
    .filter('fileTypeFilter', function() {
        return function(files, type) {
            if (!type || type === 'all') return files;
            
            const typeMap = {
                'images': ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp', 'ico'],
                'documents': ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf', 'odt'],
                'code': ['js', 'ts', 'py', 'php', 'html', 'css', 'json', 'xml', 'yml', 'yaml', 'md', 'sql', 'sh'],
                'archives': ['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz']
            };
            
            return files.filter(file => {
                if (file.type === 'folder') return true;
                const ext = file.name.toLowerCase().split('.').pop();
                return typeMap[type] && typeMap[type].includes(ext);
            });
        };
    })
    .controller('fileManagerCtrl', ['$scope', '$http', '$timeout', 'FileUploader', function($scope, $http, $timeout, FileUploader) {
        
        // Initialize scope variables
        $scope.viewMode = 'grid';
        $scope.files = [];
        $scope.filteredFiles = [];
        $scope.selectedFiles = [];
        $scope.breadcrumbs = [];
        $scope.currentPath = '/home';
        $scope.loading = false;
        $scope.searchQuery = '';
        $scope.filter = { type: 'all' };
        $scope.sortField = 'name';
        $scope.sortReverse = false;
        $scope.sidebarCollapsed = false;
        $scope.showPreview = false;
        $scope.previewFile = null;
        $scope.showContextMenu = false;
        $scope.contextFile = null;
        $scope.contextMenuX = 0;
        $scope.contextMenuY = 0;
        $scope.isDragging = false;
        $scope.clipboard = null;
        $scope.showUpload = false;  // Make sure this is false
        $scope.uploadQueue = [];
        $scope.uploadDragging = false;
        
        // Storage info (mock data - replace with real API)
        $scope.storageUsed = 45.2;
        $scope.storageTotal = 100;
        $scope.storagePercent = Math.round(($scope.storageUsed / $scope.storageTotal) * 100);
        
        // Get domain name
        $scope.domainName = document.getElementById('domainNameInitial')?.textContent || 'example.com';
        
        // Initialize file uploader
        const uploader = $scope.uploader = new FileUploader({
            url: '/filemanager/upload',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        // File uploader filters
        uploader.filters.push({
            name: 'customFilter',
            fn: function(item) {
                return this.queue.length < 10;
            }
        });
        
        // File uploader callbacks
        uploader.onWhenAddingFileFailed = function(item, filter, options) {
            console.info('onWhenAddingFileFailed', item, filter, options);
        };
        
        uploader.onAfterAddingFile = function(fileItem) {
            console.info('onAfterAddingFile', fileItem);
            $scope.uploadQueue.push({
                name: fileItem.file.name,
                size: fileItem.file.size,
                progress: 0,
                status: 'pending'
            });
        };
        
        uploader.onAfterAddingAll = function(addedFileItems) {
            console.info('onAfterAddingAll', addedFileItems);
        };
        
        uploader.onBeforeUploadItem = function(item) {
            console.info('onBeforeUploadItem', item);
            item.formData.push({ path: $scope.currentPath });
        };
        
        uploader.onProgressItem = function(fileItem, progress) {
            console.info('onProgressItem', fileItem, progress);
            const queueItem = $scope.uploadQueue.find(f => f.name === fileItem.file.name);
            if (queueItem) {
                queueItem.progress = progress;
                queueItem.status = 'uploading';
            }
        };
        
        uploader.onProgressAll = function(progress) {
            console.info('onProgressAll', progress);
        };
        
        uploader.onSuccessItem = function(fileItem, response, status, headers) {
            console.info('onSuccessItem', fileItem, response, status, headers);
            const queueItem = $scope.uploadQueue.find(f => f.name === fileItem.file.name);
            if (queueItem) {
                queueItem.progress = 100;
                queueItem.status = 'success';
            }
            $scope.refreshFiles();
        };
        
        uploader.onErrorItem = function(fileItem, response, status, headers) {
            console.info('onErrorItem', fileItem, response, status, headers);
            const queueItem = $scope.uploadQueue.find(f => f.name === fileItem.file.name);
            if (queueItem) {
                queueItem.status = 'error';
            }
        };
        
        uploader.onCancelItem = function(fileItem, response, status, headers) {
            console.info('onCancelItem', fileItem, response, status, headers);
        };
        
        uploader.onCompleteItem = function(fileItem, response, status, headers) {
            console.info('onCompleteItem', fileItem, response, status, headers);
        };
        
        uploader.onCompleteAll = function() {
            console.info('onCompleteAll');
            $timeout(function() {
                $scope.uploadQueue = [];
                $scope.showUpload = false;
            }, 2000);
        };
        
        // Initialize
        $scope.init = function() {
            $scope.loadFiles();
            $scope.setupEventListeners();
            $scope.updateBreadcrumbs();
        };
        
        // Load files from server
        $scope.loadFiles = function() {
            $scope.loading = true;
            
            // Mock data - replace with real API call
            $timeout(function() {
                $scope.files = [
                    { name: 'Documents', type: 'folder', size: 0, modified: new Date(), permissions: 'drwxr-xr-x', itemCount: 24 },
                    { name: 'Images', type: 'folder', size: 0, modified: new Date(), permissions: 'drwxr-xr-x', itemCount: 156 },
                    { name: 'Videos', type: 'folder', size: 0, modified: new Date(), permissions: 'drwxr-xr-x', itemCount: 12 },
                    { name: 'index.html', type: 'file', size: 24567, modified: new Date(), permissions: '-rw-r--r--' },
                    { name: 'style.css', type: 'file', size: 12890, modified: new Date(), permissions: '-rw-r--r--' },
                    { name: 'script.js', type: 'file', size: 45678, modified: new Date(), permissions: '-rw-r--r--' },
                    { name: 'logo.png', type: 'file', size: 89012, modified: new Date(), permissions: '-rw-r--r--', thumbnail: '/static/images/not-available-preview.png' },
                    { name: 'data.json', type: 'file', size: 3456, modified: new Date(), permissions: '-rw-r--r--' },
                    { name: 'backup.zip', type: 'file', size: 567890, modified: new Date(), permissions: '-rw-r--r--' }
                ];
                
                $scope.files.forEach(file => {
                    file.selected = false;
                    file.starred = false;
                });
                
                $scope.loading = false;
            }, 800);
        };
        
        // Refresh files
        $scope.refreshFiles = function() {
            $scope.loadFiles();
        };
        
        // Update breadcrumbs
        $scope.updateBreadcrumbs = function() {
            const parts = $scope.currentPath.split('/').filter(p => p);
            $scope.breadcrumbs = [{ name: 'Home', path: '/home' }];
            
            let path = '';
            parts.forEach(part => {
                if (part !== 'home') {
                    path += '/' + part;
                    $scope.breadcrumbs.push({ name: part, path: '/home' + path });
                }
            });
        };
        
        // Set view mode
        $scope.setViewMode = function(mode) {
            $scope.viewMode = mode;
        };
        
        // Set filter
        $scope.setFilter = function(type) {
            $scope.filter.type = type;
        };
        
        // Toggle sidebar
        $scope.toggleSidebar = function() {
            $scope.sidebarCollapsed = !$scope.sidebarCollapsed;
        };
        
        // Navigate to path
        $scope.navigateTo = function(path) {
            $scope.currentPath = path;
            $scope.updateBreadcrumbs();
            $scope.loadFiles();
        };
        
        // Select file
        $scope.selectFile = function(file, event) {
            if (event.ctrlKey || event.metaKey) {
                // Multi-select with Ctrl/Cmd
                file.selected = !file.selected;
            } else if (event.shiftKey && $scope.selectedFiles.length > 0) {
                // Range select with Shift
                const lastSelected = $scope.selectedFiles[$scope.selectedFiles.length - 1];
                const startIndex = $scope.files.indexOf(lastSelected);
                const endIndex = $scope.files.indexOf(file);
                const start = Math.min(startIndex, endIndex);
                const end = Math.max(startIndex, endIndex);
                
                for (let i = start; i <= end; i++) {
                    $scope.files[i].selected = true;
                }
            } else {
                // Single select
                $scope.files.forEach(f => f.selected = false);
                file.selected = true;
            }
            
            $scope.updateSelectedFiles();
            
            // Show preview for single selection
            if ($scope.selectedFiles.length === 1) {
                $scope.showPreview = true;
                $scope.previewFile = file;
            } else {
                $scope.showPreview = false;
                $scope.previewFile = null;
            }
        };
        
        // Update selected files array
        $scope.updateSelectedFiles = function() {
            $scope.selectedFiles = $scope.files.filter(f => f.selected);
        };
        
        // Open file
        $scope.openFile = function(file) {
            if (file.type === 'folder') {
                $scope.navigateTo($scope.currentPath + '/' + file.name);
            } else {
                // Open file based on type
                const ext = file.name.toLowerCase().split('.').pop();
                const codeExts = ['js', 'ts', 'py', 'php', 'html', 'css', 'json', 'xml', 'yml', 'yaml', 'md', 'sql', 'sh'];
                
                if (codeExts.includes(ext)) {
                    // Open in code editor
                    $scope.editFile(file);
                } else {
                    // Download file
                    $scope.downloadFile(file);
                }
            }
        };
        
        // Toggle star
        $scope.toggleStar = function(file, event) {
            if (event) {
                event.stopPropagation();
            }
            file.starred = !file.starred;
            
            // Save starred state (implement API call)
            console.log('Starred:', file.name, file.starred);
        };
        
        // Sort by field
        $scope.sortBy = function(field) {
            if ($scope.sortField === field) {
                $scope.sortReverse = !$scope.sortReverse;
            } else {
                $scope.sortField = field;
                $scope.sortReverse = false;
            }
        };
        
        // Select all
        $scope.selectAll = function() {
            $scope.files.forEach(f => f.selected = true);
            $scope.updateSelectedFiles();
        };
        
        // Unselect all
        $scope.unSelectAll = function() {
            $scope.files.forEach(f => f.selected = false);
            $scope.updateSelectedFiles();
            $scope.showPreview = false;
            $scope.previewFile = null;
        };
        
        // Clear selection
        $scope.clearSelection = function() {
            $scope.unSelectAll();
        };
        
        // Toggle select all
        $scope.toggleSelectAll = function() {
            if ($scope.selectAll) {
                $scope.selectAll();
            } else {
                $scope.unSelectAll();
            }
        };
        
        // Search files
        $scope.searchFiles = function() {
            // Search is handled by Angular filter
        };
        
        // Format file size
        $scope.formatFileSize = function(bytes) {
            if (!bytes) return '0 B';
            const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
        };
        
        // Format date
        $scope.formatDate = function(date) {
            if (!date) return '';
            const d = new Date(date);
            const now = new Date();
            const diff = now - d;
            
            if (diff < 86400000) { // Less than 24 hours
                if (diff < 3600000) { // Less than 1 hour
                    const mins = Math.floor(diff / 60000);
                    return mins + ' min ago';
                }
                const hours = Math.floor(diff / 3600000);
                return hours + ' hour' + (hours > 1 ? 's' : '') + ' ago';
            }
            
            return d.toLocaleDateString();
        };
        
        // Get file icon
        $scope.getFileIcon = function(file) {
            if (file.type === 'folder') {
                return 'fa-folder';
            }
            
            const ext = file.name.toLowerCase().split('.').pop();
            const iconMap = {
                // Images
                'jpg': 'fa-image', 'jpeg': 'fa-image', 'png': 'fa-image', 'gif': 'fa-image',
                'svg': 'fa-image', 'webp': 'fa-image', 'bmp': 'fa-image', 'ico': 'fa-image',
                // Documents
                'pdf': 'fa-file-pdf', 'doc': 'fa-file-word', 'docx': 'fa-file-word',
                'xls': 'fa-file-excel', 'xlsx': 'fa-file-excel', 'ppt': 'fa-file-powerpoint',
                'pptx': 'fa-file-powerpoint', 'txt': 'fa-file-alt', 'rtf': 'fa-file-alt',
                // Code
                'js': 'fa-file-code', 'ts': 'fa-file-code', 'py': 'fa-file-code',
                'php': 'fa-file-code', 'html': 'fa-file-code', 'css': 'fa-file-code',
                'json': 'fa-file-code', 'xml': 'fa-file-code', 'sql': 'fa-file-code',
                // Archives
                'zip': 'fa-file-archive', 'rar': 'fa-file-archive', '7z': 'fa-file-archive',
                'tar': 'fa-file-archive', 'gz': 'fa-file-archive', 'bz2': 'fa-file-archive',
                // Media
                'mp3': 'fa-file-audio', 'wav': 'fa-file-audio', 'flac': 'fa-file-audio',
                'mp4': 'fa-file-video', 'avi': 'fa-file-video', 'mkv': 'fa-file-video'
            };
            
            return iconMap[ext] || 'fa-file';
        };
        
        // Show context menu
        $scope.showContextMenu = function(file, event) {
            event.preventDefault();
            event.stopPropagation();
            
            $scope.contextFile = file;
            $scope.contextMenuX = event.pageX;
            $scope.contextMenuY = event.pageY;
            $scope.showContextMenu = true;
            
            // Adjust position if menu goes off screen
            $timeout(function() {
                const menu = document.querySelector('.fm-context-menu');
                if (menu) {
                    const rect = menu.getBoundingClientRect();
                    if (rect.right > window.innerWidth) {
                        $scope.contextMenuX = event.pageX - rect.width;
                    }
                    if (rect.bottom > window.innerHeight) {
                        $scope.contextMenuY = event.pageY - rect.height;
                    }
                }
            });
        };
        
        // Hide context menu
        $scope.hideContextMenu = function() {
            $scope.showContextMenu = false;
            $scope.contextFile = null;
        };
        
        // Download file
        $scope.downloadFile = function(file, event) {
            if (event) {
                event.stopPropagation();
            }
            
            // Implement download logic
            console.log('Download:', file.name);
            window.location.href = '/filemanager/download?path=' + encodeURIComponent($scope.currentPath + '/' + file.name);
        };
        
        // Download selected
        $scope.downloadSelected = function() {
            if ($scope.selectedFiles.length === 1) {
                $scope.downloadFile($scope.selectedFiles[0]);
            } else {
                // Create zip and download
                console.log('Download multiple:', $scope.selectedFiles);
            }
        };
        
        // Share file
        $scope.shareFile = function(file, event) {
            if (event) {
                event.stopPropagation();
            }
            
            // Implement share logic
            console.log('Share:', file.name);
            alert('Share functionality coming soon!');
        };
        
        // Share selected
        $scope.shareSelected = function() {
            console.log('Share selected:', $scope.selectedFiles);
            alert('Share functionality coming soon!');
        };
        
        // Delete file
        $scope.deleteFile = function(file, event) {
            if (event) {
                event.stopPropagation();
            }
            
            if (confirm('Are you sure you want to delete "' + file.name + '"?')) {
                // Implement delete logic
                console.log('Delete:', file.name);
                $scope.refreshFiles();
            }
        };
        
        // Delete selected
        $scope.deleteSelected = function() {
            if (confirm('Are you sure you want to delete ' + $scope.selectedFiles.length + ' items?')) {
                console.log('Delete selected:', $scope.selectedFiles);
                $scope.refreshFiles();
            }
        };
        
        // Move selected
        $scope.moveSelected = function() {
            console.log('Move selected:', $scope.selectedFiles);
            // Show move dialog
        };
        
        // Copy selected
        $scope.copySelected = function() {
            $scope.clipboard = {
                action: 'copy',
                files: [...$scope.selectedFiles]
            };
            console.log('Copy selected:', $scope.selectedFiles);
        };
        
        // Cut file
        $scope.cutFile = function(file) {
            $scope.clipboard = {
                action: 'cut',
                files: [file]
            };
            $scope.hideContextMenu();
        };
        
        // Copy file
        $scope.copyFile = function(file) {
            $scope.clipboard = {
                action: 'copy',
                files: [file]
            };
            $scope.hideContextMenu();
        };
        
        // Paste file
        $scope.pasteFile = function() {
            if ($scope.clipboard) {
                console.log('Paste:', $scope.clipboard);
                // Implement paste logic
                $scope.refreshFiles();
            }
            $scope.hideContextMenu();
        };
        
        // Rename file
        $scope.renameFile = function(file) {
            const newName = prompt('Enter new name:', file.name);
            if (newName && newName !== file.name) {
                console.log('Rename:', file.name, 'to', newName);
                // Implement rename logic
                $scope.refreshFiles();
            }
            $scope.hideContextMenu();
        };
        
        // Edit file
        $scope.editFile = function(file) {
            console.log('Edit:', file.name);
            // Open editor modal
            window.location.href = '/filemanager/edit?path=' + encodeURIComponent($scope.currentPath + '/' + file.name);
        };
        
        // Show properties
        $scope.showProperties = function(file) {
            console.log('Properties:', file);
            alert('File: ' + file.name + '\nSize: ' + $scope.formatFileSize(file.size) + '\nModified: ' + $scope.formatDate(file.modified) + '\nPermissions: ' + file.permissions);
            $scope.hideContextMenu();
        };
        
        // Close preview
        $scope.closePreview = function() {
            $scope.showPreview = false;
            $scope.previewFile = null;
        };
        
        // Show upload modal
        $scope.showUploadModal = function() {
            $scope.showUpload = true;
            $scope.uploadQueue = [];
        };
        
        // Close upload modal
        $scope.closeUploadModal = function() {
            $scope.showUpload = false;
            if (uploader.queue.length > 0) {
                uploader.clearQueue();
            }
        };
        
        // Create new folder
        $scope.createNewFolder = function() {
            const folderName = prompt('Enter folder name:');
            if (folderName) {
                console.log('Create folder:', folderName);
                // Implement create folder logic
                $scope.refreshFiles();
            }
        };
        
        // Remove from upload queue
        $scope.removeFromQueue = function(file) {
            const index = $scope.uploadQueue.indexOf(file);
            if (index > -1) {
                $scope.uploadQueue.splice(index, 1);
            }
        };
        
        // Start upload
        $scope.startUpload = function() {
            uploader.uploadAll();
        };
        
        // Setup event listeners
        $scope.setupEventListeners = function() {
            // Hide context menu on click
            document.addEventListener('click', function() {
                $scope.$apply(function() {
                    $scope.hideContextMenu();
                });
            });
            
            // Keyboard shortcuts
            document.addEventListener('keydown', function(e) {
                $scope.$apply(function() {
                    // Ctrl/Cmd + A - Select all
                    if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
                        e.preventDefault();
                        $scope.selectAll();
                    }
                    
                    // Delete - Delete selected
                    if (e.key === 'Delete' && $scope.selectedFiles.length > 0) {
                        e.preventDefault();
                        $scope.deleteSelected();
                    }
                    
                    // F2 - Rename
                    if (e.key === 'F2' && $scope.selectedFiles.length === 1) {
                        e.preventDefault();
                        $scope.renameFile($scope.selectedFiles[0]);
                    }
                    
                    // Ctrl/Cmd + C - Copy
                    if ((e.ctrlKey || e.metaKey) && e.key === 'c' && $scope.selectedFiles.length > 0) {
                        e.preventDefault();
                        $scope.copySelected();
                    }
                    
                    // Ctrl/Cmd + X - Cut
                    if ((e.ctrlKey || e.metaKey) && e.key === 'x' && $scope.selectedFiles.length > 0) {
                        e.preventDefault();
                        $scope.clipboard = {
                            action: 'cut',
                            files: [...$scope.selectedFiles]
                        };
                    }
                    
                    // Ctrl/Cmd + V - Paste
                    if ((e.ctrlKey || e.metaKey) && e.key === 'v' && $scope.clipboard) {
                        e.preventDefault();
                        $scope.pasteFile();
                    }
                    
                    // Escape - Clear selection
                    if (e.key === 'Escape') {
                        $scope.clearSelection();
                        $scope.hideContextMenu();
                    }
                });
            });
            
            // Drag and drop
            const filesContainer = document.querySelector('.fm-files-container');
            if (filesContainer) {
                filesContainer.addEventListener('dragover', function(e) {
                    e.preventDefault();
                    $scope.$apply(function() {
                        $scope.isDragging = true;
                    });
                });
                
                filesContainer.addEventListener('dragleave', function(e) {
                    if (e.target === filesContainer) {
                        $scope.$apply(function() {
                            $scope.isDragging = false;
                        });
                    }
                });
                
                filesContainer.addEventListener('drop', function(e) {
                    e.preventDefault();
                    $scope.$apply(function() {
                        $scope.isDragging = false;
                        // Handle dropped files
                        const files = e.dataTransfer.files;
                        if (files.length > 0) {
                            $scope.showUploadModal();
                            // Add files to uploader
                            for (let i = 0; i < files.length; i++) {
                                uploader.addToQueue(files[i]);
                            }
                        }
                    });
                });
            }
            
            // Upload modal drag and drop
            const uploadZone = document.querySelector('.fm-upload-zone');
            if (uploadZone) {
                uploadZone.addEventListener('dragover', function(e) {
                    e.preventDefault();
                    $scope.$apply(function() {
                        $scope.uploadDragging = true;
                    });
                });
                
                uploadZone.addEventListener('dragleave', function(e) {
                    $scope.$apply(function() {
                        $scope.uploadDragging = false;
                    });
                });
                
                uploadZone.addEventListener('drop', function(e) {
                    e.preventDefault();
                    $scope.$apply(function() {
                        $scope.uploadDragging = false;
                        // Handle dropped files
                        const files = e.dataTransfer.files;
                        for (let i = 0; i < files.length; i++) {
                            uploader.addToQueue(files[i]);
                        }
                    });
                });
            }
        };
        
        // Initialize on load
        $scope.init();
    }])
    .directive('ngRightClick', ['$parse', function($parse) {
        return function(scope, element, attrs) {
            const fn = $parse(attrs.ngRightClick);
            element.bind('contextmenu', function(event) {
                scope.$apply(function() {
                    event.preventDefault();
                    fn(scope, {$event: event});
                });
            });
        };
    }]);

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}