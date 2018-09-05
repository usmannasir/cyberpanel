<?php

class LogFilter
{

    const LOGTYPE_ERRLOG = 1;
    const LOGTYPE_ACCESS = 2;
    const LOGTYPE_RESTART = 3;

    //'E' => 1, 'W' => 2, 'N' => 3, 'I' => 4, 'D' => 5

    private $LEVEL_DESCR = array(1 => 'ERROR', 2 => 'WARNING', 3 => 'NOTICE', 4 => 'INFO', 5 => 'DEBUG');

    const LEVEL_ERR = 1;
    const LEVEL_WARN = 2;
    const LEVEL_NOTICE = 3;
    const LEVEL_INFO = 4;
    const LEVEL_DEBUG = 5;
    const POS_FILEEND = -1;
    const FLD_LEVEL = 1;
    const FLD_LOGFILE = 2;
    const FLD_FROMINPUT = 3;
    const FLD_BLKSIZE = 4;
    const FLD_FROMPOS = 5;
    const FLD_TOPOS = 6;
    const FLD_TOTALSEARCHED = 7;
    const FLD_OUTMESG = 8;
    const FLD_TOTALFOUND = 9;
    const FLD_FILE_SIZE = 10;

    private $_logfile;
    private $_logtype;
    private $_level;
    private $_frominput;
    private $_blksize;
    private $_frompos;
    private $_topos;
    private $_filesize;
    private $_output = '';
    private $_outlines = 0;
    private $_totallines = 0;
    private $_outmesg = '';

    function __construct($filename, $type = self::LOGTYPE_ERRLOG)
    {
        $this->_logfile = $filename;
        $this->_logtype = $type;
    }

    function Get($field)
    {
        switch ($field) {
            case self::FLD_LEVEL: return $this->_level;
            case self::FLD_LOGFILE: return $this->_logfile;
            case self::FLD_FROMPOS: return number_format($this->_frompos / 1024, 2);
            case self::FLD_FROMINPUT: return $this->_frominput;
            case self::FLD_BLKSIZE: return $this->_blksize;
            case self::FLD_OUTMESG:
                $repl = array('%%totallines%%' => number_format($this->_totallines),
                    '%%outlines%%'   => number_format($this->_outlines),
                    '%%level%%'      => $this->LEVEL_DESCR[$this->_level]
                );
                return DMsg::UIStr('service_logresnote', $repl) . ' ' . $this->_outmesg;
            case self::FLD_TOTALFOUND: return $this->_outlines;
            case self::FLD_FILE_SIZE: return number_format($this->_filesize / 1024, 2);

            default: die("Illegal entry! field = $field");
        }
    }

    function GetLogOutput()
    {
        return $this->_output;
    }

    function AddLogEntry($level, $time, $message)
    {
        $this->_outlines ++;
        $buf = '<tr><td>' . $time . '</td><td';
        switch ($level) {
            case LogFilter::LEVEL_ERR:
                $buf .= ' class="danger">ERROR';
                break;
            case LogFilter::LEVEL_WARN:
                $buf .= ' class="warning">WARN';
                break;
            case LogFilter::LEVEL_NOTICE:
                $buf .= ' class="info">NOTICE';
                break;
            case LogFilter::LEVEL_INFO:
                $buf .= '>INFO';
                break;
            default: $buf .= '>DEBUG';
        }
        $buf .= '</td><td>' . $message . '</td></tr>' . "\n";
        $this->_output .= $buf;
    }

    function Set($field, $value)
    {
        switch ($field) {
            case self::FLD_LEVEL: $this->_level = $value;
                break;
            case self::FLD_FROMPOS: $this->_frompos = $value;
                break;
            case self::FLD_FROMINPUT: $this->_frominput = $value;
                break;
            case self::FLD_TOPOS: $this->_topos = $value;
                break;
            case self::FLD_TOTALSEARCHED: $this->_totallines = $value;
                break;
            case self::FLD_FILE_SIZE: $this->_filesize = $value;
                break;
        }
    }

    function SetRange($from, $size)
    {
        if ($from < 0)
            $from = 0;
        $this->_frominput = $from;
        $this->_blksize = $size;
        $this->_output = '';
    }

