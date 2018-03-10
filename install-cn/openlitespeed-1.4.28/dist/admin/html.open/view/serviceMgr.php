<?php

require_once("inc/auth.php");

$act = UIBase::GrabGoodInput("any",'act');
$actId = UIBase::GrabGoodInput("any",'actId');

switch ($act) {
	case 'restart':
		Service::ServiceRequest(SInfo::SREQ_RESTART_SERVER);
		break;

	case 'lang':
		DMsg::SetLang($actId);
		break;

	case 'toggledebug':
		Service::ServiceRequest(SInfo::SREQ_TOGGLE_DEBUG);
		break;

	case 'reload':
		if ($actId != '') {
			Service::ServiceRequest(SInfo::SREQ_VH_RELOAD, $actId);
		}
		break;
	case 'disable':
		if ($actId != '') {
			Service::ServiceRequest(SInfo::SREQ_VH_DISABLE, $actId);
		}
		break;
	case 'enable':
		if ($actId != '') {
			Service::ServiceRequest(SInfo::SREQ_VH_ENABLE, $actId);
		}
		break;
	default:
		error_log("illegal act $act ");
}

