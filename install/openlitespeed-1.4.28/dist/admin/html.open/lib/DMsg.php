<?php

class DMsg
{
	const LANG_DIR = 'admin/html/res/lang/';

	const DEFAULT_LANG = 'english';
	const LANG_ENGLISH = 'english';
	const LANG_CHINESE = 'chinese';
	const LANG_JAPANES = 'japanes';

	const _COOKIE_LANG_ = 'litespeed_admin_lang';

	private static $_supported = array(
			self::LANG_ENGLISH => array('English', 'en-US'),
			self::LANG_CHINESE => array('中文', 'zh-CN'),
			self::LANG_JAPANES => array('日本語', 'ja-JP')
	);


	private static $_curlang = '';
	private static $_curtips = '';

	private static function init()
	{
		$lang = DMsg::DEFAULT_LANG;

		if (isset($_SESSION[DMsg::_COOKIE_LANG_])) {
			$lang = $_SESSION[DMsg::_COOKIE_LANG_];
		}
		else {
			$lang1 = UIBase::GrabGoodInput('cookie',self::_COOKIE_LANG_);
			if ($lang1 != NULL && $lang != $lang1 && array_key_exists($lang1, self::$_supported)) {
				$lang = $lang1;
			}
			DMsg::SetLang($lang);
		}

		$filecode = self::$_supported[$lang][1];
		self::$_curlang = $lang;

        $msgfile = SERVER_ROOT . self::LANG_DIR . 'en-US_msg.php';
        if (file_exists($msgfile)) {
            // maybe called from command line for converter tool
            include $msgfile;

            if ($lang != DMsg::DEFAULT_LANG) {
                include SERVER_ROOT . self::LANG_DIR . $filecode . '_msg.php';
            }
        }
	}

	private static function init_tips()
	{
		if (self::$_curlang == '')
			self::init();

		if (self::$_curlang != self::DEFAULT_LANG) {
			$filecode = self::$_supported[self::DEFAULT_LANG][1];
			include SERVER_ROOT . self::LANG_DIR . $filecode . '_tips.php';
		}
		$filecode = self::$_supported[self::$_curlang][1];
		self::$_curtips = $filecode . '_tips.php';
		include SERVER_ROOT . self::LANG_DIR . self::$_curtips;
	}

	public static function GetSupportedLang(&$cur_lang)
	{
		if (self::$_curlang == '')
			self::init();

		$cur_lang = self::$_curlang;
		return self::$_supported;
	}

	public static function SetLang($lang)
	{
		if (array_key_exists($lang, self::$_supported)) {
			$_SESSION[DMsg::_COOKIE_LANG_] = $lang;
			self::$_curlang = '';
			self::$_curtips = '';
			$domain = $_SERVER['HTTP_HOST'];
			if ($pos = strpos($domain, ':')) {
				$domain = substr($domain, 0, $pos);
			}
			$secure = !empty($_SERVER['HTTPS']);
			$httponly = true;

			setcookie(DMsg::_COOKIE_LANG_, $lang, strtotime('+10 days'), '/', $domain, $secure, $httponly);
		}
	}

	public static function GetAttrTip($label)
	{
		if ($label == '')
			return NULL;

		global $_tipsdb;

		if (self::$_curtips == '') {
			self::init_tips();
		}

		if (isset($_tipsdb[$label]))
			return $_tipsdb[$label];
		else {
			//error_log("DMsg:undefined attr tip $label"); allow null
			return NULL;
		}
	}

    public static function GetEditTips($labels)
    {
		global $_tipsdb;

		if (self::$_curtips == '') {
			self::init_tips();
		}

        $tips = array();
        foreach ($labels as $label) {
            $label = 'EDTP:' . $label;
            if (isset($_tipsdb[$label]))
                $tips = array_merge($tips, $_tipsdb[$label]);
        }
        if (empty($tips))
            return NULL;
        else
            return $tips;
    }

