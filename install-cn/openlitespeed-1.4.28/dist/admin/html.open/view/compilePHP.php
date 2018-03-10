<?php

require_once('inc/auth.php');
include_once('../lib/util/build_php/BuildConfig.php');

//todo: review set timeout

class CompilePHPUI
{
	private $steps;
	private $check;

	function __construct()
	{
		$this->init();
	}

	private function init()
	{
		$this->steps = array(1 => DMsg::ALbl('buildphp_step1'),
			2 => DMsg::ALbl('buildphp_step2'),
			3 => DMsg::ALbl('buildphp_step3'),
			4 => DMsg::ALbl('buildphp_step4'));

		$this->check = new BuildCheck();
	}

	private function step_indicator()
	{
		$cur_step = $this->check->GetNextStep();

		$buf = '<div class="form-bootstrapWizard"><ul class="bootstrapWizard form-wizard">';
		foreach ($this->steps as $i => $title) {
			$class = '';
			$label = $i;

			if ($i == $cur_step)
				$class = 'active';
			elseif ($i < $cur_step) {
				$class = 'complete';
				$label = '<i class="fa fa-check"></i>';
			}

			$buf .= '<li';
			if ($class)
				$buf .= ' class="' . $class . '"';
			$buf .= '><span class="step">' . $label . '</span>
					<span class="title">' . $title . '</span></li>';
		}
		$buf .= '</ul></div>';

		return $buf;
	}

	private function toolbar_btn($label, $hrefjs, $id='', $disabled='')
	{
		$buf = '<div class="widget-toolbar" role="menu"><a href="javascript:'
				. $hrefjs . '" ';
		if ($id != '')
			$buf .= 'id="' . $id . '" ';

		$buf .= 'class="btn btn-info';
		if ($disabled)
			$buf .= ' disabled';
		$buf .= '">' . $label . "</a></div>\n";
		return $buf;
	}

	private function form_start()
	{
		$cur_step = $this->check->GetNextStep();

		$buf .= '<form name="buildform" id="buildform">
		<div class="jarviswidget jarviswidget-color-blueLight">
		<header role="heading">';

		$hasNext = ($cur_step < 4);
		$hasPrev = ($cur_step == 2 || $cur_step == 3);
		$disabled = ($cur_step == 3);

		if ($hasNext)
			$buf .= $this->toolbar_btn(DMsg::UIStr('btn_next'), 'step(1)', 'nextbtn', $disabled);
		if ($hasPrev)
			$buf .= $this->toolbar_btn(DMsg::UIStr('btn_prev'), 'step(0)', 'prevbtn', $disabled);

		$buf .=	'<span class="widget-icon"><i class="fa fa-arrow-circle-right"></i></span>
			<h2><strong> ' . $cur_step . '</strong> - ' . $this->steps[$cur_step];

		if ($cur_step > 1) {
			$buf .= ' for PHP ' . $this->check->pass_val['php_version'];
		}

		$buf .= '</h2></header>
		<div role="content"><div class="widget-body form-horizontal">
			<fieldset>';
		return $buf;
	}

	private function form_end()
	{
		$cur_step = $this->check->GetNextStep();
		$version = $this->check->pass_val['php_version'];
		return '</fieldset></div></div></div>
				<input type="hidden" name="curstep" value="' . $cur_step . '">
				<input type="hidden" name="buildver" value="' . $version . '">
				<input type="hidden" name="next" id="next">
				</form>';
	}

	private function form_group($label, $required, $input, $tip='', $note='', $err='')
	{
		$buf = '<div class="form-group';
		if ($err)
			$buf .= ' has-error';
		$buf .= '"><label class="col-md-3 control-label">' . $label;

		if ($required)
			$buf .= ' *';

		$buf .= '</label><div class="col-md-9"><div class="input-group">';

		if ($tip)
			$buf .= '<span class="input-group-addon">' . $tip . '</span>';

		$buf .= $input . '</div>';

		if ($err)
			$buf .= '<span class="help-block"><i class="fa fa-warning"></i> '
					. htmlspecialchars($err,ENT_QUOTES) . '</span>';

		if ( $note )
			$buf .= '<p class="note">'. htmlspecialchars($note,ENT_QUOTES) .'</p>';

		$buf .= '</div></div>';
		return $buf;
	}

