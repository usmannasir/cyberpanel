<?php


class fileManager
{

    private $basePath = null;

    public function requestHandler()
    {
        $postdata = file_get_contents("php://input");
        $request = json_decode($postdata);

        $pathToSeed = '/home/' . $request->domainName . '/..filemanagerkey';
        $receivedSeed = $request->domainRandomSeed;

        $myfile = fopen($pathToSeed, "r") or die("Unable to open file!");
        $seed = fread($myfile,filesize($pathToSeed));
        fclose($myfile);

        if ($seed != $receivedSeed){

            $json_data = array(
                "error_message" => "You can not open filemanager for this domain.",
                "copied" => 1,
            );
            $json = json_encode($json_data);
            echo $json;
            return;
        }


        if (isset($request->method)) {

            switch ($request->method) {
                case 'list':
                    $this->listDir($request->completeStartingPath);
                    break;
                case 'listForTable':
                    $home = $this->cleanInput($request->home);
                    $completeStartingPath = $this->cleanInput($request->completeStartingPath);
                    $this->listForTable($home,$completeStartingPath);
                    break;
                case 'readFileContents':
                    $this->readFileContents($request->fileName);
                    break;
                case 'writeFileContents':
                    $this->writeFileContents($request->fileName, $request->fileContent);
                    break;
                case 'createNewFolder':
                    $folderName = $this->cleanInput($request->folderName);
                    $this->createNewFolder($folderName);
                    break;
                case 'createNewFile':
                    $fileName = $this->cleanInput($request->fileName);
                    $this->createNewFile($fileName);
                    break;
                case 'deleteFolderOrFile':
                    $this->deleteFolderOrFile($request->path, $request->fileAndFolders);
                    break;
                case 'compress':
                    $compressedFileName = $this->cleanInput($request->compressedFileName);
                    $this->compress($request->basePath, $request->listOfFiles, $compressedFileName, $request->compressionType);
                    break;
                case 'extract':
                    $extractionLocation = $this->cleanInput($request->extractionLocation);
                    $this->extract($request->home,$request->basePath,$request->fileToExtract,$request->extractionType,$extractionLocation);
                    break;
                case 'move':
                    $this->moveFileAndFolders($request->home,$request->basePath,$request->newPath,$request->fileAndFolders);
                    break;
                case 'copy':
                    $this->copyFileAndFolders($request->home,$request->basePath,$request->newPath,$request->fileAndFolders);
                    break;
                case 'rename':
                    $newFileName = $this->cleanInput($request->newFileName);
                    $this->renameFileOrFolder($request->basePath,$request->existingName,$newFileName);
                    break;
                case 'changePermissions':
                    $this->changePermissions($request->basePath, $request->permissionsPath, $request->newPermissions, $request->recursive);
                    break;
            }
        }
    }

    private function changePermissions($basePath, $permissionsPath, $newPermissions, $recursive)
    {
        try {

            $completePath = $basePath . DIRECTORY_SEPARATOR . $permissionsPath;

            if($recursive == 1){

                $commandToExecute = 'chmod -R ' . $newPermissions . " '". $completePath . "'";
                $programOutput = fopen('temp.txt', 'a');

            }else{
                $commandToExecute = 'chmod ' . $newPermissions . " '". $completePath . "'";
                $programOutput = fopen('temp.txt', 'a');
            }


            exec($commandToExecute, $programOutput);

            $json_data = array(
                "error_message" => "None",
                "permissionsChanged" => 1,
            );
            $json = json_encode($json_data);
            echo $json;

        } catch (Exception $e) {
            $json_data = array(
                "error_message" => $e->getMessage(),
                "permissionsChanged" => 0,
            );
            $json = json_encode($json_data);
            echo $json;
        }

    }

