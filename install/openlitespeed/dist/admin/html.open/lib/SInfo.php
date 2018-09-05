<?php

class SInfo
{

    const SREQ_RESTART_SERVER = 2;
    const SREQ_TOGGLE_DEBUG = 3;
    const SREQ_VH_RELOAD = 4;
    const SREQ_VH_ENABLE = 5;
    const SREQ_VH_DISABLE = 6;
    const DATA_ADMIN_EMAIL = 10;
    const DATA_ADMIN_KEYFILE = 11;
    const DATA_DEBUGLOG_STATE = 12;
    const DATA_PID = 13;
    const DATA_VIEW_LOG = 14;
    const DATA_DASH_LOG = 15;

    private $_servData;
    private $_listeners;
    private $_adminL;
    private $_vhosts;
    private $_serverLog = null;
    private $_serverLastModTime = 100;

    const FNAME = '/tmp/lshttpd/.admin';
    const FPID = '/tmp/lshttpd/lshttpd.pid';
    const DATA_Status_LV = 1;
    const FLD_Listener = 'lis';
    const FLD_VHosts = 'vhosts';

    private $_data = [];

    function __construct()
    {
        clearstatcache();
        $this->_serverLastModTime = filemtime(self::GetStatusFile());
    }

    public static function GetStatusFile()
    {
        $statsDir = isset($_SERVER['LSWS_STATDIR']) ? $_SERVER['LSWS_STATDIR'] : '/tmp/lshttpd';
        $status = rtrim($statsDir, '/') . '/.status';
        return $status;
    }

    public static function GetLicenseInfo()
    {
        if (($lines = file_get_contents(self::GetStatusFile())) == false)
            return false;

        // LICENSE_EXPIRES: 0, UPDATE_EXPIRES: 1597636800, SERIAL: , TYPE: 2-CPU
        if (preg_match("/^LICENSE_EXPIRES: (\d+), UPDATE_EXPIRES: (\d+), SERIAL: (.+), TYPE: (.+)$/m", $lines, $m)) {
            return array(
                'exp'         => $m[1], 'upd_exp'     => $m[2], 's'           => $m[3], 't'           => $m[4],
                'exp_date'    => (($m[1] == 0) ? 'Never' : date('M d, Y', $m[1])),
                'upd_expdate' => date('M d, Y', $m[2]));
        } else
            return false;
    }

    public static function GetDebugLogState()
    {
        $state = -1; // -1: error, 0: off, 1: on
        if ($lines = file_get_contents(self::GetStatusFile())) {
            if (preg_match("/DEBUG_LOG: ([01]), VERSION: (.+)$/m", $lines, $m)) {
                $state = $m[1];
            }
        }
        return $state;
    }

    public function Set($field, $value)
    {
        $this->_data[$field] = $value;
    }

    public function Get($field)
    {
        switch ($field) {
            case self::FLD_Listener:
                return $this->_listeners;
            case self::FLD_VHosts:
                return $this->_vhosts;
        }
    }

    public function Init($servdata)
    {
        $this->_servData = $servdata;
    }

    public function WaitForChange()
    {
        for ($count = 0; $count < 5; ++$count) {
            if (!$this->checkLastMod())
                sleep(1);
            else
                return true;
        }
        return false;
    }

    private function checkLastMod()
    {
        clearstatcache();
        $mt = filemtime(self::GetStatusFile());
        if ($this->_serverLastModTime != $mt) {
            $this->_serverLastModTime = $mt;
            return true;
        }
        return false;
    }

    public function LoadLog($field)
    {
        $this->_serverLog = PathTool::GetAbsFile($this->_servData->GetChildVal('errorlog'), 'SR');

        if ($field == SInfo::DATA_DASH_LOG)
            $logdata = LogViewer::GetDashErrLog($this->_serverLog);
        else
            $logdata = LogViewer::GetErrLog($this->_serverLog);

        return $logdata;
    }

    public function LoadStatus()
    {
        $this->_listeners = [];
        $this->_adminL = [];
        $root = $this->_servData->GetRootNode();

        if (($lns = $root->GetChildren('listener')) != null) {
            if (!is_array($lns))
                $lns = array($lns);
            foreach ($lns as $l) {
                $listener = array('daddr' => $l->GetChildVal('address')); //defined addr
                if (($maps = $l->GetChildren('vhmap')) != null) {
                    if (!is_array($maps))
                        $maps = array($maps);
                    foreach ($maps as $map) {
                        $vn = $map->Get(CNode::FLD_VAL);
                        $domain = $map->GetChildVal('domain');
                        $listener['map'][$vn] = $domain;
                    }
                }
                $lname = $l->Get(CNode::FLD_VAL);
                $this->_listeners[$lname] = $listener;
            }
        }


        $vhnames = $this->_servData->GetChildrenValues('virtualhost');
        $vhosts = array_fill_keys($vhnames, array('running' => -1));

        if (($tps = $root->GetChildren('vhTemplate')) != null) {
            if (!is_array($tps))
                $tps = array($tps);
            foreach ($tps as $tp) {
                if (($member = $tp->GetChildren('member')) != null) {
                    $tpname = $tp->Get(CNode::FLD_VAL);
                    $initval = array('templ' => $tpname, 'running' => -1);
                    if (is_array($member)) { // cannot use array_merge, will empty the number only keys
                        $tvhnames = array_keys($member);
                        foreach ($tvhnames as $m) {
                            $vhosts[$m] = $initval;
                        }
                    } else {
                        $vhosts[$member->Get(CNode::FLD_VAL)] = $initval;
                    }
                }
            }
        }
        $this->_vhosts = $vhosts;

        if (($lines = file_get_contents(self::GetStatusFile())) == false)
            return false;

        $pos = strpos($lines, "VHOST");
        if ($pos === false)
            return false;

        $listenerlines = explode("\n", substr($lines, 0, $pos - 1));
        $vhoststr = substr($lines, $pos);

        $m = [];
        if ($found = preg_match_all("/^VHOST \[(.+)\] ([01])$/m", $vhoststr, $m)) {
            for ($i = 0; $i < $found; $i++) {
                $vn = $m[1][$i];
                $this->_vhosts[$vn]['running'] = $m[2][$i];
            }
        }

        while (($line = current($listenerlines)) != false) {
            if (substr($line, 0, 3) == 'LIS') {
                // LISTENER0 is regular, LISTENER1 is admin
                if (preg_match("/\[(.+)\] (.+)$/", $line, $m)) {
                    $name = $m[1];
                    $addr = $m[2];
                    while (($lvmap = next($listenerlines)) != 'ENDL') {
                        if (preg_match("/LVMAP \[(.+)\] (.+)$/", $lvmap, $tm)) {
                            $vn = $tm[1];
                            $domain = $tm[2];
                            if (isset($this->_vhosts[$vn])) {
                                if (!isset($this->_vhosts[$vn]['domains']))
                                    $this->_vhosts[$vn]['domains'] = array($domain => $name);
                                elseif (!isset($this->_vhosts[$vn]['domains'][$domain]))
                                    $this->_vhosts[$vn]['domains'][$domain] = $name;
                                else
                                    $this->_vhosts[$vn]['domains'][$domain] .= ' ' . $name;
                            }
                        }
                    }

                    if (strncmp($line, 'LISTENER0', 9) == 0) {
                        $this->_listeners[$name]['addr'] = $addr;
                    } else {
                        $this->_adminL[$name]['addr'] = $addr;
                    }
                }
            }
            next($listenerlines);
        }

        return true;
    }

}