	private function input_select($name, $options, $val='')
	{
		$buf = '<select class="form-control" name="' . $name . '" id="' . $name . '">'
				. UIBase::genOptions($options, $val, true)
				. '</select>';
		return $buf;
	}

	private function input_text($name, $val)
	{
		$buf = '<input class="form-control" type="text" name="' . $name . '" id="' . $name . '" value="' . $val . '">';
		return $buf;
	}

	private function input_textarea($name, $value, $rows, $wrap='off')
	{
		$buf = '<textarea class="form-control" name="' . $name . '" rows="' . $rows . '" wrap="' . $wrap . '">' . $value . "</textarea>\n";
		return $buf;
	}

	private function input_checkbox($name, $value, $label)
	{
		$buf = '<div class="checkbox"><label><input type="checkbox" name="' . $name . '"';
		if ($value)
			$buf .= ' checked';
		$buf .= '>' . $label . "</label></div>\n";
		return $buf;
	}

	public function PrintPage()
	{
		echo $this->step_indicator();

		switch ($this->check->GetNextStep()) {
			case 1: return $this->print_step_1();
			case 2: return $this->print_step_2();
			case 3: return $this->print_step_3();
			case 4: return $this->print_step_4();
			default: echo UIBase::error_divmesg("Invalid entrance");
		}
	}

	function print_step_1()
	{
		$buf = $this->form_start();

		if ( isset($this->check->pass_val['err'])) {
			$buf .= UIBase::error_divmesg($this->check->pass_val['err']);
		}

		$phpversion = BuildConfig::GetVersion(BuildConfig::PHP_VERSION);
		$select = $this->input_select('phpversel', $phpversion);
		$note = DMsg::ALbl('buildphp_updatever') . '/usr/local/lsws/admin/html/lib/util/build_php/BuildConfig.php';

		$buf .= $this->form_group(DMsg::ALbl('buildphp_phpver'), true, $select, '', $note);

		$buf .= $this->form_end();

		echo $buf;
	}