    private function listDir($basePath)
    {
        try {
            $path = "";
            $listPath = $basePath . $path;
            $files = scandir($listPath);
            $json_data = array(
                "error_message" => "None",
                "fetchStatus" => 1
            );
            $counter = 0;

            $tempDir = array();
            $tempFiles = array();

            // sorting files at end

            foreach ($files as $dirFile) {

                $completePath = $basePath . $path . DIRECTORY_SEPARATOR . $dirFile;
                if (is_dir($completePath) == true) {
                    array_push($tempDir, $dirFile);
                } else {
                        array_push($tempFiles, $dirFile);

                }
            }

            $result = array_merge($tempDir, $tempFiles);

            foreach ($result as $dirFile) {
                if ($dirFile == "." or $dirFile == "..") {
                    continue;
                }
                $arrayCounter = 0;
                $tempArray = array($dirFile);
                $arrayCounter += 1;
                $completePath = $basePath . $path . DIRECTORY_SEPARATOR . $dirFile;
                $tempArray[$arrayCounter] = $completePath;
                $arrayCounter += 1;

                if (is_dir($completePath) == true) {
                    $list = true;
                    $tempArray[$arrayCounter] = $list;
                } else {
                    $list = false;
                    $tempArray[$arrayCounter] = $list;
                }

                $json_data[(string)$counter] = $tempArray;
                $counter += 1;

            }

            $json = json_encode($json_data);
            echo $json;
        } catch (Exception $e) {
            $answer = array(
                'uploadStatus' => 0,
                'answer' => [1, 2, 3],
                'error_message' => $e->getMessage(),
            );
            $json = json_encode($answer);
            echo $json;
        }

    }

    private function getPermissions($fileName){

        $perms = fileperms($fileName);

        switch ($perms & 0xF000) {
            case 0xC000: // socket
                $info = 's';
                break;
            case 0xA000: // symbolic link
                $info = 'l';
                break;
            case 0x8000: // regular
                $info = 'r';
                break;
            case 0x6000: // block special
                $info = 'b';
                break;
            case 0x4000: // directory
                $info = 'd';
                break;
            case 0x2000: // character special
                $info = 'c';
                break;
            case 0x1000: // FIFO pipe
                $info = 'p';
                break;
            default: // unknown
                $info = 'u';
        }

        // Owner
        $info .= (($perms & 0x0100) ? 'r' : '-');
        $info .= (($perms & 0x0080) ? 'w' : '-');
        $info .= (($perms & 0x0040) ?
            (($perms & 0x0800) ? 's' : 'x' ) :
            (($perms & 0x0800) ? 'S' : '-'));

        // Group
        $info .= (($perms & 0x0020) ? 'r' : '-');
        $info .= (($perms & 0x0010) ? 'w' : '-');
        $info .= (($perms & 0x0008) ?
            (($perms & 0x0400) ? 's' : 'x' ) :
            (($perms & 0x0400) ? 'S' : '-'));

        // World
        $info .= (($perms & 0x0004) ? 'r' : '-');
        $info .= (($perms & 0x0002) ? 'w' : '-');
        $info .= (($perms & 0x0001) ?
            (($perms & 0x0200) ? 't' : 'x' ) :
            (($perms & 0x0200) ? 'T' : '-'));

        return $info;

    }

