<?php

if ( $_GET['id'] == 'pid_load' ) {
    // do not update timeout stamp
    define('NO_UPDATE_ACCESS', 1) ;
}

require_once('inc/auth.php') ;

function ajax_pid_load()
{
    $data = array( 'pid' => Service::ServiceData(SInfo::DATA_PID),
        'serverload' => implode(', ', sys_getloadavg()) ) ;
    echo json_encode($data) ;
}

function ajax_dashstat()
{
    $d = RealTimeStats::GetDashPlot() ;
    echo json_encode($d) ;
}

function ajax_plotstat()
{
    $stat = RealTimeStats::GetPlotStats() ;

    $d = $stat->GetServerData() ;
    $vhd = $stat->GetVHData() ;

    $s = '{"serv":' . json_encode($d) ;

    foreach ( $vhd as $vn => $vh ) {
        unset($vh['ea']) ;
        $s .= ', "' . $vn . '":' . json_encode($vh) ;
    }

    $s .= '}' ;

    echo $s ;
}

function ajax_vhstat()
{
    $stat = RealTimeStats::GetVHStats() ;
    $vhd = $stat->GetVHData() ;

    $vbody = '' ;
    $ebody = '' ;
    $td = '</td><td>' ;

    foreach ( $vhd as $vn => $vh ) {
        $vbody .= '<tr><td><span class="btn btn-default btn-xs txt-color-blueLight" data-lstmonitor="vh">
				<i class="fa fa-stethoscope"></i></span></td><td class="lst-vhname">' . $vn
                . $td . $vh[RealTimeStats::FLD_VH_REQ_PROCESSING]
                . $td . $vh[RealTimeStats::FLD_VH_REQ_PER_SEC]
                . $td . $vh[RealTimeStats::FLD_VH_TOT_REQS]
                . $td . $vh[RealTimeStats::FLD_VH_EAP_COUNT]
                . $td . $vh[RealTimeStats::FLD_VH_EAP_INUSE]
                . $td . $vh[RealTimeStats::FLD_VH_EAP_IDLE]
                . $td . $vh[RealTimeStats::FLD_VH_EAP_WAITQUE]
                . $td . $vh[RealTimeStats::FLD_VH_EAP_REQ_PER_SEC]
                . "</td></tr>" ;

        if ( isset($vh['ea']) && count($vh['ea']) > 0 ) {
            foreach ( $vh['ea'] as $appname => $ea ) {
                $ebody .= '<tr><td>' . $vn
                        . $td . $ea[RealTimeStats::FLD_EA_TYPE]
                        . $td . $appname
                        . $td . $ea[RealTimeStats::FLD_EA_CMAXCONN]
                        . $td . $ea[RealTimeStats::FLD_EA_EMAXCONN]
                        . $td . $ea[RealTimeStats::FLD_EA_POOL_SIZE]
                        . $td . $ea[RealTimeStats::FLD_EA_INUSE_CONN]
                        . $td . $ea[RealTimeStats::FLD_EA_IDLE_CONN]
                        . $td . $ea[RealTimeStats::FLD_EA_WAITQUE_DEPTH]
                        . $td . $ea[RealTimeStats::FLD_EA_REQ_PER_SEC]
                        . $td . $ea[RealTimeStats::FLD_EA_TOT_REQS]
                        . "</td></tr>" ;
            }
        }
    }
    $data = array( 'vbody' => $vbody, 'ebody' => $ebody ) ;

    echo json_encode($data) ;
}