	function print_step_2()
	{
		$options = NULL;
		$saved_options = NULL;
		$default_options = NULL;
		$cur_step = $this->check->GetCurrentStep();
		$pass_val = $this->check->pass_val;

		if ($cur_step == 1) {
			$php_version = $pass_val['php_version'];
			$options = new BuildOptions($php_version);
			$options->setDefaultOptions();
			$default_options = $options;
            $supported = $this->check->GetModuleSupport($php_version);
		}
		elseif ($cur_step == 2) {
			$options = $pass_val['input_options'];
			$php_version = $options->GetValue('PHPVersion');
			$default_options = new BuildOptions($php_version);
			$default_options->setDefaultOptions();
		}
		elseif ($cur_step == 3) {
			$php_version = $pass_val['php_version'];
			$options = new BuildOptions($php_version);
			$default_options = new BuildOptions($php_version);
			$default_options->setDefaultOptions();
		}
		if ($options == NULL)
			return "NULL options\n";

		$saved_options = $options->getSavedOptions();
		if ($saved_options != NULL && $cur_step == 3) {
			$options = $saved_options;
		}

		$buf = $this->form_start();
		if ( isset($pass_val['err'])) {
			$buf .= UIBase::error_divmesg(DMsg::ALbl('note_inputerr'));
		}

		$input = '<input type="button" class="btn btn-default btn-sm" value="' . DMsg::ALbl('buildphp_useprevconf') . '" '
				. ($saved_options ? $saved_options->gen_loadconf_onclick('IMPORT') : 'disabled')
				. '> &nbsp;&nbsp;<input type="button" class="btn btn-default btn-sm" value="' . DMsg::ALbl('buildphp_restoredefault') .'" '
				. $default_options->gen_loadconf_onclick('DEFAULT')
				. '>';
		$buf .= $this->form_group(DMsg::ALbl('buildphp_loadconf'), false, $input);

		$input = $this->input_text('path_env', $options->GetValue('ExtraPathEnv'));
		$err = isset($pass_val['err']['path_env'])? $pass_val['err']['path_env']:'';
		$tip = DMsg::GetAttrTip('extrapathenv')->Render();
		$buf .= $this->form_group(DMsg::ALbl('buildphp_extrapathenv'), false, $input, $tip, '', $err);

		$input = $this->input_text('installPath', $options->GetValue('InstallPath'));
		$err = isset($pass_val['err']['installPath'])? $pass_val['err']['installPath']:'';
		$tip = DMsg::GetAttrTip('installpathprefix')->Render();
		$buf .= $this->form_group(DMsg::ALbl('buildphp_installpathprefix'), true, $input, $tip, '', $err);

		$input = $this->input_text('compilerFlags', $options->GetValue('CompilerFlags'));
		$err = isset($pass_val['err']['compilerFlags'])? $pass_val['err']['compilerFlags']:'';
		$tip = DMsg::GetAttrTip('compilerflags')->Render();
		$buf .= $this->form_group(DMsg::ALbl('buildphp_compilerflags'), false, $input, $tip, '', $err);

		$input = $this->input_textarea('configureParams', $options->GetValue('ConfigParam'), 6, 'soft');
		$err = isset($pass_val['err']['configureParams'])? $pass_val['err']['configureParams']:'';
		$tip = DMsg::GetAttrTip('configureparams')->Render();
		$buf .= $this->form_group(DMsg::ALbl('buildphp_confparam'), true, $input, $tip, '', $err);

        $input = '';
        if ($supported['mailheader']) {
            $input = $this->input_checkbox('addonMailHeader', $options->GetValue('AddOnMailHeader'),
                    '<a href="http://choon.net/php-mail-header.php" target="_blank" rel="noopener noreferrer">' . DMsg::ALbl('buildphp_mailheader1')
                    . '</a> (' . DMsg::ALbl('buildphp_mailheader2') .')');
        }
		if ($supported['suhosin']) {
			$input .= $this->input_checkbox('addonSuhosin', $options->GetValue('AddOnSuhosin'), '<a href="http://suhosin.org" target="_blank" rel="noopener noreferrer">Suhosin</a> ' . DMsg::ALbl('buildphp_suhosin'));
		}

		$label_opcode = DMsg::ALbl('buildphp_opcodecache');
        if ($supported['apc']) {
    		$input .= $this->input_checkbox('addonAPC', $options->GetValue('AddOnAPC'), '<a href="http://pecl.php.net/package/APC" target="_blank" rel="noopener noreferrer">APC</a> (' . $label_opcode .') V' . BuildConfig::GetVersion(BuildConfig::APC_VERSION));
		}

		if ($supported['xcache']) {
			$input .= $this->input_checkbox('addonXCache', $options->GetValue('AddOnXCache'), '<a href="http://xcache.lighttpd.net/" target="_blank" rel="noopener noreferrer">XCache</a> (' . $label_opcode .') V' . BuildConfig::GetVersion(BuildConfig::XCACHE_VERSION));
		}
		if ($supported['opcache']) {
            $input .= $this->input_checkbox('addonOPcache', $options->GetValue('AddOnOPcache'), '<a href="http://pecl.php.net/package/ZendOpcache" target="_blank" rel="noopener noreferrer">Zend OPcache</a> (' . $label_opcode .') V' . BuildConfig::GetVersion(BuildConfig::OPCACHE_VERSION));
		}
		if ($supported['memcache']) {
			$input .= $this->input_checkbox('addonMemCache', $options->GetValue('AddOnMemCache'), '<a href="http://pecl.php.net/package/memcache" target="_blank" rel="noopener noreferrer">memcache</a> (memcached extension) V' . BuildConfig::GetVersion(BuildConfig::MEMCACHE_VERSION));
		}
		if ($supported['memcachd']) {
			$input .= $this->input_checkbox('addonMemCachd', $options->GetValue('AddOnMemCachd'), '<a href="http://pecl.php.net/package/memcached" target="_blank" rel="noopener noreferrer">memcached</a> (PHP extension for interfacing with memcached via libmemcached library) V' . BuildConfig::GetVersion(BuildConfig::MEMCACHED_VERSION));
		}
		if ($supported['memcachd7']) {
			$input .= $this->input_checkbox('addonMemCachd7', $options->GetValue('AddOnMemCachd7'), '<a href="http://pecl.php.net/package/memcached" target="_blank" rel="noopener noreferrer">memcached</a> (PHP extension for interfacing with memcached via libmemcached library) V' . BuildConfig::GetVersion(BuildConfig::MEMCACHED7_VERSION));
		}
		$note = DMsg::ALbl('buildphp_updatever') . ' /usr/local/lsws/admin/html/lib/util/build_php/BuildConfig.php';
		$buf .= $this->form_group(DMsg::ALbl('buildphp_addonmodules'), false, $input, '', $note);

		$buf .= $this->form_end();

		echo $buf;
	}

