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

/* database/structure/body_for_table_summary.twig */
class __TwigTemplate_22c47d7681533131f798a127b03cdc6ff1329e41f7b954cb88ec0c8bd3cfe7bd extends \Twig\Template
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
        echo "<tfoot id=\"tbl_summary_row\" class=\"thead-light\">
<tr>
    <th class=\"d-print-none\"></th>
    <th class=\"tbl_num text-nowrap\">
        ";
        // line 5
        ob_start(function () { return ''; });
        // line 6
        echo _ngettext("%s table", "%s tables", abs(($context["num_tables"] ?? null)));
        $context["num_tables_trans"] = ('' === $tmp = ob_get_clean()) ? '' : new Markup($tmp, $this->env->getCharset());
        // line 8
        echo "        ";
        echo twig_escape_filter($this->env, twig_sprintf(($context["num_tables_trans"] ?? null), PhpMyAdmin\Util::formatNumber(($context["num_tables"] ?? null), 0)), "html", null, true);
        echo "
    </th>
    ";
        // line 10
        if (($context["server_slave_status"] ?? null)) {
            // line 11
            echo "        <th>";
            echo _gettext("Replication");
            echo "</th>
    ";
        }
        // line 13
        echo "    ";
        $context["sum_colspan"] = ((($context["db_is_system_schema"] ?? null)) ? (4) : (7));
        // line 14
        echo "    ";
        if ((($context["num_favorite_tables"] ?? null) == 0)) {
            // line 15
            echo "        ";
            $context["sum_colspan"] = (($context["sum_colspan"] ?? null) - 1);
            // line 16
            echo "    ";
        }
        // line 17
        echo "    <th colspan=\"";
        echo twig_escape_filter($this->env, ($context["sum_colspan"] ?? null), "html", null, true);
        echo "\" class=\"d-print-none\">";
        echo _gettext("Sum");
        echo "</th>
    ";
        // line 18
        $context["row_count_sum"] = PhpMyAdmin\Util::formatNumber(($context["sum_entries"] ?? null), 0);
        // line 19
        echo "    ";
        // line 20
        echo "    ";
        $context["row_sum_url"] = [];
        // line 21
        echo "    ";
        if (array_key_exists("approx_rows", $context)) {
            // line 22
            echo "        ";
            $context["row_sum_url"] = ["ajax_request" => true, "db" =>             // line 24
($context["db"] ?? null), "real_row_count_all" => "true"];
            // line 27
            echo "    ";
        }
        // line 28
        echo "    ";
        if (($context["approx_rows"] ?? null)) {
            // line 29
            echo "        ";
            ob_start(function () { return ''; });
            // line 30
            echo "<a href=\"";
            echo PhpMyAdmin\Url::getFromRoute("/database/structure/real-row-count", ($context["row_sum_url"] ?? null));
            echo "\" class=\"ajax row_count_sum\">~";
            // line 31
            echo twig_escape_filter($this->env, ($context["row_count_sum"] ?? null), "html", null, true);
            // line 32
            echo "</a>";
            $context["cell_text"] = ('' === $tmp = ob_get_clean()) ? '' : new Markup($tmp, $this->env->getCharset());
            // line 34
            echo "    ";
        } else {
            // line 35
            echo "        ";
            $context["cell_text"] = ($context["row_count_sum"] ?? null);
            // line 36
            echo "    ";
        }
        // line 37
        echo "    <th class=\"value tbl_rows text-monospace text-right\">";
        echo twig_escape_filter($this->env, ($context["cell_text"] ?? null), "html", null, true);
        echo "</th>
    ";
        // line 38
        if ( !(($context["properties_num_columns"] ?? null) > 1)) {
            // line 39
            echo "        ";
            // line 40
            echo "        ";
            $context["default_engine"] = twig_get_attribute($this->env, $this->source, ($context["dbi"] ?? null), "fetchValue", [0 => "SELECT @@storage_engine;"], "method", false, false, false, 40);
            // line 41
            echo "        ";
            if (twig_test_empty(($context["default_engine"] ?? null))) {
                // line 42
                echo "            ";
                // line 43
                echo "            ";
                $context["default_engine"] = twig_get_attribute($this->env, $this->source, ($context["dbi"] ?? null), "fetchValue", [0 => "SELECT @@default_storage_engine;"], "method", false, false, false, 43);
                // line 44
                echo "        ";
            }
            // line 45
            echo "        <th class=\"text-center\">
            <dfn title=\"";
            // line 46
            echo twig_escape_filter($this->env, twig_sprintf(_gettext("%s is the default storage engine on this MySQL server."), ($context["default_engine"] ?? null)), "html", null, true);
            echo "\">
                ";
            // line 47
            echo twig_escape_filter($this->env, ($context["default_engine"] ?? null), "html", null, true);
            echo "
            </dfn>
        </th>
        <th>
            ";
            // line 51
            if ( !twig_test_empty(($context["database_collation"] ?? null))) {
                // line 52
                echo "                <dfn title=\"";
                echo twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, ($context["database_collation"] ?? null), "description", [], "any", false, false, false, 52), "html", null, true);
                echo " (";
                echo _gettext("Default");
                echo ")\">
                    ";
                // line 53
                echo twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, ($context["database_collation"] ?? null), "name", [], "any", false, false, false, 53), "html", null, true);
                echo "
                </dfn>
            ";
            }
            // line 56
            echo "        </th>
    ";
        }
        // line 58
        echo "
    ";
        // line 59
        if (($context["is_show_stats"] ?? null)) {
            // line 60
            echo "        ";
            $context["sum"] = PhpMyAdmin\Util::formatByteDown(($context["sum_size"] ?? null), 3, 1);
            // line 61
            echo "        ";
            $context["sum_formatted"] = (($__internal_compile_0 = ($context["sum"] ?? null)) && is_array($__internal_compile_0) || $__internal_compile_0 instanceof ArrayAccess ? ($__internal_compile_0[0] ?? null) : null);
            // line 62
            echo "        ";
            $context["sum_unit"] = (($__internal_compile_1 = ($context["sum"] ?? null)) && is_array($__internal_compile_1) || $__internal_compile_1 instanceof ArrayAccess ? ($__internal_compile_1[1] ?? null) : null);
            // line 63
            echo "        <th class=\"value tbl_size text-monospace text-right\">";
            echo twig_escape_filter($this->env, ($context["sum_formatted"] ?? null), "html", null, true);
            echo " ";
            echo twig_escape_filter($this->env, ($context["sum_unit"] ?? null), "html", null, true);
            echo "</th>

        ";
            // line 65
            $context["overhead"] = PhpMyAdmin\Util::formatByteDown(($context["overhead_size"] ?? null), 3, 1);
            // line 66
            echo "        ";
            $context["overhead_formatted"] = (($__internal_compile_2 = ($context["overhead"] ?? null)) && is_array($__internal_compile_2) || $__internal_compile_2 instanceof ArrayAccess ? ($__internal_compile_2[0] ?? null) : null);
            // line 67
            echo "        ";
            $context["overhead_unit"] = (($__internal_compile_3 = ($context["overhead"] ?? null)) && is_array($__internal_compile_3) || $__internal_compile_3 instanceof ArrayAccess ? ($__internal_compile_3[1] ?? null) : null);
            // line 68
            echo "        <th class=\"value tbl_overhead text-monospace text-right\">";
            echo twig_escape_filter($this->env, ($context["overhead_formatted"] ?? null), "html", null, true);
            echo " ";
            echo twig_escape_filter($this->env, ($context["overhead_unit"] ?? null), "html", null, true);
            echo "</th>
    ";
        }
        // line 70
        echo "
    ";
        // line 71
        if (($context["show_charset"] ?? null)) {
            // line 72
            echo "        <th>";
            echo twig_escape_filter($this->env, ($context["database_charset"] ?? null), "html", null, true);
            echo "</th>
    ";
        }
        // line 74
        echo "    ";
        if (($context["show_comment"] ?? null)) {
            // line 75
            echo "        <th></th>
    ";
        }
        // line 77
        echo "    ";
        if (($context["show_creation"] ?? null)) {
            // line 78
            echo "        <th class=\"value tbl_creation text-monospace text-right\">
            ";
            // line 79
            echo twig_escape_filter($this->env, ($context["create_time_all"] ?? null), "html", null, true);
            echo "
        </th>
    ";
        }
        // line 82
        echo "    ";
        if (($context["show_last_update"] ?? null)) {
            // line 83
            echo "        <th class=\"value tbl_last_update text-monospace text-right\">
            ";
            // line 84
            echo twig_escape_filter($this->env, ($context["update_time_all"] ?? null), "html", null, true);
            echo "
        </th>
    ";
        }
        // line 87
        echo "    ";
        if (($context["show_last_check"] ?? null)) {
            // line 88
            echo "        <th class=\"value tbl_last_check text-monospace text-right\">
            ";
            // line 89
            echo twig_escape_filter($this->env, ($context["check_time_all"] ?? null), "html", null, true);
            echo "
        </th>
    ";
        }
        // line 92
        echo "</tr>
