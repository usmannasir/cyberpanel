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

/* database/structure/table_header.twig */
class __TwigTemplate_08bb8cfb432300f4d4b45a0660189310aca03c30c6bf9897f2f544b501e920d8 extends \Twig\Template
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
        echo "<form method=\"post\" action=\"";
        echo PhpMyAdmin\Url::getFromRoute("/database/structure");
        echo "\" name=\"tablesForm\" id=\"tablesForm\">
";
        // line 2
        echo PhpMyAdmin\Url::getHiddenInputs(($context["db"] ?? null));
        echo "
<div class=\"table-responsive\">
<table class=\"table table-light table-striped table-hover table-sm w-auto data\">
    <thead class=\"thead-light\">
        <tr>
            <th class=\"d-print-none\"></th>
            <th>";
        // line 8
        echo PhpMyAdmin\Util::sortableTableHeader(_gettext("Table"), "table");
        echo "</th>
            ";
        // line 9
        if (($context["replication"] ?? null)) {
            // line 10
            echo "                <th>";
            echo _gettext("Replication");
            echo "</th>
            ";
        }
        // line 12
        echo "
            ";
        // line 13
        if (($context["db_is_system_schema"] ?? null)) {
            // line 14
            echo "                ";
            $context["action_colspan"] = 3;
            // line 15
            echo "            ";
        } else {
            // line 16
            echo "                ";
            $context["action_colspan"] = 6;
            // line 17
            echo "            ";
        }
        // line 18
        echo "            ";
        if ((($context["num_favorite_tables"] ?? null) > 0)) {
            // line 19
            echo "                ";
            $context["action_colspan"] = (($context["action_colspan"] ?? null) + 1);
            // line 20
            echo "            ";
        }
        // line 21
        echo "            <th colspan=\"";
        echo twig_escape_filter($this->env, ($context["action_colspan"] ?? null), "html", null, true);
        echo "\" class=\"d-print-none\">
                ";
        // line 22
        echo _gettext("Action");
        // line 23
        echo "            </th>
            ";
        // line 25
        echo "            <th>
                ";
        // line 26
        echo PhpMyAdmin\Util::sortableTableHeader(_gettext("Rows"), "records", "DESC");
        echo "
                ";
        // line 27
        echo \PhpMyAdmin\Html\Generator::showHint(PhpMyAdmin\Sanitize::sanitizeMessage(_gettext("May be approximate. Click on the number to get the exact count. See [doc@faq3-11]FAQ 3.11[/doc].")));
        echo "
            </th>
            ";
        // line 29
        if ( !(($context["properties_num_columns"] ?? null) > 1)) {
            // line 30
            echo "                <th>";
            echo PhpMyAdmin\Util::sortableTableHeader(_gettext("Type"), "type");
            echo "</th>
                <th>";
            // line 31
            echo PhpMyAdmin\Util::sortableTableHeader(_gettext("Collation"), "collation");
            echo "</th>
            ";
        }
        // line 33
        echo "
            ";
        // line 34
        if (($context["is_show_stats"] ?? null)) {
            // line 35
            echo "                ";
            // line 36
            echo "                <th>";
            echo PhpMyAdmin\Util::sortableTableHeader(_gettext("Size"), "size", "DESC");
            echo "</th>
                ";
            // line 38
            echo "                <th>";
            echo PhpMyAdmin\Util::sortableTableHeader(_gettext("Overhead"), "overhead", "DESC");
            echo "</th>
            ";
        }
        // line 40
        echo "
            ";
        // line 41
        if (($context["show_charset"] ?? null)) {
            // line 42
            echo "                <th>";
            echo PhpMyAdmin\Util::sortableTableHeader(_gettext("Charset"), "charset");
            echo "</th>
            ";
        }
        // line 44
        echo "
            ";
        // line 45
        if (($context["show_comment"] ?? null)) {
            // line 46
            echo "                <th>";
            echo PhpMyAdmin\Util::sortableTableHeader(_gettext("Comment"), "comment");
            echo "</th>
            ";
        }
        // line 48
        echo "
            ";
        // line 49
        if (($context["show_creation"] ?? null)) {
            // line 50
            echo "                ";
            // line 51
            echo "                <th>";
            echo PhpMyAdmin\Util::sortableTableHeader(_gettext("Creation"), "creation", "DESC");
            echo "</th>
            ";
        }
        // line 53
        echo "
            ";
        // line 54
        if (($context["show_last_update"] ?? null)) {
            // line 55
            echo "                ";
            // line 56
            echo "                <th>";
            echo PhpMyAdmin\Util::sortableTableHeader(_gettext("Last update"), "last_update", "DESC");
            echo "</th>
            ";
        }
        // line 58
        echo "
            ";
        // line 59
        if (($context["show_last_check"] ?? null)) {
            // line 60
            echo "                ";
            // line 61
            echo "                <th>";
            echo PhpMyAdmin\Util::sortableTableHeader(_gettext("Last check"), "last_check", "DESC");
            echo "</th>
            ";
        }
        // line 63
        echo "        </tr>
    </thead>
    <tbody>
    ";
        // line 66
        $context['_parent'] = $context;
        $context['_seq'] = twig_ensure_traversable(($context["structure_table_rows"] ?? null));
        foreach ($context['_seq'] as $context["_key"] => $context["structure_table_row"]) {
            // line 67
            echo "        ";
            $this->loadTemplate("database/structure/structure_table_row.twig", "database/structure/table_header.twig", 67)->display(twig_to_array($context["structure_table_row"]));
            // line 68
            echo "    ";
        }
        $_parent = $context['_parent'];
        unset($context['_seq'], $context['_iterated'], $context['_key'], $context['structure_table_row'], $context['_parent'], $context['loop']);
        $context = array_intersect_key($context, $_parent) + $_parent;
        // line 69
        echo "    </tbody>
    ";
        // line 70
        if (($context["body_for_table_summary"] ?? null)) {
            // line 71
            echo "        ";
            $this->loadTemplate("database/structure/body_for_table_summary.twig", "database/structure/table_header.twig", 71)->display(twig_to_array(($context["body_for_table_summary"] ?? null)));
            // line 72
            echo "    ";
        }
        // line 73
        echo "</table>
