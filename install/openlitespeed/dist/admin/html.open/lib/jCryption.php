<?php

/**
 * jCryption
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
 * I just changed, added, removed and improved some functions to fit the needs of jCryption
 *
 * @author     Daniel Griesser <daniel.griesser@jcryption.org>
 * @copyright  2010 Daniel Griesser
 * @license    http://www.php.net/license/3_0.txt  PHP License 3.0
 * @version    1.1
 * @link       http://jcryption.org/
 */
class jCryption
{

    private $_key_len;
    private $_e;

    /**
     * Constructor
     *
     * @access public
     */
    public function __construct($e = "\x01\x00\x01")
    {
        $this->_e = $e;
    }

    /**
     * Generates the Keypair with the given keyLength the encryption key e ist set staticlly
     * set to 65537 for faster encryption.
     *
     * @param int $keyLength
     * @return array
     * @access public
     */
    public function generateKeypair($keyLength)
    {
        $this->_key_len = intval($keyLength);
        if ($this->_key_len < 8) {
            $this->_key_len = 8;
        }

        // set [e] to 0x10001 (65537)
        $e = $this->bin2int($this->_e);

        // generate [p], [q] and [n]
        $p_len = intval(($this->_key_len + 1) / 2);
        $q_len = $this->_key_len - $p_len;
        $p1 = $q1 = 0;
        do {
            // generate prime number [$p] with length [$p_len] with the following condition:
            // GCD($e, $p - 1) = 1

            do {
                $p = $this->getPrime($p_len);
                $p1 = $this->dec($p);
                $tmp = $this->GCD($e, $p1);
            } while (!$this->isOne($tmp));
            // generate prime number [$q] with length [$q_len] with the following conditions:
            // GCD($e, $q - 1) = 1
            // $q != $p

            do {
                $q = $this->getPrime($q_len);
                //$q = 102238965184417281201422828818276460200050705922822343263269460146519295919831;
                $q1 = $this->dec($q);
                $tmp = $this->GCD($e, $q1);
            } while (!$this->isOne($tmp) && !$this->cmpAbs($q, $p));

            // if (p < q), then exchange them
            if ($this->cmpAbs($p, $q) < 0) {
                $tmp = $p;
                $p = $q;
                $q = $tmp;
                $tmp = $p1;
                $p1 = $q1;
                $q1 = $tmp;
            }
            // calculate n = p * q
            $n = $this->mul($p, $q);
        } while ($this->bitLen($n) != $this->_key_len);

        // calculate d = 1/e mod (p - 1) * (q - 1)
        $pq = $this->mul($p1, $q1);
        $d = $this->invmod($e, $pq);

        // store RSA keypair attributes
        $keypair = array('n' => $n, 'e' => $e, 'd' => $d, 'p' => $p, 'q' => $q);

        return $keypair;
    }

    public function useKeys($keys, $keyLength)
    {
        $this->_key_len = intval($keyLength);
        if ($this->_key_len < 8) {
            $this->_key_len = 8;
        }

        // set [e] to 0x10001 (65537)
        $e = $this->bin2int($this->_e);

        // generate [p], [q] and [n]
        $p_len = intval(($this->_key_len + 1) / 2);
        $q_len = $this->_key_len - $p_len;
        $p1 = $q1 = 0;
        do {
            do {
                $q = $keys[rand(0, count($keys))];
                $p = $keys[rand(0, count($keys))];
                $p1 = $this->dec($p);
                $q1 = $this->dec($q);
            } while (!$this->cmpAbs($q, $p));


            // if (p < q), then exchange them
            if ($this->cmpAbs($p, $q) < 0) {
                $tmp = $p;
                $p = $q;
                $q = $tmp;
                $tmp = $p1;
                $p1 = $q1;
                $q1 = $tmp;
            }
            // calculate n = p * q
            $n = $this->mul($p, $q);
        } while ($this->bitLen($n) != $this->_key_len);

        // calculate d = 1/e mod (p - 1) * (q - 1)
        $pq = $this->mul($p1, $q1);
        $d = $this->invmod($e, $pq);

        // store RSA keypair attributes
        $keypair = array('n' => $n, 'e' => $e, 'd' => $d, 'p' => $p, 'q' => $q);

        return $keypair;
    }

    /**
     * Finds greatest common divider (GCD) of $num1 and $num2
     *
     * @param string $num1
     * @param string $num2
     * @return string
     * @access public
     */
    public function GCD($num1, $num2)
    {
        do {
            $tmp = bcmod($num1, $num2);
            $num1 = $num2;
            $num2 = $tmp;
        } while (bccomp($num2, '0'));
        return $num1;
    }

