<?php

class RealTimeStats
{

    const FLD_BPS_IN = 0;
    const FLD_BPS_OUT = 1;
    const FLD_SSL_BPS_IN = 2;
    const FLD_SSL_BPS_OUT = 3;
    const FLD_PLAINCONN = 4;
    const FLD_IDLECONN = 5;
    const FLD_SSLCONN = 6;
    const FLD_S_REQ_PROCESSING = 7;
    const FLD_S_REQ_PER_SEC = 8;
    const FLD_UPTIME = 9;
    const FLD_MAXCONN = 10;
    const FLD_MAXSSL_CONN = 11;
    const FLD_AVAILCONN = 12;
    const FLD_AVAILSSL = 13;
    const FLD_BLOCKEDIP_COUNT = 14;
    const FLD_S_TOT_REQS = 15;
    const COUNT_FLD_SERVER = 16;
    const FLD_BLOCKEDIP = 16;
    //const FLD_VH_NAME = 0;
    const FLD_VH_EAP_INUSE = 0;
    const FLD_VH_EAP_WAITQUE = 1;
    const FLD_VH_EAP_IDLE = 2;
    const FLD_VH_EAP_REQ_PER_SEC = 3;
    const FLD_VH_REQ_PROCESSING = 4;
    const FLD_VH_REQ_PER_SEC = 5;
    const FLD_VH_TOT_REQS = 6;
    const FLD_VH_EAP_COUNT = 7;
    const COUNT_FLD_VH = 8;
    const FLD_EA_CMAXCONN = 0;
    const FLD_EA_EMAXCONN = 1;
    const FLD_EA_POOL_SIZE = 2;
    const FLD_EA_INUSE_CONN = 3;
    const FLD_EA_IDLE_CONN = 4;
    const FLD_EA_WAITQUE_DEPTH = 5;
    const FLD_EA_REQ_PER_SEC = 6;
    const FLD_EA_TOT_REQS = 7;
    const FLD_EA_TYPE = 8;
    const COUNT_FLD_EA = 9;

    private $_serv;
    private $_vhosts;
    private $_rawdata;

    private function __construct()
    {
        $this->_rawdata = '';
        $processes = $_SERVER['LSWS_CHILDREN'];
        $statsDir = isset($_SERVER['LSWS_STATDIR']) ? $_SERVER['LSWS_STATDIR'] : '/tmp/lshttpd';

        $rtrpt = rtrim($statsDir, '/') . '/.rtreport';
        for ($i = 1; $i <= $processes; $i ++) {
            if ($i > 1)
                $this->_rawdata .= "\n" . file_get_contents("{$rtrpt}.{$i}");
            else {
                $this->_rawdata = file_get_contents($rtrpt);
                if ($this->_rawdata == false)
                    break; // fail to open, may due to restart, ignore
            }
        }
    }

    public static function GetDashPlot()
    {
        $stat = new RealTimeStats();
        $stat->parse_server();
        return $stat->_serv;
    }

    public static function GetPlotStats()
    {
        $stat = new RealTimeStats();
        $stat->parse_server();
        $stat->parse_plotvh();
        $stat->_rawdata = '';

        return $stat;
    }

    public static function GetVHStats()
    {
        $stat = new RealTimeStats();
        $stat->parse_vhosts();
        $stat->_rawdata = '';

        return $stat;
    }

    public function GetServerData()
    {
        return $this->_serv;
    }

    public function GetVHData()
    {
        return $this->_vhosts;
    }

