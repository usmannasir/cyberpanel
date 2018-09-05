<?php

class DKeywordAlias
{

    private $_aliasmap;
    private $_aliaskey;

    public static function GetInstance()
    {
        if (!isset($GLOBALS['_DKeywordAlias_']))
            $GLOBALS['_DKeywordAlias_'] = new DKeywordAlias();
        return $GLOBALS['_DKeywordAlias_'];
    }

    public static function NormalizedKey($rawkey)
    {
        $tool = DKeywordAlias::GetInstance();
        return $tool->get_normalized_key($rawkey);
    }

    public static function GetShortPrintKey($normalizedkey)
    {
        $tool = DKeywordAlias::GetInstance();
        return $tool->get_short_print_key($normalizedkey);
    }

    private function __construct()
    {
        $this->define_alias();
        $this->_aliaskey = [];
        foreach ($this->_aliasmap as $nk => $sk) {
            $this->_aliaskey[strtolower($sk)] = $nk;
        }
    }

    private function get_normalized_key($rawkey)
    {
        $key = strtolower($rawkey);
        if (isset($this->_aliaskey[$key]))
            return $this->_aliaskey[$key];
        else
            return $key;
    }

    private function get_short_print_key($normalizedkey)
    {
        if (isset($this->_aliasmap[$normalizedkey]))
            return $this->_aliasmap[$normalizedkey];
        else
            return NULL;
    }

    private function define_alias()
    {
        // key is all lower case, value is output case
        $this->_aliasmap = array(
                //'accesscontrol' => 'acc',
                //'address' => 'addr',
        );
    }

}
