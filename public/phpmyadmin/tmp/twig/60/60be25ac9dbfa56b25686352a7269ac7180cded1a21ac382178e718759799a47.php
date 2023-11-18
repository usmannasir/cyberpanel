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

/* console/display.twig */
class __TwigTemplate_80076b819d5e639e4cb33ddfaf232d099a5031deab6875a5cea52d20f88ccad0 extends \Twig\Template
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
        echo "<div id=\"pma_console_container\">
    <div id=\"pma_console\">
        ";
        // line 4
        echo "        ";
        $this->loadTemplate("console/toolbar.twig", "console/display.twig", 4)->display(twig_to_array(["parent_div_classes" => "collapsed", "content_array" => [0 => [0 => "switch_button console_switch", 1 => _gettext("Console"), "image" =>         // line 7
($context["image"] ?? null)], 1 => [0 => "button clear", 1 => _gettext("Clear")], 2 => [0 => "button history", 1 => _gettext("History")], 3 => [0 => "button options", 1 => _gettext("Options")], 4 => ((        // line 11
array_key_exists("cfg_bookmark", $context)) ? ([0 => "button bookmarks", 1 => _gettext("Bookmarks")]) : (null)), 5 => [0 => "button debug hide", 1 => _gettext("Debug SQL")]]]));
        // line 15
        echo "        ";
        // line 16
        echo "        <div class=\"content\">
            <div class=\"console_message_container\">
                <div class=\"message welcome\">
                    <span id=\"instructions-0\">
                        ";
        // line 20
        echo _gettext("Press Ctrl+Enter to execute query");
        // line 21
        echo "                    </span>
                    <span class=\"hide\" id=\"instructions-1\">
                        ";
        // line 23
        echo _gettext("Press Enter to execute query");
        // line 24
        echo "                    </span>
                </div>
                ";
        // line 26
        if ( !twig_test_empty(($context["sql_history"] ?? null))) {
            // line 27
            echo "                    ";
            $context['_parent'] = $context;
            $context['_seq'] = twig_ensure_traversable(twig_reverse_filter($this->env, ($context["sql_history"] ?? null)));
            foreach ($context['_seq'] as $context["_key"] => $context["record"]) {
                // line 28
                echo "                        <div class=\"message history collapsed hide";
                // line 29
                echo ((preg_match("@^SELECT[[:space:]]+@i", (($__internal_compile_0 = $context["record"]) && is_array($__internal_compile_0) || $__internal_compile_0 instanceof ArrayAccess ? ($__internal_compile_0["sqlquery"] ?? null) : null))) ? (" select") : (""));
                echo "\"
                            targetdb=\"";
                // line 30
                echo twig_escape_filter($this->env, (($__internal_compile_1 = $context["record"]) && is_array($__internal_compile_1) || $__internal_compile_1 instanceof ArrayAccess ? ($__internal_compile_1["db"] ?? null) : null), "html", null, true);
                echo "\" targettable=\"";
                echo twig_escape_filter($this->env, (($__internal_compile_2 = $context["record"]) && is_array($__internal_compile_2) || $__internal_compile_2 instanceof ArrayAccess ? ($__internal_compile_2["table"] ?? null) : null), "html", null, true);
                echo "\">
                            ";
                // line 31
                $this->loadTemplate("console/query_action.twig", "console/display.twig", 31)->display(twig_to_array(["parent_div_classes" => "action_content", "content_array" => [0 => [0 => "action collapse", 1 => _gettext("Collapse")], 1 => [0 => "action expand", 1 => _gettext("Expand")], 2 => [0 => "action requery", 1 => _gettext("Requery")], 3 => [0 => "action edit", 1 => _gettext("Edit")], 4 => [0 => "action explain", 1 => _gettext("Explain")], 5 => [0 => "action profiling", 1 => _gettext("Profiling")], 6 => ((                // line 40
array_key_exists("cfg_bookmark", $context)) ? ([0 => "action bookmark", 1 => _gettext("Bookmark")]) : (null)), 7 => [0 => "text failed", 1 => _gettext("Query failed")], 8 => [0 => "text targetdb", 1 => _gettext("Database"), "extraSpan" => (($__internal_compile_3 =                 // line 42
$context["record"]) && is_array($__internal_compile_3) || $__internal_compile_3 instanceof ArrayAccess ? ($__internal_compile_3["db"] ?? null) : null)], 9 => [0 => "text query_time", 1 => _gettext("Queried time"), "extraSpan" => ((twig_get_attribute($this->env, $this->source,                 // line 46
$context["record"], "timevalue", [], "array", true, true, false, 46)) ? ((($__internal_compile_4 =                 // line 47
$context["record"]) && is_array($__internal_compile_4) || $__internal_compile_4 instanceof ArrayAccess ? ($__internal_compile_4["timevalue"] ?? null) : null)) : (_gettext("During current session")))]]]));
                // line 51
                echo "                            <span class=\"query\">";
                echo twig_escape_filter($this->env, (($__internal_compile_5 = $context["record"]) && is_array($__internal_compile_5) || $__internal_compile_5 instanceof ArrayAccess ? ($__internal_compile_5["sqlquery"] ?? null) : null), "html", null, true);
                echo "</span>
                        </div>
                    ";
            }
            $_parent = $context['_parent'];
            unset($context['_seq'], $context['_iterated'], $context['_key'], $context['record'], $context['_parent'], $context['loop']);
            $context = array_intersect_key($context, $_parent) + $_parent;
            // line 54
            echo "                ";
        }
        // line 55
        echo "            </div><!-- console_message_container -->
            <div class=\"query_input\">
                <span class=\"console_query_input\"></span>
            </div>
        </div><!-- message end -->
        ";
        // line 61
        echo "        <div class=\"mid_layer\"></div>
        ";
        // line 63
        echo "        <div class=\"card\" id=\"debug_console\">
            ";
        // line 64
        $this->loadTemplate("console/toolbar.twig", "console/display.twig", 64)->display(twig_to_array(["parent_div_classes" => "", "content_array" => [0 => [0 => "button order order_asc", 1 => _gettext("ascending")], 1 => [0 => "button order order_desc", 1 => _gettext("descending")], 2 => [0 => "text", 1 => _gettext("Order:")], 3 => [0 => "switch_button", 1 => _gettext("Debug SQL")], 4 => [0 => "button order_by sort_count", 1 => _gettext("Count")], 5 => [0 => "button order_by sort_exec", 1 => _gettext("Execution order")], 6 => [0 => "button order_by sort_time", 1 => _gettext("Time taken")], 7 => [0 => "text", 1 => _gettext("Order by:")], 8 => [0 => "button group_queries", 1 => _gettext("Group queries")], 9 => [0 => "button ungroup_queries", 1 => _gettext("Ungroup queries")]]]));
        // line 79
        echo "            <div class=\"content debug\">
                <div class=\"message welcome\"></div>
                <div class=\"debugLog\"></div>
            </div> <!-- Content -->
            <div class=\"templates\">
                ";
        // line 84
        $this->loadTemplate("console/query_action.twig", "console/display.twig", 84)->display(twig_to_array(["parent_div_classes" => "debug_query action_content", "content_array" => [0 => [0 => "action collapse", 1 => _gettext("Collapse")], 1 => [0 => "action expand", 1 => _gettext("Expand")], 2 => [0 => "action dbg_show_trace", 1 => _gettext("Show trace")], 3 => [0 => "action dbg_hide_trace", 1 => _gettext("Hide trace")], 4 => [0 => "text count hide", 1 => _gettext("Count")], 5 => [0 => "text time", 1 => _gettext("Time taken")]]]));
        // line 95
        echo "            </div> <!-- Template -->
        </div> <!-- Debug SQL card -->
        ";
        // line 97
        if (($context["cfg_bookmark"] ?? null)) {
            // line 98
            echo "            <div class=\"card\" id=\"pma_bookmarks\">
                ";
            // line 99
            $this->loadTemplate("console/toolbar.twig", "console/display.twig", 99)->display(twig_to_array(["parent_div_classes" => "", "content_array" => [0 => [0 => "switch_button", 1 => _gettext("Bookmarks")], 1 => [0 => "button refresh", 1 => _gettext("Refresh")], 2 => [0 => "button add", 1 => _gettext("Add")]]]));
            // line 107
            echo "                <div class=\"content bookmark\">
                    ";
            // line 108
            echo ($context["bookmark_content"] ?? null);
            echo "
                </div>
                <div class=\"mid_layer\"></div>
                <div class=\"card add\">
                    ";
            // line 112
            $this->loadTemplate("console/toolbar.twig", "console/display.twig", 112)->display(twig_to_array(["parent_div_classes" => "", "content_array" => [0 => [0 => "switch_button", 1 => _gettext("Add bookmark")]]]));
            // line 118
            echo "                    <div class=\"content add_bookmark\">
                        <div class=\"options\">
                            <label>
                                ";
            // line 121
            echo _gettext("Label");
            echo ": <input type=\"text\" name=\"label\">
                            </label>
                            <label>
                                ";
            // line 124
            echo _gettext("Target database");
            echo ": <input type=\"text\" name=\"targetdb\">
                            </label>
                            <label>
                                <input type=\"checkbox\" name=\"shared\">";
            // line 127
            echo _gettext("Share this bookmark");
            // line 128
            echo "                            </label>
                            <button class=\"btn btn-primary\" type=\"submit\" name=\"submit\">";
            // line 129
            echo _gettext("OK");
            echo "</button>
                        </div> <!-- options -->
                        <div class=\"query_input\">
                            <span class=\"bookmark_add_input\"></span>
                        </div>
                    </div>
                </div> <!-- Add bookmark card -->
            </div> <!-- Bookmarks card -->
        ";
        }
        // line 138
        echo "        ";
        // line 139
        echo "        <div class=\"card\" id=\"pma_console_options\">
            ";
        // line 140
        $this->loadTemplate("console/toolbar.twig", "console/display.twig", 140)->display(twig_to_array(["parent_div_classes" => "", "content_array" => [0 => [0 => "switch_button", 1 => _gettext("Options")], 1 => [0 => "button default", 1 => _gettext("Set default")]]]));
        // line 147
        echo "            <div class=\"content\">
                <label>
                    <input type=\"checkbox\" name=\"always_expand\">";
        // line 149
        echo _gettext("Always expand query messages");
        // line 150
        echo "                </label>
                <br>
                <label>
                    <input type=\"checkbox\" name=\"start_history\">";
        // line 153
        echo _gettext("Show query history at start");
        // line 154
        echo "                </label>
                <br>
                <label>
                    <input type=\"checkbox\" name=\"current_query\">";
        // line 157
        echo _gettext("Show current browsing query");
        // line 158
        echo "                </label>
                <br>
                <label>
                    <input type=\"checkbox\" name=\"enter_executes\">
                        ";
        // line 162
        echo _gettext("Execute queries on Enter and insert new line with Shift + Enter. To make this permanent, view settings.");
        // line 165
        echo "                </label>
                <br>
                <label>
                    <input type=\"checkbox\" name=\"dark_theme\">";
        // line 168
        echo _gettext("Switch to dark theme");
        // line 169
        echo "                </label>
                <br>
            </div>
        </div> <!-- Options card -->
        <div class=\"templates\">
            ";
        // line 175
        echo "            ";
        $this->loadTemplate("console/query_action.twig", "console/display.twig", 175)->display(twig_to_array(["parent_div_classes" => "query_actions", "content_array" => [0 => [0 => "action collapse", 1 => _gettext("Collapse")], 1 => [0 => "action expand", 1 => _gettext("Expand")], 2 => [0 => "action requery", 1 => _gettext("Requery")], 3 => [0 => "action edit", 1 => _gettext("Edit")], 4 => [0 => "action explain", 1 => _gettext("Explain")], 5 => [0 => "action profiling", 1 => _gettext("Profiling")], 6 => ((        // line 184
array_key_exists("cfg_bookmark", $context)) ? ([0 => "action bookmark", 1 => _gettext("Bookmark")]) : (null)), 7 => [0 => "text failed", 1 => _gettext("Query failed")], 8 => [0 => "text targetdb", 1 => _gettext("Database"), "extraSpan" => ""], 9 => [0 => "text query_time", 1 => _gettext("Queried time"), "extraSpan" => ""]]]));
        // line 190
        echo "        </div>
    </div> <!-- #console end -->
</div> <!-- #console_container end -->
";
    }

    public function getTemplateName()
    {
        return "console/display.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  238 => 190,  236 => 184,  234 => 175,  227 => 169,  225 => 168,  220 => 165,  218 => 162,  212 => 158,  210 => 157,  205 => 154,  203 => 153,  198 => 150,  196 => 149,  192 => 147,  190 => 140,  187 => 139,  185 => 138,  173 => 129,  170 => 128,  168 => 127,  162 => 124,  156 => 121,  151 => 118,  149 => 112,  142 => 108,  139 => 107,  137 => 99,  134 => 98,  132 => 97,  128 => 95,  126 => 84,  119 => 79,  117 => 64,  114 => 63,  111 => 61,  104 => 55,  101 => 54,  91 => 51,  89 => 47,  88 => 46,  87 => 42,  86 => 40,  85 => 31,  79 => 30,  75 => 29,  73 => 28,  68 => 27,  66 => 26,  62 => 24,  60 => 23,  56 => 21,  54 => 20,  48 => 16,  46 => 15,  44 => 11,  43 => 7,  41 => 4,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "console/display.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/console/display.twig");
    }
}
