<?php

class RawFiles
{
    private $_list = [];
    // list of obj (name, level, fid, dir, fullpath)

    private $_errs = [];
    private $_fatal = 0;

    public function GetFullFileName($fid)
    {
        return $this->_list[$fid][4];
    }

    public function AddRawFile($node)
    {
        $filename = $node->Get(CNode::FLD_VAL);
        $index = count($this->_list);
        $parentid = $index - 1;
        $level = ($index > 0) ? $this->_list[$parentid][1] + 1 : 0;
        $fullpath = $filename;
        if ($filename{0} != '/') {
            if ($parentid) {
                $fullpath = $this->_list[$parentid][3] . '/' . $filename;
            } else {
                $fullpath = SERVER_ROOT . '/conf/' . $fullpath;
            }
        }
        $dir = dirname($fullpath);

        $this->_list[$index] = array($filename, $level, $index, $dir, $fullpath); // list of obj (name, level, fid, dir, fullpath)

        return $index;
    }

    public function MarkError($node, $errlevel, $errmsg)
    {
        $node->SetErr($errmsg, $errlevel);
        $this->_errs[] = array($errlevel, $errmsg, $node->Get(CNode::FLD_FID), $node->Get(CNode::FLD_FLFROM), $node->Get(CNode::FLD_FLTO));
        if ($errlevel == CNode::E_FATAL)
            $this->_fatal ++;
    }

    public function HasFatalErr()
    {
        return ($this->_fatal > 0);
    }

    public function HasErr()
    {
        return (count($this->_errs) > 0);
    }

    public function GetAllErrors()
    {
        $level = array(CNode::E_WARN => 'WARN', CNode::E_FATAL => 'FATEL');

        $buf = "\nShow Errors: \n";
        foreach ($this->errs as $e) {
            $errlevel = $level[$e[0]];
            $filename = $_list[$e[2]]->filename;
            $buf .= "$errlevel $filename line $e[3]";
            if ($e[3] != $e[4])
                $buf .= " ~ $e[4]";
            $buf .= ": $e[1]\n";
        }
        return $buf;
    }

}

class PlainConfParser
{
    public function __construct()
    {
    }

    public function Parse($filename)
    {
        $root = new CNode(CNode::K_ROOT, $filename, CNode::T_ROOT);
        $rawfiles = new RawFiles();

        $this->parse_raw($rawfiles, $root);

        return $root;
    }