</div>
";
        // line 75
        if (($context["check_all_tables"] ?? null)) {
            // line 76
            echo "    ";
            $this->loadTemplate("database/structure/check_all_tables.twig", "database/structure/table_header.twig", 76)->display(twig_to_array(($context["check_all_tables"] ?? null)));
        }
        // line 78
        echo "</form>
";
    }

    public function getTemplateName()
    {
        return "database/structure/table_header.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  241 => 78,  237 => 76,  235 => 75,  231 => 73,  228 => 72,  225 => 71,  223 => 70,  220 => 69,  214 => 68,  211 => 67,  207 => 66,  202 => 63,  196 => 61,  194 => 60,  192 => 59,  189 => 58,  183 => 56,  181 => 55,  179 => 54,  176 => 53,  170 => 51,  168 => 50,  166 => 49,  163 => 48,  157 => 46,  155 => 45,  152 => 44,  146 => 42,  144 => 41,  141 => 40,  135 => 38,  130 => 36,  128 => 35,  126 => 34,  123 => 33,  118 => 31,  113 => 30,  111 => 29,  106 => 27,  102 => 26,  99 => 25,  96 => 23,  94 => 22,  89 => 21,  86 => 20,  83 => 19,  80 => 18,  77 => 17,  74 => 16,  71 => 15,  68 => 14,  66 => 13,  63 => 12,  57 => 10,  55 => 9,  51 => 8,  42 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "database/structure/table_header.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/database/structure/table_header.twig");
    }
}