    private function listForTable($home,$basePath)
    {
        try {

            $pos = strpos($basePath, $home);

            if ($pos === false) {
                throw new Exception("Not allowed to browse this path, going back home!");
            }

            $path = "";
            $listPath = $basePath . $path;
            $files = scandir($listPath);
            $json_data = array("error_message" => "None",
                "fetchStatus" => 1
            );
            $counter = 0;

            $tempDir = array();
            $tempFiles = array();

            // sorting files at end

            foreach ($files as $dirFile) {

                $completePath = $basePath . $path . DIRECTORY_SEPARATOR . $dirFile;
                if (is_dir($completePath) == true) {
                    array_push($tempDir, $dirFile);
                } else {
                    array_push($tempFiles, $dirFile);
                }
            }

            $result = array_merge($tempDir, $tempFiles);

            foreach ($result as $dirFile) {
                if ($dirFile == "." or $dirFile == "..") {
                    continue;
                }
                $arrayCounter = 0;
                $tempArray = array($dirFile);
                $arrayCounter += 1;
                $completePath = $basePath . $path . DIRECTORY_SEPARATOR . $dirFile;
                $tempArray[$arrayCounter] = $completePath;
                $arrayCounter += 1;

                // find last modified

                $lastModified = date("F d Y H:i:s.", filemtime($completePath));
                $tempArray[$arrayCounter] = $lastModified;
                $arrayCounter += 1;

                // find size of file

                $fileSize = (int)(filesize($completePath) / 1024);
                $tempArray[$arrayCounter] = $fileSize;
                $arrayCounter += 1;

                // find permissions of file


                $tempArray[$arrayCounter] = substr(sprintf('%o', fileperms($completePath)), -4);;
                $arrayCounter += 1;


                // Deciding if the current path is file or dir.

                if (is_dir($completePath) == true) {
                    $list = true;
                    $tempArray[$arrayCounter] = $list;
                } else {
                    $list = false;
                    $tempArray[$arrayCounter] = $list;
                }

                $json_data[(string)$counter] = $tempArray;
                $counter += 1;

            }

            $json = json_encode($json_data);
            echo $json;
        } catch (Exception $e) {
            $answer = array(
                'fetchStatus' => 0,
                'error_message' => $e->getMessage(),
            );
            $json = json_encode($answer);
            echo $json;
        }

    }

    private function readFileContents($pathToFile)
    {

        try {
            $listPath = $pathToFile;
            $contentsofFile = file_get_contents($pathToFile);

            if ($contentsofFile !== false) {
                $json_data = array(
                    "error_message" => "None",
                    "fetchStatus" => 1,
                    "fileContents" => $contentsofFile
                );
                $json = json_encode($json_data);
                echo $json;
            } else {
                throw new Exception("Can not read the file Contents");
            }


        } catch (Exception $e) {
            $json_data = array(
                "error_message" => $e->getMessage(),
                "fetchStatus" => 0,
            );
            $json = json_encode($json_data);
            echo $json;
        }

    }

    private function writeFileContents($pathToFile, $fileContent)
    {

        try {


            $contentsofFile = file_put_contents($pathToFile, $fileContent);

            if ($contentsofFile !== false) {
                $json_data = array(
                    "error_message" => "None",
                    "saveStatus" => 1,
                );
                $json = json_encode($json_data);
                echo $json;
            } else {
                throw new Exception("Can not write the file Contents.");
            }


        } catch (Exception $e) {
            $json_data = array(
                "error_message" => $e->getMessage(),
                "saveStatus" => 0,
            );
            $json = json_encode($json_data);
            echo $json;
        }

    }

    private function createNewFolder($folderName)
    {

        try {


            $returnVal = mkdir($folderName);

            if ($returnVal !== false) {
                $json_data = array(
                    "error_message" => "None",
                    "createStatus" => 1,
                );
                $json = json_encode($json_data);
                echo $json;
            } else {
                throw new Exception("Can not create Folder");
            }


        } catch (Exception $e) {
            $json_data = array(
                "error_message" => $e->getMessage(),
                "createStatus" => 0,
            );
            $json = json_encode($json_data);
            echo $json;
        }

    }

    private function createNewFile($fileName)
    {

        try {


            if (touch($fileName)) {
                $json_data = array(
                    "error_message" => "None",
                    "createStatus" => 1,
                );
                $json = json_encode($json_data);
                echo $json;
            } else {
                throw new Exception("Can not create file!");
            }


        } catch (Exception $e) {
            $json_data = array(
                "error_message" => $e->getMessage(),
                "createStatus" => 0,
            );
            $json = json_encode($json_data);
            echo $json;
        }

    }

