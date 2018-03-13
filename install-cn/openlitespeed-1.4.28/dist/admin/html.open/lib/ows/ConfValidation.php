<?php

class ConfValidation extends CValidation
{
	// to hold special validation
	protected function isValidAttr($attr, $cval)
	{
		$isValid = parent::isValidAttr($attr, $cval);

		if ($isValid == 1 && $attr->_type == 'modulename') {
			$res = $this->chkAttr_modulename($attr, $cval);
			$this->setValid($isValid, $res);
		}
		return $isValid;
	}

	protected function chkAttr_modulename($attr, $cval)
	{
		$name = $cval->Get(CNode::FLD_VAL);
		if ( preg_match( "/[<>&%\s]/", $name) ) {
			$cval->SetErr('invalid characters in name');
			return -1;
		}
		else
			return 1;
	}

	protected function validatePostTbl($tbl, $extracted)
	{
		if ($tbl->Get(DTbl::FLD_ID) == 'S_MOD') {
			$isValid = $this->chkPostTbl_SERV_MODULE($extracted);
		}
		else {
			$isValid = parent::validatePostTbl($tbl, $extracted);
		}
		return $isValid;
	}

	protected function chkPostTbl_SERV_MODULE($extracted)
	{
		$isValid = 1;

		if ($extracted->GetChildVal('internal') == 0) {
			$name = $extracted->GetChildVal('name');
			$module = SERVER_ROOT . "modules/{$name}.so" ;
			if (!file_exists($module)) {
				$extracted->SetChildErr('name', "cannot find external module: $module");
				$isValid = -1;
			}
		}

		return $isValid;
	}
}
