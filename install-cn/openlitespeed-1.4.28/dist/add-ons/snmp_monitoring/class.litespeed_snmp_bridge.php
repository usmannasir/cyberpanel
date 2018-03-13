<?php

/*----------------------------------------
LiteSpeed_Stats to SNMP bridge. Relay stats to SNMPD.

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

require_once("class.litespeed_stats.php");

class litespeed_snmp_bridge
{
    public $processes = 1;
    public $report_path = "/tmp/lshttpd/";
    public $cache_time = 0;
    public $cache_file = null;
    public $stats = null;

    public function __construct($processes = 1, $report_path = "/tmp/lshttpd/", $cache_time = 0, $cache_file = null)
    {
        $this->processes = (int) $processes;
        $this->report_path = trim($report_path);

        //prepare parser
        if($this->cache_time > 0 && strlen($this->cache_file) > 0) {
            if(file_exists($this->cache_file) && time() - filemtime($this->cache_file) <= $this->cache_time) {
                $unserial = unserialize(file_get_contents($this->cache_file));

                if(is_a($unserial,"litespeed_stats")) {
                    $this->stats = $unserial;
                } else {
                    $this->stats = new litespeed_stats($this->processes,$this->report_path);
                    $this->stats->parse();
                    $this->save_cache($this->cache_file, $this->stats);
                }
            } else {
                $this->stats = new litespeed_stats($this->processes,$this->report_path);
                $this->stats->parse();
                $this->save_cache($this->cache_file, $this->stats);
            }
        } else {
            $this->stats = new litespeed_stats($this->processes,$this->report_path);
            $this->stats->parse();
        }
    }

    //generate snmp compatible response
    public function format_response($oid, $type, $data)
    {
        return "{$oid}\n{$type}\n{$data}\n";
    }

    //aggregate oid info from 1 to 7 sector
    public function oid_part($tarray = null)
    {
        $str = "";
        for($i=1; $i <= 7; $i++) {
            $str .= "." . $tarray[$i];
        }

        return $str;
    }

    //retrieve single oid data
    public function oid_get($super, $oid)
    {
        $parsed = explode(".",$oid);

        //error..invalid oid parse
        if(count($parsed) < 9) {
            return;
        }

        $major = (int) $parsed[8];

        if(count($parsed) < 10) {
            $minor = 1;
        } else {
            $minor =  (int) $parsed[9];
        }

        foreach($super as $key => $value) {
            $sanitized_major = (int) substr($major,0,1) . "00";

            //index only
            if( $major == (int) $key ) {
                return $this->format_response($this->oid_part($parsed) . "." . $major . "." . $minor,"integer",$minor);

            }

            //non-index value
            if( $sanitized_major == (int) $key) {
                $size = count($value[0]);

                $map = $value[1];

                if($size <= 0) {
                    return null;
                }

                if(count($parsed) == 10) {
                    if($minor > 0 && $minor <= $size) {
                        $tempkeys = array_keys($value[0]);
                        $temp = $value[0][$tempkeys[$minor-1]];
                        list($format,$itemkey) = explode(",",$value[1][$major]);

                        return $this->format_response($oid, $format, $temp->$itemkey);
                    }
                }
            }
        }
    }

    public function save_cache($file, $data)
    {
        file_put_contents($file, serialize($data));
    }

    public function process($type, $oid)
    {
        //setup oid to var maps
        $vh_map = array(
            "201" => "string,vhost",
            "202" => "gauge,req_processing",
            "203" => "gauge,req_per_sec",
            "204" => "counter,req_total"
        );

        $ext_map = array(
            "301" => "string,vhost",
            "302" => "string,type",
            "303" => "string,extapp",
            "304" => "gauge,config_max_conn",
            "305" => "gauge,effect_max_conn",
            "306" => "gauge,pool_size",
            "307" => "gauge,inuse_conn",
            "308" => "gauge,idle_conn",
            "309" => "gauge,waitqueue_depth",
            "310" => "gauge,req_per_sec",
            "311" => "counter,req_total"
        );

        $gen_map = array(
            "101" => "string,product",
            "102" => "string,edition",
            "103" => "string,version",
            "104" => "string,uptime",
            "105" => "gauge,bps_in",
            "106" => "gauge,bps_out",
            "107" => "gauge,ssl_bps_in",
            "108" => "gauge,ssl_bps_out",
            "109" => "gauge,max_conn",
            "110" => "gauge,max_ssl_conn",
            "111" => "gauge,plain_conn",
            "112" => "gauge,avail_conn",
            "113" => "gauge,idle_conn",
            "114" => "gauge,ssl_conn",
            "115" => "gauge,avail_ssl_conn"
        );

        //setup pointers
        $super = array();
        $super["100"] = array(array($this->stats), $gen_map);
        $super["200"] = array($this->stats->vhosts, $vh_map);

        //put alll extapps to single array
        $extapps = array();
        foreach($this->stats->vhosts as $value) {
            foreach($value->extapps as $vextapp) {
                $extapps[] = $vextapp;
            }
        }

        $super["300"] = array($extapps, $ext_map);

        //get single method
        if($type == "-g") {
            echo $this->oid_get($super, $oid);
            return;
        } else if($type == "-n") {
            //snmp walk traversal
            //build traversal nodes/oids
            $parsed = explode(".",$oid);
            $major = $parsed[8];

            foreach($super as $key => $value) {
                //form index walk
                if($major == $key) {
                    $size = count($value[0]);

                    if($size <= 0) {
                        return;
                    }

                    if(count($parsed) == 10) {
                        $minor = (int) $parsed[9];

                        if($minor > 0 && $minor < $size) {
                            echo $this->format_response($this->oid_part($parsed).".{$key}.".($minor+1),"integer",$minor+1);

                        }
                    } else if(count($parsed) == 9) {
                        echo $this->format_response("{$oid}.1","integer",1);
                    }

                } else if(array_key_exists($major,$value[1])) {
                    //data walk
                    $size = count($value[0]);

                    if($size <= 0) {
                        return;
                    }

                    if(count($parsed) == 10) {
                        $minor = (int) $parsed[9];

                        if($minor > 0 && $minor < $size) {
                            echo $this->oid_get($super, $this->oid_part($parsed).".{$major}.".($minor+1));
                        }
                    } else if(count($parsed) == 9){
                        echo $this->oid_get($super, $this->oid_part($parsed).".{$major}.".(1));
                    }
                }
            }
        }
    }
}