    private function parse_server()
    {
        $this->_serv = array_fill(0, self::COUNT_FLD_SERVER, 0);
        //error_log("rawdata = " . $this->_rawdata);

        $m = [];
        if ($found = preg_match_all("/^UPTIME: ([0-9A-Za-z\ \:]+)\nBPS_IN:([0-9\ ]+), BPS_OUT:([0-9\ ]+), SSL_BPS_IN:([0-9\ ]+), SSL_BPS_OUT:([0-9\ ]+)\nMAXCONN:([0-9\ ]+), MAXSSL_CONN:([0-9\ ]+), PLAINCONN:([0-9\ ]+), AVAILCONN:([0-9\ ]+), IDLECONN:([0-9\ ]+), SSLCONN:([0-9\ ]+), AVAILSSL:([0-9\ ]+)/m", $this->_rawdata, $m)) {
            for ($f = 0; $f < $found; $f ++) {
                $this->_serv[self::FLD_UPTIME] = trim($m[1][$f]);
                $this->_serv[self::FLD_BPS_IN] += (int) $m[2][$f];
                $this->_serv[self::FLD_BPS_OUT] += (int) $m[3][$f];
                $this->_serv[self::FLD_SSL_BPS_IN] += (int) $m[4][$f];
                $this->_serv[self::FLD_SSL_BPS_OUT] += (int) $m[5][$f];

                $this->_serv[self::FLD_MAXCONN] += (int) $m[6][$f];
                $this->_serv[self::FLD_MAXSSL_CONN] += (int) $m[7][$f];

                $this->_serv[self::FLD_PLAINCONN] += (int) $m[8][$f];
                $this->_serv[self::FLD_AVAILCONN] += (int) $m[9][$f];
                $this->_serv[self::FLD_IDLECONN] += (int) $m[10][$f];

                $this->_serv[self::FLD_SSLCONN] += (int) $m[11][$f];
                $this->_serv[self::FLD_AVAILSSL] += (int) $m[12][$f];
            }
        }

        $m = [];
        if ($found = preg_match_all("/^BLOCKED_IP: ([0-9 \[\]\.,]*)/m", $this->_rawdata, $m)) {
            $blockedips = [];

            for ($f = 0; $f < $found; $f ++) {
                $ips = trim($m[1][$f]);
                if ($ips != "") {
                    $iplist = preg_split("/[\s,]+/", $ips, -1, PREG_SPLIT_NO_EMPTY);
                    $blockedips = array_merge($blockedips, $iplist);
                }
            }
            //$this->_serv[self::FLD_BLOCKEDIP] = $blockedips;
            $this->_serv[self::FLD_BLOCKEDIP_COUNT] = count($blockedips);
        }


        $m = [];
        if ($found = preg_match_all("/^REQ_RATE \[\]: REQ_PROCESSING: ([0-9]+), REQ_PER_SEC: ([0-9\.]+), TOT_REQS: ([0-9]+)/m", $this->_rawdata, $m)) {
            for ($f = 0; $f < $found; $f ++) {
                $this->_serv[self::FLD_S_REQ_PROCESSING] += (int) $m[1][$f];
                $this->_serv[self::FLD_S_REQ_PER_SEC] += doubleval($m[2][$f]);
                $this->_serv[self::FLD_S_TOT_REQS] += doubleval($m[3][$f]);
            }
        }
    }

    private function parse_plotvh()
    {
        $this->_vhosts = [];

        $vhmonitored = null;
        if (isset($_REQUEST['vhnames']) && is_array($_REQUEST['vhnames']))
            $vhmonitored = $_REQUEST['vhnames'];
        else
            return;

        $vhosts = [];
        $m = [];
        $found = preg_match_all("/REQ_RATE \[(.+)\]: REQ_PROCESSING: ([0-9]+), REQ_PER_SEC: ([0-9\.]+), TOT_REQS: ([0-9]+)/i", $this->_rawdata, $m);
        //$found = preg_match_all("/REQ_RATE \[(.+)\]: REQ_PROCESSING: ([0-9]+), REQ_PER_SEC: ([0-9\.]+), TOT_REQS: ([0-9]+), CACHE_HITS_PER_SEC: ([0-9\.]+), TOTAL_CACHE_HITS: ([0-9]+)/i", $this->_rawdata, $m);

        for ($f = 0; $f < $found; $f ++) {
            $vhname = trim($m[1][$f]);

            if ($vhmonitored != null && !in_array($vhname, $vhmonitored))
                continue;

            if (!isset($vhosts[$vhname])) {
                $vhosts[$vhname] = array_fill(0, self::COUNT_FLD_VH, 0);
                $vhosts[$vhname]['ea'] = [];
            }
            $vh = &$vhosts[$vhname];
            $vh[self::FLD_VH_REQ_PROCESSING] += (int) $m[2][$f];
            $vh[self::FLD_VH_REQ_PER_SEC] += doubleval($m[3][$f]);
            $vh[self::FLD_VH_TOT_REQS] += doubleval($m[4][$f]);
        }

        //reset
        $m = [];
        $found = preg_match_all("/EXTAPP \[(.+)\] \[(.+)\] \[(.+)\]: CMAXCONN: ([0-9]+), EMAXCONN: ([0-9]+), POOL_SIZE: ([0-9]+), INUSE_CONN: ([0-9]+), IDLE_CONN: ([0-9]+), WAITQUE_DEPTH: ([0-9]+), REQ_PER_SEC: ([0-9\.]+), TOT_REQS: ([0-9]+)/i", $this->_rawdata, $m);

        for ($f = 0; $f < $found; $f ++) {
            $vhname = trim($m[2][$f]);
            $extapp = trim($m[3][$f]);

            if ($vhname == '') {
                $vhname = '_Server';
                if (!isset($vhosts[$vhname])) {
                    $vhosts[$vhname] = array_fill(0, self::COUNT_FLD_VH, 0);
                    $vhosts[$vhname]['ea'] = [];
                }
            } else {
                if (!isset($vhosts[$vhname]))
                    continue;
            }

            if (!isset($vhosts[$vhname]['ea'][$extapp])) {
                $vhosts[$vhname][self::FLD_VH_EAP_COUNT] ++;
                $vhosts[$vhname]['ea'][$extapp] = 1;
            }

            $vhosts[$vhname][self::FLD_VH_EAP_INUSE] += (int) $m[7][$f];
            $vhosts[$vhname][self::FLD_VH_EAP_IDLE] += (int) $m[8][$f];
            $vhosts[$vhname][self::FLD_VH_EAP_WAITQUE] += (int) $m[9][$f];
            $vhosts[$vhname][self::FLD_VH_EAP_REQ_PER_SEC] += doubleval($m[10][$f]);
        }

        $this->_vhosts = $vhosts;
    }

