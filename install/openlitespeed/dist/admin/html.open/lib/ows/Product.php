<?php

class Product
{

    const PROD_NAME = 'OpenLiteSpeed';

    private $version;
    private $new_version;

    private function __construct()
    {
        $matches = [];
        $str = $_SERVER['LSWS_EDITION'];
        if (preg_match('/ (\d.*)$/i', $str, $matches)) {
            $this->version = trim($matches[1]);
        }
        $releasefile = SERVER_ROOT . 'autoupdate/release';
        if (file_exists($releasefile)) {
            $this->new_version = trim(file_get_contents($releasefile));
            if ($this->version == $this->new_version)
                $this->new_version = null;
        }
    }

    public static function GetInstance()
    {
        if (!isset($GLOBALS['_PRODUCT_']))
            $GLOBALS['_PRODUCT_'] = new Product();
        return $GLOBALS['_PRODUCT_'];
    }

    public function getVersion()
    {
        return $this->version;
    }

    public function refreshVersion()
    {
        $versionfile = SERVER_ROOT . 'VERSION';
        $this->version = trim(file_get_contents($versionfile));
    }

    public function getNewVersion()
    {
        return $this->new_version;
    }

}