    /**
     * Performs Miller-Rabin primality test for number $num
     * with base $base. Returns true, if $num is strong pseudoprime
     * by base $base. Else returns false.
     *
     * @param string $num
     * @param string $base
     * @return bool
     * @access private
     */
    public function _millerTest($num, $base)
    {
        if (!bccomp($num, '1')) {
            // 1 is not prime ;)
            return false;
        }
        $tmp = bcsub($num, '1');

        $zero_bits = 0;
        while (!bccomp(bcmod($tmp, '2'), '0')) {
            $zero_bits++;
            $tmp = bcdiv($tmp, '2');
        }

        $tmp = $this->powmod($base, $tmp, $num);
        if (!bccomp($tmp, '1')) {
            // $num is probably prime
            return true;
        }

        while ($zero_bits--) {
            if (!bccomp(bcadd($tmp, '1'), $num)) {
                // $num is probably prime
                return true;
            }
            $tmp = $this->powmod($tmp, '2', $num);
        }
        // $num is composite
        return false;
    }

    /**
     * Transforms binary representation of large integer into its native form.
     *
     * Example of transformation:
     *    $str = "\x12\x34\x56\x78\x90";
     *    $num = 0x9078563412;
     *
     * @param string $str
     * @return string
     * @access public
     */
    public function bin2int($str)
    {
        $result = '0';
        $n = strlen($str);
        do {
            $result = bcadd(bcmul($result, '256'), ord($str { --$n}));
        } while ($n > 0);
        return $result;
    }

    /**
     * Transforms large integer into binary representation.
     *
     * Example of transformation:
     *    $num = 0x9078563412;
     *    $str = "\x12\x34\x56\x78\x90";
     *
     * @param string $num
     * @return string
     * @access public
     */
    public function int2bin($num)
    {
        $result = '';
        do {
            $result .= chr(bcmod($num, '256'));
            $num = bcdiv($num, '256');
        } while (bccomp($num, '0'));
        return $result;
    }

    /**
     * Calculates pow($num, $pow) (mod $mod)
     *
     * @param string $num
     * @param string $pow
     * @param string $mod
     * @return string
     * @access public
     */
    public function powmod($num, $pow, $mod)
    {
        if (function_exists('bcpowmod')) {
            // bcpowmod is only available under PHP5
            return bcpowmod($num, $pow, $mod);
        }

        // emulate bcpowmod
        $result = '1';
        do {
            if (!bccomp(bcmod($pow, '2'), '1')) {
                $result = bcmod(bcmul($result, $num), $mod);
            }
            $num = bcmod(bcpow($num, '2'), $mod);
            $pow = bcdiv($pow, '2');
        } while (bccomp($pow, '0'));
        return $result;
    }

    /**
     * Calculates $num1 * $num2
     *
     * @param string $num1
     * @param string $num2
     * @return string
     * @access public
     */
    public function mul($num1, $num2)
    {
        return bcmul($num1, $num2);
    }

    /**
     * Calculates $num1 % $num2
     *
     * @param string $num1
     * @param string $num2
     * @return string
     * @access public
     */
    public function mod($num1, $num2)
    {
        return bcmod($num1, $num2);
    }

    /**
     * Compares abs($num1) to abs($num2).
     * Returns:
     *   -1, if abs($num1) < abs($num2)
     *   0, if abs($num1) == abs($num2)
     *   1, if abs($num1) > abs($num2)
     *
     * @param string $num1
     * @param string $num2
     * @return int
     * @access public
     */
    public function cmpAbs($num1, $num2)
    {
        return bccomp($num1, $num2);
    }

    /**
     * Tests $num on primality. Returns true, if $num is strong pseudoprime.
     * Else returns false.
     *
     * @param string $num
     * @return bool
     * @access private
     */
    public function isPrime($num)
    {
        static $primes = null;
        static $primes_cnt = 0;
        if (is_null($primes)) {
            // generate all primes up to 10000
            $primes = array();
            for ($i = 0; $i < 10000; $i++) {
                $primes[] = $i;
            }
            $primes[0] = $primes[1] = 0;
            for ($i = 2; $i < 100; $i++) {
                while (!$primes[$i]) {
                    $i++;
                }
                $j = $i;
                for ($j += $i; $j < 10000; $j += $i) {
                    $primes[$j] = 0;
                }
            }
            $j = 0;
            for ($i = 0; $i < 10000; $i++) {
                if ($primes[$i]) {
                    $primes[$j++] = $primes[$i];
                }
            }
            $primes_cnt = $j;
        }

        // try to divide number by small primes
        for ($i = 0; $i < $primes_cnt; $i++) {
            if (bccomp($num, $primes[$i]) <= 0) {
                // number is prime
                return true;
            }
            if (!bccomp(bcmod($num, $primes[$i]), '0')) {
                // number divides by $primes[$i]
                return false;
            }
        }

        /*
          try Miller-Rabin's probable-primality test for first
          7 primes as bases
         */
        for ($i = 0; $i < 7; $i++) {
            if (!$this->_millerTest($num, $primes[$i])) {
                // $num is composite
                return false;
            }
        }
        // $num is strong pseudoprime
        return true;
    }

