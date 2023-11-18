<?php

use Twig\Environment;
use Twig\Error\LoaderError;
use Twig\Error\RuntimeError;
use Twig\Extension\SandboxExtension;
use Twig\Markup;
use Twig\Sandbox\SecurityError;
use Twig\Sandbox\SecurityNotAllowedTagError;
use Twig\Sandbox\SecurityNotAllowedFilterError;
use Twig\Sandbox\SecurityNotAllowedFunctionError;
use Twig\Source;
use Twig\Template;

/* database/structure/check_all_tables.twig */
class __TwigTemplate_b3fe2ccd2f9f96e0fbd2e7dae3f7e1685e4f28cae6aaec1acbb0b7851799e1b7 extends \Twig\Template
{
    private $source;
    private $macros = [];

    public function __construct(Environment $env)
    {
        parent::__construct($env);

        $this->source = $this->getSourceContext();

        $this->parent = false;

        $this->blocks = [
        ];
    }

    protected function doDisplay(array $context, array $blocks = [])
    {
        $macros = $this->macros;
        // line 1
        echo "<div class=\"clearfloat print_ignore\">
    <img class=\"selectallarrow\" src=\"";
        // line 2
        echo twig_escape_filter($this->env, ($context["theme_image_path"] ?? null), "html", null, true);
        echo "arrow_";
        echo twig_escape_filter($this->env, ($context["text_dir"] ?? null), "html", null, true);
        echo ".png\" width=\"38\" height=\"22\" alt=\"";
        echo _gettext("With selected:");
        echo "\">
    <input type=\"checkbox\" id=\"tablesForm_checkall\" class=\"checkall_box\" title=\"";
        // line 3
        echo _gettext("Check all");
        echo "\">
    <label for=\"tablesForm_checkall\">";
        // line 4
        echo _gettext("Check all");
        echo "</label>
    ";
        // line 5
        if ((($context["overhead_check"] ?? null) != "")) {
            // line 6
            echo "        / <a href=\"#\" class=\"checkall-filter\" data-checkall-selector=\".tbl-overhead\">";
            echo _gettext("Check tables having overhead");
            echo "</a>
    ";
        }
        // line 8
        echo "    <select name=\"submit_mult\" style=\"margin: 0 3em 0 3em;\">
        <option value=\"";
        // line 9
        echo _gettext("With selected:");
        echo "\" selected=\"selected\">";
        echo _gettext("With selected:");
        echo "</option>
        <option value=\"copy_tbl\">";
        // line 10
        echo _gettext("Copy table");
        echo "</option>
        <option value=\"show_create\">";
        // line 11
        echo _gettext("Show create");
        echo "</option>
        <option value=\"export\">";
        // line 12
        echo _gettext("Export");
        echo "</option>
        ";
        // line 13
        if (( !($context["db_is_system_schema"] ?? null) &&  !($context["disable_multi_table"] ?? null))) {
            // line 14
            echo "            <optgroup label=\"";
            echo _gettext("Delete data or table");
            echo "\">
                <option value=\"empty_tbl\">";
            // line 15
            echo _gettext("Empty");
            echo "</option>
                <option value=\"drop_tbl\">";
            // line 16
            echo _gettext("Drop");
            echo "</option>
            </optgroup>
            <optgroup label=\"";
            // line 18
            echo _gettext("Table maintenance");
            echo "\">
                <option value=\"analyze_tbl\">";
            // line 19
            echo _gettext("Analyze table");
            echo "</option>
                <option value=\"check_tbl\">";
            // line 20
            echo _gettext("Check table");
            echo "</option>
                <option value=\"checksum_tbl\">";
            // line 21
            echo _gettext("Checksum table");
            echo "</option>
                <option value=\"optimize_tbl\">";
            // line 22
            echo _gettext("Optimize table");
            echo "</option>
                <option value=\"repair_tbl\">";
            // line 23
            echo _gettext("Repair table");
            echo "</option>
            </optgroup>
            <optgroup label=\"";
            // line 25
            echo _gettext("Prefix");
            echo "\">
                <option value=\"add_prefix_tbl\">";
            // line 26
            echo _gettext("Add prefix to table");
            echo "</option>
                <option value=\"replace_prefix_tbl\">";
            // line 27
            echo _gettext("Replace table prefix");
            echo "</option>
                <option value=\"copy_tbl_change_prefix\">";
            // line 28
            echo _gettext("Copy table with prefix");
            echo "</option>
            </optgroup>
        ";
        }
        // line 31
        echo "        ";
        if ((array_key_exists("central_columns_work", $context) && ($context["central_columns_work"] ?? null))) {
            // line 32
            echo "            <optgroup label=\"";
            echo _gettext("Central columns");
            echo "\">
                <option value=\"sync_unique_columns_central_list\">";
            // line 33
            echo _gettext("Add columns to central list");
            echo "</option>
                <option value=\"delete_unique_columns_central_list\">";
            // line 34
            echo _gettext("Remove columns from central list");
            echo "</option>
                <option value=\"make_consistent_with_central_list\">";
            // line 35
            echo _gettext("Make consistent with central list");
            echo "</option>
            </optgroup>
        ";
        }
        // line 38
        echo "    </select>
    ";
        // line 39
        echo twig_join_filter(($context["hidden_fields"] ?? null), "
");
        echo "
</div>
";
    }

    public function getTemplateName()
    {
        return "database/structure/check_all_tables.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  169 => 39,  166 => 38,  160 => 35,  156 => 34,  152 => 33,  147 => 32,  144 => 31,  138 => 28,  134 => 27,  130 => 26,  126 => 25,  121 => 23,  117 => 22,  113 => 21,  109 => 20,  105 => 19,  101 => 18,  96 => 16,  92 => 15,  87 => 14,  85 => 13,  81 => 12,  77 => 11,  73 => 10,  67 => 9,  64 => 8,  58 => 6,  56 => 5,  52 => 4,  48 => 3,  40 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "database/structure/check_all_tables.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/database/structure/check_all_tables.twig");
    }
}
