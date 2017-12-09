<?php

/*----------------------------------------
LiteSpeed_Stats class and subclasses. Parse Real-Time data for LiteSpeed Products

Copyright (C) 2006 LiteSpeed Technologies, Inc.
This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

Version: 1.0 @ 08/23/2006
Contact: bug@litespeedtech.com
Url: http://www.litespeedtech.com

Requirement:

1)LiteSpeed Web Server version >= 2.1.18
2)PHP 5+
----------------------------------------*/

class litespeed_stats
{
    public $product = null;
    public $edition = null;
    public $version = null;
    public $uptime = null;

    public $bps_in = 0;
    public $bps_out = 0;
    public $ssl_bps_in = 0;
    public $ssl_bps_out = 0;

    public $max_conn = 0;
    public $max_ssl_conn = 0;

    public $plain_conn = 0;
    public $avail_conn = 0;
    public $idle_conn = 0;

    public $ssl_conn = 0;
    public $avail_ssl_conn = 0;

    public $vhosts = array();

    //misc settings

    //full path to .rtreports files. different products have different paths
    public $report_path = "/tmp/lshttpd/";

    //processes..enterprise version can spawn proccess = cpu cores
    public $processes = 1;

    public function __construct($processes = 1, $report_path = "/tmp/lshttpd/")
    {
        $this->processes = (int) $processes;
        $this->report_path = trim($report_path);
    }

    public function parse()
    {
        for ( $i = 1 ; $i <= $this->processes ; $i++ )
        {
            if ( $i > 1 ) {
                $content = file_get_contents("{$this->report_path}.rtreport.{$i}");
            } else {
                $content = file_get_contents("{$this->report_path}.rtreport");
            }

            $result = array();

            $found = 0;

            $found = preg_match_all("/VERSION: ([a-zA-Z0-9\ ]+)\/([a-zA-Z]*)\/([a-zA-Z0-9\.]+)\nUPTIME: ([0-9A-Za-z\ \:]+)\nBPS_IN:([0-9\ ]+), BPS_OUT:([0-9\ ]+), SSL_BPS_IN:([0-9\ ]+), SSL_BPS_OUT:([0-9\ ]+)\nMAXCONN:([0-9\ ]+), MAXSSL_CONN:([0-9\ ]+), PLAINCONN:([0-9\ ]+), AVAILCONN:([0-9\ ]+), IDLECONN:([0-9\ ]+), SSLCONN:([0-9\ ]+), AVAILSSL:([0-9\ ]+)/i", $content, $result);

            if($found == 1) {
                $this->product = trim($result[1][0]);
                $this->edition = trim($result[2][0]);
                $this->version = trim($result[3][0]);
                $this->uptime = trim($result[4][0]);
                $this->bps_in += (int) $result[5][0];
                $this->bps_out += (int) $result[6][0];
                $this->ssl_bps_in += (int) $result[7][0];
                $this->ssl_bps_out += (int) $result[8][0];

                $this->max_conn += (int) $result[9][0];
                $this->max_ssl_conn += (int) $result[10][0];

                $this->plain_conn += (int) $result[11][0];
                $this->avail_conn += (int) $result[12][0];
                $this->idle_conn += (int) $result[13][0];

                $this->ssl_conn += (int) $result[14][0];
                $this->avail_ssl_conn += (int) $result[15][0];
            }

            $result = array();
            $found = 0;

            $found = preg_match_all("/REQ_RATE \[([^\]]*)\]: REQ_PROCESSING: ([0-9]+), REQ_PER_SEC: ([0-9]+), TOT_REQS: ([0-9]+)/i",$content,$result);

            for($f = 0; $f < $found; $f++) {
                $vhost = trim($result[1][$f]);

                if($vhost == "") {
                    $vhost = "_Server";
                }

                if(!array_key_exists($vhost,$this->vhosts)) {
                    $this->vhosts[$vhost] = new litespeed_stats_vhost($vhost);
                }

                $temp = $this->vhosts[$vhost];

                $temp->req_processing += (int) $result[2][$f];
                $temp->req_per_sec += (int) $result[3][$f];
                $temp->req_total += (int) $result[4][$f];
            }

            //reset
            $result = array();
            $found = 0;

            $found = preg_match_all("/EXTAPP \[([^\]]*)\] \[([^\]]*)\] \[([^\]]*)\]: CMAXCONN: ([0-9]+), EMAXCONN: ([0-9]+), POOL_SIZE: ([0-9]+), INUSE_CONN: ([0-9]+), IDLE_CONN: ([0-9]+), WAITQUE_DEPTH: ([0-9]+), REQ_PER_SEC: ([0-9]+), TOT_REQS: ([0-9]+)/i",$content,$result);

            for($f = 0; $f < $found; $f++) {
                $vhost = trim($result[2][$f]);
                $extapp = trim($result[3][$f]);

                if($vhost == "") {
                    $vhost = "_Server";
                }

                if(!array_key_exists($vhost,$this->vhosts)) {
                    $this->vhosts[$vhost] = new litespeed_stats_vhost($vhost);
                }

                if(!array_key_exists($extapp,$this->vhosts[$vhost]->extapps)) {
                    $this->vhosts[$vhost]->extapps[$extapp] = new litespeed_stats_vhost_extapp($extapp, $vhost);
                }

                $temp = $this->vhosts[$vhost]->extapps[$extapp];

                $temp->type = trim($result[1][$f]);
                $temp->config_max_conn += (int) $result[4][$f];
                $temp->effect_max_conn += (int) $result[5][$f];
                $temp->pool_size += (int) $result[6][$f];
                $temp->inuse_conn += (int) $result[7][$f];
                $temp->idle_conn += (int) $result[8][$f];
                $temp->waitqueue_depth += (int) $result[9][$f];
                $temp->req_per_sec += (int) $result[10][$f];
                $temp->req_total += (int) $result[11][$f];
            }
        }
    }
}

class liteSpeed_stats_vhost
{
    public $vhost = null;
    public $req_processing = 0;
    public $req_per_sec = 0;
    public $req_total = 0;
    public $extapps = array();

    public function __construct($vhost = null)
    {
        $this->vhost = trim($vhost);
    }
}

class litespeed_stats_vhost_extapp
{
    public function __construct($extapp = null, $vhost = null)
    {
        $this->extapp = trim($extapp);
        $this->vhost = trim($vhost);
    }

    public $vhost = null;
    public $type = null;
    public $extapp = null;
    public $config_max_conn = 0;
    public $effect_max_conn = 0;
    public $pool_size = 0;
    public $inuse_conn = 0;
    public $idle_conn = 0;
    public $waitqueue_depth = 0;
    public $req_per_sec = 0;
    public $req_total = 0;
}
