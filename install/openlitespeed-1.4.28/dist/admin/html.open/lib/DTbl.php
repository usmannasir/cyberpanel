<?php

class DTbl
{
	const FLD_INDEX = 1;
	const FLD_SHOWPARENTREF = 2;
	const FLD_LINKEDTBL = 3;
	const FLD_DEFAULTEXTRACT = 4;
	const FLD_DATTRS = 5;
	const FLD_ID = 6;
	const FLD_SUBTBLS = 7;

	private $_id;
	private $_dattrs;
	private $_helpKey;
	private $_cols = 0;
	private $_isTop = false;

	private	$_holderIndex = NULL;
	private $_showParentRef = false;

	private $_subTbls = NULL;
	private $_defaultExtract = NULL;
	private $_linkedTbls = NULL;

	private $_width = '100%';
	private $_align;
	private $_title;
	private $_addTbl;
	private $_icon;
	private $_hasNote;

	private $_sorted_tbl = FALSE;
	private $_sort_ascend;
	private $_sort_key;

	public static function NewRegular($id, $title, $attrs, $helpkey=NULL, $cols=NULL)
	{
		$tbl = new DTbl($id, $title, $attrs, $helpkey);
		$tbl->_cols = ($cols > 0) ? $cols : 2;
		return $tbl;
	}

	public static function NewIndexed($id, $title, $attrs, $index, $helpkey=NULL, $defaultExtract=NULL)
	{
		$tbl = new DTbl($id, $title, $attrs, $helpkey);
		$tbl->_holderIndex = $index;
		$tbl->_cols = 2;
		if ($defaultExtract != NULL)
			$tbl->_defaultExtract = $defaultExtract;
		return $tbl;
	}

	public static function NewTop($id, $title, $attrs, $index, $addTbl, $align=0, $helpkey=NULL, $icon=NULL, $hasNote=FALSE)
	{
		$tbl = new DTbl($id, $title, $attrs, $helpkey);
		$cols = count($attrs);
		$tbl->_holderIndex = $index;
		$tbl->_addTbl = $addTbl;
		$tbl->_align = $align;
		$tbl->_isTop = true;
		if ($icon != NULL) {
			$tbl->_icon = $icon;
			$cols ++;
		}
		if ($hasNote) {
			$cols ++;
			$tbl->_hasNote = $hasNote;
		}
		$tbl->_cols = $cols;
		return $tbl;
	}

	public static function NewSel($id, $title, $attrs, $subtbls, $helpkey=NULL)
	{
		$tbl = new DTbl($id, $title, $attrs, $helpkey);
		$tbl->_subTbls = $subtbls;
		$tbl->_cols = 3;
		return $tbl;
	}

	private function __construct($id, $title, $attrs, $helpKey=NULL)
	{
		$this->_id = $id;
		$this->_title = $title;
		$this->_dattrs = $attrs;
		$this->_helpKey = $helpKey;
	}

	public function Dup($newId, $title=NULL)
	{
		$d = new DTbl($newId, (($title == NULL)? $this->_title : $title), $this->_dattrs, $this->_helpKey);
		$d->_addTbl = $this->_addTbl;
		$d->_align = $this->_align;
		$d->_icon = $this->_icon;
		$d->_width = $this->_width;
		$d->_cols = $this->_cols;
		$d->_hasNote = $this->_hasNote;
		$d->_holderIndex = $this->_holderIndex;
		$d->_subTbls = $this->_subTbls;
		$d->_linkedTbls = $this->_linkedTbls;
		$d->_defaultExtract = $this->_defaultExtract;
		$d->_showParentRef = $this->_showParentRef;

		return $d;
	}

	public function Get($field)
	{
		switch ($field) {
			case self::FLD_ID: return $this->_id;
			case self::FLD_LINKEDTBL: return $this->_linkedTbls;
			case self::FLD_INDEX: return $this->_holderIndex;
			case self::FLD_DATTRS: return $this->_dattrs;
			case self::FLD_DEFAULTEXTRACT: return $this->_defaultExtract;
			case self::FLD_SUBTBLS: return $this->_subTbls;
		}
		die("DTbl field $field not supported");
	}