function ajax_dashstatus()
{
    $sinfo = Service::ServiceData(SInfo::DATA_Status_LV) ;
    $listeners = $sinfo->Get(SInfo::FLD_Listener) ;

    $body = '' ;
    $running = 0 ;
    $broken = '' ;
    foreach ( $listeners as $lname => $l ) {
        $body .= '<tr><td class="' ;
        if ( isset($l['addr']) ) {
            $body .= 'success"><i class="fa fa-link"></i>' ;
            $running ++ ;
            $addr = $l['addr'] ;
        }
        else {
            $body .= 'danger"><i class="fa fa-unlink"></i>' ;
            $broken ++ ;
            $addr = $l['daddr'] ;
        }
        $body .= '</td><td>' . $lname . ' </td><td>' . $addr
                . '</td></tr>' . "\n" ;
    }

    $vhosts = $sinfo->Get(SInfo::FLD_VHosts) ;
    $vrunning = 0 ;
    $vdisabled = '' ;
    $verrors = '' ;

    $vbody = '' ;

    $note_stopped = DMsg::ALbl('service_stopped') ;
    $note_running = DMsg::ALbl('service_running') ;
    $note_suspendvh = DMsg::ALbl('service_suspendvh') ;
    $note_enablevh = DMsg::ALbl('service_enablevh') ;
    $note_disabled = DMsg::ALbl('service_disabled') ;

    foreach ( $vhosts as $vn => $vh ) {
        $vbody .= '<tr data-vn="' . $vn . '"><td>' ;

        if ( $vh['running'] == -1 ) {
            $verrors ++ ;
            $vbody .= '<span class="text-danger" title="' . $note_stopped . '"><i class="fa fa-ban"></i></span> ' ;
            $actions = '' ;
        }
        elseif ( $vh['running'] == 1 ) {
            $vrunning ++ ;
            $vbody .= '<span class="text-success" title="' . $note_running . '"><i class="fa fa-rocket"></i></span> ' ;
            $actions = '<a class="btn btn-warning btn-xs" data-action="lstvhcontrol" data-lstact="disable" title="'
                    . $note_suspendvh . '"><i class="fa fa-pause"></i></a>' ;
        }
        else {
            $vdisabled ++ ;
            $vbody .= '<span class="text-warning" title="' . $note_disabled . '"><i class="fa fa-stop"></i></span> ' ;
            $actions = '<a class="btn btn-success btn-xs"  data-action="lstvhcontrol" data-lstact="enable" title="'
                    . $note_enablevh . '"><i class="fa fa-play"></i></a>' ;
        }
        $vbody .= '</td><td>' . htmlspecialchars(wordwrap($vn, 40, "\n", true)) . '</td><td>' ;
        if ( isset($vh['templ']) )
            $vbody .= $vh['templ'] ;
        $vbody .= '</td><td>' ;
        if ( isset($vh['domains']) ) {
            $vbody .= htmlspecialchars(wordwrap(implode("\n", array_keys($vh['domains'])), 60, "\n", true)) ;
        }
        $vbody .= '</td><td>' ;
        $vbody .= $actions ;
        $vbody .= '</td></tr>' ;
    }

    $res = array( 'l_running' => $running,
        'l_broken' => $broken,
        'v_running' => $vrunning,
        'v_disabled' => $vdisabled,
        'v_err' => $verrors,
        'l_body' => $body,
        'v_body' => $vbody
            ) ;

    echo json_encode($res) ;
}

function ajax_dashlog()
{
    $logfilter = Service::ServiceData(SInfo::DATA_DASH_LOG) ;
    $debug = Service::ServiceData(SInfo::DATA_DEBUGLOG_STATE) ;

    $res = array( 'debuglog' => $debug,
        'logfound' => $logfilter->Get(LogFilter::FLD_TOTALFOUND),
        'logfoundmesg' => $logfilter->Get(LogFilter::FLD_OUTMESG),
        'log_body' => $logfilter->GetLogOutput() ) ;
    echo json_encode($res) ;
}

function ajax_viewlog()
{
    $logfilter = Service::ServiceData(SInfo::DATA_VIEW_LOG) ;

    $res = array( 'logfound' => $logfilter->Get(LogFilter::FLD_TOTALFOUND),
        'logfoundmesg' => $logfilter->Get(LogFilter::FLD_OUTMESG),
        'cur_log_file' => $logfilter->Get(LogFilter::FLD_LOGFILE),
        'cur_log_size' => $logfilter->Get(LogFilter::FLD_FILE_SIZE),
        'sellevel' => $logfilter->Get(LogFilter::FLD_LEVEL),
        'startpos' => $logfilter->Get(LogFilter::FLD_FROMPOS),
        'blksize' => $logfilter->Get(LogFilter::FLD_BLKSIZE),
        'log_body' => $logfilter->GetLogOutput() ) ;

    echo json_encode($res) ;
}

function ajax_downloadlog()
{
    $file = UIBase::GrabGoodInput('get', 'filename') ;

    if ( file_exists($file) ) {
        if ( ob_get_level() ) {
            ob_end_clean() ;
        }
        header('Content-Description: File Transfer') ;
        header('Content-Type: application/octet-stream') ;
        header('Content-Disposition: attachment; filename=' . basename($file)) ;
        header('Expires: 0') ;
        header('Cache-Control: must-revalidate') ;
        header('Pragma: public') ;
        header('Content-Length: ' . filesize($file)) ;
        readfile($file) ;
        exit ;
    }
    else {
        error_log("download log $file not exist") ;
    }
}

function ajax_buildprogress()
{
    $progress_file = $_SESSION['progress_file'] ;
    $log_file = $_SESSION['log_file'] ;

    echo file_get_contents($progress_file) ;

    echo "\n**LOG_DETAIL** retrieved from $log_file\n" ;
    echo file_get_contents($log_file) ;
}

$id = UIBase::GrabGoodInput('get', 'id') ;
$supported = array( 'dashstat', 'plotstat', 'vhstat', 'dashstatus', 'pid_load',
    'dashlog', 'viewlog', 'downloadlog', 'buildprogress' ) ;

if ( in_array($id, $supported) ) {
    $func = "ajax_$id" ;
    $func() ;
}
else {
    error_log("invalid action ajax_data id = $id") ;
}

