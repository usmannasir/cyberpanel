<?php

/*
 * type: parse  _minVal = pattern, _maxVal = pattern tips
 *
 */
define('ATTR_VAL_NOT_SET', DMsg::UIStr('o_notset'));
define('ATTR_VAL_BOOL_YES', DMsg::UIStr('o_yes'));
define('ATTR_VAL_BOOL_NO', DMsg::UIStr('o_no'));
define('ATTR_NOTE_NUM_RANGE', DMsg::UIStr('note_numvalidrange'));
define('ATTR_NOTE_NUMBER', DMsg::UIStr('note_number'));

class DAttrBase
{

    protected $_key;
    protected $_keyalias;
    public $_helpKey;
    public $_type;
    public $_minVal;
    public $_maxVal;
    public $_label;
    public $_href;
    public $_hrefLink;
    public $_multiInd;
    public $_note;
    public $_icon;
    protected $_inputType;
    protected $_inputAttr;
    protected $_glue;
    protected $_bitFlag = 0;

    const BM_NOTNULL = 1;
    const BM_NOEDIT = 2;
    const BM_HIDE = 4;
    const BM_NOFILE = 8;

    public function __construct($key, $type, $label, $inputType = null, $allowNull = true, $min = null, $max = null, $inputAttr = null, $multiInd = 0, $helpKey = null)
    {
        $this->_key = $key;
        $this->_type = $type;
        $this->_label = $label;
        $this->_minVal = $min;
        $this->_maxVal = $max;
        $this->_inputType = $inputType;
        $this->_inputAttr = $inputAttr;
        $this->_multiInd = $multiInd;
        $this->_helpKey = ($helpKey == null) ? $key : $helpKey;

        $this->_bitFlag = $allowNull ? 0 : self::BM_NOTNULL;
    }

    public function SetGlue($glue)
    {
        $this->_glue = $glue;
    }

    public function SetFlag($flag)
    {
        $this->_bitFlag |= $flag;
    }

    public function IsFlagOn($flag)
    {
        return (($this->_bitFlag & $flag) == $flag );
    }

    public function GetKey()
    {
        return $this->_key;
    }

    public function dup($key, $label, $helpkey)
    {
        $cname = get_class($this);
        $d = new $cname($this->_key, $this->_type, $this->_label, $this->_inputType, true, $this->_minVal, $this->_maxVal, $this->_inputAttr, $this->_multiInd, $this->_helpKey);

        $d->_glue = $this->_glue;
        $d->_href = $this->_href;
        $d->_hrefLink = $this->_hrefLink;
        $d->_bitFlag = $this->_bitFlag;
        $d->_note = $this->_note;
        $d->_icon = $this->_icon;


        if ($key != null) {
            $d->_key = $key;
        }
        if ($label != null)
            $d->_label = $label;

        if ($helpkey != null)
            $d->_helpKey = $helpkey;

        return $d;
    }

    protected function extractCheckBoxOr()
    {
        $value = 0;
        $novalue = 1;
        foreach ($this->_maxVal as $val => $disp) {
            $name = $this->_key . $val;
            if (isset($_POST[$name])) {
                $novalue = 0;
                $value = $value | $val;
            }
        }
        return ( $novalue ? '' : (string) $value );
    }

    protected function extractSplitMultiple(&$value)
    {
        if ($this->_glue == ' ')
            $vals = preg_split("/[,; ]+/", $value, -1, PREG_SPLIT_NO_EMPTY);
        else
            $vals = preg_split("/[,;]+/", $value, -1, PREG_SPLIT_NO_EMPTY);

        $vals1 = array();
        foreach ($vals as $val) {
            $val1 = trim($val);
            if (strlen($val1) > 0 && !in_array($val1, $vals1)) {
                $vals1[] = $val1;
            }
        }

        if ($this->_glue == ' ')
            $value = implode(' ', $vals1);
        else
            $value = implode(', ', $vals1);
    }

