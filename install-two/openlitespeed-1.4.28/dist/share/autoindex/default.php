<?php


// To customize look & feel of generated index page
class UserSettings
{
    var $HeaderName = 'HEADER';
    var $ReadmeName = 'README';

    var $Exclude_Patterns =
        array(  ".",
                "..",
                ".??*",
                "*~",
                "*#",
                "HEADER*",
                "README*",
                "RCS",
                "CVS",
                "*,v",
                "*,t",
                "*.lsz"
                );

    var $Time_Format = " d-M-Y H:i ";
    var $IconPath = "/_autoindex/icons";
    var $nameWidth = 80;
    var $nameFormat;

    function UserSettings()
    {
        $this->nameFormat = '%-' . ($this->nameWidth + 4) . '.' . ($this->nameWidth + 4) .'s';
    }
}

class IMG_Mapping
{
    var $suffixes;
    var $imageName;
    var $desc;
    var $alt;
    function IMG_Mapping( $arrSuffix, $imgName, $altName, $descr )
    {
        $this->suffixes = $arrSuffix;
        $this->imageName = $imgName;
        $this->alt = $altName;
        $this->desc = $descr;
    }
    function found($ext)
    {
        return in_array($ext, $this->suffixes);
    }
}

class AllImgs
{
    var $mapping, $default_img, $dir_img;

    function AllImgs()
    {
        $this->mapping = array(
            new IMG_Mapping( array( 'gif', 'png', 'jpg', 'jpeg', 'tif', 'tiff', 'bmp', 'svg', 'raw'),
                             'image.png', '[IMG]', '' ),
            new IMG_Mapping( array( 'html', 'htm', 'shtml', 'php', 'phtml',
                                    'css', 'js' ),
                             'html.png',  '[HTM]', '' ),
            new IMG_Mapping( array( 'txt', 'md5', 'c', 'cpp', 'cc', 'h', 'sh' ),
                             'text.png',  '[TXT]', '' ),
            new IMG_Mapping( array( 'gz', 'tgz', 'zip', 'Z', 'z'),
                             'compress.png', '[CMP]', '' ),
            new IMG_Mapping( array( 'bin', 'exe' ),
                             'binary.png','[BIN]', '' ),
            new IMG_Mapping( array( 'mpg', 'avi', 'mpeg', 'ram', 'wmv' ),
                             'movie.png','[VID]', '' ),
            new IMG_Mapping( array( 'mp3', 'mp2', 'ogg', 'wav', 'wma',
                                    'aac', 'mp4', 'rm'),
                             'sound.png', '[SND]', '' )

            );

        $this->default_img = new IMG_Mapping( NULL, 'unknown.png', 'unknown', '' );
        $this->dir_img = new IMG_Mapping( NULL, 'folder.png', 'directory', '' );
        $this->parent_img = new IMG_Mapping( NULL, 'up.png', 'up', '' );
    }

    function findImgMapping($file)
    {
        $found = NULL;
        $pos = strrpos( $file, '.' );
        if ( $pos !== FALSE )
        {
            $ext = substr($file, $pos+1);
            if ( $ext !== FALSE )
            {
                $l = count($this->mapping);
                for ( $i = 0 ; $i < $l ; ++$i )
                {
                    if ( in_array($ext, $this->mapping[$i]->suffixes) )
                    {
                        $found = $this->mapping[$i];
                        break;
                    }
                }
            }
        }
        if ( !isset($found) )
            $found = $this->default_img;
        return $found;
    }
}

// END of customization section



class FileStat
{
    var $name;
    var $size;
    var $mtime;
    var $isdir;
    var $img;

    function FileStat($filename)
    {
        $this->name = $filename;
    }
}

function shouldExclude( $file, &$excludes )
{
    $ex = reset( $excludes );
    foreach( $excludes as $ex )
    {
        if ( fnmatch( $ex, $file ) )
            return true;
    }
    return false;
}