    /**
     * Produces a better random number
     * for seeding mt_rand()
     *
     * @access private
     */
    public function _makeSeed()
    {
        return hexdec(sha1(sha1(microtime(true) * mt_rand()) . md5(microtime(true) * mt_rand())));
    }

    /**
     * Generates prime number with length $bits_cnt
     *
     * @param int $bits_cnt
     * @access public
     */
    public function getPrime($bits_cnt)
    {
        $bytes_n = intval($bits_cnt / 8);
        $bits_n = $bits_cnt % 8;
        do {
            $str = '';
            mt_srand((int) $this->_makeSeed());
            for ($i = 0; $i < $bytes_n; $i++) {
                $str .= chr((int) sha1(mt_rand() * microtime(true)) & 0xff);
            }
            $n = mt_rand() * microtime(true) & 0xff;

            $n |= 0x80;
            $n >>= 8 - $bits_n;
            $str .= chr($n);
            $num = $this->bin2int($str);

            // search for the next closest prime number after [$num]
            if (!bccomp(bcmod($num, '2'), '0')) {
                $num = bcadd($num, '1');
            }
            while (!$this->isPrime($num)) {
                $num = bcadd($num, '2');
            }
        } while ($this->bitLen($num) != $bits_cnt);
        return $num;
    }

    /**
     * Calculates $num - 1
     *
     * @param string $num
     * @return string
     * @access public
     */
    public function dec($num)
    {
        return bcsub($num, '1');
    }

    /**
     * Returns true, if $num is equal to one. Else returns false
     *
     * @param string $num
     * @return bool
     * @access public
     */
    public function isOne($num)
    {
        return !bccomp($num, '1');
    }

    /**
     * Finds inverse number $inv for $num by modulus $mod, such as:
     *     $inv * $num = 1 (mod $mod)
     *
     * @param string $num
     * @param string $mod
     * @return string
     * @access public
     */
    public function invmod($num, $mod)
    {
        $x = '1';
        $y = '0';
        $num1 = $mod;
        do {
            $tmp = bcmod($num, $num1);
            $q = bcdiv($num, $num1);
            $num = $num1;
            $num1 = $tmp;

            $tmp = bcsub($x, bcmul($y, $q));
            $x = $y;
            $y = $tmp;
        } while (bccomp($num1, '0'));
        if (bccomp($x, '0') < 0) {
            $x = bcadd($x, $mod);
        }
        return $x;
    }

    /**
     * Returns bit length of number $num
     *
     * @param string $num
     * @return int
     * @access public
     */
    public function bitLen($num)
    {
        $tmp = $this->int2bin($num);
        $bit_len = strlen($tmp) * 8;
        $tmp = ord($tmp {strlen($tmp) - 1});
        if (!$tmp) {
            $bit_len -= 8;
        }
        else {
            while (!($tmp & 0x80)) {
                $bit_len--;
                $tmp <<= 1;
            }
        }
        return $bit_len;
    }

    /**
     * Calculates bitwise or of $num1 and $num2,
     * starting from bit $start_pos for number $num1
     *
     * @param string $num1
     * @param string $num2
     * @param int $start_pos
     * @return string
     * @access public
     */
    public function bitOr($num1, $num2, $start_pos)
    {
        $start_byte = intval($start_pos / 8);
        $start_bit = $start_pos % 8;
        $tmp1 = $this->int2bin($num1);

        $num2 = bcmul($num2, 1 << $start_bit);
        $tmp2 = $this->int2bin($num2);
        if ($start_byte < strlen($tmp1)) {
            $tmp2 |= substr($tmp1, $start_byte);
            $tmp1 = substr($tmp1, 0, $start_byte) . $tmp2;
        }
        else {
            $tmp1 = str_pad($tmp1, $start_byte, "\0") . $tmp2;
        }
        return $this->bin2int($tmp1);
    }

    /**
     * Returns part of number $num, starting at bit
     * position $start with length $length
     *
     * @param string $num
     * @param int start
     * @param int length
     * @return string
     * @access public
     */
    public function subint($num, $start, $length)
    {
        $start_byte = intval($start / 8);
        $start_bit = $start % 8;
        $byte_length = intval($length / 8);
        $bit_length = $length % 8;
        if ($bit_length) {
            $byte_length++;
        }
        $num = bcdiv($num, 1 << $start_bit);
        $tmp = substr($this->int2bin($num), $start_byte, $byte_length);
        $tmp = str_pad($tmp, $byte_length, "\0");
        $tmp = substr_replace($tmp, $tmp {$byte_length - 1} & chr(0xff >> (8 - $bit_length)), $byte_length - 1, 1);
        return $this->bin2int($tmp);
    }

