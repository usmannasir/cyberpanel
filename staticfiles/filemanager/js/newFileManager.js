// Helper functions
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

function bytesToHumanReadable(bytes, suffix = 'B') {
    let units = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z'];
    let i = 0;
    while (Math.abs(bytes) >= 1024 && i < units.length - 1) {
        bytes /= 1024;
        ++i;
    }
    return bytes.toFixed(1) + units[i] + suffix;
}

function kilobytesToHumanReadable(kilobytes, suffix = 'KB') {
    let units = ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    let i = 0;
    while (Math.abs(kilobytes) >= 1024 && i < units.length - 1) {
        kilobytes /= 1024;
        ++i;
    }
    return kilobytes.toFixed(2) + ' ' + units[i];
}

function findFileExtension(fileName) {
    return (/[.]/.exec(fileName)) ? /[^.]+$/.exec(fileName) : undefined;
}

// Initialize Angular module
(function() {
    'use strict';
    
    console.log('File Manager: Initializing...');
    
    // Wait for Angular and dependencies to load
    if (typeof angular === 'undefined') {
        console.error('File Manager: Angular not loaded');
        return;
    }
    
    // Since the base template already defines CyberCP module, we'll just get it
    var app = angular.module('CyberCP');
    console.log('File Manager: Using CyberCP module');

    // Define the controller
    app.controller('newFileManagerCtrl', ['$scope', '$http', '$window', '$timeout', '$compile', '$injector',
    function ($scope, $http, $window, $timeout, $compile, $injector) {
    
    // Try to get FileUploader if available
    var FileUploader;
    try {
        FileUploader = $injector.get('FileUploader');
    } catch (e) {
        // FileUploader not available, we'll create a fallback
        console.warn('FileUploader not available, using fallback upload');
        FileUploader = null;
    }
    
    // Initialize editor later to avoid conflicts
    var editor;
    var aceEditorMode = '';
    
    // Domain and path initialization
    var domainName = $("#domainNameInitial").text();
    var domainRandomSeed = "";
    
    // Path management
    $scope.currentRPath = "/";
    var homeRPathBack = "/";
    
    if (domainName === "") {
        // Root user mode
        $scope.currentPath = "/";
        $scope.startingPath = "/";
        $scope.completeStartingPath = "/";
        var homePathBack = "/";
        var trashPath = '/.trash';
    } else {
        // Domain user mode
        var homePathBack = "/home/" + domainName;
        $scope.currentPath = "/home/" + domainName;
        $scope.startingPath = domainName;
        $scope.completeStartingPath = "/home/" + domainName;
        var trashPath = homePathBack + '/.trash';
    }
    
    // UI State variables
    $scope.editDisable = true;
    $scope.treeLoading = true;
    $scope.errorMessageEditor = true;
    $scope.htmlEditorLoading = true;
    $scope.saveSuccess = true;
    $scope.errorMessageFolder = true;
    $scope.errorMessageFile = true;
    $scope.createSuccess = true;
    $scope.deleteLoading = true;
    $scope.compressionLoading = true;
    $scope.extractionLoading = true;
    $scope.moveLoading = true;
    $scope.copyLoading = true;
    $scope.renameLoading = true;
    $scope.changePermissionsLoading = true;
    $scope.cyberPanelLoading = true;
    $scope.errorMessage = true;
    
    // Permissions
    $scope.userPermissions = 0;
    $scope.groupPermissions = 0;
    $scope.wordlPermissions = 0;
    
    // File management
    var allFilesAndFolders = []; // Selected files array
    $scope.allFilesAndFolders = []; // All files data for display
    
    // Modern UI enhancements
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
    
    // Test data to verify ng-repeat works
    $scope.testItems = [
        {name: 'Test 1'},
        {name: 'Test 2'},
        {name: 'Test 3'}
    ];
    
    // Debug: Log scope binding
    console.log('File Manager: Scope initialized, testItems:', $scope.testItems);
    
    // Helper function to add files to selection list
    function addFileOrFolderToList(nodeName) {
        allFilesAndFolders.push(nodeName);
    }
    
    // Modal functions
    $scope.showUploadBox = function () {
        $("#uploadBox").modal();
    };
    
    $scope.showHTMLEditorModal = function (MainFM = 0) {
        $scope.fileInEditor = allFilesAndFolders[0];
        $("#showHTMLEditor").modal();
        if (MainFM === 0) {
            $scope.getFileContents();
        } else {
            $scope.getFileContents(1);
        }
    };
    
    $scope.showCreateFolderModal = function () {
        $("#showCreateFolder").modal();
    };
    
    $scope.showCreateFileModal = function () {
        $("#showCreateFile").modal();
    };
    
    $scope.showDeleteModal = function () {
        $("#showDelete").modal();
    };
    
    $scope.showCompressionModal = function () {
        $scope.listOfFiles = "";
        $scope.compressedFileName = "";
        
        for (var i = 0; i < allFilesAndFolders.length; i++) {
            $scope.listOfFiles = $scope.listOfFiles + allFilesAndFolders[i] + "\n";
        }
        
        $("#showCompression").modal();
    };
    
    $scope.showExtractionModal = function () {
        $scope.extractionLocation = $scope.currentPath || $scope.completeStartingPath;
        $scope.fileToBeExtracted = allFilesAndFolders[0];
        $("#showExtraction").modal();
    };
    
    $scope.showMoveModal = function () {
        $scope.pathToMoveTo = $scope.currentPath || $scope.completeStartingPath;
        $scope.listOfFiles = "";
        
        for (var i = 0; i < allFilesAndFolders.length; i++) {
            $scope.listOfFiles = $scope.listOfFiles + allFilesAndFolders[i] + "\n";
        }
        
        $("#showMove").modal();
    };
    
    $scope.showCopyModal = function () {
        $scope.pathToCopyTo = $scope.currentPath || $scope.completeStartingPath;
        $scope.listOfFiles = "";
        
        for (var i = 0; i < allFilesAndFolders.length; i++) {
            $scope.listOfFiles = $scope.listOfFiles + allFilesAndFolders[i] + "\n";
        }
        
        $("#showCopy").modal();
    };
    
    $scope.showRenameModal = function () {
        $scope.fileToRename = allFilesAndFolders[0];
        $scope.newFileName = "";
        $("#showRename").modal();
    };
    
    $scope.showPermissionsModal = function () {
        $scope.permissionsPath = allFilesAndFolders[0];
        $("#showPermissions").modal();
    };
    
    $scope.showRestoreModal = function () {
        $("#showRestore").modal();
    };
    
    // Button activation based on selection
    $scope.buttonActivator = function () {
        if (allFilesAndFolders.length > 0) {
            $(".notActivate").prop("disabled", false);
        } else {
            $(".notActivate").prop("disabled", true);
        }
        if (allFilesAndFolders.length > 1) {
            $(".notActivateOnMulti").prop("disabled", true);
        } else {
            $(".notActivateOnMulti").prop("disabled", false);
        }
    };
    
    // Tree view functions
    function finalPrepration(parentNode, path, completePath, dropDown) {
        if (dropDown) {
            // Create the tree link div
            var linkDiv = document.createElement("div");
            linkDiv.setAttribute("class", "fm-tree-link");
            linkDiv.addEventListener("click", function () {
                $scope.fetchForTableSecondary(null, "fromTree", completePath);
                $scope.$apply();
            });
            
            // Create folder icon
            var iNodeFolder = document.createElement("i");
            iNodeFolder.setAttribute("class", "fas fa-folder fm-tree-icon");
            
            // Create folder name
            var pathSpan = document.createElement("span");
            pathSpan.textContent = path;
            
            // Create expand icon
            var expandIcon = document.createElement("i");
            expandIcon.setAttribute("class", "fas fa-chevron-right fm-tree-expand");
            expandIcon.addEventListener("click", function(event) {
                event.stopPropagation();
                var childrenUl = parentNode.querySelector('.fm-tree-children');
                if (!childrenUl) {
                    childrenUl = document.createElement("ul");
                    childrenUl.setAttribute("class", "fm-tree-children");
                    parentNode.appendChild(childrenUl);
                }
                
                if (childrenUl.classList.contains('expanded')) {
                    childrenUl.classList.remove('expanded');
                    expandIcon.classList.remove('fa-chevron-down');
                    expandIcon.classList.add('fa-chevron-right');
                } else {
                    childrenUl.classList.add('expanded');
                    expandIcon.classList.remove('fa-chevron-right');
                    expandIcon.classList.add('fa-chevron-down');
                    
                    // Load children if not loaded
                    if (childrenUl.children.length === 0) {
                        $scope.fetchChilds(childrenUl, completePath, "minus");
                    }
                }
            });
            
            linkDiv.appendChild(iNodeFolder);
            linkDiv.appendChild(pathSpan);
            linkDiv.appendChild(expandIcon);
            parentNode.appendChild(linkDiv);
        }
    }
    
    function prepareChildNodeLI(path, completePath, dropDown) {
        var liNode = document.createElement("li");
        liNode.setAttribute("id", completePath.replace(/[^a-zA-Z0-9]/g, '_'));
        liNode.setAttribute("class", "fm-tree-item");
        liNode.setAttribute("data-path", completePath);
        finalPrepration(liNode, path, completePath, dropDown);
        return liNode;
    }
    
    function prepareChildNodeUL() {
        var ulNode = document.createElement("ul");
        ulNode.setAttribute("class", "fm-tree-children");
        return ulNode;
    }
    
    window.activateMinus = function(node, completePath) {
        if (node.className === "fa fa-minus") {
            deleteChilds(node, completePath);
            node.className = "fa fa-plus";
        } else {
            var element = angular.element(document.getElementById("folderStructureContent"));
            $scope.fetchChilds(element, completePath, "minus");
            node.className = "fa fa-minus";
        }
    };
    
    function deleteChilds(aNode, completePath) {
        $("#" + completePath).find("ul").remove();
    }
    
    // Tree fetching
    $scope.fetchChilds = function (element, completePath, functionName) {
        $scope.treeLoading = false;
        
        var url = "/filemanager/controller";
        var data = {
            completeStartingPath: completePath,
            method: "list",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.fetchStatus === 1) {
                $scope.treeLoading = true;
                
                if (functionName === "startPoint") {
                    var ulNode = prepareChildNodeUL();
                    
                    // Process the response data similar to original format
                    var filesData = response.data;
                    var keys = Object.keys(filesData);
                    
                    for (var i = 0; i < keys.length; i++) {
                        if (keys[i] === "error_message" || keys[i] === "status") {
                            continue;
                        }
                        
                        var fileData = filesData[keys[i]];
                        if (fileData && fileData.length >= 3) {
                            var fileName = fileData[0];
                            var completePath = fileData[1];
                            var dropDown = fileData[2];
                            
                            if (dropDown) {
                                var liNode = prepareChildNodeLI(fileName, completePath, dropDown);
                                ulNode.appendChild(liNode);
                            }
                        }
                    }
                    
                    var nodeToInsert = $compile(ulNode)($scope);
                    element.append(nodeToInsert);
                } else if (functionName === "minus") {
                    var parent = element;
                    
                    if (parent.getElementsByTagName('ul').length === 0) {
                        var ulNode = prepareChildNodeUL();
                        
                        // Process the response data 
                        var filesData = response.data;
                        var keys = Object.keys(filesData);
                        
                        for (var i = 0; i < keys.length; i++) {
                            if (keys[i] === "error_message" || keys[i] === "status") {
                                continue;
                            }
                            
                            var fileData = filesData[keys[i]];
                            if (fileData && fileData.length >= 3) {
                                var fileName = fileData[0];
                                var completePath = fileData[1];
                                var dropDown = fileData[2];
                                
                                if (dropDown) {
                                    var liNode = prepareChildNodeLI(fileName, completePath, dropDown);
                                    ulNode.appendChild(liNode);
                                }
                            }
                        }
                        
                        var nodeToInsert = $compile(ulNode)($scope);
                        angular.element(parent).append(nodeToInsert);
                    }
                }
            } else {
                $scope.treeLoading = true;
            }
        });
    };
    
    // Table functions
    function createTR(fileName, fileSize, lastModified, permissions, dirCheck) {
        return {
            fileName: fileName,
            fileSize: fileSize,
            lastModified: lastModified,
            permissions: permissions,
            dirCheck: dirCheck === true || dirCheck === 1 || dirCheck === "1" || dirCheck === "True"
        };
    }
    
    $scope.fetchForTableSecondary = function (node, functionName, completePath) {
        console.log('File Manager: fetchForTableSecondary called with:', {
            functionName: functionName,
            nodeText: node ? node.textContent : null,
            completePath: completePath,
            currentPath: $scope.currentPath,
            completeStartingPath: $scope.completeStartingPath
        });
        
        $scope.isLoading = true;
        allFilesAndFolders = [];
        $scope.selectedFiles = [];
        $scope.buttonActivator();
        
        var url = "/filemanager/controller";
        var completePathToFile = "";
        
        if (domainName === "") {
            // Root user logic
            if (functionName === "startPoint") {
                completePathToFile = $scope.currentRPath;
            } else if (functionName === "doubleClick") {
                // Ensure we don't create double slashes
                var separator = $scope.currentRPath.endsWith('/') ? '' : '/';
                completePathToFile = $scope.currentRPath + separator + node.textContent;
                $scope.currentRPath = completePathToFile;
            } else if (functionName === "fromTree") {
                $scope.currentRPath = completePath;
                completePathToFile = completePath;
            } else if (functionName === "pathNavigation") {
                completePathToFile = $scope.currentPath;
                $scope.currentRPath = completePathToFile;
            }
        } else {
            // Domain user logic
            if (functionName === "startPoint") {
                completePathToFile = $scope.completeStartingPath;
            } else if (functionName === "doubleClick") {
                // Ensure we don't create double slashes
                var separator = $scope.completeStartingPath.endsWith('/') ? '' : '/';
                completePathToFile = $scope.completeStartingPath + separator + node.textContent;
                $scope.completeStartingPath = completePathToFile;
            } else if (functionName === "fromTree") {
                $scope.completeStartingPath = completePath;
                completePathToFile = completePath;
            } else if (functionName === "pathNavigation") {
                completePathToFile = $scope.currentPath;
                $scope.completeStartingPath = completePathToFile;
            } else if (functionName === "refresh") {
                completePathToFile = $scope.completeStartingPath;
            }
        }
        
        console.log('File Manager: Path after logic:', completePathToFile);
        
        var data = {
            method: "listForTable",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName,
            completeStartingPath: completePathToFile
        };
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            console.log('File Manager: Server response:', {
                status: response.data.status,
                dataKeys: Object.keys(response.data),
                error: response.data.error_message
            });
            
            if (response.data.status === 1) {
                $scope.isLoading = false;
                $scope.allFilesAndFolders = [];
                
                // Process response data
                var keys = Object.keys(response.data);
                console.log('File Manager: Processing', keys.length, 'items from server');
                
                keys.forEach(function(key) {
                    if (key !== 'status' && key !== 'error_message') {
                        var fileData = response.data[key];
                        if (fileData && typeof fileData === 'object' && fileData.length >= 6) {
                            // Skip ..filemanagerkey file
                            if (fileData[0] === "..filemanagerkey") {
                                return;
                            }
                            
                            var fileItem = createTR(
                                fileData[0], // fileName
                                fileData[1], // fileSize  
                                fileData[2], // lastModified
                                fileData[4], // permissions (index 4 in original)
                                fileData[5]  // dirCheck (index 5 in original)
                            );
                            $scope.allFilesAndFolders.push(fileItem);
                        }
                    }
                });
                
                console.log('File Manager: Loaded', $scope.allFilesAndFolders.length, 'files for display');
                console.log('File Manager: Sample files:', $scope.allFilesAndFolders.slice(0, 3));
                console.log('File Manager: Current viewMode:', $scope.viewMode);
                
                // Update path
                if (domainName === "") {
                    $scope.currentPath = completePathToFile;
                } else {
                    $scope.currentPath = completePathToFile;
                }
                
                $scope.updatePathSegments();
                
                // Force Angular to update the view
                $timeout(function() {
                    console.log('File Manager: Forcing digest cycle after navigation');
                    console.log('File Manager: Current scope data:', {
                        viewMode: $scope.viewMode,
                        isLoading: $scope.isLoading,
                        filesLength: $scope.allFilesAndFolders.length,
                        firstFile: $scope.allFilesAndFolders[0],
                        currentPath: $scope.currentPath,
                        completeStartingPath: $scope.completeStartingPath
                    });
                    
                    // Ensure view mode is preserved
                    var savedViewMode = localStorage.getItem('fileManagerViewMode') || 'grid';
                    if ($scope.viewMode !== savedViewMode) {
                        console.log('File Manager: Restoring viewMode to:', savedViewMode);
                        $scope.viewMode = savedViewMode;
                    }
                    
                    // Force scope update
                    if (!$scope.$$phase && !$scope.$root.$$phase) {
                        $scope.$apply();
                    }
                    
                    // Double-check grid visibility
                    var gridElement = document.querySelector('.fm-grid');
                    if (gridElement) {
                        console.log('Grid element found:', gridElement);
                        console.log('Grid display:', window.getComputedStyle(gridElement).display);
                        console.log('Grid children:', gridElement.children.length);
                        
                        // Check ng-show condition
                        var ngShowCondition = $scope.viewMode === 'grid' && !$scope.isLoading && $scope.allFilesAndFolders && $scope.allFilesAndFolders.length > 0;
                        console.log('Grid ng-show condition:', ngShowCondition);
                    }
                    
                    // Also check list view
                    var listElement = document.querySelector('.fm-list');
                    if (listElement) {
                        console.log('List element found:', listElement);
                        console.log('List display:', window.getComputedStyle(listElement).display);
                    }
                }, 100);
            } else {
                $scope.isLoading = false;
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        }).catch(function (error) {
            $scope.isLoading = false;
            console.error('Error:', error);
        });
    };
    
    // Select all files
    $scope.selectAll = function () {
        allFilesAndFolders = [];
        $scope.selectedFiles = [];
        $scope.allFilesAndFolders.forEach(function(file) {
            if (file.fileName !== "..") {
                allFilesAndFolders.push(file.fileName);
                $scope.selectedFiles.push(file);
            }
        });
        $scope.buttonActivator();
    };
    
    // Unselect all files
    $scope.unSelectAll = function () {
        allFilesAndFolders = [];
        $scope.selectedFiles = [];
        $scope.buttonActivator();
    };
    
    // Right-click functions
    $scope.rightClickCallBack = function (event, trNode) {
        event.preventDefault();
        
        $("#rightClickMenu").css("display", "block");
        $("#rightClickMenu").css("top", event.clientY);
        $("#rightClickMenu").css("left", event.clientX);
        
        $scope.addFileOrFolderToListForRightClick(trNode.fileName);
    };
    
    $scope.addFileOrFolderToListForRightClick = function (nodeName) {
        allFilesAndFolders = [nodeName];
        $scope.buttonActivator();
    };
    
    // File operations
    $scope.getFileContents = function (MainFM = 0) {
        $scope.htmlEditorLoading = false;
        
        var data = {
            method: "readFileContents",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName,
            fileName: allFilesAndFolders[0],
            completeStartingPath: $scope.completeStartingPath
        };
        
        var url = "/filemanager/controller";
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.status === 1) {
                $scope.htmlEditorLoading = true;
                // Initialize editor if not already done
                if (!editor && typeof ace !== 'undefined') {
                    editor = ace.edit("htmlEditorContent");
                    editor.setTheme("ace/theme/monokai");
                }
                editor.setValue(response.data.fileContents);
                $scope.editWithCodeMirror();
            } else {
                $scope.htmlEditorLoading = true;
                $scope.errorMessageEditor = false;
                $scope.error_message = response.data.error_message;
            }
        });
    };
    
    $scope.putFileContents = function () {
        $scope.htmlEditorLoading = false;
        $scope.saveSuccess = true;
        
        // Ensure editor is initialized
        if (!editor) {
            console.error('Editor not initialized');
            return;
        }
        
        var data = {
            method: "writeFileContents",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName,
            fileName: allFilesAndFolders[0],
            fileContent: editor.getValue(),
            completeStartingPath: $scope.completeStartingPath
        };
        
        var url = "/filemanager/controller";
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.status === 1) {
                $scope.htmlEditorLoading = true;
                $scope.saveSuccess = false;
                $timeout(function() {
                    $scope.saveSuccess = true;
                }, 3000);
            } else {
                $scope.htmlEditorLoading = true;
                $scope.errorMessageEditor = false;
                $scope.error_message = response.data.error_message;
            }
        });
    };
    
    $scope.editWithCodeMirror = function () {
        var mode = 'htmlmixed';
        var fileExtension = findFileExtension(allFilesAndFolders[0]);
        
        if (fileExtension) {
            switch (fileExtension[0].toLowerCase()) {
                case 'html':
                case 'htm':
                    mode = 'htmlmixed';
                    break;
                case 'js':
                    mode = 'javascript';
                    break;
                case 'css':
                    mode = 'css';
                    break;
                case 'php':
                    mode = 'php';
                    break;
                case 'py':
                    mode = 'python';
                    break;
                case 'rb':
                    mode = 'ruby';
                    break;
                case 'java':
                    mode = 'text/x-java';
                    break;
                case 'c':
                case 'cpp':
                case 'h':
                    mode = 'text/x-c++src';
                    break;
                case 'sh':
                    mode = 'shell';
                    break;
                case 'conf':
                    mode = 'nginx';
                    break;
                case 'json':
                    mode = 'javascript';
                    break;
                case 'xml':
                    mode = 'xml';
                    break;
                case 'sql':
                    mode = 'text/x-sql';
                    break;
                case 'md':
                    mode = 'markdown';
                    break;
                default:
                    mode = 'htmlmixed';
            }
        }
        
        if (editor) {
            editor.getSession().setMode("ace/mode/" + mode);
        }
    };
    
    // Initialize modal variables
    $scope.newFolderName = "";
    $scope.newFileName = "";
    $scope.pathToMoveTo = "";
    $scope.pathToCopyTo = "";
    $scope.listOfFiles = "";
    $scope.compressedFileName = "";
    $scope.compressionType = "zip";
    $scope.extractionLocation = "";
    $scope.fileToBeExtracted = "";
    $scope.fileToRename = "";
    $scope.permissionsPath = "";
    $scope.skipTrash = false;
    $scope.fileInEditor = "";
    
    // Create new folder
    $scope.createNewFolder = function () {
        $scope.errorMessageFolder = true;
        $scope.cyberPanelLoading = false;
        
        var folderName = $scope.newFolderName;
        
        if (folderName === "" || folderName === undefined) {
            $scope.errorMessageFolder = false;
            $scope.error_message = "Please enter folder name.";
            $scope.cyberPanelLoading = true;
            return;
        }
        
        var data = {
            method: "createNewFolder",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName,
            folderName: folderName,
            completeStartingPath: $scope.completeStartingPath
        };
        
        var url = "/filemanager/controller";
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.status === 1) {
                $scope.cyberPanelLoading = true;
                $scope.createSuccess = false;
                $scope.errorMessageFolder = true;
                $scope.folderName = "";
                $timeout(function() {
                    $scope.createSuccess = true;
                    $("#showCreateFolder").modal('hide');
                    $scope.fetchForTableSecondary(null, "startPoint");
                }, 3000);
            } else {
                $scope.cyberPanelLoading = true;
                $scope.errorMessageFolder = false;
                $scope.error_message = response.data.error_message;
            }
        });
    };
    
    $scope.createFolderEnter = function ($event) {
        if ($event.which === 13) {
            $scope.createNewFolder();
        }
    };
    
    // Create new file
    $scope.createNewFile = function () {
        $scope.errorMessageFile = true;
        $scope.cyberPanelLoading = false;
        
        var fileName = $scope.newFileName;
        
        if (fileName === "" || fileName === undefined) {
            $scope.errorMessageFile = false;
            $scope.error_message = "Please enter file name.";
            $scope.cyberPanelLoading = true;
            return;
        }
        
        var data = {
            method: "createNewFile",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName,
            fileName: fileName,
            completeStartingPath: $scope.completeStartingPath
        };
        
        var url = "/filemanager/controller";
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.status === 1) {
                $scope.cyberPanelLoading = true;
                $scope.createSuccess = false;
                $scope.errorMessageFile = true;
                $scope.fileName = "";
                $timeout(function() {
                    $scope.createSuccess = true;
                    $("#showCreateFile").modal('hide');
                    $scope.fetchForTableSecondary(null, "startPoint");
                }, 3000);
            } else {
                $scope.cyberPanelLoading = true;
                $scope.errorMessageFile = false;
                $scope.error_message = response.data.error_message;
            }
        });
    };
    
    $scope.createFileEnter = function ($event) {
        if ($event.which === 13) {
            $scope.createNewFile();
        }
    };
    
    // Delete files/folders
    $scope.deleteFolderOrFile = function () {
        $scope.deleteLoading = false;
        
        var data = {
            method: "deleteFolderOrFile",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName,
            listOfFiles: allFilesAndFolders,
            completeStartingPath: $scope.completeStartingPath
        };
        
        var url = "/filemanager/controller";
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.status === 1) {
                $scope.deleteLoading = true;
                $("#showDelete").modal('hide');
                new PNotify({
                    title: 'Success!',
                    text: 'Files deleted successfully',
                    type: 'success'
                });
                $scope.fetchForTableSecondary(null, "startPoint");
            } else {
                $scope.deleteLoading = true;
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        });
    };
    
    // Compression
    $scope.startCompression = function () {
        $scope.compressionLoading = false;
        
        var compressedFileName = $scope.compressedFileName;
        var compressionType = $scope.compressionType;
        
        if (compressedFileName === "" || compressedFileName === undefined) {
            new PNotify({
                title: 'Error!',
                text: 'Please enter file name',
                type: 'error'
            });
            $scope.compressionLoading = true;
            return;
        }
        
        var data = {
            method: "compress",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName,
            listOfFiles: allFilesAndFolders,
            compressedFileName: compressedFileName,
            compressionType: compressionType,
            completeStartingPath: $scope.completeStartingPath
        };
        
        var url = "/filemanager/controller";
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.status === 1) {
                $scope.compressionLoading = true;
                $("#showCompression").modal('hide');
                new PNotify({
                    title: 'Success!',
                    text: 'Files compressed successfully',
                    type: 'success'
                });
                $scope.fetchForTableSecondary(null, "startPoint");
            } else {
                $scope.compressionLoading = true;
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        });
    };
    
    // Extraction
    $scope.startExtraction = function () {
        $scope.extractionLoading = false;
        
        var extractionLocation = $scope.extractionLocation;
        var fileToExtract = allFilesAndFolders[0];
        
        var data = {
            method: "extract",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName,
            fileToExtract: fileToExtract,
            extractionLocation: extractionLocation,
            completeStartingPath: $scope.completeStartingPath
        };
        
        var url = "/filemanager/controller";
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.status === 1) {
                $scope.extractionLoading = true;
                $("#showExtraction").modal('hide');
                new PNotify({
                    title: 'Success!',
                    text: 'Files extracted successfully',
                    type: 'success'
                });
                $scope.fetchForTableSecondary(null, "startPoint");
            } else {
                $scope.extractionLoading = true;
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        });
    };
    
    // Move files
    $scope.startMoving = function () {
        $scope.moveLoading = false;
        
        var newPath = $scope.pathToMoveTo;
        
        if (newPath === "" || newPath === undefined) {
            new PNotify({
                title: 'Error!',
                text: 'Please enter destination path',
                type: 'error'
            });
            $scope.moveLoading = true;
            return;
        }
        
        var data = {
            method: "move",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName,
            listOfFiles: allFilesAndFolders,
            newPath: newPath,
            completeStartingPath: $scope.completeStartingPath
        };
        
        var url = "/filemanager/controller";
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.status === 1) {
                $scope.moveLoading = true;
                $("#showMove").modal('hide');
                new PNotify({
                    title: 'Success!',
                    text: 'Files moved successfully',
                    type: 'success'
                });
                $scope.fetchForTableSecondary(null, "startPoint");
            } else {
                $scope.moveLoading = true;
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        });
    };
    
    // Copy files
    $scope.startCopying = function () {
        $scope.copyLoading = false;
        
        var newPath = $scope.pathToCopyTo;
        
        if (newPath === "" || newPath === undefined) {
            new PNotify({
                title: 'Error!',
                text: 'Please enter destination path',
                type: 'error'
            });
            $scope.copyLoading = true;
            return;
        }
        
        var data = {
            method: "copy",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName,
            listOfFiles: allFilesAndFolders,
            newPath: newPath,
            completeStartingPath: $scope.completeStartingPath
        };
        
        var url = "/filemanager/controller";
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.status === 1) {
                $scope.copyLoading = true;
                $("#showCopy").modal('hide');
                new PNotify({
                    title: 'Success!',
                    text: 'Files copied successfully',
                    type: 'success'
                });
                $scope.fetchForTableSecondary(null, "startPoint");
            } else {
                $scope.copyLoading = true;
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        });
    };
    
    // Rename file
    $scope.renameFile = function () {
        $scope.renameLoading = false;
        
        var newFileName = $scope.newFileName;
        var fileToRename = allFilesAndFolders[0];
        
        if (newFileName === "" || newFileName === undefined) {
            new PNotify({
                title: 'Error!',
                text: 'Please enter new file name',
                type: 'error'
            });
            $scope.renameLoading = true;
            return;
        }
        
        var data = {
            method: "rename",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName,
            fileToRename: fileToRename,
            newFileName: newFileName,
            completeStartingPath: $scope.completeStartingPath
        };
        
        var url = "/filemanager/controller";
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.status === 1) {
                $scope.renameLoading = true;
                $("#showRename").modal('hide');
                new PNotify({
                    title: 'Success!',
                    text: 'File renamed successfully',
                    type: 'success'
                });
                $scope.fetchForTableSecondary(null, "startPoint");
            } else {
                $scope.renameLoading = true;
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        });
    };
    
    $scope.renameEnter = function ($event) {
        if ($event.which === 13) {
            $scope.renameFile();
        }
    };
    
    // Permissions
    $scope.fixPermissions = function () {
        var data = {
            domainName: domainName
        };
        
        var url = "/filemanager/changePermissions";
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.permissionsChanged === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'Permissions fixed successfully',
                    type: 'success'
                });
            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        });
    };
    
    $scope.changePermissions = function (recursive) {
        $scope.changePermissionsLoading = false;
        
        var data = {
            method: "changePermissions",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName,
            fileName: allFilesAndFolders[0],
            recursive: recursive,
            newPermissions: $scope.userPermissions.toString() + $scope.groupPermissions.toString() + $scope.wordlPermissions.toString(),
            completeStartingPath: $scope.completeStartingPath
        };
        
        var url = "/filemanager/controller";
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.status === 1) {
                $scope.changePermissionsLoading = true;
                $("#showPermissions").modal('hide');
                new PNotify({
                    title: 'Success!',
                    text: 'Permissions changed successfully',
                    type: 'success'
                });
                $scope.fetchForTableSecondary(null, "startPoint");
            } else {
                $scope.changePermissionsLoading = true;
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        });
    };
    
    $scope.changePermissionsRecursively = function () {
        $scope.changePermissions(1);
    };
    
    // Permission UI updates
    $scope.updateReadPermissions = function (value) {
        $scope.userPermissions = parseInt($scope.userPermissions) + parseInt(value);
    };
    
    $scope.updateWritePermissions = function (value) {
        $scope.groupPermissions = parseInt($scope.groupPermissions) + parseInt(value);
    };
    
    $scope.updateExecutePermissions = function (value) {
        $scope.wordlPermissions = parseInt($scope.wordlPermissions) + parseInt(value);
    };
    
    // Download
    $scope.downloadFile = function () {
        if (domainName === "") {
            $window.location.href = "/filemanager/RootDownloadFile?fileToDownload=" + $scope.currentRPath + "/" + allFilesAndFolders[0];
        } else {
            $window.location.href = "/filemanager/downloadFile?fileToDownload=" + $scope.completeStartingPath + "/" + allFilesAndFolders[0] + "&domainName=" + domainName;
        }
    };
    
    $scope.RootDownloadFile = function () {
        $scope.downloadFile();
    };
    
    // Restore from trash
    $scope.restoreFinal = function () {
        var data = {
            method: "restore",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName,
            listOfFiles: allFilesAndFolders,
            completeStartingPath: $scope.completeStartingPath
        };
        
        var url = "/filemanager/controller";
        
        $http.post(url, data, {
            headers: {'X-CSRFToken': getCookie('csrftoken')}
        }).then(function (response) {
            if (response.data.status === 1) {
                $("#showRestore").modal('hide');
                new PNotify({
                    title: 'Success!',
                    text: 'Files restored successfully',
                    type: 'success'
                });
                $scope.fetchForTableSecondary(null, "startPoint");
            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.data.error_message,
                    type: 'error'
                });
            }
        });
    };
    
    // File uploader configuration
    var uploader;
    if (FileUploader) {
        uploader = $scope.uploader = new FileUploader({
            url: "/filemanager/upload",
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        uploader.onAfterAddingFile = function (fileItem) {
            if (domainName === "") {
                uploader.formData = [{
                    "method": "upload",
                    "home": homeRPathBack,
                    "domainName": domainName,
                    "domainRandomSeed": domainRandomSeed,
                    "completeStartingPath": $scope.currentRPath
                }];
            } else {
                uploader.formData = [{
                    "method": "upload",
                    "home": homePathBack,
                    "domainName": domainName,
                    "domainRandomSeed": domainRandomSeed,
                    "completeStartingPath": $scope.completeStartingPath
                }];
            }
        };
        
        uploader.onCompleteItem = function (fileItem, response, status, headers) {
            if (response.uploadStatus === 1) {
                new PNotify({
                    title: 'Success!',
                    text: 'File uploaded successfully',
                    type: 'success'
                });
                $scope.fetchForTableSecondary(null, "startPoint");
            } else {
                new PNotify({
                    title: 'Error!',
                    text: response.error_message,
                    type: 'error'
                });
            }
        };
        
        uploader.onProgressItem = function(item, progress) {
            $scope.uploadProgress = progress;
        };
        
        uploader.onCompleteAll = function() {
            $scope.uploadProgress = 100;
            $timeout(function() {
                $scope.uploadProgress = 0;
                $("#uploadBox").modal('hide');
            }, 1000);
        };
    } else {
        // Fallback for when FileUploader is not available
        $scope.uploader = {
            queue: [],
            uploadAll: function() {
                new PNotify({
                    title: 'Info',
                    text: 'Please ensure angular-file-upload library is loaded',
                    type: 'info'
                });
            }
        };
    }
    
    // Modern UI enhancements
    $scope.setViewMode = function(mode) {
        $scope.viewMode = mode;
        localStorage.setItem('fileManagerViewMode', mode);
    };
    
    $scope.sortFiles = function(sortBy) {
        if ($scope.sortBy === sortBy) {
            $scope.sortReverse = !$scope.sortReverse;
        } else {
            $scope.sortBy = sortBy;
            $scope.sortReverse = false;
        }
    };
    
    $scope.toggleFileSelection = function(file, event) {
        if (event) {
            event.stopPropagation();
        }
        
        var fileName = file.fileName;
        var index = allFilesAndFolders.indexOf(fileName);
        var selectedIndex = $scope.selectedFiles.indexOf(file);
        
        if (index === -1) {
            if (!$scope.isCtrlPressed && !event.shiftKey) {
                allFilesAndFolders = [];
                $scope.selectedFiles = [];
            }
            addFileOrFolderToList(fileName);
            $scope.selectedFiles.push(file);
        } else {
            if ($scope.isCtrlPressed || event.ctrlKey || event.metaKey) {
                allFilesAndFolders.splice(index, 1);
                $scope.selectedFiles.splice(selectedIndex, 1);
            } else {
                allFilesAndFolders = [fileName];
                $scope.selectedFiles = [file];
            }
        }
        
        $scope.buttonActivator();
    };
    
    $scope.isFileSelected = function(file) {
        return allFilesAndFolders.indexOf(file.fileName) !== -1;
    };
    
    // Helper function to add/remove files from selection
    function addFileOrFolderToList(fileName) {
        var index = allFilesAndFolders.indexOf(fileName);
        if (index === -1) {
            allFilesAndFolders.push(fileName);
        }
        $scope.buttonActivator();
    }
    
    function removeFileOrFolderFromList(fileName) {
        var index = allFilesAndFolders.indexOf(fileName);
        if (index !== -1) {
            allFilesAndFolders.splice(index, 1);
        }
        $scope.buttonActivator();
    }
    
    $scope.openFile = function(file) {
        console.log('File Manager: openFile called for:', file);
        
        if (file.dirCheck) {
            // Navigate into folder
            var node = { textContent: file.fileName };
            console.log('File Manager: Navigating into folder:', file.fileName);
            
            // Use $timeout to ensure Angular processes this properly
            $timeout(function() {
                $scope.fetchForTableSecondary(node, "doubleClick");
            }, 0);
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
    
    $scope.updatePathSegments = function() {
        var path = $scope.currentPath || $scope.completeStartingPath;
        console.log('File Manager: Updating path segments for:', path);
        
        $scope.pathSegments = [];
        
        if (path && path !== '/') {
            var segments = path.split('/').filter(function(s) { return s; });
            var currentPath = '';
            
            // Skip the first segment if it's 'home' for domain users
            var startIndex = (domainName !== "" && segments[0] === 'home') ? 2 : 0;
            
            for (var i = startIndex; i < segments.length; i++) {
                var segment = segments[i];
                currentPath += '/' + segment;
                $scope.pathSegments.push({
                    name: segment,
                    path: currentPath,
                    isLast: i === segments.length - 1
                });
            }
        }
        
        console.log('File Manager: Path segments:', $scope.pathSegments);
    };
    
    $scope.navigateToPath = function(path) {
        console.log('File Manager: navigateToPath called with:', path);
        $scope.currentPath = path;
        $scope.completeStartingPath = path;
        $scope.fetchForTableSecondary(null, "pathNavigation");
    };
    
    $scope.navigateBack = function() {
        console.log('File Manager: navigateBack called');
        
        var currentPath = domainName === "" ? $scope.currentRPath : $scope.completeStartingPath;
        
        // Don't go back beyond home
        var homePath = domainName === "" ? "/" : "/home/" + domainName;
        if (currentPath === homePath) {
            console.log('File Manager: Already at home directory');
            return;
        }
        
        // Get parent directory
        var lastSlash = currentPath.lastIndexOf('/');
        if (lastSlash > 0) {
            var parentPath = currentPath.substring(0, lastSlash);
            console.log('File Manager: Navigating back to:', parentPath);
            
            if (domainName === "") {
                $scope.currentRPath = parentPath;
            } else {
                $scope.completeStartingPath = parentPath;
            }
            $scope.currentPath = parentPath;
            
            $scope.fetchForTableSecondary(null, "refresh");
        }
    };
    
    $scope.navigateHome = function() {
        if (domainName === "") {
            // Root user mode
            $scope.currentRPath = homeRPathBack;
            $scope.fetchForTableSecondary(null, "startPoint");
        } else {
            // Domain user mode  
            $scope.currentPath = homePathBack;
            $scope.completeStartingPath = homePathBack;
            $scope.fetchForTableSecondary(null, "startPoint");
        }
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
    angular.element($window).on('keydown', $scope.handleKeyDown);
    angular.element($window).on('keyup', $scope.handleKeyUp);
    
    // Tree toggle functionality
    $scope.toggleTreeNode = function(event) {
        event.stopPropagation();
        var element = angular.element(event.currentTarget);
        var parentLi = element.closest('.fm-tree-item');
        var childrenUl = parentLi.find('.fm-tree-children');
        var icon = element.find('.fm-tree-expand');
        
        if (childrenUl.hasClass('expanded')) {
            childrenUl.removeClass('expanded');
            icon.removeClass('fa-chevron-down').addClass('fa-chevron-right');
        } else {
            childrenUl.addClass('expanded');
            icon.removeClass('fa-chevron-right').addClass('fa-chevron-down');
            
            // Load children if not loaded
            if (childrenUl.children().length === 0) {
                var path = parentLi.data('path') || $scope.completeStartingPath;
                $scope.fetchChilds(childrenUl[0], path, "startPoint");
            }
        }
    };
    
    // Sidebar toggle
    $scope.toggleSidebar = function() {
        var sidebar = angular.element('#fmSidebar');
        sidebar.toggleClass('collapsed');
    };
    
    // Drag and drop functionality
    $scope.handleDragStart = function(event, file) {
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', JSON.stringify(file));
        $scope.draggedFile = file;
    };
    
    $scope.handleDragOver = function(event) {
        if (event.preventDefault) {
            event.preventDefault();
        }
        event.dataTransfer.dropEffect = 'move';
        return false;
    };
    
    $scope.handleDrop = function(event, targetFolder) {
        if (event.stopPropagation) {
            event.stopPropagation();
        }
        
        try {
            var file = JSON.parse(event.dataTransfer.getData('text/plain'));
            if (file && targetFolder && file !== targetFolder && targetFolder.dirCheck) {
                // Move file to target folder
                allFilesAndFolders = [file.fileName];
                $scope.newPath = $scope.completeStartingPath + "/" + targetFolder.fileName;
                $scope.startMoving();
            }
        } catch (e) {
            console.error('Drop error:', e);
        }
        
        return false;
    };
    
    // Clean up on destroy
    $scope.$on('$destroy', function() {
        angular.element($window).off('keydown', $scope.handleKeyDown);
        angular.element($window).off('keyup', $scope.handleKeyUp);
        $(document).off("click");
    });
    
    // Initialize ACE editor settings
    $timeout(function() {
        if (typeof ace !== 'undefined' && document.getElementById("htmlEditorContent")) {
            editor = ace.edit("htmlEditorContent");
            editor.setTheme("ace/theme/monokai");
            editor.getSession().setMode("ace/mode/html");
            editor.setOptions({
                fontSize: "14px",
                showPrintMargin: false,
                enableBasicAutocompletion: true,
                enableLiveAutocompletion: true
            });
        }
    }, 1000);
    
    // Prevent form submission
    $('form').submit(function() {
        return false;
    });
    
    // Hide right-click menu on document click
    $(document).click(function() {
        $("#rightClickMenu").hide();
    });
    
    // Initialize
    $scope.buttonActivator();
    $scope.updatePathSegments();
    
    // Initialize view mode
    console.log('File Manager: Initial view mode:', $scope.viewMode);
    
    // Initialize tree structure and load data
    $timeout(function() {
        console.log('File Manager: Initializing with domain:', domainName);
        console.log('File Manager: Starting path:', $scope.completeStartingPath);
        
        // Load initial data first
        $scope.fetchForTableSecondary(null, "startPoint");
        
        // Fetch initial tree for both root and domain users
        var element = document.getElementById("treeRoot");
        if (element) {
            console.log('File Manager: Loading tree structure');
            if (domainName !== "") {
                $scope.fetchChilds(element, $scope.completeStartingPath, "startPoint");
            } else {
                $scope.fetchChilds(element, $scope.currentRPath, "startPoint");
            }
        } else {
            console.warn('File Manager: Tree root element not found');
        }
        
        // Force a view update after everything is loaded
        $timeout(function() {
            console.log('File Manager: Final view update - View mode:', $scope.viewMode, 'Files:', $scope.allFilesAndFolders.length);
        }, 500);
    }, 200);
    
    console.log('New File Manager loaded successfully');
}]);

})(); // Close the IIFE