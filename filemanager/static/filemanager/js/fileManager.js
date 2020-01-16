function getCookie(name) {
    var cookieValue = null;
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

var fileManager = angular.module('fileManager', ['angularFileUpload']);

fileManager.config(['$interpolateProvider', function ($interpolateProvider) {
    $interpolateProvider.startSymbol('{$');
    $interpolateProvider.endSymbol('$}');
}]);


fileManager.controller('fileManagerCtrl', function ($scope, $http, FileUploader, $window) {

    $('form').submit(function (e) {
        e.preventDefault();
    });

    $(document.body).click(function () {
        rightClickNode.style.display = "none";
    });

    var editor = ace.edit("htmlEditorContent");
    var aceEditorMode = '';

    var domainName = $("#domainNameInitial").text();
    var domainRandomSeed = "";

    var homePathBack = "/home/" + domainName;
    $scope.currentPath = "/home/" + domainName;
    $scope.startingPath = domainName;
    $scope.completeStartingPath = "/home/" + domainName;

    $scope.editDisable = true;
    // disable loading image on tree loading
    $scope.treeLoading = true;
    // html editor
    $scope.errorMessageEditor = true;
    $scope.htmlEditorLoading = true;
    $scope.saveSuccess = true;
    var allFilesAndFolders = [];

    $scope.showUploadBox = function () {
        $('#uploadBox').modal('show');
    };

    $scope.showHTMLEditorModal = function () {
        $scope.htmlEditorLoading = false;
        $scope.errorMessageEditor = true;
        $('#showHTMLEditor').modal('show');
        $scope.fileInEditor = allFilesAndFolders[0];
        $scope.getFileContents();

    };


    // tree

    $scope.fetchChilds = function (element, completePath, functionName) {

        // start loading tree
        $scope.treeLoading = false;

        var funcCompletePath = "";
        var nodeForChilds = "";

        if (functionName === "primary") {
            nodeForChilds = element.currentTarget.parentNode;
            funcCompletePath = completePath;
        } else {
            nodeForChilds = element.parentNode;
            funcCompletePath = completePath;
        }
        url = '/filemanager/controller';


        var data = {
            completeStartingPath: completePath,
            method: "list",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            $scope.treeLoading = true;


            if (response.data.status === 1) {

                /// node prepration

                var ulNode = prepareChildNodeUL();
                nodeForChilds.appendChild(ulNode);

                var filesData = response.data;

                var keys = Object.keys(filesData);

                for (var i = 0; i < keys.length; i++) {
                    if (keys[i] === "error_message" | keys[i] === "status") {
                        continue;
                    } else {
                        path = filesData[keys[i]][0];
                        completePath = filesData[keys[i]][1];
                        dropDown = filesData[keys[i]][2];
                        finalPrepration(ulNode, path, completePath, dropDown);
                    }
                }

                activateMinus(nodeForChilds, funcCompletePath);
            } else {
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };

    function finalPrepration(parentNode, path, completePath, dropDown) {
        parentNode.appendChild(prepareChildNodeLI(path, completePath, dropDown));
    }

    function prepareChildNodeLI(path, completePath, dropDown) {

        // text nodes are created
        var spaceNode = document.createTextNode(" ");
        var pathNode = document.createTextNode(" " + path);

        //

        var attachFunc = function () {
            $scope.fetchChilds(aNode, completePath, "secondary");
        };

        var aNode = document.createElement('a');
        aNode.setAttribute('href', '#');
        aNode.addEventListener("click", attachFunc);
        aNode.setAttribute('onclick', 'return false;');

        var secondANode = document.createElement('a');
        secondANode.setAttribute('href', '#');
        secondANode.setAttribute('onclick', 'return false;');

        //

        var iNodePlus = document.createElement('i');
        iNodePlus.setAttribute('class', 'fa fa-plus');
        iNodePlus.setAttribute('aria-hidden', 'true');
        iNodePlus.style.color = "#007bff";

        var iNodeFolder = document.createElement('i');
        iNodeFolder.setAttribute('class', 'fa fa-folder');
        iNodeFolder.setAttribute('aria-hidden', 'true');

        var iNodeFile = document.createElement('i');
        iNodeFile.setAttribute('class', 'fa fa-file');
        iNodeFile.setAttribute('aria-hidden', 'true');
        iNodeFile.style.color = "#007bff";

        //

        var liNode = document.createElement('li');
        liNode.setAttribute('class', 'list-group-item');
        liNode.style.border = "None";

        // node preparation

        if (dropDown == true) {
            secondANode.appendChild(iNodeFolder);
            secondANode.appendChild(pathNode);
            secondANode.addEventListener("click", function () {
                $scope.fetchForTableSecondary(secondANode, "fromTree", completePath);
            });

            // This makes completion of <a href="#"><i class="fa fa-folder" aria-hidden="true"></i> {{ startingPath }} </a>


            aNode.appendChild(spaceNode);
            aNode.appendChild(iNodePlus);
            aNode.appendChild(spaceNode);

            //

            liNode.appendChild(aNode);
            liNode.appendChild(secondANode);

            return liNode;
        } else {
            liNode.appendChild(iNodeFile);
            liNode.appendChild(pathNode);
            return liNode;

        }
    }


    function prepareChildNodeUL() {

        // text nodes are created
        var ulNode = document.createElement('ul');
        ulNode.setAttribute('class', 'list-group list-group-flush');
        return ulNode;
    }

    function activateMinus(node, completePath) {

        var collectionOfA = node.getElementsByTagName("a");

        //

        var aNode = document.createElement('a');
        aNode.setAttribute('href', '#');
        aNode.addEventListener("click", function () {
            deleteChilds(aNode, completePath);
        });
        aNode.setAttribute('onclick', 'return false;');

        //

        var spaceNode = document.createTextNode(" ");

        var iNodeMinus = document.createElement('i');
        iNodeMinus.setAttribute('class', 'fa fa-minus');
        iNodeMinus.setAttribute('aria-hidden', 'true');
        iNodeMinus.style.color = "#007bff";

        // prepare node

        aNode.appendChild(iNodeMinus);
        aNode.appendChild(spaceNode);

        node.insertBefore(aNode, collectionOfA[1]);
        node.removeChild(collectionOfA[0]);

    }

    function deleteChilds(aNode, completePath) {

        parent = aNode.parentNode;

        var collectionOfUL = parent.getElementsByTagName("ul");
        parent.removeChild(collectionOfUL[0]);


        var collectionOfA = parent.getElementsByTagName("a");

        //

        var newANode = document.createElement('a');
        newANode.setAttribute('href', '#');
        newANode.addEventListener("click", function () {
            $scope.fetchChilds(newANode, completePath, "secondary");
        });
        newANode.setAttribute('onclick', 'return false;');

        //

        var spaceNode = document.createTextNode(" ");

        var iNodePlus = document.createElement('i');
        iNodePlus.setAttribute('class', 'fa fa-plus');
        iNodePlus.setAttribute('aria-hidden', 'true');
        iNodePlus.style.color = "#007bff";

        // prepare node

        newANode.appendChild(iNodePlus);
        newANode.appendChild(spaceNode);

        parent.insertBefore(newANode, collectionOfA[1]);
        parent.removeChild(collectionOfA[0]);


    }

    // tree ends


    $scope.selectAll = function () {

        var tableBody = document.getElementById("tableBodyFiles");
        var getFileName = tableBody.firstChild.firstChild.innerHTML;
        allFilesAndFolders = []

        var collectionOfA = tableBody.getElementsByTagName("tr");

        for (var i = 0; i < collectionOfA.length; i++) {
            collectionOfA[i].style.background = "aliceblue";
            var getFileName = collectionOfA[i].getElementsByTagName('td')[0].innerHTML;
            allFilesAndFolders.push(getFileName);
        }

        $scope.buttonActivator();

    };
    $scope.unSelectAll = function () {

        var tableBody = document.getElementById("tableBodyFiles");
        var getFileName = tableBody.firstChild.firstChild.innerHTML;
        allFilesAndFolders = [];

        var collectionOfA = tableBody.getElementsByTagName("tr");

        for (var i = 0; i < collectionOfA.length; i++) {
            collectionOfA[i].style.background = "None";
        }

        $scope.buttonActivator();
    };

    function addFileOrFolderToList(nodeName) {

        var rightClickNode = document.getElementById("rightClick")

        var check = 1;
        var getFileName = nodeName.getElementsByTagName('td')[0].innerHTML;

        if (nodeName.style.backgroundColor == "aliceblue") {

            var tempArray = [];
            nodeName.style.background = "None";

            for (var j = 0; j < allFilesAndFolders.length; j++) {
                if (allFilesAndFolders[j] != getFileName) {
                    tempArray.push(allFilesAndFolders[j]);
                }
            }
            allFilesAndFolders = tempArray;
            // activating deactivating functions
            $scope.buttonActivator();
            return;
        }

        nodeName.style.background = "aliceblue";


        for (var j = 0; j < allFilesAndFolders.length; j++) {
            if (allFilesAndFolders[j] === getFileName) {
                check = 0;
                break;
            }
        }
        if (check === 1) {
            allFilesAndFolders.push(getFileName);
        }

        // activating deactivating functions
        $scope.buttonActivator();


    }

    /*

     <tr>
     <th scope="row"><i class="fa fa-folder" aria-hidden="true"></i></th>
     <td>public_html</td>
     <td>26KB</td>
     <td>26 Oct</td>
     <td>775</td>
     <td>Folder/File</td>
     </tr>

     */

    function createTR(fileName, fileSize, lastModified, permissions, dirCheck) {

        // text nodes are created
        var fileNameNode = document.createTextNode(fileName);
        var fileSizeNode = document.createTextNode(fileSize);
        var lastModifiedNode = document.createTextNode(lastModified);
        var permissionsNode = document.createTextNode(permissions);


        //


        var iNodeFolder = document.createElement('i');
        iNodeFolder.setAttribute('class', 'fa fa-folder');
        iNodeFolder.setAttribute('aria-hidden', 'true');
        iNodeFolder.style.color = "#007bff";

        var iNodeFile = document.createElement('i');
        iNodeFile.setAttribute('class', 'fa fa-file');
        iNodeFile.setAttribute('aria-hidden', 'true');
        iNodeFile.style.color = "#007bff";

        //

        var firstTDNode = document.createElement('td');
        var secondTDNode = document.createElement('td');
        var thirdTDNode = document.createElement('td');
        var forthTDNode = document.createElement('td');
        var fifthTDNode = document.createElement('td');

        fifthTDNode.style.display = "none";

        //


        var thNode = document.createElement('th');
        thNode.setAttribute('scope', 'row');

        //

        var trNode = document.createElement('tr');

        // node preparation

        firstTDNode.appendChild(fileNameNode);
        secondTDNode.appendChild(fileSizeNode);
        thirdTDNode.appendChild(lastModifiedNode);
        forthTDNode.appendChild(permissionsNode);

        if (dirCheck == true) {
            thNode.appendChild(iNodeFolder);
            trNode.appendChild(thNode);
            trNode.addEventListener("dblclick", function () {
                $scope.fetchForTableSecondary(firstTDNode, "doubleClick");
            });
            trNode.addEventListener("click", function () {
                addFileOrFolderToList(trNode);
            });
            trNode.addEventListener("contextmenu", function (event) {
                $scope.rightClickCallBack(event, trNode);
            });

            // Hidden td to represent file or folder

            var fileOrFolderNode = document.createTextNode("Folder");
            fifthTDNode.appendChild(fileOrFolderNode)
        } else {
            thNode.appendChild(iNodeFile);
            trNode.appendChild(thNode);
            trNode.addEventListener("click", function () {
                addFileOrFolderToList(trNode);
            });
            trNode.addEventListener("contextmenu", function (event) {
                $scope.rightClickCallBack(event, trNode);
            });

            // Hidden td to represent file or folder

            var fileOrFolderNode = document.createTextNode("File");
            fifthTDNode.appendChild(fileOrFolderNode)
        }

        trNode.appendChild(firstTDNode);
        trNode.appendChild(secondTDNode);
        trNode.appendChild(thirdTDNode);
        trNode.appendChild(forthTDNode);
        trNode.appendChild(fifthTDNode);

        return trNode;

    }


    // Button Activator

    $scope.buttonActivator = function () {

        // for edit button
        if (allFilesAndFolders.length === 1) {
            var editNode = document.getElementById("editFile");
            editNode.style.pointerEvents = "auto";

            var editNotRight = document.getElementById("editOnRight");

            var result = findFileExtension(allFilesAndFolders[0]);

            if (result !== undefined) {
                if (result[0] === "js") {
                    aceEditorMode = "ace/mode/javascript";
                    editNotRight.style.display = "Block";
                } else if (result[0] === "html") {
                    aceEditorMode = "ace/mode/html";
                    editNotRight.style.display = "Block";
                } else if (result[0] === "css") {
                    aceEditorMode = "ace/mode/css";
                    editNotRight.style.display = "Block";
                } else if (result[0] === "php") {
                    aceEditorMode = "ace/mode/php";
                    editNotRight.style.display = "Block";
                } else if (result[0] === "txt") {
                    aceEditorMode = "";
                    editNotRight.style.display = "Block";
                } else if (result[0] === "htaccess") {
                    aceEditorMode = "";
                    editNotRight.style.display = "Block";
                } else {
                    var editNode = document.getElementById("editFile");
                    editNode.style.pointerEvents = "none";
                    editNotRight.style.display = "None";
                }
            } else {
                var editNode = document.getElementById("editFile");
                editNode.style.pointerEvents = "none";
                editNotRight.style.display = "None";
            }
        } else {
            var editNode = document.getElementById("editFile");
            editNode.style.pointerEvents = "none";
        }

        // extraction button

        if (allFilesAndFolders.length === 1) {
            var extractFileNode = document.getElementById("extractFile");
            extractFileNode.style.pointerEvents = "auto";

            var extractNodeRight = document.getElementById("extractOnRight");

            var result = findFileExtension(allFilesAndFolders[0]);

            if (result !== undefined) {
                if (result[0] === "gz") {
                    extractFileNode.style.pointerEvents = "auto";
                    extractNodeRight.style.display = "Block";
                } else if (result[0] === "zip") {
                    extractFileNode.style.pointerEvents = "auto";
                    extractNodeRight.style.display = "Block";
                } else {
                    extractFileNode.style.pointerEvents = "none";
                    extractNodeRight.style.display = "None";
                }
            } else {
                extractFileNode.style.pointerEvents = "none";
                extractNodeRight.style.display = "None";
            }
        } else {
            var extractFileNode = document.getElementById("extractFile");
            extractFileNode.style.pointerEvents = "none";
        }


        // move button

        if (allFilesAndFolders.length >= 1) {

            var moveFileNode = document.getElementById("moveFile");
            moveFileNode.style.pointerEvents = "auto";
        } else {
            var moveFileNode = document.getElementById("moveFile");
            moveFileNode.style.pointerEvents = "none";
        }

        //copy button

        if (allFilesAndFolders.length >= 1) {

            var copeFileNode = document.getElementById("copyFile");
            copeFileNode.style.pointerEvents = "auto";
        } else {
            var copeFileNode = document.getElementById("copyFile");
            copeFileNode.style.pointerEvents = "none";
        }


        // rename button

        if (allFilesAndFolders.length === 1) {

            var renameFileNode = document.getElementById("renameFile");
            renameFileNode.style.pointerEvents = "auto";
        } else {
            var renameFileNode = document.getElementById("renameFile");
            renameFileNode.style.pointerEvents = "none";
        }


        // compress button

        if (allFilesAndFolders.length >= 1) {
            var compressFile = document.getElementById("compressFile");
            compressFile.style.pointerEvents = "auto";
        } else {
            var compressFile = document.getElementById("compressFile");
            compressFile.style.pointerEvents = "none";
        }


        // move button

        if (allFilesAndFolders.length >= 1) {

            var deleteFile = document.getElementById("deleteFile");
            deleteFile.style.pointerEvents = "auto";
        } else {
            var deleteFile = document.getElementById("deleteFile");
            deleteFile.style.pointerEvents = "none";
        }


    };
    $scope.buttonActivator();

    // table functions


    $scope.fetchForTableSecondary = function (node, functionName) {

        allFilesAndFolders = [];
        $scope.buttonActivator();
        url = "/filemanager/controller";
        var completePathToFile = "";

        if (functionName === "startPoint") {
            completePathToFile = $scope.currentPath;
        } else if (functionName === "doubleClick") {
            completePathToFile = $scope.currentPath + "/" + node.innerHTML;
        } else if (functionName === "homeFetch") {
            completePathToFile = homePathBack;
        } else if (functionName === "goBackOnPath") {
            var pos = $scope.currentPath.lastIndexOf("/");
            completePathToFile = $scope.currentPath.slice(0, pos);
        } else if (functionName === "refresh") {
            completePathToFile = $scope.currentPath;
            var rightClickNode = document.getElementById("rightClick");
        } else if (functionName === "fromTree") {
            completePathToFile = arguments[2];
        }

        $scope.currentPath = completePathToFile;

        var data = {
            completeStartingPath: completePathToFile,
            method: "listForTable",
            home: homePathBack,
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };

        var tableBody = document.getElementById("tableBodyFiles");
        var loadingPath = "/static/filemanager/images/loading.gif";
        tableBody.innerHTML = '<img src="' + loadingPath + '">';


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            tableBody.innerHTML = '';


            if (response.data.status === 1) {


                /// node prepration

                var filesData = response.data;

                var keys = Object.keys(filesData);

                for (var i = 0; i < keys.length; i++) {
                    if (keys[i] === "error_message" | keys[i] === "status") {
                        continue;
                    } else {
                        var fileName = filesData[keys[i]][0];
                        var lastModified = filesData[keys[i]][2];
                        var fileSize = filesData[keys[i]][3];
                        var permissions = filesData[keys[i]][4];
                        var dirCheck = filesData[keys[i]][5];
                        console.log(fileName);
                        if (fileName === "..filemanagerkey") {

                            continue;
                        }
                        tableBody.appendChild(createTR(fileName, fileSize, lastModified, permissions, dirCheck));

                    }
                }
            } else {
                var notification = alertify.notify(response.data.error_message, 'error', 10, function () {
                });
                $scope.fetchForTableSecondary(null, 'homeFetch');
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };

    function findFileExtension(fileName) {
        return (/[.]/.exec(fileName)) ? /[^.]+$/.exec(fileName) : undefined;
    }

    $scope.fetchForTableSecondary(null, "startPoint");

    // html editor

    $scope.getFileContents = function () {

        var completePathForFile = $scope.currentPath + "/" + allFilesAndFolders[0];


        var data = {
            fileName: completePathForFile,
            method: "readFileContents",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };

        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);


        function ListInitialDatas(response) {

            $scope.htmlEditorLoading = true;

            if (response.data.status === 1) {

                var editor = ace.edit("htmlEditorContent");
                editor.setTheme("ace/theme/chrome");
                editor.getSession().setMode(aceEditorMode);
                editor.setValue(response.data.fileContents);

            } else {
                $scope.errorMessageEditor = false;
                $scope.error_message = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };

    $scope.putFileContents = function () {

        $scope.htmlEditorLoading = false;
        $scope.saveSuccess = true;
        $scope.errorMessageEditor = true;

        var completePathForFile = $scope.currentPath + "/" + allFilesAndFolders[0];

        var data = {
            fileName: completePathForFile,
            method: "writeFileContents",
            fileContent: editor.getValue(),
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            $scope.htmlEditorLoading = true;

            if (response.data.status === 1) {
                $scope.htmlEditorLoading = true;
                $scope.saveSuccess = false;
            } else {
                $scope.errorMessageEditor = false;
                $scope.error_message = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };


    // uploads

    $scope.errorMessage = true;

    var uploader = $scope.uploader = new FileUploader({
        url: "/filemanager/upload",
        headers: {
            'X-CSRFToken': getCookie('csrftoken') // X-CSRF-TOKEN is used for Ruby on Rails Tokens
        },
        formData: [{
            "method": "upload",
            "home": homePathBack
        }]
    });

    uploader.onCompleteItem = function (fileItem, response, status, headers) {
        if (response.uploadStatus === 1) {
            $scope.errorMessage = true;
            $scope.fetchForTableSecondary(null, 'refresh');
        } else {
            $scope.errorMessage = false;
            $scope.fileName = response.fileName;
            $scope.error_message = response.error_message;
        }
    };

    uploader.onAfterAddingFile = function (fileItem) {
        $scope.errorMessage = true;
        fileItem.formData.push(
            {
                "completePath": $scope.currentPath,
                domainRandomSeed: domainRandomSeed,
                domainName: domainName

            });
    };

    // folder functions

    $scope.createSuccess = true;
    $scope.errorMessageFolder = true;

    //
    $scope.showCreateFolderModal = function () {
        $scope.createSuccess = true;
        $scope.errorMessageFolder = true;
        $scope.newFolderName = "";
        $('#showCreateFolder').modal('show');
    };

    $scope.createFolderEnter = function ($event) {
        var keyCode = $event.which || $event.keyCode;
        if (keyCode === 13) {
            $scope.htmlEditorLoading = false;
            $scope.createNewFolder();
        }
    };

    $scope.createNewFolder = function () {

        $scope.errorMessageFolder = true;

        var completePathForFolder = $scope.currentPath + "/" + $scope.newFolderName;

        if ($scope.newFolderName.length === 0) {
            $scope.errorMessageFolder = false;
            $scope.error_message = "Please enter folder name!";
            return;
        }


        var data = {
            folderName: completePathForFolder,
            method: "createNewFolder",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };

        var url = '/filemanager/controller';
        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                $scope.createSuccess = false;
                $scope.fetchForTableSecondary(null, 'refresh');
                $('#showCreateFolder').modal('hide');
            } else {
                $scope.errorMessageFolder = false;
                $scope.error_message = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };

    //

    $scope.createSuccess = true;
    $scope.errorMessageFile = true;

    $scope.showCreateFileModal = function () {
        $scope.createSuccess = true;
        $scope.errorMessageFile = true;
        $scope.newFileName = "";
        $('#showCreateFile').modal('show');
    };

    $scope.createFileEnter = function ($event) {
        var keyCode = $event.which || $event.keyCode;
        if (keyCode === 13) {
            $scope.htmlEditorLoading = false;
            $scope.createNewFile();
        }

    };

    $scope.createNewFile = function () {

        var completePathForFile = $scope.currentPath + "/" + $scope.newFileName;
        $scope.errorMessageFile = true;

        if ($scope.newFileName.length === 0) {
            $scope.errorMessageFile = false;
            $scope.error_message = "Please enter file name!";
            return;
        }

        var data = {
            fileName: completePathForFile,
            method: "createNewFile",
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            if (response.data.status === 1) {
                $scope.createSuccess = false;
                $scope.fetchForTableSecondary(null, 'refresh');
                $('#showCreateFile').modal('hide');
            } else {
                $scope.errorMessageFile = false;
                $scope.error_message = response.data.error_message;
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };

    $scope.createSuccess = true;
    $scope.errorMessageFile = true;

    //

    $scope.deleteLoading = true;

    $scope.showDeleteModal = function () {
        $('#showDelete').modal('show');
    };

    $scope.deleteFolderOrFile = function () {

        $scope.deleteLoading = false;

        var data = {
            path: $scope.currentPath,
            method: "deleteFolderOrFile",
            fileAndFolders: allFilesAndFolders,
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.deleteLoading = true;
            if (response.data.status === 1) {
                $('#showDelete').modal('hide');
                var notification = alertify.notify('Successfully Deleted!', 'success', 5, function () {
                });
                $scope.fetchForTableSecondary(null, 'refresh');
            } else {
                var notification = alertify.notify('Files/Folders can not be deleted', 'error', 5, function () {
                    console.log('dismissed');
                });
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };


    // Compression

    $scope.compressionLoading = true;

    $scope.showCompressionModal = function () {
        $('#showCompression').modal('show');

        $scope.listOfFiles = "";
        $scope.compressedFileName = "";

        for (var i = 0; i < allFilesAndFolders.length; i++) {
            $scope.listOfFiles = $scope.listOfFiles + allFilesAndFolders[i] + "\n";
        }
    };

    $scope.startCompression = function () {

        $scope.compressionLoading = false;

        var data = {
            home: homePathBack,
            basePath: $scope.currentPath,
            listOfFiles: allFilesAndFolders,
            compressedFileName: $scope.compressedFileName,
            compressionType: $scope.compressionType,
            method: 'compress',
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            $scope.compressionLoading = true;
            $('#showCompression').modal('hide');
            if (response.data.status === 1) {
                var notification = alertify.notify('Successfully Compressed!', 'success', 5, function () {
                });
                $scope.fetchForTableSecondary(null, 'refresh');
            } else {
                var notification = alertify.notify(response.data.error_message, 'error', 5, function () {
                });
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };

    // extraction

    $scope.extractionLoading = true;

    $scope.showExtractionModal = function () {
        $scope.extractionLocation = $scope.currentPath;
        $('#showExtraction').modal('show');
        $scope.fileToBeExtracted = allFilesAndFolders[0];
    };

    $scope.startExtraction = function () {

        $scope.extractionLoading = false;

        var basePath = $scope.currentPath;
        var completeFileToExtract = $scope.currentPath + "/" + allFilesAndFolders[0];
        var extractionType = "";

        if (findFileExtension(completeFileToExtract) == "gz") {
            extractionType = "tar.gz";
        } else {
            extractionType = "zip";
        }

        var data = {
            home: homePathBack,
            basePath: basePath,
            fileToExtract: completeFileToExtract,
            extractionType: extractionType,
            extractionLocation: $scope.extractionLocation,
            method: 'extract',
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            $scope.extractionLoading = true;
            $('#showExtraction').modal('hide');

            if (response.data.status === 1) {
                var notification = alertify.notify('Successfully Extracted!', 'success', 5, function () {
                    console.log('dismissed');
                });
                $scope.fetchForTableSecondary(null, 'refresh');
            } else {
                var notification = alertify.notify(response.data.error_message, 'error', 10, function () {
                    console.log('dismissed');
                });
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };


    /// move

    $scope.moveLoading = true;

    $scope.showMoveModal = function () {
        $('#showMove').modal('show');
        $scope.pathToMoveTo = $scope.currentPath;

        $scope.listOfFiles = "";

        for (var i = 0; i < allFilesAndFolders.length; i++) {
            $scope.listOfFiles = $scope.listOfFiles + allFilesAndFolders[i] + "\n";
        }

    }


    $scope.startMoving = function () {

        $scope.moveLoading = false;

        var data = {
            home: homePathBack,
            basePath: $scope.currentPath,
            newPath: $scope.pathToMoveTo,
            fileAndFolders: allFilesAndFolders,
            method: 'move',
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            $scope.moveLoading = true;
            $('#showMove').modal('hide');

            if (response.data.status === 1) {
                var notification = alertify.notify('Successfully Moved!', 'success', 5, function () {
                });
                $scope.fetchForTableSecondary(null, 'refresh');
            } else {
                var notification = alertify.notify(response.data.error_message, 'error', 5, function () {
                });
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };

    /// copy

    $scope.copyLoading = true;

    $scope.showCopyModal = function () {
        $('#showCopy').modal('show');
        $scope.pathToCopyTo = $scope.currentPath;

        $scope.listOfFiles = "";

        for (var i = 0; i < allFilesAndFolders.length; i++) {
            $scope.listOfFiles = $scope.listOfFiles + allFilesAndFolders[i] + "\n";
        }

    };


    $scope.startCopying = function () {

        $scope.copyLoading = false;

        var data = {
            home: homePathBack,
            basePath: $scope.currentPath,
            newPath: $scope.pathToCopyTo,
            fileAndFolders: allFilesAndFolders,
            method: 'copy',
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {
            $scope.copyLoading = true;

            $('#showCopy').modal('hide');

            if (response.data.status === 1) {
                var notification = alertify.notify('Successfully Copied!', 'success', 5, function () {
                });
                $scope.fetchForTableSecondary(null, 'refresh');
            } else {
                var notification = alertify.notify(response.data.error_message, 'error', 5, function () {
                });
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };

    // right click settings

    var rightClickNode = document.getElementById("rightClick");
    rightClickNode.style.display = "none";

    $scope.rightClickCallBack = function (event, trNode) {
        var rightClickNode = document.getElementById("rightClick")
        rightClickNode.style.display = "block";

        event.preventDefault();
        $scope.unSelectAll();

        $('#rightClick').css({
            'top': event.pageY,
            'left': event.pageX
        });

        // If we want to enable download for this node

        var downloadOnRight = document.getElementById("downloadOnRight");

        if (trNode.lastChild.innerHTML === "File") {
            downloadOnRight.style.display = "Block";
        } else {
            downloadOnRight.style.display = "none";
        }


        $scope.addFileOrFolderToListForRightClick(trNode);
    };

    $scope.addFileOrFolderToListForRightClick = function (nodeName) {

        var check = 1;
        var getFileName = nodeName.getElementsByTagName('td')[0].innerHTML;

        if (nodeName.style.backgroundColor === "aliceblue") {

            var tempArray = [];
            nodeName.style.background = "None";

            for (var j = 0; j < allFilesAndFolders.length; j++) {
                if (allFilesAndFolders[j] != getFileName) {
                    tempArray.push(allFilesAndFolders[j]);
                }
            }
            allFilesAndFolders = tempArray;
            // activating deactivating functions
            $scope.buttonActivator();
            return;
        }

        nodeName.style.background = "aliceblue";


        for (var j = 0; j < allFilesAndFolders.length; j++) {
            if (allFilesAndFolders[j] === getFileName) {
                check = 0;
                break;
            }
        }
        if (check === 1) {
            allFilesAndFolders.push(getFileName);
        }

        // activating deactivating functions
        $scope.buttonActivator();


    };

    // rename


    $scope.renameLoading = true;

    $scope.showRenameModal = function () {
        $('#showRename').modal('show');
        $scope.fileToRename = allFilesAndFolders[0];
        $scope.newFileName = "";
    };

    $scope.renameEnter = function ($event) {
        var keyCode = $event.which || $event.keyCode;
        if (keyCode === 13) {
            $scope.htmlEditorLoading = false;
            $scope.renameFile();
        }
    };


    $scope.renameFile = function () {

        $scope.renameLoading = false;

        var data = {
            basePath: $scope.currentPath,
            existingName: $scope.fileToRename,
            newFileName: $scope.newFileName,
            method: 'rename',
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            $scope.moveLoading = true;
            $('#showRename').modal('hide');
            $scope.renameLoading = true;

            if (response.data.status === 1) {
                var notification = alertify.notify('Successfully Renamed!', 'success', 5, function () {
                });
                $scope.fetchForTableSecondary(null, 'refresh');
            } else {
                var notification = alertify.notify(response.data.error_message, 'error', 5, function () {
                });
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };


    // Fix permissions

    $scope.fixPermissions = function () {

        url = "/filemanager/changePermissions";


        var data = {
            domainName: domainName,
            domainRandomSeed: domainRandomSeed,
            domainName: domainName
        };


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {


            if (response.data.permissionsChanged === 1) {
                var notification = alertify.notify('Permissions successfully fixed!', 'success', 5, function () {
                    console.log('dismissed');
                });
                $scope.fetchForTableSecondary(null, 'refresh');
            } else {
                var notification = alertify.notify(response.data.error_message, 'error', 5, function () {
                    console.log('dismissed');
                });
                $scope.fetchForTableSecondary(null, 'refresh');
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };

    // Download files

    $scope.downloadFile = function () {

        url = "/filemanager/downloadFile";
        var downloadURL = $scope.currentPath + "/" + allFilesAndFolders[0];
        window.location.href = url + '?domainName=' + domainName + '&fileToDownload=' + downloadURL;
    };


    // Change permissions

    $scope.changePermissionsLoading = true;

    $scope.userPermissions = 0;
    $scope.groupPermissions = 0;
    $scope.wordlPermissions = 0;


    $scope.showPermissionsModal = function () {
        $('#showPermissions').modal('show');
        $scope.permissionsPath = allFilesAndFolders[0];
    };


    $scope.updateReadPermissions = function (value) {

        switch (value) {

            case 'userRead':

                if ($scope.userRead === true) {
                    $scope.userPermissions = $scope.userPermissions + 4;
                } else {
                    if ($scope.userRead !== undefined) {
                        $scope.userPermissions = $scope.userPermissions - 4;
                    }
                }
                break;


            case  'groupRead':
                if ($scope.groupRead === true) {
                    $scope.groupPermissions = $scope.groupPermissions + 4;
                } else {
                    if ($scope.groupRead !== undefined) {
                        $scope.groupPermissions = $scope.groupPermissions - 4;
                    }
                }
                break;


            case 'worldRead':
                if ($scope.worldRead === true) {
                    $scope.wordlPermissions = $scope.wordlPermissions + 4;
                } else {
                    if ($scope.worldRead !== undefined) {
                        $scope.wordlPermissions = $scope.wordlPermissions - 4;
                    }
                }
                break;
        }
    };

    $scope.updateWritePermissions = function (value) {

        switch (value) {

            case 'userWrite':

                if ($scope.userWrite === true) {
                    $scope.userPermissions = $scope.userPermissions + 2;
                } else {
                    if ($scope.userWrite !== undefined) {
                        $scope.userPermissions = $scope.userPermissions - 2;
                    }
                }
                break;


            case  'groupWrite':
                if ($scope.groupWrite === true) {
                    $scope.groupPermissions = $scope.groupPermissions + 2;
                } else {
                    if ($scope.groupWrite !== undefined) {
                        $scope.groupPermissions = $scope.groupPermissions - 2;
                    }
                }
                break;


            case 'worldWrite':
                if ($scope.worldWrite === true) {
                    $scope.wordlPermissions = $scope.wordlPermissions + 2;
                } else {
                    if ($scope.worldWrite !== undefined) {
                        $scope.wordlPermissions = $scope.wordlPermissions - 2;
                    }
                }
                break;
        }
    };

    $scope.updateExecutePermissions = function (value) {

        switch (value) {

            case 'userExecute':

                if ($scope.userExecute === true) {
                    $scope.userPermissions = $scope.userPermissions + 1;
                } else {
                    if ($scope.userExecute !== undefined) {
                        $scope.userPermissions = $scope.userPermissions - 1;
                    }
                }
                break;


            case  'groupExecute':
                if ($scope.groupExecute === true) {
                    $scope.groupPermissions = $scope.groupPermissions + 1;
                } else {
                    if ($scope.groupExecute !== undefined) {
                        $scope.groupPermissions = $scope.groupPermissions - 1;
                    }
                }
                break;


            case 'worldExecute':
                if ($scope.worldExecute === true) {
                    $scope.wordlPermissions = $scope.wordlPermissions + 1;
                } else {
                    if ($scope.worldExecute !== undefined) {
                        $scope.wordlPermissions = $scope.wordlPermissions - 1;
                    }
                }
                break;
        }
    };


    $scope.changePermissionsRecursively = function () {
        $scope.changePermissions(1);
    };


    $scope.changePermissions = function (recursive) {

        $scope.changePermissionsLoading = false;
        var newPermissions = String($scope.userPermissions) + String($scope.groupPermissions) + String($scope.wordlPermissions);

        var data = {
            basePath: $scope.currentPath,
            permissionsPath: $scope.permissionsPath,
            method: 'changePermissions',
            domainRandomSeed: domainRandomSeed,
            recursive: recursive,
            newPermissions: newPermissions,
            domainName: domainName
        };


        var config = {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        };


        $http.post(url, data, config).then(ListInitialDatas, cantLoadInitialDatas);

        function ListInitialDatas(response) {

            $scope.changePermissionsLoading = true;
            $('#showPermissions').modal('hide');

            if (response.data.status === 1) {
                var notification = alertify.notify('Permissions Successfully Changed!', 'success', 5, function () {
                });
                $scope.fetchForTableSecondary(null, 'refresh');
            } else {
                var notification = alertify.notify(response.data.error_message, 'error', 5, function () {
                });
            }

        }

        function cantLoadInitialDatas(response) {
        }

    };


});