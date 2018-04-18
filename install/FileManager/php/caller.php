<?php

class Caller{

    private $basePath = null;

    public function __construct($basePath = null)
    {
        $this->basePath = $basePath ?: dirname(__DIR__);
    }

    public function requestHandler()
    {
        if ($_SERVER['REQUEST_METHOD'] === 'POST' and isset($_POST['method'])) {

            $pathToSeed = '/home/' . $_POST['domainName'] . '/..filemanagerkey';
            $receivedSeed = $_POST['domainRandomSeed'];

            $myfile = fopen($pathToSeed, "r") or die("Unable to open file!");
            $seed = fread($myfile,filesize($pathToSeed));
            fclose($myfile);

            if ($seed != $receivedSeed){
                $answer = array(
                    'uploadStatus' => 0,
                    'answer' => 'Not allowed to upload in this path.',
                    'error_message' => "None",
                    'fileName' => $_FILES['file']['name']
                );
                $json = json_encode($answer);
                echo $json;
                return;
            }

            switch ($_POST['method']) {
                case 'upload':
                    $this->uploadFile();
                    break;
            }
        }
    }

    private function uploadFile(){
        try {
            if (!empty($_FILES)) {

                if($this->return_bytes(ini_get('upload_max_filesize')) < $_SERVER['CONTENT_LENGTH']){
                    throw new Exception("Size of uploaded file is greater than upload limit!");
                }

                $completePath = $this->cleanInput($_POST['completePath']);
                $fileName = $this->cleanInput($_FILES['file']['name']);
                $homePath = $this->cleanInput($_POST['home']);

                $tempPath = $_FILES['file']['tmp_name'];
                $uploadPath = $completePath . DIRECTORY_SEPARATOR . $fileName;

                $pos = strpos($uploadPath, $homePath);

                if ($pos === false) {
                    throw new Exception("Not allowed to upload in this path!");
                }


                if(move_uploaded_file($tempPath, $uploadPath)==true){
                    $answer = array(
                        'uploadStatus' => 1,
                        'answer' => 'File transfer completed',
                        'error_message' => "None",
                        'fileName' => $_FILES['file']['name']
                    );
                    $json = json_encode($answer);
                    echo $json;
                }
                else{
                    throw new Exception("Can not move uploaded file to destination location!");
                }

            }
            else {
                throw new Exception("No Files to upload!");
            }
        }
        catch(Exception $e) {
            $answer = array(
                'uploadStatus' => 0,
                'answer' => 'No files',
                'error_message' => $e->getMessage(),
                'fileName' => $_FILES['file']['name'],
            );
            $json = json_encode($answer);
            echo $json;
        }

    }

    private function return_bytes($val) {
        $val = trim($val);
        $last = strtolower($val[strlen($val)-1]);
        switch($last) {
            // The 'G' modifier is available since PHP 5.1.0
            case 'g':
                $val *= 1024;
            case 'm':
                $val *= 1024;
            case 'k':
                $val *= 1024;
        }

        return $val;
    }

    private function cleanInput($input) {
        $search = array(
            '@<script[^>]*?>.*?</script>@si',
            '@<[\/\!]*?[^<>]*?>@si',
            '@<style[^>]*?>.*?</style>@siU',
            '@<![\s\S]*?--[ \t\n\r]*>@'
        );
        $output = preg_replace($search, '', $input);
        return $output;
    }

}

$caller = new Caller("/");
$caller->requestHandler();