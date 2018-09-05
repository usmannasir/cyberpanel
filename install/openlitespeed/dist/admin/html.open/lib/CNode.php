<?php

class FileLine
{
    public $_note0;  // begin notes
    public $_note1 = '';  // end notes
    public $_fid;
    public $_fline0;
    public $_fline1;

    function __construct($file_id, $from_line, $to_line, $comment)
    {
        $this->_fid = $file_id;
        $this->_fline0 = $from_line;
        $this->_fline1 = $to_line;
        $this->_note0 = $comment;
    }

    function AddEndComment($note1)
    {
        $this->_note1 .= "$note1\n";
    }

}

class CNode
{

    const E_WARN = 1;
    const E_FATAL = 2;
    const K_ROOT = '__root__';
    const K_EXTRACTED = '__extracted__';
    const BM_VAL = 1;
    const BM_BLK = 2;
    const BM_INC = 4;
    const BM_IDX = 8;
    const BM_MULTI = 16;
    const BM_ROOT = 32;
    const BM_HAS_RAW = 64; // block contains raw node
    const BM_RAW = 128; // raw node, no key, just content
    const T_ROOT = 32;
    const T_KV = 1;  //key-value pair
    const T_KB = 2;  // key blk
    const T_KVB = 3; // key-value blk
    const T_INC = 4; // include
    const T_RAW = 128; // raw content, no key parsed
    const KEY_WIDTH = 25;
    const FLD_TYPE = 1;
    const FLD_KEY = 2;
    const FLD_VAL = 3;
    const FLD_ERR = 4;
    const FLD_ERRLEVEL = 5;
    const FLD_PARENT = 6;
    const FLD_FID = 7;
    const FLD_FLFROM = 8;
    const FLD_FLTO = 9;
    const FLD_ELM = 10;
    const FLD_PRINTKEY = 11;

    private $_type = self::T_KV;
    private $_k;
    private $_raw_k;
    private $_print_k;
    private $_v = null; //value
    private $_raw_content = null; // raw content
    private $_raw_tag = null;
    private $_e = null; //err
    private $_errlevel = 0; //  1-Warning, 2-fatal
    private $_parent = null;
    private $_fileline;
    private $_changed;
    private $_els;  // elements

    function __construct($key, $val, $type = CNode::T_KV)
    {
        $this->_raw_k = $key;
        $this->_k = DKeywordAlias::NormalizedKey($key);
        $this->_print_k = $key;
        $this->_changed = true;
        $this->_type = $type;

        if ($this->_type != CNode::T_KV) {
            $this->_els = array();
        }
        $this->_v = $val;
        if ($val != null && ($this->_type & self::BM_VAL == 0)) {
            $this->_type |= self::BM_VAL;
        }
    }

    public function AddRawContent($line, &$current_comment)
    {
        if ($current_comment != '') {
            $this->_raw_content .= rtrim($current_comment) . "\n";
            $current_comment = '';
        }
        $this->_raw_content .= rtrim($line) . "\n";
    }

    public function AddRawTag($tag)
    {
        $this->_type |= self::BM_HAS_RAW;
        $this->_raw_content = '';
        $this->_raw_tag = $tag;
    }

    public function Get($field)
    {
        switch ($field) {

            case self::FLD_KEY: return $this->_k;
            case self::FLD_VAL: return $this->_v;
            case self::FLD_ERR: return $this->_e;
            case self::FLD_PARENT: return $this->_parent;
            case self::FLD_FID: return ($this->_fileline == null) ? '' : $this->_fileline->_fid;
            case self::FLD_FLFROM: return ($this->_fileline == null) ? '' : $this->_fileline->_fline0;
            case self::FLD_FLTO: return ($this->_fileline == null) ? '' : $this->_fileline->_fline1;
        }
        die("field $field not supported");
    }

    public function Set($field, $fieldval)
    {
        switch ($field) {

            case self::FLD_FLTO: $this->_fileline->_fline1 = $fieldval;
                break;
            case self::FLD_PRINTKEY: $this->_print_k = $fieldval;
                break;
            case self::FLD_TYPE: $this->_type = $fieldval;
                break;
            case self::FLD_KEY:
                $this->_raw_k = $fieldval;
                $this->_k = DKeywordAlias::NormalizedKey($fieldval);
                $this->_print_k = $fieldval;
                break;

            default: die("field $field not supported");
        }
    }