	public function Set($field, $fieldval)
	{
		switch ($field) {
			case self::FLD_SHOWPARENTREF: $this->_showParentRef = $fieldval;
			break;
			case self::FLD_LINKEDTBL: $this->_linkedTbls = $fieldval;
			break;
			case self::FLD_DEFAULTEXTRACT: $this->_defaultExtract = $fieldval;
			break;
			default: die("field $field not supported");
		}
	}

	public function ResetAttrEntry($index, $newAttr)
	{
		$this->_dattrs[$index] = $newAttr;
	}


	public function GetSubTid($node)
	{
		if ($this->_subTbls == '')
			return NULL;

		$keynode = $node->GetChildren($this->_subTbls[0]);
		if ($keynode == NULL)
			return NULL;
		$newkey = $keynode->Get(CNode::FLD_VAL);
		if ( ($newkey == '0') || !isset($this->_subTbls[$newkey]) ) {
			return $this->_subTbls[1]; // use default
		}
		else
			return $this->_subTbls[$newkey];
	}


	public function PrintHtml($dlayer, $disp)
	{
		if ($this->_holderIndex != NULL && $dlayer != NULL) {
			// populate missing index
			if (is_array($dlayer)) {
				foreach ($dlayer as $key => $nd) {
					if ($nd->GetChildren($this->_holderIndex) == NULL) {
						$nd->AddChild(new CNode($this->_holderIndex, $nd->Get(CNode::FLD_VAL)));
					}
				}
			}
			elseif ($dlayer->GetChildren($this->_holderIndex) == NULL) {
				$dlayer->AddChild(new CNode($this->_holderIndex, $dlayer->Get(CNode::FLD_VAL)));
			}
		}

		if ($disp->IsViewAction())
			$this->print_view($dlayer, $disp);
		else
			$this->print_edit($dlayer, $disp);
	}