function readDirList( $path, &$excludes, &$map )
{
    $handle = opendir( $path );
    if ( $handle === false )
    {
        return null;
    }
    clearstatcache();
    $list = array();
    if ( isset( $_SERVER['LS_AI_INDEX_IGNORE'] ) )
    {
        $ignore = explode( ' ', $_SERVER['LS_AI_INDEX_IGNORE'] );
        $excludes = array_merge( $ignore, $excludes );
    }
    while( false !== ($file=readdir($handle)) )
    {
        if ( shouldExclude( $file, $excludes ) )
            continue;
        $fileStat = new FileStat($file);
        $s = stat("$path$file");
        $fileStat->mtime = $s[9];
        $fileStat->isdir = ($s[2] & 040000)? '/':'';

        // get image mapping
        if ( $fileStat->isdir )
        {
            $fileStat->size = -1;
            $fileStat->img = $map->dir_img;
        }
        else
        {
            if ( $s[12] > 0 )
                $fileStat->size = 512*$s[12];
            else
                $fileStat->size = $s[7];
            $fileStat->img = $map->findImgMapping($file);
        }

        $list[] = $fileStat;
    }
    closedir( $handle );
    return $list;
}

function printOneEntry( $base, $name, $fileStat, $setting )
{
    $encoded = str_replace(array('%2F', '%26amp%3B'), array('/', '%26'), 
                           rawurlencode( $base . $fileStat->name ));
    if ( isset($_SERVER['LS_FI_OFF'])&& $_SERVER['LS_FI_OFF'] )
    {
        $buf = '<li>' . '<a href="' . $encoded .
                 $fileStat->isdir.'">' . sprintf( $setting->nameFormat, $name."</a></li>\n");
    }
    else
    {
        $buf = '<img src="' . $setting->IconPath . '/' . $fileStat->img->imageName .
            '" alt="' . $fileStat->img->alt . '"> <a href="' . $encoded . $fileStat->isdir.'">';
        if ( strlen( $name ) > $setting->nameWidth )
        {
            $name = substr( $name, 0, $setting->nameWidth - 3 ). '...';
        }
        $buf .= sprintf( $setting->nameFormat, $name."</A>");
        if ( $fileStat->mtime != -1 )
            $buf .= date($setting->Time_Format, $fileStat->mtime);
        else
            $buf .= '                   ';
        if ( $fileStat->size != -1 )
            $buf .= sprintf( "%7ldk  ", ( $fileStat->size + 1023 ) / 1024);
        else
            $buf .= '       -  ';
        $buf .= '     ' . $fileStat->img->desc;
        $buf .= "\n";
    }
    echo $buf;

}

function printIncludes( $path, $name )
{
    $testNames = array( "$name.html", "$name.htm", $name );
    foreach ( $testNames as $n )
    {
        $filename = $path . $n;

        if ( file_exists($filename) )
        {
            $content = file_get_contents($filename);
            if ( $n == $name )
            {
                echo "<pre>\n";
                echo $content;
                echo "</pre>\n";
            }
            else
                echo $content;
            break;
        }
    }
}

function printFileList( $list, $base_uri, $setting )
{
    foreach( $list as $fileStat )
    {
        if ( $fileStat->isdir )
        {
            printOneEntry( $base_uri, $fileStat->name, $fileStat, $setting );
        }
    }

    foreach( $list as $fileStat )
    {
        if ( !$fileStat->isdir )
        {
            printOneEntry( $base_uri, $fileStat->name, $fileStat, $setting );
        }
    }

}


function cmpNA( $a, $b )
{
    return strcmp( $a->name, $b->name );
}

function cmpND( $a, $b )
{
    return -cmpNA( $a, $b );
}

function cmpSA( $a, $b )
{
    $ret = $a->size - $b->size;
    if ( $ret )
        return $ret;
    return cmpNA( $a, $b );
}

function cmpSD( $a, $b )
{
    return -cmpSA( $a, $b );
}

function cmpMA( $a, $b )
{
    return $a->mtime - $b->mtime;

}

function cmpMD( $a, $b )
{
    return -cmpMA( $a, $b );
}

function cmpDA( $a, $b )
{
    $ret = strcmp( $a->img->desc, $b->img->desc );
    if ( $ret )
        return $ret;
    return strcmp( $a->name, $b->name );
}