    private function parse_vhosts()
    {
        $this->_vhosts = [];

        $top = UIBase::GrabGoodInput("request", "vh_topn", 'int');
        $filter = UIBase::GrabGoodInput("request", "vh_filter", "string");
        $sort = UIBase::GrabGoodInput("request", "vh_sort", "int");

        $vhosts = [];
        $m = [];
        $found = preg_match_all("/REQ_RATE \[(.+)\]: REQ_PROCESSING: ([0-9]+), REQ_PER_SEC: ([0-9\.]+), TOT_REQS: ([0-9]+)/i", $this->_rawdata, $m);

        for ($f = 0; $f < $found; $f ++) {
            $vhname = trim($m[1][$f]);

            if ($filter != "" && (!preg_match("/$filter/i", $vhname)))
                continue;

            if (!isset($vhosts[$vhname])) {
                $vhosts[$vhname] = array_fill(0, 10, 0);
                $vhosts[$vhname]['ea'] = [];
            }
            $vh = &$vhosts[$vhname];
            $vh[self::FLD_VH_REQ_PROCESSING] += (int) $m[2][$f];
            $vh[self::FLD_VH_REQ_PER_SEC] += doubleval($m[3][$f]);
            $vh[self::FLD_VH_TOT_REQS] += doubleval($m[4][$f]);
        }

        //reset
        $m = [];
        $found = preg_match_all("/EXTAPP \[(.+)\] \[(.+)\] \[(.+)\]: CMAXCONN: ([0-9]+), EMAXCONN: ([0-9]+), POOL_SIZE: ([0-9]+), INUSE_CONN: ([0-9]+), IDLE_CONN: ([0-9]+), WAITQUE_DEPTH: ([0-9]+), REQ_PER_SEC: ([0-9\.]+), TOT_REQS: ([0-9]+)/i", $this->_rawdata, $m);

        for ($f = 0; $f < $found; $f ++) {
            $vhname = trim($m[2][$f]);
            $extapp = trim($m[3][$f]);

            if ($vhname == '') {
                $vhname = '_Server';
                if (!isset($vhosts[$vhname])) {
                    $vhosts[$vhname] = array_fill(0, 10, 0);
                    $vhosts[$vhname]['ea'] = [];
                }
            } else {
                if (!isset($vhosts[$vhname]))
                    continue;
            }

            if (!isset($vhosts[$vhname]['ea'][$extapp])) {
                $vhosts[$vhname][self::FLD_VH_EAP_COUNT] ++;
                $vhosts[$vhname]['ea'][$extapp] = array_fill(0, 8, 0);
            }

            $ea = &$vhosts[$vhname]['ea'][$extapp];
            $ea[self::FLD_EA_TYPE] = trim($m[1][$f]);
            $ea[self::FLD_EA_CMAXCONN] += (int) $m[4][$f];
            $ea[self::FLD_EA_EMAXCONN] += (int) $m[5][$f];
            $ea[self::FLD_EA_POOL_SIZE] += (int) $m[6][$f];
            $ea[self::FLD_EA_INUSE_CONN] += (int) $m[7][$f];
            $ea[self::FLD_EA_IDLE_CONN] += (int) $m[8][$f];
            $ea[self::FLD_EA_WAITQUE_DEPTH] += (int) $m[9][$f];
            $ea[self::FLD_EA_REQ_PER_SEC] += doubleval($m[10][$f]);
            $ea[self::FLD_EA_TOT_REQS] += doubleval($m[11][$f]);

            $vhosts[$vhname][self::FLD_VH_EAP_INUSE] += (int) $m[7][$f];
            $vhosts[$vhname][self::FLD_VH_EAP_IDLE] += (int) $m[8][$f];
            $vhosts[$vhname][self::FLD_VH_EAP_WAITQUE] += (int) $m[9][$f];
            $vhosts[$vhname][self::FLD_VH_EAP_REQ_PER_SEC] += doubleval($m[10][$f]);
        }

        $sortDesc1 = [];
        $sortAsc2 = [];
        $names = array_keys($vhosts);
        if ($sort != "" && count($names) > 1) {
            foreach ($names as $vhname) {
                if ($vhosts[$vhname][$sort] > 0) {
                    $sortDesc1[] = $vhosts[$vhname][$sort];
                    $sortAsc2[] = $vhname;
                }
            }
            if (count($sortAsc2) > 0) {
                array_multisort($sortDesc1, SORT_DESC, SORT_NUMERIC, $sortAsc2, SORT_ASC, SORT_STRING);
                $names = $sortAsc2;
            }
        }

        if ($top != 0 && count($names) > $top) {
            $names = array_slice($names, 0, $top);
        }

        foreach ($names as $vn) {
            $this->_vhosts[$vn] = $vhosts[$vn];
        }
    }

}