	private function get_print_header($disp, $actString, $isEdit=FALSE, $hasSort=FALSE)
	{
		$buf = '<header role="heading">';

		// tooltip
		$table_help = ' ';

		if ($this->_helpKey != NULL && ($dhelp_item = DMsg::GetAttrTip($this->_helpKey)) != NULL) {
			$table_help = $dhelp_item->Render();
		}
		else if (count($this->_dattrs) == 1 && $this->_cols == 1) {
			$av = array_values($this->_dattrs);
			$a0 = $av[0];
			if ($a0->_label == NULL || $a0->_label == $this->_title) {
				if(($dhelp_item = DMsg::GetAttrTip($a0->_helpKey)) != NULL) {
					$is_blocked = $a0->blockedVersion();
					$version = $is_blocked? $a0->_version: 0;
					$table_help = $dhelp_item->Render($version);
				}
			}

		}
		$title = $this->_title;
		if ($isEdit)
			$title = '<i class="fa fa-edit fa-lg"></i> ' . $title;
		$ref = $disp->Get(DInfo::FLD_REF);
		if ($this->_showParentRef && $ref != NULL) {
			$pos = strpos($ref, '`');
			if ($pos !== FALSE)
				$title .= ' - ' . substr($ref, 0, $pos);
			else
				$title .= ' - ' . $ref;
		}

		$all_blocked = TRUE;
		$keys = array_keys($this->_dattrs);
		foreach( $keys as $i )
		{
			if ( !$this->_dattrs[$i]->blockedVersion() ) {
				$all_blocked = FALSE;
				break;
			}
		}
		if ($all_blocked)
			$actString = NULL;

		if ( $actString != NULL ) {
			$actdata = $disp->GetActionData($actString, $this->_id, '', $this->_addTbl);
			$buf .= UI::GetActionButtons($actdata, 'toolbar');
		}
		$buf .= '<h2>'. $title . '</h2><span class="lst-tooltip pull-left">' . $table_help . '</span></header>';


		if ( $this->_isTop )
		{
			$buf .= '<thead><tr>';
			if ($hasSort) {
				$this->_sorted_tbl  = FALSE;
				$sortval = $disp->Get(DInfo::FLD_SORT);
				if ($sortval != NULL) {
					$pos = strpos($sortval, '`');
					if ($this->_id == substr($sortval, 0, $pos)) {
						$this->_sorted_tbl = TRUE;
						$this->_sort_ascend = $sortval[$pos+1];
						$this->_sort_key = substr($sortval, $pos+2);
					}
				}
			}
			$url = $disp->Get(DInfo::FLD_CtrlUrl);
			if ( $disp->Get(DInfo::FLD_TID) != NULL )
				$url .= '&t=' . $disp->Get(DInfo::FLD_TID);
			if ( $disp->Get(DInfo::FLD_REF) != NULL )
				$url .= '&r=' . $disp->Get(DInfo::FLD_REF);

			if ($this->_icon != NULL)
				$buf .= '<th></th>';

			foreach( $keys as $i )
			{
				$attr = $this->_dattrs[$i];
				if ( $attr->IsFlagOn(DAttr::BM_HIDE) )
					continue;

				$buf .= '<th';
				if ( isset($this->_align[$i]) )
					$buf .= ' align="'.$this->_align[$i] .'"';

				$buf .= '>' . $attr->_label;
				if ( $hasSort && $attr->_type != 'action' )
				{
					$buf .= ' <a href="' . $url . '&sort=' . $this->_id . '`';
					if ($this->_sorted_tbl && ($this->_sort_key == $attr->GetKey())) {
						if ($this->_sort_ascend == 1)
							$buf .= '0' . $attr->GetKey() . '"><i class="pull-right fa fa-sort-asc"></i>';
						else
							$buf .= '1' . $attr->GetKey() . '"> <i class="pull-right fa fa-sort-desc"></i>';
					}
					else {
						$buf .= '1' . $attr->GetKey() . '"> <i class="pull-right fa fa-sort"></i>';
					}
					$buf .= '</a>';

				}
				if ( $attr->_type == 'ctxseq' ) {
					$attr->_hrefLink = $url . $attr->_href;
				}
				$buf .= '</th>';
			}
			$buf .= "</tr></thead>\n";
		}

		return $buf;
	}

	private function print_view($dlayer, $disp)
	{
		$buf = '<div class="jarviswidget jarviswidget-color-blue"><table class="table table-bordered table-condensed">' . "\n";
		$ref = $disp->GetLast(DInfo::FLD_REF);
		$disptid = $disp->Get(DInfo::FLD_TID);
		$hasB = ($disptid != '');

		if ( $this->_isTop ) {
			if ( $this->_addTbl == NULL )
				$actString = 'E'; //e';
			else if ( $this->_addTbl != 'N' )
				$actString = 'a';
			else
				$actString = '';

			if ($hasB)
				$actString .= 'B';

			$hasSort = ($dlayer != NULL && is_array($dlayer));
			$buf .= $this->get_print_header($disp, $actString, false, $hasSort);
			$buf .= '<tbody>';

			if ( $dlayer != NULL)
			{
				if (!is_array($dlayer)) {
					$dlayer = array($dlayer->Get(CNode::FLD_VAL) => $dlayer);
				}

				if ($hasSort && $this->_sorted_tbl) {
					$sorted = array();
					$is_num = TRUE;
					foreach ($dlayer as $key => $node) {
						$val = $node->GetChildVal($this->_sort_key);
						if ($is_num && !is_numeric($val))
							$is_num = FALSE;
						$sorted[$key] = $val;
					}
					$flag = $is_num ? SORT_NUMERIC : SORT_STRING;
					if ($this->_sort_ascend == 1)
						asort($sorted, $flag);
					else
						arsort($sorted, $flag);
					$keys = array_keys($sorted);
				}
				else
					$keys = array_keys($dlayer);

				$action_attr = NULL;
				foreach ($this->_dattrs as $attr) {
					if ($attr->_type == 'action') {
						if ( $attr->IsFlagOn(DAttr::BM_NOTNULL) && strpos($attr->_maxVal, 'd') !== FALSE && count($dlayer) == 1	)
							$attr->_maxVal = str_replace('d', '', $attr->_maxVal); // do not allow delete if only one left
						$action_attr = $attr;
						break;
					}
				}
				$index = 0;
				foreach ( $keys as $key ) {
					$nd = $dlayer[$key];
					$buf .= $this->get_print_line_multi($nd, $key, $index, $disp, $action_attr);
					$index ++;
				}
			}
		}
		else
		{
			$actString = 'E';
			if ($hasB)
				$actString .= 'B';
			if ($ref != NULL && is_array($dlayer)) {
				$dlayer = $dlayer[$ref];
			}

			$buf .= $this->get_print_header($disp, $actString);
			$buf .= '<tbody>';

			foreach ($this->_dattrs as $attr) {
				$buf .= $this->get_print_line($dlayer, $disp, $attr);
			}
		}

		$buf .= '</tbody></table></div>';
		echo "$buf \n";

	}

