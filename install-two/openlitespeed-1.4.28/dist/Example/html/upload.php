<!--
/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2015  LiteSpeed Technologies, Inc.                 *
*                                                                            *
*    This program is free software: you can redistribute it and/or modify    *
*    it under the terms of the GNU General Public License as published by    *
*    the Free Software Foundation, either version 3 of the License, or       *
*    (at your option) any later version.                                     *
*                                                                            *
*    This program is distributed in the hope that it will be useful,         *
*    but WITHOUT ANY WARRANTY; without even the implied warranty of          *
*    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the            *
*    GNU General Public License for more details.                            *
*                                                                            *
*    You should have received a copy of the GNU General Public License       *
*    along with this program. If not, see http://www.gnu.org/licenses/.      *
*****************************************************************************/
-->
<html>
<head><style> 
    body { 
        font-family: monospace; 
        font-size: 12px; 
    } 
</style></head>
<body>

<?php
function moveAndShow($src, $dest)
{
    if (empty($src)) {
        echo "<p>file is empty, not stored.</p>\n";
    } else {
        rename($src, $dest);
        echo "<p>Moved: " . $src . " ====> " . $dest . "<br>";
        echo "MD5  : " . md5_file($dest). "<br>";
        echo "Size : " . filesize($dest). " bytes</p>\n"; 
    }
}

function disaplyParsedFile($filekey)
{
    echo "<p>File : " . $filekey . "<br>";
    echo "Name : " . $_POST["{$filekey}_name"] . "<br>";
    echo "Type : " . $_POST["{$filekey}_content-type"] . "<br>";
    echo "Path : " . $_POST["{$filekey}_path"] . "<br>";
    echo "MD5  : " . $_POST["{$filekey}_md5"] . "<br>";
    echo "Size : " . $_POST["{$filekey}_size"] .  " Bytes<br></p>\n";
}

function displayNoParsedFile($filekey)
{
    echo "<p>File : " . $filekey . "<br>";
    echo "Name : " . $_FILES["{$filekey}"]['name'] . "<br>";
    echo "Type : " . $_FILES["{$filekey}"]['type'] . "<br>";
    echo "Path : " . $_FILES["{$filekey}"]['tmp_name'] . "<br>";
    echo "Size : " . $_FILES["{$filekey}"]['size'] . "</p>\n";
}




if(empty($_FILES["file1"])) 
{
    echo "<h1>Request body updated by Parser</h1>\n";

    for ($i = 1; $i <= 2; $i++) {
        disaplyParsedFile("file{$i}");
        $moved_to_path = '/tmp/uploadfile_' . $_POST["file{$i}_name"];
        moveAndShow($_POST["file{$i}_path"], $moved_to_path);
    }

} else {
    echo "<h1>No Parser used</h1>\n";
    for ($i = 1; $i <= 2; $i++) {
        displayNoParsedFile("file{$i}");
        $moved_to_path = '/tmp/uploadfile_' . $_FILES["file{$i}"]["name"];
        moveAndShow($_FILES["file{$i}"]["tmp_name"], $moved_to_path);
    }
}
?>

</body></html>