    public function SetVal($v)
    {
        $this->_v = $v;
        if ($v != null && ($this->_type & self::BM_VAL == 0))
            $this->_type |= self::BM_VAL;
    }

    public function AddFlag($flag)
    {
        $this->_type |= $flag;
    }

    public function HasFlag($flag)
    {
        return ($this->_type & $flag) != 0;
    }

    public function HasVal()
    {
        // 0 is valid
        return ($this->_v !== null && $this->_v !== '');
    }

    public function SetErr($errmsg, $level = 1)
    {
        if ($errmsg != '') {
            $this->_e .= $errmsg;
            if ($this->_errlevel < $level)
                $this->_errlevel = $level;
        }
    }

    public function HasErr()
    {
        return $this->_e != null;
    }

    public function HasFatalErr()
    {
        return ($this->_errlevel == self::E_FATAL);
    }

    public function HasChanged()
    {
        return $this->_changed;
    }

    public function DupHolder()
    {
        // create an empty blk node
        $holder = new CNode($this->_k, $this->_v, $this->_type);
        if ($this->_errlevel > 0) {
            $holder->_e = $this->_e;
            $holder->_errlevel = $this->_errlevel;
        }
        $holder->_changed = $this->_changed;
        $holder->_fileline = $this->_fileline;
        return $holder;
    }

    public function MergeUnknown($node)
    {
        if ($this->_type != self::T_ROOT && !($this->_type & self::BM_BLK)) {
            echo "Err, should merge at parent level $node->_k $node->_v \n";
            return;
        }

        foreach ($node->_els as $k => $el) {
            if (isset($this->_els[$k])) {
                if (is_a($el, 'CNode')) {
                    echo " k = $k \n";
                    $this->_els[$k]->MergeUnknown($el);
                } else {
                    foreach ($el as $id => $elm) {
                        if (isset($this->_els[$k][$id]))
                            $this->_els[$k][$id]->MergeUnknown($elm);
                        else
                            $this->AddChild($elm);
                    }
                }
            }
            else {
                if (is_a($el, 'CNode'))
                    $this->AddChild($el);
                else
                    $this->_els[$k] = $el; // move array over
            }
        }
    }

    public function SetRawMap($file_id, $from_line, $to_line, $comment)
    {
        $this->_fileline = new FileLine($file_id, $from_line, $to_line, $comment);
        $this->_changed = false;
    }

    public function EndBlock(&$cur_comment)
    {
        $this->_fileline->AddEndComment($cur_comment);
        $cur_comment = '';
        if ($this->_raw_tag != '') {
            if ($this->_raw_content != '') {
                $child = new CNode($this->_raw_tag, $this->_raw_content, self::T_KV | self::T_RAW);
                $this->AddChild($child);
            } else {
                // backward compatible, mark existing node to raw
                $child = $this->GetChildren($this->_raw_tag);
                if ($child != null && is_a($child, 'CNode')) {
                    $child->_type |= self::T_RAW;
                }
            }
        }
    }

    public function AddChild($child)
    {
        if ($this->_type == self::T_KV) {
            $this->_type = ($this->_v == '') ? self::T_KB : self::T_KVB;
        }
        $child->_parent = $this;
        $k = $child->_k;
        if (isset($this->_els[$k])) {
            if (!is_array($this->_els[$k])) {
                $first_node = $this->_els[$k];
                $this->_els[$k] = array();
                if ($first_node->_v == null)
                    $this->_els[$k][] = $first_node;
                else
                    $this->_els[$k][$first_node->_v] = $first_node;
            }
            if ($child->_v == null)
                $this->_els[$k][] = $child;
            else
                $this->_els[$k][$child->_v] = $child;
        }
        else {
            $this->_els[$k] = $child;
        }
    }

