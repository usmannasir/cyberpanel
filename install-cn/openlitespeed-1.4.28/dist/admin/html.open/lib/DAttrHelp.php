<?php

class DAttrHelp
{
	private $name;
	private $desc;
	private $tips;
	private $syntax;
	private $example;

	function __construct($name, $desc, $tips = NULL, $syntax = NULL, $example = NULL) {

		$this->name = $name;
		$this->desc = $desc;
		$this->tips = str_replace('<br>', '<br/>', $tips);
		$this->syntax = $syntax;
		$this->example = $example;
	}

	public function Render($blocked_version=0)
	{
		$buf = '<a href="javascript:void(0);" rel="popover" data-placement="right"
				data-original-title="<i class=\'fa fa-fw fa-tag\'></i> <strong>' . $this->name
						. '</strong>" data-html="true" data-content=\'<div>';

		switch ($blocked_version) {
			case 0: break;
			case 1:  // LSWS ENTERPRISE;
				$buf .= ' <i>' . DMsg::UIStr('note_entfeature') . '</i>';
				break;
			case 2: // LSWS 2CPU +
			case 3: // LSLB 2CPU +
				$buf .= ' <i>' . DMsg::UIStr('note_multicpufeature') . '</i>';
				break;
		}
		$buf .= $this->desc
				. '<br><br>';
		if ($this->syntax) {
			$buf .= '<strong>' . DMsg::UIStr('note_syntax') . ':</strong> '
					. $this->syntax
					. '<br><br>';
		}
		if ($this->example) {
			$buf .= '<strong>' . DMsg::UIStr('note_example') . ':</strong> '
					. $this->example
					. '<br><br>';
		}
		if ($this->tips) {
			$buf .= '<strong>' . DMsg::UIStr('note_tips') . ':</strong><ul type=circle>';
			$tips = explode('<br/>', $this->tips);
			foreach($tips as $ti) {
				$ti = trim($ti);
				if ($ti != '')
					$buf .= '<li>' . $ti . '</li>';
			}
			$buf .= '</ul>';
		}

		$buf .= '</div>\'><i class="icon-prepend fa fa-question-circle text-muted"></i></a>';
		return $buf;
	}

}

