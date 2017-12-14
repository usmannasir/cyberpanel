<?php

class BuildConfig
{

    const OPTION_VERSION = 1;
    const BUILD_DIR = 2;
    const LAST_CONF = 3;
    const DEFAULT_INSTALL_DIR = 4;
    const DEFAULT_PARAMS = 5;
    const PHP_VERSION = 10;
    const LSAPI_VERSION = 11;
    const SUHOSIN_VERSION = 12;
    const APC_VERSION = 13;
    const XCACHE_VERSION = 14;
    const MEMCACHE_VERSION = 15;
    const OPCACHE_VERSION = 16;
    const MEMCACHED_VERSION = 17;
    const MEMCACHED7_VERSION = 18;

    public static function GetVersion($field)
    {
        // you can update the below list to include your versions
        switch ($field) {

            case self::PHP_VERSION: return
                        array(
                            '7.1.9',
                            '7.0.23',
                            '5.6.31',
                            '5.5.38',
                            '5.4.45',
                            '5.3.29',
                            '5.2.17',
                            '4.4.9');

            case self::LSAPI_VERSION: return '6.11';

            case self::SUHOSIN_VERSION: return '0.9.38';

            case self::APC_VERSION: return '3.1.9';

            case self::XCACHE_VERSION: return '3.2.0';

            case self::MEMCACHE_VERSION: return '2.2.7';

            case self::MEMCACHED_VERSION: return '2.2.0';

            case self::MEMCACHED7_VERSION: return '3.0.3'; // for php7 only

            case self::OPCACHE_VERSION: return '7.0.5';

            default: die("illegal field");
        }
    }

    public static function Get($field)
    {
        switch ($field) {
            case self::OPTION_VERSION:
                return 3;
            case self::BUILD_DIR:
                return SERVER_ROOT . 'phpbuild';
            case self::LAST_CONF:
                return SERVER_ROOT . 'phpbuild/savedconfig.';
            case self::DEFAULT_INSTALL_DIR:
                return SERVER_ROOT . 'lsphp';  // actual dir will include . php base version.
            case self::DEFAULT_PARAMS:
                return array(
                    '7' => '--with-mysqli --with-zlib --with-gd --enable-shmop --enable-sockets --enable-sysvsem --enable-sysvshm --enable-mbstring --with-iconv --with-mcrypt --with-pdo-mysql --enable-ftp --enable-zip --with-curl --enable-soap --enable-xml --enable-json  --with-openssl --enable-bcmath',
                    '5' => '--with-mysqli --with-zlib --with-gd --enable-shmop --enable-sockets --enable-sysvsem --enable-sysvshm --enable-mbstring --with-iconv --with-mysql --with-mcrypt --with-pdo --with-pdo-mysql --enable-ftp --enable-zip --with-curl --enable-soap --enable-xml --enable-json  --with-openssl --enable-bcmath',
                    '4' => '--with-mysql  --with-zlib --with-gd --enable-shmop --enable-sockets --enable-sysvsem --enable-sysvshm --enable-magic-quotes --enable-mbstring'
                        );
        }
    }

}

include_once( 'buildfunc.inc.php' );