    public function AddIncludeChildren($incroot)
    {
        if (is_array($incroot->_els)) {
            foreach ($incroot->_els as $elm) {
                if (is_array($elm)) {
                    foreach ($elm as $elSingle) {
                        $elSingle->AddFlag(self::BM_INC);
                        $this->AddChild($elSingle);
                    }
                } else {
                    $elm->AddFlag(self::BM_INC);
                    $this->AddChild($elm);
                }
            }
        }
    }

    public function RemoveChild($key) // todo: key contains :
    {
        $key = strtolower($key);
        unset($this->_els[$key]);
    }

    public function RemoveFromParent()
    {
        if ($this->_parent != null) {
            if (is_array($this->_parent->_els[$this->_k])) {
                foreach ($this->_parent->_els[$this->_k] as $key => $el) {
                    if ($el == $this) {
                        unset($this->_parent->_els[$this->_k][$key]);
                        return;
                    }
                }
            } else
                unset($this->_parent->_els[$this->_k]);
            $this->_parent = null;
        }
    }

    public function HasDirectChildren($key = '')
    {
        if ($key == '')
            return ($this->_els != null && count($this->_els) > 0);
        else
            return ($this->_els != null && isset($this->_els[strtolower($key)]));
    }

    public function GetChildren($key)
    {
        $key = strtolower($key);
        if (($pos = strpos($key, ':')) > 0) {
            $node = $this;
            $keys = explode(':', $key);
            foreach ($keys as $k) {
                if (isset($node->_els[$k]))
                    $node = $node->_els[$k];
                else
                    return null;
            }
            return $node;
        }
        elseif (isset($this->_els[$key]))
            return $this->_els[$key]; // can be array
        else
            return null;
    }

    public function GetChildVal($key)
    {
        $child = $this->GetChildren($key);
        return ($child == null || !is_a($child, 'CNode')) ? null : $child->_v;
    }

    public function SetChildVal($key, $val)
    {
        $child = $this->GetChildren($key);
        if ($child == null && !is_a($child, 'CNode'))
            return false;
        $child->SetVal($val);
        return true;
    }

    public function SetChildErr($key, $err)
    {
        $child = $this->GetChildren($key);
        if ($child == null && !is_a($child, 'CNode'))
            return false;
        if ($err == null) // clear err
            $child->SetErr(null, 0);
        else
            $child->SetErr($err);
        return true;
    }

    public function GetChildNodeById($key, $id)
    {
        $layer = $this->GetChildren($key);
        if ($layer != null) {
            if (is_array($layer)) {
                return isset($layer[$id]) ? $layer[$id] : null;
            } elseif ($layer->_v == $id)
                return $layer;
        }
        return null;
    }

    private function get_last_layer($location)
    {
        $layers = explode(':', $location);
        $lastlayer = array_pop($layers);
        if ($lastlayer != null) {
            $lastlayer = ltrim($lastlayer, '*');
            if (($varpos = strpos($lastlayer, '$')) > 0) {
                $lastlayer = substr($lastlayer, 0, $varpos);
            }
        }
        return $lastlayer;
    }

    public function GetChildrenByLoc(&$location, &$ref)
    {
        $node = $this;
        if ($location == '')
            return $node;

        $layers = explode(':', $location);
        foreach ($layers as $layer) {
            $ismulti = false;
            if ($layer[0] == '*') {
                $layer = ltrim($layer, '*');
                $ismulti = true;
            }
            if (($varpos = strpos($layer, '$')) > 0) {
                $layer = substr($layer, 0, $varpos);
            }
            $location = substr($location, strpos($location, $layer));
            $layer = strtolower($layer);
            if (!isset($node->_els[$layer])) {
                if ($ismulti && ($ref == '~')) { // for new child, return parent
                    return $node;
                } else {
                    return null;
                }
            }

            $nodelist = $node->_els[$layer];
            if ($ismulti) {
                if ($ref == '')
                    return $nodelist;

                if ($ref == '~') { // for new child, return parent
                    return $node;
                }

                if (($pos = strpos($ref, '`')) > 0) {
                    $curref = substr($ref, 0, $pos);
                    $ref = substr($ref, $pos + 1);
                } else {
                    $curref = $ref;
                    $ref = '';
                }

                if (is_array($nodelist)) {
                    if (!isset($nodelist[$curref])) {
                        return null;
                    }
                    $node = $nodelist[$curref];
                } else {
                    $node = $nodelist;
                    if ($node->_v != $curref) {
                        return null;
                    }
                }
            } else
                $node = $nodelist;
        }
        return $node;
    }