    function SetMesg($mesg)
    {
        $this->_outmesg = $mesg;
    }

}

class LogViewer
{

    public static function GetDashErrLog($errorlogfile)
    {
        $filter = new LogFilter($errorlogfile);
        $filter->Set(LogFilter::FLD_LEVEL, LogFilter::LEVEL_NOTICE);
        $filter->SetRange(LogFilter::POS_FILEEND, 20);
        self::loadErrorLog($filter);
        return $filter;
    }

    public static function GetErrLog($errorlogfile)
    {
        // get from input
        $filename = UIBase::GrabGoodInput('any', 'filename');
        if ($filename == '')
            return self::GetDashErrLog($errorlogfile);

        // todo: validate
        $level = UIBase::GrabGoodInput('ANY', 'sellevel', 'int');
        $startinput = UIBase::GrabGoodInput('any', 'startpos', 'float');
        $block = UIBase::GrabGoodInput('any', 'blksize', 'float');
        $act = UIBase::GrabGoodInput('any', 'act');


        switch ($act) {
            case 'begin':
                $startinput = 0;
                break;
            case 'end':
                $startinput = LogFilter::POS_FILEEND;
                break;
            case 'prev':
                $startinput -= $block;
                break;
            case 'next':
                $startinput += $block;
                break;
        }

        $filter = new LogFilter($filename);

        $filter->Set(LogFilter::FLD_LEVEL, $level);
        $filter->SetRange($startinput, $block);
        $filter->SetMesg('');
        self::loadErrorLog($filter);
        return $filter;
    }

    private static function loadErrorLog($filter)
    {
        $logfile = $filter->Get(LogFilter::FLD_LOGFILE);
        if (($fd = fopen($logfile, 'r')) == false) {
            $filter->SetMesg(DMsg::Err('err_failreadfile') . ': ' . $filter->Get(LogFilter::FLD_LOGFILE));
            return;
        }

        $frominput = $filter->Get(LogFilter::FLD_FROMINPUT);

        $block = $filter->Get(LogFilter::FLD_BLKSIZE) * 1024;
        $file_size = filesize($logfile);
        $filter->Set(LogFilter::FLD_FILE_SIZE, $file_size);

        $frompos = ($frominput == LogFilter::POS_FILEEND) ? ($file_size - $block) : ($frominput * 1024);
        if ($frompos < 0) {
            $frompos = 0;
            $endpos = $file_size;
        } else {
            $endpos = $frompos + $block;
        }

        fseek($fd, $frompos);
        $filter->Set(LogFilter::FLD_FROMPOS, $frompos);

        $found = false;
        $totalLine = 0;

        $newlineTag = '[ERR[WAR[NOT[INF[DEB';
        $levels = array('E' => 1, 'W' => 2, 'N' => 3, 'I' => 4, 'D' => 5);
        $filterlevel = $filter->Get(LogFilter::FLD_LEVEL);

        $cur_level = '';
        $cur_time = '';
        $cur_mesg = '';

        while ($buffer = fgets($fd)) {
            // check if new line
            $c28 = substr($buffer, 28, 3);
            if ($c28 && strstr($newlineTag, $c28)) {
                // is new line
                $totalLine ++;
                if ($found) { // finish prior line
                    $filter->AddLogEntry($cur_level, $cur_time, $cur_mesg);
                    $found = false;
                }
                $cur_level = $levels[$c28{0}];
                if ($cur_level <= $filterlevel && preg_match("/^\d{4}-\d{2}-\d{2} /", $buffer)) {
                    // start a new line
                    $found = true;
                    $cur_time = substr($buffer, 0, 26);
                    $cur_mesg = htmlspecialchars(substr($buffer, strpos($buffer, ']', 27) + 2));
                }
            } elseif ($found) { // multi-line output
                $cur_mesg .= '<br>' . htmlspecialchars($buffer);
            }

            $curpos = ftell($fd);
            if ($curpos >= $endpos)
                break;
        }

        fclose($fd);
        if ($found)
            $filter->AddLogEntry($cur_level, $cur_time, $cur_mesg);

        $filter->Set(LogFilter::FLD_TOTALSEARCHED, $totalLine);
    }

}
