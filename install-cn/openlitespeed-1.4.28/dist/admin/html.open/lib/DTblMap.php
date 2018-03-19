<?php

class DTblMap
{
	private $_layer;
	private $_map;  // array of  string: tid or submap
	private $_extended_map;

	public function __construct($layer, $map, $extended_map=NULL)
	{
		$this->_layer = $layer;
		$this->_map = $map;
		$this->_extended_map = $extended_map;
	}

	public function GetLoc($index=0)
	{
		return is_array($this->_layer) ? $this->_layer[$index] : $this->_layer;
	}

	public function GetMaps($extended)
	{
		$maps = is_array($this->_map) ? $this->_map : array($this->_map);

		if ($extended && $this->_extended_map != NULL) {
			if (is_array($this->_extended_map))
				$maps = array_merge($maps, $this->_extended_map);
			else
				$maps[] = $this->_extended_map;
		}
		return $maps;
	}

	public function FindTblLoc($tid)
	{
		$location = $this->_layer; // page data, layer is not array
		$maps = $this->GetMaps(TRUE);

		foreach ($maps as $m)
		{
			if (is_a($m, 'DTblMap')) {
				$nextloc = $m->FindTblLoc($tid);
				if ($nextloc != NULL) {
					return ($location == '') ? $nextloc : "{$location}:$nextloc";
				}
			}
			elseif ($tid == $m) {
				return $location;
			}
		}
		return NULL;
	}

	public function Convert($srcloc_index, $srcnode, $dstloc_index, $dstnode)
	{
		$srcloc = $this->GetLoc($srcloc_index);
		$dstloc = $this->GetLoc($dstloc_index);

		$srclayer = $srcnode->LocateLayer($srcloc);
		if ($srclayer == NULL) {
			return;
		}

		$tonode = $dstnode->AllocateLayerNode($dstloc);

		$is_multi = (strpos($dstloc, '*') !== FALSE );
		$map = $this->GetMaps(FALSE);

		if ($is_multi) {
			// get last layer
			$k0 = strrpos($dstloc, ':');
			if ($k0 === FALSE)
				$k0 = 0;
			else
				$k0 ++;
			$type = CNode::BM_BLK | CNode::BM_MULTI;
			$k1 = strrpos($dstloc, '$');
			if ($k1 === FALSE) {
				$key = ($k0 > 0) ? substr($dstloc, $k0) : $dstloc;
			}
			else {
				$key = substr($dstloc, $k0, $k1 - $k0);
				$type |= CNode::BM_VAL;
			}
			$key = ltrim($key, '*');

			if (!is_array($srclayer))
				$srclayer = array($srclayer);

			foreach ($srclayer as $fromnode) {
				$child = new CNode($key, NULL, $type); // value will be set later
				$this->convert_map($map, $srcloc_index, $fromnode, $dstloc_index, $child);
				$tonode->AddChild($child);
			}
		}
		else {
			$this->convert_map($map, $srcloc_index, $srclayer, $dstloc_index, $tonode);
		}

	}

	private function convert_map($map, $srcloc_index, $srcnode, $dstloc_index, $dstnode)
	{
		foreach ($map as $m)
		{
			if (is_a($m, 'DTblMap'))
				$m->Convert($srcloc_index, $srcnode, $dstloc_index, $dstnode);
			else
				$this->convert_tbl($m, $srcnode, $dstnode);
		}
	}

	private function convert_tbl($tid, $srcnode, $dstnode)
	{
		$tbl = DTblDef::GetInstance()->GetTblDef($tid);
		$attrs = $tbl->Get(DTbl::FLD_DATTRS);
		$index = $tbl->Get(DTbl::FLD_INDEX);

		foreach ( $attrs as $attr )	{

			if ( $attr->_type == 'action' || $attr->IsFlagOn(DAttr::BM_NOFILE) )
				continue;

			$key = $attr->GetKey();
			$layerpos = strpos($key, ':');
			if ($layerpos > 0) {
				$layer = substr($key, 0, $layerpos);
				$key = substr($key, $layerpos+1);
				$snode = $srcnode->LocateLayer($layer);
				if ($snode == NULL) {
					//echo "attr layer loc $layer return NULL\n";
					continue;
				}
				$dnode = $dstnode->AllocateLayerNode($layer);
			}
			else {
				$snode = $srcnode;
				$dnode = $dstnode;
			}

			$from = $snode->GetChildren($key);
			if ($from == NULL) {
				$val = ($key == $index) ? $snode->Get(CNode::FLD_VAL) : '';
				if ($val == '' && !$attr->IsFlagOn(DAttr::BM_NOTNULL))
					continue;
				$from = new CNode($key, $val);
			}
			else
				$snode->RemoveChild($key);

			if (is_array($from)) {
				foreach($from as $fnode) {
					$fnode->Set(CNode::FLD_PRINTKEY, $key);
					$dnode->AddChild($fnode);
				}
			}
			else {
				$from->Set(CNode::FLD_PRINTKEY, $key);
				$dnode->AddChild($from);
				if ($key == $index) {
					$from->AddFlag(CNode::BM_IDX);
					$dnode->SetVal($from->Get(CNode::FLD_VAL));
				}
			}
		}

		if ( ($subtid = $tbl->GetSubTid($dstnode)) != NULL ) {
			$this->convert_tbl($subtid, $srcnode, $dstnode);
		}

		if (!$srcnode->HasDirectChildren())
			$srcnode->RemoveFromParent();
	}

}