	private function print_edit($dlayer, $disp)
	{
		$buf = '';
		$ref = $disp->GetLast(DInfo::FLD_REF);

		if ($ref != NULL && is_array($dlayer)) {
			$dlayer = $dlayer[$ref];
		}

        $labels = array($this->_helpKey);
        foreach ($this->_dattrs as $attr) {
            $labels[] = $attr->_helpKey;
        }
		if (($tips = DMsg::GetEditTips($labels)) != NULL) {
			$buf .= UI::GetTblTips($tips);
		}

		$buf .= '<div class="jarviswidget jarviswidget-color-teal">' . "\n";

		$actString = ( (substr($this->_id, -3) == 'SEL') ? 'n':'s' ) . 'B';
		$buf .= $this->get_print_header($disp, $actString, true);

		$buf .= '<div role="content"><div class="widget-body form-horizontal"><fieldset>';
		foreach ($this->_dattrs as $attr) {
			$buf .= $this->get_print_inputline($dlayer, $disp, $attr);
		}

		$buf .= '</fieldset></div></div></div>';
		echo "$buf \n";
	}

	private function get_print_line($node, $disp, $attr)
	{
		$valwid = 0;
		if ( $attr == NULL || $attr->IsFlagOn(DAttr::BM_HIDE)) {
			return '';
		}

		$is_blocked = $attr->blockedVersion();
		$version = $is_blocked? $attr->_version: 0;
		if ( $attr->_type == 'sel1' && $node != NULL && $node->GetChildVal($attr->GetKey()) != NULL ) {
			$attr->SetDerivedSelOptions($disp->GetDerivedSelOptions($this->_id, $attr->_minVal, $node));
		}

		$buf = '<tr>';
		if ( $attr->_label ) {

			if ($is_blocked) {
				$buf .= '<td class="xtbl_label_blocked">';
			}
			else {
				$buf .= '<td class="xtbl_label">';
			}
			$buf .= $attr->_label;

			$dhelp_item = DMsg::GetAttrTip($attr->_helpKey);
			if ($this->_cols == 1) {
				$buf .= '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;';
			}
			else {
				if($dhelp_item != NULL) {
					$buf .= '<span class="pull-right">'.  $dhelp_item->Render($version) . '</span>';
				}

				$buf .= '</td>';
			}

			$buf .= '</td>';
		}

		if ($this->_cols == 1) {

			//$buf .= '</tr><tr class="xtbl_value"><td';
			$buf .= '</tr><tr ><td';
		}
		else {
			$buf .= '<td';
		}
		if ($attr->blockedVersion()) {
			$buf .= ' class="xtbl_value_blocked"';
		}
		if ($valwid > 0) {
			$buf .= " width=\"$valwid\"";
		}
		$buf .= '>';


		if ( $attr->_href )	{
			//$link = $disp->_ctrlUrl . 'm=' . $disp->_mid . '&p=' . $disp->_pid;
			$link = $disp->Get(DInfo::FLD_CtrlUrl);
			if ( $disp->Get(DInfo::FLD_TID) != NULL )
				$link .= '&t=' . $disp->Get(DInfo::FLD_TID);
			if ( $disp->Get(DInfo::FLD_REF) != NULL )
				$link .= '&r='. $disp->Get(DInfo::FLD_REF);

			$link .= $attr->_href;
			$attr->_hrefLink = str_replace('$R', $disp->Get(DInfo::FLD_REF), $link);
		}

		$buf .= ($attr->toHtml($node));


		$buf .= "</td></tr>\n";
		return $buf;
	}