    public function GetChildNode(&$location, &$ref)
    {
        $node = $this->GetChildrenByLoc($location, $ref);
        return is_a($node, 'CNode') ? $node : null;
    }

    public function UpdateChildren($loc, $curref, $extractData)
    {
        $location = $loc;
        $ref = $curref;
        $child = $this->GetChildNode($location, $ref);
        if ($child == null) {
            // need original loc
            $child = $this->AllocateLayerNode($loc);
        } elseif (!is_a($child, 'CNode')) {
            die("child is not cnode \n");
        }

        if ($ref == '~') {
            // new node, ref & location has been modified by GetChildNode
            // right now, only last one
            $lastlayer = $this->get_last_layer($loc);
            $extractData->Set(CNode::FLD_KEY, $lastlayer);
            $child->AddChild($extractData);
        } else {
            foreach ($extractData->_els as $key => $exchild) {
                if (isset($child->_els[$key])) {
                    $nd = $child->_els[$key];
                    if (is_array($nd) || (is_a($exchild, 'CNode') && $exchild->HasFlag(CNode::BM_BLK)))
                        $child->_els[$key] = $exchild; // this will lost inline notes
                    else {
                        $nd->SetVal($exchild->_v);
                    }
                } else if (is_array($exchild)) {
                    foreach ($exchild as $exchildSingle) {
                        $child->AddChild($exchildSingle);
                    }
                } else {
                    $child->AddChild($exchild);
                }
            }
            if ($extractData->_v != null && $extractData->_v !== $child->_v) {
                $child->update_holder_val($extractData->_v);
            }
        }
    }

    private function update_holder_val($val)
    {
        if ($this->_parent != null) {
            $oldval = $this->_v;
            $this->_v = $val;
            if (is_array($this->_parent->_els[$this->_k])) {
                unset($this->_parent->_els[$this->_k][$oldval]);
                $this->_parent->_els[$this->_k][$val] = $this;
            }
        }
    }

    public function debug_out(&$buf, $level = 0)
    {
        $indent = str_pad('', $level * 2);
        $buf .= "key={$this->_k} val= {$this->_v} type={$this->_type}";
        if ($this->_els != null) {
            $buf .= " {\n";
            $level ++;
            foreach ($this->_els as $k => $el) {
                $buf .= "$indent   [$k] => ";
                if (is_array($el)) {
                    foreach ($el as $k0 => $child)
                        $buf .= " [$k0] => ";
                    $level ++;
                    if (!is_a($child, 'CNode')) {
                        $buf .= "not cnode ";
                    }
                    $child->debug_out($buf, $level);
                } else
                    $el->debug_out($buf, $level);
            }
            $buf .= "$indent }\n";
        } else
            $buf .= "\n";
    }