	public static function UIStr($tag, $repl='')
	{
		if ($tag == '')
			return NULL;

		global $_gmsg;
		if (self::$_curlang == '')
			DMsg::init();

		if (isset($_gmsg[$tag]))
			if ($repl == '')
				return $_gmsg[$tag];
			else {
				$search = array_keys($repl);
				$replace = array_values($repl);
				return str_replace($search, $replace, $_gmsg[$tag]);
			}
		else {
			//error_log("DMsg:undefined UIStr tag $tag");
			return 'Unknown';
		}
	}

	public static function EchoUIStr($tag, $repl='')
	{
		echo DMsg::UIStr($tag, $repl);
	}
	
	public static function DocsUrl()
	{
		if (self::$_curlang == '') {
			DMsg::init();
		}
	
		$url = '/docs/';
		if (self::$_curlang != self::DEFAULT_LANG) {
			$url .= self::$_supported[self::$_curlang][1] . '/';
		}
		return $url;
	}

	public static function ALbl($tag)
	{
		if ($tag == '')
			return NULL;

		global $_gmsg;
		if (self::$_curlang == '') {
			DMsg::init();
		}

		if (isset($_gmsg[$tag]))
			return $_gmsg[$tag];
		else {
			//error_log("DMsg:undefined ALbl tag $tag");
			return 'Unknown';
		}
	}

	public static function Err($tag)
	{
		if ($tag == '')
			return NULL;

		global $_gmsg;
		if (self::$_curlang == '')
			DMsg::init();

		if (isset($_gmsg[$tag]))
			return $_gmsg[$tag] . ' '; // add extra space
		else {
			//error_log("DMsg:undefined Err tag $tag");
			return 'Unknown';
		}
	}

	private static function echo_sort_keys($lang_array, $priority)
	{
		$keys = array_keys($lang_array);
		$key2 = array();
		foreach ($keys as $key) {
			$pos = strpos($key, '_') + 1;
			$key2[substr($key, 0, $pos)][] = substr($key, $pos);
		}

		foreach ($priority as $pri) {
			if (isset($key2[$pri])) {
				sort($key2[$pri]);
				foreach ($key2[$pri] as $subid) {
					$id = $pri . $subid;
					echo '$_gmsg[\'' . $id . '\'] = \'' . addslashes($lang_array[$id]) . "'; \n";
				}
				echo "\n\n";
				unset($key2[$pri]);
			}
		}

		if (count($key2) > 0) {
			echo "// *** Not in priority \n";
			print_r($key2);
		}
	}

	public static function Util_SortMsg($lang, $option)
	{
		if (!array_key_exists($lang, self::$_supported)) {
			echo "language $lang not supported! \n" .
				"Currently supported:" . print_r(array_keys(self::$_supported), true);
			return;
		}

		global $_gmsg;

		$filecode = self::$_supported[$lang][1];
		include 'en-US_msg.php';

		$english = $_gmsg;
		$added = NULL;
		$_gmsg = NULL;

		if ($lang != DMsg::DEFAULT_LANG) {
			include $filecode . '_msg.php';
			$added = $_gmsg;
		}

		$header = '<?php

/**
 * WebAdmin Language File
* ' . self::$_supported[$lang][0] . '(' . self::$_supported[$lang][1] . ')
*
* Please Note: These language files will be overwritten during software updates.
*
* @author     LiteSpeed Technoglogies
* @copyright  Copyright (c) LiteSpeed 2014-2017
* @link       http://www.litespeedtech.com/
*/

global $_gmsg;';

		echo $header . "\n\n";

		$priority = array('menu_', 'tab_', 'btn_', 'note_', 'err_', 'l_', 'o_', 'parse_', 'service_', 'buildphp_', 'mail_');

		if (!$added) {
			// output sorted english
			self::echo_sort_keys($english, $priority);
		}
		else {

			if ($option == 'mixed') {
				$mixed = array_merge($english, $added);
				self::echo_sort_keys($mixed, $priority);
			}
			else {
				self::echo_sort_keys($added, $priority);

				echo "\n//***** Not in original lang file ***\n\n";

				foreach ($added as $addedkey => $msg) {
					unset($english[$addedkey]);
				}
				self::echo_sort_keys($english, $priority);
			}
		}

	}

}