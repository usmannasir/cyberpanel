<?php

class DAttr extends DAttrBase
{

	public function blockedVersion()
	{
		// no restriction
		return FALSE;
	}

	public function bypassSavePost()
	{
		return ($this->IsFlagOn(DAttr::BM_NOEDIT));
	}
}