	private function get_print_inputline($dlayer, $disp, $attr)
	{
		if ( $attr->IsFlagOn(DAttr::BM_NOEDIT))
			return '';

		if ( $attr->_type == 'sel1' ) {
			$attr->SetDerivedSelOptions($disp->GetDerivedSelOptions($this->_id, $attr->_minVal, $dlayer));
		}

		$is_blocked = $attr->blockedVersion();
		$helppop = '';

		if (($dhelp_item = DMsg::GetAttrTip($attr->_helpKey)) != NULL) {
			$helppop = '<span class="lst-tooltip">' . $dhelp_item->Render($is_blocked? $attr->_version: 0) . '</span>';
		}

		$buf = $attr->toInputGroup($dlayer, $is_blocked, $helppop);

		return $buf;
	}

	private function get_print_line_multi($data, $key0, $htmlid, $disp, $action_attr)
	{
		$buf = '<tr>';

		$keys = array_keys($this->_dattrs);

		//allow index field clickable, same as first action
		$actionLink = null;
		$indexActionLink = null;

		if ($action_attr != NULL) {

			if ( is_array($action_attr->_minVal) ) {
				$index = $action_attr->_minVal[0];
				$type = $data->GetChildVal($index);
				$ti = isset($action_attr->_minVal[$type]) ? $action_attr->_minVal[$type] : $action_attr->_minVal[1];
			}
			else
				$ti = $action_attr->_minVal;

			$actdata = $disp->GetActionData( $action_attr->_maxVal, $ti, $key0);
			$actionLink = UI::GetActionButtons($actdata, 'icon');
			$indexActionLink = isset($actdata['v']) ? $actdata['v']['href'] : null;
		}

		foreach( $keys as $key )
		{
			$attr = $this->_dattrs[$key];
			if ( $attr->IsFlagOn(DAttr::BM_HIDE) )
				continue;

			if($key == 0) {
				if ($this->_icon != NULL) {
					if ($attr->GetKey() == 'type' && is_array($attr->_maxVal) && is_array($this->_icon)) {
						$type = $data->GetChildVal('type');
						$icon_name = isset($this->_icon[$type]) ? $this->_icon[$type] : 'application';
					}
					else {
						$icon_name = $this->_icon;
					}
					$buf .= '<td class="icon"><img src="/res/img/icons/'. $icon_name . '.gif"></td>';
				}

			}

			$buf .= '<td';
			if ( isset($this->_align[$key]) )
				$buf .= ' align="'.$this->_align[$key] .'"';
			$buf .= '>';

			if ( $attr->_type == 'action' )	{
				$buf .= $actionLink;
			}
			else {
				if ( $attr->_type == 'sel1' && $data->GetChildVal($attr->GetKey()) != NULL ) {
					$attr->SetDerivedSelOptions($disp->GetDerivedSelOptions($this->_id, $attr->_minVal, $data));
				}
				if ($attr->GetKey() == $this->_holderIndex) {
					$buf .= $attr->toHtml($data, $indexActionLink);

					if ($this->_hasNote && (($note = $data->GetChildVal('note')) != NULL)) {
						$buf .= '<a href="javascript:void(0);" class="pull-right" rel="tooltip" data-placement="right"
								data-original-title="' . $note . '" data-html="true">
								<i class="fa fa-info-circle"></i></a>';
					}
				}
				else
					$buf .= $attr->toHtml($data, NULL);
			}
			$buf .= '</td>';
		}
		$buf .= "</tr>\n";

		return $buf;
	}


}