    private function parse_raw($rawfiles, $root)
    {
        $fid = $rawfiles->AddRawFile($root);

        $filename = $root->Get(CNode::FLD_VAL);
        $fullpath = $rawfiles->GetFullFileName($fid);
        $rawlines = file($fullpath);

        if ($rawlines == null) {
            $errlevel = ($root->Get(CNode::FLD_KEY) == CNode::K_ROOT) ? CNode::E_FATAL : CNode::E_WARN;
            $errmsg = "Failed to read file $filename, abspath = $fullpath";
            $rawfiles->MarkError($root, $errlevel, $errmsg);
            return;
        }

        $root->SetRawMap($fid, 1, count($rawlines), '');

        $stack = [];
        $cur_node = $root;
        $prev_node = null;
        $cur_val = $cur_comment = '';
        $from_line = $to_line = 0;

        $sticky = false;
        $multiline_tag = '';

        foreach ($rawlines as $line_num => $data) {

            $line_num ++;

            if ($sticky || ($multiline_tag != '')) {
                $d = rtrim($data, "\r\n");
            } else {
                $d = trim($data);
                if ($d == '') {
                    $cur_comment .= "\n";
                    continue;  // ignore empty lines
                }

                if ($d[0] == '#') {
                    $cur_comment .= $d . "\n";
                    continue; // comments
                }
                $from_line = $line_num;
            }

            if (strlen($d) > 0) {
                $end_char = $d[strlen($d) - 1];
            } else {
                $end_char = '';
            }

            $cur_val .= $d;

            if ($end_char == '\\') {
                $sticky = true;
                $cur_val .= "\n"; //make the line end with \n\
                continue;
            } else {
                $sticky = false;
            }

            if ($multiline_tag != '') {
                if (trim($d) == $multiline_tag) // stop
                    $multiline_tag = '';
                else {
                    $cur_val .= "\n";
                    continue;
                }
            } elseif (($pos = strpos($d, '<<<')) > 0) {
                $multiline_tag = trim(substr($d, $pos + 3));
                $cur_val .= "\n";
                continue;
            }

            $to_line = $line_num;

            if ($d[0] == '}') {
                // end of block
                $cur_node->EndBlock($cur_comment);

                if (strlen($cur_val) > 1) {
                    $rawfiles->MarkError($cur_node, CNode::E_WARN, 'No other characters allowed at the end of closing }');
                }

                if (count($stack) > 0) {
                    $prev_node = $cur_node;
                    $prev_node->Set(CNode::FLD_FLTO, $line_num);
                    $cur_node = array_pop($stack);
                } else {
                    $rawfiles->MarkError(($prev_node == null) ? $cur_node : $prev_node, CNode::E_FATAL, 'Mismatched blocks, may due to extra closing }');
                }
            } else {

                $is_block = false;
                if ($end_char == '{') {
                    $cur_val = rtrim(substr($cur_val, 0, (strlen($cur_val) - 1)));
                    $is_block = true;
                }

                if (preg_match('/^([\S]+)\s/', $cur_val, $m)) {
                    $key = $m[1];
                    $val = trim(substr($cur_val, strlen($m[0])));
                    if (substr($val, 0, 3) == '<<<') {
                        $posv0 = strpos($val, "\n");
                        $posv1 = strrpos($val, "\n");
                        $val = trim(substr($val, $posv0 + 1, $posv1 - $posv0));
                    }
                } else {
                    $key = $cur_val;
                    $val = null;
                }

                if ($cur_node->HasFlag(CNode::BM_HAS_RAW)) {
                    if (DTblDef::getInstance()->IsSpecialBlockRawContent($cur_node, $key)) {
                        $cur_node->AddRawContent($d, $cur_comment);
                        $cur_val = '';
                        continue;
                    }
                }

                $type = CNode::T_KV;
                if ($is_block) {
                    $type = ($val == null) ? CNode::T_KB : CNode::T_KVB;
                } elseif (strcasecmp($key, 'include') == 0) {
                    $type = CNode::T_INC;
                }

                $newnode = new CNode($key, $val, $type);
                $newnode->SetRawMap($fid, $from_line, $to_line, $cur_comment);
                // validate key
                if (!preg_match('/^([a-zA-Z_0-9:])+$/', $key))
                    $rawfiles->MarkError($newnode, CNode::E_WARN, "Invalid char in keyword $key");

                $cur_node->AddChild($newnode);

                if ($newnode->HasFlag(CNode::BM_BLK)) {
                    DTblDef::getInstance()->MarkSpecialBlock($newnode);
                    $stack[] = $cur_node;
                    $prev_node = $cur_node;
                    $cur_node = $newnode;
                } elseif ($newnode->HasFlag(CNode::BM_INC)) {
                    $this->parse_raw($rawfiles, $newnode);
                    $cur_node->AddIncludeChildren($newnode);
                }
            }

            $cur_val = '';
            $cur_comment = '';
        }

        $cur_node->EndBlock($cur_comment);

        while (count($stack) > 0) {
            $rawfiles->MarkError($cur_node, CNode::E_FATAL, 'Mismatched blocks at end of the file, may due to extra openning { or missing closing }.');

            $prev_node = $cur_node;
            $cur_node = array_pop($stack);
        }
    }

    public function Test()
    {

        ini_set('include_path', '.:ws/');

        date_default_timezone_set('America/New_York');

        spl_autoload_register(function ($class) {
            include $class . '.php';
        });

        $filename = '/home/lsong/proj/temp/t2.conf';
        $this->Parse($filename);

        /*            $confdata = new CData('serv', $filename);
          echo "Test file $filename \n";
          $root = $this->LoadData($confdata);
          //$this->ExportData($root);


          $filemap = DPageDef::GetInstance()->GetFileMap($confdata->_type);   // serv, vh, tp, admin



          $root->PrintBuf($buf1);
          echo "=======buf1====\n$buf1";

          $exproot = $root->DupHolder();
          $filemap->Convert($root, $exproot, 1, 1);

          $exproot->PrintBuf($buf2);
          echo "=======buf2====\n$buf2";

          $newxml = $exproot->DupHolder();
          $filemap->Convert($exproot, $newxml, 1, 0);
          $newxml->PrintXmlBuf($buf3);
          echo "=======buf3====\n$buf3";

          //$exproot->MergeUnknown($root);
          //$exproot->PrintBuf($buf2);
          //echo $buf2;

          return $root; */
    }

}

//$parser = new PlainConfParser();
//$parser->Test();