	function print_step_3()
	{
		$options = $this->check->pass_val['build_options'];
		if ($options == NULL) // illegal entry
			return;

		$buf = $this->form_start();

		$err = '';
		$optionsaved = '';
		$tool = new BuildTool($options);
		if (!$tool || !$tool->GenerateScript($err, $optionsaved)) {
			$buf .= UIBase::error_divmesg(DMsg::UIStr('buildphp_failgenscript') . " $err");
		}
		else {
			if ($optionsaved)
				$buf .= UIBase::info_divmesg(DMsg::UIStr('buildphp_confsaved'));
			else
				$buf .= UIBase::error_divmesg(DMsg::UIStr('buildphp_failsaveconf'));

			$_SESSION['progress_file'] = $tool->progress_file;
			$_SESSION['log_file'] = $tool->log_file;

			$cmd = 'bash -c "exec ' . $tool->build_prepare_script . ' 1> ' . $tool->log_file . ' 2>&1" &';
			exec($cmd);

			$buf .= UIBase::warn_divmesg(DMsg::UIStr('buildphp_nobrowserrefresh'));
			$buf .= '<input type="hidden" name="manual_script", value="' . $tool->build_manual_run_script . '">';
			$buf .= '<input type="hidden" name="extentions", value="' . $tool->extension_used . '">';

			$buf .= '
					<h5>' . DMsg::ALbl('buildphp_mainstatus') . ': <span id="statusgraphzone"><i class="txt-color-teal fa fa-gear fa-spin"></i></span></h5>
					<div>
					<pre class="lst-statuszone" id="statuszone"></pre>
					</div>
					<h5>' . DMsg::ALbl('buildphp_detaillog') . ': </h5>
					<div >
					<pre class="lst-logzone" id="logzone">' . $cmd . '</pre>
					</div>';
		}

		$buf .= $this->form_end();

		echo $buf;
	}

	function print_step_4()
	{
		$manual_script = $this->check->pass_val['manual_script'];
		if ($manual_script == NULL) // illegal entry
			return;

		$buf = $this->form_start();

		$ver = $this->check->pass_val['php_version'];
		$binname = 'lsphp-' . $ver;

		$repl = array('%%server_root%%' => SERVER_ROOT, '%%binname%%' => $binname, '%%phpver%%' => $ver[0]);

		$notes = '<ul><li>' . DMsg::UIStr('buildphp_binarylocnote', $repl) . '</li>';

		if ( $this->check->pass_val['extentions'] != '') {
			$notes1 = BuildTool::getExtensionNotes($this->check->pass_val['extentions']);
			$notes .= "\n" . $notes1 . '</ul>';
		}

		$buf .= UIBase::info_divmesg($notes);

		$echo_cmd = 'echo "For security reason, please log in and manually run the pre-generated script to continue."';
		exec($echo_cmd . ' > ' . $this->check->pass_val['log_file']);
		exec($echo_cmd . ' > ' . $this->check->pass_val['progress_file']);

		$repl = array('%%manual_script%%' => $manual_script);

		$buf .= UIBase::warn_divmesg(DMsg::UIStr('buildphp_manualrunnotice', $repl));

		$buf .= '
				<h5>' . DMsg::ALbl('buildphp_mainstatus') . ': <span id="statusgraphzone"><i class="txt-color-teal fa fa-gear fa-spin"></i></span></h5>
				<div>
				<pre class="lst-statuszone" id="statuszone"></pre>
				</div>
				<h5>' . DMsg::ALbl('buildphp_detaillog') . ': </h5>
				<div >
				<pre class="lst-logzone" id="logzone">' . $cmd . '</pre>
						</div>';

		$buf .= $this->form_end();
		echo $buf;
	}
}

