<?php

class XmlParser
{
	private $node_stack;
	private $cur_node;
	private $cur_val;

	public function Parse($filename)
	{
		$root = new CNode(CNode::K_ROOT, $filename, CNode::T_ROOT);

		$filename = $root->Get(CNode::FLD_VAL);
		$xmlstring = file_get_contents($filename);
		if ( $xmlstring === false )	{
			$root->SetErr("failed to read file $filename", CNode::E_FATAL);
			return $root;
		}

		$parser = xml_parser_create();
		xml_set_object($parser, $this);
		xml_parser_set_option($parser, XML_OPTION_CASE_FOLDING, false);
		xml_set_element_handler($parser, 'startElement', 'endElement');
		xml_set_character_data_handler($parser, 'characterData');

		// Build a Root node and initialize the node_stack...
		$this->node_stack = [];
		$this->cur_node = $root;

		// parse the data and free the parser...
		$result = xml_parse($parser, $xmlstring);
		if ( !$result )
		{
			$err = 'XML error: '. xml_error_string(xml_get_error_code($parser))
			. ' at line ' . xml_get_current_line_number($parser);
			$root->SetErr("failed to parse file $filename, $err", CNode::E_FATAL);
		}
		xml_parser_free($parser);

		return $root;
	}

	private function startElement($parser, $name, $attrs)
	{
		if ( $this->cur_node != null )
			$this->node_stack[] = $this->cur_node;

		$this->cur_node = new CNode($name, '');

		$this->cur_val = '';
	}

	private function endElement($parser, $name)
	{
		$this->cur_node->SetVal(trim($this->cur_val));
		$this->cur_val = '';
		$node = $this->cur_node;
		$this->cur_node = array_pop($this->node_stack);
		$this->cur_node->AddChild($node);
	}

	private function characterData($parser, $data)
	{
		$this->cur_val .= $data;
	}


	public function Test()
	{
		/*ini_set('include_path',	'.:ws/');

		date_default_timezone_set('America/New_York');

		spl_autoload_register( function ($class) {
			include $class . '.php';
		});

			$filename = '/home/lsong/proj/temp/conf/register.xml';
			//$filename = '/home/lsong/proj/temp/conf/templates/ccl.xml';
			$confdata = new ConfData('vh', $filename);
			echo "Test file $filename \n";
			$root = $this->LoadData($confdata);

			$root = $xmlroot->DupHolder();
			$tblDef = DTblDef::GetInstance();
			$filemap = DPageDef::GetInstance()->GetFileMap($confdata->_type);   // serv, vh, tp, admin
			$filemap->Convert($xmlroot, $root, 0, 1);

			$root->PrintBuf($buf1);
			$newxml = $root->DupHolder();
			$filemap->Convert($root, $newxml, 1, 0);
			$newxml->PrintXmlBuf($buf1);
			echo $buf1;
			return true;
			//$this->ExportData($root);
*/
	}
}