    protected function toHtmlContent($node, $refUrl = null)
    {
        if ($node == null || !$node->HasVal())
            return '<span class="text-muted">' . ATTR_VAL_NOT_SET . '</span>';

        $o = '';
        $value = $node->Get(CNode::FLD_VAL);
        $err = $node->Get(CNode::FLD_ERR);

        if ($this->_type == 'sel1' && $value != null && !array_key_exists($value, $this->_maxVal)) {
            $err = 'Invalid value - ' . htmlspecialchars($value, ENT_QUOTES);
        }
        else if ($err != null) {
            $type3 = substr($this->_type, 0, 3);
            if ($type3 == 'fil' || $type3 == 'pat') {
                $validator = new ConfValidation();
                $validator->chkAttr_file_val($this, $value, $err);
            }
        }

        if ($err) {
            $node->SetErr($err);
            $o .= '<span class="field_error">*' . $err . '</span><br>';
        }

        if ($this->_href) {
            $link = $this->_hrefLink;
            if (strpos($link, '$V')) {
                $link = str_replace('$V', urlencode($value), $link);
            }
            $o .= '<span class="field_url"><a href="' . $link . '">';
        }
        elseif ($refUrl != null) {
            $o .= '<span class="field_refUrl"><a href="' . $refUrl . '">';
        }


        if ($this->_type === 'bool') {
            if ($value === '1') {
                $o .= ATTR_VAL_BOOL_YES;
            }
            elseif ($value === '0') {
                $o .= ATTR_VAL_BOOL_NO;
            }
            else {
                $o .= '<span class="text-muted">' . ATTR_VAL_NOT_SET . '</span>';
            }
        }
        elseif ($this->_type == 'ctxseq') {
            $o = $value . ' <a href="javascript:lst_ctxseq(' . $value
                    . ')" class="btn bg-color-blueLight btn-xs txt-color-white"><i class="fa fa-plus"></i></a> <a href="javascript:lst_ctxseq(-' . $value
                    . ')" class="btn bg-color-blueLight btn-xs txt-color-white"><i class="fa fa-minus"></i></a>';
        }
        else if ($this->_key == "note") {
            $o .= '<textarea readonly style="width:100%;height:auto">' . htmlspecialchars($value, ENT_QUOTES) . '</textarea>';
        }
        elseif ($this->_type === 'sel' || $this->_type === 'sel1') {
            if ($this->_maxVal != null && array_key_exists($value, $this->_maxVal)) {
                $o .= $this->_maxVal[$value];
            }
            else {
                $o .= htmlspecialchars($value, ENT_QUOTES);
            }
        }
        elseif ($this->_type === 'checkboxOr') {
            if ($this->_minVal !== null && ($value === '' || $value === null)) {
                // has default value, for "Not set", set default val
                $value = $this->_minVal;
            }
            foreach ($this->_maxVal as $val => $name) {
                if (($value & $val) || ($value === $val) || ($value === '0' && $val === 0)) {
                    $o .= '<i class="fa fa-check-square-o">';
                }
                else {
                    $o .= '<i class="fa fa-square-o">';
                }
                $o .= '</i> ';
                $o .= $name . '&nbsp;&nbsp;&nbsp;&nbsp;';
            }
        }
        elseif ($this->_inputType === 'textarea1') {
            $o .= '<textarea readonly style="width:100%;"' . $this->_inputAttr . '>' . htmlspecialchars($value, ENT_QUOTES) . '</textarea>';
        }
        elseif ($this->_inputType === 'text') {
            $o .= '<span class="field_text">' . htmlspecialchars($value, ENT_QUOTES) . '</span>';
        }
        else {
            $o .= htmlspecialchars($value);
        }


        if ($this->_href || $refUrl != null) {
            $o .= '</a></span>';
        }
        return $o;
    }

    protected function getNote()
    {
        if ($this->_note != null)
            return $this->_note;
        if ($this->_type == 'uint') {
            if ($this->_maxVal)
                return ATTR_NOTE_NUM_RANGE . ': ' . $this->_minVal . ' - ' . $this->_maxVal;
            elseif ($this->_minVal !== null)
                return ATTR_NOTE_NUM_RANGE . ' >= ' . $this->_minVal;
        }
        return null;
    }