echo UI::content_header('fa-list', DMsg::ALbl('menu_tools'), DMsg::ALbl('menu_compilephp'));

$ui = new CompilePHPUI();
$ui->PrintPage();
?>


<script type="text/javascript">
/* DO NOT REMOVE : GLOBAL FUNCTIONS!

	 * pageSetUp() is needed whenever you load a page.
	 * It initializes and checks for all basic elements of the page
	 * and makes rendering easier.
	 *
	 */

	 pageSetUp();

	 // PAGE RELATED SCRIPTS

	 function step(next)
	 {
		//var spinicon = $("#refreshlog_icon");
		var form = $("#buildform");
		var container = $('#content');
		form.find("#next").val(next);
		$.ajax({
			type : "POST",
			url: "view/compilePHP.php",
			data : form.serialize(),
			dataType: "html",
			async : false,
			beforeSend : function() {
				pagefunction = null;
				container.removeData().html("");
				// place cog
				container.html('<h1 class="ajax-loading-animation"><i class="fa fa-cog fa-spin"></i> Loading...</h1>');
			}
		})
		.success (function(data) {

			// dump data to container
			container.css({
				opacity : '0.0'
			}).html(data).delay(50).animate({
				opacity : '1.0'
			}, 300);

			// clear data var
			data = null;
			container = null;
			lst_refreshFooterTime();
		})
		.error (function(mesg) {
			alert("error " + mesg);
		})
		;
	}

	function refreshStatus()
	{
		var statuszone = $("#statuszone"), logzone = $("#logzone");
		$.ajax({
			url: "view/ajax_data.php?id=buildprogress",
			dataType: "text",
			async : true,
		})
		.success (function(log) {
			var pos = log.indexOf("\n**LOG_DETAIL**");
			statuszone.text(log.substring(0,pos));
			logzone.text(log.substring(pos));
			lst_refreshFooterTime();

			if (log.indexOf("\n**DONE**") >= 0) {
				$("#statusgraphzone").html(' <span class="label label-success"><i class="fa fa-check"></i></span> <?php DMsg::EchoUIStr('buildphp_finishsuccess');?>');
				if ($("#nextbtn").length) {
					$("#nextbtn").removeClass('disabled');
					$("#prevbtn").removeClass('disabled');
				}
        	}
        	else if (log.indexOf("\n**ERROR**") >= 0) {
        		$("#statusgraphzone").html(' <span class="label label-danger"><i class="fa fa-warning"></i></span> <?php DMsg::EchoUIStr('buildphp_stopduetoerr');?>');
				if ($("#prevbtn").length)
        			$("#prevbtn").removeClass('disabled');
				else
					setTimeout(refreshStatus, 15000);
        	}
        	else {
            	setTimeout(refreshStatus, 3000);
			}

		})
		.error (function(mesg) {
			statuszone.text('Status refresh error: ' + mesg + ' ... pleasse wait');
			setTimeout(refreshStatus, 5000);
		})
		;
	}

	 // pagefunction

	var pagefunction = function() {
		if ($("#statuszone").length) {
			refreshStatus();
		}

	// load bootstrap wizard
	};

	// end pagefunction

	// Load bootstrap wizard dependency then run pagefunction
	pagefunction();

</script>