    private function deleteFolderOrFile($basePath, $fileAndFolders)
    {
        try {

            foreach ($fileAndFolders as $path) {

                $path = $basePath . DIRECTORY_SEPARATOR . $path;

                if (is_dir($path) == true) {
                    $commandToExecute = 'rm -rf ' . "'".$path ."'";
                    $programOutput = fopen('temp.txt', 'a');
                    exec($commandToExecute, $programOutput);
                } else {
                    if (unlink($path)) {
                        continue;
                    } else {
                        throw new Exception("Can not delete!");
                    }
                }

            }

            $json_data = array(
                "error_message" => "None",
                "deleteStatus" => 1,
            );
            $json = json_encode($json_data);
            echo $json;
        } catch (Exception $e) {
            $json_data = array(
                "error_message" => $e->getMessage(),
                "deleteStatus" => 0,
            );
            $json = json_encode($json_data);
            echo $json;
        }

    }

    private function compress($basePath, $listOfFiles, $compressedFileName, $compressionType)
    {
        try {

            chdir($basePath);

            if ($compressionType == "zip") {

                $compressedFileName = $basePath . DIRECTORY_SEPARATOR . $compressedFileName . ".zip";

                $commandToExecute = 'zip -r ' . $compressedFileName . ' ';

                foreach ($listOfFiles as $file) {
                    $completePathToFile = $file;
                    $commandToExecute = $commandToExecute ."'". $completePathToFile ."'". ' ';
                }

                $programOutput = fopen('temp.txt', 'a');

                exec($commandToExecute, $programOutput);

                $json_data = array(
                    "error_message" => $commandToExecute,
                    "compressed" => 1,
                );
                $json = json_encode($json_data);
                echo $json;
            }
            else {

                $compressedFileName = $basePath . DIRECTORY_SEPARATOR . $compressedFileName . ".tar.gz";

                $commandToExecute = 'tar -czvf ' . $compressedFileName . ' ';

                foreach ($listOfFiles as $file) {
                    $completePathToFile = $file;
                    $commandToExecute = $commandToExecute ."'". $completePathToFile ."'". ' ';
                }

                $programOutput = fopen('temp.txt', 'a');

                exec($commandToExecute, $programOutput);

                $json_data = array(
                    "error_message" => "None",
                    "compressed" => 1,
                );
                $json = json_encode($json_data);
                echo $json;
            }

        } catch (Exception $e) {
            $json_data = array(
                "error_message" => $e->getMessage(),
                "compressed" => 0,
            );
            $json = json_encode($json_data);
            echo $json;
        }
    }

    private function extract($home,$basePath,$completeFileToExtract, $extractionType, $extractionLocation)
    {
        try {

            $pos = strpos($extractionLocation, $home);

            if ($pos === false) {
                throw new Exception("Not allowed to extact in this path, please choose location inside home!");
            }

            if ($extractionType == "zip") {

                $commandToExecute = "unzip -o '" . $completeFileToExtract . "' -d '" . $extractionLocation . "'";

                $programOutput = fopen('temp.txt', 'a');

                exec($commandToExecute, $programOutput);

                $json_data = array(
                    "error_message" => $commandToExecute,
                    "extracted" => 1,
                );
                $json = json_encode($json_data);
                echo $json;
            } else {

                $commandToExecute = "tar xf '" . $completeFileToExtract . "' -C '" . $extractionLocation . "'";

                $programOutput = fopen('temp.txt', 'a');

                exec($commandToExecute, $programOutput);

                $json_data = array(
                    "error_message" => "None",
                    "extracted" => 1,
                );
                $json = json_encode($json_data);
                echo $json;


            }
        }catch (Exception $e) {
            $json_data = array(
                "error_message" => $e->getMessage(),
                "extracted" => 0,
            );
            $json = json_encode($json_data);
            echo $json;
        }
    }

