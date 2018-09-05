<?php

require_once('../html/lib/jCryption.php') ;

/**
 * RSAKeyImport
 *
 * PHP versions 4 and 5
 *
 * LICENSE: This source file is subject to version 3.0 of the PHP license
 * that is available through the world-wide-web at the following URI:
 * http://www.php.net/license/3_0.txt.  If you did not receive a copy of
 * the PHP License and are unable to obtain it through the web, please
 * send a note to license@php.net so we can mail you a copy immediately.
 *
 * Many of the functions in this class are from the PEAR Crypt_RSA package ...
 * So most of the credits goes to the original creator of this package Alexander Valyalkin
 * you can get the package under http://pear.php.net/package/Crypt_RSA
 *
 * This is just a simplified extraction for the PEM key import functionality and requires bcmath.
 *
 * @author     Lite Speed Technologies <info@litespeedtech.com>
 * @copyright  2009 Lite Speed Technologies
 * @license    http://www.php.net/license/3_0.txt  PHP License 3.0
 * @version    1.0.0
 */
class RSAKeyImport
{

    public static function bin2int( $str )
    {
        $result = '0' ;
        $n = strlen($str) ;
        do {
            $result = bcadd(bcmul($result, '256'), ord($str{ -- $n})) ;
        } while ( $n > 0 ) ;
        return $result ;
    }

    public static function fromPEMString( $str )
    {
        // search for base64-encoded private key
        if ( ! preg_match('/-----BEGIN RSA PRIVATE KEY-----([^-]+)-----END RSA PRIVATE KEY-----/', $str, $matches) ) {
            echo ("can't find RSA private key in the string [{$str}]") ;
            return false ;
        }

        // parse private key. It is ASN.1-encoded
        $str = base64_decode($matches[1]) ;
        $pos = 0 ;
        $tmp = RSAKeyImport::_ASN1Parse($str, $pos) ;
        if ( $tmp == false )
            return false ;

        if ( $tmp['tag'] != 0x10 ) {
            echo "Expected 0x10 (SEQUENCE) wrong ASN tag value: " . $tmp['tag'] ;
            return false ;
        }

        // parse ASN.1 SEQUENCE for RSA private key
        $attr_names = array( 'version', 'n', 'e', 'd', 'p', 'q', 'dmp1', 'dmq1', 'iqmp' ) ;
        $n = sizeof($attr_names) ;
        $rsa_attrs = array() ;
        for ( $i = 0 ; $i < $n ; $i ++  ) {
            $tmp = RSAKeyImport::_ASN1ParseInt($str, $pos) ;
            if ( $tmp === false ) {
                echo "fail to parse int" ;
                return false ;
            }
            $attr = $attr_names[$i] ;
            $rsa_attrs[$attr] = $tmp ;
        }
        return $rsa_attrs ;

    }

    public static function _ASN1Parse( $str, &$pos )
    {
        $max_pos = strlen($str) ;
        if ( $max_pos < 2 ) {
            echo ("ASN.1 string too short") ;
            return false ;
        }

        // get ASN.1 tag value
        $tag = ord($str[$pos ++]) & 0x1f ;
        if ( $tag == 0x1f ) {
            $tag = 0 ;
            do {
                $n = ord($str[$pos ++]) ;
                $tag <<= 7 ;
                $tag |= $n & 0x7f ;
            } while ( ($n & 0x80) && $pos < $max_pos ) ;
        }
        if ( $pos >= $max_pos ) {
            echo("ASN.1 string too short") ;
            return false ;
        }

        // get ASN.1 object length
        $len = ord($str[$pos ++]) ;
        if ( $len & 0x80 ) {
            $n = $len & 0x1f ;
            $len = 0 ;
            while ( $n -- && $pos < $max_pos ) {
                $len <<= 8 ;
                $len |= ord($str[$pos ++]) ;
            }
        }
        if ( $pos >= $max_pos || $len > $max_pos - $pos ) {
            echo ("ASN.1 string too short") ;
            return false ;
        }

        // get string value of ASN.1 object
        $str = substr($str, $pos, $len) ;

        return array(
            'tag' => $tag,
            'str' => $str,
        ) ;
    }

    public static function _ASN1ParseInt( $str, &$pos )
    {
        $tmp = RSAKeyImport::_ASN1Parse($str, $pos) ;
        if ( $tmp == false ) {
            return false ;
        }
        if ( $tmp['tag'] != 0x02 ) {
            echo "Expected 0x02 (INTEGER) wrong ASN tag value: " . $tmp['tag'] ;
            return false ;
        }
        $pos += strlen($tmp['str']) ;

        return strrev($tmp['str']) ;
    }

    public static function dec2string( $decimal, $base )
    {

        $string = null ;

        $base = (int) $base ;
        if ( $base < 2 | $base > 36 | $base == 10 ) {
            echo 'BASE must be in the range 2-9 or 11-36' ;
            exit ;
        }

        $charset = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ' ;

        $charset = substr($charset, 0, $base) ;

        do {
            $remainder = bcmod($decimal, $base) ;
            $char = substr($charset, $remainder, 1) ;
            $string = "$char$string" ;
            $decimal = bcdiv(bcsub($decimal, $remainder), $base) ;
        } while ( $decimal > 0 ) ;

        return strtolower($string) ;
    }

    public static function import_and_convert( $pem_filename )
    {
        $str1 = file_get_contents($pem_filename) ;
        if ( $str1 == false ) {
            echo "failed to open file $pem_filename" ;
            return false ;
        }

        $attrs = RSAKeyImport::fromPEMString($str1) ;
        if ( $attrs == false ) {
            echo "failed to parse $pem_filename" ;
            return false ;
        }

        $n_int = RSAKeyImport::bin2int($attrs['n']) ;
        $d_int = RSAKeyImport::bin2int($attrs['d']) ;
        $e_int = RSAKeyImport::bin2int($attrs['e']) ;
        $e_hex = RSAKeyImport::dec2string($e_int, 16) ;
        $n_hex = RSAKeyImport::dec2string($n_int, 16) ;
        $mykeys = array( 'e_hex' => $e_hex, 'n_hex' => $n_hex, 'd_int' => $d_int, 'n_int' => $n_int ) ;

        return $mykeys ;
    }

}

## main
# openssl genrsa -out key.pem 512

$mykeys = NULL ;

if ( isset($argv[1]) ) {
    $pemfile = $argv[1] ;
    $mykeys = RSAKeyImport::import_and_convert($pemfile) ;
}

if ( $mykeys == FALSE ) {
    echo "Using php to generate keys, please be patient ... \n" ;

    $keyLength = 512 ;
    $jCryption = new jCryption() ;
    $keys = $jCryption->generateKeypair($keyLength) ;
    $e_hex = $jCryption->dec2string($keys['e'], 16) ;
    $n_hex = $jCryption->dec2string($keys['n'], 16) ;
    $mykeys = array( 'e_hex' => $e_hex, 'n_hex' => $n_hex, 'd_int' => $keys['d'], 'n_int' => $keys['n'] ) ;
}

$keyfile = '../conf/jcryption_keypair' ;
$serialized_str = serialize($mykeys) ;
$result = file_put_contents($keyfile, $serialized_str) ;
chmod($keyfile, 0600) ;

if ( $result == TRUE )
    exit(0) ;
else
    exit(1) ;
?>