    /**
     * Converts a hex string to bigint string
     *
     * @param string $hex
     * @return string
     * @access public
     */
    public function hex2bint($hex)
    {
        $result = '0';
        for ($i = 0; $i < strlen($hex); $i++) {
            $result = bcmul($result, '16');
            if ($hex[$i] >= '0' && $hex[$i] <= '9') {
                $result = bcadd($result, $hex[$i]);
            }
            else if ($hex[$i] >= 'a' && $hex[$i] <= 'f') {
                $result = bcadd($result, '1' . ('0' + (ord($hex[$i]) - ord('a'))));
            }
            else if ($hex[$i] >= 'A' && $hex[$i] <= 'F') {
                $result = bcadd($result, '1' . ('0' + (ord($hex[$i]) - ord('A'))));
            }
        }
        return $result;
    }

    /**
     * Converts a hex string to int
     *
     * @param string $hex
     * @return int
     * @access public
     */
    public function hex2int($hex)
    {
        $result = 0;
        for ($i = 0; $i < strlen($hex); $i++) {
            $result *= 16;
            if ($hex[$i] >= '0' && $hex[$i] <= '9') {
                $result += ord($hex[$i]) - ord('0');
            }
            else if ($hex[$i] >= 'a' && $hex[$i] <= 'f') {
                $result += 10 + (ord($hex[$i]) - ord('a'));
            }
            else if ($hex[$i] >= 'A' && $hex[$i] <= 'F') {
                $result += 10 + (ord($hex[$i]) - ord('A'));
            }
        }
        return $result;
    }

    /**
     * Converts a bigint string to the ascii code
     *
     * @param string $bigint
     * @return string
     * @access public
     */
    public function bint2char($bigint)
    {
        $message = '';
        while (bccomp($bigint, '0') != 0) {
            $ascii = bcmod($bigint, '256');
            $bigint = bcdiv($bigint, '256', 0);
            $message .= chr($ascii);
        }
        return $message;
    }

    /**
     * Removes the redundacy in den encrypted string
     *
     * @param string $string
     * @return mixed
     * @access public
     */
    public function redundacyCheck($string)
    {
        $r1 = substr($string, 0, 2);
        $r2 = substr($string, 2);
        $check = $this->hex2int($r1);
        $value = $r2;
        $sum = 0;
        for ($i = 0; $i < strlen($value); $i++) {
            $sum += ord($value[$i]);
        }
        if ($check == ($sum & 0xFF)) {
            return $value;
        }
        else {
            return NULL;
        }
    }

    /**
     * Decrypts a given string with the $dec_key and the $enc_mod
     *
     * @param string $encrypted
     * @param int $dec_key
     * @param int $enc_mod
     * @return string
     * @access public
     */
    public function decrypt($encrypted, $dec_key, $enc_mod)
    {
        //replaced split with explode
        $blocks = explode(' ', $encrypted);
        $result = "";
        $max = count($blocks);
        for ($i = 0; $i < $max; $i++) {
            $dec = $this->hex2bint($blocks[$i]);
            $dec = $this->powmod($dec, $dec_key, $enc_mod);
            $ascii = $this->bint2char($dec);
            $result .= $ascii;
        }
        return $this->redundacyCheck($result);
    }

    /**
     * Converts a given decimal string to any base between 2 and 36
     *
     * @param string $decimal
     * @param int $base
     * @return string
     */
    public function dec2string($decimal, $base)
    {

        $string = null;

        $base = (int) $base;
        if ($base < 2 | $base > 36 | $base == 10) {
            echo 'BASE must be in the range 2-9 or 11-36';
            exit;
        }

        $charset = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';

        $charset = substr($charset, 0, $base);

        do {
            $remainder = bcmod($decimal, $base);
            $char = substr($charset, $remainder, 1);
            $string = "$char$string";
            $decimal = bcdiv(bcsub($decimal, $remainder), $base);
        } while ($decimal > 0);

        return strtolower($string);
    }

    public function getE()
    {
        return $this->_e;
    }

    public function generatePrime($length)
    {
        $this->_key_len = intval($length);
        if ($this->_key_len < 8) {
            $this->_key_len = 8;
        }

        $e = $this->bin2int("\x01\x00\x01");

        $p_len = intval(($this->_key_len + 1) / 2);
        do {
            $p = $this->getPrime($p_len);
            $p1 = $this->dec($p);
            $tmp = $this->GCD($e, $p1);
        } while (!$this->isOne($tmp));

        return $p;
    }

}