</tfoot>
";
    }

    public function getTemplateName()
    {
        return "database/structure/body_for_table_summary.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  270 => 92,  264 => 89,  261 => 88,  258 => 87,  252 => 84,  249 => 83,  246 => 82,  240 => 79,  237 => 78,  234 => 77,  230 => 75,  227 => 74,  221 => 72,  219 => 71,  216 => 70,  208 => 68,  205 => 67,  202 => 66,  200 => 65,  192 => 63,  189 => 62,  186 => 61,  183 => 60,  181 => 59,  178 => 58,  174 => 56,  168 => 53,  161 => 52,  159 => 51,  152 => 47,  148 => 46,  145 => 45,  142 => 44,  139 => 43,  137 => 42,  134 => 41,  131 => 40,  129 => 39,  127 => 38,  122 => 37,  119 => 36,  116 => 35,  113 => 34,  110 => 32,  108 => 31,  104 => 30,  101 => 29,  98 => 28,  95 => 27,  93 => 24,  91 => 22,  88 => 21,  85 => 20,  83 => 19,  81 => 18,  74 => 17,  71 => 16,  68 => 15,  65 => 14,  62 => 13,  56 => 11,  54 => 10,  48 => 8,  45 => 6,  43 => 5,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "database/structure/body_for_table_summary.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/database/structure/body_for_table_summary.twig");
    }
}