    public function PrintBuf(&$buf, $level = 0)
    {
        $note0 = ($this->_fileline == null) ? '' : $this->_fileline->_note0;
        $note1 = ($this->_fileline == null) ? '' : $this->_fileline->_note1;
        $key = $this->_print_k;
        $alias_note = '';
        if (($key1 = DKeywordAlias::GetShortPrintKey($this->_k)) != null) {
            $key = $key1;
            if ($note0 == '' && $key != $this->_raw_k) {
                $alias_note = "# $key is shortened alias of $this->_print_k \n";
            }
        }

        if ($note0 != '')
            $buf .= str_replace("\n\n", "\n", $note0);

        if ($this->_errlevel > 0)
            $buf .= "#__ERR__({$this->_errlevel}): $this->_e \n";

        if ($this->_type & self::BM_IDX)
            return; // do not print index node

        if (($this->_type != self::T_INC) && ($this->_type & self::BM_INC))
            return; // do not print including nodes

        if ($this->_type & self::BM_RAW) {
            $buf .= $this->_v . "\n";
            return;
        }
        $indent = str_pad('', $level * 2);
        $val = $this->_v;
        if ($val != '' && strpos($val, "\n")) {
            $val = "<<<END_{$key}\n$val\n{$indent}END_{$key}\n";
        }

        if (($this->_type & self::BM_VAL) && !($this->_type & self::BM_BLK)) {
            // do not print empty value
            if ($val != '' || $note0 != '' || $this->_errlevel > 0) {
                $width = self::KEY_WIDTH - $level * 2;
                $buf .= $alias_note;
                $buf .= $indent . str_pad($key, $width) . " $val\n";
            }
        } else {
            $begin = '';
            $end = '';
            $buf1 = '';
            $buf2 = '';

            if ($this->_type & self::BM_BLK) {
                if ($note0 == '')
                    $buf1 .= "\n";
                $buf1 .= $alias_note;
                $buf1 .= "{$indent}$key $val";
                $begin = " {\n";
                $end = "$indent}\n";
                $level ++;
            }
            elseif ($this->_type == self::T_INC) {
                $buf1 .= "{$indent}$key $val\n";
                $buf1 .= "\n##__INC__\n";
                $end = "\n##__ENDINC__\n";
            }

            foreach ($this->_els as $el) {
                if (is_array($el)) {
                    foreach ($el as $child)
                        $child->PrintBuf($buf2, $level);
                } else
                    $el->PrintBuf($buf2, $level);
            }

            if ($note1 != '') {
                $buf2 .= str_replace("\n\n", "\n", $note1);
            }

            // do not print empty block

            if ($val != '' || $buf2 != '') {
                if ($buf2 == '')
                    $buf .= $buf1 . "\n";
                else
                    $buf .= $buf1 . $begin . $buf2 . $end;
            }
        }
    }

    public function PrintXmlBuf(&$buf, $level = 0)
    {
        if ($this->_type == self::T_ROOT) {
            $buf .= '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
        }
        $indent = str_pad('', $level * 2);

        $key = $this->_print_k;
        $value = htmlspecialchars($this->_v);

        if (($this->_type & self::BM_VAL) && !($this->_type & self::BM_BLK)) {
            if ($value !== '')
                $buf .= "$indent<$key>$value</$key>\n";
        }
        else {
            $buf1 = '';
            $buf2 = '';

            if ($this->_type & self::BM_BLK) {
                $buf1 .= "$indent<$key>\n";
                $level ++;
            }
            foreach ($this->_els as $el) {
                if (is_array($el)) {
                    foreach ($el as $child)
                        $child->PrintXmlBuf($buf2, $level);
                } else
                    $el->PrintXmlBuf($buf2, $level);
            }

            // do not print empty block
            if ($buf2 != '') {
                $buf .= $buf1 . $buf2;
                if ($this->_type & self::BM_BLK) {
                    $buf .= "$indent</$key>\n";
                }
            }
        }
    }

    public function LocateLayer($location)
    {
        $node = $this;
        if ($location != '') {
            $layers = explode(':', $location);
            foreach ($layers as $layer) {
                $holder_index = '';
                if ($layer[0] == '*')
                    $layer = ltrim($layer, '*');
                $varpos = strpos($layer, '$');
                if ($varpos > 0) {
                    $holder_index = substr($layer, $varpos + 1);
                    $layer = substr($layer, 0, $varpos);
                }
                $children = $node->GetChildren($layer);
                if ($children == null)
                    return null;

                $node = $children;
            }
        }
        return $node;
    }

    public function AllocateLayerNode($location)
    {
        $node = $this;
        if ($location != '') {
            $layers = explode(':', $location);
            foreach ($layers as $layer) {
                if ($layer[0] == '*') {
                    // contains multiple items, return parent node
                    return $node;
                }

                $varpos = strpos($layer, '$');
                if ($varpos > 0) {
                    $key = substr($layer, 0, $varpos);
                    $type = CNode::T_KVB;
                } else {
                    $key = $layer;
                    $type = CNode::T_KB;
                }
                $children = $node->GetChildren($key);
                if ($children == null) {
                    $children = new CNode($key, null, $type);
                    $node->AddChild($children);
                }
                $node = $children;
            }
        }
        return $node;
    }

}