    public function extractPost($parent)
    {
        if ($this->_type == 'checkboxOr')
            $value = $this->extractCheckBoxOr();
        else {
            $value = UIBase::GrabInput("post", $this->_key);
            if (get_magic_quotes_gpc())
                $value = stripslashes($value);
        }

        $key = $this->_key;
        $node = $parent;
        while (($pos = strpos($key, ':')) > 0) {
            $key0 = substr($key, 0, $pos);
            $key = substr($key, $pos + 1);
            if ($node->HasDirectChildren($key0))
                $node = $node->GetChildren($key0);
            else {
                $child = new CNode($key0, '', CNode::T_KB);
                $node->AddChild($child);
                $node = $child;
            }
        }

        if ($this->_multiInd == 2 && $value != null) {
            $v = preg_split("/\n+/", $value, -1, PREG_SPLIT_NO_EMPTY);
            foreach ($v as $vi)
                $node->AddChild(new CNode($key, trim($vi)));
        }
        elseif ($this->_type == 'checkboxOr') {
            $node->AddChild(new CNode($key, $value));
        }
        else {
            if ($this->_multiInd == 1 && $value != null) {
                $this->extractSplitMultiple($value);
            }
            $node->AddChild(new CNode($key, $value));
        }
        return true;
    }

    public function toHtml($pnode, $refUrl = null)
    {
        $node = ($pnode == null) ? null : $pnode->GetChildren($this->_key);
        $o = '';
        if (is_array($node)) {
            foreach ($node as $nd) {
                $o .= $this->toHtmlContent($nd, $refUrl);
                $o .= '<br>';
            }
        }
        else {
            $o .= $this->toHtmlContent($node, $refUrl);
        }
        return $o;
    }

    public function toInputGroup($pnode, $is_blocked, $helppop)
    {
        $node = ($pnode == null) ? null : $pnode->GetChildren($this->_key);
        $err = '';
        $value = '';

        if (is_array($node)) {
            $value = array();
            foreach ($node as $d) {
                $value[] = $d->Get(CNode::FLD_VAL);
                $e1 = $d->Get(CNode::FLD_ERR);
                if ($e1 != null)
                    $err .= $e1 . '<br>';
            }
        }
        else {
            if ($node != null) {
                $value = $node->Get(CNode::FLD_VAL);
                $err = $node->Get(CNode::FLD_ERR);
            }
            else {
                $value = null;
            }
        }

        $buf = '<div class="form-group' . ($err ? ' has-error">' : '">');
        if ($this->_label) {

            $buf .= '<label class="col-md-3 control-label">';
            $buf .= $this->_label;
            if ($this->IsFlagOn(DAttr::BM_NOTNULL))
                $buf .= ' *';

            $buf .= "</label>\n";
            $buf .= '<div class="col-md-9">';
        }
        else {
            $buf .= '<div class="col-md-12">';
        }


        $buf .= $this->toHtmlInput($helppop, $is_blocked, $err, $value);

        $buf .= "</div></div>\n";
        return $buf;
    }

