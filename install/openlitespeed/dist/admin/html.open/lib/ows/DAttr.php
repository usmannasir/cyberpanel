<?php

class DAttr extends DAttrBase
{

	public function blockedVersion()
	{
		// no restriction
		return false;
	}

	public function bypassSavePost()
	{
		return ($this->IsFlagOn(DAttr::BM_NOEDIT));
	}
}