    private function moveFileAndFolders($home,$basePath, $newPath, $fileAndFolders)
    {
        try {

            $pos = strpos($newPath, $home);

            if ($pos === false) {
                throw new Exception("Not allowed to move in this path, please choose location inside home!");
            }

            if(!file_exists($newPath)){
                if(!mkdir($newPath, 0777, true)){
                    $json_data = array(
                        "error_message" => "Can not create the new folder, it already exists!",
                        "moved" => 0,
                    );
                    $json = json_encode($json_data);
                    echo $json;
                    die();
                }
            }

            foreach ($fileAndFolders as $path) {

                $completePathToFile = $basePath . DIRECTORY_SEPARATOR . $path;
                $completeNewPath =  $newPath . DIRECTORY_SEPARATOR . $path;

                $commandToExecute = 'mv ' ."'". $completePathToFile . "'" . ' ' . "'" . $completeNewPath . "'";
                $programOutput = fopen('temp.txt', 'a');
                exec($commandToExecute, $programOutput);
            }

            $json_data = array(
                "error_message" => "None",
                "moved" => 1,
            );
            $json = json_encode($json_data);
            echo $json;

        } catch (Exception $e) {
            $json_data = array(
                "error_message" => $e->getMessage(),
                "moved" => 0,
            );
            $json = json_encode($json_data);
            echo $json;
        }

    }

    private function copyFileAndFolders($home,$basePath, $newPath, $fileAndFolders)
    {
        try {

            $pos = strpos($newPath, $home);

            if ($pos === false) {
                throw new Exception("Not allowed to move in this path, please choose location inside home!");
            }

            if(!file_exists($newPath)){
                if(!mkdir($newPath, 0777, true)){
                    throw new Exception("Can not create the new folder, it already exists!");
                }
            }

            foreach ($fileAndFolders as $path) {

                $completePathToFile = $basePath . DIRECTORY_SEPARATOR . $path;
                $completeNewPath =  $newPath . DIRECTORY_SEPARATOR . $path;

                $commandToExecute = 'cp ' ."'". $completePathToFile . "'" . ' ' . "'" . $completeNewPath . "'";
                $programOutput = fopen('temp.txt', 'a');
                exec($commandToExecute, $programOutput);
            }

            $json_data = array(
                "error_message" => "None",
                "copied" => 1,
            );
            $json = json_encode($json_data);
            echo $json;

        } catch (Exception $e) {
            $json_data = array(
                "error_message" => $e->getMessage(),
                "copied" => 0,
            );
            $json = json_encode($json_data);
            echo $json;
        }

    }

    private function renameFileOrFolder($basePath, $currentName, $newName)
    {
        try {

            $completeOldPath = $basePath . DIRECTORY_SEPARATOR . $currentName;
            $completeNewPath = $basePath . DIRECTORY_SEPARATOR . $newName;

            $commandToExecute = 'mv ' ."'". $completeOldPath . "'" . ' ' . "'" . $completeNewPath . "'";
            $programOutput = fopen('temp.txt', 'a');
            exec($commandToExecute, $programOutput);

            $json_data = array(
                "error_message" => "None",
                "renamed" => 1,
            );
            $json = json_encode($json_data);
            echo $json;

        } catch (Exception $e) {
            $json_data = array(
                "error_message" => $e->getMessage(),
                "renamed" => 0,
            );
            $json = json_encode($json_data);
            echo $json;
        }

    }

    private function cleanInput($input) {
        $search = array(
            '@<script[^>]*?>.*?</script>@si',   // Strip out javascript
            '@<[\/\!]*?[^<>]*?>@si',            // Strip out HTML tags
            '@<style[^>]*?>.*?</style>@siU',    // Strip style tags properly
            '@<![\s\S]*?--[ \t\n\r]*>@'         // Strip multi-line comments
        );
        $output = preg_replace($search, '', $input);
        return $output;
    }
}

$caller = new fileManager();
$caller->requestHandler();