    protected function toHtmlInput($helppop, $isDisabled, $err, $value)
    {
        $spacer = '&nbsp;&nbsp;&nbsp;&nbsp;';
        $checked = ' checked="checked"';

        $input = '<div class="input-group">';
        $input .= '<span class="input-group-addon">' . $helppop . '</span>' . "\n"; // need this even empty, for alignment

        if (is_array($value) && $this->_inputType != 'checkbox') {
            if ($this->_multiInd == 1)
                $glue = ', ';
            else
                $glue = "\n";
            $value = implode($glue, $value);
        }
        $name = $this->_key;

        $inputAttr = $this->_inputAttr;
        if ($isDisabled)
            $inputAttr .= ' disabled="disabled"';

        $style = 'form-control';
        if ($this->_inputType == 'text') {
            $input .= '<input class="' . $style . '" type="text" name="' . $name . '" ' . $inputAttr . ' value="' . htmlspecialchars($value, ENT_QUOTES) . '">';
        }
        elseif ($this->_inputType == 'password') {
            $input .= '<input class="' . $style . '" type="password" name="' . $name . '" ' . $inputAttr . ' value="' . $value . '">';
        }
        elseif ($this->_inputType == 'textarea' || $this->_inputType == 'textarea1') {
            $input .= '<textarea name="' . $name . '" class="' . $style . '" ' . $inputAttr . '>' . htmlspecialchars($value, ENT_QUOTES) . '</textarea>';
        }
        elseif ($this->_inputType == 'radio' && $this->_type == 'bool') {

            $input .= '<div class="form-control"><div class="lst-radio-group"><label class="radio radio-inline">
					<input type="radio" name="' . $name . '" ' . $inputAttr . ' value="1"';
            if ($value == '1')
                $input .= $checked;
            $input .= '> ' . ATTR_VAL_BOOL_YES . '</label><label class="radio radio-inline">'
                    . '<input type="radio" name="' . $name . '" ' . $inputAttr . ' value="0"';
            if ($value == '0')
                $input .= $checked;
            $input .= '> ' . ATTR_VAL_BOOL_NO . '</label>';
            if (!$this->IsFlagOn(self::BM_NOTNULL)) {
                $input .= '<label class="radio radio-inline">
					<input type="radio" name="' . $name . '" ' . $inputAttr . ' value=""';
                if ($value != '0' && $value != '1')
                    $input .= $checked;
                $input .= '> ' . ATTR_VAL_NOT_SET . '</label>';
            }
            $input .= '</div></div>';
        }
        elseif ($this->_inputType == 'checkboxgroup') {
            $input .= '<div class="form-control">';
            if ($this->_minVal !== null && ($value === '' || $value === null)) {
                // has default value, for "Not set", set default val
                $value = $this->_minVal;
            }
            $js0 = $js1 = '';
            if (array_key_exists('0', $this->_maxVal)) {
                $chval = array_keys($this->_maxVal);
                foreach ($chval as $chv) {
                    if ($chv == '0')
                        $js1 = "document.confform.$name$chv.checked=false;";
                    else
                        $js0 .= "document.confform.$name$chv.checked=false;";
                }
                $js1 = " onclick=\"$js1\"";
                $js0 = " onclick=\"$js0\"";
            }
            foreach ($this->_maxVal as $val => $disp) {
                $id = $name . $val;
                $input .= "<input type=\"checkbox\" id=\"{$id}\" name=\"{$id}\" value=\"{$val}\"";
                if (($value & $val) || ($value === $val) || ($value === '0' && $val === 0))
                    $input .= $checked;
                $input .= ($val == '0') ? $js0 : $js1;
                $input .= "> <label for=\"{$id}\"> $disp </label> $spacer";
            }
            $input .= '</div>';
        }
        elseif ($this->_inputType == 'select') {
            $input .= '<select class="form-control" name="' . $name . '" ' . $inputAttr . '>';
            $input .= UIBase::genOptions($this->_maxVal, $value);
            $input .= '</select>';
        }

        $input .= "</div>\n";
        if ($err != '') {
            $input .= '<span class="help-block"><i class="fa fa-warning"></i> ';
            $type3 = substr($this->_type, 0, 3);
            $input .= ( $type3 == 'fil' || $type3 == 'pat' ) ? $err : htmlspecialchars($err, ENT_QUOTES);
            $input .= '</span>';
        }

        $note = $this->getNote();
        if ($note)
            $input .= '<p class="note">' . htmlspecialchars($note, ENT_QUOTES) . '</p>';

        return $input;
    }

    public function SetDerivedSelOptions($derived)
    {
        $options = ($derived) ? $derived : array();
        if (!$this->IsFlagOn(self::BM_NOTNULL))
            $options[''] = '';
        $this->_maxVal = $options;
    }

}