function cmpDD( $a, $b )
{
    return -cmpDA( $a, $b );
}




//phpinfo();
$pos = strpos( $_SERVER['REQUEST_URI'], '?' );
if ( $pos === FALSE )
{
    $uri = $_SERVER['REQUEST_URI'];
}
else
{
    $uri = substr( $_SERVER['REQUEST_URI'], 0, $pos );
}

$uri = urldecode( $uri );
$path = $_SERVER['LS_AI_PATH'];

$mime_type = $_SERVER['LS_AI_MIME_TYPE'];
if ( $mime_type )
    header( "Content-Type: $mime_type" );

if ( !$path )
{
    echo "[ERROR] Auto Index script can not be accessed directly!";
    return ;
}


if (get_magic_quotes_gpc())
{
    $uri  = stripslashes( $uri );
    $path = stripslashes( $path );
}

$uri = htmlentities($uri,ENT_COMPAT,"UTF-8");

$setting = new UserSettings();
$map = new AllImgs();
$sortOrder = $_SERVER['QUERY_STRING'];
if ( $sortOrder == ''
        || strlen($sortOrder) > 2
        || ! in_array($sortOrder, array('NA','ND','MA','MD','SA','SD','DA','DD'))) {
    $sortOrder = 'NA'; // set to default
}

$NameSort = ($sortOrder == 'NA') ? 'ND' : 'NA';
$ModSort = ($sortOrder == 'MA') ? 'MD' : 'MA';
$SizeSort = ($sortOrder == 'SA') ? 'SD' : 'SA';
$DescSort = ($sortOrder == 'DA') ? 'DD' : 'DA';

if ( !$path )
{
    header("HTTP/1.1 403 Forbidden" );
    echo "<h1>403 Access Denied</h1>";
    exit;
}
else
{
    $list = readDirList( $path, $setting->Exclude_Patterns, $map );
    if ( $list === null )
    {
        header("HTTP/1.1 403 Forbidden" );
        echo "<h1>403 Access Denied</h1>";
        exit;
    }
}


echo "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 3.2 Final//EN\">
<html>
  <head>
  <meta http-equiv=\"Content-type\" content=\"text/html; charset=UTF-8\"/>
  <title>Index of ", $uri, "</title></head>
  <body>
    <h1>Index of ", $uri, "</h1>";

if ( isset($setting->HeaderName) )
    printIncludes( $path, $setting->HeaderName );

if ( isset($_SERVER['LS_FI_OFF'])&& $_SERVER['LS_FI_OFF'] )
{
    $header = "<ul>\n";
}
else
{
    $header = "<pre><img src=\"$setting->IconPath/blank.png\" alt=\"     \"> <a href='?$NameSort'>";
    $header .= sprintf( $setting->nameFormat, 'Name</a>' );
    $header .= " <a href='?$ModSort'>Last modified</a>         <a href='?$SizeSort'>Size</a>  <a href='?$DescSort'>Description </a>\n   <hr>";
}
echo $header;

if ( $uri != '/' )
{
    $fileStat = new FileStat('');
    $fileStat->mtime = filemtime($path);
    $fileStat->img = $map->parent_img;
    $fileStat->size = -1;
    $base = substr( $uri, 0, strlen( $uri ) - 1 );
    $off = strrpos( $base, '/' );
    if ( $off !== FALSE )
    {
        $base = substr( $base, 0, $off + 1 );
        printOneEntry(  $base, "Parent Directory", $fileStat, $setting );
    }

}
$cmpFunc = "cmp$sortOrder";
usort( $list, $cmpFunc );
printFileList( $list, $uri, $setting );

if ( isset($_SERVER['LS_FI_OFF'])&& $_SERVER['LS_FI_OFF'] )
{
    echo "</ul>\n";
}
else
{
    echo "</pre><hr>";
}

if ( isset($setting->ReadmeName) ) {
    printIncludes( $path, $setting->ReadmeName );
}

echo "<address>Proudly Served by LiteSpeed Web Server at ".$_SERVER['SERVER_NAME']." Port ".$_SERVER['SERVER_PORT']."</address>
</body>
</html>";
